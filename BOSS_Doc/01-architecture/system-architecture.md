# News Intelligence Platform — 完整业务工作流

> 生成时间: 2026-07-11 | 版本: V4 frozen

---

## 总览

```
L0 RSS采集 → L1 五维评分 → L2 三路分流 → L3 全文抓取 → L4 结构抽取
→ L5 时间校验 → L6 三层增强 → L7 云端入库 → L8 事件聚合 → L9 洞察生成

  ←── 规则引擎 (0 LLM) ──→  ← LLM增强 →  ← 规则 ──→  ← LLM ──→
  
  
  
  
  
  
  
  
  
  

  ```plain
search-engine-v2/scripts/
│
├── news_intel/              数据生产层 (Pipeline)
│   ├── aggregator.py        RSS → Score → Fetch → Aggregate → Event Dossier
│   ├── db.py                写 event_registry/ source_registry/ entity_registry
│   ├── scorer.py            五维评分 (source/impact/entity/market/velocity)
│   ├── batch.py             全文抓取 (httpx/trafilatura/Scrapling/Playwright)
│   ├── enhancers.py         三级增强 (Python规则/ Qwen3/ DeepSeek)
│   ├── pipeline.py          主编排入口
│   ├── pusher.py            推送到云端 (POST /internal/news/batch)
│   └── news_intel.db        ← SQLite 数据库 (9 events, 12 sources, 80 articles)
│
├── news-intel-platform/     旧版 Web (已冻结，不运行)
│   ├── api/                 FastAPI + PostgreSQL + JWT auth
│   ├── web/                 Vue.js + Vite + nginx
│   └── docker-compose.yml   3 容器 (postgres + api + web) → 全部 Down 9h+
│
└── news-intel-web/          Sentinel V1 (当前运行)
    ├── backend/             FastAPI 只读适配器 ← 读 news_intel/news_intel.db
    ├── frontend/            Next.js 16 ← 调 backend API
    └── docker-compose.yml   云端运行 (100.107.117.23:80)
```

**数据流**：`news_intel/` 生产数据 → `news-intel-web/` 消费展示。`news-intel-platform/` 是历史系统，不动。


`news_intel/` 生产数据
```

| 层 | 环节 | LLM | 触发条件 | 单次耗时 | 成本 |
|:--:|------|:--:|------|:--:|:--:|
| L0 | RSS采集 | 🚫 | cron 5min | 16s | $0 |
| L1 | 五维评分 | 🚫 | 每篇 | <1ms | $0 |
| L2 | 三路分流 | 🚫 | if-else | <1μs | $0 |
| L3 | 全文抓取 | 🚫 | 仅 Tier A/B | 1-5s/篇 | $0 |
| L4 | 结构抽取 | 🚫 | 每篇 | 0.78ms | $0 |
| L5 | 时间校验 | 🚫 | 每篇 | <1ms | $0 |
| L6 | 三层增强 | 🤖 Qwen3/DeepSeek | Tier A/B | 15s/篇(Qwen) | ~$0.002(A) |
| L7 | 云端入库 | 🚫 | 批量 POST | 2s/批 | $0 |
| L8 | **事件聚合** | 🚫 | 每次pipeline | 0.0s | **$0** |
| L9 | 洞察生成 | 🤖 Qwen3/DeepSeek | 每个事件 | 3-5s | ~$0.002 |

---

## L0 — RSS 采集

```
rss-scanner.py (Hermes cron, every 5m, no-agent)
94源 → feedparser → SQLite rss-archive.db
境外走 SOCKS5 :10808, 国内直连
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| 采集频率 | 5min | Hermes Cron |
| RSS 源数 | 94 (境外76 + Nitter18 + 国内6) | `rss-scanner.py:49-160` |
| 隔离失败次数 | 3 | `rss-scanner.py:255` |
| 隔离时长 | 30min (1800s) | `rss-scanner.py:255` |
| 去重键 | `link` UNIQUE | `rss-archive.db` |
| description 截断 | 300字符 | `rss-scanner.py` |
| 数据库 | `~/.hermes/rss-archive.db` | 1表 `rss_articles` |
| 🚫 LLM | 无 | |

---

## L1 — 五维评分

```
sync_recent() → score_article(source_name, title, description, velocity_count)
去重: 查 rss_raw.article_url 跳过已评分
```

| 维度 | 满分 | 方法 | 位置 |
|------|:--:|------|------|
| Source Authority | 20 | `source_scores.json` 查表 (70+源) | `scorer.py:68` |
| Event Impact | 30 | `event_keywords.json` 5领域关键词, 同类取最高 | `scorer.py:78` |
| Entity Importance | 20 | `entity_weights.json` 查表 (公司/人物/国家) | `scorer.py:109` |
| Market Relevance | 20 | `asset_graph.json` 资产映射 | `scorer.py:135` |
| Velocity | 10 | Jaccard指纹 ±30min: 0源→0, 2源→2, 5源→5, 10源→10 | `scorer.py:181` |

| 参数 | 值 | 位置 |
|------|:--:|------|
| 总分封顶 | 100 | `scorer.py:241` |
| Velocity 窗口 | 30min | `scorer.py:295` |
| Jaccard 阈值 | ≥0.5 | `scorer.py:295` |
| 停用词 | 38个 | `scorer.py:274-277` |
| 指纹词数 | 8 | `scorer.py:278` |
| 🚫 LLM | 无 (纯查表+正则) | |

---

## L2 — 三路分流

```
score ≥ 90  → Tier A   DeepSeek V4 Flash
score 60-89 → Tier B   Qwen3-1.7B
score <60   → Tier C   Python 规则
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| Tier A 门槛 | ≥90 | `scorer.py:244` |
| Tier B 区间 | 60-89 | `scorer.py:246` |
| 评分去重 | 查 `rss_raw.article_url` | `sync.py:47-48` |
| 增强去重 | `LEFT JOIN news_content WHERE nc.id IS NULL` | `pipeline.py:66` |
| 🚫 LLM | 无 | |

---

## L3 — 全文抓取 (仅 Tier A/B)

```
batch.py → 域名画像 → 代理路由(境外:10808/国内直连) → 级联降级 → RateLimiter
```

| 策略 | 实现 | 超时 | 成本 |
|------|------|:--:|:--:|
| direct | httpx + trafilatura | 30s | 1 |
| google_cache | webcache.googleusercontent.com | 30s | 1 |
| archive | web.archive.org/web/0/{url} | 30s | 1 |
| scrapling | StealthyFetcher | 45s | 2 |
| browser | Playwright headless | 60s | 3 |

| 参数 | 值 | 位置 |
|------|:--:|------|
| MIN_CONTENT_LEN | 200字符 | `settings.py:23` |
| RateLimit 默认 | 1.0s | `settings.py:30` |
| RateLimit 友好域名 | 0.5s (reuters/apnews/bbc) | `settings.py:56-58` |
| 并发线程 | 4 | `settings.py:39` |
| 重试次数 | 2 | `settings.py:40` |
| 🚫 LLM | 无 | |

---

## L4 — 脚本结构化抽取

```
core/extractor.py — 纯规则 (0.78ms/篇, 1282篇/秒)
```

| 字段 | 方法 |
|------|------|
| 标题 | Markdown H1 |
| 日期 | URL路径 / ISO / "Published" / 中文日期 / 兜底当天 |
| 作者 | 前300字符 "By/Author" 正则 |
| 摘要 | 前2-3语义句 (150字符) |
| 要点 | 信号词(said/暴涨/percent)+统计数字+实体动作 加权Top5 |

| 参数 | 值 | 位置 |
|------|:--:|------|
| 摘要长度 | 150字符 | `extractor.py` |
| 要点数量 | 5 | `extractor.py` |
| 作者搜索范围 | 300字符 | `extractor.py` |
| 🚫 LLM | 无 | |

---

## L5 — 时间一致性校验

```
core/temporal.py — 5条硬规则
```

| 规则 | 说明 |
|------|------|
| URL年 ≠ 标题年 | → HIGH_RISK |
| 发布日期 vs 当前 | → 时效性标记 |
| breaking→1天, analysis→90天 | freshness_mode |
| 🚫 LLM | 无 |

---

## L6 — 三层增强

```
Tier C: enhance_python() → 规则标签+实体+前2句摘要 (0ms)
Tier B: enhance_qwen()  → Qwen3-1.7B, 1次调用 (标签+实体+摘要合并)
Tier A: enhance_deepseek() → DeepSeek V4 Flash (事件+影响+风险+关注点)
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| Qwen 地址 | `http://127.0.0.1:1234/v1` | `enhancers.py:114` |
| Qwen 模型 | `qwen3-1.7b-instruct` | `enhancers.py:115` |
| Qwen 超时 | **60s** | `enhancers.py:134` |
| Qwen max_tokens | **1024** | `enhancers.py:171` |
| Qwen 降级 | 首次失败→全局跳过 | `enhancers.py:117` |
| DeepSeek 模型 | `deepseek-v4-flash` | `enhancers.py:220` |
| DeepSeek 超时 | **45s** | `enhancers.py:263` |
| DeepSeek 降级 | 无Key→Python规则 | `enhancers.py:244` |
| 🤖 LLM | Qwen3本地 (Tier B) / DeepSeek (Tier A) | |

---

## L7 — 云端入库

```
POST /internal/news/batch (一次请求, 30s超时)
FastAPI → PostgreSQL articles (ON CONFLICT url DO UPDATE)
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| API 地址 | `$NEWS_API_BASE` (默认 `http://100.107.117.23:8001`) | `pusher.py:6` |
| Internal Token | `hermes-pipeline-secret-2026` | `pusher.py:7` |
| 推送超时 | 30s (批量) | `pusher.py:44` |
| 失败跳过 | 连续3次→跳过剩余 | `pipeline.py:163` |
| 🚫 LLM | 无 | |

---

## L8 — 事件聚合 (V4 frozen)

```
news_intel/aggregator.py — Event-Centric 3-phase
纯规则引擎, 0 LLM
```

### Phase 1: Article → Event

```
按时间升序 → 提取 SAEO指纹 → 与已有事件比较 → 得分≥50加入/否则新建
```

### Phase 2: Event → Event 合并

```
两两比较事件中心指纹 → 得分≥70 + 时间窗口内 → 合并
```

### Phase 3: Filter

```
过滤单篇事件, 计算 impact_level (HIGH ≥85 / MEDIUM 60-84 / LOW <60)
```

### SAEO 指纹维度

| 维度 | 满分 | 说明 |
|------|:--:|------|
| Action | 35 | 16种动作 (SUES/ATTACKS/SANCTIONS/NEGOTIATES/...) |
| Subject | 25 | 第一个公司/人物 |
| Object | 20 | 国家/第二个实体 |
| Primary Topic | 15 | 12类 (Legal/Military/Diplomacy/Economic/...) |
| Event Type | 5 | 动作对应的事件类型 |

### 规则

| 规则 | 说明 |
|------|------|
| Location 硬约束 | 不同国家 → 直接 0 分 |
| None 时间 | 跳过时间窗口检查 |
| HTML 描述过滤 | HTML含量 >30% → 丢弃, 只用标题 |
| 时间窗口 | 24h (参数化) |

| 参数 | 值 | 位置 |
|------|:--:|------|
| EVENT_THRESHOLD | 50 | `aggregator.py:205` |
| MERGE_THRESHOLD | 70 | `aggregator.py:206` |
| 时间窗口 | 24h | `aggregator.py:224` |
| 动作词库 | 16种 | `aggregator.py:26-42` |
| Topic 词库 | 12类 (60+关键词) | `aggregator.py:59-73` |
| 国家词库 | 46个 | `aggregator.py:93-100` |
| 日期解析 | ISO + email.utils | `aggregator.py:209-222` |
| 🚫 LLM | 无 (纯规则引擎) | |

---

## L9 — 洞察生成

```
generate_for_event() — 自动路由:
  HIGH/Tier A → DeepSeek V4 Flash
  其余 → Qwen3-1.7B
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| Qwen 超时 | 30s | `generator.py:53` |
| Qwen max_tokens | 400 | `generator.py:57` |
| DeepSeek 超时 | 30s | `generator.py:69` |
| DeepSeek max_tokens | 500 | `generator.py:76` |
| DeepSeek temperature | 0.1 | `generator.py:77` |
| 路由规则 | HIGH→DeepSeek, 其余→Qwen3 | `generator.py:97-99` |
| 🤖 LLM | Qwen3 (免费) / DeepSeek (~$0.002) | |

---

## Pipeline 运行时

| 参数 | 值 | 位置 |
|------|:--:|------|
| 时间窗口 | 1h | `news-pipeline.py` `--hours 1` |
| 单次上限 | 200篇 | `news-pipeline.py` `--limit 200` |
| Cron 频率 | every 30m | Hermes Cron |
| 报告 | `~/.hermes/news-pipeline-report.json` | `pipeline.py:243` |
| 日志 | `scripts/logs/news-pipeline.log` | `news-pipeline.py` |

---

## 数据库三层架构

```
本地 SQLite                本地 SQLite              云 PostgreSQL
─────────────              ─────────────             ─────────────
rss-archive.db             news_intel.db             news_intel
  rss_articles (1表)         rss_raw (18字段)          sources
                             news_intelligence (17字段) articles (26字段)
                             news_content (19字段)      entities
                                                        events
                                                        insights
                                                        categories, tags
                                                        + 6 关联表
```

---

## 调度

| 任务 | 调度器 | 频率 |
|------|------|:--:|
| rss-scan | Hermes Cron | 5min |
| news-pipeline | Hermes Cron | 30min |
| git-backup | Task Scheduler | 每日 12:00 |
| full-backup | Task Scheduler | 每日 18:00 |

---

## 模型

| 模型 | 用途 | 位置 | 成本 |
|------|------|------|:--:|
| deepseek-v4-pro | Hermes 对话 | API | — |
| deepseek-v4-flash | Tier A 增强 + Tier A 洞察 | API | ~$0.002/次 |
| qwen3-1.7b-instruct | Tier B 增强 + 洞察 | LM Studio :1234 | 免费 |

---

## 日均估算

```
200篇 RSS → 16篇 Tier A/B (8%) → Qwen3增强 (每篇1次, ~15s)
       → 0-1篇 Tier A → DeepSeek
       → L8 聚合 → 4-7事件 (纯规则, 0.0s)
       → L9 洞察 → 4-7次 LLM (3s/次)

日均 LLM: ~30次 Qwen3 + 1-3次 DeepSeek
日均费用: < $0.01
```






---

## v4.4 升级完成报告

### 6/6 任务全部完成

| # | 任务 | 文件 | 状态 |
|:--:|------|------|:--:|
| 1 | Phase 3.5 Event Registry | `db.py` +6表(event/source/entity_registry) | ✅ |
| 2 | Source Entity ID | `aggregator.py` `_source_name_to_id()` | ✅ |
| 3 | Entity ID 标准化 | `aggregator.py` `_entity_name_to_id()` | ✅ |
| 4 | Event Dossier 增强 | `aggregator.py` evidence + source_chain + timeline | ✅ |
| 5 | Event API 推送 | `pusher.py` `push_events()` + `push_from_registry()` | ✅ |
| 6 | Event-level LLM | `generator.py` `generate_intel()` + `_format_event_dossier()` | ✅ |

### 升级后的架构

```
                    之前 (v4.3)                          现在 (v4.4)
                    ──────────                          ──────────
Phase 3        Event Object ──────────────>    Event Dossier
               (21 fields, 内存)                (21 + 3 fields, 持久化)
                                                ├─ evidence [quotes + sources]
                                                ├─ source_chain [break/follow]
                                                └─ timeline [key moments]

Phase 3.5      ❌ 不存在                          ✅ event_registry 表
                                                ✅ source_registry (SRC_*)
                                                ✅ entity_registry (COMP_/PERS_/CTRY_)

Phase 4        Article-level LLM                Event-level LLM
               "这篇文章说什么"                   "这个事件意味着什么"
                                                用 evidence + timeline 做分析

Phase 5        POST /internal/news/batch         + POST /internal/events/batch
               (推送 Article)                    (推送 Event Dossier → 云端)
```

### 验证

```
python test_aggregator.py --hours 24 --window 6 --limit 100

输出示例:
  EVT-20260710-006 | Apple → SUES → OpenAI
  evidence: [DW News] Apple has accused the company behind ChatGPT...
  first break: DW News @ 2026-07-10T00:00:00
  follow sources: The Verge
  timeline: 1 key moments

  → event_registry 写入 9 条 event
  → source_registry 写入 25+ 条 source
```

### 云端推送

```bash
python -c "
from news_intel.pusher import push_from_registry
print(push_from_registry(stage='active', limit=50))
"
# POST /internal/events/batch → 20+ field per event → cloud PostgreSQL
```