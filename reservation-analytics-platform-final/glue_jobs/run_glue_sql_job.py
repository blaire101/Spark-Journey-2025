"""Minimal SQL-first AWS Glue runner.

Expected Glue Catalog tables:
  <SOURCE_DATABASE>.ods_reservation_event
  <SOURCE_DATABASE>.ods_order
  <SOURCE_DATABASE>.dim_campaign

Required arguments:
  --JOB_NAME
  --SOURCE_DATABASE
  --OUTPUT_BASE_PATH
  --CODE_BASE_PATH
"""
from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

import boto3
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext


def read_s3_text(uri: str) -> str:
    parsed = urlparse(uri)
    obj = boto3.client("s3").get_object(
        Bucket=parsed.netloc,
        Key=parsed.path.lstrip("/"),
    )
    return obj["Body"].read().decode("utf-8")


args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "SOURCE_DATABASE", "OUTPUT_BASE_PATH", "CODE_BASE_PATH"],
)

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

source_database = args["SOURCE_DATABASE"]
output_base = args["OUTPUT_BASE_PATH"].rstrip("/")
code_base = args["CODE_BASE_PATH"].rstrip("/")

spark.table(f"{source_database}.ods_reservation_event").createOrReplaceTempView(
    "ods_reservation_event"
)
spark.table(f"{source_database}.ods_order").createOrReplaceTempView("ods_order")
spark.table(f"{source_database}.dim_campaign").createOrReplaceTempView("dim_campaign")

config = json.loads(read_s3_text(f"{code_base}/config/pipeline.json"))

for sql_path in config["sql_files"]:
    spark.sql(read_s3_text(f"{code_base}/{sql_path}"))

for table in config["output_tables"]:
    (
        spark.table(table)
        .write
        .mode("overwrite")
        .parquet(f"{output_base}/{table}")
    )

job.commit()
