# 五维评分规则

> 基于 `news_intel/scorer.py` (2026-07-29 最新代码)
> 配置数据来源: `news_intel/config/source_scores.json`, `event_keywords.json`, `entity_weights.json`, `asset_graph.json`

## 评分总览

| 维度 | 满分 | 方法 |
|------|:----:|------|
| Source Authority | 20 | 来源权威度查表 (70+ 源) |
| Event Impact | 30 | 关键词命中 (5 领域, 同类取最高) |
| Entity Importance | 20 | 实体权重查表 (公司/人物/国家) |
| Market Relevance | 20 | 资产映射图 (实体→股票/ETF) |
| Velocity | 10 | 30 分钟内同源报道数 |
| **总分** | **100** | 五项累加, 封顶 100 |

## Tier 划分

| Tier | 分数范围 | 增强方式 | 成本 |
|:----:|:--------:|----------|:----:|
| A | ≥ 90 | DeepSeek V4 Flash | ~$0.002/篇 |
| B | 60–89 | Qwen3-1.7B 本地 | 免费 (60s 超时) |
| C | < 60 | Python 规则 (零成本) | $0 |

---

## 1. Source Authority (0-20)

**方法**: 查 `source_scores.json` 表, 按 RSS 来源名称直接映射。

```python
def score_source(source_name: str) -> int:
    scores = _load_json("source_scores.json")["scores"]
    return scores.get(source_name, scores.get("_default", 5))
```

**示例分值**:

| 来源 | 分值 |
|------|:----:|
| Reuters Top | 20 |
| AP Top News | 20 |
| Bloomberg Markets | 18 |
| BBC News / CNN | 18 |
| WSJ World | 18 |
| NYT Home | 18 |
| Fed Press / SEC Press | 20 |
| Hacker News | 8 |
| Reddit WorldNews | 5 |
| 未知来源 | 5 (默认值) |

---

## 2. Event Impact (0-30)

**方法**: 对 `title + description` 做关键词匹配。5 个领域各取最高分关键词, **不累加**, 取最大值。

| 领域 | 最高分 | 示例关键词 |
|------|:------:|-----------|
| 🚨 军事/冲突 | 30 | attack, strike, war, military, sanctions |
| ⚖️ 法律/监管 | 25 | sue, lawsuit, charged, files complaint |
| 🏛️ 政治/外交 | 20 | summit, announces, election, policy |
| 💰 金融/经济 | 15 | tariff, inflation, rate cut, earnings |
| 🔬 科技/医疗 | 10 | AI, breakthrough, FDA, launch |

```python
for category, kw_dict in keywords.items():
    for keyword, score in kw_dict.items():
        if keyword.lower() in text:
            if score > cat_best:
                cat_best = score
    if cat_best > max_score:
        max_score = cat_best   # ← 跨类别取最高，不累加
```

---

## 3. Entity Importance (0-20)

**方法**: 从 `title + description` 中匹配预定义重要实体。按实体类型分组:

| 类型 | 示例 | 最高权重 |
|------|------|:--------:|
| Companies | Apple, OpenAI, Tesla, Nvidia | 20 |
| Persons | Trump, Powell, Musk, Zelenskiy | 18 |
| Countries | US, China, Iran, Ukraine | 15 |

同类型取最高分实体, 跨类型也取最大值（不累加）。

---

## 4. Market Relevance (0-20)

**方法**: 两层匹配——实体→资产映射 + 关键词→资产映射。

```python
# 第一层: 匹配到的实体 → 关联股票
for ent in all_entities:
    for asset_key, asset_info in graph.items():
        if ent in asset_info.get("stocks", []):
            max_score = max(max_score, asset_info["weight"])

# 第二层: 标题/摘要中的关键词 → 关联股票
for asset_key, asset_info in graph.items():
    if asset_key.lower() in text:
        max_score = max(max_score, asset_info["weight"])
```

**示例映射**:

| 关键词/实体 | 影响的资产 | 权重 |
|-------------|-----------|:----:|
| Fed, rate, Powell | SPY, QQQ, TLT, DXY | 20 |
| Apple, AAPL | AAPL | 20 |
| Tesla, Elon Musk | TSLA | 18 |
| Oil, crude | USO, XLE | 18 |
| Inflation | TIPS, TLT | 15 |

---

## 5. Velocity (0-10)

**方法**: 统计 30 分钟内同一事件被多少 RSS 源报道。通过 Jaccard 指纹比对判断是否为同一事件。

```python
def score_velocity(velocity_count):
    if velocity_count >= 10: return 10
    if velocity_count >= 5:  return 5
    if velocity_count >= 2:  return 2
    return 0
```

**指纹生成**:
```
1. 标题分词 → 去停用词(38个中英文)
2. 取前 8 个实词的 set
3. Jaccard 相似度 ≥ 0.5 视为同一事件
```

**Velocity 计算场景**:

| 同时报道源数 | 得分 | 含义 |
|:-----------:|:----:|------|
| 0–1 源 | 0 | 独家/冷门 |
| 2–4 源 | 2 | 多家关注 |
| 5–9 源 | 5 | 热点发酵 |
| 10+ 源 | 10 | 全网热点 |

---

## 配置数据文件

所有评分配置存储在 `news_intel/config/` 目录下:

| 文件 | 用途 |
|------|------|
| `source_scores.json` | 70+ 新闻源权威度分值 |
| `event_keywords.json` | 5 领域事件关键词与权重 |
| `entity_weights.json` | 公司/人物/国家实体权重 |
| `asset_graph.json` | 实体/关键词 → 股票/ETF 映射 |
