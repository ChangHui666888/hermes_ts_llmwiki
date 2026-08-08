# 五维评分规则

> 基于 `news_intel/scorer.py`（**2026-08-08 最新代码**，含 V4 importance 联动 + 197 源综合评分表）
> 配置数据源: `news_intel/config/`（source_scores.json / event_keywords.json / entity_weights.json / asset_graph.json）+ `references/rss-importance-map.json`
> 入口: `score_article()` 返回 `{total, source, impact, entity, market, velocity, tier, categories, entities, market_assets, velocity_count}`

## 评分总览

| 维度 | 满分 | 方法 | 数据源 |
|------|:----:|------|--------|
| Source Authority | 20 | 来源权威度查表 + **V4 importance 兜底** | source_scores.json + rss.feeds |
| Event Impact | 30 | 关键词命中（5 领域，同类取最高，不累加） | event_keywords.json |
| Entity Importance | 20 | 实体权重查表（词边界匹配） | entity_weights.json |
| Market Relevance | 20 | 资产映射图（实体/关键词→股票） | asset_graph.json |
| Velocity | 10 | 30 分钟内同事件（同指纹）报道数 | 跨文章 Jaccard |
| **总分** | **100** | 五项累加, 封顶 100 | — |

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

**方法**: 对 `title + description` 小写后关键词命中。遍历 5 个分类，**每个分类取该类最高分，最终取所有分类最高（不累加，防标题党刷分）**。

**5 个分类**（event_keywords.json，2026-08-08 实际）:

| 分类                 | 关键词数 | 高分示例                             |
| ------------------ | :--: | -------------------------------- |
| **finance** 金融     |  40  | 利率决议 30 / 降息 30 / 加息 30          |
| **geopolitics** 地缘 |  29  | 战争 30 / war 30 / 冲突 25           |
| **ai_tech** AI科技   |  29  | GPT-5 28 / GPT-4 22 / ChatGPT 20 |
| **market** 市场      |  19  | 标普 20 / S&P 20 / 纳斯达克 20         |
| **china** 中国       |  16  | 两会 25 / 政治局 25 / 国务院 22          |

```python
def score_impact(title, description):
    for category, kw_dict in keywords.items():
        cat_best = max(score for kw, score in kw_dict.items() if kw.lower() in text)
        if cat_best > max_score: max_score = cat_best   # 跨类取最高，不累加
    return min(max_score, 30), hit_categories
```

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
| 事件关键词 | `news_intel/config/event_keywords.json` | 重启 |
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
