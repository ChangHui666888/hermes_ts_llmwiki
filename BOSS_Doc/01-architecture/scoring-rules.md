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

**5 个分类 · 500 关键词**（event_keywords.json，2026-08-08 v2；每类取该类最高、跨类只取所有分类最高，不累加）:

| 分类 | 关键词数 | 高分示例 |
|------|:--:|------|
| **finance** 金融 | 120 | 利率决议/降息/加息/美联储/Fed/破产/熔断/银行危机/bank failure = 30 |
| **geopolitics** 地缘 | 100 | 战争/war/政变/coup/暗杀/assassin/入侵/nuclear = 30 |
| **ai_tech** AI科技 | 120 | GPT-5/AGI/超级智能/superintelligence = 28 |
| **market** 市场 | 70 | 熊市/股市崩盘/flash crash/market crash = 22 |
| **china** 中国 | 90 | 台海危机/中美贸易战/台海冲突 = 30 |

> 📋 完整 500 关键词清单以 `news_intel/config/event_keywords.json` 为**权威来源**（含中文+英文多词短语），此处不再全量展开。

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

| 指标 | 旧 (133词+substring) | 新 (500词+v2) | 说明 |
|------|:--:|:--:|------|
| 平均 impact 分 | 14.30 | 7.28 | 旧 substring 系统性虚高 |
| impact=0 文章 | 1283 | 2619 | +1336 篇纠正为 0（原误标） |
| 新增命中（新>旧） | — | 451 篇 | 500 词覆盖面提升 |
| **误标修复**（word_boundary） | — | **1591 篇** | 核心收益 |
| 真关键词精化 | — | 4 篇 | 台海→台海危机 / GPU→芯片 |
| `Federal Reserve` 全名缺口 | — | 3 篇 | 均为低价值审批公告，可接受 |

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

**数据规模**: entity_weights.json — **34 国 + 79 人物 + 88 公司**（含中英别名）。

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

**方法**: 两条路径，取最高权重 `min(max_score, 20)`，同时产出受影响资产列表：
1. **实体 → 资产映射**：文章已识别实体若在资产图 stocks 中 → 该资产权重
2. **关键词 → 资产映射**：资产键（如 "GPU"/"降息"/"war"）在文本中 → 该资产权重

**资产图**（asset_graph.json，2026-08-08 实际）:

| 资产键 | 权重 | 受影响股票 |
|--------|:--:|------|
| GPU / AI芯片 / 出口管制 / chip export / 降息 / rate cut / 加息 / rate hike | 20 | NVIDIA/AMD/TSMC/ASML 或 JPMorgan/GS/BoA |
| 石油 / oil | 18 | Exxon/Chevron/Shell/BP |
| 半导体 / semiconductor / Bitcoin / 国防 / defense / 战争 / war | 18 | TSMC/Intel 或 Lockheed/RTX/Exxon |
| 加密货币 / crypto / 电动车 / EV | 15 | Coinbase/MSTR 或 Tesla/BYD |
| 云计算 / cloud / 制药 / pharma | 12 | Amazon/MS/Google 或 Pfizer/Moderna |

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

**指纹 `_make_fingerprint_set`**: 标题分词 → 去停用词（英文 the/a/an 等 + 中文 的/了/在 等 + s/re/ve）→ 取前 8 个实词。

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
