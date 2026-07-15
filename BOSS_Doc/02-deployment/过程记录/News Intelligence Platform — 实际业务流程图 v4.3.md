

---

## 产出

### 详细业务流程图

[detail-flow.html](<C:/Users/ChangHui/AppData/Local/hermes/profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/news_intel/detail-flow.html>)

### 关键纠正

你之前的分析说 search-engine-v2 "没有任何真实网络请求代码"——这在 **cascade.py/Agent模式** 是对的，但 **batch.py 是独立的真实实现**：

| 你的分析 | 实际代码状态 |
|------|------|
| "web_extract是Callable占位符" | ✅ batch.py 用 `core/fetchers.py` — 563行 httpx+trafilatura **真实实现** |
| "scrapling_fetch没引入" | ✅ fetchers.py 已 import Scrapling StealthyFetcher |
| "browser_navigate没实现" | ✅ fetchers.py 已实现 Playwright headless |
| "rate_limiter.py没被引用" | ✅ RateLimiter **内置**在 fetchers.py (token bucket per-domain) |
| "MIN_CONTENT_LEN硬编码" | ✅ 已抽出到 config/settings.py |
| "每次抓取都要Agent会话" | ❌ **错** — batch.py 用 ThreadPoolExecutor(4) 独立运行 |

### 两套模式并存

```
🟢 模式A: Standalone (cron)     🔴 模式B: Agent (人工)
   batch.py                          cascade.py
   ├─ core/fetchers.py (真实)        ├─ HermesToolbox (Callable)
   ├─ httpx + trafilatura            ├─ 等待Agent注入 web_extract
   ├─ Playwright headless            ├─ 等待Agent注入 browser_navigate
   └─ 零Agent依赖                    └─ 每次需要Agent会话
```

**模式A 已经解决了你提出的"目标2批量抓取"问题** — 可以把 `batch.py` 直接放进 cron，不需要任何 Agent 参与。

### 当前启用矩阵

| Phase | 模块 | 状态 | 依赖 |
|-------|------|:--:|------|
| 0 触发器 | Hermes cron (每30min) | ✅ | Hermes gateway 运行中 |
| 1 采集 | RSS Scanner → rss-archive.db | ✅ | feedparser, SOCKS5 |
| 1 评分 | sync.py + scorer.py | ✅ | source_scores.json |
| 2 全文抓取 | **batch.py + fetchers.py** | ✅ | httpx, trafilatura, Chromium |
| 2 抓取(Agent) | cascade.py + demo.py | ⚠️ | Hermes Agent 会话 |
| 3 聚合 | aggregator.py v4.3 | ✅ | 零依赖 |
| 4 增强 | enhancers.py Tier A/B | ⚠️ | QWEN_API_KEY / DEEPSEEK_API_KEY |
| 4 增强 | enhancers.py Tier C | ✅ | 零依赖 |
| 5 输出 | pusher.py → FastAPI | ✅ | NEWS_API_BASE 环境变量 |
| 5 分析 | Phase 2 情报分析 | ❌ | 规划中 |