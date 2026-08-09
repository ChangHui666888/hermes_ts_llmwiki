# News Intelligence Platform — 完整业务工作流

> 生成时间: 2026-07-11 | 版本: V4 frozen (历史编号) | 最后更新: 2026-08-07
>
> ⚠️ **本文档的 L0-L9 是旧 V4 编号（L8=事件聚合）。当前权威分层文档是 [pipeline-l0-l7-rules.md](pipeline-l0-l7-rules.md)（L0-L7: RSS→评分→抓取→抽取→增强→L4.5 Fact→聚合→同步→Web）。** 事件聚合现为 L5 (V4.4+), Fact 层为 L4.5。下文历史段落保留作参考。
>
> **注意: 各子系统有独立详细文档**
> - [🎨 前端详情](frontend.md) — Next.js 16, 21 页面, 19 组件
> - [⚙️ 后端详情](backend.md) — FastAPI, 60 端点, 27 ORM 模型
> - [🗄️ 数据库详情](database.md) — PostgreSQL, 27 ORM 表, ER 图, 查询示例
> - [🧩 知识库](knowledge-base.md) — 全球实体关系 (10本体 YAML + 中英别名 → Entity ID)

---

## 当前架构 (2026-08-07, 权威)

```
本地 Windows (Hermes + cron)
  rss-scanner (5m) → ~/.hermes/rss-archive.db (98 源, 中文: 人民网/中新网直连 + DW中文/RFI中文/BBC中文走代理)
  config-agent (5m): VPS 配置中心 → ~/.hermes/pipeline-config.json (60s 轮询 + :8890 推送)
  auto-pipeline (15m) 8 步 (auto-pipeline.py):
    Step0   清理占位行 → Step1 sync.py 水印游标 → news_intel.db (五维评分/tier)
    Step2   RSS 描述兜底 → Step3 batch.py 级联抓全文 (direct→…→browser)
    Step3.5 Recovery (SearXNG/Tavily 补抓) → Step3.6 视频子批 (browser+stealth)
    Step4   fact_pipeline (GLiNER + Qwen noThink + Canonicalizer) → fact payload
    Step4.5 aggregator (fused 指纹, 含中文聚合 v4.4.3 + CJK 信任门)
    Step4.6 event_normalizer (同标题合并, 云端删重复)
    Step5/6 并行 HTTP POST → VPS (events + news content + facts)
    ↓ HTTP (Tailscale 内网 + X-Internal-Token)
VPS (100.107.117.23, Docker 4 容器)
  Nginx :80 → FastAPI :8000 /api/* /internal/* /admin/* /auth/* | Next.js :3000
  PostgreSQL 27 ORM 表 (events/articles/fact/fact_entity/entities/entity_alias/
    entity_relationship/story/story_event/event_relations/... + fetch_stats + alembic_version)
    ↑ 配置中心 (admin_config) 读写 settings KV → 本地 config-agent 轮询

Web (Sentinel Intelligence)
  Next.js 21 页面: / 态势中心 /events /stories /entities /articles /map /search /sources /config
  Story 演化层: 同 subject 事件 → story (时间线打包, 非因果)
  实体画像: KB(27K 实体/41K 别名) + 事件派生 双层数据
```

关键演进 (2026-08-06/07): **v4.4.3 中文聚合**（中文源采集→Qwen 事实抽取→KB 中英别名归一→保守跨语言匹配）；**Knowledge Base V1**（10 本体 YAML + 中英别名→Entity ID, 8,038 公司/18,790 人物/249 国）；**Story 演化层**（story+story_event, 时间线打包）；**实体画像/关系网络**（entity_alias/entity_relationship, sync_kb_to_db 27K 实体入库）；**配置中心 14 Tab**（RSS/Pipeline/AI/评分/聚合/抓取/源列表/域名/状态/事件校对/实体管理/实体关系/数据模型/监控）。详见 [pipeline-l0-l7-rules.md](pipeline-l0-l7-rules.md) v4.4.3 节 与 [knowledge-base.md](knowledge-base.md)。

---

## 总览 (V4 历史)

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
│   ├── web/                 Vue.js + Vite + nginx (已冻结，不运行)
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
98源 → feedparser → SQLite rss-archive.db
境外走 SOCKS5 :10808, 国内直连
```

| 参数 | 值 | 位置 |
|------|:--:|------|
| 采集频率 | 5min | Hermes Cron |
| RSS 源数 | 98 (10 类, 含中文央媒/国际中文源) | `rss-scanner.py` FEEDS |
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

## L10 — Fact Layer (混合抽取, Schema V1.0, 2026-08-03)

> 事实层是 News Intelligence 的原创核心模型（OpenCTI 无 donor）。抽取器=LLM(Qwen noThink) + GLiNER + Canonicalizer。

### 混合策略（串联并联）
```
并发: A(规则,喂GLiNER实体,毫秒) + C(GLiNER,1s)
串行:
  1. A 验证: subject+object 在标题 且 action有效 → A(毫秒)
  2. C 验证: GLiNER 主体类+客体类 score≥0.4 → C(1s)
  3. 否则 B(Qwen noThink) → 兜底 (2.2s/篇, 8.5×提速)
→ Canonicalizer v0.4 → fact + fact_entity 入库
```

### 数据流
```
article → GLiNER(实体锚定,串行) → ThreadPool[快路径A/C | B noThink] → Canonicalizer → fact/fact_entity
本地 pipeline Step 4.5 → POST /internal/facts/batch → VPS fact + fact_entity 表
```

### 实测（50篇）
- B(Qwen) mean 1.13 通过93.3% (人工评审) → 主抽取器
- A验证通过 100% 准确; 纯新闻 B 占比 74% (内容复杂度下限)
- B noThink: 18.6s → 2.2s (8.5×), 覆盖100% 质量可比
- 调优: A喂GLiNER实体(subject 0→24%), Canonicalizer v0.4(标题仅覆盖弱动作)

### 文档
- 规划: `references/data-model-upgrade-plan.md` · 实验: `references/fact-layer-experiment-design.md`
- Schema: `references/fact-schema-v1.md` · 调优: `references/fact-extractor-tuning.md`
- 抽取器: `scripts/news_intel/fact_pipeline.py`(多线程) · 迁移: `migrations/versions/0001_fact_tables.py`

---

## Pipeline 运行时

| 参数 | 值 | 位置 |
|------|:--:|------|
| Sync 时间窗口 | 2h (可配 `pipeline.sync_hours`) | `auto-pipeline.py` Step 1 |
| Fetch 批量 | 20 篇/批 (Step 3) · 聚合 300 篇 (Step 4.5) | `auto-pipeline.py` |
| Cron 频率 | every 15m (auto-pipeline) | Hermes Cron |
| 日志 | `scripts/pipeline.log` (分步统计) | `auto-pipeline.py:39` |
| 进程锁 | `.pipeline.lock` (防并发) | `auto-pipeline.py` |

---

## 数据库三层架构

```
本地 SQLite                本地 SQLite               云 PostgreSQL
─────────────              ─────────────             ─────────────
rss-archive.db             news_intel.db             news_intel
  rss_articles (1表)         rss_raw                   sources / articles / events
                             news_intelligence         entities / entity_alias / entity_relationship
                             news_content              fact / fact_entity
                             event_registry            story / story_event / event_relations
                             source_registry           event_article_override / event_article_exclusion
                             entity_registry           settings / fetch_stats
                             sync_state (水印)          + 关联表 (event_article/event_entity/article_*)
```

---

## 调度

| 任务 | 调度器 | 频率 |
|------|------|:--:|
| rss-scanner | Hermes Cron | 5min |
| auto-pipeline | Hermes Cron | 15min |
| config-agent | 后台常驻 | 60s 轮询 |
| git-backup | Task Scheduler | 每日 12:00 |
| full-backup | Task Scheduler | 每日 18:00 |

---

## 模型

| 模型 | 用途 | 位置 | 成本 |
|------|------|------|:--:|
| deepseek-v4-flash | Tier A 增强 + Tier A 洞察 + Hermes 会话 | API | ~$0.002/次 |
| qwen3-1.7b-instruct | Tier B 增强 + 洞察 + Fact 抽取兜底 | LM Studio :1234 | 免费 |
| GLiNER (gliner_small-v1 / multi-v2.1) | Fact 层实体锚定 (无 LLM) | 本地 torch | 免费 |

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