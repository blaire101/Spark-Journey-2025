# Deployment checklist

## Before running

- [ ] AWS CLI installed
- [ ] `aws sts get-caller-identity` succeeds
- [ ] correct AWS region selected
- [ ] IAM permission to create S3, Glue and IAM demo resources
- [ ] Python virtual environment activated
- [ ] local test passes

## Local success criteria

- [ ] `pytest -q` returns `1 passed`
- [ ] `output/dm_reservation_conversion.csv` exists
- [ ] U001 is converted
- [ ] U002 and U003 are in CRM audience

## AWS success criteria

- [ ] S3 bucket contains `ods/`, `code/`, `curated/`
- [ ] Glue databases `reservation_ods` and `reservation_curated` exist
- [ ] Glue job status is `SUCCEEDED`
- [ ] Athena returns three DM rows
- [ ] CRM table returns U002 and U003
- [ ] optional daily trigger is enabled

## After learning

- [ ] run cleanup script
- [ ] confirm Glue job and trigger are deleted
- [ ] confirm S3 bucket is deleted if requested
