# 第一阶段：信息处理 → 事件资产

## 定位

> 全球碎片化信息 → 结构化、可计算、可关联、可验证的事件资产

不是"AI帮你读新闻"。是**把世界正在发生的事情加工成实时事件数据库**。

---

## 两阶段边界

```
Phase 1: Information Processing          Phase 2: Intelligence Analysis
────────────────────────────             ────────────────────────────
输入: 新闻/公告/报告/社交                  输入: Event Object + 历史 + 外部数据
输出: Event Object                      输出: Event Intelligence Dossier

回答: "发生了什么？"                      回答: "为什么？意味着什么？接下来？"
```

| | Phase 1 输出 | Phase 2 自行获取 |
|------|------|------|
| 主体/动作/对象 | ✅ 必须 |
| 事件类型 | ✅ 必须 |
| 时间/地点 | ✅ 必须 |
| 来源/证据 | ✅ 必须 |
| 可信度 | ✅ 必须 |
| 参与者角色 | ✅ 建议 |
| 摘要/关键词 | ✅ 必须 |
| 历史事件 | | Phase 2 查询 |
| Actor画像 | | Phase 2 查询 |
| 市场数据 | | Phase 2 查询 |
| 外部知识 | | Phase 2 查询 |

---

## Phase 1 输出 Schema（冻结）

```json
{
  "event_id": "EVT-20260711-001",

  "subject":   {"id": "FED", "name": "Federal Reserve", "type": "Organization"},
  "action":     {"type": "RATE_CUT", "detail": "25 basis points"},
  "object":    {"id": "INT_RATE", "name": "Federal Funds Rate", "type": "Financial"},
  "event_type": "Economic",

  "event_time":  "2026-07-11T14:00:00Z",
  "location":    {"region": "North America", "country": "United States"},

  "source":      {"type": "Official", "name": "Federal Reserve", "authority": 95},
  "doc_ref":     {"url": "...", "doc_id": "..."},
  "evidence":    "The Fed decided to lower rates by 25 basis points",

  "actors": [
    {"entity": "US Government", "role": "Initiator"},
    {"entity": "Financial Markets", "role": "Affected"}
  ],

  "title":    "Fed cuts interest rates by 25bp",
  "summary":  "The Federal Reserve announced a 25 basis point rate cut...",
  "keywords": ["rate_cut", "Federal_Reserve", "monetary_policy"],

  "confidence": 0.92,
  "extraction_method": {"method": "qwen3", "model": "qwen3-1.7b", "version": "1.2"},

  "related_events":    ["EVT-20260709-003"],
  "related_entities":  ["Federal Reserve", "US Dollar", "S&P 500"]
}
```

---

## 8 大核心卖点

### 卖点 1：Article → Event（从文章到事件）

**问题**：100 篇新闻 = 100 条信息噪音
**解决**：识别为 1 个事件，聚合所有关联文章

### 卖点 2：跨媒体事件聚合

**不是关键词匹配，是事件级聚合。** 不同媒体的不同标题指向同一事件。

技术：Event Fingerprint (Subject + Action + Object + Time + Location)

### 卖点 3：事件时间线自动生成

```
Day 0  首次声明
Day 1  市场反应
Day 3  外交回应
Day 7  结果
```

### 卖点 4：首发识别

回答"谁最早知道/报道"。区分 `event_time` 和 `publish_time`。

### 卖点 5：事实标准化

不同表述 → 统一规范：`US strike Iran` / `American attack` / `Pentagon operation` → `Actor:US, Action:Military, Target:Iran`

### 卖点 6：事件可信度评分

| 来源 | Confidence |
|------|:--:|
| 官方公告 | 0.95 |
| 多源一致 | 0.85 |
| 单一来源 | 0.60 |
| 匿名消息 | 0.45 |

### 卖点 7：实时事件雷达

主动发现——油+3% → 中东事件簇 → 风险上升。不是被动搜索。

### 卖点 8：事件资产沉淀

文章一次性消费，事件持续增长。半年后一个事件拥有：2000 articles, 50 actors, 20 predictions, 5 outcomes。

---

## 7 模块能力架构

| # | 模块 | 输入 | 输出 |
|:--:|------|------|------|
| 1 | Source Intelligence | RSS/API/Crawler | 来源评分+权威等级 |
| 2 | Document Understanding | Raw Document | Entities + Event Candidates |
| 3 | Entity Extraction | Document | 国家/企业/人物/组织 (Entity ID) |
| 4 | Event Extraction | Entities + Text | Event Candidate (SAO+T+L+Evidence) |
| 5 | Event Resolution | New Candidate + Existing Events | Merge 或 New Event |
| 6 | Event Lifecycle | Event DB | First/Latest/Stage/Status |
| 7 | Quality Control | All outputs | Confidence + Cross-validation |

### 当前实现状态

|            模块            |  状态   | 实现                                                      |
| :----------------------: | :---: | ------------------------------------------------------- |
|  1 Source Intelligence   | ✅ 已实现 | `scorer.py` Source Authority (source_scores.json, 70+源) |
| 2 Document Understanding | ✅ 已实现 | L6 enhance_qwen (Qwen3) + L4 extractor (规则)             |
|   3 Entity Extraction    | ✅ 已实现 | L1 entity_weights.json + L6 Qwen3 entities              |
|    4 Event Extraction    | ✅ 已实现 | V4.3 `aggregator.py` (SAEO fingerprint + Event-Centric) |
|    5 Event Resolution    | ✅ 已实现 | Phase 1/2 clustering + Phase 3 filter                   |
|    6 Event Lifecycle     | ⚠️ 部分 | `start_time`/`last_time` 已跟踪, Stage/Status 待实现          |
|    7 Quality Control     | ⚠️ 部分 | `coherence` 已加入, Source cross-validation 待实现            |

---

## 成功指标（KPI）

| 指标 | 目标 | 当前 |
|------|:--:|:--:|
| Event Precision | >90% | ~83% |
| Merge Accuracy | 85-95% | 验证中 |
| First Source Accuracy | >95% | 待实现 |
| Entity Accuracy | >95% | ~90% |
| Update Latency | <10min | ~30min (cron) |

---

## 最终产品形态

用户看到的不是新闻列表，而是**全球事件地图**：

```
Event: 美伊谈判
Status:   Negotiation
First detected: Reuters 09:02
Updates: 23篇
Actors:  US, Iran, EU
Latest:  Iran accepts talks
Confidence: 91%
Timeline: Day0→Day3→Day7
```

---

## 三个核心问题

| 问题 | 解决 |
|------|------|
| 信息降噪 | 10000篇新闻 → 100个事件 |
| 事实结构化 | 文章 → 可计算事件 |
| 持续积累 | 一次新闻 → 长期事件资产 |

---

## v4.4.3 中文事件聚合 (2026-08-06)

- 中文文章现在走通：采集 → 入库评分 → Qwen 事实抽取 → 推送 VPS（`backfill_chinese_content.py` 补 RSS 描述为 content, content_len>0 可推送）。
- 事件层：`aggregator.py` 加 `_cjk` 指纹标记 + 保守跨语言匹配（主体精确+同主题→50 分, 阈值 `aggregate.cross_lingual_threshold`）。
- KB 中英别名归一：美国↔US→United States、五角大楼↔Pentagon、三星电子↔Samsung、SK海力士↔SK Hynix、中微↔AMEC 等（`knowledge_base/entity_alias.yaml`）。
- **数据限制**: 中国聚焦故事（无人机管制/232条款/DUV光刻机/五角大楼战略）英文语料无同题 → 事件层受覆盖限制; 跨语言匹配在有同主体英文报道时生效。
