USE DATABASE HEALTHCARE_DW;
USE SCHEMA GOLD;

CREATE OR REPLACE TABLE dim_patient (
    patient_id NUMBER PRIMARY KEY,
    patient_name VARCHAR NOT NULL,
    dob DATE,
    gender VARCHAR,
    is_frequent_visitor BOOLEAN,
    signup_month VARCHAR
);

CREATE OR REPLACE TABLE dim_doctor (
    doctor_id NUMBER PRIMARY KEY,
    doctor_name VARCHAR
);

CREATE OR REPLACE TABLE dim_appointment (
    appointment_id NUMBER PRIMARY KEY,
    patient_id NUMBER NOT NULL,
    doctor_id NUMBER NOT NULL,
    start_time TIMESTAMP_NTZ NOT NULL,
    end_time TIMESTAMP_NTZ NOT NULL,
    visit_duration_minutes NUMBER(10,2),
    total_treatment_cost NUMBER(12,2),
    avg_treatment_cost NUMBER(12,2),
    treatment_count NUMBER,
    total_treatment_duration NUMBER(10,2),
    appointment_month VARCHAR,
    has_overlap BOOLEAN,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES dim_doctor(doctor_id)
);

CREATE OR REPLACE TABLE fact_treatment (
    treatment_id NUMBER PRIMARY KEY,
    appointment_id NUMBER NOT NULL,
    treatment_type VARCHAR,
    duration_minutes NUMBER(10,2),
    cost NUMBER(12,2),
    is_high_cost_outlier BOOLEAN,
    load_timestamp TIMESTAMP_NTZ,
    FOREIGN KEY (appointment_id) REFERENCES dim_appointment(appointment_id)
);

CREATE OR REPLACE TABLE etl_audit_log (
    audit_id NUMBER AUTOINCREMENT PRIMARY KEY,
    rows_extracted NUMBER,
    rows_transformed NUMBER,
    rows_loaded NUMBER,
    invalid_records NUMBER,
    duplicates_removed NUMBER,
    orphan_appointments NUMBER,
    orphan_treatments NUMBER,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
);
