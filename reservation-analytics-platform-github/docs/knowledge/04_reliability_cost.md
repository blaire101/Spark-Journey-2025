# Reliability and cost

## Reliability
- validate source readiness;
- test duplicate keys and flags;
- make the job rerunnable;
- monitor runtime and SLA;
- alert on failure;
- separate test and production output paths.

## Cost
- use Parquet columnar files;
- read only required columns and partitions;
- keep Glue workers and timeout small for the demo;
- delete the demo resources after use;
- avoid adding always-on services when they are not needed.
