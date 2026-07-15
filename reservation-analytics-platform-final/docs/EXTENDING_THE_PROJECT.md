# Extending the Project

## Add a new DM table

Example: `dm_user_channel_profile`.

### 1. Add SQL

Create:

```text
sql/dm/31_dm_user_channel_profile.sql
```

```sql
CREATE OR REPLACE TEMP VIEW dm_user_channel_profile AS
SELECT
    mid,
    channel,
    COUNT(DISTINCT campaign_id) AS campaign_count,
    MAX(reserve_time) AS latest_reserve_time
FROM dm_reservation_conversion
GROUP BY mid, channel;
```

### 2. Register execution and output

Add the SQL path and output table to `config/pipeline.json`.

### 3. Add its Glue Catalog schema

Add the table columns to `OUTPUT_TABLES` in `scripts/aws_setup.py`.

### 4. Add a test

Add expected row counts or key business cases to `tests/test_pipeline.py`.

### 5. Deploy

For this learning repository:

```bash
python scripts/aws_setup.py --region ap-southeast-1
python scripts/aws_run.py
python scripts/aws_validate.py
```

In a team environment, the same change should normally go through a pull request and CI/CD pipeline rather than being deployed directly from a developer laptop.
