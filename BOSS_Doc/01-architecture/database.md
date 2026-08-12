# 数据库 — PostgreSQL 16

> 最后更新: 2026-08-07
> 版本: PostgreSQL 16-alpine · 大小: 15 MB
> 连接: `postgresql://news_admin:news_pass@postgres:5432/news_intel`

## 字段使用状态 (前端分析)

### events 表 (33 列) — 前端使用/未用/扩展

| 字段 | 前端使用 | 说明 |
|:-----|:--------:|:-----|
| event_id | ✅ | 主键/URL |
| title | ✅ | 事件标题 |
| summary | ✅ | 摘要 |
| event_type | ✅ | 类型标签/筛选 |
| stage | ✅ | 阶段徽章 |
| confidence | ✅ | 置信度 |
| coherence | ❌ | 内部一致性, 未展示 |
| subject_name/type | ✅ | 主体 |
| action_type/detail | ✅ | 动作 |
| object_name/type | ✅ | 客体 |
| location_country | ✅ | 地图/位置 |
| primary_source_id | ✅ | 来源 |
| source_count | ✅ | 来源数 |
| article_count | ✅ | 文章数 |
| actors | ✅ | 参与者角色 |
| keywords | ❌ | 未直接展示 (可做标签云) |
| related_entities | ✅ | 关联实体 |
| evidence | ✅ | 证据引用 (聚合器生成, description 优先 + summary_cn 回退, 去重) |
| source_chain | ✅ | 来源链 (每源一节点, BREAK/FOLLOW) |
| timeline | ✅ | 时间线 (每篇不同文章一节点, 按 URL 去重) |
| llm_analysis | ✅ | AI 分析面板 (规则版: event_summary/risk/market/significance, 100% 覆盖) |
| article_ids | ❌ | 内部关联, 未展示 |
| doc_refs | ❌ | 引用文档, 未展示 |
| first_seen/last_updated | ✅ | 时间 |
| extraction_method | ❌ | 抽取方式 |
| id/created_at | ❌ | 内部字段 |
| **tone** | ❌ | 🔮 扩展: 情绪/语气分析 |
| **goldstein** | ❌ | 🔮 扩展: 冲突-合作量表 (Goldstein Scale) |

### articles 表 (31 列) — 前端使用/未用/扩展

| 字段                               | 前端使用 | 说明                 |
| :------------------------------- | :--: | :----------------- |
| id/url                           |  ✅   | 标识/链接              |
| title                            |  ✅   | 标题                 |
| summary_cn                       |  ✅   | 中文摘要 (自动回退正文前200字) |
| summary                          |  ❌   | 英文摘要, 未展示          |
| content_md                       |  ✅   | 全文 (VIP/Admin)     |
| content_len                      |  ❌   | 内部                 |
| source_name/domain               |  ✅   | 来源                 |
| published_at                     |  ✅   | 发布时间               |
| category                         |  ✅   | 分类                 |
| tier                             |  ✅   | 级别徽章               |
| score_total                      |  ✅   | 评分                 |
| score_breakdown                  |  ❌   | 五维明细, 未展示          |
| tags                             |  ✅   | 标签                 |
| entities                         |  ✅   | 实体                 |
| analysis                         |  ✅   | AI 分析 (VIP)        |
| key_points                       |  ❌   | 要点, 未展示            |
| importance/importance_level      |  ❌   | 重要度, 未展示           |
| fetch_strategy/fetch_cost        |  ❌   | 抓取策略, 运维用          |
| extraction_method                |  ❌   | 抽取方式               |
| language                         |  ❌   | 语言                 |
| status/is_published              |  ✅   | 查询过滤用              |
| is_duplicate                     |  ❌   | 去重标记               |
| source_id                        |  ❌   | FK                 |
| created_at/updated_at/fetched_at |  ❌   | 时间戳                |

## 🔮 扩展方向

> 🗺 **数据模型升级**（2026-08-03）：
> - **Fact Schema V1.0 已冻结** → 仓库 `references/fact-schema-v1.md`（fact + fact_entity 完整 DDL）
> - 规划 → `references/data-model-upgrade-plan.md`；实验 → `references/fact-layer-experiment-design.md`
> - 目标 10 表（source/article/entity/entity_alias/fact/event/event_fact/event_relationship/story/story_event）；抽取器=LLM(Qwen)+Canonicalizer v0.3
> - 关键: `event_relations` 表已存在(VPS)可复用为 event_relationship；Fact 层为 News Intelligence 原创核心模型；Confidence 分层不先验公式化。

| 扩展 | 字段 | 状态 | 用途 |
|:-----|:-----|:-----|:-----|
| **冲突分析** | tone | ✅ 已有字段 | 情绪/语气 (正面/负面/中性) |
| **冲突-合作量化** | goldstein | ✅ 已有字段 | Goldstein Scale (合作+10~冲突-10) |
| 五维评分明细 | score_breakdown | ✅ 已有字段 | 雷达图/评分解析 |
| 文章要点 | key_points | ✅ 已有字段 | 前端要点展示 |
| 引用文档 | doc_refs | ✅ 已有字段 | 文档引用链接 |
| 关联文章 | article_ids | ✅ 已有字段 | 事件-文章关联展示 |
| 实体知识库 | entity-network.json | ✅ 已建 | 实体画像/国家关联 |

## 已实现的数据流

```
Pipeline 本地聚合 → POST /internal/events/batch → events 表 (33字段)
                    → POST /internal/news/batch → articles 表 (31字段)
前端 → /api/v1/* 只读查询
```

## 手动聚合表 (2026-08-02 新增)

**event_article_override** — 管理员手动将文章(按URL)归入事件。独立于自动聚合，Pipeline 重跑 upsert 事件时不触碰此表；读取侧 `/events/{id}` 合并生效（move 语义：被归到其他事件的 URL 从本事件证据中排除）。

| 字段 | 说明 |
|:-----|:-----|
| event_id | 目标事件 (不强外键, 避免事件删除阻塞) |
| article_url | 文章 URL (唯一标识, 与 articles.url 对应) |
| created_at / created_by | 归属时间 / 操作者 |

**event_article_exclusion** — 管理员剔除的自动聚合文章（按URL，持久生效）。自动聚合文章的 `article_ids` 是本地 SQLite id 无法映射 VPS，故以事件证据/引用的 URL 作为"自动文章"的展示与剔除对象。读取侧合并：自动证据 − exclusion + override。

| 字段 | 说明 |
|:-----|:-----|
| event_id | 事件 |
| article_url | 被剔除的文章 URL |
| created_at / created_by | 剔除时间 / 操作者 |

## Fact 层表 (Schema V1.0 + V2, 2026-08-12 实查 16 列)

**fact** — 单条事实（混合抽取器产出: LLM(Qwen noThink) + GLiNER + Canonicalizer）。

| 列 | 类型 | 说明 |
|----|------|------|
| id | `SERIAL PK` | 自增 |
| article_id | `INTEGER` | 本地 pipeline 文章 id（无 FK, 与 VPS articles.id 不匹配; 用 article_url 关联） |
| article_url | `VARCHAR(2048)` | 文章 URL（未来按 URL 关联 VPS 文章） |
| action_type | `VARCHAR(50) NOT NULL` | 规范动作本体 (SANCTIONS/ATTACKS/EXPORT_CONTROL...) |
| action_event_type | `VARCHAR(20)` | 事件类别 (Military/Finance/...) |
| action_detail | `TEXT` | 原始动作文本 (LLM 原话) |
| event_time | `TIMESTAMP` | 事件时间 (端点 _clean_time 清洗) |
| location | `VARCHAR(200)` | 地点 |
| confidence | `FLOAT` | 预留, 不公式化 |
| evidence_type | `VARCHAR(20)` | Told/Induced/Deduced/Witnessed, 默认 Told |
| **subject_name** | `VARCHAR(200)` | Schema V2 冗余主体名（去 normal form 查询） |
| **object_name** | `VARCHAR(200)` | Schema V2 冗余客体名 |
| **action_status** | `VARCHAR(20)` | Schema V2: completed/ongoing/planned/denied/proposed/rumored |
| **action_polarity** | `VARCHAR(20)` | Schema V2: positive/negative/neutral |
| **evidence** | `TEXT` | Schema V2 证据原文 |
| created_at | `TIMESTAMP` | 入库时间 |

> **Schema V2（2026-08-10, ISS-20260810-012）**: 一篇文章产 `facts[]`(≤3 条)；object 为值/数字/日期/短语时 `entity_id=null` 且**不进 fact_entity**。契约唯一真相源: `references/fact-schema-v2.md`。

**fact_entity** — 事实参与者（Role 模型, 支持多主体/多客体）。

| 列 | 类型 | 说明 |
|----|------|------|
| fact_id | `INTEGER FK→fact` | 事实 |
| entity_id | `VARCHAR(100) NOT NULL` | 稳定 id (CTRY_/PERS_/COMP_/ORG_/LOC_/ENT_) |
| entity_name | `VARCHAR(200)` | 规范名 |
| entity_type | `VARCHAR(20)` | Country/Person/Company/Organization/Location/Other |
| role | `VARCHAR(20) NOT NULL` | SUBJECT/OBJECT/TARGET/VICTIM/SOURCE/RESPONDER |

**数据流**: 本地 pipeline Step 4.5（混合抽取器, 多线程）→ POST `/internal/facts/batch` → fact + fact_entity。
完整 DDL 与设计: 仓库 `references/fact-schema-v1.md` + `migrations/versions/0001_fact_tables.py`。

## 总览

| 项目 | 值 |
|------|-----|
| 数据库 | `news_intel` |
| 用户 | `news_admin` |
| 密码 | `news_pass` |
| 容器 | `news-platform-v8-postgres-1` (healthcheck: pg_isready) |
| 数据卷 | `news-intel-platform_pgdata` (Docker volume, external) |
| 表数量 | **31** (2026-08-12: 27 ORM 表 + fetch_stats + alembic_version + **ab_event/ab_bundle**; 迁移 0001-0004 全应用) |
| Pool | 连接池 10, 最大溢出 20 |

## 数据量统计 (2026-08-12 VPS 实查)

| 表 | 行数 | 说明 |
|----|:----:|------|
| events | **500** | 事件 Dossier (subject_type: Other 303/Company 105/Person 91; 随重聚合波动) |
| articles | **3,235** | 文章 (VPS 仅收有正文/描述的文章; 本地 rss_raw 22,722) |
| fact | **13,032** | Fact 层 (Step 4.5 混合抽取, Schema V2 16 列) |
| fact_entity | **25,512** | Fact 参与者 (Role 模型, KB 稳定 ID) |
| sources | 24-36 | RSS 来源注册 (VPS 24; 本地 source_registry 66) |
| entities | **27,366** | 实体主数据 (KB V1 sync_kb_to_db 导入 + 事件派生) |
| entity_alias | **41,089** | 结构化别名 (全部 lang='en', sync_kb_to_db) |
| entity_relationship | **223** | 实体-实体关系 (**in_segment 218**/subsidiary_of 3/parent_of 1/in_industry 1, backfill 从 KB V1) |
| event_relations | **83** | 事件-事件关系 (同 subject 时间序 precedes) |
| ab_event | **50** | A 事件 (同 subject+action+object 合并, 高精度) |
| ab_bundle | **38** | B 事件 (同 subject 脉络, 宽松) |
| story | **101** | Story 打包 (dimension: action 38/subject 23/object 23/location 17) |
| story_event | **1,336** | 故事-事件关联 (position 排序) |
| settings | 21 | 配置中心 KV |
| event_article_override | 16 | 手动聚合归属 (事件校对) |
| users | 3 | 管理员/免费用户 |
| fetch_stats | ~ 数百 | 抓取策略统计 |

> Dashboard (`/api/v1/dashboard`) 实时指标以 VPS 为准（active_events 随 pipeline 波动）。

## 完整表结构 (29 表)

### 1. events — 事件 Dossier (核心表)

| 列 | 类型 | 说明 |
|----|------|------|
| id | `INTEGER PK` | 自增 |
| event_id | `VARCHAR(30) UNIQUE` | 格式: `EVT-YYYYMMDD-NNN` |
| title | `VARCHAR(500) NOT NULL` | 事件标题 |
| summary | `TEXT` | 多源摘要 |
| event_type | `VARCHAR(50)` | Military/Finance/Politics/Diplomacy/Legal/Economic/Leadership/General |
| stage | `VARCHAR(20)` | developing(324) / active(133) / stable(55) |
| confidence | `FLOAT` | 0.0–1.0 |
| coherence | `FLOAT` | 0.0–100.0 |
| subject_name / subject_type | `VARCHAR` | SAO: 主体 |
| action_type / action_detail | `VARCHAR` / `TEXT` | SAO: 动作 |
| object_name / object_type | `VARCHAR` | SAO: 客体 |
| location_country | `VARCHAR(100)` | 关联国家 |
| primary_source_id | `VARCHAR(100)` | 首发来源 ID |
| source_count | `INTEGER` | 涉及来源数 (1–8) |
| article_count | `INTEGER` | 关联文章数 |
| article_ids | `JSONB` | 关联文章 ID 列表 |
| doc_refs | `JSONB` | 引用文档 |
| actors | `JSONB` | `[{entity, type, role}]` |
| keywords | `JSONB` | 关键词标签 |
| related_entities | `JSONB` | 关联实体 |
| evidence | `JSONB` | `[{quote, source, url}]` |
| source_chain | `JSONB` | `[{source_id, source_name, time, role(break/follow)}]` |
| timeline | `JSONB` | `[{time, update, source}]` |
| llm_analysis | `JSONB` | DeepSeek/Qwen3 分析 (可空) |
| extraction_method | `VARCHAR(50)` | 默认 v8 |
| first_seen / last_updated | `TIMESTAMP` | 时间窗口 |
| created_at | `TIMESTAMP` | 入库时间 |
| tone | `VARCHAR` | 🔮 情绪/语气分析 (字段已建, 未填充) |
| goldstein | `INTEGER` | 🔮 冲突-合作量表 (字段已建, 未填充) |

**索引**: PRIMARY KEY (id), UNIQUE (event_id)

**外键引用**: event_article, event_entity, event_relations, insights

### 2. articles — 文章 (次核心表)

| 列 | 类型 | 说明 |
|----|------|------|
| id | `INTEGER PK` | 自增 |
| url | `VARCHAR(2048) UNIQUE NOT NULL` | 文章 URL (去重键) |
| title | `VARCHAR(500) NOT NULL` | 标题 |
| summary | `TEXT` | 英文摘要 |
| summary_cn | `TEXT` | 中文摘要 |
| content_md | `TEXT` | 全文 Markdown (VIP 可见) |
| content_len | `INTEGER` | 内容长度 |
| source_name | `VARCHAR(200)` | RSS 来源名称 |
| source_domain | `VARCHAR(200)` | 源域名 |
| published_at | `TIMESTAMP` | 发布时间 |
| category | `VARCHAR(100)` | 分类 |
| score_total | `INTEGER` | 五维总分 (0–100) |
| score_breakdown | `JSON` | `{source, impact, entity, market, velocity}` |
| tier | `VARCHAR(1)` | A(10篇) / B(924篇) / C(1篇) |
| tags | `JSON` | 标签 |
| entities | `JSON` | `{companies, persons, countries}` |
| analysis | `JSON` | LLM 增强分析 |
| key_points | `JSON` | 关键要点 |
| extraction_method | `VARCHAR(50)` | 结构化抽取方式 |
| fetch_strategy | `VARCHAR(50)` | 抓取策略 (direct/archive/jina/...) |
| fetch_cost | `INTEGER` | 抓取成本 |
| is_published | `BOOLEAN` | 是否发布 |
| fetched_at / created_at / updated_at | `TIMESTAMP` | 时间戳 |
| language | `VARCHAR(5)` | 语言 (默认 en) |
| source_id | `INTEGER FK→sources.id` | 来源 ID |
| importance_level | `VARCHAR(20)` | medium (默认) |

**索引**: PK(id), UNIQUE(url), idx_articles_pub(published_at, tier), idx_articles_src(source_id), idx_articles_status(status), **GIN 全文搜索索引**

### 3. sources — 来源注册表

| 列 | 类型 |
|----|------|
| id | `INTEGER PK` |
| name | `VARCHAR(200)` |
| url | `VARCHAR(2048)` |
| type | `VARCHAR(20)` (default: rss) |
| status | `VARCHAR(20)` (default: active) |
| failure_count | `INTEGER` |
| quarantine_until | `TIMESTAMP` |
| created_at | `TIMESTAMP` |

### 4. users — 用户

| 列 | 类型 | 说明 |
|----|------|------|
| id | `INTEGER PK` | |
| email | `VARCHAR(200) UNIQUE` | 登录邮箱 |
| password_hash | `VARCHAR(300)` | bcrypt (兼容旧版 SHA256) |
| level | `VARCHAR(20)` | free / vip / admin |
| expire_at | `TIMESTAMP` | VIP 过期时间 |
| created_at | `TIMESTAMP` | |

**用户数据**: admin@newsintel.com(admin), test@free.com(free), admin@test.com(admin)

### 5–25. 关联表

| 表 | 列 | 说明 |
|----|-----|------|
| **entities** | id, name, type, country, importance, aliases(JSONB), confidence, first_seen, last_seen, created_at | 实体主数据 (v0.2 升级: +country/importance/confidence/first_seen/last_seen) |
| **entity_alias** | id, entity_id(FK), alias, lang, created_at | 结构化别名 (中英/简称, 唯一 entity_id+alias) — v0.2 新增 |
| **entity_relationship** | id, from_entity_id(FK), to_entity_id(FK), relation_type, confidence, description, evidence_count, first_seen, last_seen, created_at | 实体-实体关系 (KB associations 接入) — v0.2 新增 |
| **story** | id PK, story_id(30 UNIQUE), title(300), description, **dimension**(20: subject/action/object/location), created_at, updated_at | Story 打包 (迁移 0003 + 0004 dimension; story_id 前缀 `STORY_`/`ACT_`/`OBJ_`/`LOC_`) |
| **story_event** | story_id(FK→story.id) + event_id VARCHAR(30) 复合 PK, position INT | 故事-事件关联 (仅排序展示, 不表达因果) — 迁移 0003 |
| **categories** | id, name, parent_id | 分类层级 |
| **tags** | id, name (UNIQUE) | 标签库 |
| **ads** | id, title, image_url, link_url, position, is_active | 广告管理 |
| **assets** | id, type, symbol, name, exchange | 金融资产 |
| **settings** | id, key (UNIQUE), value(TEXT→ORM JSON), updated_at | Pipeline 配置 (KV) ⚠️ 值实际为 TEXT 字符串 |
| **logs** | id, level, message, created_at | 系统日志 |
| **insights** | id, event_id(FK), content(JSONB) | LLM 深度洞察 |
| **fetch_stats** | domain, source_name, strategy, ok_count, fail_count, run_at | 抓取统计 |
| **subscriptions** | user_id(FK), tag_id(FK) | 用户订阅 |
| **article_category** | article_id(FK), category_id(FK) | 文章-分类 (M:N) |
| **article_tag** | article_id(FK), tag_id(FK) | 文章-标签 (M:N) |
| **article_entity** | article_id(FK), entity_id(FK), relevance_score | 文章-实体 (M:N) |
| **event_article** | event_id(FK), article_id(FK) | 事件-文章 (M:N) |
| **event_entity** | event_id(FK), entity_id(FK) | 事件-实体 (M:N) |
| **event_relations** | id, parent_event_id, child_event_id, relation_type, confidence, start_time, end_time, evidence_count, created_at | 事件-事件关系 (v0.2 扩展 start/end_time+evidence_count; 同 subject 时间序派生 precedes) |
| **event_article_override** | event_id, article_url, created_at/by | 手动聚合归属 (见上 §手动聚合表) |
| **event_article_exclusion** | event_id, article_url, created_at/by | 手动剔除 (见上 §手动聚合表) |
| **fact** | 见上 §Fact 层表 | Fact 层 (DDL: references/fact-schema-v1.md + v2) |
| **fact_entity** | 见上 §Fact 层表 | Fact 参与者 (Role 模型) |
| **ab_event** | a_event_id(PK), b_event_id(idx), subject_id(idx), subject_name, action_type, object_id, object_name, n_facts, created_at | A 事件（同 subject_id+action_type+object_id 合并, 宁拆勿错） |
| **ab_bundle** | b_event_id(PK), subject_id(idx), subject_name, a_event_ids(TEXT JSON), created_at | B 事件（同 subject_id 的 A 事件 → 实体行为脉络） |
| **alembic_version** | version_num | Alembic migration 版本 |

## 事件类型分布 (2026-08-03 实查, 总计 385)

| 类型 | 数量 | 占比 |
|------|:----:|:----:|
| Politics | 97 | 25.2% |
| Military | 90 | 23.4% |
| General | 74 | 19.2% |
| Finance | 49 | 12.7% |
| Leadership | 23 | 6.0% |
| Economic | 19 | 4.9% |
| Diplomacy | 18 | 4.7% |
| Legal | 15 | 3.9% |

> ⚠️ 分布随 pipeline 增长变化, 属 point-in-time 快照

## 事件阶段分布 (2026-08-06 VPS 实查, 样本 100/200)

| 阶段 | 样本数 | 说明 |
|------|:----:|------|
| breaking | 87 | 突发 (主导) |
| active | 8 | 活跃中 |
| developing | 5 | 发展中 |
| stable | 0 (样本) | 已稳定 (pipeline 重聚合后稳定事件较少) |

> Dashboard: active_events=185, critical_events=15。

## 文章 Tier 分布 (2026-08-03)

| Tier | 数量 | 平均分 | 增强方式 |
|:----:|:----:|:------:|----------|
| A | 10 | 88 | DeepSeek V4 Flash |
| B | 1650 | 70 | Qwen3-1.7B |
| C | 58 | 50 | Python 规则 |
| (空) | 1 | 0 | 未评分 |

## 常用查询

```sql
-- 最新事件
SELECT event_id, title, event_type, stage, confidence 
FROM events ORDER BY first_seen DESC LIMIT 10;

-- 高置信度活跃事件
SELECT event_id, title, event_type, confidence, source_count 
FROM events WHERE stage = 'active' AND confidence > 0.8 
ORDER BY confidence DESC;

-- 按国家统计事件
SELECT location_country, COUNT(*) as cnt 
FROM events WHERE location_country IS NOT NULL 
GROUP BY location_country ORDER BY cnt DESC LIMIT 10;

-- 热门文章
SELECT title, source_name, score_total, tier 
FROM articles WHERE is_published = true 
ORDER BY score_total DESC LIMIT 10;

-- Tier A 文章
SELECT title, source_name, score_total FROM articles 
WHERE tier = 'A' ORDER BY score_total DESC;

-- 策略成功率
SELECT strategy, SUM(ok_count) as ok, SUM(fail_count) as fail,
       ROUND(SUM(ok_count)*100.0/SUM(ok_count+fail_count), 1) as rate
FROM fetch_stats GROUP BY strategy ORDER BY ok DESC;

-- 文章全文搜索 (GIN 索引)
SELECT title, source_name, score_total FROM articles 
WHERE to_tsvector('english', coalesce(title,'') || ' ' || coalesce(summary,'')) 
      @@ to_tsquery('english', 'iran & strike');
```

## 实体关系图

```
sources ──→ articles ──→ events ──→ story
  │            │  │          │  │        │
  │            │  │          │  │        └── story_event (M:N, position 排序)
  │            │  │          │  ├── insights (LLM)
  │            │  │          │  ├── event_relations (precedes 时间序)
  │            │  │          │  ├── event_article_override (手动归入)
  │            │  │          │  ├── event_article_exclusion (手动剔除)
  │            │  │          │  ├── fact ── fact_entity (Role 模型)
  │            │  │          │  │
  │            │  │          ▼  │
  │            │  └──── event_article (M:N)
  │            │
  │            ├── article_category (M:N) ── categories
  │            ├── article_tag (M:N) ── tags
  │            └── article_entity (M:N) ── entities ── entity_alias
  │                                          │
  │                                          └── entity_relationship (from/to)
  └─── fetch_stats (Pipeline 统计)
```

## 数据流 (Pipeline → DB)

```
本地 news_intel.db (SQLite)
  → POST /internal/news/batch  (articles 表, 分块 50 篇/批)
  → POST /internal/events/batch (events 表, 30 字段/事件)
  → POST /internal/facts/batch  (fact + fact_entity, Step 4.5 混合抽取)
  → POST /internal/fetch_stats  (fetch_stats 表, 策略统计)
```

> ✅ fused 指纹已接线 (2026-08-03): auto-pipeline Step 4 抽 fact → Step 4.5 聚合用 facts_by_article (payload 桥接), 无 facts 文章回退 legacy。VPS fact/fact_entity 表随每轮增量。

## 本地 news_intel.db (SQLite, 10 表, 2026-08-12 实查)

路径: `search-engine-v2/scripts/news_intel/news_intel.db`（`db.py` DB_PATH）。数据量: rss_raw=22,722, news_intelligence=22,722, news_content=3,148, event_registry=**478**, entity_registry=**94**, source_registry=66, ab_event=66, ab_bundle=54。

| 表 | 行数 | 关键字段 |
|----|:----:|----------|
| **rss_raw** | 22,722 | id PK, guid UNIQUE, source_name, source_domain, feed_url, article_url UNIQUE, title, description, published_at, category_raw, created_at (复合水印游标 `created_at|id`) |
| **news_intelligence** | 22,722 | id PK, raw_id FK→rss_raw, score_total/source/impact/entity/market/velocity (五维评分), tier (A≥90/B60-89/C<60), category, tags, entities(JSON), scored_at, facts_json |
| **news_content** | 3,148 | id PK, intel_id FK, article_url UNIQUE, content_md/html, content_len, fetch_strategy, retry_count, fetch_at, summary_cn/en, key_points, extraction_method, llm_model, event_id |
| **event_registry** | 478 | event_id PK, title, subject_name/action_type/object_name, location_country, article_ids(JSON), source_count/article_count, confidence, coherence, stage, first_seen/last_updated |
| **entity_registry** | 94 | entity_id PK, canonical_name, aliases, type, country, importance, first_seen/last_seen（Company 46/Person 25/Country 23） |
| **source_registry** | 66 | source_id PK, name, display_name, type, authority, country, language, url |
| **ab_event** | 66 | a_event_id PK, b_event_id, subject_id/name, action_type, object_id/name, n_facts |
| **ab_bundle** | 54 | b_event_id PK, subject_id/name, a_event_ids(JSON) |
| **sync_state** | 1 | key PK (rss_last_synced_at), value (复合水印) |
| **event_registry_bak** | — | 重聚合前备份 |

> 说明: Fact 层在本地**无表**（fact/fact_entity 只在 VPS）。本地事实经 `fact_pipeline_payload.json` → `/internal/facts/batch` 推送 VPS。A/B 事件本地落 SQLite（event_ab.py），再推 VPS `/internal/ab-events`。`sync_state` 水印为复合游标 `created_at|id`（v4.4.3 修复同刻并列漏同步）。
