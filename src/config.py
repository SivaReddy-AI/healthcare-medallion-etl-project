import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket: str = os.getenv("S3_BUCKET", "your-healthcare-etl-bucket")
    bronze_prefix: str = os.getenv("BRONZE_PREFIX", "bronze/healthcare")
    silver_prefix: str = os.getenv("SILVER_PREFIX", "silver/healthcare")

    snowflake_account: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    snowflake_user: str = os.getenv("SNOWFLAKE_USER", "")
    snowflake_password: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    snowflake_role: str = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    snowflake_warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE", "HEALTHCARE_DW")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA", "GOLD")
