# AWS Console Guide

## S3

```text
S3 → Buckets → reservation-demo-<account>-<region>
```

Important folders:

```text
ods/       input mock ODS
code/      SQL and Glue runner
curated/   ETL output
athena-results/
```

## Glue Catalog

```text
AWS Glue → Data Catalog → Databases
```

Databases:

```text
reservation_ods
reservation_curated
```

Open a table and inspect:

- columns;
- S3 location;
- input format: Parquet.

## Glue Job

```text
AWS Glue → ETL jobs → reservation-analytics-demo
```

Important tabs:

- Script: the small Python SQL runner;
- Job details: Glue 5.0, G.1X, two workers;
- Runs: status and duration;
- Logs: CloudWatch driver logs.

## Athena

```text
Athena → Query editor
```

Select:

```text
AwsDataCatalog
reservation_curated
```

Run the queries in:

```text
sql/athena_validation.sql
```

## Schedule

```text
AWS Glue → Triggers
```

Trigger:

```text
reservation-analytics-daily-trigger
```
