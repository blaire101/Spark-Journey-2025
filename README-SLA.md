**STAR — Spark OOM Optimization**

---

**S — Situation**

> "we had a critical daily payment report for our remittance business. The Spark job was running 75 minutes and frequently crashing with OOM errors. This was blocking downstream reports and causing SLA breaches."

---

**T — Task**

> "My task was to diagnose the root cause, fix the OOM, and bring the job runtime down to meet our SLA target."

---

**A — Action**

**Step 1: Diagnose**

> "I opened Spark UI and profiled the job. One stage was taking 60 of those 75 minutes. I found the culprit — a COUNT DISTINCT on a composite key: country, channel, and currency. One specific combination had 4 million records all shuffling to a single reducer. Spark was building a giant HashSet in memory. HashSet cannot spill to disk. When memory ran out, the executor crashed."

---

**Step 2: Fix 1 — Two-Stage Aggregation**

> "I rewrote COUNT DISTINCT as a two-stage query. First, SELECT DISTINCT to deduplicate sender IDs at the partition level before shuffle. Then COUNT on the already-deduped result. This converts the unspillable HashSet into a spillable sorted merge, and massively reduces shuffle data volume."

---

**Step 3: Fix 2 — Salting**

> "Two-stage alone wasn't enough. Even after dedup, that one key still had 2 million unique IDs going to one reducer. So I applied targeted salting — added a salt column using hash of sender ID modulo 8, splitting the hot key into 8 buckets. Each bucket goes to a separate reducer. Instead of one reducer handling 2 million records, each now handles 250 thousand. This increased parallelism 8x."

---

**Step 4: Fix 3 — Force SortAggregate**

> "Finally, I disabled HashAggregate and forced SortAggregate. Even with two-stage and salting, Spark defaults to HashAgg internally — still unspillable. SortAgg sorts data first and processes one group at a time, so it can always spill to disk. This was the safety net — guaranteed no OOM regardless of any remaining skew."

---

**R — Result**

> "After all three fixes, runtime dropped from 75 minutes to 13 minutes. OOM was completely resolved. Daily report SLA improved from 95% to 99% plus, unblocking all downstream reports."

---

**If asked: which fix had the biggest impact?**

> "Fix 1 and Fix 2 gave the speed — two-stage reduced shuffle volume, salting increased parallelism 8x. Fix 3 gave the stability — eliminated OOM retries. Together they delivered 75 to 13 minutes."

---

**Key numbers — memorize these:**

```sql
-- Step 0: FX dedup
WITH fx_dedup AS (
    SELECT currency, fdate, fx_to_cnh, fx_to_usd
    FROM (
        SELECT *, 
               ROW_NUMBER() OVER (PARTITION BY currency, fdate ORDER BY fdate DESC) AS rn
        FROM exchange_rates
        WHERE fdate BETWEEN '20240101' AND '20241231'
    ) WHERE rn = 1
),

-- Step 1: add salt + join FX
base AS (
    SELECT
        t.institution,
        t.sender_country,
        t.currency,
        t.sender_id,
        t.transaction_id,
        t.amount * fx.fx_to_cnh  AS amt_cnh,
        t.amount * fx.fx_to_usd  AS amt_usd,
        CASE
            WHEN (t.sender_country = 'US' AND t.institution = 'Wise')
              OR (t.sender_country = 'KR' AND t.institution = 'PandaRemit')
            THEN (hash(t.sender_id) & 2147483647) % 8
            ELSE 8
        END AS salt
    FROM payment_transactions t
    JOIN fx_dedup fx ON t.currency = fx.currency AND t.fdate = fx.fdate
    WHERE t.fdate BETWEEN '20240101' AND '20241231'
),

-- Step 2a: dedup sender per bucket (no HashSet, fully spillable)
sender_deduped AS (
    SELECT DISTINCT institution, sender_country, currency, salt, sender_id
    FROM base
),

-- Step 2b: count sender per bucket (no DISTINCT needed)
sender_per_bucket AS (
    SELECT institution, sender_country, currency, salt,
           COUNT(sender_id) AS sender_cnt
    FROM sender_deduped
    GROUP BY institution, sender_country, currency, salt
),

-- Step 2c: sum metrics per bucket
metrics_per_bucket AS (
    SELECT institution, sender_country, currency, salt,
           COUNT(transaction_id)  AS tx_cnt,
           SUM(amt_cnh)           AS total_cnh,
           SUM(amt_usd)           AS total_usd
    FROM base
    GROUP BY institution, sender_country, currency, salt
),

-- Step 3: sum across all buckets
final AS (
    SELECT
        m.institution,
        m.sender_country,
        m.currency,
        SUM(m.tx_cnt)      AS tx_count,
        SUM(s.sender_cnt)  AS sender_count,
        SUM(m.total_cnh)   AS total_cnh,
        SUM(m.total_usd)   AS total_usd,
        ROUND(SUM(m.total_cnh) / NULLIF(SUM(m.tx_cnt), 0), 2) AS avg_txn_cnh,
        ROUND(SUM(m.total_usd) / NULLIF(SUM(m.tx_cnt), 0), 2) AS avg_txn_usd
    FROM metrics_per_bucket m
    JOIN sender_per_bucket s
        ON  m.institution    = s.institution
        AND m.sender_country = s.sender_country
        AND m.currency       = s.currency
        AND m.salt           = s.salt
    GROUP BY m.institution, m.sender_country, m.currency
)

SELECT * FROM final
```

```
75 mins → 13 mins
4M records → 1 reducer
8 salt buckets → 250K per reducer
SLA 95% → 99%+
```
