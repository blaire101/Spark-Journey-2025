# AWS Certified Data Engineer – Associate (DEA-C01)
## Complete Study Guide + Practice Quiz

> **Pass Score:** 720/1000 | **Questions:** 65 (50 scored + 15 unscored) | **Duration:** 130 min | **Price:** USD 150 | **Exam version:** v1.1 (December 2025)

---

## 📚 Table of Contents

- [Exam At a Glance](#exam-at-a-glance)
- [6-Week Study Plan](#6-week-study-plan)
- [P1 — Data Ingestion & Transformation (34%)](#p1--data-ingestion--transformation-34)
- [P2 — Data Store Management (26%)](#p2--data-store-management-26)
- [P3 — Data Operations & Support (22%)](#p3--data-operations--support-22)
- [P4 — Data Security & Governance (18%)](#p4--data-security--governance-18)
- [Practice Quiz — 20 Questions](#practice-quiz--20-questions)
- [Study Resources](#study-resources)

---

## Exam At a Glance

```
Domain Weights (bar length = exam weight)

P1 — Data Ingestion & Transformation   ████████████████████████████████████ 34%  ← biggest weight
P2 — Data Store Management             █████████████████████████████        26%
P3 — Data Operations & Support         █████████████████████████            22%
P4 — Data Security & Governance        ████████████████████                 18%
```

| Item | Detail |
|------|--------|
| Target experience | 2-3 years data engineering + 1-2 years AWS hands-on |
| Questions | 65 total — 50 scored, 15 unscored (you can't tell which) |
| Score range | 100–1000, pass at 720 |
| Question types | Multiple choice (1 answer) and Multiple response (2+ answers) |
| Out of scope | ML model training, language-specific syntax, business conclusions from data |

### ⚡ Exam version: v1.1 (December 2025)

Version 1.1 adds new topics not in v1.0 — watch for these:
- **Apache Iceberg** open table format
- **HNSW** and **IVF** vector index types for semantic search
- **Amazon Bedrock** knowledge bases
- **Amazon SageMaker Catalog** for business metadata
- **LLM integration patterns** in data pipelines

### In-scope services quick reference

**Analytics & Streaming:** `Athena` `EMR` `Glue` `Glue DataBrew` `Lake Formation` `Kinesis Data Firehose` `Kinesis Data Streams` `Managed Flink` `MSK` `OpenSearch` `QuickSight`

**Database & Storage:** `DynamoDB` `RDS` `Aurora` `Redshift` `DocumentDB` `MemoryDB` `Neptune` `Keyspaces` `S3` `S3 Tables` `S3 Glacier`

**Security & Governance:** `IAM` `KMS` `Macie` `Secrets Manager` `CloudTrail` `Lake Formation` `VPC / PrivateLink`

**New in v1.1 ⭐:** `Amazon Bedrock` `SageMaker AI` `Amazon Kendra` `SageMaker Catalog`

---

## 6-Week Study Plan

```
Week 1        Week 2         Week 3         Week 4         Week 5         Week 6
┌─────────┐  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐
│ P1:     │  │ P1 cont │   │ P2 cont │   │ P4: IAM │   │ v1.1    │   │ Practice     │
│ Kinesis │→ │ + P2:   │→  │ + P3:   │→  │ KMS     │→  │ New:    │→  │ exams        │
│ Glue    │  │ Redshift│   │ Athena  │   │ Macie   │   │ Bedrock │   │ + weak spots │
│ Lambda  │  │ DDB     │   │ CW      │   │ Trail   │   │ Iceberg │   │              │
└─────────┘  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └──────────────┘
```

> Domain P1 deserves the most time — if studying part-time, stretch Weeks 1-2 into 3 weeks.

---

## P1 — Data Ingestion & Transformation (34%)

**The heaviest domain.** Covers streaming, batch ingestion, ETL, orchestration, and programming concepts.

```
Pipeline overview:

Sources          Ingest           Transform         Orchestrate        Sink
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ S3      │    │ Kinesis │    │ Glue    │    │ Step Fn │
│ Kinesis │ →  │ MSK     │ →  │ EMR     │ →  │ MWAA    │ →  destination
│ MSK/RDS │    │ AppFlow │    │ Lambda  │    │ Glue    │
│ DynamoDB│    │ DMS     │    │ Redshift│    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Task 1.1 — Perform Data Ingestion

**Streaming vs Batch — when to use what:** Streaming sources deliver data continuously in real time — Kinesis Data Streams for custom real-time applications, MSK (Managed Streaming for Apache Kafka) for Kafka-native workloads, DynamoDB Streams for capturing table changes, AWS DMS for continuous database replication. Batch sources process data in scheduled intervals — S3 for file-based loads, Glue for large ETL, EMR for distributed processing, AppFlow for SaaS connectors, Lambda for lightweight event-driven triggers.

| Scenario | Service to use | Why |
|----------|-----------------|-----|
| Real-time clickstream from mobile app | Kinesis Data Streams | Sub-second latency, consumer fan-out |
| Existing Kafka workload on-prem | Amazon MSK | Managed Kafka, no migration of producer code |
| Trigger ETL when a file lands in S3 | S3 Event Notifications + Lambda | EventBridge or direct Lambda trigger |
| Replicate RDS to S3 continuously | AWS DMS (CDC mode) | Change Data Capture, near-real-time |
| SaaS data (Salesforce → S3) | Amazon AppFlow | No-code connector, scheduled or event-triggered |

**Key concepts:**
- **Fan-in / fan-out:** fan-in aggregates multiple streams into one consumer; fan-out distributes one stream to multiple consumers (Kinesis Enhanced Fan-Out)
- **Stateful vs stateless:** stateful maintains context across events (session data); stateless treats each event independently
- **Replayability:** Kinesis retains records for 24h–365 days, allowing replay; SQS does not natively support ordered replay
- **Throttling:** when hitting DynamoDB or RDS rate limits, use exponential backoff, SQS as buffer, or Kinesis Firehose to absorb spikes

### Task 1.2 — Transform and Process Data

**AWS Glue** is the primary ETL service — serverless, scales automatically, supports PySpark, integrates natively with S3, Redshift, and the Glue Data Catalog. **Amazon EMR** is for large-scale distributed processing needing full Spark/Hadoop control. **Lambda** handles lightweight, event-driven transformations under 15 minutes. **Redshift** does in-warehouse transformations using SQL when data is already loaded.

> ⭐ **NEW v1.1 — LLM Integration in Data Pipelines:** The exam now tests LLM integration in data processing. Key patterns: using Amazon Bedrock to classify or enrich records as part of a Glue ETL job, calling Bedrock inference APIs from Lambda for per-record enrichment, and using Bedrock knowledge bases for semantic search over processed documents.

| Format conversion | Tool | Key benefit |
|--------------------|------|-------------|
| CSV → Parquet | Glue ETL job | Columnar format reduces Athena query cost by ~80% |
| JSON → Avro | Glue or Kafka Streams | Schema evolution support |
| Unstructured → structured | Lambda + Bedrock | LLM extraction of fields |

### Task 1.3 — Orchestrate Data Pipelines

**AWS Step Functions** is a visual state machine for complex branching, error handling, and retry logic. **Amazon MWAA** (Managed Apache Airflow) suits teams already using Airflow DAGs. **AWS Glue Workflows** is simpler/cheaper when the entire pipeline lives in Glue. **EventBridge** is for event-driven triggers, not full orchestration.

| Tool | Best for | Avoid when |
|------|----------|------------|
| Step Functions | Multi-service workflows with complex branching | Need Python-native DAG syntax |
| MWAA | Existing Airflow users, rich scheduling | Simple single-service pipelines |
| Glue Workflows | Glue-only pipelines | Need cross-service orchestration |
| EventBridge | Event-driven triggers (time-based, S3 events) | Complex dependency chains |

### Task 1.4 — Apply Programming Concepts

The exam tests concepts, not code. Know that Lambda **reserved concurrency** sets a hard cap per function to prevent throttling under burst load. IaC: **CloudFormation** deploys templates declaratively, **CDK** generates CloudFormation using Python/TypeScript, **SAM** is CloudFormation simplified for serverless. CI/CD typically means CodePipeline triggering Glue job deployment or Lambda updates. A **DAG** (Directed Acyclic Graph — Airflow, Step Functions) prevents circular dependencies.

### 🌳 Decision tree — which ingestion path?

```
Does data arrive continuously?
├── YES
│   ├── Custom real-time app        → Kinesis Data Streams
│   └── Existing Kafka workload     → Amazon MSK
└── NO
    ├── File lands in S3            → S3 Event + Lambda
    ├── SaaS app (Salesforce etc.)  → Amazon AppFlow
    └── Existing DB, need CDC       → AWS DMS (Change Data Capture mode)
```

### ⚡ P1 Cheat Sheet — fast recall table

| If you see... | Pick... |
|----------------|---------|
| "real-time", "sub-second", "clickstream" | Kinesis Data Streams |
| "Kafka", "on-prem streaming" | Amazon MSK |
| "serverless ETL", "PySpark", "no cluster" | AWS Glue |
| "full Spark control", "Hadoop", "huge scale" | Amazon EMR |
| "complex branching", "retry logic", "state machine" | Step Functions |
| "existing Airflow DAGs" | Amazon MWAA |
| "no-code SaaS connector" | Amazon AppFlow |
| "LLM enrichment", "sentiment", "classify text" | Amazon Bedrock ⭐v1.1 |
| "CSV to Parquet", "reduce Athena cost" | Glue ETL job with Parquet + Snappy |

---

## P2 — Data Store Management (26%)

Choosing the right data store, cataloging, lifecycle management, and data modelling.

### Task 2.1 — Choose the Right Data Store

| Use case | Service | Key differentiator |
|----------|---------|---------------------|
| Data warehouse / analytics | Amazon Redshift | MPP columnar, RA3 nodes, Spectrum for S3 |
| Big data distributed processing | Amazon EMR | Full Spark/Hadoop control, spot instances |
| Data lake management | AWS Lake Formation | Centralised permissions on top of S3 + Glue Catalog |
| Relational / OLTP | RDS / Aurora | Aurora is 5x MySQL / 3x PostgreSQL performance |
| NoSQL key-value (massive scale) | DynamoDB | Single-digit ms at any scale, serverless |
| Real-time streaming store | Kinesis / MSK | Kinesis for AWS-native; MSK for Kafka compatibility |
| Fast key-value cache | MemoryDB for Redis | Durable Redis, microsecond reads |
| Vector similarity search ⭐ | Aurora PostgreSQL + HNSW / IVF | New in v1.1 — for ML embedding search |

> ⭐ **NEW v1.1 — Apache Iceberg and Vector Indexes:** Apache Iceberg is an open table format for data lakes — provides ACID transactions, schema evolution, and time travel on top of S3. Iceberg offers row-level updates/deletes (Hive does not), full schema evolution without table rewrites, and partition evolution without data migration. For vector indexes: **HNSW** (Hierarchical Navigable Small World) is approximate nearest-neighbour search optimised for speed; **IVF** (Inverted File Index) clusters vectors and searches clusters first, good for very large datasets.

### Task 2.2 — Data Cataloging Systems

**AWS Glue Data Catalog** is the primary technical metadata catalog — stores table schemas, partition information, connection definitions; backing store for Athena, EMR, Redshift Spectrum. **Glue Crawlers** auto-discover schemas by sampling data. **Apache Hive Metastore** is the open-source equivalent, used for on-prem Hadoop compatibility. **Amazon SageMaker Catalog** (new in v1.1) is a business-facing catalog for data discovery.

### Task 2.3 — Manage Data Lifecycle

```
S3 Storage Tiers — cost vs access frequency

Standard → Standard-IA → Glacier Instant → Glacier Flexible → Glacier Deep Archive
(daily)     (monthly)      (quarterly)      (yearly, min-hrs)   (rare, 12h retrieval)

← Frequent access, higher cost                    Rare access, lowest cost →
```

S3 Standard is for frequently accessed data — highest cost. S3 Standard-IA is for data accessed less than monthly — lower storage cost, retrieval fee applies. S3 Glacier Instant matches Standard-IA pricing for quarterly access. S3 Glacier Flexible takes minutes-to-hours — for backups. S3 Glacier Deep Archive is cheapest — under $1/TB/month, 12-hour retrieval. Use **S3 Lifecycle Policies** to automate tier transitions based on object age.

### Task 2.4 — Data Models and Schema Evolution

**AWS SCT** (Schema Conversion Tool) converts Oracle/SQL Server schemas to Aurora PostgreSQL/MySQL. **AWS DMS Schema Conversion** is the newer managed version integrated into DMS. For Redshift: consider distribution keys (which node owns which data) and sort keys (query performance via data ordering). For DynamoDB: partition key design is critical — avoid hot partitions with high-cardinality keys and write sharding.

### 🗺️ Visual — matching workload shape to data store

```
┌──────────────────────────────┬──────────────────────────────┐
│ 📊 SQL analytics, BI          │ ⚡ Key-value, massive scale   │
│ Large scans, aggregations     │ Single-digit ms lookups       │
│ → Amazon Redshift             │ → Amazon DynamoDB             │
├──────────────────────────────┼──────────────────────────────┤
│ 🏦 Relational, transactional  │ 🌊 Continuous streaming       │
│ ACID transactions, FKs        │ Real-time ingestion, replay   │
│ → RDS or Aurora               │ → Kinesis Data Streams / MSK  │
└──────────────────────────────┴──────────────────────────────┘
```

### ⚡ P2 Cheat Sheet — fast recall table

| If you see... | Pick... |
|----------------|---------|
| "data warehouse", "MPP", "columnar analytics" | Amazon Redshift |
| "NoSQL", "single-digit ms", "any scale" | Amazon DynamoDB |
| "ACID on S3", "time travel", "schema evolution" | Apache Iceberg ⭐v1.1 |
| "technical metadata", "auto-discover schema" | Glue Data Catalog + Crawlers |
| "business catalog", "data discovery for analysts" | SageMaker Catalog ⭐v1.1 |
| "rarely accessed", "cost optimisation" | S3 Lifecycle → Standard-IA → Glacier |
| "vector similarity", "embedding search" | Aurora PostgreSQL + HNSW/IVF ⭐v1.1 |
| "schema migration between engines" | AWS SCT / DMS Schema Conversion |

---

## P3 — Data Operations & Support (22%)

Automation, analysis, monitoring, and data quality.

### Task 3.1 — Automate Data Processing

**AWS Glue DataBrew** is a visual data preparation tool — 250+ built-in transformations, no code required. **Amazon Athena** is serverless SQL against S3 — pay per query by data scanned; Parquet + partitioning dramatically cut costs. **Amazon EventBridge** routes events between AWS services and SaaS apps, supports scheduled rules as a cron replacement.

### Task 3.2 — Analyse Data

| Tool | Best use | Exam tip |
|------|----------|----------|
| Amazon QuickSight | BI dashboards, SPICE in-memory engine | SPICE = Super-fast Parallel In-memory Calculation Engine |
| AWS Glue DataBrew | Visual data profiling, cleaning, no-code | For data quality rules and anomaly detection |
| Amazon Athena | Ad-hoc SQL on S3 data | Partitioning + Parquet = lowest query cost |
| Athena + Spark | Interactive notebook for ML prep | No cluster to manage vs EMR |
| SageMaker Data Wrangler | ML-focused data prep + feature engineering | Integrates with SageMaker Pipelines |

**Redshift (provisioned) vs Athena (serverless)** — classic exam tradeoff: Redshift suits consistent, predictable query load with sub-second performance — you pay for capacity regardless of use. Athena suits ad-hoc/unpredictable patterns — pay only for data scanned. Small BI team with occasional reports on S3 → Athena is cheaper. Hundreds of queries/day on a stable warehouse → Redshift gives better performance per dollar.

### Task 3.3 — Maintain and Monitor Pipelines

```
The monitoring stack — three layers

┌────────────────────────────────────────────────────────┐
│ Layer 3 — OpenSearch + Managed Grafana                  │
│ Full-text search, aggregations at massive log volume    │
└────────────────────────────────────────────────────────┘
                          ↑
┌────────────────────────────────────────────────────────┐
│ Layer 2 — CloudWatch Logs + Logs Insights                │
│ App log storage — Lambda, Glue, EMR logs; query language │
└────────────────────────────────────────────────────────┘
                          ↑
┌────────────────────────────────────────────────────────┐
│ Layer 1 — CloudTrail                                     │
│ Every AWS API call: who, what, when, from where — audit  │
└────────────────────────────────────────────────────────┘
```

Start at CloudTrail (what happened), move up to CloudWatch (application detail), OpenSearch when volume exceeds what Logs Insights alone can handle.

### Task 3.4 — Ensure Data Quality

Common checks: empty fields/null values in mandatory columns, type mismatches, duplicates via primary key violations, completeness (% of expected records arrived). **Glue DataBrew** defines quality rules visually. **Glue Data Quality** (DQDL — Data Quality Definition Language) writes rules in code during Glue ETL jobs. Sampling: simple random sampling is unbiased; **stratified sampling** preserves proportions across subgroups — important for skewed datasets.

### ⚡ P3 Cheat Sheet — fast recall table

| If you see... | Pick... |
|----------------|---------|
| "visual data prep", "no-code cleaning" | AWS Glue DataBrew |
| "ad-hoc SQL on S3", "pay per query" | Amazon Athena |
| "BI dashboards", "SPICE" | Amazon QuickSight |
| "predictable heavy query load" | Amazon Redshift (provisioned) |
| "audit every API call" | AWS CloudTrail |
| "application log errors", "Lambda timeout debug" | CloudWatch Logs + Logs Insights |
| "log analytics at huge scale" | Amazon OpenSearch Service |
| "null rate threshold alert" | Glue DataBrew data quality rules + SNS |
| "skewed dataset sampling" | Stratified sampling |

---

## P4 — Data Security & Governance (18%)

Authentication, authorisation, encryption, audit, and privacy.

```
Four pillars of Domain 4

┌───────────────┬───────────────┬───────────────┬───────────────────┐
│ Authenticate  │ Authorise     │ Encrypt        │ Audit & Govern     │
│ IAM Roles     │ Lake Formation│ AWS KMS        │ CloudTrail(Lake)   │
│ Secrets Mgr   │ RBAC/ABAC     │ TLS in transit │ Amazon Macie       │
│ VPC Sec Grps  │ Least priv.   │ Masking / PII  │ AWS Config         │
└───────────────┴───────────────┴───────────────┴───────────────────┘
```

### Tasks 4.1 & 4.2 — Authentication and Authorisation

Managed policies are reusable across multiple principals; inline policies embed in a single principal for non-reusable permissions. **Principle of least privilege** — grant only what's required. **AWS Lake Formation** adds a permissions layer on S3 + Glue Data Catalog — column-level, row-level, table-level permissions, auto-generates underlying policies. **RBAC** assigns permissions by job function; **ABAC** uses tags on both resource and principal to determine access dynamically.

### Task 4.3 — Encryption and Masking

**AWS KMS** manages encryption keys — CMKs give full rotation control and cross-account capability. S3 encryption: SSE-S3 (AWS-managed, simplest), SSE-KMS (customer control, audit trail, cross-account), SSE-C (customer-provided keys). Encryption in transit = TLS, enforced via `aws:SecureTransport` condition. **Data masking** replaces sensitive values with tokens/hashes for PII in non-prod. **Anonymisation** is irreversible masking.

### Tasks 4.4 & 4.5 — Audit and Privacy

**CloudTrail** records every API call — who, what, when, from where. **CloudTrail Lake** is a managed event data store queryable with SQL, no S3/Athena setup needed. **Amazon Macie** uses ML to auto-discover and classify PII in S3 (passport numbers, credit cards, health info). Combine Macie with Lake Formation column-level security to auto-restrict access to discovered sensitive columns.

> ⭐ **NEW v1.1 — Governance frameworks and SageMaker Catalog:** Governance covers data quality, lineage, access control, and compliance — not just technical cataloging. SageMaker Catalog is a business-facing metadata catalog for data consumers to discover datasets without technical Glue knowledge, supporting projects, domain units, custom metadata, integrated with SageMaker Unified Studio.

### ⚡ P4 Cheat Sheet — fast recall table

| If you see... | Pick... |
|----------------|---------|
| "full control of keys", "custom rotation", "cross-account" | SSE-KMS with Customer Managed Key |
| "simplest S3 encryption", "no key management" | SSE-S3 |
| "column-level security", "row-level filter" | AWS Lake Formation |
| "auto-discover PII", "classify sensitive data" | Amazon Macie |
| "query API history with SQL" | CloudTrail Lake |
| "rotate DB credentials automatically" | AWS Secrets Manager |
| "share live data cross-account, no copy" | Redshift Data Sharing |
| "tags determine access dynamically" | Attribute-Based Access Control (ABAC) |
| "business-facing governance catalog" | SageMaker Catalog ⭐v1.1 |

---

## Practice Quiz — 20 Questions

> Answer key is inline after each question. Cover the answer and try each one first.

**Q1.** A company needs to ingest clickstream data from a mobile app in real time and process it within 500 milliseconds. Which service is the MOST appropriate? *(P1)*
A. Amazon SQS with Lambda consumer B. **Amazon Kinesis Data Streams with Managed Flink** C. AWS Glue ETL job triggered every minute D. Amazon S3 with EventBridge scheduled rule
> ✅ **B** — Kinesis Data Streams provides sub-second latency; Managed Flink processes streams with millisecond latency. SQS adds polling latency; Glue and S3+EventBridge are batch-oriented.

**Q2.** A data engineer wants to convert 10TB of JSON files in S3 to Parquet to reduce Athena costs. Most cost-effective approach? *(P1)*
A. Load into Redshift, UNLOAD as Parquet B. EC2 with custom PySpark C. **AWS Glue ETL job, JSON → Parquet with Snappy** D. Lambda converting each file individually
> ✅ **C** — Glue is serverless, natively reads JSON/writes Parquet, integrates with the Data Catalog. Lambda has a 15-min timeout/10GB limit — unsuitable for large files.

**Q3.** An application uses DynamoDB and needs to process all table changes in real time to update a search index. Which feature enables this? *(P1)*
A. DynamoDB Global Tables B. DynamoDB Accelerator (DAX) C. DynamoDB Point-in-Time Recovery D. **DynamoDB Streams with a Lambda trigger**
> ✅ **D** — DynamoDB Streams captures item-level modifications in near real time; Lambda triggers directly from the stream — standard CDC pattern.

**Q4.** A company needs ACID transactions, schema evolution without table rewrites, and time travel on data in S3. Which solution meets ALL requirements? *(P2)*
A. Redshift Spectrum with Parquet files B. **Amazon S3 with Apache Iceberg table format** C. Athena with standard Hive tables D. Lake Formation with standard S3 prefixes
> ✅ **B** — Apache Iceberg (v1.1) provides ACID transactions, schema/partition evolution, and time travel natively on S3. Hive tables lack row-level updates and time travel.

**Q5.** A startup runs ad-hoc SQL on 500GB of Parquet in S3, unpredictable query frequency. Most cost-effective solution? *(P3)*
A. **Amazon Athena with partitioned Parquet tables** B. Redshift provisioned cluster C. EMR cluster running continuously D. RDS PostgreSQL with S3 import
> ✅ **A** — Athena is pay-per-query-scanned ($5/TB). Redshift/EMR charge continuously regardless of use; RDS is for OLTP, not ad-hoc S3 analytics.

**Q6.** A data team needs column-level access — analysts see masked PII, data scientists see raw values. Which service provides this natively? *(P4)*
A. S3 bucket policies with condition keys B. IAM inline policies with resource-level permissions C. **AWS Lake Formation with column-level security and data filters** D. Amazon Macie with automatic remediation
> ✅ **C** — Lake Formation supports column-level security and data filters across Athena, Redshift Spectrum, EMR. S3 policies are object-level; IAM has no column awareness; Macie discovers but doesn't restrict.

**Q7.** A pipeline ingests 1M records/day from Salesforce, needs a schedule every 6 hours, no code. Simplest solution? *(P1)*
A. Glue custom connector with EventBridge trigger B. Lambda calling Salesforce REST API on schedule C. AWS DMS with Salesforce as source D. **Amazon AppFlow with a scheduled flow every 6 hours**
> ✅ **D** — AppFlow provides no-code Salesforce connectors with native scheduling, field mapping, validation. Glue/Lambda require development; DMS doesn't natively connect to Salesforce.

**Q8.** A Glue ETL job fails intermittently with "out of memory" on large partitions. Best fix? *(P3)*
A. Increase job timeout B. **Enable job bookmarks and increase DPUs (Data Processing Units)** C. Switch PySpark to Python shell D. Convert source to CSV
> ✅ **B** — More DPUs = more memory/executors for the Spark job. Timeout addresses time limits not memory; Python shell is single-node (worse); CSV doesn't reduce memory use.

**Q9.** A company needs S3 encryption with fully self-controlled keys, custom rotation, and cross-account access. Which option? *(P4)*
A. **SSE-KMS with a Customer Managed Key (CMK)** B. SSE-S3 with AWS-managed keys C. SSE-C with client-provided keys D. Client-side encryption before upload
> ✅ **A** — SSE-KMS + CMK gives custom rotation, IAM/key policy control, cross-account sharing, CloudTrail audit. SSE-S3 has no customer control; SSE-C requires providing keys on every request.

**Q10.** A data lake has 5 years of logs; 90+ days rarely accessed, 1+ year almost never accessed. Lifecycle config that minimises cost? *(P2)*
A. Move all to Glacier Deep Archive immediately B. Keep everything in S3 Standard C. **Transition to Standard-IA after 90 days, Glacier Flexible after 365 days** D. Intelligent-Tiering after 30 days for all files
> ✅ **C** — Standard-IA for 90+ day access; Glacier Flexible after a year of near-zero access. Deep Archive immediately adds 12h latency for the first 90 days; Standard is most expensive; Intelligent-Tiering suits unpredictable patterns, not this predictable aging.

**Q11.** Which service auto-discovers and classifies sensitive PII in S3 buckets across an account? *(P4)*
A. AWS Config B. AWS CloudTrail C. Amazon Inspector D. **Amazon Macie**
> ✅ **D** — Macie uses ML to discover, classify, and protect sensitive data in S3. Config tracks configuration changes; CloudTrail logs API calls; Inspector scans EC2/Lambda for vulnerabilities.

**Q12.** A pipeline needs complex branching, exponential backoff retry, and parallel execution across 5 Lambdas. Most suitable orchestration tool? *(P1)*
A. EventBridge with multiple rules B. **Step Functions with Map state and Catch/Retry configuration** C. Glue Workflows with triggers D. Lambda calling Lambda in sequence
> ✅ **B** — Step Functions natively supports branching (Choice), parallel (Parallel/Map), retry with backoff, and error handling (Catch). EventBridge routes events; Glue Workflows is Glue-only; Lambda-chaining lacks built-in retry/branching.

**Q13.** A Glue Crawler discovered new S3 partitions, but they're not visible in Athena. Most likely cause? *(P2)*
A. **The Glue Data Catalog was not updated after the crawler ran** B. Athena doesn't support partitioned tables C. The S3 bucket is in a different region D. Parquet requires a schema registry
> ✅ **A** — Athena reads Catalog metadata; if partition metadata wasn't refreshed (e.g. MSCK REPAIR TABLE, re-running the crawler), new partitions won't appear. B, C, D are all false statements.

**Q14.** Security team needs a complete, SQL-queryable audit trail of API calls for the last 90 days. Best solution? *(P4)*
A. CloudWatch Logs + Logs Insights B. Export CloudTrail to S3, query with Athena C. **Enable CloudTrail Lake, run SQL directly in console** D. AWS Config rules to query API history
> ✅ **C** — CloudTrail Lake is a managed event data store, auto-ingests CloudTrail events, SQL-queryable in-console, retains up to 7 years. B works but needs more setup; CloudWatch is app logs; Config tracks resource config, not API audit.

**Q15.** A pipeline needs to enrich customer records with LLM-based sentiment analysis of support tickets. Most appropriate architecture? *(P1, v1.1)*
A. Train a custom SageMaker model, call from Glue B. **Call Bedrock's InvokeModel API from Lambda, triggered per record** C. Use Comprehend for entity recognition only D. Store text in Redshift, use a SQL UDF
> ✅ **B** — Bedrock provides foundation models via API — no training needed. This is a key v1.1 addition. Custom training is unnecessary; Comprehend doesn't use an LLM; Redshift UDFs add complexity.

**Q16.** A DynamoDB hot partition receives 80% of writes, causing throttling. Best mitigation? *(P2)*
A. Enable DAX B. Switch to provisioned capacity with auto-scaling C. Create a GSI on the hot key D. **Use write sharding — append a random suffix to the partition key**
> ✅ **D** — Write sharding distributes writes across multiple physical partitions. DAX is a read cache (doesn't help writes); auto-scaling reacts after throttling; GSI has the same hotness problem.

**Q17.** A Lambda function processing Kinesis records times out during spikes. Which TWO changes MOST improve throughput? *(P1, select TWO)*
A. **Increase Kinesis shard count for more parallelism** B. **Increase Lambda reserved concurrency** C. Enable Kinesis Enhanced Fan-Out D. Switch Lambda runtime from Python to Java
> ✅ **A and B** — More shards = more parallel Lambda invocations; more reserved concurrency = capacity to scale without account-level throttling. Enhanced Fan-Out is for multiple distinct consumers, not single-consumer throughput; runtime change doesn't fix a throughput bottleneck.

**Q18.** A team needs to share a Redshift warehouse with a partner in a different account — specific tables only, no copying to their S3. Which feature? *(P4)*
A. Export tables to S3, cross-account bucket sharing B. Create an assumable IAM role C. **Redshift Data Sharing with cross-account access and restricted consumer IAM** D. AWS DMS replicating specified tables
> ✅ **C** — Redshift Data Sharing gives live, read-only, no-copy access across accounts, restrictable to table/view level. S3 export copies data; IAM role gives full cluster access; DMS copies data — violates the no-copy requirement.

**Q19.** A DataBrew data quality job finds 15% nulls in "customer_email." Need automatic alerts if the rate exceeds 10% in future runs. Best approach? *(P3)*
A. CloudWatch alarm on job duration B. **DataBrew data quality rule with threshold, connected to SNS on failure** C. Lambda function counting nulls after each job D. Enable CloudTrail on the DataBrew job
> ✅ **B** — DataBrew supports data quality rules with configurable thresholds; rule failure can trigger SNS via EventBridge — a declarative, code-free quality gate. Job duration measures performance not quality; custom Lambda is unnecessary; CloudTrail logs API calls not data stats.

**Q20.** A company needs Lambda-to-RDS credentials with automatic 30-day rotation and auditable access logs. Best solution? *(P4)*
A. Lambda environment variables encrypted with KMS B. SSM Parameter Store (Standard) C. Hard-code credentials in the deployment package D. **AWS Secrets Manager with automatic rotation and CloudTrail logging**
> ✅ **D** — Secrets Manager is purpose-built for credentials: automatic rotation (Lambda rotator), versioning, CloudTrail logging of every access. Env vars have no auto-rotation; SSM auto-rotation requires custom setup; hard-coding is never acceptable.

---

## Study Resources

### Official AWS resources (start here)

| Resource | Link | Notes |
|----------|------|-------|
| AWS Exam Guide (DEA-C01 v1.1) | [aws.amazon.com/certification/certified-data-engineer-associate](https://aws.amazon.com/certification/certified-data-engineer-associate/) | Official · Free — the definitive source |
| AWS Skill Builder — Official Practice Qs | [skillbuilder.aws](https://skillbuilder.aws) | Free · 20 official practice questions |
| AWS Skill Builder — Exam Prep Course | [skillbuilder.aws](https://skillbuilder.aws) | Paid · ~$29/mo — labs, flashcards, 65-Q practice exam |

### Top third-party practice tests

| Resource | Link | Notes |
|----------|------|-------|
| Udemy — DEA-C01 Practice Exams (Jon Bonso) | [udemy.com/course/aws-data-engineer-associate-dea-c01-practice-exam](https://www.udemy.com/course/aws-data-engineer-associate-dea-c01-practice-exam/?couponCode=MT260629G3) | Paid · Recommended — 300+ Qs, best explanations |
| Tutorials Dojo Portal | [portal.tutorialsdojo.com/.../dea-c01](https://portal.tutorialsdojo.com/courses/aws-certified-data-engineer-associate-practice-exam-dea-c01/) | Paid · 300+ Qs, per-domain tracking, flashcards |
| Whizlabs | [whizlabs.com/aws-certified-data-engineer](https://www.whizlabs.com/aws-certified-data-engineer/) | Paid · Budget option |
| ExamTopics | [examtopics.com/.../data-engineer-associate](https://www.examtopics.com/exams/amazon/aws-certified-data-engineer-associate/) | Free · Community — verify answers independently |

### AWS Documentation (deep-dive reference)

- [Kinesis Data Streams Developer Guide](https://docs.aws.amazon.com/streams/latest/dev/introduction.html)
- [AWS Glue Developer Guide](https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html)
- [AWS Lake Formation Developer Guide](https://docs.aws.amazon.com/lake-formation/latest/dg/what-is-lake-formation.html)
- [Amazon Redshift Database Developer Guide](https://docs.aws.amazon.com/redshift/latest/dg/welcome.html)
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html) *(new in v1.1)*

### Community

- [r/AWSCertifications](https://www.reddit.com/r/AWSCertifications/) — search "DEA-C01" for real exam experience reports
- [AWS re:Post](https://repost.aws) — official Q&A community

---

*Exam guide version 1.1 — Published December 2025. Always check [aws.amazon.com/certification](https://aws.amazon.com/certification/) for updates before your exam date.*
