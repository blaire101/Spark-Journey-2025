# PySpark Hello

📌 **RDD, DataFrame, Lazy |  fault** /fɔːlt/ **tolerance** /ˈtɒlərəns/ **mechanisms** /ˈmekənɪzəmz/

- spark concepts & pyspark sample
    

    ```sql
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, lit
    
    def main():
        # Step 1: Initialize SparkSession
        spark = SparkSession.builder \
            .appName("CityCountWithDataFrame") \
            .getOrCreate()
        # Step 2: Read the text file into a DataFrame
        # Each line in the file is a single city name
        input_path = "hdfs://path/to/cities.txt"  # or "file:///your/local/path.txt"
        df = spark.read.text(input_path).withColumnRenamed("value", "city")
        # Step 3: Add a 'count' column with constant value 1
        df_with_count = df.withColumn("count", lit(1))
        # Step 4: Group by city and count total occurrences
        city_counts = df_with_count.groupBy("city").sum("count") \
            .withColumnRenamed("sum(count)", "total")
        # Step 5: Show result
        print("=== PySpark DataFrame result ===")
        city_counts.orderBy("city").show(truncate=False)
        # Step 6: Stop SparkSession
        spark.stop()
    
    if __name__ == "__main__":
        main()
    """
      === PySpark DataFrame result ===
    	+-------------+-----+
    	|city         |total|
    	+-------------+-----+
    	|Kuala Lumpur |2    |
    	|Shanghai     |2    |
    	|Singapore    |3    |
    	+-------------+-----+
    """
    ```
    

### 2.1  pyspark quick start

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder.getOrCreate()
df = spark.createDataFrame([(1, 10), (2, 20), (3, 30)], ["id", "value"])
df.show()
"""
+---+-----+
| id|value|
+---+-----+
|  1|   10|
|  2|   20|
|  3|   30|
+---+-----+
"""
# agg, sum
df.agg({"value": "sum"}).show()
+----------+
|sum(value)|
+----------+
|        60|
+----------+
# Its purpose is:
# ✅ It triggers Spark’s computation and retrieves the distributed data to the driver.
# ✅ It returns a list of Row objects, so you can access the data using standard Python syntax.
max_value1 = df.agg({"value": "max"}).collect() # [Row(max(value)=30)]
+----------+
|max(value)|
+----------+
|        30|
+----------+
max_value = max_value1[0]["max(value)"]
print(max_value)  #  30

df.groupBy("id").sum("value").show()
+---+----------+
| id|sum(value)|
+---+----------+
|  1|        10|
|  2|        20|
|  3|        30|
+---+----------+
```

---

### **2.2 PySpark Interview**

| 问题 | 答案简述 |
| --- | --- |
| Spark Core | Driver，Executor，Cluster Manager，RDD，DataFrame，Dataset |
| RDD vs DataFrame vs Dataset  | **RDD**: Low-level API, no schema. **DataFrame**: Has schema, structured.**Dataset**: Strongly-typed collection (only available in Java/Scala). |
| Transformation vs Action | Transformation lazy（map, filter），Action  triggers computation（count, show, collect） |
| broadcast join | Broadcast the small table to each executor to avoid shuffling the large table and reduce network I/O. |
| lineage | **RDD’s lineage information is used for fault tolerance  by recomputing lost data.      fault tolerance /fɔːlt ˈtɒlərəns** |
| Spark job ？ | （repartition/coalesce），（persist），broadcast join， partition key |
| window function |  `from pyspark.sql.window import Window`，定义 windowSpec，配合函数（如 row_number） |
| Catalyst Optimiser |  The `query optimizer of Spark SQL` automatically generates efficient execution plans |
| How to use UDF？ | `from pyspark.sql.functions import udf`  |
|  |  |

### 2.3 PySpark Jupyter Notebook

### 🔹  SparkSession

```python
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName("PySpark Basic Tutorial") \
    .getOrCreate()
```

---

### 🔹  DataFrame

```python
data = [
    ("A", 10, 1),
    ("B", 20, 2),
    ("A", 30, 3),
    ("B", 40, 4),
    ("A", 50, 5)
]
columns = ["Category", "Value1", "Value2"]

df = spark.createDataFrame(data, columns)
df.show()
+--------+------+------+
|Category|Value1|Value2|
+--------+------+------+
|       A|    10|     1|
|       B|    20|     2|
|       A|    30|     3|
|       B|    40|     4|
|       A|    50|     5|
+--------+------+------+
```

---

### 🔹 groupBy + sum, filter, select + withColumn

```python
df.groupBy("Category").sum().show()
+--------+---------+---------+
|Category|sum(Value1)|sum(Value2)|
+--------+---------+---------+
|       A|       90|        9|
|       B|       60|        6|
+--------+---------+---------+
# filter
df.filter(df.Value1 > 20).show()
+--------+------+------+
|Category|Value1|Value2|
+--------+------+------+
|       A|    30|     3|
|       B|    40|     4|
|       A|    50|     5|
+--------+------+------+
# select + withColumn
from pyspark.sql.functions import col
df.withColumn("Value3", col("Value1") + col("Value2")).show()
```

---

### 2.4 UDF 7 Steps

In PySpark, a UDF (User-Defined Function) is typically applied to a **column** of a DataFrame.

`check_udf = udf(function-, IntegerType())`

```python
**# 1. Import necessary libraries**
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType
# **2. Create Spark session**
spark = SparkSession.builder.appName("UDF Example").getOrCreate()
# **3. Prepare sample DataFrame**
data = [("hello",), ("world",), ("example",), ("common",)]
df = spark.createDataFrame(data, ["before_checking"])
df.show()
"""
+----------------+
|before_checking|
+----------------+
|           hello|
|           world|
|         example|
|          common|
+----------------+
"""
# 4. **Define Python function for UDF**
def check(col, common_words):
    if col in common_words:
        return 1
    else:
        return 0
# **5. Prepare predefined list**
common_words = ["hello", "common"]
# **6. Register the UDF**
my_udf = udf(lambda col: check(col, common_words), IntegerType())
# Not using lambda (clearer)
# def check_wrapper(col):
#    return check(col, common_words)
# my_udf = udf(check_wrapper, IntegerType())

# **7. Apply the UDF using withColumn**
df = df.withColumn("after_checking", my_udf(df["before_checking"]))
df.show()
"""
+----------------+---------------+
|before_checking |after_checking|
+----------------+---------------+
|           hello|              1|
|           world|              0|
|         example|              0|
|          common|              1|
+----------------+---------------+
"""
```

### 🔹  SQL

```python
df.createOrReplaceTempView("my_table")
spark.sql("SELECT Category, SUM(Value1) as total_value1 FROM my_table GROUP BY Category").show()

# Explain
df.groupBy("Category").sum().explain()
```

---


### **3. Find Tuples Matching a Sum Condition in Python**

### **Problem Statement:**

Given four lists `A`, `B`, `C`, and `D`, find the number of tuples `(i, j, k, l)` such that:

\[
A[i] + B[j] + C[k] = D[l]
\]

---

### **Approach:**

1. Precompute the sums of pairs from lists `A` and `B`, storing them in a dictionary `sum_AB`.
2. Iterate through pairs from lists `C` and `D`, checking if `D[l] - C[k]` exists in `sum_AB`.
3. Count matches based on occurrences stored in `sum_AB`.

---

```python
# Example lists
A = [1, 2, 3, 4]
B = [2, 4, 5, 6]
C = [1, 3, 4, 9]
D = [7, 4, 9, 10]

# Precompute sums from A and B
sum_AB = {}
for i in range(len(A)):
    for j in range(len(B)):
        s = A[i] + B[j]
        if s not in sum_AB:
            sum_AB[s] = 0
        sum_AB[s] += 1

# Count matching tuples
count = 0
for i in range(len(C)):
    for j in range(len(D)):
        target = D[j] - C[i]
        if target in sum_AB:
            count += sum_AB[target]

print(f"Number of tuples: {count}")

```

### 4. PySpark UDF for Column Matching Check

### **Problem Statement:**

Given a PySpark DataFrame `df` with a column `before_checking`, use a UDF to check if each value exists in a predefined list `common_words`. Add a new column `after_checking` that contains `1` if the word exists and `0` otherwise.

---

### **Approach:  3 steps**

1. Define a Python function `check` that checks if a word exists in `common_words`.
2. Register this function as a PySpark UDF.
3. Use `withColumn` to create a new column `after_checking` based on the UDF.

---

```python
# Import necessary libraries
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

# Initialize Spark session
spark = SparkSession.builder.appName("UDF Example").getOrCreate()

# Sample DataFrame
data = [("hello",), ("world",), ("example",), ("common",)]
df = spark.createDataFrame(data, ["before_checking"])
# 1. df data sample， Output after creating initial DataFrame
+----------------+
|before_checking |
+----------------+
|hello           |
|world           |
|example         |
|common          |
+----------------+

# 2. Example list of common words
common_words = ["hello", "common"]

# 3. Register UDF - User Defined Function
"""
In PySpark, a UDF (User Defined Function) refers to a custom function defined by the user. It allows you to apply a Python function to each row of a DataFrame—similar to how apply works in Pandas—and use the result to create a new column.

UDFs are especially useful when you need custom logic that cannot be easily achieved using Spark's built-in functions.
"""
# Define function for matching check
def check(col, common_words):
    if col in common_words:
        return 1
    else:
        return 0
check_udf = udf(lambda col: check(col, common_words), IntegerType())

# Apply UDF to DataFrame
df = df.withColumn("after_checking", check_udf(df["before_checking"]))
# Output after applying UDF
+----------------+---------------+
|before_checking|after_checking |
+----------------+---------------+
|hello           |1              |
|world           |0              |
|example         |0              |
|common          |1              |
+----------------+---------------+

# Show result
df.show()

```

---

```sql
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

# Basic usage with a regular function 
def double2(x):
    return x * 2

double_udf = udf(double2, IntegerType())

# Concise usage with a lambda function
double_udf = udf(lambda x: x * 2, IntegerType())

# -------------------------------------- #
# ✅ "Concise explanation" = a brief, clear explanation.
# ✅ "Sample code" = a real, working example of code.
```
