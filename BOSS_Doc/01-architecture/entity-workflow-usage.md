# 业务工作流 — 实体使用环节表

> 版本: v1.0 · 2026-08-07
> 定位: **按表格速查** —— 当前业务工作流（采集→展示）哪些环节用到实体/关系库、用什么库、如何实现、产出落点在哪。
> 依据: 代码逐行核实（`search-engine-v2/scripts/`）+ [business-process.md](business-process.md)。
> 相关: [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)（详细分析+升级方案）· [entity-kb.md](entity-kb.md) · [knowledge-base.md](knowledge-base.md)

---

## 1. 总览表（工作流各环节 × 实体使用）

> ✅=直接用 · 🔄=间接用（经归一函数） · ➖=不用

| # | 环节 | 用实体? | 实体/关系库来源 | 实现机制（关键函数 + 逻辑） | 产出 / 落点 | 代码定位 |
|---|------|:------:|----------------|------------------------------|-------------|----------|
| 0 | **采集** (rss-scanner) | ➖ | 无 | 只 RSS 抓取 + SHA256 去重；实体无关 | rss_articles 原始文章 | `hermes-cron/rss-scanner.py` |
| 1 | **评分** | ✅ | `entity_weights.json`（34国/79人物/88公司） | `score_entities(title,desc)` 遍历实体名权重表，`_entity_in_text` 匹配（CJK子串 / 拉丁词边界 / ≤3短名大小写敏感）→ 命中取最高权重 `min(20)`；同时产出实体清单 | 五维评分 entity 维(满分20) + `entities{companies,persons,countries}` → 云端 `articles.entities` | `scorer.py:125` `:109` / `db.py:275` |
| 2 | **Fact 抽取** | ✅ | **KB V1** `knowledge_base/*.yaml`（249国/8038公司/18790人物 + 别名） | 三层归一: GLiNER 实体锚定 → `resolve_entity`（① `loader.resolve()` KB 中英别名→稳定ID ② 回退 entity_weights 别名 + `CITY_TO_COUNTRY` 33城 + `_infer_type` ③ `_ID_PREFIX` 生成ID）→ `ontology_validator`（ID前缀↔类型 + REL_ 白名单） | `fact_entity{entity_id(KB V1稳定ID), entity_name, type, role}` → `/internal/facts/batch` | `fact_pipeline.py:156` / `canonicalizer.py:283` / `knowledge_base/loader.py:87` / `ontology_validator.py:61` |
| 3 | **事件聚合** | 🔄 | 文章 `entities` 清单 + GLiNER + Fact 实体（经归一函数间接用 KB） | `_canonicalize`(调 resolve_entity 归一) → `_compute_entity_idf`(全局/主题IDF) → `_entity_weight`(类型×idf) → `build_fused_fingerprint`(subject/object←fact优先+CJK信任门、hub降权、标题×2) → `fingerprint_score`(同主体+25跨语言/主题硬约束) → `_entity_name_to_id`(**本地生成ID,不查KB**) → `_infer_actor_roles` | 事件 `subject/object/actors/related_entities`（entity_id=本地ID）+ 本地 SQLite `entity_registry` | `aggregator.py:85/289/387/682/484/1195/583/1165` |
| 4 | **推送/云端入库** | 🔄 | 事件: 实体名；Fact: KB V1 ID | `_event_to_push_format` 发原始结构 → `internal.py` UPSERT；events 存名、fact_entity 存 KB ID | `events.subject_name/object_name/actors(JSONB)` · `fact_entity.entity_id` | `pusher.py:144` / `internal.py` |
| 5 | **知识加工/关系回填** | ✅ | entity-network associations + events + KB V1 | `backfill_entity_model.py`: 事件派生实体35 + KB 149 → `entities`；KB associations → `entity_relationship`(26)；同subject时间序 → `event_relations`(28)。`sync_kb_to_db.py`: KB V1 全量 → `entities/entity_alias`。`fill_entity_kb.py`: 事件派生 → `entity-network.json` | DB 4表: `entities`(27176)/`entity_alias`(41110)/`entity_relationship`(26)/`event_relations`(28) | `scripts/news-platform-v8/backfill_entity_model.py` `sync_kb_to_db.py` `fill_entity_kb.py` |
| 6 | **展示** | ✅ | entity-network.json + DB 关系表 + events | 列表: events subject/object/actors 去重计数+`_find_entity`(KB) 补类型/国家；画像: KB + DB(entities/alias/relationship in-out) + 相关事件；Story: `STORY_DIMENSIONS` 按 subject_name 等 4 维打包 | 前端 `/entities` `/entities/[name]` `/stories` | `routes/entities.py:223/272` / `stories.py:69` |
| 7 | **配置中心** | ✅(管理) | entity-network.json + DB 4表 | 实体管理 Tab: 编辑→校验(悬空/重名)→保存热生效→git-sync；实体关系 Tab: 增删实体/事件关系 + regenerate(backfill) | 管理入口（只影响画像/回填，**不影响 Pipeline 抽取**） | `routes/entities.py` / `routes/entity_relations.py` |

---

## 2. 关系库使用环节（relations / associations / entity_relationship）

> 关键结论: **关系数据在生产 Pipeline 几乎不用**，只在本体验证处做白名单校验；真正的实体-实体关系纯展示层。

| 关系数据 | 环节 | 用法 | 代码 |
|----------|:----:|------|------|
| `knowledge_base/relations.yaml`（106 种） | 2 Fact 归一 | `ontology_validator.validate_relationship` 仅校验 REL_ 前缀白名单（不读关系语义） | `ontology_validator.py:48` |
| `entity-network.json` associations | 5 回填 | → DB `entity_relationship` 表 | `backfill_entity_model.py` §3 |
| DB `entity_relationship`（26 条） | 6 展示 | 画像页"关系网络"（in/out 方向） | `routes/entities.py:346` |
| `event_relations`（28 条 precedes） | 5 回填 + 6 展示 | 同 subject 事件时间序派生 → `/events/{id}/relations` | `backfill_entity_model.py` §4 / `events_v1.py` |

> 待评估: 关系语义（competitor/investor/part_of）目前无任何事件/fact 生成逻辑消费 → 见 [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md) ISS-004。

---

## 3. 实体 ID 落点对照（两套体系）

| 载体 | 实体 ID 来源 | ID 示例 | 是否 KB V1 |
|------|--------------|---------|:----------:|
| `fact_entity.entity_id` | KB V1（`loader.resolve`） | `PERS_TRUMP` / `CTRY_CHN` / `COMP_NVIDIA` | ✅ |
| `events.subject/object.entity_id` | aggregator `_entity_name_to_id`（本地生成） | `COMP_APPLE` / `ENT_XXX` | ❌ |
| `events.subject_name/object_name` | canonicalizer canonical（KB 归一后名） | `Trump` / `China` | 🔄 |
| 本地 `entity_registry.entity_id` | 同上本地方案 | — | ❌ |
| DB `entities.name` | 事件派生 + KB + backfill canonical | `Trump` | 🔄 |

> ⚠️ 事件层与 Fact 层 entity_id 不同源 → 云端无法按 ID 跨表关联，只能 name 匹配（ISS-002）。

---

## 4. 一句话总结

> 实体**知识库**（KB V1 + entity_weights + GLiNER）在 **评分→Fact→聚合** 三个生产环节持续参与决策；实体**关系库**（relations/associations/entity_relationship）只在 **本体验证白名单** 与 **展示层画像** 使用，未进入事件/fact 生成逻辑。
