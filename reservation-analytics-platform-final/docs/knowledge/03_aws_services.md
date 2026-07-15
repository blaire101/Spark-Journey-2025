# AWS Services Used

| Service | Responsibility |
|---|---|
| Amazon S3 | Stores mock ODS Parquet, SQL artifacts, Glue scripts and curated outputs |
| AWS Glue Data Catalog | Registers ODS, DWD, DM and ADS table metadata |
| AWS Glue ETL | Runs the PySpark wrapper and shared Spark SQL |
| Amazon CloudWatch | Stores Glue logs and metrics |
| Amazon Athena | Validates the curated output |
| IAM | Grants least-privilege access to Glue, S3 and Catalog resources |
| Glue Trigger | Runs the job on a schedule |

## Where code is written

The repository is the source of truth. SQL and the small Glue wrapper are normally developed in an IDE, reviewed in Git, tested, and deployed by automation. Glue Studio remains useful for interactive exploration, job configuration, logs, and troubleshooting, but production code should not depend on unreviewed console-only edits.
