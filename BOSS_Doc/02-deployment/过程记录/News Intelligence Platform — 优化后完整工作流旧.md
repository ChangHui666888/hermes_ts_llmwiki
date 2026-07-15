

---

# News Intelligence Platform — 优化后完整工作流

```
═══════════════════════════════════════════════════════════════════════
                       八层流水线
═══════════════════════════════════════════════════════════════════════

 L0采集 → L1评分 → L2路由 → L3抓取 → L4抽取 → L5校验 → L6增强 → L7入库

  ←── 零 LLM ──→  ← 规则 ──→  ←── 零 LLM ──→  ← 三层增强 ──→
═══════════════════════════════════════════════════════════════════════
```

---

## L0 — RSS 持续采集（已有，不动）

| 项 | 值 |
|------|------|
| 脚本 | `~/.hermes/scripts/rss-scanner.py` |
| 调度 | Hermes cron, 每30min, no_agent |
| 源 | 94 RSS feed，10 分类 |
| 代理 | 境外 → `127.0.0.1:10808`，国内直连 |
| 输出 | `~/.hermes/rss-archive.db`（6字段） |
| **LLM** | 🚫 无 |

---

## L1 — 五维新闻价值评分（`news_intel/scorer.py`）

**输入：** RSS 的 `source_name` + `title` + `description`

```
                 title + description + source_name
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐       ┌──────────┐
   │ Source  │      │  Event   │       │  Entity  │
   │ Authority│     │  Impact  │       │Importance│
   │  (20分)  │     │  (30分)  │       │  (20分)  │
   └────┬─────┘      └────┬─────┘       └────┬─────┘
        │                  │                  │
        │    ┌──────────┐  │   ┌──────────┐   │
        │    │  Market  │  │   │ Velocity │   │
        │    │ Relevance│  │   │  (10分)  │   │
        │    │  (20分)  │  │   └────┬─────┘   │
        │    └────┬─────┘  │        │          │
        │         │        │        │          │
        └─────────┴────────┴────────┴──────────┘
                           │
                           ▼
                    total = min(∑, 100)
```

**五维详解：**

| 维度 | 满分 | 输入 | 方法 | 示例 |
|------|:--:|------|------|------|
| Source Authority | 20 | `source_name` | `source_scores.json` 查表 | Bloomberg→20, The Verge→10, Unknown→5 |
| Event Impact | 30 | `title`+`description` | 5领域关键词匹配（同类取最高，不累加） | ceasefire→28, 降息→30, AI→20 |
| Entity Importance | 20 | `title`+`description` | `entity_weights.json` 查表（取最高） | Trump→20, NVIDIA→20, 比亚迪→15 |
| Market Relevance | 20 | `title`+`entities` | `asset_graph.json` 资产映射 | GPU→NVIDIA/AMD/TSMC(20分) |
| Velocity | 10 | 跨文章指纹比对 | Jaccard≥0.5 + ±30min窗口 | 3源同报→2分, 10源→10分 |

**评分结果示例：**

```
Bloomberg: "Trump Says US-Iran Ceasefire Is Over After Strikes"
  src=20 + imp=28 + ent=20 + mkt=15 + vel=2 = 85 → Tier A

BBC: "Trump says ceasefire is over"
  src=16 + imp=28 + ent=20 + mkt=0 + vel=2 = 66 → Tier B

The Verge: "New smartphone features at MWC"
  src=10 + imp=0 + ent=0 + mkt=0 + vel=0 = 10 → Tier C
```

| 项 | 值 |
|------|------|
| 单篇耗时 | <1ms |
| **LLM** | 🚫 无（纯查表+正则） |

---

## L2 — Intelligence Router（`news_intel/router.py`）

```
score.total
    │
    ├─ ≥85 ──► Tier A → DeepSeek V4 Flash 深度分析
    │
    ├─ 60-84 ─► Tier B → Qwen3-1.7B 本地增强
    │
    └─ <60 ──► Tier C → Python 规则抽取（零成本）
```

**实测分布（60篇真实RSS）：**

```
Tier A:  1篇 ( 1.7%) → DeepSeek 云
Tier B:  6篇 (10.0%) → Qwen3 本地
Tier C: 53篇 (88.3%) → Python 零成本
```

---

## L3 — 级联抓取（`batch.py`，仅 Tier A/B 触发）

```
python batch.py --urls tier_ab_urls.txt --out fetched.jsonl

每个 URL：
  域名画像查表 → 代理路由(境外10808/国内直连) → 级联降级 → RateLimiter
    direct ──403──► google_cache ──404──► archive ──► search_snippet
```

| 项 | 值 |
|------|------|
| 并发 | ThreadPoolExecutor × 4 |
| 单篇成功耗时 | ~1s |
| Tier C 不触发 | 省 88% 抓取配额 |
| **LLM** | 🚫 无 |

---

## L4 — 脚本结构化抽取（`core/extractor.py`，所有 Tiers）

```
Markdown 正文
  ├─ 标题    → Markdown H1
  ├─ 日期    → URL路径 / ISO / "Published" / 中文日期 / 兜底当天
  ├─ 作者    → 前300字符 "By/Author" 正则
  ├─ 摘要    → 前2-3语义句（跳过标头）
  └─ 要点    → 信号词(said/暴涨/percent)+统计数字+实体动作 加权Top5
```

| 项 | 值 |
|------|------|
| 单篇耗时 | 0.78ms |
| 100篇耗时 | 0.078s |
| **LLM** | 🚫 无 |

---

## L5 — 时间一致性校验（`core/temporal.py`）

| 项 | 值 |
|------|------|
| 规则 | 5条硬规则（URL年/标题年/发布日期/正文年 交叉比对） |
| 输出 | `{confidence: high/medium/low, conflicts: [...], stale_warning: bool}` |
| **LLM** | 🚫 无 |

---

## L6 — 三层智能增强（`news_intel/enhancers.py`）

```
根据 Tier 分流：

┌──────────────────────────────────────────────────────────────┐
│ Tier C: enhance_python()                                     │
│  规则推导标签 + 实体合并 + 前2句摘要                            │
│  0ms | $0                                                    │
├──────────────────────────────────────────────────────────────┤
│ Tier B: enhance_qwen()                                       │
│  Qwen3-1.7B @ http://127.0.0.1:1234/v1                       │
│  标签生成 + 实体抽取 + 中文一句话摘要                           │
│  ~2s/篇 | $0（本地免费）                                       │
│  Qwen不可用 → 自动降级 Python                                  │
├──────────────────────────────────────────────────────────────┤
│ Tier A: enhance_deepseek()                                   │
│  DeepSeek V4 Flash @ api.deepseek.com                        │
│  深度分析：事件概括 + 市场影响 + 风险评级 + 未来关注点           │
│  ~3s/篇 | ~$0.002/篇                                          │
│  无API Key → 自动降级 Python                                  │
└──────────────────────────────────────────────────────────────┘
```

**增强输出对比：**

| 字段 | Tier C (Python) | Tier B (Qwen3) | Tier A (DeepSeek) |
|------|:--:|:--:|:--:|
| tags | ✅ 规则 | ✅ LLM精标 | ✅ |
| entities | ✅ 规则 | ✅ LLM抽取 | ✅ |
| summary_cn | ✅ 前2句 | ✅ LLM一句话 | ✅ |
| event | — | — | ✅ 深度概括 |
| impact | — | — | ✅ 市场影响 |
| market_signal | — | — | ✅ bullish/bearish |
| risk_level | — | — | ✅ low~critical |
| future_watch | — | — | ✅ 未来节点 |

---

## L7 — 三层入库（`news_intel/db.py`）

```
news_intel.db
  ├─ rss_raw          — RSS原始数据（不可修改）
  ├─ news_intelligence — 评分 + 分类 + 标签 + 实体
  └─ news_content     — 正文 + 分析结果 + 增强方法标记
```

**news_content 关键字段：**

| 字段 | 来源 | 用途 |
|------|------|------|
| `extraction_method` | `rule_based` / `qwen3` / `deepseek-flash` | 审计增强来源 |
| `llm_model` | 模型名 | 成本追踪 |
| `llm_cost` | `$0.000000` | 成本核算 |
| `summary_cn` | 增强输出 | 中文展示 |
| `temporal_check` | 校验结果 JSON | 时效标记 |

---

## 成本分析

### 单篇成本

| 层级 | 方法 | 耗时 | 费用 |
|------|------|:--:|:--:|
| L0 RSS | cron脚本 | <1s | $0 |
| L1 评分 | 查表+正则 | <1ms | $0 |
| L2 路由 | if-else | <1μs | $0 |
| L3 抓取 | httpx级联 | 1-5s | $0 |
| L4 抽取 | trafilatura+规则 | 0.78ms | $0 |
| L5 校验 | 纯算法 | <1ms | $0 |
| L6 增强 | Python规则 | 0ms | $0 |
| | Qwen3本地 | ~2s | **$0** |
| | DeepSeek云 | ~3s | **~$0.002** |
| L7 入库 | SQLite INSERT | <1ms | $0 |

### 批量成本（100篇）

```
88篇 Tier C × $0      = $0
10篇 Tier B × $0      = $0      (Qwen3本地免费)
 2篇 Tier A × $0.002  = $0.004
─────────────────────────────────
总计                    ≈ $0.004
```

### 对比：如果全部走 LLM

```
100篇 × DeepSeek结构化   = $0.20
100篇 × 全文送DeepSeek   = $0.50+
─────────────────────────────────
优化后节省: 98%+
```

### 月度成本（日均100篇）

| 模式 | 月均抓取 | LLM调用 | 月费 |
|------|:--:|:--:|:--:|
| 全LLM | 3000篇 | 3000次 | ~$6 |
| 优化后 | 3000篇 | ~60次Tier A | **~$0.12** |

---

## 最终架构图

```
                    RSS (94源, 30min cron)
                           │
                    rss-archive.db
                           │
                    ┌──────▼──────┐
                    │  L1 五维评分  │  ← source_scores.json
                    │  0-100分     │  ← event_keywords.json
                    │  <1ms/篇     │  ← entity_weights.json
                    └──────┬──────┘  ← asset_graph.json
                           │
                    ┌──────▼──────┐
                    │  L2 Router  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      Tier C (<60)    Tier B (60-84)    Tier A (≥85)
      88.3%            10.0%             1.7%
          │                │                │
          │           L3 抓全文          L3 抓全文
          │           (batch.py)        (batch.py)
          │                │                │
          ├────────────────┼────────────────┤
          │          L4 脚本抽取            │
          │          L5 时间校验            │
          ├────────────────┼────────────────┤
          │                │                │
      Python规则       Qwen3本地       DeepSeek云
      零成本            零成本          ~$0.002
          │                │                │
          └────────────────┴────────────────┘
                           │
                    news_intel.db
                   (raw / intelligence / content)
                           │
                    ┌──────▼──────┐
                    │  消费端      │
                    │  网站/分析    │
                    └─────────────┘
```

---

## 命令索引

```bash
cd search-engine-v2/scripts/

# 评分 + 增强
python -m news_intel.pipeline --hours 2

# 评分 + 抓全文(Tier A/B) + 增强
python -m news_intel.pipeline --hours 2 --fetch

# 分布统计
sqlite3 news_intel/news_intel.db \
  "SELECT tier,COUNT(*),ROUND(AVG(score_total),1) FROM news_intelligence GROUP BY tier;"

# Tier A 详情
sqlite3 news_intel/news_intel.db \
  "SELECT rr.title,ni.score_total FROM news_intelligence ni
   JOIN rss_raw rr ON ni.raw_id=rr.id WHERE tier='A';"

# 抓取方法审计
sqlite3 news_intel/news_intel.db \
  "SELECT extraction_method,COUNT(*) FROM news_content GROUP BY 1;"
```