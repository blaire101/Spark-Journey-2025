## 📚 Table of Contents

- [Chap 1. Apache Spark Core Concepts](#-1-apache-spark-core-concepts)
- [Chap 2. Execution Model](#-2-execution-model)
- [Chap 3. Shuffle & Partitioning](#-3-shuffle--partitioning)
- [Chap 4. Data Skew（Skewness）](#4-data-skewskewness)
- [Chap 5. General Spark Tuning (Skew Indirectly Helpful)](#5-general-spark-tuning-skew-indirectly-helpful)
- [Chap 6. ❓ Spark QA](#6--spark-qa)

Apache Spark (Distributed computing engine)

## 🟩 1. Apache Spark Core Concepts
📌 **RDD, DataFrame, Lazy |  fault tolerance mechanisms** /fɔːlt/ /ˈtɒlərəns/ /ˈmekənɪzəmz/

| No. | ❓Question | ✅ Answer | 📘 Notes |
| --- | --- | --- | --- |
| 1 | **What is Apache Spark?** | A distributed computing engine for large-scale data processing. | Supports in-memory computation and APIs in Scala, Python, Java, SQL. |
| 2 | **What is an RDD?** | An immutable, partitionable, distributed collection of objects. | immutable to enhance the stability of parallel computation and simplify fault tolerance mechanisms;    supports transformations like `map`, `filter`, `reduceByKey`. |
| 3 | **What is a DataFrame?** | A distributed table with named columns and typed rows. | Built on RDDs; optimized by Catalyst engine; like a distributed Pandas/DataTable. |
| 4 | **What is a transformation?** | A lazy operation that returns a new RDD or DataFrame. | Examples: `map()`, `filter()`, `groupBy()`. |
| 5 | **What is an action?** | An operation that triggers actual computation and returns results. | Examples: `collect()`, `count()`, `show()`. |
| 6 | **What is lazy evaluation?** | Spark builds a **logical DAG of transformations**, which is only executed when an action is called</span>. | Enables optimization and fault tolerance. |

Spark builds a <span style="color:red; font-weight:bold">logical DAG of transformations</span>, which is only executed when <span style="color:red; font-weight:bold">an action is called</span>.

> Spark builds a <span style="color:red">logical DAG of transformations</span>, which is only executed when <span style="color:red">an action is called</span>.

```mermaid
flowchart TB
    Session["SparkSession"]
    subgraph APIs ["Data Ingestion APIs"]
      PyAPI["PySpark<br>spark.read.text(...)"]
      SQLAPI["SparkSQL<br>createOrReplaceTempView(...)"]
    end

    Session --> PyAPI
    Session --> SQLAPI

    PyAPI --> DF1["DataFrame<br>Schema: city:String"]
    SQLAPI --> TempView["TempView 'cities_txt'"]

    DF1 --> WithCount["withColumn('count', lit(1))"]
    TempView --> SQL1["SQL:<br>SELECT city, COUNT(*) AS cnt<br>FROM cities_txt GROUP BY city"]

    WithCount --> GroupByDF["GroupBy city<br>agg(sum('count'))"]
    GroupByDF & SQL1 --> Action["Action: show()/collect()"]
    Action --> Driver["Driver<br>receives final result"]

    %% Styling
    style Session  fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style PyAPI    fill:#bbdefb,stroke:#0d47a1,stroke-width:2px
    style SQLAPI   fill:#d1c4e9,stroke:#4a148c,stroke-width:2px
    style DF1      fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    style WithCount fill:#e1f5fe,stroke:#039be5,stroke-width:2px
    style GroupByDF fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style TempView fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style SQL1     fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style Action   fill:#ede7f6,stroke:#5e35b1,stroke-width:2px
    style Driver   fill:#ffffff,stroke:#999,stroke-width:1px,stroke-dasharray:5 5
```

---
## 🟨 2. Execution Model

📌 **Job → Stage → Task**

| No. | Question | Summary |
| --- | --- | --- |
| 7 | What is a Spark job? | Triggered by action, consists of stages. |
| 8 | What is a stage in Spark? | A set of tasks between shuffles. |
| 9 | What is a task? | Unit of execution on a partition. |

```mermaid
flowchart TD
    A["Action<br>(e.g. collect())"]
    A --> Job["Spark Job"]

    Job --> Stage1["Stage 1<br>No shuffle<br>(e.g. map, filter)"]
    Stage1 --> Stage2["Stage 2<br>After shuffle<br>(e.g. reduceByKey)"]

    Stage1 --> T1["Task 1<br>Partition 0"]
    Stage1 --> T2["Task 2<br>Partition 1"]
    Stage1 --> T3["Task 3<br>Partition 2"]

    Stage2 --> T4["Task 1<br>Partition A"]
    Stage2 --> T5["Task 2<br>Partition B"]

    style A fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px
    style Job fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style Stage1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Stage2 fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    style T1 fill:#fffde7,stroke:#f57f17
    style T2 fill:#fffde7,stroke:#f57f17
    style T3 fill:#fffde7,stroke:#f57f17
    style T4 fill:#f3e5f5,stroke:#6a1b9a
    style T5 fill:#f3e5f5,stroke:#6a1b9a
```

| No. | Question | Summary |
| --- | --- | --- |
| Stage1 | contains narrow transformations (e.g. `map`, `filter`) that don't require shuffling data. | 👉 It is divided into multiple **Tasks**, each processing one partition (e.g. Partition 0, 1, 2). These tasks run **in parallel**. |
| Stage2 | begins **after** Stage 1 is completed, it involves **shuffle** operations like `reduceByKey` | 👉 It too is broken into **Tasks**, now operating on **shuffled partitions** (e.g. Partition A, B). Again, tasks in this stage run in parallel.， Once Stage 2 completes, the final result is returned to the **Driver** |

   
## 🟧 3. Shuffle & Partitioning

📌 **Shuffle = Costly, Wide vs Narrow**

| # | Question | Summary |
| --- | --- | --- |
| 10 | What is a shuffle in Spark? | Data redistribution across partitions. |
| 11 | Why is shuffle expensive? | Disk I/O + network + serialization. |
| 12 | What is the difference between narrow and wide transformations? | Narrow = no shuffle, Wide = shuffle needed. |

<details>
<summary><strong>Narrow vs Wise Dependency</strong></summary>

<div align="center">
  <img src="docs/spark-wide-dependency.webp" alt="Diagram" width="500">
</div>

| No. | ❓Question                              | ✅ Answer                                                                                                                                                   | 📘 Notes                                                                                                                                                                   |
|-----|----------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | What is a Narrow Dependency in Spark?  | A **narrow dependency** means that **each partition** of the parent RDD is used by **at most one partition** of the child RDD.                            | No shuffle is required. Examples include `map`, `filter`, and `union`. These operations allow pipelined execution and are typically faster and more efficient.           |
| 2   | What is a Wide Dependency in Spark?    | A **wide dependency** means that **multiple partitions** of the parent RDD may be used by **multiple partitions** of the child RDD.                       | This necessitates a shuffle across the cluster, typically seen in operations like `groupBy`, `reduceByKey`, or `join`. It incurs higher overhead and network transfer.   |
| 3   | Why are Wide Dependencies expensive?   | Because they involve **shuffles**, during which data must be **redistributed** across nodes, leading to **disk I/O**, **network transfer**, and **skew**. | Wide dependencies are often the primary bottleneck. Optimisation may require techniques such as salting, repartitioning, or adaptive execution.                         |
| 4   | Can Spark optimise Wide Dependencies?  | Yes, Spark can use **Adaptive Query Execution (AQE)** to detect skew and adjust partitioning dynamically to reduce overhead.                             | Enable configs like `spark.sql.adaptive.enabled` and `spark.sql.adaptive.skewJoin.enabled`. AQE may merge small partitions or split skewed ones to improve performance. |

</details>

```mermaid
flowchart TD
    subgraph InputPartitions["Input Partitions"]
        A0["Partition 0"]
        A1["Partition 1"]
        A2["Partition 2"]
    end

    subgraph NarrowTransformation["Narrow Transformation<br>(e.g. map, filter)"]
        B0["Partition 0"]
        B1["Partition 1"]
        B2["Partition 2"]
    end

    subgraph WideTransformation["Wide Transformation<br>(e.g. reduceByKey, groupByKey)"]
        C0["Partition A"]
        C1["Partition B"]
    end

    A0 --> B0
    A1 --> B1
    A2 --> B2

    B0 -->|Shuffle Write| ShuffleStage
    B1 -->|Shuffle Write| ShuffleStage
    B2 -->|Shuffle Write| ShuffleStage

    ShuffleStage -->|Shuffle Read| C0
    ShuffleStage -->|Shuffle Read| C1

    Note1["💡 Shuffle involves:<br>• Disk I/O<br>• Network<br>• Serialization<br><br>❗ Partition count may change!"]
    ShuffleStage -.-> Note1

    %% Styling
    style InputPartitions fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style NarrowTransformation fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style WideTransformation fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style ShuffleStage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style Note1 fill:#fffde7,stroke:#fbc02d,stroke-width:2px,stroke-dasharray: 5 5
```

🔁 Task Count Comparison

| Stage    | Task Type         | Count | Description                                                             |
|----------|-------------------|--------|-------------------------------------------------------------------------|
| Stage 1  | Map Tasks          | 3      | Each processes one original input partition.                           |
| Stage 1  | Shuffle Map Tasks  | 3      | Same as above; each writes shuffle files for downstream consumption.   |
| **Stage 2**  | Reduce Tasks       | 2      | **Each fetches its partitioned data from all 3 shuffle files, merges and aggregates.** |

## 4. Data Skew（skewness)

🔥 Data Skew in Spark - *Unbalanced data across partitions*

| Category                      | Optimization Methods                                           |
|------------------------------|----------------------------------------------------------------|
| 1️⃣ Skewed Input Files        | Repartitioning, Merging small files, Using more suitable file formats |
| 2️⃣ Skewed Join Keys          | Broadcast Join, Salting, Adaptive Query Execution (AQE)       |
| 3️⃣ Skewed Aggregation        | Salting + Two-stage aggregation                               |
| 4️⃣ General Tuning & SQL Hints| SQL hints, Repartitioning, Adaptive Query Execution (AQE)     |

| # | Question | Summary |
| --- | --- | --- |
| 13 | What is data skew? | Unbalanced data across partitions. |
| 14 | What causes it? | Skewed key distribution. |
| 15 | Why is it bad? | Causes long-running tasks, resource underuse. |
| 16 | How to detect it? | Spark UI (task duration, skewed keys). |
| 17 | What ops are sensitive? | Joins, groupByKey, reduceByKey. |
| 18 | What is salting? | Adding randomness to distribute hot keys. |
| 19 | How does salting+grouping work? | Salt keys → aggregate → merge. |
| 20 | What is a broadcast join? | Send small table to all workers. |
| 21 | When to use broadcast? | Small tables (<10MB), skewed joins. |
| 22 | What Spark configs help? | `spark.sql.shuffle.partitions`, `autoBroadcastJoinThreshold`. |
| 23 | What is AQE? | Adaptive runtime optimizations (incl. skew fix). |
| 24 | Other methods to handle skew? | Filter hot keys, use approx algorithms, repartition. |

### 🟢 1. Skewed Input Files

```mermaid
flowchart TD
    A["Input Files<br>City Logs (Text)"] --> B["Spark Read<br>spark.read.text(...)"]
    B --> C1["Partition 0<br>📄 10MB"]
    B --> C2["Partition 1<br>📄 500KB"]
    B --> C3["Partition 2<br>📄 600KB"]
    
    C1 --> D["Skewed Stage Execution<br>❌ One task takes much longer"]
    
    D --> E["✅ Solution:<br>• Repartition<br>• Combine small files<br>• Use columnar format (e.g., Parquet)"]

    style A fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style D fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style E fill:#e0f7fa,stroke:#006064,stroke-width:2px
```


```bash
spark.conf.set("spark.sql.files.maxPartitionBytes", 256*1024*1024)  # 128–512MB common setting
spark.conf.set("spark.sql.files.openCostInBytes",   8*1024*1024)    # 8–16MB adjustable for small file sizes, 1M+8M = 9M
# 1000 1M small files
# 1000 / 256 = 4 tasks VS 1000 / (256/9) = 36 tasks can reduce file handles
spark.conf.set("spark.sql.orc.enableVectorizedReader","true")
spark.conf.set("spark.sql.orc.filterPushdown","true")
# AQE (valid for shuffles)
spark.conf.set("spark.sql.adaptive.enabled","true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled","true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled","true")
```

<details>
<summary>💬 **Solution:**</summary>

> SET spark.sql.shuffle.partitions = 20;     
> SET hive.exec.dynamic.partition.mode = nonstrict;

```mermaid
graph TD
    A[Detect too many small files]:::start --> B[Set spark.sql parameters]:::config
    B --> C[Use INSERT OVERWRITE]:::action
    C --> D{Need to shuffle output?}:::decision
    D -- Yes --> E[Use DISTRIBUTE BY rand（） or column]:::shuffle
    D -- No --> F[Direct INSERT OVERWRITE]:::overwrite
    E --> G[Files merged successfully]:::success
    F --> G

    classDef start fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;
    classDef config fill:#f9f0ff,stroke:#9254de,stroke-width:2px;
    classDef action fill:#fffbe6,stroke:#faad14,stroke-width:2px;
    classDef decision fill:#fff0f6,stroke:#eb2f96,stroke-width:2px;
    classDef shuffle fill:#f6ffed,stroke:#52c41a,stroke-width:2px;
    classDef overwrite fill:#e6fffb,stroke:#13c2c2,stroke-width:2px;
    classDef success fill:#f0f5ff,stroke:#2f54eb,stroke-width:2px;
```

</details>

### 🟣 2. Skewed Join Keys

```mermaid
flowchart TD
    A["Join Two Tables<br>users JOIN logs<br>ON user_id"]
    A --> B["Skewed Key Detected<br>e.g., user_id = 123 appears 1M times"]
    
    B --> C1["Solution 1: Broadcast Join<br>if one table is small (<10MB)"]
    B --> C2["Solution 2: Salting<br>add random prefix/suffix to skewed keys"]
    B --> C3["Solution 3: AQE<br>Adaptive Query Execution handles skewed joins"]

    style A fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style B fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    style C1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style C2 fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    style C3 fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

| Feature                  | AQE (Adaptive Query Execution)          | Salting                                          |
| ------------------------ | --------------------------------------- | ------------------------------------------------ |
| **Optimization timing**  | After shuffle (runtime)                 | Before shuffle (logical rewrite)                 |
| **Implementation**       | Automatic (enable config)               | Manual (modify SQL/ETL)                          |
| **Skew type handled**    | Join/aggregation skew **after** shuffle <br> 1. AQE does not rewrite data to disk — it only modifies the scheduling metadata. <br> 2. The shuffle files remain exactly the ones written by the map stage. <br> 3. As a result, AQE’s overhead is minimal (it’s just analysis and re-planning), and there’s no need for a disk rewrite. | Join skew or data source skew **before** shuffle |
| **Intrusiveness**        | No SQL changes required                 | SQL changes required                             |
| **Best fit scenario**    | Skew is mild and/or not fixed           | Skewed key is known and severe                   |


How Spark chooses (Spark 3.3)
- Broadcast first: if one side fits autoBroadcastJoinThreshold → BHJ. (You can disable by setting to -1 or force via /*+ BROADCAST(t) */.) 
- Otherwise default = SMJ for equi-joins (because spark.sql.join.preferSortMergeJoin=true by default). 
- SHJ: considered when SMJ is not preferred (set spark.sql.join.preferSortMergeJoin=false, or hint /*+ SHUFFLE_HASH(t) */). Spark uses a per-partition hash map on the build side.

### 🟡 3. Skewed Aggregation Keys

```mermaid
flowchart TD
    A["Raw DataFrame<br>Logs with city names"]
    A --> B["Aggregation: GROUP BY city"]
    B --> C["Skewed Key Detected<br>e.g., 'Singapore' appears 1M times"]
    
    C --> D["✅ Solution:<br>• Add salt (e.g., city_1, city_2)<br>• First stage: group by salted keys<br>• Second stage: merge original keys"]

    style A fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style B fill:#bbdefb,stroke:#0d47a1,stroke-width:2px
    style C fill:#f8bbd0,stroke:#c2185b,stroke-width:2px
    style D fill:#e0f7fa,stroke:#006064,stroke-width:2px
```

### 🔧 4. General Spark Tuning & SQL Optimization

```mermaid
flowchart TD
    A["🔥 Task takes long or skewed output"]
    A --> B["Check Spark UI"]
    A --> C["Enable AQE<br>(Adaptive Query Execution)"]
    A --> D["Use SQL Hints<br>e.g., BROADCAST(table), REPARTITION(N)"]
    A --> E["Tune configs:<br>• spark.sql.shuffle.partitions<br>• spark.sql.autoBroadcastJoinThreshold"]

    style A fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    style B fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style C fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style D fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    style E fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
```

## ⚙️ 5. General Spark Tuning (Skew Indirectly Helpful)

These don't solve skew but improve performance or stability overall.
   
```mermaid
flowchart TD
    A["🔥 Spark Optimization Techniques"]

    A --> G1["⚙️ Memory Tuning<br>- executor.memory<br>- memoryOverhead"]
    A --> G2["⚙️ Parallelism<br>- shuffle partitions"]
    A --> G3["⚙️ GC Config<br>- memory fraction<br>- G1GC"]
    A --> G4["⚙️ Dynamic Allocation<br>- auto executor scaling"]
    A --> G5["⚙️ Caching<br>- persist()/cache()"]

    style A fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style G1 fill:#e0f7fa,stroke:#0288d1,stroke-width:2px
    style G2 fill:#e0f7fa,stroke:#0288d1,stroke-width:2px
    style G3 fill:#e0f7fa,stroke:#0288d1,stroke-width:2px
    style G4 fill:#e0f7fa,stroke:#0288d1,stroke-width:2px
    style G5 fill:#e0f7fa,stroke:#0288d1,stroke-width:2px
```

1. **Memory Configuration**
    - Adjust executor/driver memory
    - Configure memory overhead
2. **Parallelism Settings**
    - Tune `spark.sql.shuffle.partitions`
    - Adjust `spark.default.parallelism`
3. **GC Optimization**
    - Tune memory fraction
4. **Dynamic Resource Allocation**
    - Enable auto-scaling of executors
5. **Caching & Persistence**
    - Reuse intermediate results
  
## 6. ❓ Spark QA

---

<details>
<summary><strong>Q1: After Spark reads data, what determines the number of partitions, and what is the role of `spark.sql.shuffle.partitions`? Is setting it to 200 meaningful?</strong></summary>

- The initial partition count is determined by the data source (e.g., HDFS block size, file format, and parallelism).
- `spark.sql.shuffle.partitions` sets the number of partitions **after a shuffle** (e.g., joins, aggregations, groupBy), not during file read.
- Setting it to 200 can be helpful for **large datasets**, increasing parallelism; however, it might introduce overhead for small datasets.

```sql
-- Set partition count for shuffle
SET spark.sql.shuffle.partitions = 200;
```

#### 🔍 Detailed Explanation:

##### 1.1 Input Partitioning:
- Spark reads data based on HDFS block size or other input format configurations. This determines the **initial parallelism**.

##### 1.2 Read & Partition:
- After reading, data is split into partitions.
- More partitions = more parallel tasks = higher throughput (if cluster resources allow).

##### 1.3 Map Phase:
- Tasks transform data within their partition.
- No shuffle or inter-node communication occurs in this phase.

##### 1.4 Reduce Phase:
- Shuffle re-partitions data based on key, such as `groupBy`, `join`, etc.
- Number of reduce tasks is controlled by `spark.sql.shuffle.partitions`.

##### 1.5 Partitions ↔️ Tasks:
- One partition = One task.
- Parallelism depends on partition count **and** available cluster resources (e.g., executor cores).

</details>

<details>
<summary><strong>Q2: What's the difference between MapReduce and Spark in terms of shuffle and memory?</strong></summary>

- **Spark**: Supports in-memory computation and DAG execution.
- **MapReduce**: Always writes intermediate data to disk.

#### 🔹 (1) In-Memory Advantage:

- Spark can cache data in memory across stages, significantly reducing I/O overhead.
- MapReduce flushes to HDFS between each stage.

#### 🔹 (2) DAG Execution:

- Spark builds a Directed Acyclic Graph (DAG) of stages and tasks.
- Reduces unnecessary data writes by chaining operations intelligently.

<div align="center">
  <img src="docs/spark-components-arch.webp" alt="Diagram" width="700">
</div>

#### 🔹 (3) Spark Architecture:

- **Driver & SparkContext**: Starts app, builds DAG via RDD/DataFrame ops.
- **DAG Scheduler**: Splits stages, submits tasks.
- **Execution Engine**: Executes tasks on workers.

<div align="center">
  <img src="docs/spark-components.webp" alt="Diagram" width="700">
</div>

</details>

<details>
<summary><strong> Q3: Why is "Shuffle Read" the bottleneck in skewed aggregations?</strong></summary>

- Spark **reduce tasks** fetch partition files written by map tasks — this is the **Shuffle Read** stage.
- Under skew, some partitions are significantly larger → more data to read → **slower tasks**.
- Aggregation (CPU-bound) is usually lightweight vs I/O-heavy Shuffle Read.

#### 📊 Spark UI Indicators:

- **Shuffle Read Time**: High = skewed data fetch.
- **Task CPU Time**: Usually low even in skew cases.

</details>

<details>
<summary><strong>Q4: How do I troubleshoot Spark performance problems?</strong></summary>

| **Step** | **Description**  | **Key Focus** |
| --- | --- | --- |
| **1. Web UI** | Identify slow jobs and stages.  | Optimize resource allocation and adjust configurations. |
| **2. SQL Code & DAG Inspection** | Analyze long SQL queries and the corresponding DAG to pinpoint problematic parts  | Simplify query logic and optimize expensive operations. |
| **3. Examine Execution Plans** | Use EXPLAIN to view the logical, optimized logical, and physical plans. Focus on problematic nodes like **HashAggregate, SortAggregate, SortMergeJoin**, etc. | Identify problematic nodes and adjust join strategies or grouping techniques. |
| **4.** Web UI - **Stage Summary Metrics** | Analyze task metrics in the Spark Web UI (execution time, data processed) to detect data skew, slow tasks, or resource bottlenecks. | Identify data skew and resource bottlenecks by examining task-level metrics. |
| **5. Data Context Investigation** | Examine the underlying datasets (e.g., using GROUP BY and COUNT queries) to detect skewed keys or large columns that may cause performance issues. | Collaborate with teams to adjust the data model or partitioning strategy if necessary. |

💡 Also monitor:
- **Shuffle Read Time**: If it dominates, the issue is I/O, not CPU.
- **Task Duration Distribution**: Long tails often mean skew.
- **Spill Metrics**: Frequent spills imply memory pressure.

</details>

<details>
<summary><strong>Q5: What is Spark Catalyst Optimizer?</strong></summary>

**A:** Catalyst is the **query optimiser** in SparkSQL.

<div align="center">
  <img src="docs/spark-catalyst.webp" alt="Diagram" width="700">
</div>

- Applies rule-based optimizations:
  - Predicate Pushdown
  - Constant Folding
  - Join Reordering
  - Column Pruning
- Generates efficient execution plans for better performance.

</details>


<details>
<summary><strong>Q6: How to use salting to resolve join skew in Spark?</strong></summary>

```sql
-- Spark SQL / Hive SQL
WITH saltedLarge AS (
  SELECT 
    CONCAT(CAST(FLOOR(RAND() * 10) AS STRING), '_', joinKey) AS saltedKey,
    someValue
  FROM largeTable
),

saltedSmall AS (
  WITH saltValues AS (
    SELECT '0' AS salt
    UNION ALL SELECT '1'
    UNION ALL SELECT '2'
    UNION ALL SELECT '3'
    UNION ALL SELECT '4'
    UNION ALL SELECT '5'
    UNION ALL SELECT '6'
    UNION ALL SELECT '7'
    UNION ALL SELECT '8'
    UNION ALL SELECT '9'
  )
  SELECT 
    CONCAT(sv.salt, '_', t.joinKey) AS saltedKey,
    otherValue
  FROM smallTable t
  CROSS JOIN saltValues sv
)  -- 

SELECT 
  split(s.saltedKey, '_')[1] AS originalKey,
  sum(s.someValue) AS aggregatedValue
FROM saltedLarge s
JOIN saltedSmall ss
  ON s.saltedKey = ss.saltedKey
GROUP BY split(s.saltedKey, '_')[1];
```

</details>
