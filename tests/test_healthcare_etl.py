import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_etl import calculate_visit_duration, aggregate_treatment_costs, drop_duplicates


def test_visit_duration_computation():
    start = pd.Series(pd.to_datetime(["2025-01-01 10:00:00"]))
    end = pd.Series(pd.to_datetime(["2025-01-01 11:30:00"]))
    result = calculate_visit_duration(start, end)
    assert result.iloc[0] == 90


def test_treatment_cost_aggregation():
    df = pd.DataFrame({
        "appointment_id": [1, 1, 2],
        "treatment_id": [101, 102, 103],
        "cost": [100.0, 200.0, 300.0],
        "duration_minutes": [10, 20, 30]
    })
    result = aggregate_treatment_costs(df)
    appt_1 = result[result["appointment_id"] == 1].iloc[0]
    assert appt_1["total_treatment_cost"] == 300.0
    assert appt_1["treatment_count"] == 2


def test_patient_duplicates_detection():
    df = pd.DataFrame({"patient_id": [1, 1, 2], "patient_name": ["John", "John", "Mary"]})
    cleaned, removed = drop_duplicates(df, ["patient_id"])
    assert removed == 1
    assert len(cleaned) == 2
