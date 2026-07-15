# Reliability and Cost

## Reliability

- Keep code in Git and require pull-request review.
- Test SQL locally with deterministic mock ODS data.
- Separate dev, test and production parameters.
- Make job outputs idempotent for the target processing date.
- Add row-count, uniqueness, null and business-rule checks.
- Monitor Glue job status and CloudWatch logs.
- Avoid editing production code only in the console.

## Cost

- This demo uses small Parquet files and two `G.1X` workers.
- Glue startup time usually dominates this tiny workload.
- Athena scans little data because outputs are Parquet.
- Delete the trigger and demo resources after practice.
