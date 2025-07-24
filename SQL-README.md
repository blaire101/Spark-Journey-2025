# SQL Preparation Guide

> In life, you can choose who you want to be; be very careful with that choice.

---

## 📘 SQL Basics

### 1. Query Structure & Clauses
- `FROM`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`
- `WHERE`: `NOT IN`, `NULL`, `<>`
- Aggregate Functions: `AVG()`, `SUM()`, `COUNT()`
- Conditional: `IF`, `IFNULL(expr, val)`, `CASE WHEN`
- NULL Handling: `COALESCE()`
- `DISTINCT`

![sql](docs/sql-1.png)

### 2. Joins & Subqueries
- `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `SELF JOIN`, `CROSS JOIN`

## 🧮 SQL Advanced Aggregation & Window Functions

### 3. Window Function Basics
- `PARTITION BY`, `ORDER BY` in `OVER()` clause
- Ranking: `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`
- Analytics: `SUM()`, `AVG()`, `MIN()`, `MAX()` over windows
- Lag/Lead: `LAG()`, `LEAD()` to access previous/next rows
- First/Last: `FIRST_VALUE()`, `LAST_VALUE()`

#### Example:
```sql
ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date)
LAG(txn_date) OVER (PARTITION BY customer_id ORDER BY txn_date)
```

---

## 🧑‍💻 SQL Classic Use Cases

### 4. Daily Average Spend > 3
```sql
SELECT customer_id, AVG(daily_sum) AS average_spend
FROM (
    SELECT customer_id, txn_date, SUM(txn_amount) AS daily_sum
    FROM transaction
    GROUP BY customer_id, txn_date
) daily_spend
GROUP BY customer_id
HAVING AVG(daily_sum) > 3;
```

### 5. Average Days Between Transactions
```sql
WITH transaction_date AS (
    SELECT customer_id, txn_date,
        LAG(txn_date) OVER (PARTITION BY customer_id ORDER BY txn_date) AS prev_date
    FROM transaction
),
diff_days AS (
    SELECT customer_id, DATEDIFF(txn_date, prev_date) AS gap
    FROM transaction_date
    WHERE prev_date IS NOT NULL
)
SELECT customer_id, AVG(gap) AS avg_gap
FROM diff_days
GROUP BY customer_id;
```

### 6. Top 10 Spenders in Last 30 Days
```sql
SELECT user_id, SUM(amount) AS total_spend
FROM transactions
WHERE tx_time >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY user_id
ORDER BY total_spend DESC
LIMIT 10;
```

### 7. Consecutive 3-Day Logins ✅

```sql
ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date)
```

| user\_id | login\_date | rn | flag\_date |
| -------- | ----------- | -- | ---------- |
| A        | 2025-01-01  | 1  | 2024-12-31 |
| A        | 2025-01-02  | 2  | 2024-12-31 |
| A        | 2025-01-03  | 3  | 2024-12-31 |
| A        | 2025-01-05  | 4  | 2025-01-01 |
| B        | 2025-01-02  | 1  | 2025-01-01 |
| B        | 2025-01-04  | 2  | 2025-01-02 |
| B        | 2025-01-05  | 3  | 2025-01-03 |
| B        | 2025-01-06  | 4  | 2025-01-04 |

```sql
WITH flags AS (
    SELECT 
        user_id, 
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn,
        DATE_SUB(login_date, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date)) AS flag_date
    FROM logins
),
segments AS (
    SELECT 
        user_id, 
        flag_date, 
        COUNT(*) AS cnt,
        MIN(login_date) AS start_date,
        MAX(login_date) AS end_date
    FROM flags
    GROUP BY user_id, flag_date
    HAVING COUNT(*) >= 3
)
SELECT * FROM segments;
```

| user\_id | flag\_date | cnt | start\_date | end\_date  |
| -------- | ---------- | --- | ----------- | ---------- |
| A        | 2024-12-31 | 3   | 2025-01-01  | 2025-01-03 |
| B        | 2025-01-04 | 3   | 2025-01-04  | 2025-01-06 |


---

## 📊 Sales & Ranking Questions

### 8. Daily City Sales Ranking ✅

🧾 **Sample Table: orders**

| order\_id | city      | order\_date | sales |
| --------- | --------- | ----------- | ----- |
| 1         | Beijing   | 2025-01-01  | 100   |
| 2         | Shanghai  | 2025-01-01  | 150   |
| 3         | Guangzhou | 2025-01-01  | 120   |
| 4         | Beijing   | 2025-01-02  | 300   |
| 5         | Shanghai  | 2025-01-02  | 250   |
| 6         | Guangzhou | 2025-01-02  | 180   |
| 7         | Beijing   | 2025-01-02  | 50    |

> 👆 Note: Beijing has two rows on 2025-01-02 (300 + 50), they’ll be summed to 350.

```sql
WITH aggregated AS (
  SELECT
      city, order_date,
      SUM(sales) AS daily_sales
  FROM orders
  GROUP BY city, order_date
)
```

---

>
> 🥇 **Within each day, assign a unique rank to each city based on its sales, from highest to lowest.**     
> `ROW_NUMBER() OVER (PARTITION BY order_date ORDER BY daily_sales DESC) AS rank`,
>
> 🔁 **One total per date, repeated across rows of that day.**     
>`SUM(daily_sales) OVER (PARTITION BY order_date) AS total`,
> 
> 🧠 **City by city accumulation within the same date.**     
> `SUM(daily_sales) OVER (PARTITION BY order_date ORDER BY daily_sales DESC) AS cumulative`

```sql
SELECT
    order_date, city, daily_sales,
    ROW_NUMBER() OVER (PARTITION BY order_date ORDER BY daily_sales DESC) AS rank,
    SUM(daily_sales) OVER (PARTITION BY order_date) AS total, -- important point： 🔁 "One total per date, repeated across rows of that day."
    SUM(daily_sales) OVER (PARTITION BY order_date ORDER BY daily_sales DESC) AS cumulative
FROM aggregated
ORDER BY order_date, daily_sales DESC; -- important point
```
| order\_date | city      | daily\_sales | rank | total | cumulative |
| ----------- | --------- | ------------ | ---- | ----- | ---------- |
| 2025-01-01  | Shanghai  | 150          | 1    | 370   | 150        |
| 2025-01-01  | Guangzhou | 120          | 2    | 370   | 270        |
| 2025-01-01  | Beijing   | 100          | 3    | 370   | 370        |
| 2025-01-02  | Beijing   | 350          | 1    | 780   | 350        |
| 2025-01-02  | Shanghai  | 250          | 2    | 780   | 600        |
| 2025-01-02  | Guangzhou | 180          | 3    | 780   | 780        |


---

### 2.2 Top 3 Operators per City per Day
```sql
WITH operator_sales AS (
    SELECT city, order_date, operator_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY city, order_date, operator_id
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY city, order_date ORDER BY total_sales DESC) AS rn
    FROM operator_sales
)
SELECT * FROM ranked WHERE rn <= 3;
```

**Intermediate Sample:**

| city     | order_date | operator_id | total_sales | rn |
|----------|-------------|-------------|-------------|----|
| Beijing  | 2025-01-01  | 101         | 500         | 1  |
| Beijing  | 2025-01-01  | 102         | 300         | 2  |

---

## 3. 🧠 Sessionization (App Logs)

### 3.1 Group App Logs Into Sessions (> 60s Gap)
```sql
WITH logs_diff AS (
  SELECT id, ts,
      LAG(ts) OVER (PARTITION BY id ORDER BY ts) AS prev_ts,
      CASE 
        WHEN ts - LAG(ts) OVER (PARTITION BY id ORDER BY ts) > 60 
          OR LAG(ts) IS NULL THEN 1 ELSE 0 END AS is_new_session
  FROM logs
),
sessions AS (
  SELECT id, ts,
      SUM(is_new_session) OVER (PARTITION BY id ORDER BY ts) AS session_id
  FROM logs_diff
)
SELECT * FROM sessions;
```

**Sample Table: `logs`**

| id   | ts          |
|------|-------------|
| 1001 | 17523641234 |
| 1001 | 17523641256 |
| 1001 | 17523641334 |

**Output:**

| id   | ts          | session_id |
|------|-------------|------------|
| 1001 | 17523641234 | 1          |
| 1001 | 17523641256 | 1          |
| 1001 | 17523641334 | 2          |

---

## 4. 🔁 Retention & Rolling Behavior

### 4.1 Seller 30-Day Retention Rate
```sql
WITH prev_txn AS (
  SELECT 
      seller_id, 
      transaction_date,
      LAG(transaction_date) OVER (PARTITION BY seller_id ORDER BY transaction_date) AS prev_date
  FROM transactions
)
SELECT 
    transaction_date,
    COUNT(seller_id) AS total,
    SUM(CASE WHEN DATEDIFF(transaction_date, prev_date) <= 30 THEN 1 ELSE 0 END) AS retained,
    ROUND(SUM(CASE WHEN DATEDIFF(transaction_date, prev_date) <= 30 THEN 1 ELSE 0 END) / COUNT(seller_id), 2) AS rate
FROM 
    prev_txn
GROUP BY 
    transaction_date;
```

**Sample Table: `transactions`**

| seller_id | transaction_date |
|-----------|------------------|
| 101       | 2024-01-05       |
| 101       | 2024-02-03       |
| 101       | 2024-03-10       |

---

## 5. 🎥 Live Stream Max Online Count

### 5.1 Count Concurrent Streamers
```sql
SELECT MAX(amt) AS max_online
FROM (
  SELECT dt, SUM(tag) OVER (ORDER BY dt) AS amt
  FROM (
    SELECT stt AS dt, 1 AS tag FROM streams
    UNION ALL
    SELECT edt AS dt, -1 AS tag FROM streams
  ) events
) result;
```

**Sample Table: `streams`**

| id   | stt                 | edt                 |
|------|---------------------|---------------------|
| 1    | 2025-01-01 10:00:00 | 2025-01-01 12:00:00 |
| 2    | 2025-01-01 11:00:00 | 2025-01-01 13:00:00 |

---

## 6. 🧾 Bonus Techniques

- **Duplicates**:
```sql
SELECT name, COUNT(*) FROM students GROUP BY name HAVING COUNT(*) > 1;
```

- **Nth Highest (Per Group)**:
```sql
SELECT * FROM (
  SELECT user_id, amount,
         ROW_NUMBER() OVER (PARTITION BY city ORDER BY amount DESC) AS rn
  FROM transactions
) t WHERE rn = 3;
```

- **Left Anti Join**:
```sql
SELECT a.* FROM a
LEFT JOIN b ON a.key = b.key
WHERE b.key IS NULL;
```

- **Overlapping Ranges**:
```sql
MAX(edt) OVER (PARTITION BY id ORDER BY stt ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
```

---

## ✅ Tips for Interview Prep

1. Master `WINDOW FUNCTIONS`: ROW_NUMBER, LAG, SUM OVER
2. Practice `SESSIONIZATION`, `ROLLING SUM`, `RETENTION`
3. Real use-cases: sales ranking, login streaks, top-N filters
4. Review join types and query execution order
5. Understand skew handling, filter pushdown, indexing

---

Happy practicing! 🎯
