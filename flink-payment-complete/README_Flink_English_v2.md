# Flink Data Engineering Design: Two End-to-End Cases

This guide explains two production-oriented Flink solutions from **architecture first** to **implementation details**.

- **Case 1 — First-Payment Detection:** identify a user's first study-abroad payment and trigger a coupon.
- **Case 2 — Hourly Payment Dashboard:** calculate hourly metrics, backfill history, and reconcile T-1 data.

The structure follows this order:

```text
Business Goal
→ System Architecture
→ Job Flow
→ Flink Tables
→ Core SQL
→ Reliability and Operations
```

---

## Table of Contents

- [1. Shared Foundations](#1-shared-foundations)
  - [1.1 Naming Conventions](#11-naming-conventions)
  - [1.2 Event Time, Processing Time, and Watermarks](#12-event-time-processing-time-and-watermarks)
  - [1.3 Connector Roles](#13-connector-roles)
  - [1.4 Delivery Semantics and Recovery](#14-delivery-semantics-and-recovery)

- [2. Case 1 — First-Payment Detection](#2-case-1--first-payment-detection)
  - [2.1 Business Goal](#21-business-goal)
  - [2.2 Macro Architecture](#22-macro-architecture)
  - [2.3 Job Inventory](#23-job-inventory)
  - [2.4 Real-Time Flink Job Flow](#24-real-time-flink-job-flow)
  - [2.5 Kafka Source Table](#25-kafka-source-table)
  - [2.6 HBase Dimension Data](#26-hbase-dimension-data)
  - [2.7 Flink HBase Lookup Table](#27-flink-hbase-lookup-table)
  - [2.8 Coupon-Trigger Sink Table](#28-coupon-trigger-sink-table)
  - [2.9 Core Flink SQL](#29-core-flink-sql)
  - [2.10 Downstream Idempotency](#210-downstream-idempotency)

- [3. Case 2 — Hourly Payment Dashboard](#3-case-2--hourly-payment-dashboard)
  - [3.1 Business Goal](#31-business-goal)
  - [3.2 Macro Architecture](#32-macro-architecture)
  - [3.3 Real-Time Window Job](#33-real-time-window-job)
  - [3.4 Watermark Behaviour](#34-watermark-behaviour)
  - [3.5 Historical Backfill](#35-historical-backfill)
  - [3.6 Daily T-1 Reconciliation](#36-daily-t-1-reconciliation)
  - [3.7 ClickHouse Serving Layer](#37-clickhouse-serving-layer)

- [4. Job Inventory and Deployment](#4-job-inventory-and-deployment)
- [5. Interview Quick Reference](#5-interview-quick-reference)

---

# 1. Shared Foundations

## 1.1 Naming Conventions

| Pattern | Meaning | Example |
|---|---|---|
| `dm_` | Hive data-mart table | `dm_user_first_payment_d` |
| `hbt_dm_` | HBase serving table copied from Hive | `hbt_dm_user_first_payment_d` |
| `ft_src_` | Flink source table | `ft_src_payment_events` |
| `ft_dim_` | Flink lookup or dimension table | `ft_dim_hbase_first_pay` |
| `ft_sink_` | Flink sink table | `ft_sink_coupon_trigger` |
| `_d` | Daily snapshot suffix | `dm_user_first_payment_d` |

> A Flink SQL table is normally a connector definition. It maps Flink SQL to an external system and does not store data by itself.

---

## 1.2 Event Time, Processing Time, and Watermarks

![Event Time, Processing Time, and Watermark](docs/watermark-proctime-explained.svg)

| Concept | Meaning | Typical Use |
|---|---|---|
| Event Time | Business time carried by the event, such as `pay_time` | Window aggregation |
| Processing Time | Flink system time when the record is processed | Temporal lookup join |
| Watermark | Estimated progress of event time | Closing event-time windows |

Example:

```sql
proctime AS PROCTIME(),

WATERMARK FOR pay_time
AS pay_time - INTERVAL '5' SECOND
```

The watermark allows events to arrive up to five seconds out of order:

```text
Watermark = Maximum observed event time - 5 seconds
```

---

## 1.3 Connector Roles

| Connector | Source | Sink | Lookup | Main Use |
|---|:---:|:---:|:---:|---|
| Kafka | ✅ | ✅ | ❌ | Append event streams |
| Upsert Kafka | ✅ | ✅ | ❌ | Keyed changelog streams |
| HBase | ✅ | ✅ | ✅ | Low-latency key lookup |
| JDBC | ✅ | ✅ | ✅ | Relational databases |
| Hive | ✅ | ✅ | ✅ | Batch tables and warehouse integration |
| Filesystem | ✅ | ✅ | ❌ | CSV, Parquet, and ORC |
| ClickHouse | ⚠️ | ⚠️ | ⚠️ | Analytical serving through JDBC or a community connector |

---

## 1.4 Delivery Semantics and Recovery

| Semantic | Behaviour |
|---|---|
| At-most-once | May lose records but does not retry |
| At-least-once | Does not lose records but may produce duplicates |
| Exactly-once | Prevents duplicate effects within the guaranteed boundary |

Flink uses checkpoints for state recovery:

```sql
SET 'execution.checkpointing.interval' = '60 s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';
SET 'state.checkpoints.dir' = 'hdfs:///flink-checkpoints';
```

Recommended planned restart:

```bash
flink stop --savepointPath hdfs:///savepoints/first-pay <job_id>
flink run -s hdfs:///savepoints/first-pay -d first_pay_job.sql
```

External business actions should still be idempotent because the complete end-to-end chain may behave as:

```text
At-least-once delivery
+ downstream idempotency
```

---

# 2. Case 1 — First-Payment Detection

## 2.1 Business Goal

When a user makes a study-abroad payment:

1. keep the earliest payment made by that user today;
2. check whether the user has paid before;
3. trigger a coupon only for a genuine first-time payer.

---

## 2.2 Macro Architecture

![Data Source Flow](docs/data-source-flow.svg)

```text
MySQL Payment Table
        │
        │ CDC: Canal / Debezium
        ▼
Kafka: study_abroad_payment_events
        │
        ▼
Single Flink SQL Job
  ├── Daily first-payment deduplication
  ├── HBase temporal lookup
  └── First-time user filtering
        │
        ▼
Kafka: first_pay_coupon_trigger
        │
        ▼
Coupon Service
  └── Redis SETNX idempotency
```

Historical dimension path:

```text
Hive Authoritative Snapshot
→ Daily Merge Job
→ HBase Bulk Load
→ Flink Lookup Join
```

---

## 2.3 Job Inventory

| Job | Technology | Mode | Purpose |
|---|---|---|---|
| `FirstPayDetectionJob` | Flink SQL | Long-running | Deduplicate, look up HBase, and publish coupon events |
| `HiveFirstPayMergeJob` | Hive/Spark SQL | Daily 02:00 | Maintain the authoritative first-payment snapshot |
| `BulkLoadHBaseJob` | Spark + HBase | Daily 02:30 | Refresh the HBase lookup table |

The real-time flow is kept in **one Flink job** because the deduplication and HBase lookup form one business path and the intermediate result is not reused by other consumers.

---

## 2.4 Real-Time Flink Job Flow

```text
1. Read payment events from Kafka
2. Partition by user_id and business date
3. Keep the earliest payment using ROW_NUMBER()
4. Use processing time to look up HBase
5. Keep rows not found in HBase
6. Write coupon-trigger events to Kafka
```

---

## 2.5 Kafka Source Table

```sql
CREATE TABLE ft_src_payment_events (
    order_id    STRING,
    user_id     STRING,
    pay_time    TIMESTAMP(3),
    pay_amount  DECIMAL(10, 2),

    proctime AS PROCTIME(),

    WATERMARK FOR pay_time
    AS pay_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'study_abroad_payment_events',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'first-pay-job-group',
    'properties.auto.offset.reset' = 'latest',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets'
);
```

Key fields:

| Field | Purpose |
|---|---|
| `pay_time` | Business event time |
| `proctime` | Processing-time attribute for HBase lookup |
| Watermark | Supports event-time logic if needed elsewhere |

---

## 2.6 HBase Dimension Data

### Hive Authoritative Table

```text
dm.dm_user_first_payment_d
```

| user_id | first_pay_time | first_order_id | dt |
|---|---|---|---|
| u_8002 | 2025-11-03 07:20:00 | order_31005 | 2026-07-02 |

The daily batch job keeps the earliest historical payment for each user.

### HBase Serving Table

```text
hbt_dm_user_first_payment_d
```

Recommended row key:

```text
MD5(user_id).substring(0, 2) + "_" + user_id
```

The hash prefix distributes rows across HBase regions and reduces hotspot risk.

### Why HBase

| Hive | HBase |
|---|---|
| Designed for batch scanning | Designed for low-latency key lookup |
| Expensive for per-event lookup | Direct row-key access |
| Authoritative offline dataset | Online serving copy |

---

## 2.7 Flink HBase Lookup Table

This is the Flink SQL mapping for the physical HBase table.

```sql
CREATE TABLE ft_dim_hbase_first_pay (
    rowkey STRING,

    cf ROW<
        first_pay_time STRING,
        first_order_id STRING
    >,

    PRIMARY KEY (rowkey) NOT ENFORCED
) WITH (
    'connector' = 'hbase-2.2',
    'table-name' = 'hbt_dm_user_first_payment_d',
    'zookeeper.quorum' = 'zk1:2181,zk2:2181,zk3:2181',

    'lookup.cache.max-rows' = '500000',
    'lookup.cache.ttl' = '30 min'
);
```

### What this table means

```text
Flink table name:
ft_dim_hbase_first_pay

Physical HBase table:
hbt_dm_user_first_payment_d

Lookup key:
rowkey

Returned columns:
cf.first_pay_time
cf.first_order_id
```

The Flink table does not copy HBase data into Flink permanently. It defines how Flink performs lookup requests against HBase.

---

## 2.8 Coupon-Trigger Sink Table

```sql
CREATE TABLE ft_sink_coupon_trigger (
    user_id  STRING,
    order_id STRING,
    pay_time TIMESTAMP(3),

    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'upsert-kafka',
    'topic' = 'first_pay_coupon_trigger',
    'key.format' = 'json',
    'value.format' = 'json'
);
```

The sink publishes one logical coupon-trigger record per user.

---

## 2.9 Core Flink SQL

### Step 1 — Keep Today's Earliest Payment

```sql
CREATE TEMPORARY VIEW first_payment_of_day AS
SELECT
    user_id,
    order_id,
    pay_time,
    proctime
FROM (
    SELECT
        user_id,
        order_id,
        pay_time,
        proctime,

        ROW_NUMBER() OVER (
            PARTITION BY
                user_id,
                DATE_FORMAT(pay_time, 'yyyy-MM-dd')
            ORDER BY pay_time ASC
        ) AS rn

    FROM ft_src_payment_events
)
WHERE rn = 1;
```

Why include the date?

```text
PARTITION BY user_id only
→ earliest payment across the entire job lifetime

PARTITION BY user_id + date
→ earliest payment for each business day
```

Bound the state:

```sql
SET 'table.exec.state.ttl' = '25 h';
```

### Step 2 — Lookup HBase and Trigger Coupon

```sql
INSERT INTO ft_sink_coupon_trigger
SELECT
    t.user_id,
    t.order_id,
    t.pay_time
FROM first_payment_of_day AS t

LEFT JOIN ft_dim_hbase_first_pay
    FOR SYSTEM_TIME AS OF t.proctime AS h

ON CONCAT(
       md5_prefix(t.user_id),
       '_',
       t.user_id
   ) = h.rowkey

WHERE h.rowkey IS NULL;
```

Interpretation:

| SQL Logic | Meaning |
|---|---|
| `FOR SYSTEM_TIME AS OF t.proctime` | Look up the HBase value visible when Flink processes the event |
| `LEFT JOIN` | Preserve the payment event even when no HBase row exists |
| `h.rowkey IS NULL` | The user has no historical payment record |
| `INSERT INTO` | Publish the genuine first-payment event |

---

## 2.10 Downstream Idempotency

The coupon service should protect the business action:

```text
SETNX coupon:u_7001:activity_2026Q3
```

```text
Key does not exist
→ create key
→ issue coupon

Key already exists
→ skip duplicate request
```

The key should contain both the user identifier and the campaign identifier.

---

# 3. Case 2 — Hourly Payment Dashboard

## 3.1 Business Goal

Provide hourly payment metrics for operations:

- payment count;
- total payment amount.

The design must support:

- real-time hourly windows;
- out-of-order events;
- historical backfill;
- daily T-1 correction;
- BI access through ClickHouse.

---

## 3.2 Macro Architecture

```text
Kafka Payment Events
        │
        ▼
Flink Hourly Window Job
        │
        ▼
ClickHouse Hourly Metrics
        │
        ▼
BI Dashboard

ODS Payment Detail
   ├── One-Time Historical Backfill
   └── Daily T-1 Reconciliation
            │
            ▼
      ClickHouse Correction
```

---

## 3.3 Real-Time Window Job

```sql
CREATE TABLE ft_src_payment_events_stats (
    order_id    STRING,
    user_id     STRING,
    pay_time    TIMESTAMP(3),
    pay_amount  DECIMAL(10, 2),

    WATERMARK FOR pay_time
    AS pay_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'study_abroad_payment_events',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'hourly-stats-job-group',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets',
    'scan.watermark.idle-timeout' = '1 min'
);
```

```sql
INSERT INTO ft_sink_pay_hourly_stats
SELECT
    window_start,
    window_end,
    COUNT(*) AS pay_count,
    SUM(pay_amount) AS pay_amount
FROM TABLE(
    TUMBLE(
        TABLE ft_src_payment_events_stats,
        DESCRIPTOR(pay_time),
        INTERVAL '1' HOUR
    )
)
GROUP BY window_start, window_end;
```

---

## 3.4 Watermark Behaviour

```text
09:58 event arrives
→ watermark remains before 10:00
→ 09:00–10:00 window stays open

10:02 event arrives
→ watermark passes 10:00
→ 09:00–10:00 window closes
→ Flink emits the hourly result
```

The watermark advances because newer event-time records arrive, not simply because the wall clock reaches the next hour.

Idle partition handling:

```sql
'scan.watermark.idle-timeout' = '1 min'
```

This prevents an inactive Kafka partition from blocking the global watermark.

---

## 3.5 Historical Backfill

A streaming job cannot calculate data from before its deployment date. Historical data is loaded once from the complete ODS table.

```sql
INSERT OVERWRITE TABLE dm.dm_pay_hourly_stats_d
PARTITION (dt)
SELECT
    DATE_FORMAT(pay_time, 'yyyy-MM-dd') AS dt,
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00') AS window_start,
    COUNT(*) AS pay_count,
    SUM(pay_amount) AS pay_amount
FROM ods.ods_payment_detail
WHERE dt >= '2026-01-01'
  AND dt <  '2026-07-01'
GROUP BY
    DATE_FORMAT(pay_time, 'yyyy-MM-dd'),
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00');
```

---

## 3.6 Daily T-1 Reconciliation

The real-time result may miss very late events. A daily batch job recalculates yesterday from the complete ODS data.

```sql
INSERT OVERWRITE TABLE dm.dm_pay_hourly_stats_d
PARTITION (dt = '${yesterday}')
SELECT
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00') AS window_start,
    COUNT(*) AS pay_count,
    SUM(pay_amount) AS pay_amount
FROM ods.ods_payment_detail
WHERE dt = '${yesterday}'
GROUP BY DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00');
```

Accuracy model:

```text
History before go-live
→ one-time backfill
→ final

Yesterday
→ real-time result
→ T-1 recalculation
→ final

Today
→ real-time approximation
→ corrected tomorrow
```

---

## 3.7 ClickHouse Serving Layer

```sql
CREATE TABLE dws_pay_hourly_stats
(
    window_start DateTime,
    pay_count    UInt64,
    pay_amount   Decimal(18, 2),
    update_time  DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(update_time)
ORDER BY window_start;
```

Latest-version query:

```sql
SELECT
    window_start,
    argMax(pay_count, update_time) AS pay_count,
    argMax(pay_amount, update_time) AS pay_amount
FROM dws_pay_hourly_stats
GROUP BY window_start
ORDER BY window_start;
```

Why ClickHouse?

| HBase | ClickHouse |
|---|---|
| Key-based online lookup | Analytical aggregation |
| Used by Flink or services | Used by BI tools and analysts |
| Best for Case 1 | Best for Case 2 |

---

# 4. Job Inventory and Deployment

| Job | Case | Technology | Mode |
|---|---|---|---|
| `FirstPayDetectionJob` | Case 1 | Flink SQL | Long-running, P0 |
| `HiveFirstPayMergeJob` | Case 1 | Hive/Spark SQL | Daily 02:00 |
| `BulkLoadHBaseJob` | Case 1 | Spark + HBase | Daily 02:30 |
| `HourlyPayStatsJob` | Case 2 | Flink SQL | Long-running, P2 |
| `HourlyStatsBackfillJob` | Case 2 | Hive/Spark SQL | One-time |
| `HourlyStatsReconciliationJob` | Case 2 | Hive/Spark SQL | Daily 02:00 |

| Job Type | Deployment Method |
|---|---|
| Long-running Flink job | Submit with checkpointing enabled |
| Scheduled batch job | Register in Airflow or DolphinScheduler |
| One-time backfill | Run manually with a fixed date range |

---

# 5. Interview Quick Reference

| Question | Concise Answer |
|---|---|
| Why use one Flink job in Case 1? | Deduplication and HBase lookup form one business path, and no reusable intermediate stream is required. |
| Why is `proctime` needed? | It provides the time attribute required for a processing-time temporal lookup join. |
| What is `ft_dim_hbase_first_pay`? | It is a Flink SQL connector mapping to the physical HBase dimension table. |
| Why not query Hive directly? | Hive is designed for batch scans, while HBase supports low-latency key lookup. |
| Why add a hash prefix to the HBase row key? | It distributes rows across regions and reduces hotspot risk. |
| Why include the date in `ROW_NUMBER()`? | The job runs continuously, so the date keeps each day's earliest payment independent. |
| Why configure state TTL? | It prevents daily deduplication state from growing indefinitely. |
| Why is downstream idempotency still required? | Recovery and at-least-once delivery may produce duplicate business-action requests. |
| When does a tumbling window emit? | When the watermark passes the window end. |
| Why use T-1 reconciliation? | It corrects the real-time result with complete offline data. |
| Why use ClickHouse for Case 2? | It supports analytical aggregation and BI queries efficiently. |
