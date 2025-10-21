**What is a shuffle in Spark?**  

> Data **<mark>redistribution across partitions</mark>**, may involve moving data between **<mark>Executors (nodes)</mark>** over **<mark>network</mark>**.  
This makes it an **<mark>expensive operation</mark>** due to **<mark>disk I/O</mark>**, **<mark>network transfer</mark>**, and **<mark>serialization</mark>**.

## 📚 Table of Contents

- [Chap 1. Apache Spark Core Concepts](#-1-apache-spark-core-concepts)
- [Chap 2. Execution Model](#-2-execution-model)
- [Chap 3. Shuffle & Partitioning](#-3-shuffle--partitioning)
- [Chap 4. Data Skew（Skewness）](#4-data-skewskewness)
- [Chap 5. General Spark Tuning (Skew Indirectly Helpful)](#5-general-spark-tuning-skew-indirectly-helpful)
- [Chap 6. ❓ Spark QA](#6--spark-qa)

Apache Spark (Distributed computing engine)

## 🟩 1. Apache Spark Core Concepts
📌 **RDD, DataFrame, Lazy evaluation · Fault-tolerance mechanisms** /fɔːlt/ /ˈtɒlərəns/ /ˈmekənɪzəmz/

| No. | ❓Question | ✅ Answer | 📘 Notes |
| --- | --- | --- | --- |
| 1 | **What is Apache Spark?** | A distributed computing engine for large-scale data processing. | Supports in-memory computation and APIs in Scala, Python, Java, SQL. |
| 2 | **What is an RDD?** | An immutable, partitioned, distributed collection of objects. | Immutability stabilises parallel computation and simplifies fault tolerance.    supports transformations like `map`, `filter`, `reduceByKey`. |
| 3 | **What is a DataFrame?** | A distributed table with named columns and typed rows. | Built on RDDs; optimized by the Catalyst optimizer; like a distributed Pandas/DataTable. |
| 4 | **What is a transformation?** | A lazy operation producing a new RDD or DataFrame. **<mark>Narrow transformations + Wide transformations</mark>** | Examples: `map()`, `filter()`, `groupBy()`. |
| 5 | **What is an action?** | An operation that triggers actual computation and returns results. | Examples: `collect()`, `count()`, `show()`. |
| 6 | **What is lazy evaluation?** | Spark builds a **<mark>logical DAG of transformations</mark>**, which is only executed when **an action is called**. | Enables optimization and fault tolerance. |

- Spark builds a <mark>**logical DAG of transformations**</mark> when you define operations, but it does not execute them immediately.

### 1️⃣ Compile phase : User Program → Logical/Physical Plan → RDD DAG

```mermaid
flowchart LR
    A[**User Program**<br/>DataFrame/SQL / RDD] --> B[**SparkSession**]

    %% Catalyst Optimizer subgraph
    subgraph C[**Catalyst Optimizer**]
        direction TB
        C1[**Logical Plan**<br/>Parsed from SQL]
        C2[**Analyzed Logical Plan**<br/>Resolved with metadata]
        C3[**Optimized Logical Plan**<br/>Catalyst rules: predicate pushdown, column pruning]
        C4[**Physical Plan**<br/>Operators decided: HashAggregate / SortMergeJoin]

        C1 --> C2 --> C3 --> C4
    end

    B --> C1
    C4 --> X[**DAG of Transformations**<br/>RDD Lineage]

    X -.-> Y[Ac]

    %% === Color classes ===
    classDef user fill:#fce5ff,stroke:#666,stroke-width:1px;
    classDef context fill:#e6f0ff,stroke:#666,stroke-width:1px;
    classDef logical fill:#e6f0ff,stroke:#333,stroke-width:1px;
    classDef analyzed fill:#d9f0ff,stroke:#333,stroke-width:1px;
    classDef optimized fill:#e6ffe6,stroke:#333,stroke-width:1px;
    classDef physical fill:#fff2cc,stroke:#333,stroke-width:1px;
    classDef dag fill:#fff2cc,stroke:#666,stroke-width:1px;

    %% Assign styles
    class A user;
    class B context;
    class C1 logical;
    class C2 analyzed;
    class C3 optimized;
    class C4 physical;
    class X dag;

    %% Make Action node black & white
    style Y fill:#ffffff,stroke:#000000,stroke-width:1px;
```

```mermaid
flowchart LR
    Z[**User SQL**<br/>Example:<br/>SELECT city, count all<br/>FROM people<br/>WHERE age > 18<br/>GROUP BY city] --> A[**Logical Plan**<br/>Parsed from SQL<br/>Not yet resolved]

    subgraph Catalyst[**Catalyst Optimizer**]
        A --> B[**Analyzed Logical Plan**<br/>Resolved with metadata<br/>e.g., check schema, validate columns]
        B --> C[**Optimized Logical Plan**<br/>Catalyst rules applied<br/>e.g., predicate pushdown, column pruning]
        C --> D[**Physical Plan**<br/>Choose execution operators<br/>e.g., HashAggregate vs SortMergeJoin]
    end

    classDef user fill:#ffffff,stroke:#000000,stroke-width:1px;
    classDef logical fill:#e6f0ff,stroke:#333,stroke-width:1px;
    classDef analyzed fill:#d9f0ff,stroke:#333,stroke-width:1px;
    classDef optimized fill:#e6ffe6,stroke:#333,stroke-width:1px;
    classDef physical fill:#fff2cc,stroke:#333,stroke-width:1px;

    class Z user;
    class A logical;
    class B analyzed;
    class C optimized;
    class D physical;
```

1. **User Program (DataFrame / SQL / RDD)**

   * The developer writes Spark code using DataFrames, SQL, or RDD APIs.

2. **SparkSession**

   * Entry point of Spark. <mark>**Translates**</mark> user code into Spark’s internal representations.
   * SparkSession is the <mark>**bridge**</mark> between the **user world (DataFrame / SQL / RDD APIs)** and **Spark’s internal world (Plans / DAGs / Tasks)**.

3. **Catalyst Optimizer (Logical → Physical Plan)**

   * Spark uses Catalyst to optimize SQL/DataFrame queries.
   * It creates a **Logical Plan**, applies optimization rules, and produces a **Physical Plan**, 

4. **DAG of Transformations (RDD DAG - RDD Lineage is Lineage Graph)**

   * From the physical plan, Spark builds a **Directed Acyclic Graph (DAG)** of transformations.
   * The DAG represents dependencies between RDDs.  for example: **map → filter → join**

5. Lazy Execution until Action

   * Transformations are only recorded.
   * Nothing runs until an Action (e.g., collect, count, save) is triggered.

<details>
<summary><strong>Spark Code - Lazy Execution until Action</strong></summary>

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import length, col

# ✅ Step 0 — Create a SparkSession (Unified entry point in Spark 3.3+)
spark = SparkSession.builder \
    .appName("SparkLazyEvaluationDemo") \
    .master("local[*]") \
    .getOrCreate()

# ✅ Step 1 — Create initial DataFrame (Lazy; logical plan only, not executed yet)
df = spark.createDataFrame(
    [("Spark is fast",), ("Big data",), ("Spark powers analytics",)],
    ["value"]
)
# Conceptual content of df (Spark has not executed anything yet):
# +-------------------------+
# | value                   |
# +-------------------------+
# | Spark is fast           |
# | Big data                |
# | Spark powers analytics  |
# +-------------------------+

# ✅ Step 2 — Apply transformations (Still lazy; no execution yet)
df2 = df.filter(col("value").contains("Spark")) \
        .withColumn("length", length(col("value")))
# Conceptual content of df2 (still lazy, not executed yet):
# +-------------------------+--------+
# | value                   | length |
# +-------------------------+--------+
# | Spark is fast           | 14     |
# | Spark powers analytics  | 24     |
# +-------------------------+--------+

# ✅ Step 3 — Action: show() triggers actual execution
df2.show()

# ✅ Step 4 — Stop SparkSession
spark.stop()
```

```python
from pyspark import SparkContext

sc = SparkContext("local", "LazyEvaluationExample")

# Step 1: Create an RDD (Lazy - no computation yet)
rdd = sc.parallelize(["Spark is fast", "Big data", "Spark powers analytics"])
# RDD content (conceptually): ["Spark is fast", "Big data", "Spark powers analytics"]

# Step 2: Transformation: filter (Lazy)
filtered_rdd = rdd.filter(lambda line: "Spark" in line)
# Conceptual result (not executed yet): ["Spark is fast", "Spark powers analytics"]

# Step 3: Transformation: map (Lazy)
mapped_rdd = filtered_rdd.map(lambda line: (line, len(line)))
# Conceptual result (not executed yet):
# [
#   ("Spark is fast", 14),
#   ("Spark powers analytics", 24)
# ]

# Step 4: Action: collect() (Triggers execution, returns actual results)
result = mapped_rdd.collect()
# Actual result after execution:
# [
#   ("Spark is fast", 14),
#   ("Spark powers analytics", 24)
# ]
print(result)
sc.stop()
```

</details>
    
> In Spark, transformations like **filter** and **map are lazy** — they are only recorded in the DAG and not executed immediately.  
> Actual execution happens only when an action like collect is triggered.
In this example, the **RDD chain is built in steps 1-3**, but **Spark only runs them at step 4**.
     
### 2️⃣ Run Phase : DAG Execution → Driver Result

```mermaid
flowchart LR
    A[**Action**<br>collect / count / save] --> B[**DAGScheduler**<br>DAG → Stages]
    B --> C[**Stage**<br>split into Tasks]
    C --> D[**TaskScheduler**<br>Tasks → Executors]
    D --> E[**Driver**<br>collects Results]

    %% === Color classes ===
    classDef action fill:#ffd580,stroke:#333,stroke-width:2px;
    classDef dag fill:#bbf,stroke:#333,stroke-width:2px;
    classDef stage fill:#bfb,stroke:#333,stroke-width:2px;
    classDef scheduler fill:#ffb3b3,stroke:#333,stroke-width:2px;
    classDef driver fill:#d5b3ff,stroke:#333,stroke-width:2px;

    %% === Assign classes ===
    class A action;
    class B dag;
    class C stage;
    class D scheduler;
    class E driver;
```

```mermaid
flowchart LR
    A[**Action**<br/>collect, count, save] 
      --> B[**DAGScheduler**<br/>Build Scheduling DAG<br/>Split by shuffle boundaries]
    B --> C[**Stages**<br/>Example:<br/>Stage 1 → Scan and Filter<br/>Stage 2 → Shuffle and Aggregate]
    C --> D[**Tasks**<br/>Each stage has many tasks<br/>One task corresponds to one partition]
    D --> E[**TaskScheduler**<br/>Assign tasks to Executors<br/>Handle retries and locality]
    E --> F[**Driver**<br/>Coordinate execution<br/>Return results to user]

    %% === Color classes ===
    classDef action fill:#ffd580,stroke:#333,stroke-width:2px;
    classDef dag fill:#bbf,stroke:#333,stroke-width:2px;
    classDef stage fill:#bfb,stroke:#333,stroke-width:2px;
    classDef tasks fill:#fce5ff,stroke:#333,stroke-width:2px;
    classDef scheduler fill:#ffb3b3,stroke:#333,stroke-width:2px;
    classDef driver fill:#d5b3ff,stroke:#333,stroke-width:2px;

    %% === Assign classes ===
    class A action;
    class B dag;
    class C stage;
    class D tasks;
    class E scheduler;
    class F driver;
```

> Responsible for: actually executing the tasks and running the DAG.
> Keywords: Action → DAGScheduler → Stages → TaskScheduler → Executors → Driver.

1. **Action (collect / count / save)**

   * When an action is triggered, Spark executes the DAG to actually process the data.
   * Until an action is called, transformations remain **lazy**.

2. **DAGScheduler (DAG → Stages)** <mark>Scheduling DAG</mark> – the actual execution graph of computation tasks.

   * Splits the DAG into **Stages** based on shuffle boundaries.
   * Each stage contains a set of tasks that can run in parallel.

3. **Stage (split into Tasks)**

   * A stage is further divided into multiple **Tasks**, one per partition.

4. **TaskScheduler (Tasks → Executors)**

   * The TaskScheduler assigns tasks to worker nodes (Executors).
   * Handles task retries and scheduling policies.

5. **Driver (collects Results)**

   * The Driver program coordinates execution.
   * Collects results from Executors and returns them to the user program.


> 1. The **<mark>DAG</mark>** is only executed when you call an **<mark>action</mark>** (e.g., `collect`, `count`, `save`).  
> 2. At this point, the **<mark>DAGScheduler</mark>** converts the **<mark>logical DAG</mark>** into a **<mark>DAG of stages</mark>**.  
> 3. Each **<mark>stage</mark>** is then further divided into multiple **<mark>tasks</mark>**.  
> 4. The **<mark>TaskScheduler</mark>** is responsible for **<mark>scheduling</mark>** these **<mark>tasks</mark>** to **<mark>executors</mark>** and **<mark>monitoring</mark>** their execution.  

<div align="center">
  <img src="docs/spark-shuffle-kl-1.jpg" alt="Diagram" width="800">
</div>

<details>
<summary><strong>SparkSession</strong></summary>

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

</details>

---

## 🟨 2. Execution Model

### 2.1 📌 **<mark>Job → Stage → Task</mark>**

| No. | Question | Summary |
| --- | --- | --- |
| 7 | What is a Spark job? | Triggered by action ("collect, take(n), saveAsTextFile(path), show..DF"), Spark creates a job - **<mark>consists of stages</mark>**, |
| 8 | What is a stage in Spark? | a set of parallel **tasks** that execute the same computation on different **partitions of the data**. <br> **<mark>A set of tasks</mark>** between shuffles. |
| 9 | What is a task? | **<mark>Unit of execution</mark>** on a partition. |

Stage division： Spark splits the DAG into stages at shuffle operations (like reduceByKey, groupBy, join).

```mermaid
flowchart TD
    %% Action & Job
    A["Action<br>(e.g. collect())"]
    A --> Job["Spark Job"]

    %% Stages
    Job --> Stage0["Stage 0<br>Shuffle Map Stage"]
    Stage0 --> Stage1["Stage 1<br>Reduce Stage"]

    %% ===== Map0: Sort-based Shuffle 子图 =====
    subgraph SB0["Map Task 0 — Sort Shuffle (per-map: single data file + index)"]
        direction TB
        T1["Shuffle Map Task<br>Partition 0"]
        T1 --> SF1["Shuffle File (Map0.data + Map0.index)"]
    end

    %% ===== Map1: Sort-based Shuffle 子图 =====
    subgraph SB1["Map Task 1 — Sort Shuffle (per-map: single data file + index)"]
        direction TB
        T2["Shuffle Map Task<br>Partition 1"]
        T2 --> SF2["Shuffle File (Map1.data + Map1.index)"]
    end

    %% ===== Map2: Sort-based Shuffle 子图 =====
    subgraph SB2["Map Task 2 — Sort Shuffle (per-map: single data file + index)"]
        direction TB
        T3["Shuffle Map Task<br>Partition 2"]
        T3 --> SF3["Shuffle File (Map2.data + Map2.index)"]
    end

    %% Stage0 指向各 Map 任务（在子图内）
    Stage0 --> T1
    Stage0 --> T2
    Stage0 --> T3

    %% AQE 节点 (黄色虚线框，Stage1 reduce task 调整)
    subgraph AQE["AQE Re-Planning<br>(Coalesce / Skew Split / Join Strategy)"]
        direction TB
        AQE_T["Adjust Reduce Tasks"]
    end
    SF1 -.-> AQE
    SF2 -.-> AQE
    SF3 -.-> AQE
    AQE -.-> Stage1

    %% Stage1 Reduce Tasks (调整后)
    Stage1 --> T4["Reduce Task<br>Partition A"]
    Stage1 --> T5["Reduce Task<br>Partition B"]

    %% 在 Reduce Task 右侧加注释（非流程节点）
    subgraph G1[ ]
      direction LR
      T4 -. note .- NoteT4["Note: reads its slice<br/>from all map shuffle files → aggregate"]
    end
    subgraph G2[ ]
      direction LR
      T5 -. note .- NoteT5["Note: reads its slice<br/>from all map shuffle files → aggregate"]
    end

    %% Stage颜色
    style Stage0 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Stage1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

    %% Task颜色
    style T1 fill:#fffde7,stroke:#f57f17
    style T2 fill:#fffde7,stroke:#f57f17
    style T3 fill:#fffde7,stroke:#f57f17
    style T4 fill:#f3e5f5,stroke:#6a1b9a
    style T5 fill:#f3e5f5,stroke:#6a1b9a
    style AQE_T fill:#fff59d,stroke:#fbc02d,stroke-dasharray:5 5,stroke-width:2px

    %% Shuffle 文件颜色
    style SF1 fill:#e0e0e0,stroke:#9e9e9e
    style SF2 fill:#e0e0e0,stroke:#9e9e9e
    style SF3 fill:#e0e0e0,stroke:#9e9e9e

    %% Note颜色
    style NoteT4 fill:#fafafa,stroke:#bdbdbd,stroke-dasharray: 2 2
    style NoteT5 fill:#fafafa,stroke:#bdbdbd,stroke-dasharray: 2 2

    %% Action & Job 颜色
    style A fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px
    style Job fill:#bbdefb,stroke:#1565c0,stroke-width:2px
```

| No. | Question | Summary |
| --- | --- | --- |
| Stage0 | contains narrow transformations (e.g. `map`, `filter`) **and writes shuffle output if followed by a wide transformation** | 👉 Divided into multiple **Tasks**, each processing **one input partition** (e.g. Partition 0, 1, 2), executing all narrow transformations **in parallel**. Shuffle files are written if needed for Stage1. |
| Stage1 | begins **after Stage 0 completes**, involves **wide transformations** (e.g. `reduceByKey`)                                | 👉 Divided into **Tasks** operating on **shuffled partitions** (e.g. Partition A, B). Tasks run **in parallel**, and once Stage 1 completes, the **final result** is returned to the **Driver**.            |

> Wide Dependency : A parent partition may be used by multiple child partitions.

```mermaid
flowchart LR
    subgraph Static[Without AQE: Static Mode]
        direction TB
        A1[Input Data<br/>30 partitions]
        A2[Shuffle Stage<br/>spark.sql.shuffle.partitions = 20<br/>Fixed number of partitions]
        A3[Output Data<br/>20 partitions]
        A1 --> A2 --> A3
    end

    subgraph Adaptive[With AQE: Adaptive Mode]
        direction TB
        B1[Input Data<br/>30 partitions]
        B2[Shuffle Stage<br/>Initial value = 20<br/>AQE adjusts at runtime]
        B3[Output Data<br/>Dynamic partitions<br/>e.g., 10 partitions if data is small<br/>or 40 if data is large]
        B1 --> B2 --> B3
    end

    Static --> Adaptive
```

### 2.2 Spark Component

| No. | Component       | What It Does |
| --- |-----------------|-------------|
| 1 | Client | Acts as the client on the user’s behalf, responsible for submitting applications.
| 2 | **Driver**      | Runs your main application code (`main()`), creates the `SparkContext` <br> Responsible for the scheduling of jobs, i.e., the distribution of tasks. Think of it as the “orchestrator” of your Spark job. |
| 3 | **Worker**      | A machine/node in the cluster that runs executors. It follows the driver’s instructions and reports back its status. |
| 4 | **Executor**    | Runs the actual tasks on a worker node. Each executor has a pool of threads to process multiple tasks in parallel. |
| 5 | **Cluster Manager** | Controls the cluster (like the “master controller”). In Standalone mode, it launches workers, monitors them, and helps schedule jobs. |

<div align="center">
  <img src="docs/spark-introduce-03.jpeg" alt="Diagram" width="600">
</div>

<details>
<summary><strong>Spark App Process</strong></summary>

```mermaid
flowchart TD
    A["Client<br/>spark-submit or Notebook"] --> B["Cluster Manager<br/>Standalone / YARN / K8s"]
    B --> C["Driver<br/>Parse code + SparkContext"]
    C --> D["Logical Plan<br/>RDD/DataFrame Lineage"]
    D --> E["DAGScheduler<br/>Split into Stages at shuffle"]
    E --> F["TaskScheduler<br/>Assign Tasks to Executors"]
    F --> G["Executors<br/>Execute Tasks<br/>Map writes / Reduce fetches"]
    G --> H["Driver Monitor<br/>Track status, retry, return result"]
```

| Step | Keyword / Component              | Description |
|------|----------------------------------|-------------|
| 1    | <mark>**Client Application Submit**</mark>  | User submits the application via <mark>**spark-submit / Notebook**</mark>. |
| 2    | <mark>**Cluster Manager Allocation**</mark> | <mark>**Standalone / YARN / K8s**</mark> allocates resources and launches the Driver. |
| 3    | <mark>**Driver and SparkContext**</mark>    | Driver starts, creates <mark>**SparkContext**</mark>, and parses the user program. |
| 4    | <mark>**DAG of Transformations**</mark>     | User-defined operations (map, filter, join, etc.) are recorded lazily as <mark>**lineage**</mark>. |
| 5    | <mark>**Action Trigger Execution**</mark>   | An <mark>**action**</mark> (collect, count, save) triggers execution of the DAG. |
| 6    | <mark>**DAGScheduler Planning**</mark>      | Converts the transformations DAG into a <mark>**DAG of Stages**</mark>, splitting at <mark>**shuffle boundaries**</mark>. |
| 7    | <mark>**TaskScheduler Dispatch**</mark>     | Breaks each stage into multiple <mark>**tasks**</mark> (by partition) and schedules them on <mark>**Executors**</mark>. |
| 8    | <mark>**Executors Execution**</mark>        | Executors run <mark>**tasks**</mark>, perform <mark>**shuffle read/write**</mark>, and return results. |
| 9    | <mark>**Driver Monitoring & Result**</mark> | Driver monitors <mark>**task execution**</mark>, retries failures, aggregates results, and returns the final <mark>**output**</mark> to the user or storage. |

</details>
  
## 🟧 3. Shuffle & Partitioning

📌 **Shuffle = Costly, Wide vs Narrow**

| # | Question | Summary |
| --- | --- | --- |
| 10 | What is a shuffle in Spark? | Data redistribution across partitions. Data **<mark>redistribution across partitions</mark>**, which may involve moving data between **<mark>Executors (nodes)</mark>** over the **<mark>network</mark>**.  <br><br> This makes it an **<mark>expensive operation</mark>** due to **<mark>disk I/O</mark>**, **<mark>network transfer</mark>**, and **<mark>serialization</mark>**. |
| 11 | Why is shuffle expensive? | Disk I/O + network + serialization. |
| 12 | What is the difference between narrow and wide transformations? | Narrow = no shuffle, Wide = shuffle needed. |

```mermaid
flowchart TD
    subgraph Driver[Driver Program]
        D1[Driver<br/>Coordinates execution<br/>Schedules stages and tasks]
    end

    D1 --> W1
    D1 --> W2

    %% Worker Node A
    subgraph W1[Worker Node A]
        direction TB
        E1[Executor 1<br/>JVM Process]
        subgraph T1[Tasks in Executor 1]
            direction TB
            T1a[Task 1<br/>Partition 0]
            T1b[Task 2<br/>Partition 1]
        end
    end

    %% Worker Node B
    subgraph W2[Worker Node B]
        direction TB
        E2[Executor 2<br/>JVM Process]
        subgraph T2[Tasks in Executor 2]
            direction TB
            T2a[Task 3<br/>Partition 2]
            T2b[Task 4<br/>Partition 3]
        end

        E3[Executor 3<br/>JVM Process]
        subgraph T3[Tasks in Executor 3]
            direction TB
            T3a[Task 5<br/>Partition 4]
            T3b[Task 6<br/>Partition 5]
        end
    end
```

```mermaid
flowchart LR
    subgraph Node1[Node 1 - Executor A]
        M1[Map Task 1]
        M2[Map Task 2]
        SW1[Shuffle Write]
    end

    subgraph Node2[Node 2 - Executor B]
        M3[Map Task 3]
        SW2[Shuffle Write]
    end

    subgraph Node3[Node 3 - Executor C]
        SR1[Shuffle Read]
        R1[Reduce Task 1]
    end

    subgraph Node4[Node 4 - Executor D]
        SR2[Shuffle Read]
        R2[Reduce Task 2]
    end

    %% Map → Shuffle Write
    M1 --> SW1
    M2 --> SW1
    M3 --> SW2

    %% Shuffle Write → Shuffle Read (跨节点传输)
    SW1 -- network transfer --> SR1
    SW1 -- network transfer --> SR2
    SW2 -- network transfer --> SR1
    SW2 -- network transfer --> SR2

    %% Shuffle Read → Reduce
    SR1 --> R1
    SR2 --> R2
```

### ✅ Now the flow explains - Serialization :

```mermaid
flowchart LR
    A[In-memory Objects<br/>Rows and Records] 
        --> B[Serialization<br/>Convert objects to bytes<br/>Examples: Java, Kryo, Tungsten]
    B --> C[Network and Disk IO<br/>Shuffle write and transfer<br/>Data stored as bytes]
    C --> D[Deserialization<br/>Convert bytes back to objects<br/>Rebuild JVM objects]
    D --> E[In-memory Objects<br/>Used by next stage tasks]

    %% Style
    classDef obj fill:#e6f0ff,stroke:#333,stroke-width:1px;
    classDef ser fill:#ffe6cc,stroke:#333,stroke-width:1px;
    classDef io fill:#fff2cc,stroke:#333,stroke-width:1px;
    classDef deser fill:#ffe6f0,stroke:#333,stroke-width:1px;

    class A obj;
    class B ser;
    class C io;
    class D deser;
    class E obj;
```

1. **In-memory Objects** → JVM data structures (rows, records).
2. **Serialization** → Converts objects into bytes, using **Java serialization, Kryo, or Tungsten UnsafeRow**.
3. **Network and Disk IO** → Bytes written to shuffle files and transferred across Executors.
4. **Deserialization** → Bytes converted back into JVM objects.
5. **In-memory Objects** → Data ready for the next stage’s tasks.

<details>
<summary><strong>Narrow vs Wide Dependency</strong></summary>

<div align="center">
  <img src="docs/spark-wide-dependency.webp" alt="Diagram" width="500">
</div>

| No. | ❓Question   | ✅ Answer| 📘 Notes                                                                                                    
| --- | --- | --- | --- |
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

    Note1["💡 Shuffle involves:<br>• Disk I/O<br>• Network<br>• Serialization<br><br>❗ The number of partitions may change."]
    ShuffleStage -.-> Note1

    %% Styling
    style InputPartitions fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style NarrowTransformation fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style WideTransformation fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style ShuffleStage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style Note1 fill:#fffde7,stroke:#fbc02d,stroke-width:2px,stroke-dasharray: 5 5
```

🔁 Task Count Comparison

| Stage   | Task Type | Count | Description 
| --- | --- | --- | --- |
| **Stage 1** | **Shuffle Map Tasks** | **3** | One task per input partition (P0–P2). Each task executes all narrow transformations (map/flatMap/…) in a pipeline, then buckets records by key and writes **2 shuffle outputs** (for partitions A and B). |
| **Stage 2** | **Reduce Tasks**      | **2** | One task per output partition (A, B). **Each reduce task fetches its partition’s blocks from all 3 shuffle map tasks** (one block per map task), then merges/aggregates to produce the final result.      |

## 4. Data Skew（skewness)

🔥 Data Skew in Spark - *Unbalanced data across partitions*

| Category  | Optimization Methods | Notes / Best Practices                       
| --- | --- | --- | 
| 1️⃣ Skewed Input Files         | Repartitioning, **<mark>Merging small files</mark>**, Using columnar file formats (Parquet/ORC), Increasing `spark.sql.files.maxPartitionBytes` <br> `spark.sql.files.openCostInBytes` | Avoid too many small files that lead to excessive tasks or file handle pressure; control partition sizes appropriately                               |
| 2️⃣ Skewed Join Keys           | Broadcast Join, **<mark>Salting, Adaptive Query Execution (AQE)</mark>**, Map-side join               | For highly skewed join keys, AQE can split large partitions at runtime or broadcast small tables to reduce shuffle                                   |
| 3️⃣ Skewed Aggregation         | **<mark>Salting + Two-stage aggregation, AQE coalesce partitions</mark>**                             | For uneven key distributions in aggregations, pre-salt to scatter keys, then aggregate and remove salt; AQE can automatically split large partitions |
| 4️⃣ General Tuning & SQL Hints | SQL hints (e.g., `/*+ BROADCAST */`), Repartitioning, AQE (coalesce & skew join), Cache/Checkpoint    | Overall performance tuning: use hints to guide joins/partitions, cache hotspot data appropriately, adjust parallelism                                |

| # | Question | Summary |
| --- | --- | --- |
| 13 | **What is data skew?** | **<mark>Unbalanced data across partitions</mark>**. <br> It often occurs when a few keys have significantly more records than others.  <br> This leads to some tasks running much longer than others, causing **performance bottlenecks** and **OOM errors**.|
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

| AQE  —  Functions    | What It Does - (Adaptive Query Execution)   |    Benefit      |
| ------------------------ | --------------------------- | ---------------- |
| **1. Dynamically coalesce shuffle partitions** | Merges many small shuffle partitions into fewer larger ones at runtime                                      | Reduces empty tasks, lowers scheduling overhead   |
| **2. Handle skewed joins (skew split)**        | Detects skewed partitions (hot keys) and splits them into multiple tasks   <br> It will add a <mark>final aggregation step</mark> to merge the intermediate results. <br><br> “AQE can automatically **split a large partition into multiple tasks**, so it works well when the partition contains multiple keys. But if a partition is dominated by a single extreme hot key, AQE can only slice the file, not rebalance the key itself. **The key still ends up as one group**, so the fundamental skew problem remains. That’s why in extreme skew cases, we still need manual techniques like salting.”     | Avoids long-tail stragglers, improves parallelism |
| **3. Switch join strategies at runtime**       | Can change SortMergeJoin → BroadcastHashJoin (or others) if actual stats differ from estimates              | Better performance, avoids unnecessary shuffles   |
| **4. Improve overall robustness**              | Uses *runtime statistics* (row count, size, distribution) instead of relying only on compile-time estimates | More stable performance even with bad statistics  |

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
| ------------------------ | ----------------------------- | ----------------------------- |
| **Optimization timing**  | After shuffle (runtime) <br> **With AQE enabled**, spark.sql.shuffle.partitions is used only as an **<mark>initial value / upper bound</mark>** for the shuffle partitions. AQE will dynamically merge or split them at runtime.                | Before shuffle (logical rewrite)                 |
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

| Aspect  | Spark (Closest Feature)        | MapReduce (MR)   |
|---------------------|-----------------------------|----------------------------|
| **Execution Model** | **<mark>DAG of stages</mark>**; in-memory, **<mark>pipelined execution</mark>** | Two fixed stages: Map → Reduce; disk-based    |
| **Shuffle**         | Sort-based Shuffle with optimizations (AQE, push-based, bypass merge) | Always disk + full sort, heavy I/O            |
| **Intermediate Data** | Cached in memory (spill to disk only if needed) | Written to disk every stage                 |
| **Fault Tolerance** | RDD lineage recomputes only lost partitions  | Restart tasks using on-disk data

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
