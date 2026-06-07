-- No orphan treatments
SELECT COUNT(*) AS orphan_treatments
FROM fact_treatment t
LEFT JOIN dim_appointment a ON t.appointment_id = a.appointment_id
WHERE a.appointment_id IS NULL;

-- No duplicate appointment IDs
SELECT appointment_id, COUNT(*) AS duplicate_count
FROM dim_appointment
GROUP BY appointment_id
HAVING COUNT(*) > 1;

-- Valid appointment durations
SELECT COUNT(*) AS invalid_duration_count
FROM dim_appointment
WHERE visit_duration_minutes <= 0 OR visit_duration_minutes IS NULL;
