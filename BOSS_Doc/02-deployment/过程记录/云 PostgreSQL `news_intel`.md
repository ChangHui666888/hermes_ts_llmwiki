

## 完整数据库清单

### 总览

```
本地 SQLite                          云 PostgreSQL
─────────────                        ─────────────
rss-archive.db (1表)                 news_intel (6表)
news_intel.db   (3表)
```

---

## 一、本地 `rss-archive.db` (SQLite)

**位置** `~/.hermes/rss-archive.db`

### `rss_articles` — RSS 原始采集

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK | 唯一 ID |
| `date` | TEXT | RSS pubDate |
| `category` | TEXT | 分类（10类） |
| `source` | TEXT NOT NULL | 来源名称 |
| `title` | TEXT | 标题 |
| `summary` | TEXT | 摘要(前300字符) |
| `link` | TEXT UNIQUE | 文章 URL（去重键） |
| `created_at` | TEXT | 入库时间 |

---

## 二、本地 `news_intel.db` (SQLite)

**位置** `search-engine-v2/scripts/news_intel/news_intel.db`

### `rss_raw` — RSS 原始数据（扩展版）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `guid` | TEXT UNIQUE | URL 去重 |
| `source_name` | TEXT | 来源名称 |
| `source_domain` | TEXT | 域名 |
| `feed_url` | TEXT | RSS 源 URL |
| `article_url` | TEXT | 文章 URL |
| `title` | TEXT | 标题 |
| `description` | TEXT | 摘要 |
| `content_encoded` | TEXT | 部分正文 |
| `author` | TEXT | 作者 |
| `published_at` | TEXT | 发布时间 |
| `updated_at` | TEXT | 更新时间 |
| `language` | TEXT | 语言 |
| `category_raw` | TEXT | 原始分类 |
| `tags_raw` | TEXT | 原始标签 |
| `image_url` | TEXT | 图片 URL |
| `enclosure_url` | TEXT | 附件 URL |
| `raw_xml` | TEXT | 原始 XML |
| `created_at` | TEXT | 入库时间 |

### `news_intelligence` — 评分 + 分类

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `raw_id` | INTEGER FK → rss_raw | |
| `score_total` | INTEGER | 总分 0-100 |
| `score_source` | INTEGER | 来源分 0-20 |
| `score_impact` | INTEGER | 影响力 0-30 |
| `score_entity` | INTEGER | 实体分 0-20 |
| `score_market` | INTEGER | 市场关联 0-20 |
| `score_velocity` | INTEGER | 传播速度 0-10 |
| `tier` | TEXT | A/B/C |
| `category` | TEXT | 分类 |
| `tags` | TEXT(JSON) | `["AI","NVIDIA"]` |
| `entities` | TEXT(JSON) | `{"companies":[],"persons":[],"countries":[]}` |
| `importance` | TEXT | critical/high/medium/low |
| `velocity_count` | INTEGER | 同事件报道数 |
| `scored_at` | TEXT | 评分时间 |

### `news_content` — 正文 + 分析

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `intel_id` | INTEGER FK → news_intelligence | |
| `article_url` | TEXT UNIQUE | |
| `content_md` | TEXT | Markdown 正文 |
| `content_len` | INTEGER | 正文字数 |
| `fetch_strategy` | TEXT | direct/archive/google_cache |
| `fetch_cost` | INTEGER | 抓取成本 |
| `summary_cn` | TEXT | 中文摘要 |
| `summary_en` | TEXT | 英文摘要 |
| `key_points` | TEXT(JSON) | `["要点1","要点2"]` |
| `source_headline` | TEXT | 原标题 |
| `published_at` | TEXT | 发布日期 |
| `author_name` | TEXT | 作者 |
| `extraction_method` | TEXT | rule_based/qwen3/deepseek-flash |
| `llm_model` | TEXT | 使用的模型 |
| `llm_cost` | REAL | LLM 费用 |
| `temporal_check` | TEXT(JSON) | 时间校验结果 |
| `created_at` | TEXT | 入库时间 |

---

## 三、云 PostgreSQL `news_intel`

**位置** `100.107.117.23:5432` (Docker 内网)

### `articles` — 新闻（主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `url` | VARCHAR(2048) UNIQUE | 去重键 |
| `title` | VARCHAR(500) | |
| `summary` | TEXT | 英文摘要 |
| `summary_cn` | TEXT | 中文摘要 |
| `content_md` | TEXT | Markdown 正文 |
| `content_len` | INTEGER | |
| `source_name` | VARCHAR(200) | |
| `source_domain` | VARCHAR(200) | |
| `published_at` | TIMESTAMP | |
| `category` | VARCHAR(100) | |
| `importance` | VARCHAR(20) | critical/high/medium/low |
| `tags` | JSON | `["AI","NVIDIA"]` |
| `entities` | JSON | `{"companies":[],"persons":[],"countries":[]}` |
| `score_total` | INTEGER | 0-100 |
| `score_breakdown` | JSON | 五维明细 |
| `tier` | VARCHAR(1) | A/B/C |
| `analysis` | JSON | AI 分析结果 |
| `key_points` | JSON | 关键要点 |
| `extraction_method` | VARCHAR(50) | |
| `fetch_strategy` | VARCHAR(50) | |
| `fetch_cost` | INTEGER | |
| `is_published` | BOOLEAN | 是否发布 |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### `users` — 用户

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `email` | VARCHAR(255) UNIQUE | |
| `password_hash` | VARCHAR(255) | SHA256 |
| `level` | VARCHAR(20) | free/vip/admin |
| `expire_at` | TIMESTAMP | VIP 过期 |
| `created_at` | TIMESTAMP | |

### `subscriptions` — 标签订阅

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER | |
| `tag` | VARCHAR(100) | |
| `created_at` | TIMESTAMP | |

### `ads` — 广告

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `title` | VARCHAR(200) | |
| `image_url` | VARCHAR(500) | |
| `link_url` | VARCHAR(500) | |
| `position` | VARCHAR(50) | sidebar/banner/inline |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMP | |

### `settings` — 系统配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `key` | VARCHAR(100) UNIQUE | |
| `value` | TEXT | |
| `updated_at` | TIMESTAMP | |

### `logs` — 操作日志

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `action` | VARCHAR(100) | |
| `detail` | TEXT | |
| `ip` | VARCHAR(50) | |
| `created_at` | TIMESTAMP | |

---

## 数据流

```
rss-scanner.py
    │
    ▼
rss-archive.db  (rss_articles)
    │
    ▼ sync_recent()
news_intel.db
    ├── rss_raw           ← 原始数据
    ├── news_intelligence ← 评分 + 分类
    └── news_content      ← 正文 + 分析
    │
    ▼ push_batch()
POST /internal/news/batch
    │
    ▼
PostgreSQL
    └── articles          ← 网站展示
```