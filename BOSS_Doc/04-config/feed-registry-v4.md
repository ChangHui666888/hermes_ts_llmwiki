# V4 Enterprise Feed Registry — 全球信息源注册中心（升级方案）

> 版本: v1.2 · 2026-08-07 · **状态: 🟢 已决策（P1 ✅ 完成，P2-P5 待续）**
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
| **P2 存量重映射** | 现有 98 源映射到 16 类 + 补全 country/language/type/importance | 分类统计正确 |
| **P3 新源导入** | 批量导入 ~80 新源，**URL probe 验证**，失效源隔离 | 全部源可访问，扫描正常 |
| **P4 移除 categorize_feed** | scanner 改读源 category + 回退兜底，删除 `categorize_feed()` | 新源无需改代码即正确分类 |
| **P5 统计/前端** | sources 页 16 类层级展示 + 按类统计 | 统计美观 |

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

## 7. 后续扩展（信息源注册中心愿景）

- `type` 扩展：Atom / JSON Feed / YouTube / GitHub Release / Mastodon / 邮件简报。
- 多标签（`tags` 数组）支持一源多属（Reuters ∈ Wire + Finance）。
- 源健康度（quarantine 历史）→ 配置中心可视化。
- 与实体库/评分联动：importance 参与评分加权、category 参与事件主题先验。
