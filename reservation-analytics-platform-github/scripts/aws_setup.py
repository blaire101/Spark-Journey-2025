from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


ODS_TABLES = {
    "ods_reservation_event": [
        ("reservation_id", "string"),
        ("mid", "string"),
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("reserve_time", "timestamp"),
        ("channel", "string"),
    ],
    "ods_order": [
        ("order_id", "string"),
        ("mid", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("order_time", "timestamp"),
        ("order_status", "string"),
    ],
    "dim_campaign": [
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("launch_start", "timestamp"),
        ("launch_end", "timestamp"),
    ],
}

OUTPUT_TABLES = {
    "dwd_reservation": [
        ("reservation_id", "string"),
        ("mid", "string"),
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("reserve_time", "timestamp"),
        ("channel", "string"),
    ],
    "dwd_paid_order": [
        ("order_id", "string"),
        ("mid", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("order_time", "timestamp"),
    ],
    "fact_reservation_conversion": [
        ("reservation_id", "string"),
        ("mid", "string"),
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("reserve_time", "timestamp"),
        ("channel", "string"),
        ("reserve_flag", "int"),
        ("order_flag", "int"),
        ("tag_reserved_not_paid", "int"),
        ("order_id", "string"),
        ("order_time", "timestamp"),
    ],
    "dm_user_campaign_profile": [
        ("mid", "string"),
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("channel", "string"),
        ("reserve_time", "timestamp"),
        ("order_flag", "int"),
        ("tag_reserved_not_paid", "int"),
        ("conversion_segment", "string"),
    ],
    "ads_campaign_conversion": [
        ("campaign_id", "string"),
        ("site", "string"),
        ("channel", "string"),
        ("reserved_users", "bigint"),
        ("paid_users", "bigint"),
        ("unconverted_users", "bigint"),
        ("conversion_rate", "double"),
    ],
    "crm_reserved_not_paid": [
        ("mid", "string"),
        ("campaign_id", "string"),
        ("product_id", "string"),
        ("site", "string"),
        ("channel", "string"),
        ("reserve_time", "timestamp"),
    ],
}


def ensure_bucket(s3, bucket: str, region: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket exists: {bucket}")
        return
    except ClientError:
        pass

    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket)
    else:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    print(f"Created bucket: {bucket}")


def upload_tree(s3, local_dir: Path, bucket: str, prefix: str) -> None:
    for path in local_dir.rglob("*"):
        if path.is_file():
            key = f"{prefix}/{path.relative_to(local_dir).as_posix()}"
            s3.upload_file(str(path), bucket, key)
            print(f"Uploaded s3://{bucket}/{key}")


def ensure_database(glue, name: str) -> None:
    try:
        glue.get_database(Name=name)
    except glue.exceptions.EntityNotFoundException:
        glue.create_database(DatabaseInput={"Name": name})
        print(f"Created Glue database: {name}")


def parquet_table_input(name: str, columns: list[tuple[str, str]], location: str) -> dict:
    return {
        "Name": name,
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {
            "classification": "parquet",
            "EXTERNAL": "TRUE",
        },
        "StorageDescriptor": {
            "Columns": [{"Name": n, "Type": t} for n, t in columns],
            "Location": location,
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                "Parameters": {"serialization.format": "1"},
            },
        },
    }


def upsert_table(glue, database: str, table_input: dict) -> None:
    name = table_input["Name"]
    try:
        glue.get_table(DatabaseName=database, Name=name)
        glue.update_table(DatabaseName=database, TableInput=table_input)
        print(f"Updated table: {database}.{name}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_table(DatabaseName=database, TableInput=table_input)
        print(f"Created table: {database}.{name}")


def ensure_role(iam, role_name: str, bucket: str) -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "glue.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="Demo role for reservation analytics Glue job",
        )["Role"]
        print(f"Created IAM role: {role_name}")

    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
    )

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "glue:GetDatabase", "glue:GetDatabases",
                    "glue:GetTable", "glue:GetTables",
                    "glue:GetPartition", "glue:GetPartitions",
                ],
                "Resource": "*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="ReservationDemoDataAccess",
        PolicyDocument=json.dumps(policy),
    )
    return role["Arn"]


def create_or_update_job(glue, job_name: str, role_arn: str, bucket: str) -> None:
    spec = {
        "Role": role_arn,
        "Command": {
            "Name": "glueetl",
            "ScriptLocation": f"s3://{bucket}/code/glue_jobs/run_glue_sql_job.py",
            "PythonVersion": "3",
        },
        "DefaultArguments": {
            "--SOURCE_DATABASE": "reservation_ods",
            "--OUTPUT_BASE_PATH": f"s3://{bucket}/curated",
            "--CODE_BASE_PATH": f"s3://{bucket}/code",
            "--enable-metrics": "true",
            "--enable-observability-metrics": "true",
            "--job-language": "python",
        },
        "GlueVersion": "5.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 2,
        "Timeout": 15,
        "MaxRetries": 0,
    }
    try:
        glue.get_job(JobName=job_name)
        glue.update_job(JobName=job_name, JobUpdate=spec)
        print(f"Updated Glue job: {job_name}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_job(Name=job_name, **spec)
        print(f"Created Glue job: {job_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    sts = session.client("sts")
    account = sts.get_caller_identity()["Account"]
    region = session.region_name
    bucket = f"reservation-demo-{account}-{region}"
    role_name = "reservation-demo-glue-role"
    job_name = "reservation-analytics-demo"

    s3 = session.client("s3")
    glue = session.client("glue")
    iam = session.client("iam")

    ensure_bucket(s3, bucket, region)

    mock_dir = Path("aws/mock_ods")
    if not mock_dir.exists():
        raise SystemExit("Run: python scripts/generate_mock_ods.py")

    upload_tree(s3, mock_dir, bucket, "ods")
    upload_tree(s3, Path("sql"), bucket, "code/sql")
    upload_tree(s3, Path("config"), bucket, "code/config")
    upload_tree(s3, Path("glue_jobs"), bucket, "code/glue_jobs")

    ensure_database(glue, "reservation_ods")
    ensure_database(glue, "reservation_curated")

    for name, columns in ODS_TABLES.items():
        upsert_table(
            glue,
            "reservation_ods",
            parquet_table_input(
                name,
                columns,
                f"s3://{bucket}/ods/{name}/",
            ),
        )

    for name, columns in OUTPUT_TABLES.items():
        upsert_table(
            glue,
            "reservation_curated",
            parquet_table_input(
                name,
                columns,
                f"s3://{bucket}/curated/{name}/",
            ),
        )

    role_arn = ensure_role(iam, role_name, bucket)
    print("Waiting briefly for IAM role propagation...")
    time.sleep(10)
    create_or_update_job(glue, job_name, role_arn, bucket)

    state = {
        "region": region,
        "account": account,
        "bucket": bucket,
        "role_name": role_name,
        "job_name": job_name,
        "source_database": "reservation_ods",
        "output_database": "reservation_curated",
    }
    Path("aws_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    print("\nAWS setup complete.")
    print(json.dumps(state, indent=2))
    print("\nNext command:")
    print("python scripts/aws_run.py")


if __name__ == "__main__":
    main()
