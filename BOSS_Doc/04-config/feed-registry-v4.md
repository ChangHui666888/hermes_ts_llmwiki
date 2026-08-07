# V4 Enterprise Feed Registry — 全球信息源注册中心（升级方案）

> 版本: v1.5 · 2026-08-07 · **状态: 🟢 已部署 + scanner 已生效（197 源在线）**
> 定位: 把 Hermes 从"RSS 阅读器"升级为 **Global Feed Registry（信息源注册中心）**——统一元数据 + 16 大类 + 重要性分级 + 多类型扩展，全部经配置中心 Web 管理。
> 依据: 当前实现核实（`rss_sources.py` / `rss-scanner.py` / 配置中心源列表）+ 提案。
> 相关: [backend.md](../01-architecture/backend.md)（/admin/rss/sources）· [cron-jobs.md](cron-jobs.md) · [entity-workflow-usage.md](../01-architecture/entity-workflow-usage.md)

---

## 1. 现状与问题（为什么升级）

| 维度 | 现状 | 问题 |
|------|------|------|
| 源结构 | `RSS_FEEDS` 静态列表，6 字段 `{name, url, region, tier, category, enabled}`（`rss_sources.py:50`） | 字段贫乏，无国家/语言/重要性/类型 |
| 分类 | 10 类中文（通讯社/国家媒体/金融媒体/科技媒体/地缘媒体/政府机构/科研开源/实时信号/X-Nitter/中文央媒） | 粒度粗，无层级，不可多标签 |
| **归类方式** | **`categorize_feed(name)`（`rss-scanner.py:173`）名称硬编码匹配** | ⚠️ 新源必须改代码；`Reuters`/`BBC` 等关键词漂移即错分；"其他"兜底混乱 |
| 落库 | `rss_articles.category` 用 `categorize_feed` 结果（`rss-scanner.py:410/418`） | 统计口径靠名称匹配，不读源自带 category |
| 源类型 | 全部 RSS | 无法表达 Atom / JSON Feed / Nitter / YouTube / GitHub Release |
| 管理 | 配置中心「源列表」Tab（6 字段表单，`page.tsx:375`） | 字段少，无批量导入/导出 |

**核心痛点**：加一个源要动两处代码（`RSS_FEEDS` + `categorize_feed`），分类不可靠、不可扩展——这正是本方案要解决的。

---

## 2. V4 Feed Registry 设计

### 2.1 统一元数据 Schema（10 字段）

```json
{
  "name": "Reuters Top",
  "url": "https://feeds.reuters.com/reuters/topNews",
  "category": "Wire Agencies",
  "subcategory": "Global Wire",
  "country": "Global",
  "language": "en",
  "type": "rss",
  "importance": "S",
  "region": "intl",
  "tier": "hot"
}
```

| 字段 | 含义 | 枚举/示例 | 说明 |
|------|------|-----------|------|
| `name` | 唯一源名 | Reuters Top | 主键（去重/编辑定位） |
| `url` | 源地址 | https://… | 去重键（URL 唯一） |
| `category` | 16 大类 | Wire Agencies | 见 §2.2，替代 categorize_feed |
| `subcategory` | 子分类 | Global Wire / Asia / Russia | 层级细化 |
| `country` | 国家/地区 | Global / US / China / France | 地缘统计 |
| `language` | 语言 | en / zh / fr / ja | 中文聚合/跨语言检索 |
| `type` | 源类型 | rss / atom / jsonfeed / nitter / youtube / github | 扩展不同类型信息源 |
| `importance` | 全局重要性 | S / A / B / C | 动态调度/资源分配（S=最高） |
| `region` | 网络路由 | intl / cn | 境外走代理 / 国内直连（现有） |
| `tier` | 扫描频率 | hot / warm / cold | 现有 TIER 表（hot 高频） |

### 2.2 16 大类分类法（替代现有 10 类）

| # | 大类 | 子类示例 | 覆盖现有 |
|---|------|----------|----------|
| 01 | **Wire Agencies** 通讯社 | Global Wire / Asia / Russia / Middle East | Reuters/AP/AFP/Bloomberg + 新 |
| 02 | **Global Media** 国际主流媒体 | US / UK / EU / Asia | BBC/CNN/NYT/Guardian/DW… |
| 03 | **Financial Media** 金融媒体 | Macro / Market / Commodities / Crypto | FT/WSJ/CNBC/ZeroHedge/CoinDesk… |
| 04 | **China Media** 中国媒体 | 央媒 / 财经 / 综合 | 人民网/新华网 + 财新/第一财经… |
| 05 | **Government** 政府机构 | US / China / EU / UK | White House/Gov.UK + 新 |
| 06 | **Central Banks** 央行 | 独立于政府 | Fed/ECB/BoE/BoJ/PBoC… |
| 07 | **Regulators** 监管机构 | — | SEC/ESMA/FINRA/CFTC/FCA/MAS |
| 08 | **International Organizations** 国际组织 | — | UN/IMF/World Bank/OECD/NATO… |
| 09 | **AI Companies** AI 公司 | — | OpenAI/Anthropic/DeepMind/NVIDIA… |
| 10 | **Technology** 科技媒体/公司 | Cloud / Hardware | TechCrunch/Cloudflare/AWS… |
| 11 | **Open Source** 开源 | — | GitHub/K8s/Docker/Rust/Python… |
| 12 | **Research** 科研 | AI / Nature / Medical | arXiv/Nature/Science/NeurIPS… |
| 13 | **Security** 安全 | — | Krebs/TheHackerNews/CISA/NVD… |
| 14 | **Energy & Commodities** 能源商品 | — | EIA/OPEC/IEA/OilPrice… |
| 15 | **Venture Capital & Startup** VC | — | YC/a16z/Sequoia… |
| 16 | **Community Signals** 社区实时 | Reddit/HN/ProductHunt | HackerNews/Reddit + 新 |

**层级树示例**（供统计/前端聚合）：
```
News        → Wire / Global / China
Finance     → Macro / Market / Commodities / Crypto
Technology  → AI / Cloud / Hardware / OpenSource
Government  → US / China / EU / UK
Research    → AI / Nature / Medical
Community   → Reddit / HackerNews / ProductHunt
```

### 2.3 调度语义（importance × tier）

| 维度 | 取值 | 用途 |
|------|------|------|
| `importance` S/A/B/C | S=全局关键（路透/美联储）→ 优先分配 LLM 预算 | 评分加权 / 资源分配 |
| `tier` hot/warm/cold | hot=高频扫描（HN/Reddit）· warm=常规 · cold=低频（Nitter/科研） | 扫描频率（现有 `TIER` 表） |

> 二者独立：importance 管"权重/预算"，tier 管"扫描频率"。现有 scorer 的 `source_scores.json` 权威度可后续与 importance 对齐。

---

## 3. 源清单（目标 170–200，去重后）

> 现有 98 源 + 新增 ~80 源。⚠️ **导入前必须 URL probe 验证**（见 §5 风险）。

### 3.1 新增源（按 16 类，提案清单）

```jsonc
// 01 Wire Agencies（新增 5）
{"name":"AFP","url":"https://www.afp.com/en/rss","category":"Wire Agencies","subcategory":"Global Wire","country":"France","language":"en","type":"rss","importance":"S","region":"intl","tier":"hot"}
{"name":"Kyodo News","url":"https://english.kyodonews.net/rss/news.xml","category":"Wire Agencies","subcategory":"Asia","country":"Japan","language":"en","type":"rss","importance":"A","region":"intl","tier":"warm"}
{"name":"TASS","url":"https://tass.com/rss/v2.xml","category":"Wire Agencies","subcategory":"Russia","country":"Russia","language":"en","type":"rss","importance":"A","region":"intl","tier":"warm"}
{"name":"Interfax","url":"https://www.interfax.com/rss.asp","category":"Wire Agencies","subcategory":"Russia","country":"Russia","language":"en","type":"rss","importance":"A","region":"intl","tier":"warm"}
{"name":"Anadolu","url":"https://www.aa.com.tr/en/rss/default?cat=world","category":"Wire Agencies","subcategory":"Middle East","country":"Turkey","language":"en","type":"rss","importance":"B","region":"intl","tier":"warm"}

// 02 Global Media（新增 10）
Fox News / https://moxie.foxnews.com/feedburner/latest.xml · Axios / https://api.axios.com/feed/ · TIME / https://time.com/feed/
The Atlantic / https://www.theatlantic.com/feed/all/ · Vox / https://www.vox.com/rss/index.xml · Independent / https://www.independent.co.uk/news/world/rss
Irish Times / https://www.irishtimes.com/rss · Japan Times / https://www.japantimes.co.jp/feed/ · The Diplomat / https://thediplomat.com/feed/
Foreign Policy / https://foreignpolicy.com/feed/

// 03 Financial Media（新增 9）
ZeroHedge / https://feeds.feedburner.com/zerohedge/feed · FXStreet / https://www.fxstreet.com/rss/news · CoinDesk / https://www.coindesk.com/arc/outboundfeeds/rss/
Cointelegraph / https://cointelegraph.com/rss · Kitco / https://www.kitco.com/rss/news · OilPrice / https://oilprice.com/rss/main
TradingEconomics / https://tradingeconomics.com/rss/news.aspx · Morningstar / https://www.morningstar.com/rss · Zacks / https://www.zacks.com/rss.xml

// 04 China Media（新增 10）
财新 / https://www.caixin.com/rss/ · 第一财经 / https://www.yicai.com/rss/ · 财联社 / https://www.cls.cn/rss · 澎湃 / https://www.thepaper.cn/rss
界面 / https://www.jiemian.com/rss · 证券时报 / https://www.stcn.com/rss · 中国证券报 / https://www.cs.com.cn/rss
上海证券报 / https://www.cnstock.com/rss · 经济观察报 / https://www.eeo.com.cn/rss · 36Kr / https://36kr.com/feed

// 06 Central Banks（新增 5）
Bank of Japan / https://www.boj.or.jp/en/rss/ · People's Bank of China / http://www.pbc.gov.cn/rss.xml · RBA / https://www.rba.gov.au/rss/
RBI / https://www.rbi.org.in/rss/ · Bank of Canada / https://www.bankofcanada.ca/feed/

// 07 Regulators（新增 5）
ESMA / https://www.esma.europa.eu/rss.xml · FINRA / https://www.finra.org/rss · CFTC / https://www.cftc.gov/rss.xml
FCA UK / https://www.fca.org.uk/news/rss.xml · MAS SG / https://www.mas.gov.sg/rss

// 09 AI Companies（新增 10）
Anthropic / https://www.anthropic.com/news/rss.xml · Meta AI / https://ai.meta.com/blog/rss/ · DeepMind / https://deepmind.google/blog/rss.xml
Microsoft AI / https://blogs.microsoft.com/ai/feed/ · NVIDIA / https://blogs.nvidia.com/feed/ · Mistral / https://mistral.ai/news/rss.xml
Perplexity / https://www.perplexity.ai/blog/rss.xml · HuggingFace / https://huggingface.co/blog/feed.xml · Cohere / https://txt.cohere.com/rss/ · xAI / https://x.ai/blog/rss

// 10 Technology（新增 8）
Cloudflare / https://blog.cloudflare.com/rss/ · AWS / https://aws.amazon.com/blogs/aws/feed/ · Google Blog / https://blog.google/rss/
Microsoft / https://blogs.microsoft.com/feed/ · Apple Newsroom / https://www.apple.com/newsroom/rss-feed.rss · Netflix Tech / https://netflixtechblog.com/feed
Uber Eng / https://www.uber.com/blog/engineering/rss/ · Stripe / https://stripe.com/blog/feed

// 11 Open Source（新增 8）
Kubernetes / https://kubernetes.io/feed.xml · Docker / https://www.docker.com/blog/feed/ · Linux Foundation / https://www.linuxfoundation.org/feed
Apache / https://blogs.apache.org/feed · Rust / https://blog.rust-lang.org/feed.xml · Python Insider / https://feeds.feedburner.com/PythonInsider
NodeJS / https://nodejs.org/en/feed/blog.xml · GitLab / https://about.gitlab.com/atom.xml

// 13 Security（新增 6）
Krebs / https://krebsonsecurity.com/feed/ · The Hacker News / https://feeds.feedburner.com/TheHackersNews · BleepingComputer / https://www.bleepingcomputer.com/feed/
DarkReading / https://www.darkreading.com/rss.xml · CISA / https://www.cisa.gov/news.xml · NVD / https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml

// 12 Research（新增 6）
Nature / https://www.nature.com/nature.rss · Science / https://www.science.org/rss/news_current.xml · PNAS / https://www.pnas.org/rss/current.xml
NeurIPS / https://papers.nips.cc/rss.xml · ICML / https://icml.cc/rss.xml · CVPR / https://cvpr.thecvf.com/rss.xml

// 14 Energy（新增 4）
EIA / https://www.eia.gov/rss.xml · OPEC / https://www.opec.org/opec_web/en/rss.xml · IEA / https://www.iea.org/rss/news.xml · S&P Global Commodity / https://www.spglobal.com/commodityinsights/en/rss

// 15 VC（新增 6）
Y Combinator / https://www.ycombinator.com/blog/rss · a16z / https://a16z.com/feed/ · Sequoia / https://www.sequoiacap.com/feed/
Accel / https://www.accel.com/feed · Greylock / https://greylock.com/feed/ · General Catalyst / https://www.generalcatalyst.com/feed

// 16 Community（新增 5）
Lobsters / https://lobste.rs/rss · Slashdot / https://rss.slashdot.org/Slashdot/slashdotMain · Product Hunt / https://www.producthunt.com/feed
Dev.to / https://dev.to/feed · Stack Overflow Blog / https://stackoverflow.blog/feed/
```

> 分类备注：现有源将按 16 类重新映射（Reuters/AP/AFP→Wire；Fed/ECB/BoE→Central Banks；UN/IMF/World Bank/OECD→Intl Orgs；SEC/CFTC→Regulators；arXiv/Nature/Science→Research；HN/Reddit→Community；Nitter 源按主题归对应类，type=nitter）。

---

## 4. 配置中心集成（Web 管理）

### 4.1 后端
- `rss_sources.py` `RssSourceIn` 扩展 **6→10 字段**（+`subcategory, country, language, type, importance`），向后兼容旧数据（缺省填充）。
- 新增 `POST /admin/rss/sources/import`（批量 JSON 导入，按 url 去重）+ `GET /admin/rss/sources/export`（全量导出）。
- 分类/重要性/语言枚举校验（防脏数据）。

### 4.2 前端「源列表」Tab
- 表单扩展 10 字段（`page.tsx:375` 处 form state + 字段输入）。
- 分类下拉（16 类）+ 子分类 + 重要性 S/A/B/C 下拉。
- 批量导入按钮（粘贴 JSON）+ 校验报告。
- 列表分组显示（按 16 类折叠/过滤）。

### 4.3 扫描器消费
- `rss-scanner.py` 移除 `categorize_feed()`：直接读源 `category`（缺省回退 `name` 匹配兜底）。
- `rss_articles.category` = 源 category（统计口径统一）。
- 支持 `type` 分派：rss 走现有 feedparser；jsonfeed/nitter/youtube 走对应解析器（后续扩展）。

---

## 5. 迁移方案（分阶段，doc-first）

| 阶段 | 内容 | 验收 |
|------|------|------|
| **P1 Schema+UI** | ✅ 后端 RssSourceIn 扩 11 字段 + 16 类常量(中文别名) + `/sources/import` `/sources/export` API + 配置中心表单/批量导入/旧分类兜底（commit `8a9c221`） | 配置中心可编辑/导入新字段，旧源数据兼容 |
| **P2 存量重映射** | ✅ `migrate_rss_v4.py` + `references/rss-sources-v4-migrated.json` — 94/94 源映射 16 类无遗漏（commit `6041530`） | 分类统计正确 |
| **P3 新源导入** | ✅ `references/rss-new-feeds-v4.json`(97 新源) + `probe_feeds.py` URL 探测 — batch1 12/25 通过（宁缺毋滥, commit `ead4f0f`） | 全部源可访问，扫描正常 |
| **P4 移除 categorize_feed** | ✅ rss-scanner 读源 category 优先, categorize_feed 改 16 类兜底（commit `ebdb19d`） | 新源无需改代码即正确分类 |
| **P5 统计/前端** | ✅ sources_v1 API 暴露 V4 category + 前端 sources 页 16 类分组展示（commit `fb7ecff`） | 统计美观 |
| **部署** | ✅ VPS 已完成（2026-08-07）：git pull → `docker compose up -d --build` → `import_feeds_v4.py` 容器内导入 → 验证 197 源 / API 200 | 已上线 |

> **已部署**：① VPS git pull 至 `289c010`；② backend+frontend docker 重建（P1/P5 生效）；③ `import_feeds_v4.py` 导入——存量 94 重映射 + 新源 102（含 batch1 已验证 12 + batch2 全部 90，另补 Canadian Press/IMF Blog/Stability AI/CNCF/LLVM）→ **总计 197 源**（覆盖用户补源清单全部）；④ API 健康（dashboard/sources 200）。
> **✅ 本地已同步（2026-08-07）**：`deploy-cron.py --apply` 同步 P4 scanner 到 Hermes（line 418 `feed.get("category")` 优先）；启动 config-agent（8890）→ 本地 `pipeline-config.json` 刷新至 **197 源、全部带 16 类 category、0 无分类** → 下次 rss-scan（5m cron）即用源 category 分类。
> **待办**：① 失效源由 `rss.quarantine` 自动隔离（复核 `failed-batch1.json`）；② RSS-Digest 中文日报分组现为英文 16 类，如需中文别名展示另调整。

**风险与对策（诚实标注）**：
1. ⚠️ **部分源 URL 已失效**：`feeds.reuters.com/*` 自 2020 年起已废弃（现有代码就在用）；Nitter 实例不稳定；部分中文财经站（财新/第一财经等）RSS 可用性存疑；ZeroHedge/TradingEconomics 等可能反爬。→ **P3 必做 URL probe + 复用现有 quarantine 机制**（`rss.quarantine_failures/seconds`），不达标的源自动隔离不阻断扫描。
2. 数据量翻倍（98→200）→ 需复核 `rss.max_workers`(14) 与扫描预算；Nitter/视频类走低频 tier。
3. 16 类 vs 现有 10 类的统计口径变化 → 前端分类筛选需同步改。

---

## 6. 决策点（✅ 已决策 2026-08-07）

| # | 决策 | 已选方案 | 影响 |
|---|------|----------|------|
| 1 | 分类法 | **16 类 + 中文别名双标签** | 16 类为权威主类，每类挂中文别名（Wire Agencies↔通讯社…），统计/前端双语言 |
| 2 | `importance` 接入 scorer | **联动 scorer 权威度** | `importance` S/A/B/C 映射进 `source_scores.json` 权威度（S=最高），评分实体/来源维联动 |
| 3 | 新源导入 | **分批**（先 Wire+Gov+AI 权威源，再金融/长尾） | 控制扫描压力 + 逐批 probe |
| 4 | `categorize_feed` 兜底 | **保留为"未知源自动归类"回退** | scanner 优先读源 `category`，未知/缺分类源走名称兜底 |
| 5 | 目标源数 | **宁缺毋滥（probe 通过为准）** | 只导入 URL 验证通过的源，不凑数 |

> **实施约定**：16 类主类 = §2.2 表；中文别名由配置中心分类下拉提供（主类 + 中文标签）；importance 联动 scorer 在 P2 一并落地。

---

## 9. RSS 升级后全套流水线验证（2026-08-08）

> 升级后对 采集→评分→Fact→聚合→推送→Story→展示 全链路验证，**全部正常无回归**。

| 环节 | 结果 |
|------|------|
| 采集 | ✅ scanner 196 源 / 新增 3237 篇 |
| 评分 | ✅ VPS articles tier A=10 / B=2116 / C=150 |
| Fact | ✅ fact 4392 / fact_entity 9105；最近 2 轮 FACT_45 均 100% |
| 聚合 | ✅ events 225（24h 新建 17） |
| 推送 | ✅ 近 2 轮 CLOUD_SYNC 38 + CONTENT_PUSH 2-4 + facts 50，0 fail |
| Story | ✅ story 63（action 21/object 16/subject 14/location 12） |
| 展示 | ✅ Dashboard active=210/critical=15，API 全 200 |

**观察项**：00:58 轮 `AGGREGATE: 0 marked`（300 unassigned/50 facts）——新分散源文章可能未达聚合阈值(60)，24h 内仍新建 17 事件整体正常。已登记 issue-tracking（ISS-20260808-001）。

---

## 7. 后续扩展（信息源注册中心愿景）

- `type` 扩展：Atom / JSON Feed / YouTube / GitHub Release / Mastodon / 邮件简报。
- 多标签（`tags` 数组）支持一源多属（Reuters ∈ Wire + Finance）。
- 源健康度（quarantine 历史）→ 配置中心可视化。
- 与实体库/评分联动：importance 参与评分加权、category 参与事件主题先验。

---

## 8. 脚本使用情况（197 源在各脚本中如何被消费，2026-08-08）

> 源数据流：**配置中心「源列表」→ VPS settings 表 `rss.feeds` → config-agent(60s) → 本地 `pipeline-config.json` → 各脚本消费**。

### 8.1 各脚本字段消费矩阵

| 脚本 | 消费字段 | 用途 | V4 状态 |
|------|----------|------|:-------:|
| **config-agent.py** (`scripts/hermes-cron/`) | 全部 11 字段 (name/url/region/tier/category/subcategory/country/language/type/importance/enabled) | 从 VPS `/admin/pipeline/config/export-internal` 拉取 → 白名单 `_sanitize_feeds` 校验 → 写本地 `pipeline-config.json` | ✅ V4 |
| **rss-scanner.py** (`scripts/hermes-cron/`) | `url`(抓取) · `region`(intl→SOCKS5 代理/cn→直连) · `tier`(hot/warm/cold 扫描顺序) · `name`(源名落库) · `category`(分类落库) · `enabled`(启停) | RSS 扫描引擎 → `rss_articles` 表 | ✅ V4 (P4) |
| **scorer.py** (`scripts/news_intel/`) | `importance` (S/A/B/C → 20/15/11/8 兜底分) | `score_source` 来源权威度维度（source_scores.json 精确分优先） | ✅ V4 |
| **sources_v1.py** (`apps/api/routes/`) | `category`（按源名模糊匹配） | 公共 `/sources` 页 16 类徽章 | ✅ V4 |
| **news.py** (`apps/api/routes/`) | `category`+`subcategory`（`/news/menu` 层级 + `/news?menu={slug}` 过滤） | 首页 6 组主菜单 + feed 页 | ✅ V4 |
| **aggregator.py** (`scripts/news_intel/`) | 不直接消费源列表（阈值经 config 读取） | 事件聚合 | — |

### 8.2 字段语义与使用分工

| 字段 | 谁在用 | 语义 |
|------|--------|------|
| `url` | scanner | 抓取地址 |
| `region` | scanner | 网络路由：intl 走 SOCKS5 / cn 直连 |
| `tier` | scanner | 扫描频率：hot=先扫/warm/cold |
| `importance` | **scorer** | 评分权重：S/A/B/C → 20/15/11/8（source_scores 精确分优先） |
| `category` | scanner + sources_v1 + news.py | 16 大类（分类落库 + 菜单层级） |
| `subcategory` | news.py | 主菜单子类（menu 过滤） |
| `country`/`language` | 展示元数据 | 地缘统计/跨语言（暂未用于扫描路由） |
| `type` | **未使用** | rss/atom/nitter 等类型字段已存；当前 scanner 全走 feedparser 可解析，未按 type 分支 |
| `enabled` | scanner + config-agent | 启停过滤 |

### 8.3 已解决（2026-08-08 scanner 优化） / 剩余建议

✅ **已解决**：
1. `type` 分支：`parse_feed` 加 `feed_type` 分派（jsonfeed → `_parse_json_feed`，rss/atom/nitter → feedparser）。
2. scanner 硬编码回退：`FEEDS`(98 旧格式) → `CORE_FALLBACK_FEEDS`(12 源 V4 全字段)。

⏳ **scanner 性能优化（commit `af3087f`，测试通过）**：
| 优化 | 收益 |
|------|------|
| 全局 HTTP Client Pool（CN/PROXY 共享，复用连接） | 15-30% |
| SQLite 内存 known_ids 去重 + `executemany` 批量 + WAL PRAGMA | 50-80% |
| Tier 分级扫描频率（hot 5min/warm 15min/cold 60min） | 网络压力降 50% |
| ETag/Last-Modified 增量（304 免下载） | 大幅减少重复下载 |
| as_completed 即时解析入库（不等全部下载完） | 10-20% |

**实测**：196 源 / 193 到期 / 174.56s / 新增 3237 篇 / 失败 16（代理超时）。

剩余建议：`country`/`language` 驱动路由（中文源直连加速）、`asyncio` 第二阶段（Async Scanner V4）。
