-- 1. Most common treatments
SELECT treatment_type, COUNT(*) AS treatment_count
FROM fact_treatment
GROUP BY treatment_type
ORDER BY treatment_count DESC;

-- 2. Average visits per patient
SELECT AVG(visit_count) AS average_visits_per_patient
FROM (
    SELECT patient_id, COUNT(*) AS visit_count
    FROM dim_appointment
    GROUP BY patient_id
);

-- 3. Monthly appointment trends
SELECT appointment_month, COUNT(*) AS total_appointments
FROM dim_appointment
GROUP BY appointment_month
ORDER BY appointment_month;

-- 4. Total cost per patient
SELECT p.patient_id, p.patient_name, SUM(a.total_treatment_cost) AS total_cost
FROM dim_patient p
JOIN dim_appointment a ON p.patient_id = a.patient_id
GROUP BY p.patient_id, p.patient_name
ORDER BY total_cost DESC;

-- 5. Average treatment duration by type
SELECT treatment_type, AVG(duration_minutes) AS avg_duration_minutes
FROM fact_treatment
GROUP BY treatment_type
ORDER BY avg_duration_minutes DESC;

-- 6. Patients with overlapping appointments
SELECT p.patient_id, p.patient_name, a.appointment_id, a.start_time, a.end_time
FROM dim_patient p
JOIN dim_appointment a ON p.patient_id = a.patient_id
WHERE a.has_overlap = TRUE;

-- 7. Patients with frequent visits greater than 3 per month
SELECT patient_id, appointment_month, COUNT(*) AS monthly_visits
FROM dim_appointment
GROUP BY patient_id, appointment_month
HAVING COUNT(*) > 3
ORDER BY monthly_visits DESC;

-- 8. Treatments per doctor
SELECT d.doctor_id, d.doctor_name, COUNT(t.treatment_id) AS total_treatments
FROM dim_doctor d
JOIN dim_appointment a ON d.doctor_id = a.doctor_id
JOIN fact_treatment t ON a.appointment_id = t.appointment_id
GROUP BY d.doctor_id, d.doctor_name
ORDER BY total_treatments DESC;

-- 9. Treatment cost outliers top 1%
SELECT *
FROM fact_treatment
WHERE cost >= (SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY cost) FROM fact_treatment)
ORDER BY cost DESC;

-- 10. Cohort analysis: patients by signup month vs treatment frequency
SELECT p.signup_month, COUNT(DISTINCT p.patient_id) AS patient_count, COUNT(t.treatment_id) AS treatment_count,
       COUNT(t.treatment_id) / NULLIF(COUNT(DISTINCT p.patient_id), 0) AS treatments_per_patient
FROM dim_patient p
LEFT JOIN dim_appointment a ON p.patient_id = a.patient_id
LEFT JOIN fact_treatment t ON a.appointment_id = t.appointment_id
GROUP BY p.signup_month
ORDER BY p.signup_month;
