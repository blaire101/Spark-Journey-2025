# SQL Preparation Guide

> In life, you can choose who you want to be; be very careful with that choice.

---

## 📘 SQL Basics

### 1. Query Structure & Clauses

![sql](docs/sql-1.png)

- `FROM`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`
- `WHERE`: `NOT IN`, `NULL`, `<>`
- Aggregate Functions: `AVG()`, `SUM()`, `COUNT()`
- Conditional: `CASE WHEN`, `IFNULL(expr, val)`, `SELECT IFNULL(score, 0) AS score_val FROM student;`
- NULL Handling: `COALESCE()`, `SELECT COALESCE(score1, score2, 0) AS score_val FROM student;`   **COALESCE more Versatile**
- `DISTINCT`

**Duplicates**:

```sql
SELECT name, COUNT(*), count(student_id)  -- COUNT(column) Counts column is NOT NULL
FROM students
GROUP BY name
HAVING COUNT(*) > 1;
```

**Left Join**:  The query returns only those rows from a whose key does not exist in b
 
```sql
SELECT a.* 
FROM a 
LEFT JOIN b ON a.key = b.key 
WHERE b.key IS NULL;
```

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

| customer\_id | txn\_date  | txn\_amount |
| ------------ | ---------- | ----------- |
| 1            | 2025-08-01 | 1.00        |
| 1            | 2025-08-01 | 2.00        |
| 1            | 2025-08-02 | 5.00        |
| 2            | 2025-08-01 | 4.00        |
| 2            | 2025-08-02 | 2.00        |

### 4. Average Spend - Questions

Case 1: Find **customers** whose **average daily spend** exceeds 3.

- Aggregate by day to get each customer’s total spend per day.
- Average those daily totals and filter customers whose daily average exceeds 3.

```sql
SELECT
  customer_id,
  AVG(daily_sum) AS average_spend
FROM (
  -- Step 1: sum per customer per day
  SELECT
    customer_id,
    txn_date,
    SUM(txn_amount) AS daily_sum
  FROM transaction
  GROUP BY customer_id, txn_date
) AS daily_spend
GROUP BY customer_id
HAVING AVG(daily_sum) > 3;
```

Result on the sample data:

- customer_id = 1: daily sums = {3.00, 5.00} → average = 4.00 → included
- customer_id = 2: daily sums = {4.00, 2.00} → average = 3.00 → excluded

---

Case 2: On **average**, how much is each **individual transaction** / **per customer**?

```sql
SELECT
  customer_id,
  AVG(txn_amount) AS average_spend
FROM transaction
GROUP BY customer_id
HAVING AVG(txn_amount) > 3;
```

<details>
<summary><strong>Coding -  Continuous 3 Days</strong></summary>

- **a. Using ROW_NUMBER() to Build a Group Identifier**  
- **b. Group Aggregation**

- **user_id**: User ID / **flag_date**: Group flag indicating a continuous login segment  
- **cnt**: Number of consecutive login days  
- **min_login_date** and **max_login_date**: The start and end dates of the continuous login segment

| user_id | login_date |
| --- | --- |
| A | 2025-01-01 |
| A | 2025-01-02 |
| A | 2025-01-03 |
| A | 2025-01-05 |

```sql
-- Step 1: Assign Row Numbers and Calculate Grouping Flag
WITH t2_sub_flag AS 
(
	SELECT 
	    user_id,
	    login_date,
	    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rk,
	    DATE_SUB(login_date, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date)) AS flag_date
	FROM table1;
	-- WHERE amount > 30
)
```

```sql
-- Step 2: Group and Filter for Continuous Login Segments
WITH segments AS 
(
	SELECT
	    user_id,
	    flag_date,
	    COUNT(1) AS cnt,
	    MIN(login_date) AS min_login_date,
	    MAX(login_date) AS max_login_date
	FROM 
	    t2_sub_flag
	GROUP BY 
	    user_id, flag_date
	HAVING 
	    COUNT(1) >= 3
)
-- Step 3: Join Back to Original Table to List Concrete Login Dates
SELECT 
    s.user_id,
    s.flag_date,
    s.cnt,
    s.min_login_date,
    s.max_login_date,
    t.login_date
FROM segments s
JOIN table1 t
    ON t.user_id = s.user_id 
   AND t.login_date BETWEEN s.min_login_date AND s.max_login_date
ORDER BY s.user_id, t.login_date;
```

Example Intermediate Output:

| user_id | login_date | rk | flag_date |
| --- | --- | --- | --- |
| A | 2025-01-01 | 1 | 2024-12-31 |
| A | 2025-01-02 | 2 | 2024-12-31 |
| A | 2025-01-03 | 3 | 2024-12-31 |
| A | 2025-01-05 | 4 | 2025-01-01 |

**Expected Final Output:**

| user_id | flag_date | cnt | min_login_date | max_login_date |
| --- | --- | --- | --- | --- |
| A | 2024-12-31 | 3 | 2025-01-01 | 2025-01-03 |

Expected Final Output:

| user_id | flag_date | cnt | min_login_date | max_login_date | login_date |
| --- | --- | --- | --- | --- | --- |
| A | 2024-12-31 | 3 | 2025-01-01 | 2025-01-03 | 2025-01-01 |
| A | 2024-12-31 | 3 | 2025-01-01 | 2025-01-03 | 2025-01-02 |
| A | 2024-12-31 | 3 | 2025-01-01 | 2025-01-03 | 2025-01-03 |

**Variant 2 – Allowing a One-Day Gap for Continuous Logins**

**Example Input Data (table1):**

| user_id | login_date |
| --- | --- |
| A | 2025-01-01 |
| A | 2025-01-03 |
| A | 2025-01-05 |
| A | 2025-01-06 |

**Result from `login_diffs`:**

| user_id | login_date | diff_days | gap_flag |
| --- | --- | --- | --- |
| A | 2025-01-01 | NULL | 0 |
| A | 2025-01-03 | 2 | 0 |
| A | 2025-01-05 | 2 | 0 |
| A | 2025-01-06 | 1 | 0 |

```sql
WITH login_diffs AS (
  SELECT
    user_id,
    login_date,
    DATEDIFF(login_date, LAG(login_date) OVER (PARTITION BY user_id ORDER BY login_date)) AS diff_days,
    CASE 
      WHEN DATEDIFF(login_date, LAG(login_date) OVER (PARTITION BY user_id ORDER BY login_date)) > 2 
      THEN 1 ELSE 0 END AS gap_flag
  FROM table1
)
```

Step 2: Assign Segment IDs Based on the Gaps

```sql
, segments AS (
  SELECT
    user_id,
    login_date,
    SUM(gap_flag) OVER (PARTITION BY user_id ORDER BY login_date) AS segment_id
  FROM login_diffs
)
```

*Result from `segments`:*

| user_id | login_date | segment_id |
| --- | --- | --- |
| A | 2025-01-01 | 0 |
| A | 2025-01-03 | 0 |
| A | 2025-01-05 | 0 |
| A | 2025-01-06 | 0 |

```sql
SELECT
  user_id,
  segment_id,
  MIN(login_date) AS min_login_date,
  MAX(login_date) AS max_login_date,
  DATEDIFF(MAX(login_date), MIN(login_date)) + 1 AS continuous_days
FROM segments
GROUP BY user_id, segment_id
HAVING DATEDIFF(MAX(login_date), MIN(login_date)) + 1 >= 3;
```

</details>

---

### 5. Average Days Between Transactions

| customer\_id | txn\_date  | txn\_amount |
| ------------ | ---------- | ----------- |
| C1           | 2024-01-10 | 20          |
| C1           | 2024-01-01 | 10          |
| C1           | 2024-01-05 | 15          |
| C2           | 2024-01-04 | 7           |
| C2           | 2024-01-02 | 5           |

```sql
-- Step 1: Get previous transaction date
WITH transaction_date AS (
    SELECT
        customer_id,
        txn_date,
        LAG(txn_date) OVER (PARTITION BY customer_id ORDER BY txn_date) AS prev_transaction_date
    FROM 
        transaction
)
```

| customer\_id | txn\_date  | prev\_transaction\_date |
| ------------ | ---------- | ----------------------- |
| C1           | 2024-01-01 | NULL                    |
| C1           | 2024-01-05 | 2024-01-01              |
| C1           | 2024-01-10 | 2024-01-05              |
| C2           | 2024-01-02 | NULL                    |
| C2           | 2024-01-04 | 2024-01-02              |

- “Although the input is unordered, LAG first sorts the records for each customer_id by txn_date, and then takes the previous row.
- Therefore, the result is still ordered, and prev_transaction_date correctly corresponds to the previous transaction.” ✅


```sql
-- Step 2: Calculate days between transactions
, date_diff AS (
    SELECT
        customer_id,
        DATEDIFF(txn_date, prev_transaction_date) AS date_between_transactions
    FROM transaction_date
    WHERE prev_transaction_date IS NOT NULL
)
```

| customer\_id | date\_between\_transactions   |
| ------------ | ----------------------------- |
| C1           | 4   (2024-01-05 − 2024-01-01) |
| C1           | 5   (2024-01-10 − 2024-01-05) |
| C2           | 2   (2024-01-04 − 2024-01-02) |

```sql
-- Step 3: Calculate average days between transactions
SELECT
    customer_id,
    AVG(date_between_transactions) AS avg_days_transactions
FROM date_diff
GROUP BY customer_id;
```

| customer\_id | avg\_days\_transactions |
| ------------ | ----------------------- |
| C1           | 4.5   ( (4 + 5) / 2 )   |
| C2           | 2.0                     |

### 6. Top 10 Spenders in Last 30 Days

![sql](docs/sql-1.png)

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

### 9. Top 3 Operators per City per Day

✅ Step 1: orders

| order\_id | city     | order\_date | operator\_id | sales |
| --------- | -------- | ----------- | ------------ | ----- |
| 1         | Beijing  | 2025-01-01  | 101          | 200   |
| 2         | Beijing  | 2025-01-01  | 101          | 300   |
| 3         | Beijing  | 2025-01-01  | 102          | 300   |
| 4         | Beijing  | 2025-01-01  | 103          | 250   |
| 5         | Beijing  | 2025-01-01  | 104          | 100   |
| 6         | Shanghai | 2025-01-01  | 201          | 400   |
| 7         | Shanghai | 2025-01-01  | 202          | 300   |
| 8         | Shanghai | 2025-01-01  | 203          | 200   |
| 9         | Shanghai | 2025-01-01  | 204          | 100   |

✅ Step 2: operator_sales

```sql
WITH operator_sales AS (
    SELECT city, order_date, operator_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY city, order_date, operator_id
),
```

| city     | order\_date | operator\_id | total\_sales |
| -------- | ----------- | ------------ | ------------ |
| Beijing  | 2025-01-01  | 101          | 500          |
| Beijing  | 2025-01-01  | 102          | 300          |
| Beijing  | 2025-01-01  | 103          | 250          |
| Beijing  | 2025-01-01  | 104          | 100          |
| Shanghai | 2025-01-01  | 201          | 400          |
| Shanghai | 2025-01-01  | 202          | 300          |
| Shanghai | 2025-01-01  | 203          | 200          |
| Shanghai | 2025-01-01  | 204          | 100          |

✅ Step 3: ranked 

```sql
ranked AS (
    SELECT city, order_date, operator_id, total_sales,
        ROW_NUMBER() OVER (PARTITION BY city, order_date ORDER BY total_sales DESC) AS rn
    FROM operator_sales
),
SELECT city, order_date, operator_id, total_sales, rn
FROM ranked
WHERE rn <= 3
ORDER BY city, order_date, rn;
```

| city     | order\_date | operator\_id | total\_sales | rn |
| -------- | ----------- | ------------ | ------------ | -- |
| Beijing  | 2025-01-01  | 101          | 500          | 1  |
| Beijing  | 2025-01-01  | 102          | 300          | 2  |
| Beijing  | 2025-01-01  | 103          | 250          | 3  |
| Shanghai | 2025-01-01  | 201          | 400          | 1  |
| Shanghai | 2025-01-01  | 202          | 300          | 2  |
| Shanghai | 2025-01-01  | 203          | 200          | 3  |

### 10. 30-Day Retention

🔄 Difference Between Rolling Retention and Cohort Retention

- **Rolling retention** → For each day, check whether the active users today returned within 30 days of their previous activity.
- **Cohort retention** → Group users by their first use date and then track whether they come back within a specific future time window.

A simple analogy:

- Rolling is like “monitoring every day to see who has come back.”
- Cohort is like “looking at a batch of new users and seeing how long it takes them to come back.”

#### 10.1 🔄 A) Rolling 30-Day Retention (gap-based)

| seller\_id | transaction\_date |            desc           |
| ---------- | ----------------- | ------------------------- |
| 201        | 2024-01-02        |                           |
| 201        | 2024-01-20        | ← return within 30 days ✅ |
| 201        | 2024-02-02        | ← return within 30 days ✅ |
| 202        | 2024-01-02        |                           |
| 202        | 2024-01-25        | ← return within 30 days ✅ |
| 203        | 2024-01-02        | ← no return ❌             |

**Step 1 - prev\_data, gap_days**

| seller\_id | transaction\_date | prev\_date | gap\_days |
| ---------- | ----------------- | ---------- | --------- |
| 201        | 2024-01-02        | NULL       | NULL      |
| 201        | 2024-01-20        | 2024-01-02 | 18        |
| 201        | 2024-02-02        | 2024-01-20 | 13        |
| 202        | 2024-01-02        | NULL       | NULL      |
| 202        | 2024-01-25        | 2024-01-02 | 23        |
| 203        | 2024-01-02        | NULL       | NULL      |

```sql
prev_txn AS (
  SELECT
    seller_id,
    transaction_date,
    LAG(transaction_date) OVER (
      PARTITION BY seller_id
      ORDER BY transaction_date
    ) AS prev_date
  FROM base
),
with_gap AS (
  SELECT
    seller_id,
    transaction_date,
    prev_date,
    CASE WHEN prev_date IS NULL THEN NULL
         ELSE datediff(transaction_date, prev_date)
    END AS gap_days
  FROM prev_txn
),
```

**Step 2**

| transaction\_date | total\_active | eligible\_repeaters | retained | rate\_among\_eligible |
| ----------------- | ------------- | ------------------- | -------- | --------------------- |
| 2024-01-02        | 3             | 0                   | 0        | NULL                  |
| 2024-01-20        | 1             | 1                   | 1        | 1.00                  |
| 2024-01-25        | 1             | 1                   | 1        | 1.00                  |
| 2024-02-02        | 1             | 1                   | 1        | 1.00                  |

```sql
daily AS (
  SELECT
    transaction_date,
    COUNT(*) AS total_active,
    COUNT(prev_date) AS eligible_repeaters,
    SUM(CASE WHEN gap_days <= 30 THEN 1 ELSE 0 END) AS retained
  FROM with_gap
  GROUP BY transaction_date
)
SELECT
  transaction_date,
  total_active,
  eligible_repeaters,
  retained,
  CASE WHEN eligible_repeaters = 0 THEN NULL
       ELSE ROUND(retained * 1.0 / eligible_repeaters, 2)
  END AS rate_among_eligible
FROM daily
ORDER BY transaction_date;
```

#### 10.2 🔄 B) Cohort 30-Day Retention 

We compute **cohort 30-day retention** directly on table **`transactions(seller_id, transaction_date)`** — *no extra base/DEDUP step*.

| seller_id | transaction_date |
|-----------|------------------|
| 201       | 2024-01-02 |
| 201       | 2024-01-20 |  ← within 30 days ✅  
| 201       | 2024-02-02 |  ← 31 days after 01-02 (NOT within 30) ❌  
| 202       | 2024-01-02 |
| 202       | 2024-01-25 |  ← within 30 days ✅  
| 203       | 2024-01-02 |  ← no return ❌  
| 204       | 2024-03-01 |
| 204       | 2024-03-20 |  ← within 30 days ✅  
| 204       | 2024-05-01 |  ← after 30 days ❌  

Cohorts present: **2024-01-02** (201, 202, 203) and **2024-03-01** (204).

**Step 1 — First transaction per seller (cohort anchor)**

| seller\_id | first\_date |
| ---------- | ----------- |
| 201        | 2024-01-02  |
| 202        | 2024-01-02  |
| 203        | 2024-01-02  |
| 204        | 2024-03-01  |

```sql
WITH first_txn AS (
  SELECT
    seller_id,
    MIN(transaction_date) AS first_date
  FROM transactions
  GROUP BY seller_id
)
```

**Step 2 — Candidate returns within (0, 30] days after first_date**

| f.seller\_id | f.first\_date | return\_date | gap\_days |
| ---------- | ----------- | ------------ | --------- |
| 201        | 2024-01-02  | 2024-01-20   | 18        |
| 202        | 2024-01-02  | 2024-01-25   | 23        |
| 203        | 2024-01-02  | (NULL)       | (NULL)    |
| 204        | 2024-03-01  | 2024-03-20   | 19        |

> (Note: 201’s 2024-02-02 is 31 days after 2024-01-02, so it is excluded.)

```sql
cand_returns AS (
	SELECT
	  f.seller_id,
	  f.first_date,
	  t.transaction_date AS return_date,
      DATEDIFF(t.transaction_date, f.first_date) AS gap_days
	FROM first_txn f
	LEFT JOIN transactions t
	  ON t.seller_id = f.seller_id
	 AND DATEDIFF(t.transaction_date, f.first_date) BETWEEN 1 AND 30
)
```

**Step 3 — Collapse to per-seller retained flag (0/1)**

| seller\_id | first\_date | retained\_30d |
| ---------- | ----------- | ------------- |
| 201        | 2024-01-02  | 1             |
| 202        | 2024-01-02  | 1             |
| 203        | 2024-01-02  | 0             |
| 204        | 2024-03-01  | 1             |

```sql
flags AS (
  SELECT
    seller_id,
    first_date,
    CASE WHEN COUNT(return_date) > 0 THEN 1 ELSE 0 END AS retained_30d
  FROM cand_returns
  GROUP BY seller_id, first_date
)
SELECT * FROM flags ORDER BY seller_id;
```

**Step 4 — Final cohort 30-day retention** - GROUP BY first_date

| cohort\_date | cohort\_size | retained\_30d | retention\_rate\_30d |
| ------------ | ------------ | ------------- | -------------------- |
| 2024-01-02   | 3            | 2             | 0.67                 |
| 2024-03-01   | 1            | 1             | 1.00                 |

```sql
SELECT
  first_date AS cohort_date,
  COUNT(*) AS cohort_size,
  SUM(retained_30d) AS retained_30d,
  ROUND(SUM(retained_30d) * 1.0 / COUNT(*), 2) AS retention_rate_30d
FROM flags
GROUP BY first_date
ORDER BY cohort_date;
```

---

**🔄 Summary**

| Step   | Description                                                                |
| ------ | -------------------------------------------------------------------------- |
| Step 1 | Use `LAG()` to retrieve each seller's previous transaction date            |
| Step 2 | Count, for each day, how many sellers are active and how many are retained |
| Step 3 | Compute retention rate as `retained / total`                               |

---

Happy practicing! 🎯
