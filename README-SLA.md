**Say this out loud, no reading:**

---

**Setup:**

> "At Tencent, we had a critical daily payment report — a Spark job that was running 75 minutes and crashing with OOM errors. This was blocking our downstream SLA."

---

**Root Cause:**

> "I profiled the job in Spark UI and found one stage was taking 60 of those 75 minutes. The culprit was a COUNT DISTINCT on a composite key — country plus channel plus currency. One specific combination, US plus Wise plus USD, had 4 million records all shuffling to a single reducer. Spark was building a giant HashSet in memory to track distinct sender IDs — 4 million entries — and HashSet cannot spill to disk. So when memory ran out, the executor crashed."

---

**Fix 1 — Two-Stage:**

> "My first fix was two-stage aggregation. Instead of COUNT DISTINCT directly, I rewrote the query — first SELECT DISTINCT to deduplicate sender IDs at the partition level before the shuffle, then COUNT on the already-deduped result. This converts the unspillable HashSet into a spillable sorted merge. Data volume going into the shuffle dropped significantly."

---

**Fix 2 — Salting:**

> "But two-stage alone wasn't enough — even after dedup, that one key still had around 2 million unique sender IDs all going to one reducer. So I applied targeted salting. I added a salt column — hash of sender ID modulo 8 — splitting that hot key into 8 buckets. Each bucket goes to a separate reducer, so instead of one reducer handling 2 million records, each handles around 250 thousand. Load distributed evenly."

---

**Fix 3 — SortAgg:**

> "Finally, I disabled HashAggregate and forced SortAggregate. Even with two-stage and salting, Spark defaults to HashAgg internally for the COUNT step — which is still unspillable. SortAgg sorts the data first and processes one group at a time, so it can always spill to disk. This was the safety net to guarantee no OOM regardless of any remaining skew."

---

**Result:**

> "After all three fixes, runtime dropped from 75 minutes to 13 minutes. OOM was completely resolved. Daily report SLA improved from 95% to 99% plus."

---

**If interviewer asks "which fix had the biggest impact":**

> "Two-stage had the biggest impact on runtime because it reduced shuffle data volume the most. Salting solved the remaining reducer imbalance. SortAgg was the safety net — it didn't change runtime much but guaranteed stability."

---

**Key numbers to remember:**

```
75 mins → 13 mins
4M records → one reducer
8 salt buckets
SLA 95% → 99%+
```

**Great question — you're right to challenge this.**

---

**Honest answer:**

```
SortAgg IS slower than HashAgg
when data fits in memory.

But in your case:
HashAgg was CRASHING, not just slow.
A crashed job = infinite runtime.
SortAgg finishing in 13 mins > HashAgg crashing at 75 mins.
```

---

**The real performance gain came from Fix 1 + Fix 2:**

```
Fix 1 — Two-stage:
Shuffle data volume: 4M → ~500K per partition
Network I/O massively reduced
→ This is where most of the 62 mins savings came from

Fix 2 — Salting:
One reducer handling 2M → 8 reducers handling 250K each
Parallelism increased 8x
→ This is the second biggest gain

Fix 3 — SortAgg:
Yes slower per record than HashAgg
But HashAgg was OOMing and retrying
Retry = wasted time + restart overhead
SortAgg finishing cleanly = faster end-to-end
```

---

**Timeline breakdown (estimated):**

```
Original:
75 mins = 60 mins skewed stage + 15 mins rest
+ OOM retries adding unpredictable extra time

After Fix 1 + 2:
Shuffle reduced, load distributed
Skewed stage: 60 mins → maybe 8 mins

After Fix 3:
SortAgg slightly slower per record
But no OOM, no retries
Total: ~13 mins
```

---

**Interview — say this if challenged:**

> "You're right that SortAgg is inherently slower than HashAgg per record. But in this case, HashAgg was crashing and retrying — which cost more time than SortAgg's overhead. The real performance gains came from two-stage aggregation reducing shuffle volume, and salting increasing parallelism from 1 reducer to 8. SortAgg was the safety net that eliminated retry overhead and guaranteed stable execution. The combination brought us from 75 minutes to 13 minutes."

---

**One line:**

> Fix 1 and Fix 2 gave the speed. Fix 3 gave the stability. Together they delivered 75 → 13 mins.
