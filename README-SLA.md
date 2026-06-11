**STAR — Spark OOM Optimization**

---

**S — Situation**

> "At T, we had a critical daily payment report for our remittance business. The Spark job was running 75 minutes and frequently crashing with OOM errors. This was blocking downstream reports and causing SLA breaches."

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

```
75 mins → 13 mins
4M records → 1 reducer
8 salt buckets → 250K per reducer
SLA 95% → 99%+
```
