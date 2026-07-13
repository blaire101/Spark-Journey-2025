# Flink 实战完整方案 —— 两个案例合集

> 初学者向完整教程，两个独立案例，用大分割线清晰区分：
> - **Case 1**：留学缴费首次支付检测（判断 + 触发发券）
> - **Case 2**：按小时缴费统计大盘（窗口聚合 + 历史回刷 + 每天T-1校准）
>
> 两个案例共用同一批基础知识（命名规范、Watermark/ProcTime、Connector生态、投递语义、容错重启），放在最前面统一讲，避免重复。

## 📖 目录

- [📚 公共基础知识（两个案例都会用到）](#sec-base)
  - [命名规范总览](#sec-naming)
  - [基础知识 A：ProcTime、EventTime、Watermark](#sec-a)
  - [基础知识 B：Connector 生态](#sec-b)
  - [基础知识 C：消息投递语义](#sec-c)
  - [基础知识 D：容错与重启](#sec-d)
- [🔵 Case 1：留学缴费首次支付检测](#sec-case1)
  - [Step 1.0：数据源全景](#sec-1-0)
  - [Step 1.1：4 个核心作业总览](#sec-1-1)
  - [Step 1.2：Kafka Source Table（作业①）](#sec-1-2)
  - [Step 1.3：流内去重（作业①核心）](#sec-1-3)
  - [Step 1.4：Hive DM 层 T-1 表（作业③）](#sec-1-4)
  - [Step 1.5：为什么引入 HBase 加速层](#sec-1-5)
  - [Step 1.6：每天同步进 HBase（作业④）](#sec-1-6)
  - [Step 1.7：Lookup Join + 触发发券（作业②）](#sec-1-7)
  - [Step 1.8：下游发券服务幂等兜底](#sec-1-8)
- [🟢 Case 2：按小时缴费统计大盘](#sec-case2)
  - [Step 2.0：Watermark 实战 —— TUMBLE 窗口聚合](#sec-2-0)
  - [Step 2.1：窗口统计作业独立成作业⑤](#sec-2-1)
  - [Step 2.2：历史数据回刷](#sec-2-2)
  - [Step 2.3：每天 T-1 校准（作业⑥）](#sec-2-3)
  - [Step 2.4：统一写入 ClickHouse](#sec-2-4)
- [📋 全部作业总览 + 部署 Checklist](#sec-jobs)
- [附录：全篇面试高频 QA 速查](#sec-qa)

---

<a id="sec-base"></a>
# 📚 公共基础知识（两个案例都会用到）

<a id="sec-naming"></a>
## 命名规范总览

| 前缀 | 类型 | 说明 | 举例 |
|---|---|---|---|
| `dm_` | Hive 数据集市层表 | 针对具体业务主题聚合加工后的结果表，权威数据源 | `dm_user_first_payment_d` |
| `hbt_dm_` | HBase 物理表 | `hbt_` 表示"这是一张 HBase 表"，后面完整保留源头 Hive 表名 | `hbt_dm_user_first_payment_d` |
| `ft_` | Flink SQL 里注册的表 | Source / Sink / 维表映射，只是 connector 配置，不存数据 | `ft_src_payment_events` |
| `_d` | 表名后缀 | 日全量快照，每天覆盖式更新 | 对应 `_i` 增量表 |

<a id="sec-a"></a>
## 基础知识 A：ProcTime、EventTime、Watermark 到底是什么

![ProcTime与Watermark讲解图](docs/watermark-proctime-explained.svg)

**EventTime（事件时间）**：数据自带的业务发生时间，比如 `pay_time`，跟 Flink 什么时候处理它无关。

**ProcTime（处理时间）**：`PROCTIME()` 返回 Flink 处理这条数据那一刻的系统墙上时钟，不可重放。

| | EventTime | ProcTime |
|---|---|---|
| 来源 | 数据自带 | 系统时钟 |
| 确定性 | 可重放 | 不可重放 |
| 典型用途 | 窗口聚合（Case 2） | Lookup Join（Case 1） |

**Watermark**：给 EventTime 划一条"不再等更早数据"的水位线。

```sql
WATERMARK FOR pay_time AS pay_time - INTERVAL '5' SECOND
```

意思：允许数据最多迟到 5 秒，当前最大 EventTime 减去这个容忍值，就是当前 Watermark 位置。

<a id="sec-b"></a>
## 基础知识 B：Flink Table/SQL 的 Connector 生态

| Connector | Source | Sink | 当维表(Lookup) | 说明 |
|---|---|---|---|---|
| Kafka | ✅ | ✅ | ❌ | 普通 append 流 |
| Upsert-Kafka | ✅ | ✅ | ❌ | 支持消费/写入 changelog |
| HBase | ✅ | ✅ | ✅ | Case 1 里当维表用 |
| JDBC | ✅ | ✅ | ✅ | MySQL/PostgreSQL 等，也能当维表 |
| Hive | ✅ | ✅ | ✅ | 三种角色都支持 |
| Filesystem | ✅ | ✅ | ❌ | 读写 CSV/Parquet/ORC，含 HDFS/S3 |
| Elasticsearch | ❌ | ✅ | ❌ | 只能当 Sink |
| ClickHouse | ⚠️ | ⚠️ | ⚠️ | 不算 Flink 官方一等公民，通常借用**通用 JDBC connector**（ClickHouse自带JDBC驱动）三种角色都能实现，也有社区专门维护的第三方connector（如 `flink-connector-clickhouse`），本文 Case 2 就是这么接的 |
| Print / Blackhole / DataGen | 部分支持 | ✅ | ❌ | 调试/测试专用 |

### 📌 关于 Redis：不算严格意义的"官方支持"

Apache Flink 官方仓库**没有 Redis connector**。Apache Bahir 提供过 Redis Sink，但那是 **DataStream API 级别**，不是 Table/SQL API，且维护不活跃。市面上有第三方 Flink SQL Redis connector，能用但不是官方项目，长期维护性要自己承担。这也是 Case 1 里最终选 HBase 而不是 Redis 当维表的原因之一——HBase 有官方 connector，跟 Hive/Flink 集成无缝。如果确实需要 Redis 特殊结构（Bitmap/HLL），通常在 DataStream API 里用 `RichAsyncFunction` 自己写异步查询逻辑。

### 📌 关于 ClickHouse：也不是官方一等公民，但接入路径比 Redis 成熟

跟 Redis 类似，**Apache Flink 官方仓库也没有内置 ClickHouse connector**，但接入 ClickHouse 比接入 Redis 容易得多，因为有两条现成路径：

1. **借用通用 JDBC connector**：ClickHouse 官方提供标准 JDBC 驱动（`clickhouse-jdbc`），Flink 的 `'connector' = 'jdbc'` 本身就是官方支持的，只要把 JDBC 连接串换成 ClickHouse 的，Source/Sink/Lookup 三种角色都能直接用，不需要额外插件
2. **社区专门维护的 ClickHouse connector**（比如 `flink-connector-clickhouse`）：针对 ClickHouse 的批量写入、`ReplacingMergeTree` 语义做了专门优化（比如攒批写入减少小文件、支持异步写），比通用 JDBC connector 性能更好，本文 Case 2 用的就是这种

**结论**：Redis 在 Flink 生态里比较边缘（连 DataStream 级别的支持都不活跃了）；ClickHouse 虽然也不是 Flink 官方仓库自带，但因为**协议兼容 JDBC**，加上社区活跃度高，接入成熟度和可靠性都比 Redis 高不少，这也是大数据团队更愿意在 Flink 生态里用 ClickHouse 而不是 Redis 做分析型存储的原因之一。

<a id="sec-c"></a>
## 基础知识 C：消息投递语义 —— At-most-once / At-least-once / Exactly-once

![投递语义对比图](docs/delivery-semantics.svg)

| | 定义 | 代价 |
|---|---|---|
| At-most-once | 出故障不重试，可能丢消息，绝不重复 | 很少用在关键业务 |
| At-least-once | 出故障会重试，不丢但可能重复 | 下游必须自己幂等 |
| Exactly-once | 既不丢也不重 | 实现复杂，跨系统很难真正做到 |

**Flink 靠 Checkpoint + Barrier 对齐做到内部 Exactly-once**：周期性插入 Barrier 标记，所有输入通道收到同一轮 Barrier 时做状态快照；失败重启从最近成功的 Checkpoint 恢复。但这只保证 Flink 自己的计算状态，写外部系统（Kafka/HBase）通常退化成 **"At-least-once 投递 + 下游幂等处理"**（按主键覆盖写、Redis SETNX 判重）。

<a id="sec-d"></a>
## 基础知识 D：容错与重启 —— 作业挂了数据丢不丢

必须开启 Checkpoint，否则常驻作业"自动接续消费"不成立：

```sql
SET 'execution.checkpointing.interval' = '60 s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';
SET 'state.checkpoints.dir' = 'hdfs:///flink-checkpoints/first-pay';
SET 'execution.checkpointing.min-pause' = '30 s';
SET 'execution.checkpointing.timeout' = '10 min';
```

| 场景 | 是否丢数据 | 需要人工操作 |
|---|---|---|
| 自动容错重启（开了Checkpoint） | ❌ 不丢 | 不需要，全自动 |
| 手动重启，用 Savepoint | ❌ 不丢 | 需要，标准操作 |
| 手动重启，裸重启不用Savepoint | ⚠️ 有风险 | 危险操作，不推荐 |

正确的手动重启流程：

```bash
flink stop --savepointPath hdfs:///savepoints/dedup-job job_id
flink run -s hdfs:///savepoints/dedup-job -d job1_new.sql
```

裸重启会退回去看 `scan.startup.mode='group-offsets'`，依赖 Kafka Broker 上最后提交的 offset，如果这个 Consumer Group 从没成功提交过 offset，会触发 `auto.offset.reset`，`latest` 丢数据、`earliest` 重复消费大量历史数据。

---
---

<a id="sec-case1"></a>
# 🔵 Case 1：留学缴费首次支付检测

> 判断用户是否首次缴纳留学费用，首次支付立刻触发优惠券。核心链路：去重 → 查 HBase 维表判断 → 触发发券。

<a id="sec-1-0"></a>
## Step 1.0：数据源全景

![数据源全景图](docs/data-source-flow.svg)

**`study_abroad_payment` 表**（MySQL）

| order_id | user_id | pay_time | pay_amount | pay_type |
|---|---|---|---|---|
| order_88213 | u_7001 | 2026-07-03 09:00:00 | 5000.00 | 订金 |
| order_88214 | u_7001 | 2026-07-03 15:30:00 | 45000.00 | 尾款 |
| order_91002 | u_8002 | 2026-07-03 10:00:00 | 30000.00 | 全款 |

数据经 **CDC（Canal/Debezium）** 读取 MySQL binlog，解析成 JSON 消息发到 Kafka，业务系统代码无需改动。

<a id="sec-1-1"></a>
## Step 1.1：4 个核心作业总览

![作业调度时间线](docs/job-schedule-timeline.svg)

| 序号 | 作业名 | 涉及表 | 类型 | 运行方式 | 优先级 |
|---|---|---|---|---|---|
| ① | DedupFirstPayJob | `ft_src_payment_events` → `ft_sink_first_pay_dedup` | Flink SQL | 🟢 常驻 | P0 |
| ② | FirstPayCouponTriggerJob | `ft_src_first_pay_dedup` + `ft_dim_hbase_first_pay` → `ft_sink_coupon_trigger` | Flink SQL | 🟢 常驻 | P0 |
| ③ | HiveFirstPayMergeJob | `dm_user_first_payment_d` | Hive/Spark SQL | 🔵 定时 02:00 | P0 |
| ④ | BulkLoadHBaseJob | `dm_user_first_payment_d` → `hbt_dm_user_first_payment_d` | Spark | 🟣 定时 02:30（依赖③） | P0 |

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
   【作业② 常驻】查 HBase 判断首次支付 ←──── 【作业④ 定时02:30】Bulk Load ←──── 【作业③ 定时02:00】Hive T-1合并
         │                                          ↑
         ▼                                    dm_user_first_payment_d（权威数据源）
Kafka: first_pay_coupon_trigger
         │
         ▼
    发券服务（Redis SETNX 幂等兜底）
```

<a id="sec-1-2"></a>
## Step 1.2：Kafka Source Table（作业①）

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
    'properties.auto.offset.reset' = 'latest',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets'
);
```

<a id="sec-1-3"></a>
## Step 1.3：流内去重（作业①核心）

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
            PARTITION BY user_id, DATE_FORMAT(pay_time, 'yyyy-MM-dd')   -- 常驻作业必须按"用户+日期"分组
            ORDER BY pay_time ASC
        ) AS rn
    FROM ft_src_payment_events
)
WHERE rn = 1;
```

> **常驻之后为什么必须加日期分组**：作业不重启会跨天累积数据，只按 `user_id` 分组会算成"历史最早"而不是"今天最早"。配合 `SET 'table.exec.state.ttl' = '25 h'`，昨天的 state 自动清理。
>
> **ROW_NUMBER 底层原理**：按 key 维护 KeyedState 记录当前最优值，新数据更优时撤回旧结果、发出新结果，产生 changelog 流——这决定了 Sink 必须用 upsert-kafka。

<a id="sec-1-4"></a>
## Step 1.4：Hive DM 层 T-1 表（作业③，🔵 定时 02:00）

**`dm_user_first_payment_d`** —— 权威数据源：

| user_id | first_pay_time | first_order_id | dt |
|---|---|---|---|
| u_8002 | 2025-11-03 07:20:00 | order_31005 | 2026-07-02 |

```sql
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

<a id="sec-1-5"></a>
## Step 1.5：为什么不直接查 Hive —— 引入 HBase 加速层

![HBase架构对比图](docs/architecture-hbase-sync.svg)

| | Hive | HBase |
|---|---|---|
| 定位 | 批量扫描分析 | 高频随机点查 |
| Lookup Join 场景下 | 整表加载进内存，用户量大易 OOM | 按 Key 直接定位 |

<a id="sec-1-6"></a>
## Step 1.6：每天同步进 HBase（作业④，🟣 定时 02:30）

![同步方式对比图](docs/sync-put-vs-bulkload.svg)
![RowKey设计图](docs/rowkey-design.svg)

```bash
create 'hbt_dm_user_first_payment_d',
{
    NAME => 'cf', DATA_BLOCK_ENCODING => 'FAST_DIFF', BLOOMFILTER => 'ROW',
    REPLICATION_SCOPE => '0', VERSIONS => '1', MIN_VERSIONS => '0',
    KEEP_DELETED_CELLS => 'false', COMPRESSION => 'SNAPPY'
}
```

RowKey 加盐：`MD5(user_id).substring(0,2) + "_" + user_id`，避免连续递增 ID 造成写入热点。用 **Bulk Load**（生成HFile绕开写路径）而不是逐行 Put，全量刷新大表更快、压力更小。

```scala
val df = spark.sql("SELECT user_id, first_pay_time, first_order_id FROM dm.dm_user_first_payment_d")
val rdd = df.rdd.map(row => {
    val rawKey = row.getAs[String]("user_id")
    (s"${md5Prefix(rawKey)}_${rawKey}", row)
}).sortByKey()
rdd.saveAsNewAPIHadoopFile("/tmp/hbase_bulkload/hbt_dm_user_first_payment_d", ...)
// bash: hbase org.apache.hadoop.hbase.tool.LoadIncrementalHFiles ... hbt_dm_user_first_payment_d
```

<a id="sec-1-7"></a>
## Step 1.7：Flink 查 HBase 判断 + 触发发券（作业②，🟢 常驻）

![发券流程图](docs/coupon-trigger-flow.svg)

```sql
CREATE TABLE ft_src_first_pay_dedup (
    user_id STRING, order_id STRING, today_first_pay_time TIMESTAMP(3),
    proctime AS PROCTIME()
) WITH (
    'connector' = 'kafka', 'topic' = 'today_first_pay_dedup',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'coupon-trigger-job-group',
    'properties.auto.offset.reset' = 'latest',
    'format' = 'json', 'scan.startup.mode' = 'group-offsets'
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
    'lookup.cache.ttl' = '30 min'
);

CREATE TABLE ft_sink_coupon_trigger (
    user_id STRING, order_id STRING, pay_time TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'upsert-kafka', 'topic' = 'first_pay_coupon_trigger',
    'key.format' = 'json', 'value.format' = 'json'
);

# 需求 A：只给真正首次支付用户发券
INSERT INTO ft_sink_coupon_trigger
SELECT t.user_id, t.order_id, t.today_first_pay_time
FROM ft_src_first_pay_dedup AS t
LEFT JOIN ft_dim_hbase_first_pay
    FOR SYSTEM_TIME AS OF t.proctime AS h # 每条 Kafka 流记录被 Flink 处理时，按照它的 key 查询 HBase 当前最新可见的维表数据
    ON CONCAT(md5_prefix(t.user_id), '_', t.user_id) = h.rowkey
WHERE h.rowkey IS NULL;

# 需求 B：输出用户权威的历史首次支付信息 - 使用 HBase 优先：
INSERT INTO ft_sink_coupon_trigger
SELECT
    t.user_id,
    COALESCE(h.cf.first_order_id, t.order_id) AS order_id,
    COALESCE(
        TO_TIMESTAMP(h.cf.first_pay_time),
        t.today_first_pay_time
    ) AS pay_time
FROM ft_src_first_pay_dedup AS t
LEFT JOIN ft_dim_hbase_first_pay
    FOR SYSTEM_TIME AS OF t.proctime AS h   # 因为这是 Flink lookup join 的用法，左侧是流，右侧是 Hbase ，不是流；  如果 2侧都是流，采用 LEFT JOIN 等等，没有  FOR SYSTEM_TIME AS OF t.proctime
ON CONCAT(md5_prefix(t.user_id), '_', t.user_id) = h.rowkey;
```

Flink 执行过程：

```
作业启动
   ↓
持续监听 Kafka topic
   ↓
新消息到达 - Kafka 记录进入 Flink - Flink 给它一个 proctime
   ↓
Flink 在这个处理时刻，用 rowkey 查询 HBase
   ↓
Lookup HBase
   ↓
执行 COALESCE
   ↓
写入 upsert-kafka
   ↓
继续等待下一条消息
```

<a id="sec-1-8"></a>
## Step 1.8：下游发券服务 —— 最后一道幂等兜底

```
SETNX coupon:u_7001:activity_2026Q3   →  key 已存在则跳过，不重复发券
```

Redis `SETNX` + 24小时过期，堵住 Kafka at-least-once 语义下重复消费导致的重复发券。

---
---

<a id="sec-case2"></a>
# 🟢 Case 2：按小时缴费统计大盘（含历史回刷 + T-1 校准）

> 运营需要实时大盘，按小时看缴费笔数/金额。这是让 Watermark 真正"触发窗口计算"的经典场景，同时要解决两个真实问题：**上线前的历史数据怎么补**、**实时计算被 Watermark 丢弃的迟到数据怎么修正**。

<a id="sec-2-0"></a>

## Step 2.0：Watermark 实战 —— TUMBLE 滚动窗口聚合

![窗口聚合演示图](docs/window-aggregation.svg)

### 示例数据

| user_id | pay_time（业务发生时间） | pay_amount | 到达 Flink 的实际时间 |
|---|---|---|---|
| u_7001 | 09:05:00 | 5000 | 09:05:02（正常） |
| u_8002 | 09:30:00 | 30000 | 09:30:01（正常） |
| u_9003 | 09:58:00 | 8000 | 09:58:03（正常） |
| u_9003 | **09:55:00** | 12000 | **10:03:00（延迟8分钟）** |
| u_7001 | 10:02:00 | 45000 | 10:02:01（正常） |

### 3 个核心作业总览

| 序号 | 作业名 | 所属Case | 类型 | 运行方式 |
|---|---|---|---|---|
| ⑤ | HourlyPayStatsJob | Case 2 | Flink SQL | 🟢 常驻，P2，每小时写1次到ClickHouse |
| ⑥ | HourlyStatsCalibrationJob | Case 2 | Hive/Spark SQL | 🔵 定时 02:00，一次写24条到ClickHouse | 
| - | HourlyStatsBackfillJob | Case 2 | Hive SQL | ⚪ 一次性，上线当天跑，写入ClickHouse |

> Case 2 最终统一写入 **ClickHouse 表 `dws_pay_hourly_stats`**（`ReplacingMergeTree` 引擎按 `window_start` 去重覆盖），BI 工具只读这一张表，详见 Step 2.4。

### Flink SQL：滚动窗口

```sql
-- ═══════════════════════════════════════════════════════════
-- 【作业⑤ - 常驻实时作业】HourlyPayStatsJob
-- 按小时统计缴费笔数和金额，供运营大盘使用
-- ═══════════════════════════════════════════════════════════

CREATE TABLE ft_src_payment_events_stats (
    order_id    STRING,
    user_id     STRING,
    pay_time    TIMESTAMP(3),
    pay_amount  DECIMAL(10,2),
    WATERMARK FOR pay_time AS pay_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'study_abroad_payment_events',
    'properties.bootstrap.servers' = 'broker:9092',
    'properties.group.id' = 'hourly-stats-job-group',   -- 独立的Consumer Group
    'properties.auto.offset.reset' = 'latest',
    'format' = 'json',
    'scan.startup.mode' = 'group-offsets'
);

CREATE TABLE ft_sink_pay_hourly_stats (
    window_start TIMESTAMP(3),
    window_end   TIMESTAMP(3),
    pay_count    BIGINT,
    pay_amount   DECIMAL(18,2),
    PRIMARY KEY (window_start) NOT ENFORCED   -- 必须能按window_start覆盖，见Step2.2
) WITH (
    'connector' = 'upsert-kafka',   -- 实际生产用upsert-kafka或ClickHouse ReplacingMergeTree
    'topic' = 'pay_hourly_stats',
    'key.format' = 'json',
    'value.format' = 'json'
);

INSERT INTO ft_sink_pay_hourly_stats
SELECT
    window_start,
    window_end,
    COUNT(*)          AS pay_count,
    SUM(pay_amount)    AS pay_amount
FROM TABLE(
    TUMBLE(TABLE ft_src_payment_events_stats, DESCRIPTOR(pay_time), INTERVAL '1' HOUR) # 就是把流里的每条记录按照事件时间放进对应的一小时滚动窗口。
)
GROUP BY window_start, window_end; # 按每个小时窗口聚合

# DESCRIPTOR(pay_time) 是使用 pay_time 这一列作为窗口划分的时间字段
```

原始 Table 数据 

| order_id | user_id | pay_time | pay_amount |
| -------- | -------- | -------- | ---------: |
| O1       | U1 | 10:05    |        100 |
| O2       | U2 | 10:20    |        200 |
| O3       | U3 | 10:55    |         50 |
| O4       | U4 | 11:10    |        300 |

经过：

```
FROM TABLE(
    TUMBLE(
        TABLE ft_src_payment_events_stats,
        DESCRIPTOR(pay_time),
        INTERVAL '1' HOUR
    )
)
```

逻辑上会变成：

| order_id | pay_time | pay_amount | window_start | window_end |
| -------- | -------- | ---------: | ------------ | ---------- |
| O1       | 10:05    |        100 | 10:00        | 11:00      |
| O2       | 10:20    |        200 | 10:00        | 11:00      |
| O3       | 10:55    |         50 | 10:00        | 11:00      |
| O4       | 11:10    |        300 | 11:00        | 12:00      |


### 📌 Watermark 怎么触发窗口计算

`[09:00,10:00)` 窗口收到 09:05/09:30/09:58 三条正常数据。当 Watermark **越过 10:00** 这条线时，Flink 判定窗口①数据到齐，触发计算：**3笔，共¥43000**。那条延迟到10:03才到的09:55事件，此时窗口①已经输出结果，**默认直接丢弃**，不会补进去——这正是 Case 2 要解决的问题之一。

### ⚠️ 重要澄清：窗口触发不是"整点后固定几秒自动触发"，而是"数据驱动"的

很容易误以为窗口是"每小时到点就自动触发，比如10:00:05左右"，**这是不准确的**。真实机制是：**只有当新数据到达时，Flink 才会重新计算一次 Watermark，并借此判断有没有哪个窗口该触发了**。如果没有新数据到达，Watermark 就停在原地不会自己往前走。

```
09:05:02  收到 pay_time=09:05:00 的数据 → Watermark = 09:04:55
09:58:03  收到 pay_time=09:58:00 的数据 → Watermark = 09:57:55 → 还没到10:00，窗口①不触发
10:02:01  收到 pay_time=10:02:00 的数据 → Watermark = 10:01:55 → 已越过10:00，窗口①立刻触发，输出(3笔,¥43000)
10:03:00  收到 pay_time=09:55:00 的迟到数据 → 此时Watermark已是10:01:55，比这条数据还晚 → 判定迟到，直接丢弃
```

**触发窗口①的，不是"到了10点0几分这个时刻"，而是"某一条新数据的EventTime减去5秒后，恰好越过了10:00这条线"**。如果数据一直连续到达，窗口大概率会在整点后不久触发；但如果业务数据本身有间隔（比如下一笔支付要等到10:30才发生），窗口就要等到那时候才触发——完全取决于数据本身，不是固定时钟调度。

### ⚠️ 面试常问的坑：数据断流时，窗口会"卡住不触发"

如果 Kafka topic 某段时间完全没有新数据（比如凌晨3-5点没人缴费），Watermark 会**停留在最后一条数据的位置不动**，导致本该早就触发的窗口一直悬空，直到很久之后才来一条新数据把 Watermark 一次性推过去，积压的窗口才会突然触发。

解决办法是配置**空闲检测（Idle Source Detection）**：

```sql
CREATE TABLE ft_src_payment_events_stats (
    ...
) WITH (
    'connector' = 'kafka',
    ...
    'scan.watermark.idle-timeout' = '1 min'   -- 某个分区超过1分钟没数据，
                                                -- 就临时忽略它，不再拖累Watermark整体推进
);
```

配置后，某个 Kafka 分区超过设定时间没数据会被标记为空闲，Watermark 照常根据其他活跃分区推进，避免"一个分区没数据，拖累所有窗口都触发不了"。这是分布式多分区场景下 Watermark 的经典陷阱，值得记住。

> 迟到数据不是必然丢弃，可以用 `allowedLateness`（窗口触发后继续接受一段时间迟到数据，重新触发计算）或**侧输出流**兜底，本例用最简单写法，默认丢弃。

<a id="sec-2-1"></a>
## Step 2.1：窗口统计作业独立成作业⑤，不跟 Case 1 核心链路合并

按小时统计大盘用的作业⑤，是一个**独立的常驻实时作业**，自己单独建 Source 表、单独用一个 Consumer Group 完整读一遍 `study_abroad_payment_events`，跟 Case 1 的作业①②物理上完全分开，各自独立提交、独立重启、独立扩缩容。

理由很直接：**故障域隔离**——大盘统计逻辑经常要改（加维度、改统计口径），如果跟发券判断耦合在同一个作业里，每次改大盘都要连带重启核心业务；**优先级也不同**——发券判断是 P0，直接影响业务，统计大盘是 P2，可以容忍短暂延迟或失败，分开之后才能按不同标准分级处理。Kafka 被多读一次的开销，Kafka 天生支持多 Consumer Group 并发读，可以忽略不计。

这跟 Case 1 里把"去重"和"发券判断"拆成作业①②，是完全同一个设计原则：**业务重要性不同、变更频率不同的逻辑，要物理拆开成独立作业**。

<a id="sec-2-2"></a>
## Step 2.2：历史数据回刷 —— 上线前 1-6月的数据怎么办

![历史回刷+校准图](docs/backfill-calibration.svg)

作业⑤是 **2026-07-01 才上线**的常驻实时作业，它天生不可能查到 1-6月的历史数据——这跟"今天0点开始消费"没关系，是"作业压根没跑过那段时间"的问题，只能靠**一次性历史回刷**。

```sql
-- ═══════════════════════════════════════════════════════════
-- 【一次性任务】HourlyStatsBackfillJob
-- 只在上线当天跑一次，把1-6月历史数据按小时聚合好
-- 跑完之后不再需要，不用调度、不用每天跑
-- ═══════════════════════════════════════════════════════════

INSERT OVERWRITE TABLE dm.dm_pay_hourly_stats_d PARTITION (dt)
SELECT
    DATE_FORMAT(pay_time, 'yyyy-MM-dd')          AS dt,
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00') AS window_start,
    COUNT(*)        AS pay_count,
    SUM(pay_amount) AS pay_amount
FROM ods.ods_payment_detail
WHERE dt >= '2026-01-01' AND dt < '2026-07-01'
GROUP BY DATE_FORMAT(pay_time, 'yyyy-MM-dd'), DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00');
```

**关键点**：历史数据从 **ODS 明细表**（完整、无 Watermark 丢失问题）算出来，天然准确，不需要"实时+校准"这套流程，一次聚合完写进 `dm_pay_hourly_stats_d`。

<a id="sec-2-3"></a>
## Step 2.3：每天 T-1 校准 —— 修正被 Watermark 丢弃的迟到数据（作业⑥，新增）

7.1 当天上线后，作业⑤是实时计算的，前面提到"09:55延迟到10:03才到"这种情况**每天都会真实发生**，需要每天凌晨用完整的离线数据重新算一遍"昨天"，覆盖修正。

```sql
-- ═══════════════════════════════════════════════════════════
-- 【作业⑥ - 定时批处理】HourlyStatsCalibrationJob
-- 调度：每天 02:00 触发（可跟Case1的作业③同批调度）
-- 用完整ODS明细重算"昨天"，覆盖实时算出的近似值
-- ═══════════════════════════════════════════════════════════

INSERT OVERWRITE TABLE dm.dm_pay_hourly_stats_d PARTITION (dt='${yesterday}')
SELECT
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00') AS window_start,
    COUNT(*)        AS pay_count,
    SUM(pay_amount) AS pay_amount
FROM ods.ods_payment_detail
WHERE dt = '${yesterday}'
GROUP BY DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00');
```

**关键点**：ODS 明细表是完整的离线数据，昨天发生的所有支付，不管多晚到 Kafka，到今天凌晨早就全部落进 ODS 了，这一步不存在 Watermark 丢弃的问题，专门用来修正实时计算的误差。

### 📌 大盘最终数据是怎么拼起来的

```
1月 ────────────────── 6月 │ 7.1 ────────────────────── 今天
      一次性历史回刷          │      实时(作业⑤) + 每天T-1校准(作业⑥)
      （准确，算一次不再变）    │      昨天及更早：已被作业⑥覆盖成准确值
                              │      今天：还是实时近似值，明天才被校准
```

**越往前的数据越"沉淀"成准确值，只有"今天"是唯一还没定稿的一天**——这跟 Case 1 里 `dm_user_first_payment_d` 每天被批处理合并、越来越准的设计哲学完全一致，Lambda 架构的思路在这两个案例里是统一的。

### ⚠️ 实现细节：Sink 表必须支持覆盖写入，不能纯追加

不管接 upsert-kafka、ClickHouse 还是 Hive，必须保证同一个 `window_start` 能被覆盖，否则作业⑤和作业⑥会各写一份，大盘上出现同一个小时两条重复记录：

- **upsert-kafka**：`PRIMARY KEY (window_start)`，天然覆盖（本文采用）
- **ClickHouse**：用 `ReplacingMergeTree` 引擎按 `window_start` 去重
- **Hive**：`INSERT OVERWRITE ... PARTITION (dt)`，按天分区整体覆盖（作业⑥写法）

<a id="sec-2-4"></a>
## Step 2.4：最终落地方案 —— 为什么统一写 ClickHouse，怎么写，写多频繁

上面 Step 2.3 只讲了"要覆盖"这个原则，这里把**完整可落地的方案**写全：两个作业到底写到哪、各自多久写一次、BI 工具怎么接。

![ClickHouse统一写入流程图](docs/clickhouse-write-flow.svg)

### 📌 为什么是 ClickHouse，不是 HBase

判断标准不是"这份数据要不要合并两份"，而是**"下游是谁在读、怎么读"**：

| | Case 1（HBase） | Case 2（ClickHouse） |
|---|---|---|
| 下游是谁 | **Flink 程序**（作业②），每条流数据都要查一次 | **人**（运营看大盘）或 BI 工具定时刷新 |
| 查询方式 | 高频、按单个 `user_id` 精确点查 | 低频、按时间范围做**聚合统计**查询 |
| 需要的能力 | 毫秒级点查 | 秒级聚合分析、支持任意维度下钻 |

Case 1 的 HBase 是给**程序**用的点查加速层；Case 2 的 ClickHouse 是给**人**用的分析引擎，两者场景不同，不能混用。

### ClickHouse 建表

```sql
CREATE TABLE dws_pay_hourly_stats
(
    window_start TIMESTAMP,
    pay_count    UInt64,
    pay_amount   Decimal(18,2),
    update_time  DateTime DEFAULT now()   -- 版本列，谁更晚写入谁就是"更新的版本"
)
ENGINE = ReplacingMergeTree(update_time)  -- 按update_time判断哪条是最新版本
ORDER BY window_start;                    -- 相同window_start的行，merge时只保留最新版本
```

### 📌 知识点科普：ReplacingMergeTree 是怎么去重的

这是 ClickHouse 专门为"同一个 Key 会被写入多次，只想保留最新一条"设计的表引擎：

1. 每次 `INSERT` 都是**真实追加写入**，不会立刻覆盖旧数据——所以短时间内，表里可能同时存在同一个 `window_start` 的两行（旧的近似值 + 新的准确值）
2. ClickHouse 会在后台**异步 merge**（合并数据分片）的过程中，按 `ORDER BY` 指定的 `window_start` 分组，只保留 `update_time` 最大的那一行，把其余的物理删除
3. **merge 是异步的，不保证立刻发生**，如果查询恰好发生在 merge 完成之前，可能会看到重复行

**这就是为什么需要在查询时加保护**：

```sql
-- 方式一：加 FINAL 关键字，强制查询时也做一次去重（有一定性能代价）
SELECT * FROM dws_pay_hourly_stats FINAL WHERE window_start >= '2026-07-03 00:00:00';

-- 方式二：用 argMax 显式取每个window_start最新版本（性能更好，大盘查询推荐这种）
SELECT
    window_start,
    argMax(pay_count, update_time)  AS pay_count,
    argMax(pay_amount, update_time) AS pay_amount
FROM dws_pay_hourly_stats
GROUP BY window_start;
```

### 📌 写入频率详解 —— 这是你问的核心问题

**作业⑤（Flink 实时）：不是持续写，而是"每小时触发一次"**

回顾 Step 2.0，`TUMBLE` 窗口默认是 **append-only（只追加，不连续更新）**——一个窗口只会在 **Watermark 越过这个窗口的结束时间**时，触发**一次**计算并输出**一条**结果，不是来一条数据就写一次。

```
09:00~10:00这个窗口 → 大约10:00左右（Watermark越过10:00时）触发一次 → 写入1条记录到ClickHouse
10:00~11:00这个窗口 → 大约11:00左右触发一次 → 写入1条记录
```

所以**作业⑤全天一共只会写 24 条记录**（每小时1条），不是持续不断地写。

```sql
CREATE TABLE ft_sink_pay_hourly_stats (
    window_start TIMESTAMP(3),
    pay_count    BIGINT,
    pay_amount   DECIMAL(18,2)
) WITH (
    'connector' = 'clickhouse',
    'url' = 'clickhouse://ch-server:8123',
    'database' = 'default',
    'table-name' = 'dws_pay_hourly_stats',
    'sink.batch-size' = '1'          -- 每次触发就是1条，不需要攒批
);

INSERT INTO ft_sink_pay_hourly_stats
SELECT window_start, COUNT(*) AS pay_count, SUM(pay_amount) AS pay_amount
FROM TABLE(
    TUMBLE(TABLE ft_src_payment_events_stats, DESCRIPTOR(pay_time), INTERVAL '1' HOUR)
)
GROUP BY window_start, window_end;
```

**作业⑥（离线校准）：每天 02:00 跑一次，一次性写入昨天的 24 条记录**

```sql
-- 每天02:00执行一次，一次性算出昨天0点到24点、24个整小时的准确值
-- 写入ClickHouse时，每个window_start都会带上"今天"的update_time，
-- 天然比作业⑤昨天写入的旧update_time更新，merge后自动替换成准确值
INSERT INTO dws_pay_hourly_stats
SELECT
    DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00') AS window_start,
    COUNT(*)        AS pay_count,
    SUM(pay_amount) AS pay_amount,
    NOW()           AS update_time
FROM ods.ods_payment_detail
WHERE dt = '${yesterday}'
GROUP BY DATE_FORMAT(pay_time, 'yyyy-MM-dd HH:00:00');
```

### 📌 BI 工具怎么接

BI 工具（Grafana / Superset / 自建大盘网页）**不需要跟 Flink 或 Kafka 打任何交道**，它只是一个**普通的 ClickHouse 客户端**，通过 JDBC 或 HTTP 接口，定时（比如每30秒）对 `dws_pay_hourly_stats` 跑一次 `SELECT`（用上面 `argMax` 那种去重查询），把结果渲染成图表。这一层跟前面 Flink/离线批处理完全解耦——不管数据是刚被作业⑤写进去的近似值，还是被作业⑥覆盖过的准确值，BI 工具永远只是"读现在这张表里有什么"，不需要知道背后是谁写的、写了几次。

### 完整时间线示例（以 2026-07-03 09:00 这个小时为例）

| 时间点 | 发生了什么 | BI大盘此时查到的值 |
|---|---|---|
| 10:00左右 | 作业⑤触发窗口计算，写入 (09:00, 3笔, ¥43000)（近似值，漏了一笔延迟数据） | ¥43000 |
| 7.3全天 | 没有新写入 | 仍是¥43000 |
| 7.4 02:00 | 作业⑥用完整ODS重算，写入 (09:00, 4笔, ¥55000)（准确值） | 取决于merge是否完成，可能短暂看到重复行，加FINAL/argMax后统一显示¥55000 |
| 7.4之后 | ReplacingMergeTree后台merge，旧的近似值行被物理清理 | 稳定显示¥55000，不再需要人工干预 |

### Hive 表 `dm_pay_hourly_stats_d` 还要不要

**可选保留，但不是给大盘用的**，它的定位调整为：**离线计算的中间存档**，方便审计、以后重新回溯校准逻辑。真正给 BI 工具查询的，只有 ClickHouse 里这一张 `dws_pay_hourly_stats` 表。

---
---

<a id="sec-jobs"></a>
# 📋 全部作业总览 + 部署 Checklist

| 序号 | 作业名 | 所属Case | 类型 | 运行方式 |
|---|---|---|---|---|
| ① | DedupFirstPayJob | Case 1 | Flink SQL | 🟢 常驻，P0 |
| ② | FirstPayCouponTriggerJob | Case 1 | Flink SQL | 🟢 常驻，P0 |
| ③ | HiveFirstPayMergeJob | Case 1 | Hive/Spark SQL | 🔵 定时 02:00 |
| ④ | BulkLoadHBaseJob | Case 1 | Spark | 🟣 定时 02:30（依赖③） |
| ⑤ | HourlyPayStatsJob | Case 2 | Flink SQL | 🟢 常驻，P2，每小时写1次到ClickHouse |
| ⑥ | HourlyStatsCalibrationJob | Case 2 | Hive/Spark SQL | 🔵 定时 02:00，一次写24条到ClickHouse | 
| - | HourlyStatsBackfillJob | Case 2 | Hive SQL | ⚪ 一次性，上线当天跑，写入ClickHouse |

> Case 2 最终统一写入 **ClickHouse 表 `dws_pay_hourly_stats`**（`ReplacingMergeTree` 引擎按 `window_start` 去重覆盖），BI 工具只读这一张表，详见 Step 2.4。

| 作业类型 | 提交方式 | 每天需要做什么 |
|---|---|---|
| 常驻（①②⑤） | 提交后转入后台常驻运行，配好 Checkpoint | 不需要任何操作；代码变更走 Savepoint 流程重启 |
| 定时（③④⑥） | 注册进 Airflow/DolphinScheduler 的 DAG | 不需要人工干预，调度平台自动触发、自动告警重试 |
| 一次性（历史回刷） | 手动执行一次 | 跑完即完成使命，不需要调度 |

---

<a id="sec-qa"></a>
# 附录：全篇面试高频 QA 速查

| 问题 | 一句话答案 |
|---|---|
| EventTime 和 ProcTime 区别？ | EventTime 是数据自带的业务时间戳，可重放；ProcTime 是处理时机器的墙上时钟，不可重放 |
| Watermark 是干嘛的？ | 给 EventTime 划一条"不再等更早数据"的水位线，决定窗口什么时候触发计算 |
| 迟到数据默认怎么处理？ | 默认直接丢弃，可用 allowedLateness 或侧输出流兜底 |
| Flink SQL 常见 Connector 有哪些？ | Kafka/Upsert-Kafka/HBase/JDBC/Hive/Filesystem/Elasticsearch(仅Sink)，都是官方支持 |
| Redis 能当 Flink SQL 的 Connector 吗？ | 没有官方 Table API 支持，只有 DataStream 级别的第三方/Bahir 实现，生产常用 RichAsyncFunction 自己写 |
| At-most/at-least/exactly-once 区别？ | 最多一次可能丢不重；至少一次不丢但可能重复；精确一次不丢不重，但跨系统很难真正做到 |
| 作业挂了重启，数据会丢吗？ | 自动容错重启+开了Checkpoint不会丢；手动重启必须走Savepoint流程 |
| 常驻作业为什么要在 PARTITION BY 里加日期？ | 作业不重启会跨天累积数据，不加日期会算成"历史最早"而不是"今天最早" |
| 窗口统计作业要跟核心链路合并吗？ | 不建议，物理拆开隔离故障域，Kafka多读一次的开销远小于耦合风险 |
| 上线前的历史数据怎么补进实时大盘？ | 一次性历史回刷任务，从ODS明细算好写入结果表，只跑一次 |
| 实时窗口计算的误差怎么修正？ | 每天凌晨用完整ODS明细重算"昨天"，INSERT OVERWRITE覆盖实时的近似值 |
| 为什么不直接用 Flink 查 Hive 当维表？ | Hive 为批量扫描设计，高频点查会 OOM、冷启动慢 |
| RowKey 为什么要加盐？ | 避免连续递增 ID 全部落在同一 Region，造成写入热点 |
| 为什么用 Bulk Load 不用逐行 Put？ | Bulk Load 绕开正常写路径，全量刷新大表更快、压力更小 |
| 发券服务为什么还要单独做幂等？ | Kafka at-least-once 语义下消息可能重复消费，需要业务侧兜底 |
| Case2为什么用ClickHouse不用HBase？ | 判断标准是"下游是谁在读"：HBase服务程序高频点查，ClickHouse服务人/BI工具的聚合分析查询 |
| ReplacingMergeTree怎么去重的？ | 后台异步merge时按ORDER BY的key只保留version列最大的一行，merge前查询可能重复，需要FINAL或argMax兜底 |
| Flink窗口作业多久写一次？ | 不是持续写，TUMBLE窗口是append-only，只在Watermark越过窗口结束时间时触发一次，本例每小时写1条 |
| 离线校准作业多久写一次？ | 每天02:00跑一次，一次性写入昨天24个小时的准确值 |
| BI工具怎么接ClickHouse？ | 就是普通的JDBC/HTTP客户端，定时对结果表跑SELECT，不需要感知Flink/Kafka的存在 |
