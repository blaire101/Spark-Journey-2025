# 留学缴费首次支付检测 —— 完整方案（含 Watermark / ProcTime 基础讲解）

---

## 命名规范总览（先记住这套规则，全文贯穿使用）

| 前缀 | 类型 | 说明 | 举例 |
|---|---|---|---|
| `dm_` | Hive 数据集市层表 | 针对具体业务主题聚合加工后的结果表，本文的**权威数据源** | `dm_user_first_payment_d` |
| `hbt_dm_` | HBase 物理表 | `hbt_` 表示"这是一张 HBase 表"，后面完整保留源头 Hive 表名，方便追溯血缘 | `hbt_dm_user_first_payment_d` |
| `ft_` | Flink SQL 里注册的表 | Source / Sink / 维表映射，只是 connector 配置，不存数据 | `ft_src_payment_events`、`ft_dim_hbase_first_pay`、`ft_sink_coupon_trigger` |
| `_d` | 表名后缀 | 日全量快照，每天覆盖式更新 | 对应 `_i` 增量表、`_his` 拉链表 |

---

## Step 0：数据源全景 —— 数据从哪来，怎么流转

![数据源全景图](docs/data-source-flow.svg)

### 数据的起点：MySQL 缴费表

**`study_abroad_payment` 表**

| order_id | user_id | pay_time | pay_amount | pay_type |
|---|---|---|---|---|
| order_88213 | u_7001 | 2026-07-03 09:00:00 | 5000.00 | 订金 |
| order_88214 | u_7001 | 2026-07-03 15:30:00 | 45000.00 | 尾款 |
| order_91002 | u_8002 | 2026-07-03 10:00:00 | 30000.00 | 全款 |

### 📌 知识点科普：数据怎么从 MySQL 变成 Kafka 消息

这一步叫 **CDC（Change Data Capture，变更数据捕获）**，常见工具是 **Canal** 或 **Debezium**。原理：MySQL 为了主从复制，会把每一次 `INSERT/UPDATE/DELETE` 记录进 **binlog** 日志文件。CDC 工具伪装成一个"从库"，实时读取这份 binlog，把每条变更解析成一条 JSON 消息发到 Kafka。好处是**完全不需要改动业务系统代码**，是旁路监听。

### 两条独立的消费管道

同一个 Kafka topic，被两个 **Consumer Group** 各自完整读一遍：

| | 谁读 | 读的范围 | 目的 |
|---|---|---|---|
| 批处理管道 | Hive/Spark 每天凌晨任务 | 昨天全天 | 落 ODS，聚合出 `dm_user_first_payment_d` |
| 实时管道 | Flink SQL 常驻作业 | 持续消费 | 实时判断今天谁是首次支付 |

### 📌 知识点科普：为什么同一个 Kafka topic 能被两边同时读，互不影响

Kafka 的消费模型是 **Consumer Group 隔离**——每个 Consumer Group 独立维护自己的 offset（读到哪了）。批处理管道读到哪、实时管道读到哪，是两本互不相干的账，可以放心同时消费同一个 topic。

---

## Step 1：基础知识 —— ProcTime、EventTime、Watermark 到底是什么

在写 Kafka Source 建表语句之前，必须先搞懂这三个概念，因为它们会贯穿整个方案。这是初学者最容易搞混的地方，花点时间讲透。

![ProcTime与Watermark讲解图](docs/watermark-proctime-explained.svg)

### 📌 EventTime（事件时间）—— 数据自己带的"业务发生时间"

就是你表里的 `pay_time` 字段——这笔支付**在业务上真实发生的时刻**。它是数据自己携带的属性，跟数据什么时候被 Flink 处理没有任何关系。

### 📌 ProcTime（处理时间）—— Flink 处理这条数据那一刻，机器的墙上时钟

`PROCTIME()` 函数返回的是"**现在**"——也就是这条数据被 Flink 算子真正处理到的那个系统时刻。它不是数据自带的，是 Flink 现算现取的。

### 两者的核心区别

| | EventTime | ProcTime |
|---|---|---|
| 来源 | 数据自带（业务时间戳） | Flink 处理时的系统时钟 |
| 确定性 | 确定的，可以重放（同一批数据，重新计算结果一样） | 不确定，不可重放（同一批数据，两次运行处理到的时刻可能不同） |
| 是否受网络延迟影响 | 数值本身不受影响，但**到达 Flink 的顺序**可能乱序 | 不存在"乱序"概念，处理到哪就是哪 |
| 典型用途 | 需要按"业务真实发生时间"计算的场景（比如统计"9点这一小时的交易额"） | 本方案里专门给 **Lookup Join** 用 |

### 📌 Watermark —— 专门配合 EventTime 使用的"我不再等更早数据了"的水位线

因为网络延迟、多个分区并行处理等原因，EventTime 数据到达 Flink 的顺序**可能是乱序的**——比如 09:00:00 发生的支付，可能比 09:00:03 发生的支付晚到 Flink。如果永远死等所有可能迟到的数据，程序永远没法往下推进。

**Watermark 的作用**：给"到底要等多久"划一条线。

```sql
WATERMARK FOR pay_time AS pay_time - INTERVAL '5' SECOND
```

意思是：**Flink 允许 EventTime 数据最多迟到 5 秒**。比如当前已经收到过 `pay_time = 10:00:05` 的数据，Watermark 就会推进到 `10:00:00`（10:00:05 减去 5 秒容忍），代表"EventTime 早于 10:00:00 的数据，就算之后才到，也不再等了，直接按迟到处理"。

### 📌 那本方案到底哪里用 EventTime+Watermark，哪里用 ProcTime？

这是初学者最容易搞混的地方，结合我们的场景说清楚：

- **建表时两个都声明了**：
  ```sql
  proctime AS PROCTIME(),
  WATERMARK FOR pay_time AS pay_time - INTERVAL '5' SECOND
  ```
- **`proctime` 专门给 Lookup Join 用**（`FOR SYSTEM_TIME AS OF t.proctime`），因为 Lookup Join 的语义是"现在，马上，去查一次维表当下的快照"，这是一个同步查找动作，跟"允许乱序、允许迟到"的事件时间体系是两套不同的设计哲学。Flink 框架层面**强制要求** Lookup Join 只能用 proctime，写成 `pay_time` 会直接编译报错
- **`pay_time` 的 Watermark 在本方案里其实没有被消费**（没有做窗口聚合），它存在更多是"标准动作"和"为未来扩展预留"——比如以后要按事件时间统计"每小时缴费笔数"，这个 Watermark 就能派上用场

> ⚠️ 面试高频考点：**为什么 Lookup Join 不能用事件时间？** 因为 Lookup Join 本质是"当下同步查询"语义（现在马上去查一下维表长什么样），跟事件时间的乱序容忍机制（要等 Watermark 推进）完全是两套体系，Flink 目前实现要求 `FOR SYSTEM_TIME AS OF` 后面必须接 proctime 列，这是硬性限制。

---

## Step 2：4 个作业总览 —— 2 个常驻 + 2 个定时

![作业调度时间线](docs/job-schedule-timeline.svg)

| 序号 | 作业名 | 涉及表 | 类型 | 运行方式 |
|---|---|---|---|---|
| ① | DedupFirstPayJob | `ft_src_payment_events` → `ft_sink_first_pay_dedup` | Flink SQL | 🟢 **常驻**，提交一次永久运行 |
| ② | FirstPayCouponTriggerJob | `ft_src_first_pay_dedup` + `ft_dim_hbase_first_pay` → `ft_sink_coupon_trigger` | Flink SQL | 🟢 **常驻**，提交一次永久运行 |
| ③ | HiveFirstPayMergeJob | `dm_user_first_payment_d` | Hive/Spark SQL | 🔵 **定时**，每天 02:00 |
| ④ | BulkLoadHBaseJob | `dm_user_first_payment_d` → `hbt_dm_user_first_payment_d` | Spark | 🟣 **定时**，每天 02:30（依赖③） |

```
Kafka: study_abroad_payment_events
         │
         ▼
   【作业① 常驻】去重
         │
         ▼
Kafka: today_first_pay_dedup
         │
         ▼
   【作业② 常驻】查 HBase 判断首次支付 ←──── 【作业④ 定时02:30】Bulk Load 同步 ←──── 【作业③ 定时02:00】Hive T-1合并
         │                                          ↑
         ▼                                    dm_user_first_payment_d（权威数据源）
Kafka: first_pay_coupon_trigger
         │
         ▼
    发券服务（Redis SETNX 幂等兜底）
```

**核心原则**：实时判断逻辑（①②）**不能每天重启**，必须常驻；只有"更新维表数据"这件事（③④）才是每天一次的批处理任务。①②常驻的好处是——③④更新完 HBase 后，①②不需要重启、不需要感知，下一条流数据来的时候查到的自然就是最新数据（因为 HBase Lookup 的缓存 TTL 是 30 分钟，早就没有旧缓存了）。

---

## Step 3：Kafka Source Table（作业① 的输入）

```sql
CREATE TABLE ft_src_payment_events (
    order_id    STRING,
    user_id     STRING,
    pay_time    TIMESTAMP(3),
    pay_amount  DECIMAL(10,2),
    proctime AS PROCTIME(),
    WATERMARK FOR pay_time AS pay_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'study_abroad_payment_events',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'dedup-job-group',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets'   -- 常驻作业不写死时间戳，
                                              -- 靠 Consumer Group 自动记录消费进度
);
```

### 📌 知识点科普：为什么不用 `scan.startup.timestamp-millis` 写死"今天0点"

写死时间戳意味着**这个作业需要每天重启+改参数才能正确工作**，而且一旦意外重启会重新从写死的那个时间点消费，造成重复计算。**常驻作业**用 `group-offsets`：第一次启动从当前位置开始消费，之后完全靠 Checkpoint + Consumer Group 自动接续，不需要人工每天介入。

---

## Step 4：流内去重（作业① 核心逻辑）

![去重演示图](docs/dedup-payment.svg)

```sql
CREATE TABLE ft_sink_first_pay_dedup (
    user_id              STRING,
    order_id             STRING,
    today_first_pay_time TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'upsert-kafka',
    'topic' = 'today_first_pay_dedup',
    'key.format' = 'json',
    'value.format' = 'json'
);

INSERT INTO ft_sink_first_pay_dedup
SELECT user_id, order_id, pay_time AS today_first_pay_time
FROM (
    SELECT
        user_id, order_id, pay_time,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, DATE_FORMAT(pay_time, 'yyyy-MM-dd')   -- 关键：常驻作业必须按"用户+日期"分组
            ORDER BY pay_time ASC
        ) AS rn
    FROM ft_src_payment_events
)
WHERE rn = 1;
```

### 📌 知识点科普：常驻之后为什么必须加"日期"分组

作业不重启，流里会持续包含跨天的数据。如果只按 `PARTITION BY user_id` 分组，算出来的是"用户**有史以来**最早一条"，不是"今天最早一条"——这是把作业改成常驻后最容易漏改、但一定会出 bug 的地方。加上 `DATE_FORMAT(pay_time, 'yyyy-MM-dd')` 后，每天每个用户各自独立计算，配合 `SET 'table.exec.state.ttl' = '25 h'`，昨天的 state 会自动清理，不会无限增长。

### 结合示例数据推演

`u_7001` 今天分两笔（订金 09:00、尾款 15:30），去重后只保留最早那笔：

| user_id | today_first_pay_time |
|---|---|
| u_7001 | 09:00（订金） |
| u_8002 | 10:00（全款） |

### 📌 知识点科普：ROW_NUMBER 去重的底层实现（面试高频）

Flink 会按 `PARTITION BY` 的字段维护一份 **KeyedState**，记录"当前见过的最早时间"。每来一条新数据就跟 state 比较：更早就更新并**撤回之前发出的结果**，重新发一条新的。所以这一步的输出**不是纯追加流**，而是带有"撤回再更新"的 **changelog 流** —— 这个特性会一路影响到最后 Sink 的 connector 选型（见 Step 7）。

### ⚠️ 业务口径提醒

"首次支付"算订金那一刻，还是要等全款到账才算，这是业务定义问题，需要跟运营/产品提前对齐，SQL 层面调整过滤条件即可实现两种口径。

---

## Step 5：Hive DM 层 T-1 表（作业③，🔵 定时 02:00）

**`dm_user_first_payment_d`** —— 数据集市层，日全量快照，全公司的**权威数据源**：

| user_id | first_pay_time | first_order_id | dt |
|---|---|---|---|
| u_8002 | 2025-11-03 07:20:00 | order_31005 | 2026-07-02 |

`u_7001` 不在表里，说明历史上没缴过费，今天是第一次出现。

```sql
-- ═══════════════════════════════════════════════════════════
-- 【作业③ - 定时批处理】HiveFirstPayMergeJob
-- 调度：每天 02:00 触发一次，跑完即结束，不是常驻进程
-- ═══════════════════════════════════════════════════════════

INSERT OVERWRITE TABLE dm.dm_user_first_payment_d PARTITION (dt='${yesterday}')
SELECT
    COALESCE(old.user_id, new.user_id) AS user_id,
    LEAST(
        COALESCE(old.first_pay_time, new.first_pay_time),
        COALESCE(new.first_pay_time, old.first_pay_time)
    ) AS first_pay_time
FROM dm.dm_user_first_payment_d old
FULL OUTER JOIN today_new_users_snapshot new
    ON old.user_id = new.user_id;
```

---

## Step 6：为什么不直接用 Flink 查 Hive —— 引入 HBase 加速层

![HBase架构对比图](docs/architecture-hbase-sync.svg)

| | Hive | HBase |
|---|---|---|
| 定位 | 批量扫描分析 | 高频随机点查 |
| 单次查询延迟 | 秒级到分钟级 | 毫秒级 |
| Lookup Join 场景下 | 整表/整分区加载进内存，用户量大易 OOM | 按 Key 直接定位，不用整表加载 |

**大厂标准做法**：`dm_user_first_payment_d` 继续作为权威数据源，每天额外同步一份进 HBase，专门给 Flink 做高速查询。

---

## Step 7：每天同步 Hive T-1 表进 HBase（作业④，🟣 定时 02:30）

![同步方式对比图](docs/sync-put-vs-bulkload.svg)
![RowKey设计图](docs/rowkey-design.svg)

### HBase 物理表建表

```bash
create 'hbt_dm_user_first_payment_d',
{
    NAME => 'cf',
    DATA_BLOCK_ENCODING => 'FAST_DIFF',
    BLOOMFILTER => 'ROW',
    REPLICATION_SCOPE => '0',
    VERSIONS => '1',
    MIN_VERSIONS => '0',
    KEEP_DELETED_CELLS => 'false',
    COMPRESSION => 'SNAPPY'
}
```

### 📌 知识点科普：为什么 RowKey 要加盐

如果直接用 `user_id` 当 RowKey，且 `user_id` 是自增 ID，新用户会全部落在同一个 Region，造成写入热点。解决办法：RowKey 前面拼一个哈希前缀，把数据打散：

```
RowKey = MD5(user_id).substring(0,2) + "_" + user_id
例如：u_8002 → "8a_u_8002"
```

### 为什么用 Bulk Load，不用逐行 Put

| | 逐行 Put | Bulk Load（推荐） |
|---|---|---|
| 原理 | 逐条调用 API，走正常写路径 | 直接生成 HFile，绕开写路径 |
| 对集群压力 | 大 | 极小 |
| 适用场景 | 小范围增量更新 | **每天全量刷新一份快照**（本场景） |

```scala
// ═══════════════════════════════════════════════════════════
// 【作业④ - 定时批处理】BulkLoadHBaseJob
// 调度：每天 02:30，依赖作业③先跑完
// 输入：dm.dm_user_first_payment_d
// 输出：hbt_dm_user_first_payment_d（HBase表）全量刷新
// ═══════════════════════════════════════════════════════════

val df = spark.sql("SELECT user_id, first_pay_time, first_order_id FROM dm.dm_user_first_payment_d")

val rdd = df.rdd.map(row => {
    val rawKey = row.getAs[String]("user_id")
    val rowkey = s"${md5Prefix(rawKey)}_${rawKey}"
    (rowkey, row)
}).sortByKey()   // Bulk Load 强制要求按 RowKey 有序

rdd.saveAsNewAPIHadoopFile(
    "/tmp/hbase_bulkload/hbt_dm_user_first_payment_d",
    classOf[org.apache.hadoop.hbase.io.ImmutableBytesWritable],
    classOf[org.apache.hadoop.hbase.KeyValue],
    classOf[org.apache.hadoop.hbase.mapreduce.HFileOutputFormat2]
)
// bash: hbase org.apache.hadoop.hbase.tool.LoadIncrementalHFiles /tmp/hbase_bulkload/hbt_dm_user_first_payment_d hbt_dm_user_first_payment_d
```

---

## Step 8：Flink 查 HBase 判断 + 触发发券（作业②，🟢 常驻）

![发券流程图](docs/coupon-trigger-flow.svg)

```sql
-- ═══════════════════════════════════════════════════════════
-- 【作业② - 常驻实时作业】FirstPayCouponTriggerJob
-- 运行方式：7×24小时常驻，只提交一次
-- 依赖：HBase 维表（数据由作业③④每天更新，作业②不需要重启即可感知）
-- ═══════════════════════════════════════════════════════════

CREATE TABLE ft_src_first_pay_dedup (
    user_id              STRING,
    order_id             STRING,
    today_first_pay_time TIMESTAMP(3),
    proctime AS PROCTIME()   -- 这是作业②这边新声明的proctime，
                              -- 跟作业①里的proctime是两回事（不同的表）
) WITH (
    'connector' = 'kafka',
    'topic' = 'today_first_pay_dedup',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'coupon-trigger-job-group',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets'
);

CREATE TABLE ft_dim_hbase_first_pay (
    rowkey STRING,
    cf ROW<first_pay_time STRING, first_order_id STRING>,
    PRIMARY KEY (rowkey) NOT ENFORCED
) WITH (
    'connector' = 'hbase-2.2',
    'table-name' = 'hbt_dm_user_first_payment_d',
    'zookeeper.quorum' = 'zk1:2181,zk2:2181,zk3:2181',
    'lookup.cache.max-rows' = '500000',
    'lookup.cache.ttl' = '30 min'   -- 每天③④更新完HBase后，最多30分钟内自动生效，不用重启
);

CREATE TABLE ft_sink_coupon_trigger (
    user_id    STRING,
    order_id   STRING,
    pay_time   TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'upsert-kafka',
    'topic' = 'first_pay_coupon_trigger',
    'key.format' = 'json',
    'value.format' = 'json'
);

INSERT INTO ft_sink_coupon_trigger
SELECT t.user_id, t.order_id, t.today_first_pay_time
FROM ft_src_first_pay_dedup AS t
LEFT JOIN ft_dim_hbase_first_pay
    FOR SYSTEM_TIME AS OF t.proctime AS h    -- proctime再次出现：Lookup Join 的硬性要求
    ON CONCAT(md5_prefix(t.user_id), '_', t.user_id) = h.rowkey
WHERE h.rowkey IS NULL;   -- HBase里查不到，说明今天真的是首次支付
```

### 📌 知识点科普：为什么这是一个独立的 Flink 作业

`ft_src_first_pay_dedup` 读的是作业①产出的中间 topic，不是直接读原始 Kafka topic。**两个作业物理拆开**的好处：去重结果可以被多个下游复用（不止发券，风控、报表也能订阅同一个中间 topic）；两个作业可以各自独立重启、独立扩缩容，互不影响。

### 为什么 Sink 用 upsert-kafka

去重环节的输出是带"撤回再更新"的 **changelog 流**（回顾 Step 4），普通 `kafka` connector 只支持纯追加写入，遇到更新会报错。`upsert-kafka` 靠 `PRIMARY KEY (user_id)` 把更新语义翻译成"同 key 新消息覆盖旧消息"。

---

## Step 9：下游发券服务 —— 最后一道幂等兜底

Kafka 的 **at-least-once** 消费语义意味着消息仍有极小概率被重复消费。发券服务收到触发消息后，自己再做一次简单幂等：

```
SETNX coupon:u_7001:activity_2026Q3   →  key 已存在则跳过，不重复发券
```

用 Redis `SETNX` 配合合理过期时间（比如 24 小时），成本很低，但能彻底堵住"重复发券"这个最终风险点。

---

## Step 10：部署 Checklist（4 个作业分别怎么上线）

| 作业 | 提交方式 | 每天需要做什么 |
|---|---|---|
| ①②（常驻） | `flink run -d job1.sql` / `job2.sql`，提交后转入后台常驻运行 | **不需要任何操作**；只有代码逻辑变更或故障时才需要重启（从最近 Checkpoint 恢复） |
| ③④（定时） | 注册进 Airflow/DolphinScheduler 的 DAG，设置 Cron | **不需要人工干预**，调度平台按 Cron 自动触发，失败自动告警/重试 |

```
02:00  作业③ HiveFirstPayMergeJob 开始
       ↓（依赖成功触发，不是固定间隔）
02:xx  作业④ BulkLoadHBaseJob 开始
       ↓
02:xx  完成，hbt_dm_user_first_payment_d 更新完毕

（作业①②全天 7×24 小时不间断运行，只在最初部署时提交一次）
```

---

## 全篇面试高频 QA 速查

| 问题 | 一句话答案 |
|---|---|
| EventTime 和 ProcTime 区别？ | EventTime 是数据自带的业务时间戳，可重放；ProcTime 是处理时机器的墙上时钟，不可重放 |
| Watermark 是干嘛的？ | 给 EventTime 划一条"不再等更早数据"的水位线，解决乱序/迟到问题 |
| 为什么 Lookup Join 只能用 proctime？ | 它是"当下同步查询"语义，跟事件时间的乱序容忍机制不是一套体系，框架强制要求 |
| CDC 是什么？ | 读 MySQL binlog 解析变更，业务系统无需改动，旁路监听 |
| 常驻作业为什么要在 PARTITION BY 里加日期？ | 作业不重启会跨天累积数据，不加日期会算成"历史最早"而不是"今天最早" |
| 为什么不直接用 Flink 查 Hive？ | Hive 为批量扫描设计，高频点查会 OOM、冷启动慢 |
| RowKey 为什么要加盐？ | 避免连续递增 ID 全部落在同一 Region，造成写入热点 |
| 为什么用 Bulk Load 不用逐行 Put？ | Bulk Load 绕开正常写路径，全量刷新大表更快、压力更小 |
| upsert-kafka 和普通 kafka connector 区别？ | upsert-kafka 支持消费 update/delete，普通 connector 只支持追加 |
| 常驻作业和定时作业怎么配合？ | 常驻作业（判断逻辑）不重启，靠 HBase lookup cache TTL 自动感知定时作业（数据刷新）的最新结果 |
| 发券服务为什么还要单独做幂等？ | Kafka at-least-once 语义下消息可能重复消费，需要业务侧兜底 |
| 权威数据源是谁？ | 一直是 `dm_user_first_payment_d`，HBase 只是它给实时链路用的加速副本 |
| `dm_` 和 `dwd_` 的区别？ | dwd是清洗后的明细数据，不做聚合；dm是针对具体主题聚合加工后的结果表，直接服务下游应用 |
