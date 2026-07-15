# AWS services

| Service | Role in this project | What to inspect |
|---|---|---|
| S3 | ODS, code and curated output | folder paths and Parquet files |
| Glue Catalog | table schemas and S3 locations | databases and table definitions |
| Glue Job | executes Spark SQL | job arguments, runs, duration |
| CloudWatch | job logs and failures | driver log and error message |
| Athena | validates curated output | counts, samples and metrics |
| Glue Trigger | daily schedule | cron and enabled state |

The Console is mainly for monitoring and validation. SQL development remains in the repository.
