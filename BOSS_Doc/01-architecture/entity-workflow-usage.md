# 业务工作流 — 实体使用环节表

> 版本: v1.2 · 2026-08-07
> 定位: **按表格速查** —— 当前业务工作流（采集→展示）哪些环节用到实体/关系库、用什么库、如何实现、产出落点在哪。
> 依据: 代码逐行核实（`search-engine-v2/scripts/`）+ [business-process.md](business-process.md)。
> 相关: [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)（详细分析+升级方案）· [entity-kb.md](entity-kb.md) · [knowledge-base.md](knowledge-base.md)

---

## 1. 总览表（工作流各环节 × 实体使用）

### 知识库使用 vs 闲置审计（2026-08-09 实测）

#### 实际使用（运行时活跃）

| KB 组件 | 消费方 | 用途 |
|---------|--------|------|
| countries/companies/people/organizations/entity_alias yaml | `canonicalizer.resolve_entity`（loader.resolve）| Fact 抽取实体中英别名 → 稳定 ID |
| industries（IND_SUB_ 细分赛道）| `backfill_entity_model.py` | 公司→细分赛道 in_segment 关系 |
| relations（类型下拉）| `entity_relations.py /types` API | 配置中心关系类型 108 种 |
| 云端 entities/entity_alias/entity_relationship/event_relations | 实体列表/画像/关系网络/事件关系 API + 配置中心 | 前端 `/entities/[name]` 画像、`/config` 实体关系 Tab |

#### ⚠️ 闲置 / 未使用（2026-08-09 实测）

| KB 组件 | 状态 | 说明 |
|---------|:--:|------|
| **actions.yaml（81 动作）** | 🟡 闲置 | loader 全量加载, 但动作检测用 `aggregator.py ACTION_MAP` **硬编码**, 不从 yaml 读; 仅 generate_kb.py 生成用 |
| **event_types.yaml（29 类型）** | 🟡 闲置 | 事件类型分类用 `_classify_topics` 硬编码, 不从 yaml 读 |
| **locations.yaml（40）** | 🟡 闲置 | 地点解析用 `canonicalizer CITY_TO_COUNTRY` 硬编码, 不从 yaml 读 |
| **industries（GICS 25）** | 🟡 半闲置 | IND_SUB_ 细分赛道用; GICS 行业仅作 company.industry 字段, 无运行时按行业查询 |
| **relations.yaml（108 种定义）** | 🟡 半闲置 | 仅用于类型下拉; 实际关系实例由 backfill 派生 (sub_segments/parent), 非读 relations.yaml 数据 |
| **entity-network.json（旧体系）** | 🔴 回退 | backfill 已改读 KB V1 (KB_V1_CANDIDATES 优先), entity-network 仅失败时回退; 配置中心实体管理仍引用 |

#### 双实体源说明（评分用 vs 知识库用）

```
评分 (scorer.py 运行时活跃):  entity_weights.json(559) + value_tiers.json(T1-T10) + asset_graph.json(39)
知识库 (canonicalizer/backfill 活跃): knowledge_base/*.yaml → 实体 ID / 关系
两套独立: 评分用权重表, 知识库用稳定 ID — 评分实体已 100% 映射 KB (561/561)
```

#### 云端实体表（全部活跃, 2026-08-09 实测数据）

| 表 | 行数 | 消费 |
|----|:--:|------|
| entities | 27,366 | 实体列表/画像/事件 SAO |
| entity_alias | 41,089 | 实体管理/画像别名 |
| entity_relationship | 223 | 画像"关系网络" + 配置中心实体关系 |
| event_relations | 83 | 事件关系 + 配置中心 |

### GLiNER/Qwen 实体抽取实测（2026-08-09, 100 篇文章）

| 指标 | **GLiNER** (英文锚定) | **Qwen noThink** (中文/兜底) |
|------|:--:|:--:|
| **耗时** | **68ms/篇** (min 38 max 219) | **6.2s/篇** |
| **吞吐** | **~53,000 篇/小时** | **~580 篇/小时** |
| 实体数 | 2.0 实体/篇 | 结构化 Fact (subject/object/action) |
| 置信 | 0.859 | — |
| **英文准确率** | ✅ 高 (Samsung/SK Hynix/Micron 0.97、Brazil/Maruti 0.96 全对) | — |
| **中文准确率** | ❌ **差**（空结果/边界错: "赖清德亲自参与"整短语）| ✅ **高**（特朗普→行政命令、赖清德→汉光演习、沙特→防务协议 3/3 主体正确）|
| KB 解析率 | 34% (表面形式 vs KB 精确匹配) | 主体多可解析 |

**结论**（印证设计）:
- **英文 → GLiNER 快路径**（68ms, 吞吐 5.3 万/时, 高置信）——成本可忽略
- **中文 → Qwen 兜底**（6.2s, 吞吐 580/时, 高准确）——准确优先
- GLiNER small-v1 对中文边界不精准（已验证）, 中文实体抽取必须走 Qwen（对应 ISS-20260806-001/002）
- KB 解析率 34% 为 GLiNER 表面形式 vs KB 精确匹配的松代理, 不反映抽取正确性

> ✅=直接用 · 🔄=间接用（经归一函数） · ➖=不用

| #   | 环节                   | 用实体?  | 实体/关系库来源                                                    | 实现机制（关键函数 + 逻辑）                                                                                                                                                                                                                                                              | 产出 / 落点                                                                                        | 代码定位                                                                                                         |
| --- | -------------------- | :---: | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 0   | **采集** (rss-scanner) |   ➖   | 无                                                           | 只 RSS 抓取 + SHA256 去重；实体无关                                                                                                                                                                                                                                                    | rss_articles 原始文章                                                                              | `hermes-cron/rss-scanner.py`                                                                                 |
| 1   | **评分**               |   ✅   | `entity_weights.json`（340公司/84人物/34国/101机构）                        | `score_entities(title,desc)` 遍历实体名权重表，`_entity_in_text` 匹配（CJK子串 / 拉丁词边界 / ≤3短名大小写敏感）→ 命中取最高权重 `min(20)`；同时产出实体清单                                                                                                                                                            | 五维评分 entity 维(满分20) + `entities{companies,persons,countries}` → 云端 `articles.entities`         | `scorer.py:125` `:109` / `db.py:275`                                                                         |
| 2   | **Fact 抽取**          |   ✅   | **KB V1** `knowledge_base/*.yaml`（249国/~8300公司/~18800人物 + 别名） | 三层归一: GLiNER 实体锚定 → `resolve_entity`（① `loader.resolve()` KB 中英别名→稳定ID ② 回退 entity_weights 别名 + `CITY_TO_COUNTRY` 33城 + `_infer_type` ③ `_ID_PREFIX` 生成ID）→ `ontology_validator`（ID前缀↔类型 + REL_ 白名单）                                                                         | `fact_entity{entity_id(KB V1稳定ID), entity_name, type, role}` → `/internal/facts/batch`         | `fact_pipeline.py:156` / `canonicalizer.py:283` / `knowledge_base/loader.py:87` / `ontology_validator.py:61` |
| 3   | **事件聚合**             |  🔄   | 文章 `entities` 清单 + GLiNER + Fact 实体（经归一函数间接用 KB）            | `_canonicalize`(调 resolve_entity 归一) → `_compute_entity_idf`(全局/主题IDF) → `_entity_weight`(类型×idf) → `build_fused_fingerprint`(subject/object←fact优先+CJK信任门、hub降权、标题×2) → `fingerprint_score`(同主体+25跨语言/主题硬约束) → `_entity_name_to_id`(**本地生成ID,不查KB**) → `_infer_actor_roles` | 事件 `subject/object/actors/related_entities`（entity_id=本地ID）+ 本地 SQLite `entity_registry`       | `aggregator.py:85/289/387/682/484/1195/583/1165`                                                             |
| 4   | **推送/云端入库**          |  🔄   | 事件: 实体名；Fact: KB V1 ID                                      | `_event_to_push_format` 发原始结构 → `internal.py` UPSERT；events 存名、fact_entity 存 KB ID                                                                                                                                                                                           | `events.subject_name/object_name/actors(JSONB)` · `fact_entity.entity_id`                      | `pusher.py:144` / `internal.py`                                                                              |
| 5   | **知识加工/关系回填**        |   ✅   | entity-network associations + events + KB V1                | `backfill_entity_model.py`: 事件派生实体35 + KB 149 → `entities`；KB associations → `entity_relationship`(223)；同subject时间序 → `event_relations`(28)。`sync_kb_to_db.py`: KB V1 全量 → `entities/entity_alias`。`fill_entity_kb.py`: 事件派生 → `entity-network.json`                          | DB 4表: `entities`(27176)/`entity_alias`(41110)/`entity_relationship`(223)/`event_relations`(28) | `scripts/news-platform-v8/backfill_entity_model.py` `sync_kb_to_db.py` `fill_entity_kb.py`                   |
| 6   | **展示**               |   ✅   | entity-network.json + DB 关系表 + events                       | 列表: events subject/object/actors 去重计数+`_find_entity`(KB) 补类型/国家；画像: KB + DB(entities/alias/relationship in-out) + 相关事件；Story: `STORY_DIMENSIONS` 按 subject_name 等 4 维打包                                                                                                      | 前端 `/entities` `/entities/[name]` `/stories`                                                   | `routes/entities.py:223/272` / `stories.py:69`                                                               |
| 7   | **配置中心**             | ✅(管理) | entity-network.json + DB 4表                                 | 实体管理 Tab: 编辑→校验(悬空/重名)→保存热生效→git-sync；实体关系 Tab: 增删实体/事件关系 + regenerate(backfill)                                                                                                                                                                                             | 管理入口（只影响画像/回填，**不影响 Pipeline 抽取**）                                                             | `routes/entities.py` / `routes/entity_relations.py`                                                          |

---

## 2. 各环节字段明细（源字段 → 输出字段）

> 完整给出每个环节消费的**源字段**（输入）与产出的**输出字段**（含结构/落点）。实体相关字段全列出，非实体字段仅列出参与本环节的。

### 环节 0 采集（rss-scanner）— 无实体字段

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | RSS feed | `title, description, link(article_url), published, source_name, source_domain` | 197 RSS 源 |
| 输出字段 | rss_raw 表 | `id, guid, source_name, source_domain, feed_url, article_url, title, description, published_at, category_raw, created_at` | `~/.hermes/rss-archive.db` |
| 实体字段 | — | **无**（实体在第 1 环才生成） | — |
| 配置参数 | `rss.max_workers`(14), `rss.timeout`(10), `rss.hot_timeout`(6), `rss.cold_timeout`(15), `rss.quarantine_failures`(3), `rss.quarantine_seconds`(1800), `rss.proxy`(socks5://…) | 扫描并发/超时/隔离/代理（实体无关） | 配置中心「RSS 参数」Tab |

### 环节 1 评分（scorer）— 产出文章实体清单

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | `title`, `description` | 文本匹配对象 | `rss_raw` / 云端 articles |
| 源字段 | `entity_weights.json` | `{companies:{名:权重}, persons:{}, countries:{}}`（340公司/84人物/34国/101机构） | `scripts/news_intel/config/` |
| 输出字段 | `entities` | JSON `{companies:[], persons:[], countries:[]}`（命中实体名列表） | 本地 `news_intelligence.entities` → 云端 `articles.entities` |
| 输出字段 | `score_entity` | int 0–20（实体重要性维度，取最高权重） | `news_intelligence.score_entity` → 云端 `articles.score_breakdown.entity` |
| 配置参数 | `scoring.entity_weight`(20) ←**实体相关**；`scoring.source_weight`(20)/`impact`(30)/`market`(20)/`velocity`(10), `scoring.velocity_window`(30), `scoring.jaccard_threshold`(0.5)；`entity_weights.json`(文件, 非 UI) | 五维权重 + 实体权重表 | 配置中心「评分」Tab |

### 环节 2 Fact 抽取（fact_pipeline + canonicalizer + KB loader + ontology_validator）— 产出 KB V1 稳定 ID

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | `title`, `description`, `content_md` | 统一文本 `_get_text()` | 文章 |
| 源字段 | GLiNER `c_entities` | `[{label(person/organization/company/country/city), text}]` | GLiNER 模型 |
| 源字段 | Qwen Raw Fact | `{subject, object, action, time, location}` | Qwen noThink（中文/B 兜底） |
| 源字段 | `knowledge_base/*.yaml` | 中英别名索引（`loader._build_index`） | KB V1 |
| 输出字段 | `entities[]` | `[{entity_id, entity_name, entity_type, role}]`，role ∈ SUBJECT/OBJECT/TARGET/VICTIM/SOURCE/RESPONDER；entity_id=KB V1（`PERS_TRUMP`） | Fact payload → 云端 `fact_entity` 表 |
| 输出字段 | `action_type`, `action_event_type`, `action_detail`, `event_time`, `location` | 规范动作/时间/地点（实体无关但同 payload） | 云端 `fact` 表 |
| 配置参数 | `ai.tier_a_threshold`(90), `ai.tier_b_threshold`(60) ←Tier 分流；`ai.qwen_base`(`http://127.0.0.1:1234/v1`), `ai.qwen_model`(`qwen3-1.7b-instruct`), `ai.qwen_timeout`(60), `ai.qwen_max_tokens`(1024)；`ai.deepseek_model`(`deepseek-v4-flash`)/`timeout`(45)/`max_tokens`(800)/`temperature`(0.1)；**硬编码(非配置中心)** GLiNER `threshold=0.35`(`fact_pipeline.py:252/309`)、Qwen noThink `max_tokens=300`(`fact_pipeline.py:132`)、`FACT_PROMPT`(`fact_pipeline.py:42`) | Qwen 事实抽取 + Tier 分流 + GLiNER 实体阈值 | 配置中心「AI 增强」Tab（硬编码项需改代码） |

### 环节 3 事件聚合（aggregator）— 产出事件 SAO/actors/related_entities

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | 文章 `entities` | `{companies, persons, countries}`（环节 1 产出） | `articles.entities` |
| 源字段 | 文章 `title/description/content` | 指纹文本 | 文章 |
| 源字段 | GLiNER `ner_entities` | `_gliner_to_entities` 转 `{persons, companies, countries}` | GLiNER |
| 源字段 | Fact `entities[]` | `facts_by_article`（环节 2 产出） | fact payload |
| 中间字段 | fingerprint | `{subject, subject_weight, action, object, object_weight, event_type, primary_topic, secondary_topic, country, participants, anchor, _cjk}` | 内存 |
| 输出字段 | `subject` | `{entity_id(本地), name, type}` | → `events.subject_name`, `events.subject_type` |
| 输出字段 | `object` | `{entity_id(本地), name, type}` | → `events.object_name`, `events.object_type` |
| 输出字段 | `actors` | `[{entity, type, role(Initiator/Target/Participant)}]` | → `events.actors`(JSONB) |
| 输出字段 | `related_entities` | `[{entity_id, name, type}]`（前 20） | → `events.related_entities`(JSONB) |
| 输出字段 | `action` | `{type, detail}` | → `events.action_type/detail` |
| 输出字段 | entity_registry（本地） | `{entity_id, canonical_name, aliases, type, country, importance}` | SQLite `entity_registry`（57 条） |
| 配置参数 | `aggregate.event_threshold`(60), `aggregate.merge_threshold`(75), `aggregate.window_hours`(24), `aggregate.cross_lingual_threshold`(50) | 聚合/合并阈值 + 跨语言阈值；`cross_lingual` 由 loader 读取、配置中心 UI 可能未暴露 | 配置中心「聚合」Tab |

### 环节 4 推送/云端入库（pusher + internal）— 实体落库

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | 事件 payload | `subject/object/actors/related_entities`（环节 3 产出） | pusher |
| 源字段 | Fact payload | `entities[]`（环节 2 产出） | fact_pipeline |
| 输出字段 | events 表 | `subject_name, subject_type, object_name, object_type, actors(JSONB), related_entities(JSONB)` | PG `events` |
| 输出字段 | fact_entity 表 | `fact_id, entity_id(KB V1), entity_name, entity_type, role` | PG `fact_entity` |
| 输出字段 | articles 表 | `entities` JSON（环节 1 产出随文章推送） | PG `articles` |
| 配置参数 | `pipeline.cloud_chunk`(50 事件/批), `pipeline.content_chunk`(200 文章/批) | 云端推送批大小（实体无关） | 配置中心「Pipeline」Tab |

### 环节 5 知识加工/关系回填（backfill / sync / fill）— 产出 DB 实体/关系表

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | `events.subject_name / object_name / actors / location_country` | 事件派生实体提取 | PG `events` |
| 源字段 | `entity-network.json` | `entities.{leaders,business,companies}`, `associations[{from,type,to,desc}]`, `global_orgs` | `/host/references/` |
| 源字段 | `knowledge_base/*.yaml` | KB V1 全量（sync 用） | 仓库 |
| 输出字段 | `entities` 表 | `id, name, type, country, importance, aliases(JSONB), confidence, first_seen, last_seen` | PG（27176 行） |
| 输出字段 | `entity_alias` 表 | `entity_id, alias, lang` | PG（41110 行） |
| 输出字段 | `entity_relationship` 表 | `from_entity_id, to_entity_id, relation_type, confidence, description, evidence_count` | PG（223 行） |
| 输出字段 | `event_relations` 表 | `parent_event_id, child_event_id, relation_type(precedes), start_time, end_time, evidence_count` | PG（28 行） |
| 配置参数 | 无配置中心键（backfill/sync/fill 脚本手动跑，参数固定） | — | — |

### 环节 6 展示（entities / stories）— 实体消费输出

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | `events.subject_name / object_name / actors` | 实体计数 | PG `events` |
| 源字段 | `entity-network.json` + DB `entities/entity_alias/entity_relationship` | 画像合并 | KB + PG |
| 输出字段 | `GET /api/v1/entities` | `items[{name, event_count, category, country, type}]`, `total` | 前端 `/entities` |
| 输出字段 | `GET /api/v1/entities/{name}` | `entity{name,country,category,role/type}, aliases[], relationships[{entity,relation_type,direction,description}], associations[], related_events[], related_entities[], event_count, article_count` | 前端 `/entities/[name]` |
| 输出字段 | `GET /api/v1/stories` | `items[{story_id, title, dimension, event_count,...}], derived_at, by_dimension` | 前端 `/stories` |
| 配置参数 | 无配置中心键（API 响应字段固定） | — | — |

### 环节 7 配置中心（实体管理 / 实体关系）— 管理字段

| 方向 | 字段 | 结构 / 说明 | 来源 / 落点 |
|------|------|-------------|-------------|
| 源字段 | `entity-network.json` | 编辑对象（leaders/business/companies + associations） | `/host/references/` |
| 源字段 | DB 4 表 | 管理对象（实体/别名/实体关系/事件关系） | PG |
| 输出字段 | `entity-network.json` + `data_entity_kb.py` | 保存（校验→写 JSON→生成 py，热生效） | /host + 镜像 |
| 输出字段 | DB 关系增删 | `entity_relationship` / `event_relations` CRUD + regenerate | PG |
| 配置参数 | N/A（本环节即配置入口，管理对象见源字段；实体保存无额外参数） | — | — |

---

## 3. 关系库使用环节（relations / associations / entity_relationship）

> 关键结论: **关系数据在生产 Pipeline 几乎不用**，只在本体验证处做白名单校验；真正的实体-实体关系纯展示层。

| 关系数据 | 环节 | 用法 | 代码 |
|----------|:----:|------|------|
| `knowledge_base/relations.yaml`（106 种） | 2 Fact 归一 | `ontology_validator.validate_relationship` 仅校验 REL_ 前缀白名单（不读关系语义） | `ontology_validator.py:48` |
| `entity-network.json` associations | 5 回填 | → DB `entity_relationship` 表 | `backfill_entity_model.py` §3 |
| DB `entity_relationship`（223 条） | 6 展示 | 画像页"关系网络"（in/out 方向） | `routes/entities.py:346` |
| `event_relations`（28 条 precedes） | 5 回填 + 6 展示 | 同 subject 事件时间序派生 → `/events/{id}/relations` | `backfill_entity_model.py` §4 / `events_v1.py` |

> 待评估: 关系语义（competitor/investor/part_of）目前无任何事件/fact 生成逻辑消费 → 见 [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md) ISS-004。

---

## 4. 实体 ID 落点对照（两套体系）

| 载体 | 实体 ID 来源 | ID 示例 | 是否 KB V1 |
|------|--------------|---------|:----------:|
| `fact_entity.entity_id` | KB V1（`loader.resolve`） | `PERS_TRUMP` / `CTRY_CHN` / `COMP_NVIDIA` | ✅ |
| `events.subject/object.entity_id` | aggregator `_entity_name_to_id`（本地生成） | `COMP_APPLE` / `ENT_XXX` | ❌ |
| `events.subject_name/object_name` | canonicalizer canonical（KB 归一后名） | `Trump` / `China` | 🔄 |
| 本地 `entity_registry.entity_id` | 同上本地方案 | — | ❌ |
| DB `entities.name` | 事件派生 + KB + backfill canonical | `Trump` | 🔄 |

> ⚠️ 事件层与 Fact 层 entity_id 不同源 → 云端无法按 ID 跨表关联，只能 name 匹配（ISS-002）。

---

## 5. 一句话总结

> 实体**知识库**（KB V1 + entity_weights + GLiNER）在 **评分→Fact→聚合** 三个生产环节持续参与决策；实体**关系库**（relations/associations/entity_relationship）只在 **本体验证白名单** 与 **展示层画像** 使用，未进入事件/fact 生成逻辑。
