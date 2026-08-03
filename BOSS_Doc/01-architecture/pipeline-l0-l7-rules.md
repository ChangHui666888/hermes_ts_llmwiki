# Pipeline L0-L8 加工规则 — 基于代码逻辑

> 严格依据实际代码参数，非概要描述
> 最后更新: 2026-07-31

---

## L0 — RSS 采集 (rss-scanner.py)

### 网络配置

| 参数 | 值 | 代码位置 |
|:-----|:---|:---------|
| 源总数 | 98 (10 类) | FEEDS |
| 并发 workers | 14 | MAX_WORKERS |
| 超时: hot/warm/cold | 6s / 10s / 15s | HOT/TIMEOUT/COLD_TIMEOUT |
| SOCKS5 代理 | `socks5://127.0.0.1:10808` | PROXY |
| 路由规则 | `region==intl` → 代理 / `cn` → 直连 | needs_proxy() |
| User-Agent | `rss-scanner/3.2-final` | USER_AGENT |
| HTTP/2 | 启用 | create_client() |
| 隔离阈值 | 连续失败 ≥3 → 隔离 1800s | update_health() |

### 解析规则

| 规则 | 值 |
|:-----|:---|
| description 截断 | 300 字符 |
| 去重键 | SHA256(源+URL+标题前40字) |
| 增量游标 | 每源 last_seen (首个 link) |
| 报告截断 | new_articles[:50], errors[:30] |
| Wiki 日报 | 每日写入 ~/wiki/RSS-Digest/ |

### 分类规则 (categorize_feed)

```
通讯社: Reuters/AP/Bloomberg/AFP
国家媒体: BBC/CNN/NBC/CBS/NYT/NPR...
金融媒体: FT/WSJ/CNBC/MarketWatch...
科技媒体: TechCrunch/The Verge/Wired...
地缘媒体: Guardian/DW/Al Jazeera...
政府机构: White House/Fed/SEC/UN...
科研: arXiv/OpenAI/GitHub...
实时: Hacker News/Reddit
X/Nitter: 18 源
中文央媒: 人民网/新华网/央视...
```

---

## L1 — 五维评分 (scorer.py)

### 评分公式 (总分100)

```
score_total = source(20) + impact(30) + entity(20) + market(20) + velocity(10)
```

### 各维度规则

| 维度 | 满分 | 方法 | 上限 |
|:-----|:----:|:-----|:----:|
| Source | 20 | source_scores.json 查表, 未知=5 | — |
| Impact | 30 | event_keywords.json 5领域, **同类取最高** (非累加) | min(30) |
| Entity | 20 | entity_weights.json 查表 | min(20) |
| Market | 20 | asset_graph.json 实体/关键词→资产 | min(20) |
| Velocity | 10 | Jaccard 指纹 ±30min | ≥10源=10, ≥5=5, ≥2=2, <2=0 |

### Tier 判定

```
A: score ≥ 90 → DeepSeek
B: 60 ≤ score < 90 → Qwen3
C: score < 60 → Python
```

### Velocity 指纹

```
窗口: 30min
Jaccard 阈值: ≥0.5
指纹词数: 8 (英文>1字符 + 中文)
停用词: 38 个
```

---

## L2 — 全文抓取 (fetchers.py + cascade.py)

### 级联顺序与成本

```
direct(1) → archive(1) → google_cache(1) → jina(2) → scrapling(2)
  → tavily(3) → browser(3) → search_snippet(1)
```

| 策略 | 成本 | 超时 | 说明 |
|:-----|:----:|:----:|:-----|
| direct | 1 | 20s | httpx + trafilatura |
| archive | 1 | 20s | web.archive.org |
| google_cache | 1 | 20s | webcache |
| search_snippet | 1 | 10s | SearXNG 摘要兜底 |
| scrapling | 2 | 30s | TLS 指纹 (硬编码45s) |
| jina | 2 | 15s | r.jina.ai |
| searxng_alt | 2 | 10s | 替代报道源 (需标题相关性校验) |
| tavily | 3 | 10s | AI 摘要 |
| browser | 3 | 30s | Playwright |
| computer_use | 5 | — | 未实现 |

### 全局参数

| 参数 | 值 |
|:-----|:---|
| MIN_CONTENT_LEN | 200 字符 |
| 限速默认 | 1.0s/域名 |
| 友好域名 | reuters/apnews/bbc/aljazeera 0.5s |
| browser 额外冷却 | 5.0s |
| 级联总超时 | 60s (cascade_timeout) |
| 跳过昂贵 | skip_expensive: browser+computer_use |
| 跳过 URL 模式 | `/watch? youtube /photos/ /gallery/` (视频 URL 走专用链路, 见下) |

### browser 策略性能基准 (2026-07-31)

| 版本 | 平均耗时 | 最慢 | 说明 |
|:-----|:----:|:----:|:-----|
| 修复前 | **87.7s** | 109.4s | 9 个 content selector 串行 8s 等待，最坏 72s |
| 修复后 | **18.6s** | 19.8s | 逗号多 selector 单次等待 (上限 8s)，4.7× 加速 |

- **瓶颈**：`wait_for_selector` 逐个 selector 串行等待 (8s × 9 = 最坏 72s)，视频页无 `article` 匹配时最明显
- **修复**：合并为逗号分隔的 CSS 列表 `page.wait_for_selector("article, [role='main'], ...", timeout=8000)`，任一匹配即返回
- **对照**：`fetch_direct` HTTP 直连 9-19s，但 DataDome/404 下全部取不到正文
- **可靠性**：Bloomberg 3 次采样 2 成功 (1440字)，1 次触发 DataDome 验证页 — 指纹伪装非 100%，约 1/3 概率被挑战
- **基准脚本**：`scripts/benchmark_browser_fetch.py`；耗时探针 `scripts/probe_browser_timing.py`

### 视频抓取链路 (Step 3.6, 2026-07-31 新增)

视频 URL 不再硬跳过，改为 auto-pipeline 独立子批 `Step 3.6 VIDEO_FETCH`：

- **入口职责**：`auto-pipeline.py` 只查候选 URL → 调 `batch.py --video` 子进程 → 落库；抓取逻辑全在 `core/fetchers.py` (extract_single `video_allow`) / `batch.py` (`--video` 标志)
- **两层过滤 → 一层**：Step 3 主批 SQL 仍排除视频；`extract_single` 仅当 `video_allow=True` 且 URL 匹配 `crawl.video_patterns` 时放行，走 `crawl.video_strategy` (browser+stealth 抓转写)
- **Step 3.5 恢复也排除视频**（searxng/tavily 查询加 NOT LIKE），视频只由 Step 3.6 专属处理，避免抢跑浪费预算
- **已知修复 (2026-07-31)**：Step 3.6 SQL 参数顺序错位（score 与 like 参数位置颠倒）曾导致永远 0 候选，已修正为 `(min_score, *like_params, batch_size)`
- **永远跳过**：`/watch?` `youtube.com` `/photos/` `/gallery/`
- **预算模型**：`video_batch_size=6` × browser 单条约 20s ÷ `video_workers=2` 并发 ≈ 60-90s 增量，子批超时上限 5 分钟，总轮次 < 15 分钟
- **只抓 A/B 级**：score ≥ `crawl.video_min_score`(60)

| 配置参数 | 默认 | 说明 |
|:-----|:---:|:-----|
| `crawl.video_enabled` | true | 视频子批总开关 |
| `crawl.video_batch_size` | 6 | 每轮最多视频数 |
| `crawl.video_workers` | 2 | 并发 worker |
| `crawl.video_min_score` | 60 | 最低评分 (A/B 级) |
| `crawl.video_timeout` | 420 | 视频子批总超时 (browser 挂起+兜底单条最坏 ~110s) |
| `crawl.video_max_content` | 20000 | 视频内容清洗后最大长度 (兜底) |
| `crawl.video_strategy` | [browser,archive,jina,tavily] | 视频级联链 |
| `crawl.video_patterns` | [/video/, /videos/] | 视频 URL 识别 |

### 视频内容清洗 (_clean_video_content)

jina 对视频页抓的是**整页 Markdown**（含相关视频卡片/导航/追踪），真实转写只在页面前部：

- `[![Image` 相关视频卡片行 → 直接截断 (CBS 200k→~0.5k)
- 导航标题 (`## Live Now`/`## About` 等) → 段落截断
- 追踪/广告 URL 行过滤 + 内嵌图片引用移除
- 实测: CBS 200k→0.5-7k(96-99%↓) | AlJazeera 11.5k→5.2k(时间戳全保留) | BBC 12.4k→9.6k(时间戳全保留)
- **局限**: jina 拿不到 CBS 视频转写 (JS 渲染, 仅~500字简介); 真转写来自 browser 策略
- **历史数据重清洗**: `scripts/reclean_video_content.py` 一次性脚本 (幂等/备份/--dry-run), 对清洗器部署前存储的噪音行批量重清洗

### 域名策略目录 (2026-07-31)
- **域名菜单无"添加"按钮是设计使然**: 22 个已知域是精选目录(定制反爬/付费墙元数据)，未知域自动走通用默认策略
- **但未知域也可自定义**: 在配置中心设 `crawl.domain.{任意域名}.strategy/failing` 即生效 (get_profile 支持, 2026-07-31 恢复重构回归)
- 单一来源 `domain_strategies.json` (本地 loader 与后端 admin_config 共享)

### ⚠️ 配置中心 settings 列类型坑 (2026-07-31)
- `settings.value` 列实际是 **TEXT** (ORM 声明 JSONB 但表结构为 text)，SQLAlchemy 读回是 **JSON 字符串**而非 list
- `admin_config._flat_from_db` 必须归一化字符串编码数组 → list，否则前端 `.map()` 崩
  (`e.strategy.map is not a function`)
- 域名策略已单一来源 `config/domain_strategies.json` (本地 loader 与后端 admin_config 共享)

### 域名画像 (22)

```
wsj.com:      DataDome → archive→google_cache→jina→tavily→browser→search [failing: scrapling]
bloomberg.com: DataDome → archive→google_cache→jina→tavily→browser→search [failing: direct,scrapling]
reuters.com:  DataDome → archive→jina→tavily→search [failing: scrapling,browser]
ft.com:       DataDome → browser→archive→search [failing: scrapling]
cnbc.com:     Cloudflare → direct→scrapling→archive→search
investing.com: Cloudflare → jina→tavily→search [failing: 大部分]
bbc.com/apnews: 无反爬 → direct
... (22 域名)
```

### 代理路由

```
境外域名 → SOCKS5 (127.0.0.1:10808)
国内域名 (.cn/.com.cn/人民网等) → 直连
```

---

## L3 — 结构抽取 (extractor.py)

### 字段抽取规则

| 字段 | 规则 |
|:-----|:-----|
| 标题 | Markdown H1 |
| 日期 | URL路径年 → ISO → "Published" → 中文日期 → 兜底当天 |
| 作者 | 前 300 字符 "By/Author" 正则 |
| 摘要 | 前 2-3 语义句 (150 字符) |
| 要点 | 信号词(said/暴涨/percent)+数字+实体动作 加权 Top5 |

### 性能

```
0.78ms/篇 (1282 篇/秒)
纯规则, 零 LLM
```

---

## L4 — 三级增强 (enhancers.py)

### Tier 路由

```
C (<60):  Python 规则 (零成本)
B (60-89): Qwen3-1.7B 本地
A (≥90):  DeepSeek V4 Flash
```

### Tier C — Python 规则

| 参数 | 值 |
|:-----|:---|
| 摘要截断 | 100 字符 |
| 句子数 | 前 2 句 (中文>5字, 英文>10字) |
| 标签 | 32 关键词 → 18 标签 |
| 股票代码映射 | NVDA→NVIDIA, TSLA→Tesla 等 8 个 |
| 默认分类 | general |

### Tier B — Qwen3 本地

| 参数 | 值 |
|:-----|:---|
| API | `http://127.0.0.1:1234/v1` |
| 模型 | `qwen3-1.7b-instruct` |
| 超时 | 60s |
| max_tokens (标签/实体) | 200 |
| max_tokens (合并) | 500 |
| 输入截断 | 600 字符 |
| 降级策略 | **首次失败→全局跳过** Qwen |

### Tier A — DeepSeek

| 参数 | 值 |
|:-----|:---|
| API | `https://api.deepseek.com/v1` |
| 模型 | `deepseek-v4-flash` |
| 超时 | 45s |
| max_tokens | 800 |
| temperature | 0.1 |
| 内容截断 | 前 3000 字符 / 前 8 段 |
| 降级策略 | 无 Key/失败 → Python 规则 |
| 产出 | event/impact/market_signal/risk_level/forecast |

### 失败降级链

```
DeepSeek 失败 → Qwen3 失败 → Python 规则 (逐级降级)
```

---

## L4.5 — Fact 抽取 (fact_pipeline.py, Schema V1.0, 2026-08-03)

> auto-pipeline Step 4.5: 混合抽取器（多线程）→ `/internal/facts/batch` → fact/fact_entity 表。
> ⚠️ 需系统 Python311（gliner/transformers/torch）+ LM Studio Qwen 在线。

### 混合策略（串联并联）

```
并发: A(规则,喂GLiNER实体,毫秒) + C(GLiNER实体,1s)   ← 廉价, 并联
串行决策(验证门):
  1. A 验证: subject+object(取A/GLiNER最优) 至少一个在标题 且 action有效 → A (毫秒)
  2. C 验证: GLiNER 主体类(person/org)+客体类(country) score≥0.4 → C (1s)
  3. 否则 B(Qwen noThink) → 兜底 (2.2s/篇)
→ Canonicalizer v0.4 → fact + fact_entity 入库
```

### 各抽取器参数

| 组 | 参数 | 值 | 说明 |
|:--:|:-----|:---|:-----|
| A | IDF 语料 | 800 篇池 | subject/object 提取 |
| A | 实体来源 | **GLiNER 注入** | 替代 pipeline 规则实体 (subject 0→24%, object→98%) |
| C | GLiNER threshold | 0.35 | 实体锚定 |
| B | prompt | **noThink** (直接回答JSON,禁止思考) | 8.5× 提速 (18.6s→2.2s) |
| B | max_tokens | 300 | 思考模式需 800 才有 content; noThink 300 即可 |

### Canonicalizer v0.4 规则

- **动作本体 ~23 类**: 语义优先级 (SANCTIONS 100 > ELECTS 50), 高信息量抢占
- **标题上下文**: 仅当动作文本优先级 <70 才覆盖 (修 Oil jumped→SURGES 误判)
- **客体联合**: verb+object → action (impose...sanctions → SANCTIONS)
- **实体 Role 模型**: split_entities 拆分复合主体 ("US and Saudi"→[CTRY_US, ORG_SAUDI])
- **排除新闻来源名** (2026-08-03): `is_media_source()` — Al Jazeera/CBS/BBC 等媒体自我指涉不当事主体; 词边界匹配防 'dw' 误伤 'dow'; 机构源(Fed/ECB/UN/OpenAI)保留

### 输入一致性 (2026-08-03, Phase A)

> 旧指纹与 Fact 指纹必须消费**同一文本 + 同一 NER 源**, 否则 subject/action 比对失真。

```
统一文本 _get_text (aggregator.py): title + description + content_md (HTML过滤, 截断)
  ⚠️ 实测 summary_cn 在本地库退化(~18字符), 不再作为主摘要源; description 是可靠英文摘要
GLiNER / Qwen 改用同一 _get_text (fact_pipeline.py) — 之前只读 summary_cn 被"饿"着
共享 GLiNER 实体: 经 aggregate_events(ner_by_article) 注入 legacy 指纹 (同一 NER 源)
```

### 实测（50 篇）

```
A 验证通过 → 100% 准确 (title_hit)   | 纯新闻 B 占比 74% (内容复杂度下限)
B noThink → 2.2s/篇, 覆盖100%, 语义可比 (偶发幻觉→由验证门拦截)
事实入库: fact 行 + fact_entity 行 (Role: SUBJECT/OBJECT/...)
```

### 相关文档

- 设计: `references/fact-schema-v1.md` · 调优: `references/fact-extractor-tuning.md`
- 脚本: `scripts/news_intel/fact_pipeline.py` (多线程, --verbose 明细)

---

## L5 — 事件聚合 (aggregator.py)

### 指纹构建 (build_fingerprint)

```
subject: 加权最高实体 (hub×0.3, 权重≥0.15)
action:  20 类动作计数排序
object:  加权最高实体 (排除 subject)
topic:   12 类关键词
country: entities.countries[0]
participants: 参与者集合
```

### Fused 指纹 (Phase A, 2026-08-03 方案 A)

> 有 fact 的文章用 **build_fused_fingerprint** — 每字段取最优源; 无 fact 回退 legacy。
> 聚合入口 `aggregate_events(fp_mode="fused"|"fact"|"legacy", ner_by_article=GLiNER实体)`。

```
subject/object ← fact (role=SUBJECT/OBJECT, 落地优先)
action         ← fact(非 OTHER) 否则 legacy (修复 fact 快路径 51% OTHER → 过度切分)
event_type     ← fact(action_event_type) 否则 legacy
country        ← legacy 优先, fact location 兜底 (恢复国家硬约束)
primary_topic  ← legacy 固定 (12 类词表一致, 防主题硬约束失效)
participants   ← 并集 (legacy + fact subj/obj)
anchor         ← 重算 (OTHER 不锚定)
```

**验证 (100/300/800 篇真实新闻, 共享 GLiNER NER)**:

| 指标 | fused | legacy |
|:-----|:-----:|:------:|
| subject 非空率 | **100%** | 33-47% |
| country 非空率 | **96%** | 74-77% |
| 事件级 OTHER 残留 | 6-12% | 10-16% |
| 退化检查 (过合并/过切分) | ✅ (最大事件2%, 无单篇) | ✅ |

- 主事件稳定: 伊朗 "President Trump→Iran" 随语料 5→8→17 篇增长
- 遗留 (fact 抽取层): 泛主体 (governments/individuals/facebook) — 待独立小修; **来源名当主语已修复** (2026-08-03 is_media_source, 100篇验证 Al Jazeera 事件消失)

### 评分 (fingerprint_score)

| 维度 | 满分 | 规则 |
|:-----|:----:|:-----|
| 国家硬约束 | — | 国家不同 → **0** |
| **主题硬约束** | — | **主主题不同 → 0** |
| Action | 25 | 动作相同且非OTHER |
| Subject | 10-25 | 相同 + 稀有度加权 |
| Object | 10-30 | 相同 + 稀有度加权 |
| Primary Topic | 10 | 主主题相同 |
| Secondary Topic | 5 | 仅副主题相同 |
| Event Type | 10 | 类型相同 |
| Participants | 5-10 | ≥2 重叠=10, 1=5 |

### 聚类阈值

```
EVENT_THRESHOLD: 60 (配置中心 aggregate.event_threshold)
MERGE_THRESHOLD: 75
时间窗口: 24-48h
最少文章数: 2
```

### 三阶段

```
Phase 1: 文章→事件 (score≥60)
Phase 2: 事件→合并 (score≥75)
Phase 3: 过滤 (≥2文章) + 计算 impact
```

### 置信度公式

```
confidence = 0.4×源权威 + 0.3×凝聚度 + 0.2×来源多样性 + 0.1×文章数量
```

### 阶段分类

```
≤2h: breaking | ≤24h: developing | ≤168h: active | ≤720h: stable | >720h: closed
```

### Impact 等级

```
≥85: HIGH | 60-84: MEDIUM | <60: LOW
(凝聚度<75 且 HIGH → 降级 MEDIUM)
```

### SAO 质心 (多数决定)

```
subject/action/object/topic = 簇内多数 (占>50% 才生效, 否则回落种子)
```

### 实体规范化

```
国家别名: US→United States, UK→United Kingdom, Russia→Russian Federation
人物别名: 川普/特朗普→Trump, 普京→Putin, 泽连斯基→Zelensky (新增)
机构: White House→US Government, Kremlin→Russian Gov...
```

---

## L6 — 云端同步 (auto-pipeline.py)

### 7 步流程

```
Step 0:   清理占位行 (retry≥3 且无内容)
Step 0.5: 积压报告 (Tier 分布 + 耗尽数)
Step 1:   Sync + 评分 (--hours 2, timeout 240s)
Step 2:   RSS 全文预检 (description≥200字 且 html<30%)
Step 3:   Fetch 批量 (LIMIT 20, workers 5, rate_delay 0.3s, timeout 600s)
Step 3.5: Recovery (searxng_alt 80-89分/10篇, tavily ≥90分/5篇)
Step 4:   聚合 (300 篇, window 48h)
Step 4.5: Fact 抽取 (混合抽取器, 系统python311 子进程, 50篇, workers 4) → /internal/facts/batch
Step 5+6: 云同步 + 内容推送 (并行)

Step 0:   清理占位行 (retry≥3 且无内容)
Step 0.5: 积压报告 (Tier 分布 + 耗尽数)
Step 1:   Sync + 评分 (--hours 2, timeout 240s)
Step 2:   RSS 全文预检 (description≥200字 且 html<30%)
Step 3:   Fetch 批量 (LIMIT 20, workers 5, rate_delay 0.3s, timeout 600s)
Step 3.5: Recovery (searxng_alt 80-89分/10篇, tavily ≥90分/5篇)
Step 4: Fact 抽取 (混合抽取器, 系统python311 子进程, 50篇, workers 4) → /internal/facts/batch----
Step 4.6:   聚合 (300 篇, window 48h)
Step 5+6: 云同步 + 内容推送 (并行)
```

### 推送参数

| 参数 | 值 |
|:-----|:---|
| 事件分块 | 50/批 |
| 内容分块 | 200/批 |
| HTTP 超时 | 60s |
| INTERNAL_TOKEN | 环境变量/配置 |
| 重试 | 连续 3 次失败→跳过剩余 |

### 进程锁

```
LOCK_FILE + BATCH_TIMEOUT(600s)
已有实例在跑 → 跳过
```

### Cron 调度

```
auto-pipeline: 每 15min (平均耗时 103s, 最大 190s)
rss-scanner:   每 5min
config-agent:  每 5min 保活
```

---

## L7 — Web 展示

### 数据源

| 页面 | API | 数据 |
|:-----|:----|:-----|
| Dashboard | /api/v1/dashboard | 指标 + hot_events + map_events |
| Event 列表 | /api/v1/events | 分页 + 筛选 |
| Event 详情 | /api/v1/events/{id} | 全字段 Dossier |
| 地图 | /api/v1/map/events | 50 条地理标记 |
| 来源 | /api/v1/sources | 真实 event_count/权威度 |
| 文章 | /news* | 列表/详情/搜索 |
| 实体画像 | /api/v1/entities/{name} | 国家+关联+事件 |

### 前端渲染

```
Dark Theme (bg #080B12)
12+ 页面, 15+ 组件
Next.js 16 App Router
```

---

## 参数来源 (配置中心联动)

| 层 | 可配置参数 | 配置键 |
|:---|:-----------|:-------|
| L0 | 并发/超时/隔离/代理 | rss.* |
| L1 | 五维权重/Velocity 窗口/Jaccard | scoring.* |
| L2 | 超时/限速/最小内容/级联 | crawl.* |
| L4 | Tier 阈值/Qwen/DeepSeek | ai.* |
| L5 | EVENT/MERGE/时间窗口 | aggregate.* |
| L6 | Batch/Workers/分块/同步窗口 | pipeline.* |
| 域名 | 22 域名策略链 | crawl.domain.* |

**配置流**: 配置中心 → settings 表 → 本地 agent 轮询 → pipeline-config.json → loader → 各模块
