# Extending the project

## Add a new DM table

Example requirement: create a daily user-channel profile.

### Step 1: add SQL

Create:

```text
sql/dm/36_dm_user_channel_profile.sql
```

The SQL must create a view whose name is the output table name:

```sql
CREATE OR REPLACE TEMP VIEW dm_user_channel_profile AS
SELECT
    mid,
    channel,
    COUNT(DISTINCT campaign_id) AS reserved_campaigns,
    MAX(reserve_time) AS latest_reserve_time
FROM fact_reservation_conversion
GROUP BY mid, channel;
```

### Step 2: update one manifest

Edit `config/pipeline.json`:

```json
{
  "sql_files": [
    "...",
    "sql/dm/36_dm_user_channel_profile.sql"
  ],
  "output_tables": [
    "...",
    "dm_user_channel_profile"
  ]
}
```

### Step 3: test locally

```bash
python -m src.run_local
```

The runner creates:

```text
output/dm_user_channel_profile.csv
```

### Step 4: add AWS Catalog schema

Add the new output table columns to `OUTPUT_TABLES` in:

```text
scripts/aws_setup.py
```

Run setup again to create/update the Glue Catalog table, upload code, and update the job:

```bash
python scripts/aws_setup.py --region ap-southeast-1
```

### Step 5: run and validate

```bash
python scripts/aws_run.py
```

Then query it in Athena.

## What normally changes

| Change | Files to modify | Usually unchanged |
|---|---|---|
| New DM/ADS table | new SQL, `pipeline.json`, AWS output schema | local runner, Glue runner |
| Change business logic | relevant SQL and tests | deployment scripts |
| New source ODS table | local mock SQL, Glue source view mapping | existing outputs |
| New schedule | `aws_schedule.py` command | SQL |
