## Phase 1 升级方案 v1

### 总览

| 批次 | 任务数 | 预计工作量 | 目标 |
|:--:|:--:|:--:|------|
| Batch 1 (P0) | 3 | ~2h | Event Schema 冻结 + Entity ID + Action 枚举 |
| Batch 2 (P1) | 3 | ~2h | Lifecycle + Confidence + Evidence |
| Batch 3 (P2) | 2 | ~3h | 首发识别 + 实时雷达 |

---

### Batch 1 (P0) — Schema 冻结 + 数据闭环

#### 任务 1.1：Event Schema 冻结并实现

**现状**：`aggregate_events()` 返回 `{title, article_ids, entities, impact_level, max_score, actions, topics, start_time, last_time, coherence}`

**目标**：升级为冻结 Schema

```python
def aggregate_events(...) -> list[dict]:
    return [{
        # Identity
        "event_id": f"EVT-{start_time.strftime('%Y%m%d')}-{i+1:03d}",
        
        # Fact Layer
        "subject": {"name": ..., "type": ...},
        "action": {"type": ..., "detail": None},
        "object": {"name": ..., "type": ...},
        "event_type": ...,
        
        # Time/Location
        "event_time": start_time.isoformat(),
        "location": {"region": infer_region(country), "country": country},
        
        # Source & Evidence
        "source": {
            "type": infer_source_type(sources),
            "primary_source": first_source_name,
            "authority": max_source_authority,
            "source_count": len(set(sources)),
        },
        "doc_refs": [{"url": url, "title": title} for ...],
        
        # Participants
        "actors": infer_actor_roles(entities, action, object),
        
        # Description
        "title": best_title,
        "summary": generate_summary(title, articles),
        "keywords": list(unique_tags),
        
        # Quality
        "confidence": compute_confidence(source_authority, coherence, article_count),
        "coherence": coherence,
        "extraction_method": "v4.3-saeo",
        
        # Links
        "related_events": [],
        "related_entities": list(unique_entities),
        "article_count": len(article_ids),
    }]
```

**涉及文件**：`aggregator.py` (新增字段计算) + `aggregator.py` (输出结构改造)

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 20 --single 1
# 检查输出是否包含 event_id、source.authority、confidence、actors
```

#### 任务 1.2：Entity ID 体系贯通

**现状**：实体在各层独立存在，无统一 ID。如 "US" 在 L1 是 "US"，在 L8 canonicalize 后是 "United States"，但无全局 ID。

**目标**：`entities` 表（已有，PostgreSQL）作为 ID 源，L1→L8 统一引用 `entity_id`

**实现**：
1. L6 增强后，将实体名写入 PostgreSQL `entities` 表（`ON CONFLICT (name) DO NOTHING`）
2. L8 聚合时，从 `entities` 表查 ID 填入 fingerprint
3. 事件输出中 `related_entities` 携带 `{id, name, type}`

**涉及文件**：`enhancers.py`（写 entities 表）、`pusher.py`（传 entity_id）、`aggregator.py`（读 entity_id）

**验证**：
```bash
# 检查云端 entities 表有数据
sqlite3 news_intel/news_intel.db "SELECT COUNT(*) FROM entities"
# 事件输出中 related_entities 含 id
python test_aggregator.py --hours 24 --limit 10 --single 1 | grep entity_id
```

#### 任务 1.3：Action 枚举标准化

**现状**：21 种 action 字符串（SUES/ATTACKS/CEASEFIRE...），无结构化 detail。

**目标**：action 升级为 `{type, detail}` 结构

| type | detail 示例 |
|------|------|
| SUES | 窃取商业机密 |
| ATTACKS | 导弹打击军事设施 |
| SANCTIONS | 石油出口限制 |
| RATE_CUT | 25 basis points |

**实现**：在 `build_fingerprint` 中增加 `action_detail` 字段，从 description 中提取关键名词短语（取 action 匹配词后紧跟的 50 字符）。

**涉及文件**：`aggregator.py`（`build_fingerprint` + 输出结构）

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 20 -v
# 检查事件指纹中 action 是否包含 detail
```

---

### Batch 2 (P1) — Lifecycle + Confidence + Evidence

#### 任务 2.1：Event Lifecycle Stage/Status

**现状**：有 `start_time`/`last_time`，无阶段划分。

**目标**：增加 `stage` 字段

| Stage | 条件 |
|------|------|
| `breaking` | 首次出现, 最近 2h 内 |
| `developing` | 2h-24h, 持续有新文章 |
| `active` | 24h-7d, 有新更新 |
| `stable` | 7d+, 无新更新 |
| `closed` | 30d+, 无新文章 |

**实现**：在 Phase 3 输出中，根据 `start_time`/`last_time` + `article_count` 变化趋势计算。

**涉及文件**：`aggregator.py`（Phase 3 输出）

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 100
# 检查事件是否携带 stage 字段
```

#### 任务 2.2：Source-based Confidence

**现状**：只有 `coherence`（簇内一致性）。

**目标**：综合 confidence 公式

```python
confidence = (
    0.4 * source_authority_normalized +   # 来源权威 (L1 source_scores)
    0.3 * coherence_normalized +           # 簇内一致性 (V4.3)
    0.2 * article_diversity +              # 来源多样性 (不同源数量)
    0.1 * article_count_factor            # 文章数量因子 (tanh(n/10))
)
```

**实现**：在 `source_scores.json` 已有分数，事件输出时聚合所有来源的 max authority。

**涉及文件**：`aggregator.py`（Phase 3 输出）

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 50
# 检查事件 confidence 字段, 多源事件应 >0.7
```

#### 任务 2.3：Evidence Span 摘要

**现状**：事件只有 `title`（最长标题）和 `summary`（空）。

**目标**：`summary` 字段填入代表性摘要

```python
# 取 coherence 最高的前 3 篇文章的 summary_cn
top_articles = sorted(members, key=lambda a: coherence_with_centroid(a), reverse=True)[:3]
summary = " | ".join(a["summary_cn"] for a in top_articles)
```

**涉及文件**：`aggregator.py`（Phase 3 输出）+ `test_aggregator.py` 传 `summary_cn`

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 20 --single 1
# 检查输出含非空 summary 字段
```

---

### Batch 3 (P2) — 新卖点

#### 任务 3.1：首发识别

**目标**：从事件成员中找出 `published_at` 最早的文章 + 来源，填入 `source.primary_source` 和 `event_time`。

**实现**：事件已含所有文章的 `published_at`，只需在 Phase 3 输出时 `sort by time` 取第一条。

**涉及文件**：`aggregator.py`（Phase 3 输出）+ 日期解析改进

**验证**：
```bash
python test_aggregator.py --hours 24 --limit 50 -v
# 检查事件的 event_time 是否等于最早文章时间
```

#### 任务 3.2：实时事件雷达（最小可行版）

**目标**：pipeline 每次运行后，对比"本次新事件" vs "上次已知事件"，输出变化摘要。

**实现**：
1. `aggregate_events` 增加 `previous_events` 参数（可选）
2. 新增事件 → 标记 `is_new: true`
3. 已有事件新增文章 → 标记 `has_update: true`
4. 输出中添加 `delta_summary`

**涉及文件**：`aggregator.py`（新增对比逻辑）+ `pipeline.py`（传历史事件）

**验证**：
```bash
# 第一次运行
python test_aggregator.py --hours 24 --limit 100 > run1.json
# 第二次运行（1小时后）
python test_aggregator.py --hours 1 --limit 50 > run2.json
# diff 检查新事件和更新事件
```

---

### 验证总表

| 批次 | 任务 | 验证命令 | 预期 |
|:--:|------|------|------|
| 1.1 | Schema | `python test_aggregator.py --single 1` | 输出含 event_id/confidence/actors |
| 1.2 | Entity ID | `SELECT COUNT(*) FROM entities` | >0 |
| 1.3 | Action enum | `python test_aggregator.py -v` | action.type 含 detail |
| 2.1 | Lifecycle | `python test_aggregator.py` | 事件含 stage |
| 2.2 | Confidence | `python test_aggregator.py` | 多源事件 confidence>0.7 |
| 2.3 | Evidence | `python test_aggregator.py --single 1` | summary 非空 |
| 3.1 | 首发 | `python test_aggregator.py --single 1` | primary_source 非空 |
| 3.2 | 雷达 | 两次运行对比 | is_new/has_update 正确 |

---

### 风险提示

| 风险 | 缓解 |
|------|------|
| Schema 过于复杂导致维护困难 | 先只实现 Batch 1.1 的核心 8 字段 |
| Entity ID 写 PostgreSQL 需网络 | 可用本地 SQLite 映射表替代 |
| RSS 日期截断导致 event_time=None | 复用 `_parse_date` 的 RSS parser，增加截断日期容错 |
| 雷达对比需要持久化上次结果 | 写入 `~/.hermes/event-snapshot.json` |

---

确认 Batch 1 后我立即开始实施。