import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime, timedelta
from pathlib import Path

fake = Faker()
np.random.seed(42)
random.seed(42)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

patients = []
for i in range(1, 1101):
    patients.append({
        "patient_id": i if random.random() > 0.03 else random.randint(1, 50),
        "patient_name": fake.name() if random.random() > 0.05 else None,
        "dob": fake.date_of_birth(minimum_age=0, maximum_age=100) if random.random() > 0.05 else "invalid_date",
        "gender": random.choice(["M", "F", None, " male ", "female"])
    })
pd.DataFrame(patients).to_csv(OUT_DIR / "patients.csv", index=False)

appointments = []
for i in range(1, 5501):
    patient_id = random.randint(1, 1200)
    start_time = datetime.now() - timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))
    end_time = start_time + timedelta(minutes=random.randint(15, 120))
    if random.random() < 0.05:
        end_time = "invalid_timestamp"
    appointments.append({
        "appointment_id": i if random.random() > 0.03 else random.randint(1, 200),
        "patient_id": patient_id if random.random() > 0.05 else None,
        "doctor_id": random.randint(1, 100),
        "start_time": start_time,
        "end_time": end_time
    })
pd.DataFrame(appointments).to_csv(OUT_DIR / "appointments.csv", index=False)

treatment_types = ["Consultation", "Surgery", "Therapy", "Medication", "Diagnostics"]
treatments = []
for i in range(1, 7501):
    treatments.append({
        "treatment_id": i if random.random() > 0.03 else random.randint(1, 200),
        "appointment_id": random.randint(1, 5600),
        "treatment_type": random.choice(treatment_types),
        "duration_minutes": random.randint(5, 180) if random.random() > 0.05 else None,
        "cost": round(random.uniform(50, 5000), 2) if random.random() > 0.05 else None
    })
pd.DataFrame(treatments).to_csv(OUT_DIR / "treatments.csv", index=False)

print(f"Healthcare sample CSV files generated at {OUT_DIR}")
