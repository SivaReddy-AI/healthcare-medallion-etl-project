import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    import boto3
except ImportError:  # local unit tests can run without AWS libraries
    boto3 = None

try:
    import snowflake.connector
except ImportError:
    snowflake = None

from config import Config

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"
SILVER_DIR = BASE_DIR / "data" / "silver"
for d in [LOG_DIR, REPORT_DIR, SILVER_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "etl.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

REQUIRED_SCHEMAS = {
    "patients": ["patient_id", "patient_name", "dob", "gender"],
    "appointments": ["appointment_id", "patient_id", "doctor_id", "start_time", "end_time"],
    "treatments": ["treatment_id", "appointment_id", "treatment_type", "duration_minutes", "cost"],
}


def validate_schema(df: pd.DataFrame, required_columns: List[str], table_name: str) -> List[str]:
    missing = sorted(list(set(required_columns) - set(df.columns)))
    if missing:
        logging.error("%s missing columns: %s", table_name, missing)
    return missing


def drop_duplicates(df: pd.DataFrame, key_columns: List[str]) -> Tuple[pd.DataFrame, int]:
    before = len(df)
    cleaned = df.drop_duplicates(subset=key_columns, keep="first").copy()
    return cleaned, before - len(cleaned)


def calculate_visit_duration(start: pd.Series, end: pd.Series) -> pd.Series:
    return (end - start).dt.total_seconds() / 60


def aggregate_treatment_costs(treatments_df: pd.DataFrame) -> pd.DataFrame:
    return treatments_df.groupby("appointment_id", as_index=False).agg(
        total_treatment_cost=("cost", "sum"),
        avg_treatment_cost=("cost", "mean"),
        treatment_count=("treatment_id", "count"),
        total_treatment_duration=("duration_minutes", "sum")
    )


class HealthcareETL:
    def __init__(self, patients_file: str, appointments_file: str, treatments_file: str, config: Config | None = None):
        self.patients_file = patients_file
        self.appointments_file = appointments_file
        self.treatments_file = treatments_file
        self.config = config or Config()
        self.patients_df = pd.DataFrame()
        self.appointments_df = pd.DataFrame()
        self.treatments_df = pd.DataFrame()
        self.dim_patient = pd.DataFrame()
        self.dim_appointment = pd.DataFrame()
        self.dim_doctor = pd.DataFrame()
        self.fact_treatment = pd.DataFrame()
        self.audit_log = []
        self.metrics = {
            "rows_extracted": 0,
            "rows_transformed": 0,
            "rows_loaded": 0,
            "invalid_records": 0,
            "duplicates_removed": 0,
            "orphan_appointments": 0,
            "orphan_treatments": 0,
        }

    def upload_bronze_to_s3(self):
        if boto3 is None:
            logging.warning("boto3 not installed. Skipping S3 bronze upload.")
            return
        s3 = boto3.client("s3", region_name=self.config.aws_region)
        for file_path in [self.patients_file, self.appointments_file, self.treatments_file]:
            key = f"{self.config.bronze_prefix}/{Path(file_path).name}"
            s3.upload_file(file_path, self.config.s3_bucket, key)
            logging.info("Uploaded raw file to s3://%s/%s", self.config.s3_bucket, key)

    def extract(self):
        logging.info("Extract started")
        self.patients_df = pd.read_csv(self.patients_file, on_bad_lines="skip")
        self.appointments_df = pd.read_csv(self.appointments_file, on_bad_lines="skip")
        self.treatments_df = pd.read_csv(self.treatments_file, on_bad_lines="skip")
        self.metrics["rows_extracted"] = len(self.patients_df) + len(self.appointments_df) + len(self.treatments_df)
        logging.info("Extract completed: %s rows", self.metrics["rows_extracted"])

    def validate(self):
        logging.info("Validation started")
        quality_rows = []
        for name, df in [("patients", self.patients_df), ("appointments", self.appointments_df), ("treatments", self.treatments_df)]:
            missing_cols = validate_schema(df, REQUIRED_SCHEMAS[name], name)
            duplicate_count = df.duplicated().sum()
            missing_values = int(df.isna().sum().sum())
            quality_rows.append({
                "table_name": name,
                "row_count": len(df),
                "missing_columns": ",".join(missing_cols),
                "missing_values": missing_values,
                "duplicate_rows": int(duplicate_count),
            })
        self.data_quality_report = pd.DataFrame(quality_rows)
        self.data_quality_report.to_csv(REPORT_DIR / "data_quality_report_extract.csv", index=False)
        logging.info("Validation completed")

    def transform(self):
        logging.info("Transform started")
        # Patients
        self.patients_df["patient_id"] = pd.to_numeric(self.patients_df["patient_id"], errors="coerce")
        self.patients_df["patient_name"] = self.patients_df["patient_name"].astype("string").str.strip().str.title()
        self.patients_df["dob"] = pd.to_datetime(self.patients_df["dob"], errors="coerce").dt.date
        self.patients_df["gender"] = self.patients_df["gender"].astype("string").str.strip().str.upper()
        self.patients_df["gender"] = self.patients_df["gender"].replace({"MALE": "M", "FEMALE": "F"})
        self.patients_df = self.patients_df.dropna(subset=["patient_id", "patient_name", "dob"])
        self.patients_df, dup = drop_duplicates(self.patients_df, ["patient_id"])
        self.metrics["duplicates_removed"] += dup
        self.patients_df["patient_id"] = self.patients_df["patient_id"].astype(int)

        # Appointments
        self.appointments_df["appointment_id"] = pd.to_numeric(self.appointments_df["appointment_id"], errors="coerce")
        self.appointments_df["patient_id"] = pd.to_numeric(self.appointments_df["patient_id"], errors="coerce")
        self.appointments_df["doctor_id"] = pd.to_numeric(self.appointments_df["doctor_id"], errors="coerce")
        self.appointments_df["start_time"] = pd.to_datetime(self.appointments_df["start_time"], errors="coerce")
        self.appointments_df["end_time"] = pd.to_datetime(self.appointments_df["end_time"], errors="coerce")
        self.appointments_df["visit_duration_minutes"] = calculate_visit_duration(self.appointments_df["start_time"], self.appointments_df["end_time"])
        self.appointments_df = self.appointments_df.dropna(subset=["appointment_id", "patient_id", "doctor_id", "start_time", "end_time", "visit_duration_minutes"])
        self.appointments_df = self.appointments_df[self.appointments_df["visit_duration_minutes"] > 0]
        self.appointments_df, dup = drop_duplicates(self.appointments_df, ["appointment_id"])
        self.metrics["duplicates_removed"] += dup
        self.appointments_df[["appointment_id", "patient_id", "doctor_id"]] = self.appointments_df[["appointment_id", "patient_id", "doctor_id"]].astype(int)

        # Treatments
        self.treatments_df["treatment_id"] = pd.to_numeric(self.treatments_df["treatment_id"], errors="coerce")
        self.treatments_df["appointment_id"] = pd.to_numeric(self.treatments_df["appointment_id"], errors="coerce")
        self.treatments_df["duration_minutes"] = pd.to_numeric(self.treatments_df["duration_minutes"], errors="coerce")
        self.treatments_df["cost"] = pd.to_numeric(self.treatments_df["cost"], errors="coerce")
        self.treatments_df["treatment_type"] = self.treatments_df["treatment_type"].astype("category")
        self.treatments_df = self.treatments_df.dropna(subset=["treatment_id", "appointment_id", "treatment_type", "duration_minutes", "cost"])
        self.treatments_df = self.treatments_df[(self.treatments_df["duration_minutes"] > 0) & (self.treatments_df["cost"] >= 0)]
        self.treatments_df, dup = drop_duplicates(self.treatments_df, ["treatment_id"])
        self.metrics["duplicates_removed"] += dup
        self.treatments_df[["treatment_id", "appointment_id"]] = self.treatments_df[["treatment_id", "appointment_id"]].astype(int)
        self.metrics["rows_transformed"] = len(self.patients_df) + len(self.appointments_df) + len(self.treatments_df)
        logging.info("Transform completed")

    def enrich(self, frequent_visit_threshold: int = 3):
        logging.info("Enrich started")
        valid_patients = set(self.patients_df["patient_id"])
        valid_appointments = set(self.appointments_df["appointment_id"])

        orphan_appointments_df = self.appointments_df[~self.appointments_df["patient_id"].isin(valid_patients)]
        orphan_treatments_df = self.treatments_df[~self.treatments_df["appointment_id"].isin(valid_appointments)]
        self.metrics["orphan_appointments"] = len(orphan_appointments_df)
        self.metrics["orphan_treatments"] = len(orphan_treatments_df)

        self.appointments_df = self.appointments_df[self.appointments_df["patient_id"].isin(valid_patients)].copy()
        self.treatments_df = self.treatments_df[self.treatments_df["appointment_id"].isin(set(self.appointments_df["appointment_id"]))].copy()

        costs = aggregate_treatment_costs(self.treatments_df)
        self.dim_appointment = self.appointments_df.merge(costs, on="appointment_id", how="left").fillna({
            "total_treatment_cost": 0,
            "avg_treatment_cost": 0,
            "treatment_count": 0,
            "total_treatment_duration": 0,
        })
        self.dim_appointment["appointment_month"] = self.dim_appointment["start_time"].dt.to_period("M").astype(str)

        visit_counts = self.dim_appointment.groupby(["patient_id", "appointment_month"]).size().reset_index(name="monthly_visit_count")
        frequent = visit_counts[visit_counts["monthly_visit_count"] > frequent_visit_threshold]["patient_id"].unique()
        self.dim_patient = self.patients_df.copy()
        self.dim_patient["is_frequent_visitor"] = self.dim_patient["patient_id"].isin(frequent)
        self.dim_patient["signup_month"] = pd.to_datetime(self.dim_patient["dob"], errors="coerce").astype("datetime64[ns]").dt.to_period("M").astype(str)

        self.dim_doctor = self.dim_appointment[["doctor_id"]].drop_duplicates().copy()
        self.dim_doctor["doctor_name"] = "Doctor " + self.dim_doctor["doctor_id"].astype(str)

        threshold = np.percentile(self.treatments_df["cost"], 99) if len(self.treatments_df) else 0
        self.fact_treatment = self.treatments_df.copy()
        self.fact_treatment["is_high_cost_outlier"] = self.fact_treatment["cost"] >= threshold
        self.fact_treatment["load_timestamp"] = pd.Timestamp.utcnow()

        # Overlapping appointments
        sorted_appts = self.dim_appointment.sort_values(["patient_id", "start_time"])
        sorted_appts["previous_end_time"] = sorted_appts.groupby("patient_id")["end_time"].shift(1)
        sorted_appts["has_overlap"] = sorted_appts["start_time"] < sorted_appts["previous_end_time"]
        overlap_cols = sorted_appts[["appointment_id", "has_overlap"]]
        self.dim_appointment = self.dim_appointment.merge(overlap_cols, on="appointment_id", how="left")

        stats = pd.DataFrame([{
            "average_treatment_cost": float(np.mean(self.fact_treatment["cost"])) if len(self.fact_treatment) else 0,
            "median_visit_duration": float(np.median(self.dim_appointment["visit_duration_minutes"])) if len(self.dim_appointment) else 0,
            "std_treatment_duration": float(np.std(self.fact_treatment["duration_minutes"])) if len(self.fact_treatment) else 0,
            "high_cost_threshold": float(threshold),
        }])
        stats.to_csv(REPORT_DIR / "business_metrics_summary.csv", index=False)
        logging.info("Enrich completed")

    def save_silver_locally(self):
        self.dim_patient.to_csv(SILVER_DIR / "dim_patient.csv", index=False)
        self.dim_appointment.to_csv(SILVER_DIR / "dim_appointment.csv", index=False)
        self.dim_doctor.to_csv(SILVER_DIR / "dim_doctor.csv", index=False)
        self.fact_treatment.to_csv(SILVER_DIR / "fact_treatment.csv", index=False)
        pd.DataFrame([self.metrics]).to_csv(REPORT_DIR / "etl_metrics.csv", index=False)
        logging.info("Silver CSV files saved locally")

    def upload_silver_to_s3(self):
        if boto3 is None:
            logging.warning("boto3 not installed. Skipping S3 silver upload.")
            return
        s3 = boto3.client("s3", region_name=self.config.aws_region)
        for file_path in SILVER_DIR.glob("*.csv"):
            key = f"{self.config.silver_prefix}/{file_path.name}"
            s3.upload_file(str(file_path), self.config.s3_bucket, key)
            logging.info("Uploaded silver file to s3://%s/%s", self.config.s3_bucket, key)

    def load(self, snowflake_connection=None):
        # In local portfolio mode, loading is represented by saved silver CSV + Snowflake SQL scripts.
        self.metrics["rows_loaded"] = len(self.dim_patient) + len(self.dim_appointment) + len(self.dim_doctor) + len(self.fact_treatment)
        pd.DataFrame([self.metrics]).to_csv(REPORT_DIR / "etl_audit_log.csv", index=False)
        logging.info("Load step completed. Rows ready for Snowflake: %s", self.metrics["rows_loaded"])

    def run(self, use_s3: bool = False):
        if use_s3:
            self.upload_bronze_to_s3()
        self.extract()
        self.validate()
        self.transform()
        self.enrich()
        self.save_silver_locally()
        if use_s3:
            self.upload_silver_to_s3()
        self.load()
        return self.metrics


if __name__ == "__main__":
    raw = BASE_DIR / "data" / "raw"
    etl = HealthcareETL(raw / "patients.csv", raw / "appointments.csv", raw / "treatments.csv")
    print(etl.run(use_s3=False))
