# 数据库业务流 — 每环节字段映射

> 清晰展示: 每个 Pipeline 阶段产生哪些字段，表间关系如何流转
> 最后更新: 2026-07-31

---

## 一、总览：七层数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       数据生产 Pipeline (本地)                            │
│                                                                         │
│  L0 RSS采集 ─→ L1 五维评分 ─→ L2 全文抓取 ─→ L3 结构抽取                  │
│  L4 三级增强 ─→ L5 事件聚合 ─→ L6 云端同步 ─→ L7 Web展示                  │
│                                                                         │
│  数据库表:                                                               │
│  rss_articles → news_intelligence → news_content → event_registry        │
│                    (SQLite)             (SQLite)     (SQLite)            │
│                            ↓ POST /internal/*                           │
│                    PostgreSQL: sources → articles → events              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、表关系总图（含字段流转）

```
sources (来源注册)
  │  id, name, url, type, status
  │  └── 聚合器从 event_registry.source_chain 注册
  │
  │  source_id (FK)
  ▼
articles (文章)
  │  id, url, title, summary_cn, content_md,
  │  source_name, source_domain, category, tier,
  │  score_total, score_breakdown, tags, entities,
  │  analysis, key_points, fetch_strategy, fetch_cost
  │  └── 来自 news_intelligence + news_content
  │
  │  article_id (FK)
  ▼
events (事件)
  │  event_id, title, summary, event_type, stage,
  │  confidence, coherence, subject/action/object,
  │  location_country, source(primary/source_count),
  │  actors, keywords, related_entities, evidence,
  │  source_chain, timeline, llm_analysis
  │  └── 来自聚合器 cluster 输出
  │
  ├── insights (LLM洞察) ─── event_id (FK)
  ├── event_relations (事件层级) ─── event_id (FK)
  └── event_article (M:N) ─── event_id + article_id
```

---

## 三、每环节字段产出明细

### L0 — RSS 采集 → `rss_articles` 表

| 字段 | 来源 | 说明 |
|:-----|:-----|:-----|
| id | 哈希 | SHA256(源+URL+标题) 去重键 |
| date | feed | 文章日期 |
| category | 规则分类 | 通讯社/金融媒体/科技... |
| source | feed | RSS 源名称 |
| title | feed | 标题 |
| summary | feed | description (截断300字) |
| link | feed | 文章 URL (UNIQUE) |
| created_at | 系统 | 入库时间 |

**产出**: 98 源原始文章流

### L1 — 五维评分 → `news_intelligence` 表

| 字段 | 来源 | 说明 |
|:-----|:-----|:-----|
| id | 系统 | 自增 |
| raw_id | FK | 关联 rss_articles |
| article_url | 上游 | 文章 URL |
| title | 上游 | 标题 |
| description | 上游 | RSS 描述 |
| **score_total** | scorer | 五维总分 0-100 |
| **score_breakdown** | scorer | `{source, impact, entity, market, velocity}` |
| **tier** | 路由 | A≥90 / B≥60 / C<60 |
| **entities** | 规则 | `{companies, persons, countries}` |
| **categories** | scorer | 影响分类 |
| **score_details** | scorer | 各维度命中关键词 |
| scored_at | 系统 | 评分时间 |

**产出**: 每篇文章的评分 + Tier + 实体

### L2+L3 — 全文抓取 + 结构抽取 → `news_content` 表

| 字段 | 来源 | 说明 |
|:-----|:-----|:-----|
| id | 系统 | 自增 |
| intel_id | FK | 关联 news_intelligence |
| article_url | 上游 | URL (UNIQUE) |
| **content_md** | fetchers | 抓取的正文 Markdown |
| **content_len** | 系统 | 内容长度 |
| **summary_cn** | enhancers | 中文摘要 |
| **fetch_strategy** | cascade | 成功策略 (direct/archive/browser...) |
| **fetch_cost** | cascade | 抓取成本 |
| retry_count | 系统 | 重试次数 |
| fetch_at | 系统 | 抓取时间 |

**产出**: 每篇 Tier A/B 文章的全文 + 摘要

### L4 — 三级增强 → 更新 news_content

| 字段 | Tier | 来源 |
|:-----|:----:|:-----|
| tags | C/B/A | Python规则 / Qwen / DeepSeek |
| entities | B/A | Qwen/DeepSeek 补充 |
| summary_cn | C/B/A | 中文摘要 (规则/Qwen/DeepSeek) |
| analysis | A | DeepSeek 深度分析 `{event, impact, risk_level...}` |
| key_points | A | DeepSeek 关键要点 |

**产出**: LLM 增强的分析字段

### L5 — 事件聚合 → `event_registry` 表

| 字段 | 来源 | 说明 |
|:-----|:-----|:-----|
| event_id | 聚合器 | `EVT-YYYYMMDD-NNN` |
| **title** | best_title | 簇内最长标题 |
| **summary** | 聚合器 | 多源摘要拼接 |
| **event_type** | 质心 | Military/Finance/Politics... |
| **stage** | 聚合器 | breaking/developing/active/stable/closed |
| **confidence** | 公式 | 0.4×权威 + 0.3×凝聚 + 0.2×多样性 + 0.1×数量 |
| **coherence** | 聚合器 | 成员指纹平均分 |
| **subject_name/type** | 质心 | SAO 主体 |
| **action_type/detail** | 质心 | SAO 动作 |
| **object_name/type** | 质心 | SAO 客体 |
| **location_country** | 质心 | 事件国家 |
| **primary_source_id** | 聚合器 | 首发来源 SRC_* |
| **source_count** | 聚合器 | 涉及来源数 |
| **article_count** | 聚合器 | 关联文章数 |
| **article_ids** | 聚合器 | 关联文章 ID 列表 |
| **doc_refs** | 聚合器 | 引用文档 |
| **actors** | 聚合器 | `[{entity, type, role}]` |
| **keywords** | 聚合器 | 主题标签 |
| **related_entities** | 聚合器 | 关联实体 |
| **evidence** | 聚合器 | `[{quote, source, url}]` |
| **source_chain** | 聚合器 | `[{role: break/follow, source}]` |
| **timeline** | 聚合器 | `[{time, update, source}]` |
| **llm_analysis** | enhancers | DeepSeek 事件分析 |
| first_seen / last_updated | 聚合器 | 时间窗口 |
| extraction_method | 系统 | v4.4-saeo |
| tone / goldstein | 🔮 | 冲突分析 (未填充) |

**产出**: 事件 Dossier 全字段

### L6 — 云端同步 → PostgreSQL

```
SQLite event_registry → POST /internal/events/batch → events 表
SQLite news_content  → POST /internal/news/batch  → articles 表
```

### L7 — Web 展示

```
events 表 → GET /api/v1/events → EventDossier JSON → 前端组件
articles → GET /news → Article JSON → 前端组件
```

---

## 四、表间关系明细

### sources → articles (一对多)

```
sources.id = articles.source_id
sources.name → articles.source_name (冗余存储)
```

**字段流转**: sources 的 name/type 被 articles 冗余

### articles → events (多对多)

```
event_article (M:N)
  event_id → events.event_id
  article_id → articles.id
```

**字段流转**: article_ids (JSONB) 冗余存于 events

### events → insights (一对多)

```
insights.event_id → events.event_id
```

**字段流转**: LLM 洞察 (独立表, 可扩展)

### events → event_relations (事件层级)

```
event_relations.event_id → events.event_id
```

**字段流转**: 事件间上下级/关联关系 (可扩展)

---

## 五、字段冗余说明

| 冗余字段 | 位置 | 原因 |
|:---------|:-----|:-----|
| source_name | articles + events | 避免 JOIN |
| article_ids | events (JSONB) | 快速关联 |
| summary | events + articles | 各自独立摘要 |
| entities | articles + events | 展示/聚合双用 |
| location_country | events | 地图标点 |

---

## 六、扩展字段使用建议

| 字段 | 当前 | 建议 |
|:-----|:-----|:-----|
| tone | 空 | 聚合时填充 (sentiment) |
| goldstein | 空 | 聚合时填充 (冲突量表) |
| score_breakdown | articles | 前端雷达图 |
| key_points | articles | 前端要点列表 |
| doc_refs | events | 引用文档链接 |
| insights 表 | 空 | LLM 深度洞察 (独立表) |
| event_relations | 空 | 事件层级树 |
