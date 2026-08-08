# 五维评分规则

> 基于 `news_intel/scorer.py`（**2026-08-08 最新代码**，含 V4 importance 联动 + 197 源综合评分表）
> 配置数据源: `news_intel/config/`（source_scores.json / event_keywords.json / entity_weights.json / asset_graph.json）+ `references/rss-importance-map.json`
> 入口: `score_article()` 返回 `{total, source, impact, entity, market, velocity, tier, categories, entities, market_assets, velocity_count}`

## 评分总览

| 维度                |   满分    | 方法                             | 数据源                            |
| ----------------- | :-----: | ------------------------------ | ------------------------------ |
| Source Authority  |   20    | 来源权威度查表 + **V4 importance 兜底** | source_scores.json + rss.feeds |
| Event Impact      |   30    | 关键词命中（5 领域，同类取最高，不累加）          | event_keywords.json            |
| Entity Importance |   20    | 实体权重查表（词边界匹配）                  | entity_weights.json            |
| Market Relevance  |   20    | 资产映射图（实体/关键词→股票）               | asset_graph.json               |
| Velocity          |   10    | 30 分钟内同事件（同指纹）报道数              | 跨文章 Jaccard                    |
| **总分**            | **100** | 五项累加, 封顶 100                   | —                              |

## Tier 划分

| Tier | 分数范围 | 增强方式 | 成本 |
|:----:|:--------:|----------|:----:|
| A | ≥ 90 | DeepSeek V4 Flash | ~$0.002/篇 |
| B | 60–89 | Qwen3-1.7B 本地 | 免费 |
| C | < 60 | Python 规则（零成本） | $0 |

---

## 1. Source Authority (0-20)

**方法（三级回退，2026-08-08 综合评估表）**:
1. **source_scores.json 精确分**：`scores.get(source_name)`（**197 源综合评分表**，分值 5-19，来自 `rss来源20分综合评估_20260808.xlsx`）
2. **V4 importance 兜底**：源名模糊匹配 `rss.feeds` 的 importance → `S=20/A=15/B=11/C=8/D=5`
3. **default**：`scores.get("_default", 5)`

```python
def score_source(source_name: str) -> int:
    if source_name in scores: return scores[source_name]   # ①精确
    for fn, iv in _get_feed_importance().items():           # ②V4 importance
        if source_name in fn or fn in source_name:
            return {"S":20,"A":15,"B":11,"C":8,"D":5}.get(iv, 8)
    return scores.get("_default", 5)                        # ③默认
```

**示例分值**（source_scores.json 部分）:

| 来源 | 分值 |
|------|:----:|
| IMF Blog / Fed Press / Reuters / AP / Bloomberg Markets / ECB Press / 白宫 / 各国央行 | 19 |
| WSJ / FT / World Bank / UN News / Anadolu / 央视新闻 / 新华网时政 | 18 |
| CNBC / BBC News / Anthropic / NYT / Nature / 财新 | 17 |
| Al Jazeera / 第一财经 / CNN Edition / Foreign Policy / SCMP | 16 |
| TechCrunch / Guardian World / 澎湃 / Seeking Alpha / TIME | 15 |
| BleepingComputer / ZeroHedge / a16z / Fox News / Ars Technica | 14 |
| GitHub Blog / Hacker News / Reddit | 12-11 |
| Nitter 系列 / Product Hunt / Lobsters / Stack Overflow Blog | 10 |
| LLVM / Dev.to / Nitter 个人账号 | 9 |
| 停用源 | 8 |
| 未知源 | 5（default）|

> **评分数据流**：Excel 综合评估表（建议等级 + 综合评分）→ ① `source_scores.json`（四舍五入整数分，scorer 精确分）② `references/rss-importance-map.json`（权威 {等级, 浮点分}）→ `update_source_importance.py` 同步等级到配置中心 `rss.feeds`。
> 新源（未在 source_scores 中）→ 由 V4 importance 兜底（如 Anthropic S→20 / TASS A→15）。

---

## 2. Event Impact (0-30)

**方法（v2, 2026-08-08）**: 对 `title + description` 关键词命中。遍历 5 个分类，**每个分类取该类最高分，最终取所有分类最高（不累加，防标题党刷分）**。返回 `(分数, 命中分类, hits详情)`。

**5 个分类 · 495 关键词**（event_keywords.json，2026-08-08 v2.1；每类取该类最高、跨类只取所有分类最高，不累加）:

| 分类 | 关键词数 | 高分示例 |
|------|:--:|------|
| **finance** 金融 | 117 | 利率决议/降息/加息/破产/熔断/银行危机/bank failure = 30 |
| **geopolitics** 地缘 | 90 | 战争/war/政变/coup/暗杀/assassin/入侵/nuclear = 30 |
| **ai_tech** AI科技 | 133 | GPT-5/AGI/超级智能/superintelligence = 28；先进封装/Chiplet/HBM = 20 |
| **market** 市场 | 70 | 熊市/股市崩盘/flash crash/market crash = 22 |
| **china** 中国 | 85 | 台海危机/中美贸易战/台海冲突 = 30；核能/核电 = 18 |

> 📋 完整关键词清单以 `news_intel/config/event_keywords.json` 为**权威来源**。
> **v2.1 (2026-08-08)**：① 移除 **23 个机构重名词**（美联储/Fed/ECB/NATO/UN/G7/国务院/证监会等）→ 转正为 `organizations` 实体（避免关键词/实体双权重）；② 新增 **18 个供应链领域词**（先进封装/Chiplet/晶圆键合/光芯片/激光器芯片/MOCVD/磷化铟/砷化镓/液冷/核能/核电/反应堆/核燃料/铀矿）。

### 2.1 匹配模式（v2 升级，自动推断）

对每个关键词自动推断匹配模式（`_kw_match_mode`），也可在 JSON 中用 dict 值显式指定 `match`：

| 关键词形态 | 模式 | 理由 | 示例 |
|-----------|------|------|------|
| 含中文 | substring | 中文无词边界概念 | 降息/美联储/台海危机 |
| 多词英文短语（含空格） | substring | 保复数/派生召回 | `bank failures` 命中 `bank failure` |
| 短英文词/缩写（字母≤3 或高风险词） | **word_boundary** | 防子串误标 | `Fed` 不命中 Federal / `war` 不命中 hardware·forward / `UN` 不命中 Underestimated / `5G` 不命中 5GHz / `coup` 不命中 coupon |
| 常规英文词（字母>3） | substring | 保复数召回 | chip→chips / crash→crashes / strike→strikes |

`_WORD_BOUNDARY_FORCE = {coup, NATO}`（字母>3 但仍需词边界的特例）。

```python
def _match_keyword(text, keyword, mode):
    if mode == "word_boundary":
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])",
                         text, flags=re.IGNORECASE) is not None
    return keyword.lower() in text.lower()
```

### 2.2 部署前后能力评估（2026-08-08, 4000 篇真实样本）

| 指标                      | 旧 (133词+substring) | 新 (500词+v2) | 说明                |
| ----------------------- | :----------------: | :---------: | ----------------- |
| 平均 impact 分             |       14.30        |    7.28     | 旧 substring 系统性虚高 |
| impact=0 文章             |        1283        |    2619     | +1336 篇纠正为 0（原误标） |
| 新增命中（新>旧）               |         —          |    451 篇    | 500 词覆盖面提升        |
| **误标修复**（word_boundary） |         —          | **1591 篇**  | 核心收益              |
| 真关键词精化                  |         —          |     4 篇     | 台海→台海危机 / GPU→芯片  |
| `Federal Reserve` 全名缺口  |         —          |     3 篇     | 均为低价值审批公告，可接受     |

**结论**：旧 scorer 纯 substring 在技术/学术文本大量误标（`war`→hardware、`UN`→Underestimated、`GPU`→GPUS 股票代码、`Fed`→Feedback）。v2 word_boundary 修复 **1591 处误标** + 500 词新增 **451 处真实命中**。平均分下降是**正确性修复**，非能力损失；tier 分布将更准确（减少虚高 A/B 级）。

---

## 3. Entity Importance (0-20)

**方法**: 从 `title + description` 匹配 entity_weights.json 已知实体（公司/人物/国家），取**最高权重** `min(max_score, 20)`；同时产出文章实体清单 `{companies, persons, countries}`。

**实体匹配规则 `_entity_in_text`（v4.4.2 修复子串误标）**:
| 实体名类型 | 匹配规则 |
|-----------|---------|
| **CJK 名**（含中文字符）| 子串匹配（无词边界） |
| **拉丁名 ≤3 字符**（Xi/US/BP/UK）| `\b` 词边界 + **大小写敏感**（防 'Xi' 命中希腊字母 xi、'us' 子串） |
| **拉丁名 >3 字符** | `\b` 词边界 + 忽略大小写 |

**数据规模**: entity_weights.json — **199 公司 + 77 人物 + 34 国 + 101 机构 = 411 实体**（含中英别名）。完整实体→权重表如下（命中多个取最高，封顶 20）。

> **v1.4 (2026-08-08)**：新增 **organizations 类目**（央行/国际组织/政府机构，101 项，权重 10-20）——从 event_keywords 关键词表剥离转正，避免同一实体双权重。新增供应链实体 111 项（AI算力/先进封装/光芯片/核能四大领域上游设备/配件/材料公司）。scorer 已支持第 4 类实体，aggregator 主体/客体候选已纳入 organizations。

##### companies 公司（88）

| 权重 | 实体 |
|:--:|--------|
| 20 | NVIDIA / Apple / Microsoft / OpenAI / TSMC / 台积电 |
| 18 | Google / Tesla / ASML / SpaceX / 华为 / Huawei / Alphabet |
| 16 | Amazon / Meta / Anthropic / DeepSeek / JPMorgan / Goldman Sachs / BlackRock / Berkshire Hathaway / 伯克希尔 / 中芯国际 / SMIC / 宁德时代 / CATL / Saudi Aramco / 沙特阿美 |
| 15 | ByteDance / AMD / Morgan Stanley / 阿里巴巴 / Alibaba / 腾讯 / Tencent / 比亚迪 / BYD |
| 14 | TikTok / Samsung / Intel / Qualcomm / Broadcom / Vanguard / Exxon / Boeing / Lockheed / 字节跳动 / 工商银行 / ICBC / Gazprom / 俄气 / Rosneft / HSBC / Volkswagen / 大众 / BMW / 宝马 / Mercedes / 奔驰 / Siemens / 西门子 / TotalEnergies / LVMH / Airbus / 空客 / Toyota / 丰田 / SoftBank |
| 13 | Shell / BP / Chevron / Pfizer / Moderna / Deutsche Bank / BNP Paribas / Sony / 索尼 / Foxconn / 鸿海 / MediaTek / Reliance / Tata |
| 12 | Johnson / 美团 / 拼多多 / Yandex / Sberbank / Adani |

##### persons 人物（79）

| 权重 | 实体 |
|:--:|--------|
| 20 | Trump / 特朗普 / 川普 / Donald Trump / Powell / 鲍威尔 / Kevin Warsh / Warsh / 凯文·沃什 / 凯文沃什 / 凯文沃舎 / Federal Reserve / 美联储 / Xi / 习近平 / Putin / 普京 / Vladimir Putin |
| 18 | 沃什 / 沃舎 / Musk / 马斯克 / Elon Musk / Sam Altman / Jensen Huang / 黄仁勋 |
| 16 | J.D. Vance / 万斯 / Marco Rubio / 卢比奥 / Altman / 奥特曼 / Buffett / 巴菲特 / Warren Buffett / Yellen / 耶伦 / 李强 / 蔡奇 / Zelensky / 泽连斯基 / Volodymyr Zelensky / Dimon / 戴蒙 / Jamie Dimon / Tim Cook / 库克 / Sundar Pichai / 皮查伊 / Satya Nadella / 纳德拉 / Mark Zuckerberg / 扎克伯格 / Jeff Bezos / 贝索斯 / Netanyahu / 内塔尼亚胡 / Benjamin Netanyahu / Narendra Modi / 莫迪 |
| 15 | Biden / 拜登 / Larry Ellison / Bill Ackman / Emmanuel Macron / 马克龙 |
| 14 | Mishustin / 米舒斯京 / Lavrov / 拉夫罗夫 / Shoigu / 绍伊古 / Gates / 盖茨 / Bill Gates / Olaf Scholz / 朔尔茨 / Keir Starmer / 斯塔默 |

##### countries 国家（34）

| 权重 | 实体 |
|:--:|--------|
| 20 | North Korea / 朝鲜 |
| 18 | China / 中国 / Russia / Russian Federation / 俄罗斯 / Iran / 伊朗 / Ukraine / 乌克兰 / Taiwan / 台湾 |
| 17 | Israel / 以色列 |
| 15 | United States / US / USA / 美国 / Saudi Arabia / 沙特 |
| 14 | India / 印度 / Japan / 日本 |
| 13 | UK / United Kingdom / 英国 / Germany / 德国 / UAE / 阿联酋 |
| 12 | France / 法国 |

> ⚠️ 拉丁名实体一律**词边界**匹配（`_entity_in_text`），故 `US` 仅匹配大写独立 `US`（不匹配小写 us 子串）；中英别名只要有一个命中即计入该实体权重。

```python
def score_entities(title, description):
    for etype, entities in weights.items():       # companies/persons/countries
        for name, weight in entities.items():
            if _entity_in_text(name, text):
                found[etype].append(name)
                max_score = max(max_score, weight)
    return min(max_score, 20), found
```

---

## 4. Market Relevance (0-20)

**方法**: 两条路径，取最高权重 `min(max_score, 20)`，同时产出受影响资产列表（stocks + indices/commodities/crypto）：
1. **实体 → 资产映射**：文章已识别实体若在资产图 stocks 中 → 该资产权重
2. **关键词 → 资产映射**：资产键（如 "GPU"/"降息"/"war"）在文本中命中 → 该资产权重

**资产图**（asset_graph.json，2026-08-08 v1.4，39 个资产键）:

> **v1.4 新增 14 个供应链领域映射**（关系）：先进封装/Chiplet/晶圆键合 → 封装设备股（ASMPT/库力索法/EV Group/AT&S/Ibiden）；光芯片/photonic chip/激光器芯片 → 光芯片股（Veeco/AIXTRON/华工科技/光库科技）；HBM → 存储股（SK海力士/美光/沪电股份）；液冷 → 冷却股（Vertiv/英维克/台达电子）；核能/核电/nuclear/反应堆 → 核电股（上海电气/东方电气/Kazatomprom/Orano）。

##### 权重 20（8 键）

| 资产键 | 受影响资产 |
|--------|-----------|
| **GPU** | NVIDIA / AMD / TSMC / ASML / Intel / Broadcom |
| **AI芯片** | NVIDIA / AMD / TSMC / Broadcom |
| **出口管制** | NVIDIA / AMD / TSMC / ASML / SMIC |
| **chip export** | NVIDIA / AMD / TSMC / ASML |
| **降息** | JPMorgan / Goldman Sachs / Bank of America / Wells Fargo + 指数 S&P500/NASDAQ/Dow Jones |
| **rate cut** | JPMorgan / Goldman Sachs / Bank of America + 指数 S&P500/NASDAQ |
| **加息** | JPMorgan / Goldman Sachs / Bank of America + 指数 S&P500/NASDAQ |
| **rate hike** | JPMorgan / Goldman Sachs / Bank of America |

##### 权重 18（9 键）

| 资产键               | 受影响资产                                                                |
| ----------------- | -------------------------------------------------------------------- |
| **石油**            | Exxon / Chevron / Shell / BP / ConocoPhillips + 商品 CL1:COM / BZ1:COM |
| **oil**           | Exxon / Chevron / Shell / BP + 商品 CL1:COM / BZ1:COM                  |
| **半导体**           | TSMC / NVIDIA / AMD / Intel / ASML / Qualcomm / Samsung              |
| **semiconductor** | TSMC / NVIDIA / AMD / Intel / ASML                                   |
| **Bitcoin**       | Coinbase / MicroStrategy / Marathon Digital + 加密货币 BTC               |
| **国防**            | Lockheed Martin / RTX / Northrop Grumman / Boeing                    |
| **defense**       | Lockheed Martin / RTX / Northrop Grumman                             |
| **战争**            | Lockheed Martin / RTX / Northrop Grumman / Exxon / Chevron           |
| **war**           | Lockheed Martin / RTX / Exxon / Chevron                              |

##### 权重 15（4 键）

| 资产键 | 受影响资产 |
|--------|-----------|
| **电动车** | Tesla / 比亚迪 / NIO / XPeng / Rivian / Lucid |
| **EV** | Tesla / BYD / Rivian / Lucid |
| **加密货币** | Coinbase / MicroStrategy / Marathon Digital + 加密货币 BTC/ETH |
| **crypto** | Coinbase / MicroStrategy + 加密货币 BTC/ETH |

##### 权重 12（3 键）

| 资产键 | 受影响资产 |
|--------|-----------|
| **云计算** | Amazon / Microsoft / Google / Oracle |
| **cloud** | Amazon / Microsoft / Google |
| **制药** | Pfizer / Moderna / Johnson & Johnson / Merck / Eli Lilly |
| **pharma** | Pfizer / Moderna / Eli Lilly / Merck |

### 4.1 匹配缺陷与修复（2026-08-08）

关键词路径现用**纯 substring**（`asset_key in text`），存在与 Event Impact v1 相同的词边界误标：

| 资产键 | 误标示例 | 假阳性后果 |
|--------|---------|-----------|
| **EV** | "every"/"event"/"several" 含 `ev` | +15 → 误挂 Tesla/BYD/Rivian/Lucid |
| **war** | "forward"/"hardware"/"award" 含 `war` | +18 → 误挂 Lockheed/Exxon |
| **oil** | "soil"/"boil"/"coil" 含 `oil` | +18 → 误挂 Exxon/Shell |
| **crypto** | "cryptography" 含 `crypto` | +15 → 误挂 Coinbase（刻意保留: substring 需覆盖 cryptocurrency） |

**✅ 已修复（2026-08-08, commit 见下）**：复用 Event Impact v2 的 `_kw_match_mode`（短英文词/缩写 → word_boundary；中文/短语/常规词 → substring）。**4000 篇真实样本评估：修复 1271 处误标（全部归 0），0 处真实命中丢失**——纯精度收益。真实命中（GPU/rate cut/war+oil/EV/oil spill/Bitcoin）全部保持。

---

## 5. Velocity (0-10)

**方法**: `score_velocity(velocity_count)` — 30 分钟内同事件报道数：

| 同源报道数 | 得分 |
|:--:|:--:|
| ≥ 10 | 10 |
| 5–9 | 5 |
| 2–4 | 2 |
| < 2 | 0 |

**批量计算 `compute_velocity`**: 对每篇文章，统计 ±30 分钟内 **同指纹**（标题词集 Jaccard 相似度 ≥ 0.5）的报道数。

**指纹 `_make_fingerprint_set`**: 标题分词 → 去停用词 → 取前 8 个实词。

> **停用词表 v2.1 (2026-08-08)**：补全英文功能词（冠词/介词 as·amid·by·from·over·under·between·among·through·during·against·about·along·around·beyond·despite·toward·via 等 + 连词 + 代词 + 系动词/助动词 + 副词）＋常见新闻框架词（says/said/say/new/latest/live/breaking/update/video/watch/photos）＋中文双字功能词（对于/由于/以及/因为/所以/虽然/但是）＋缩写后缀（s/re/ve/ll/d/m）。单字 token（含单字中文）由 `len>1` 一并过滤。目的：消除高频功能词对 Jaccard 交集的稀释，提升判同精度（实测 `as` 不再让无关标题产生交集）。

```python
def score_velocity(v):
    if v >= 10: return 10
    if v >= 5: return 5
    if v >= 2: return 2
    return 0
```

---

## 6. 主入口 `score_article`

```python
def score_article(source_name, title, description, velocity_count):
    src  = score_source(source_name)
    imp, categories = score_impact(title, description)
    ent_score, entities = score_entities(title, description)
    mkt, market_assets = score_market(title, description, entities)
    vel = score_velocity(velocity_count)
    total = min(src + imp + ent_score + mkt + vel, 100)
    tier = "A" if total >= 90 else "B" if total >= 60 else "C"
    return {...}
```

**输出字段**（落库 news_intelligence）:
| 字段 | 说明 |
|------|------|
| score_total | 五维总分 0-100（封顶） |
| score_source/impact/entity/market/velocity | 各维分 |
| tier | A/B/C |
| categories | 命中的 impact 分类 |
| entities | `{companies, persons, countries}` 文章实体清单 |
| market_assets | 受影响资产列表 |

---

## 7. 配置数据源与修改

| 配置 | 位置 | 生效 |
|------|------|------|
| 来源权威度 | `news_intel/config/source_scores.json`（197 源综合评分表） | 重启 pipeline |
| 等级→分兜底映射 | `references/rss-importance-map.json` + 配置中心 `rss.feeds` importance | update_source_importance.py 同步 / 实时 |
| 事件关键词 | `news_intel/config/event_keywords.json`（500 词, v2 match 模式） | 重启 |
| 实体权重 | `news_intel/config/entity_weights.json` | 重启 |
| 资产图 | `news_intel/config/asset_graph.json` | 重启 |
| 五维权重 | 配置中心「评分」Tab（source_weight 等 6 键） | 热下发 |
| V4 importance | 配置中心「源列表」importance 字段（S/A/B/C/D） | 实时（scorer 兜底联动） |

> ⚠️ 改 config/ 后需 `python scripts/sync_profile.py --apply` 同步生产 profile（见 [local-env.md](../02-deployment/local-env.md)）。注意 sync_profile 默认排除 `.json`，source_scores.json 等评分配置需**手动 cp** 或调同步清单。

**等级同步命令（VPS）**：
```bash
# backend 容器内，按 Excel 建议等级更新 settings rss.feeds 的 importance
docker compose exec backend python /host/scripts/news-platform-v8/update_source_importance.py
```
