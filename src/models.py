from dataclasses import dataclass
from datetime import datetime, date

@dataclass
class Patient:
    patient_id: int
    name: str
    dob: date
    gender: str

@dataclass
class Appointment:
    appointment_id: int
    patient_id: int
    start_time: datetime
    end_time: datetime
    doctor_id: int
