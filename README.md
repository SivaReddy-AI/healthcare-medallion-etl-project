# Healthcare Medallion ETL Pipeline

## Project Overview

This project implements an end-to-end healthcare ETL pipeline using a medallion architecture.
Raw patient, appointment, and treatment CSV files are stored in AWS S3 as the Bronze layer. Python and Pandas are used to clean, validate, transform, and enrich the data. Cleaned datasets are written to the Silver layer in AWS S3. Snowflake is used as the Gold layer for dimensional modeling, business aggregations, and analytical reporting.

The project is based on the capstone requirement to normalize healthcare data into fact and dimension tables, detect missing or invalid data, compute visit metrics, and enable SQL analytics on treatments and appointments.

## Architecture Flow

```text
patients.csv
appointments.csv
treatments.csv
        |
        v
AWS S3 Bronze Layer
Raw Data Storage
        |
        v
Python + Pandas
Data Cleaning, Validation, Transformation
        |
        v
AWS S3 Silver Layer
Cleaned Data Storage
        |
        v
Snowflake Gold Layer
Fact Tables, Dimension Tables, Analytics Queries
```

## Folder Structure

```text
healthcare_medallion_etl_project/
├── data/
│   ├── raw/
│   └── silver/
├── docs/
│   └── star_schema.txt
├── logs/
├── reports/
├── sql/
│   ├── 01_snowflake_setup.sql
│   ├── 02_ddl_gold_tables.sql
│   ├── 03_copy_into_snowflake.sql
│   ├── 04_analytics_queries.sql
│   └── 05_data_quality_checks.sql
├── src/
│   ├── config.py
│   ├── generate_sample_data.py
│   ├── healthcare_etl.py
│   └── models.py
├── tests/
│   └── test_healthcare_etl.py
├── .env.example
└── requirements.txt
```

## ETL Layers

### Bronze Layer

The Bronze layer stores raw CSV files in AWS S3 without changing the original data.

Example S3 paths:

```text
s3://your-healthcare-etl-bucket/bronze/healthcare/patients.csv
s3://your-healthcare-etl-bucket/bronze/healthcare/appointments.csv
s3://your-healthcare-etl-bucket/bronze/healthcare/treatments.csv
```

### Silver Layer

The Silver layer contains cleaned and validated data created by Python.

Main transformations include:

- Schema validation
- Missing value handling
- Duplicate removal
- Invalid date handling
- Patient name standardization
- Visit duration calculation
- Orphan appointment detection
- Orphan treatment detection
- Treatment cost aggregation
- High-cost treatment outlier flagging
- Frequent visitor flagging
- Overlapping appointment detection

Output files:

```text
dim_patient.csv
dim_appointment.csv
dim_doctor.csv
fact_treatment.csv
```

### Gold Layer

The Gold layer is built in Snowflake using dimensional modeling.

Tables:

- `dim_patient`
- `dim_doctor`
- `dim_appointment`
- `fact_treatment`
- `etl_audit_log`

These tables support healthcare reporting and business intelligence queries.

## How to Run Locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate sample raw CSV files

```bash
python src/generate_sample_data.py
```

### 3. Run the ETL pipeline locally

```bash
python src/healthcare_etl.py
```

This creates cleaned Silver files under:

```text
data/silver/
```

It also creates audit and quality reports under:

```text
reports/
```

### 4. Run unit tests

```bash
pytest tests
```

## How to Use AWS S3

Update `.env` with your bucket name:

```text
S3_BUCKET=your-healthcare-etl-bucket
BRONZE_PREFIX=bronze/healthcare
SILVER_PREFIX=silver/healthcare
```

Then run:

```python
etl.run(use_s3=True)
```

This uploads raw files to Bronze and cleaned files to Silver.

## How to Use Snowflake

Run these SQL scripts in order:

```text
sql/01_snowflake_setup.sql
sql/02_ddl_gold_tables.sql
sql/03_copy_into_snowflake.sql
sql/04_analytics_queries.sql
sql/05_data_quality_checks.sql
```

Before running, update the Snowflake external stage bucket path in `01_snowflake_setup.sql`.

## Business Analytics Supported

The Gold layer supports these analytical queries:

1. Most common treatments
2. Average visits per patient
3. Monthly appointment trends
4. Total treatment cost per patient
5. Average treatment duration by type
6. Patients with overlapping appointments
7. Patients with frequent visits
8. Treatments per doctor
9. Treatment cost outliers
10. Cohort analysis by patient signup month

## Data Quality Reports

The pipeline creates reports for:

- Missing values
- Duplicate rows
- Invalid dates
- Orphan appointments
- Orphan treatments
- Rows extracted, transformed, and loaded
- Duplicate records removed

## Assumptions

- CSV files are the source system for this project.
- AWS S3 is used for Bronze and Silver storage.
- Snowflake is used as the Gold analytics warehouse.
- Patient IDs, appointment IDs, and treatment IDs are business keys.
- Invalid dates and invalid durations are removed from the clean dataset.
- Treatments without valid appointments are excluded from the final fact table.
