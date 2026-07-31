# 数据库 — PostgreSQL 16

> 最后更新: 2026-07-31
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
| evidence | ✅ | 证据引用 |
| source_chain | ✅ | 来源链 |
| timeline | ✅ | 时间线 |
| llm_analysis | ✅ | AI 分析面板 |
| article_ids | ❌ | 内部关联, 未展示 |
| doc_refs | ❌ | 引用文档, 未展示 |
| first_seen/last_updated | ✅ | 时间 |
| extraction_method | ❌ | 抽取方式 |
| id/created_at | ❌ | 内部字段 |
| **tone** | ❌ | 🔮 扩展: 情绪/语气分析 |
| **goldstein** | ❌ | 🔮 扩展: 冲突-合作量表 (Goldstein Scale) |

### articles 表 (31 列) — 前端使用/未用/扩展

| 字段 | 前端使用 | 说明 |
|:-----|:--------:|:-----|
| id/url | ✅ | 标识/链接 |
| title | ✅ | 标题 |
| summary_cn | ✅ | 中文摘要 (自动回退正文前200字) |
| summary | ❌ | 英文摘要, 未展示 |
| content_md | ✅ | 全文 (VIP/Admin) |
| content_len | ❌ | 内部 |
| source_name/domain | ✅ | 来源 |
| published_at | ✅ | 发布时间 |
| category | ✅ | 分类 |
| tier | ✅ | 级别徽章 |
| score_total | ✅ | 评分 |
| score_breakdown | ❌ | 五维明细, 未展示 |
| tags | ✅ | 标签 |
| entities | ✅ | 实体 |
| analysis | ✅ | AI 分析 (VIP) |
| key_points | ❌ | 要点, 未展示 |
| importance/importance_level | ❌ | 重要度, 未展示 |
| fetch_strategy/fetch_cost | ❌ | 抓取策略, 运维用 |
| extraction_method | ❌ | 抽取方式 |
| language | ❌ | 语言 |
| status/is_published | ✅ | 查询过滤用 |
| is_duplicate | ❌ | 去重标记 |
| source_id | ❌ | FK |
| created_at/updated_at/fetched_at | ❌ | 时间戳 |

## 🔮 扩展方向

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

## 总览

| 项目 | 值 |
|------|-----|
| 数据库 | `news_intel` |
| 用户 | `news_admin` |
| 密码 | `news_pass` |
| 容器 | `news-platform-v8-postgres-1` (healthcheck: pg_isready) |
| 数据卷 | `news-intel-platform_pgdata` (Docker volume, external) |
| 表数量 | 20 |
| Pool | 连接池 10, 最大溢出 20 |

## 数据量统计

| 表 | 行数 | 说明 |
|----|:----:|------|
| events | **125** | 事件 Dossier (聚合优化后精确事件) |
| articles | **1349** | 文章 (Tier A=10, B=1337, C=1) |
| sources | 24 | RSS 来源注册 |
| users | 3 | 管理员/免费用户 |
| fetch_stats | ~ 数百 | 抓取策略统计 |

## 完整表结构 (20 表)

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

### 5–20. 关联表

| 表 | 列 | 说明 |
|----|-----|------|
| **entities** | id, name, type, country, importance | 实体注册表 |
| **categories** | id, name, parent_id | 分类层级 |
| **tags** | id, name (UNIQUE) | 标签库 |
| **ads** | id, title, image_url, link_url, position, is_active | 广告管理 |
| **assets** | id, type, symbol, name, exchange | 金融资产 |
| **settings** | id, key (UNIQUE), value(JSONB), updated_at | Pipeline 配置 (KV) |
| **logs** | id, level, message, created_at | 系统日志 |
| **insights** | id, event_id(FK), content(JSONB) | LLM 深度洞察 |
| **fetch_stats** | domain, source_name, strategy, ok_count, fail_count, run_at | 抓取统计 |
| **subscriptions** | user_id(FK), tag_id(FK) | 用户订阅 |
| **article_category** | article_id(FK), category_id(FK) | 文章-分类 (M:N) |
| **article_tag** | article_id(FK), tag_id(FK) | 文章-标签 (M:N) |
| **article_entity** | article_id(FK), entity_id(FK), relevance_score | 文章-实体 (M:N) |
| **event_article** | event_id(FK), article_id(FK) | 事件-文章 (M:N) |
| **event_entity** | event_id(FK), entity_id(FK) | 事件-实体 (M:N) |

## 事件类型分布

| 类型 | 数量 | 占比 |
|------|:----:|:----:|
| General | 161 | 31.4% |
| Finance | 89 | 17.4% |
| Politics | 67 | 13.1% |
| Military | 57 | 11.1% |
| Diplomacy | 53 | 10.4% |
| Economic | 33 | 6.4% |
| Legal | 32 | 6.3% |
| Leadership | 20 | 3.9% |

## 事件阶段分布

| 阶段 | 数量 | 说明 |
|------|:----:|------|
| developing | 324 | 发展中 (63%) |
| active | 133 | 活跃中 |
| stable | 55 | 已稳定 |

## 文章 Tier 分布

| Tier | 数量 | 平均分 | 增强方式 |
|:----:|:----:|:------:|----------|
| A | 10 | 88 | DeepSeek V4 Flash |
| B | 924 | 70 | Qwen3-1.7B |
| C | 1 | 50 | Python 规则 |
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
sources ──→ articles ──→ events
  │            │  │          │
  │            │  │          ├── insights (LLM)
  │            │  │          ├── event_relations (层级)
  │            │  │          │
  │            │  │          ▼
  │            │  └──── event_article (M:N)
  │            │
  │            ├── article_category (M:N) ── categories
  │            ├── article_tag (M:N) ── tags
  │            └── article_entity (M:N) ── entities
  │
  └─── fetch_stats (Pipeline 统计)
```

## 数据流 (Pipeline → DB)

```
本地 news_intel.db (SQLite)
  → POST /internal/news/batch  (articles 表, 分块 50 篇/批)
  → POST /internal/events/batch (events 表, 30 字段/事件)
  → POST /internal/fetch_stats  (fetch_stats 表, 策略统计)
```
