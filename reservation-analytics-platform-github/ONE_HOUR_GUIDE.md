# One-Hour Run Guide

This guide takes you from zero to:

```text
Local Mock ODS
→ local SQL ETL
→ S3 Parquet ODS
→ Glue Catalog
→ AWS Glue Spark SQL job
→ curated Parquet
→ Athena validation
```

The ingestion process is intentionally excluded. The demo creates three mock ODS tables.

---

## What you need before starting

On your Mac:

```bash
python3 --version
aws --version
```

Recommended:

- Python 3.11 or newer
- AWS CLI v2
- an AWS account
- permissions to create S3, Glue, IAM roles and run Athena
- region: `ap-southeast-1`

Configure AWS:

```bash
aws configure
aws sts get-caller-identity
```

Do not continue until `get-caller-identity` returns your AWS account.

---

# Minute 0–10: Local environment

Unzip and enter the project:

```bash
unzip reservation-analytics-one-hour.zip
cd reservation-analytics-one-hour
```

Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the local ETL:

```bash
python -m src.run_local
pytest -q
```

Expected:

```text
U001 → converted
U002 → reserved but not paid
U003 → reserved but not paid
1 passed
```

What happened locally:

```text
sql/local/00_mock_ods.sql
    creates:
        ods_reservation_event
        ods_order
        dim_campaign

sql/shared/*.sql
    creates:
        dwd_reservation
        dwd_paid_order
        fact_reservation_conversion
        ads_campaign_conversion
        crm_reserved_not_paid
```

---

# Minute 10–15: Generate AWS Mock ODS

Create Parquet files from the mock ODS:

```bash
python scripts/generate_mock_ods.py
```

Generated:

```text
aws/mock_ods/
├── ods_reservation_event/part-00000.parquet
├── ods_order/part-00000.parquet
└── dim_campaign/part-00000.parquet
```

These Parquet files simulate ODS tables already produced by an upstream ingestion system.

---

# Minute 15–30: Create AWS resources automatically

Run:

```bash
python scripts/aws_setup.py --region ap-southeast-1
```

The script creates:

```text
S3 bucket
├── ods/                         mock ODS Parquet
├── code/sql/, config/, and glue_jobs/             shared SQL
└── code/glue_jobs/              Glue Python runner

Glue databases
├── reservation_ods
└── reservation_curated

Glue ODS tables
├── reservation_ods.ods_reservation_event
├── reservation_ods.ods_order
└── reservation_ods.dim_campaign

Glue output tables
├── reservation_curated.fact_reservation_conversion
├── reservation_curated.ads_campaign_conversion
└── reservation_curated.crm_reserved_not_paid

IAM role
└── reservation-demo-glue-role

Glue job
└── reservation-analytics-demo
```

It writes the resource names to:

```text
aws_state.json
```

### Where to see these in the AWS Console

1. **S3**
   - Search for the bucket starting with `reservation-demo-`.
   - Open `ods/`, `code/`, and later `curated/`.

2. **AWS Glue**
   - Data Catalog → Databases → `reservation_ods`
   - Data Catalog → Tables
   - ETL jobs → `reservation-analytics-demo`

3. **IAM**
   - Roles → `reservation-demo-glue-role`

---

# Minute 30–45: Run the AWS Glue ETL

Run:

```bash
python scripts/aws_run.py
```

The script starts the Glue job and polls until it finishes.

The Glue job:

```text
reads Glue Catalog ODS tables
→ executes the same SQL files used conceptually locally
→ writes curated Parquet to S3
```

Console path:

```text
AWS Glue
→ ETL jobs
→ reservation-analytics-demo
→ Runs
```

If it fails:

```text
Glue Job Run
→ Logs
→ CloudWatch
```

---

# Minute 45–55: Validate with Athena

Automated:

```bash
python scripts/aws_validate.py
```

Or open the Athena console and run:

```text
sql/athena_validation.sql
```

Expected fact result:

| mid | order_flag | tag_reserved_not_paid | order_id |
|---|---:|---:|---|
| U001 | 1 | 0 | O001 |
| U002 | 0 | 1 | null |
| U003 | 0 | 1 | null |

Expected CRM result:

```text
U002
U003
```

Athena uses the AWS Glue Data Catalog metadata to expose the tables.

---

# Minute 55–60: Add a daily schedule

Create a daily Glue Trigger:

```bash
python scripts/aws_schedule.py
```

Default:

```text
02:00 UTC every day
```

Singapore time:

```text
10:00 SGT
```

For another cron expression:

```bash
python scripts/aws_schedule.py \
  --cron "cron(0 1 * * ? *)"
```

This would run at 01:00 UTC / 09:00 SGT.

Console:

```text
AWS Glue
→ Data Integration and ETL
→ Triggers
→ reservation-analytics-daily-trigger
```

---

# Daily working pattern after deployment

You do not rebuild the job every day.

```text
Scheduled Glue Trigger
→ Glue job runs automatically
→ check Job Run status
→ check CloudWatch on failure
→ query Athena for validation
→ modify SQL in PyCharm for new requirements
→ local test
→ Git / Code Review
→ upload/deploy SQL through CI/CD
```

Typical AWS console usage:

| AWS page | Why you use it |
|---|---|
| Glue Job Runs | Check success, duration and retries |
| CloudWatch Logs | Diagnose SQL/Spark failures |
| S3 | Confirm ODS and curated files |
| Glue Catalog | Confirm schemas and locations |
| Athena | Validate business data |
| Glue Triggers | Confirm schedule |

---

# Understand the three users

## U001

```text
Reserved: 28 June
Campaign: 1–7 July
Paid: 2 July
Result: converted
```

## U002

```text
Reserved: 29 June
Campaign: 1–7 July
Paid: 8 July
Result: not converted because payment was after the window
```

## U003

```text
Reserved: 30 June
Order: cancelled
Result: not converted
```

---

# Core SQL to explain in the interview

## 1. Deduplication

```sql
ROW_NUMBER() OVER (
    PARTITION BY mid, campaign_id, product_id, site
    ORDER BY reserve_time
)
```

## 2. Valid paid orders

```sql
WHERE order_status = 'PAID'
```

## 3. Non-equi campaign-window join

```sql
AND o.order_time BETWEEN c.launch_start AND c.launch_end
```

## 4. CRM audience

```sql
CASE WHEN order_id IS NULL THEN 1 ELSE 0 END
    AS tag_reserved_not_paid
```

---

# Clean up immediately after learning

Delete Glue, Catalog and IAM resources but retain S3:

```bash
python scripts/aws_cleanup.py
```

Delete everything, including the S3 bucket:

```bash
python scripts/aws_cleanup.py --delete-bucket
```

This is important because Glue job runs and stored resources can generate charges.

---

# Troubleshooting

## `AccessDenied`

Your AWS identity lacks IAM, S3 or Glue creation permissions.

Check:

```bash
aws sts get-caller-identity
```

Use a permitted development account or ask an administrator for a sandbox role.

## Glue job cannot assume role

Wait 30–60 seconds and rerun:

```bash
python scripts/aws_run.py
```

IAM role propagation can take a short time.

## Athena says table has no data

Check:

```text
S3 bucket → curated/<table>/
```

Then confirm the Glue table `Location` points to that folder.

## Region mismatch

Use the same region for:

- AWS CLI
- S3 bucket
- Glue databases/job
- Athena

This package defaults to:

```text
ap-southeast-1
```
