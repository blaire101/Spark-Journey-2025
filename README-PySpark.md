# PySpark Notes   

📌 **Core Concepts:** RDD, DataFrame, Lazy Evaluation, Fault Tolerance /fɔːlt/ /ˈtɒlərəns/, Execution Mechanisms /ˈmekənɪzəmz/

---

## 🧭 1. Getting Started with PySpark

### 1.1 Initialize SparkSession
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName("PySpark Basic Tutorial") \
    .getOrCreate()
```

### 1.2 Create a Simple DataFrame
```python
data = [(1, 10), (2, 20), (3, 30)]
df = spark.createDataFrame(data, ["id", "value"])
df.show()
```
```
+---+-----+
| id|value|
+---+-----+
|  1|   10|
|  2|   20|
|  3|   30|
+---+-----+
```

---

## 📊 2. Basic DataFrame Operations

### 2.1 Aggregations
```python
# Total Sum
df.agg({"value": "sum"}).show()

# Maximum value with collect()
max_val = df.agg({"value": "max"}).collect()[0]["max(value)"]
print(max_val)
```

### 2.2 groupBy + sum
```python
df.groupBy("id").sum("value").show()
```
```
+---+----------+
| id|sum(value)|
+---+----------+
|  1|        10|
|  2|        20|
|  3|        30|
+---+----------+
```

### 2.3 filter, select, withColumn
```python
from pyspark.sql.functions import col

# Filter rows
filtered = df.filter(col("value") > 20)
filtered.show()

# Add a new column
df.withColumn("value_doubled", col("value") * 2).show()
```

---

## 📂 3. Read and Aggregate from File

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

def main():
    spark = SparkSession.builder.appName("CityCountWithDataFrame").getOrCreate()
    input_path = "hdfs://path/to/cities.txt"
    df = spark.read.text(input_path).withColumnRenamed("value", "city")
    df = df.withColumn("count", lit(1))
    city_counts = df.groupBy("city").sum("count").withColumnRenamed("sum(count)", "total")
    city_counts.orderBy("city").show(truncate=False)
    spark.stop()

if __name__ == "__main__":
    main()
```
**Output Example:**
```
+-------------+-----+
|city         |total|
+-------------+-----+
|Kuala Lumpur |2    |
|Shanghai     |2    |
|Singapore    |3    |
+-------------+-----+
```

---

## 🧠 4. PySpark UDF (User Defined Function)

### 4.1 Purpose of UDF
- Apply custom Python logic to DataFrame columns.
- Similar to `apply()` in Pandas.

### 4.2 UDF Implementation – Step by Step

🧠 **udf(func_name, XType()), check, withColumn("col\_name", ur\_udf)**

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType
from pyspark.sql import SparkSession

# Step 1: Initialize SparkSession
spark = SparkSession.builder.appName("UDF Example").getOrCreate()

# Step 2: Create sample DataFrame
data = [("hello",), ("world",), ("example",), ("common",)]
df = spark.createDataFrame(data, ["before_checking"])

# Step 3: Define Python function
common_words = ["hello", "common"]
def check(col):
    return 1 if col in common_words else 0

# Step 4: Register as UDF
check_udf = udf(check, IntegerType())

# Step 5: Apply UDF
df = df.withColumn("after_checking", check_udf(df["before_checking"]))

# Step 6: Show result
df.show()
```
**Expected Output:**
```
+----------------+---------------+
|before_checking|after_checking |
+----------------+---------------+
|hello           |1              |
|world           |0              |
|example         |0              |
|common          |1              |
+----------------+---------------+
```

---

## 🔍 5. SQL Integration

```python
df.createOrReplaceTempView("my_table")
spark.sql("SELECT Category, SUM(Value1) as total_value1 FROM my_table GROUP BY Category").show()

# Check query plan
df.groupBy("Category").sum().explain()
```

---

## 🎯 6. PySpark Interview Essentials

| Question | Summary |
|---------|---------|
| Spark Core | Driver, Executor, Cluster Manager, RDD, DataFrame |
| RDD vs DataFrame | RDD: low-level, unstructured. DataFrame: optimized, with schema. |
| Transformation vs Action | Lazy vs Triggers computation (e.g., `count`, `show`) |
| Broadcast Join | Broadcast small table to avoid shuffle |
| Lineage | Enables fault tolerance by recomputing lost partitions |
| Catalyst Optimizer | Optimizes execution plan in Spark SQL |
| Window Function | Requires `Window` spec from `pyspark.sql.window` |
| UDF | Register with `udf()` from `pyspark.sql.functions` |

---

Happy Spark-ing! ⚡

---

```mermaid
---
config:
  layout: dagre
---
flowchart TB
 subgraph Control["Control"]
        DA["Driver Application"]
        SC["SparkContext"]
        RL["RDD Lineage (map→groupBy)"]
        DS["DAG Scheduler"]
        TS["Task Scheduler"]
        CM["Cluster Manager (master)"]
  end
 subgraph Input["Input"]
    direction TB
        P0["Partition 0: Beijing"]
        P1["Partition 1: Shanghai, Harbin"]
        P2["Partition 2: Beijing, Shenzhen, Singapore, Kuala Lumpur"]
  end
 subgraph MapStage["Stage 0: Map + In-Memory Combine"]
    direction TB
        MT0["Map Task 0: Beijing=2"]
        MT1["Map Task 1: Shanghai=1, Harbin=1"]
        MT2["Map Task 2: Beijing=1, Shenzhen=1, Singapore=1, Kuala Lumpur=1"]
  end
 subgraph ExecutorsMap["Executors (Map Stage)"]
    direction LR
        EXA["Executor A (Worker1, 2 cores)"]
        EXB["Executor B (Worker2, 2 cores)"]
  end
 subgraph ShuffleBlock["Shuffle Write & Partitions (5)"]
    direction TB
        SW["Map outputs for 5 partitions
        (in-memory combine; output on local disk)"]
        SP0["0: Beijing"]
        SP1["1: Shanghai"]
        SP2["2: Harbin"]
        SP3["3: Shenzhen"]
        SP4["4: Singapore & Kuala Lumpur"]
        SF["Shuffle Fetch\n(from local disk)"]
  end
 subgraph ReduceStage["Stage 1: Reduce (Fetch + Final)"]
    direction TB
        RT0["Reduce Task 0: Beijing"]
        RT1["Reduce Task 1: Shanghai"]
        RT2["Reduce Task 2: Harbin"]
        RT3["Reduce Task 3: Shenzhen"]
        RT4["Reduce Task 4: Singapore"]
        RT5["Reduce Task 5: Kuala Lumpur"]
  end
 subgraph Assignment["Executors (Reduce Stage)"]
    direction LR
        A1["Executor A runs RT0, RT1, RT2"]
        A2["Executor B runs RT3, RT4, RT5"]
  end
 subgraph OutputFiles["HDFS Output Files (via saveAsTextFile)"]
        OF0["part-00000"]
        OF1["part-00001"]
        OF2["part-00002"]
        OF3["part-00003"]
        OF4["part-00004"]
  end
 subgraph Output["Driver call collect() - Output"]
        FO["Local Array: Beijing=3, Shanghai=1,Harbin=1, Shenzhen=1,Singapore=1, Kuala Lumpur=1"]
  end
    A1 --> OF0 & OF1 & OF2 & FO
    A2 --> OF3 & OF4 & FO
    DA --> SC
    SC --> RL & DS & TS
    TS --> CM
    CM --> P0 & P1 & P2
    P0 --> MT0
    P1 --> MT1
    P2 --> MT2
    MT0 --> EXA & SW
    MT1 --> EXA & SW
    MT2 --> EXB & SW
    SW --> SP0 & SP1 & SP2 & SP3 & SP4
    SP0 --> SF
    SP1 --> SF
    SP2 --> SF
    SP3 --> SF
    SP4 --> SF
    SF --> RT0 & RT1 & RT2 & RT3 & RT4 & RT5
    RT0 --> A1
    RT1 --> A1
    RT2 --> A1
    RT3 --> A2
    RT4 --> A2
    RT5 --> A2
    RL --> CFG["Configs:
    spark.sql.shuffle.partitions=5
    --num-executors=2
    --executor-cores=2
    --executor-memory=4g
    spark.shuffle.compress=true
    spark.shuffle.spill.compress=true"]
    CFG --> Control
    Control --> n1["Untitled Node"]
     DA:::control
     SC:::control
     RL:::control
     DS:::control
     TS:::control
     CM:::control
     P0:::input
     P1:::input
     P2:::input
     MT0:::reduce
     MT1:::reduce
     MT2:::reduce
     EXA:::executor
     EXB:::executor
     SW:::shuffle
     SP0:::shuffle
     SP1:::shuffle
     SP2:::shuffle
     SP3:::shuffle
     SP4:::shuffle
     SF:::shuffle
     RT0:::reduce
     RT1:::reduce
     RT2:::reduce
     RT3:::reduce
     RT4:::reduce
     RT5:::reduce
     A1:::assign
     A2:::assign
     FO:::output
     CFG:::config
    classDef control   fill:#D0E8FF,stroke:#0077CC,stroke-width:1.5px
    classDef input     fill:#E8F7D4,stroke:#3C763D,stroke-width:1.5px
    classDef reduce    fill:#FADBD8,stroke:#CC0000,stroke-width:1.5px
    classDef shuffle   fill:#FFF2CC,stroke:#CCCC00,stroke-width:1.5px
    classDef assign    fill:#D4EEF7,stroke:#007299,stroke-width:1.5px
    classDef output    fill:#F0F0F0,stroke:#666666,stroke-width:1.5px
    classDef config    fill:#FFF7D6,stroke:#CC9900,stroke-width:1.5px
    classDef executor  fill:#D4EEF7,stroke:#005F73,stroke-width:1.5px
```

