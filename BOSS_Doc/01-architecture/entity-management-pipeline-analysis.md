# 实体管理链路分析 + 升级方案 — 配置中心 ↔ 业务流程

> 版本: v1.1 · 2026-08-07 · **状态: 🟡 待决策**
> 定位: 梳理"配置中心实体管理/实体关系"与"项目业务流程实际使用的实体"之间的关联，并提出升级方案供决策。
> v1.1: 展开 §三——逐环节写明实体/关系库的具体实现逻辑（评分/归一/聚合/回填/展示），并补充"关系库在生产中几乎不使用"的核查结论。
> 依据: 代码逐行核实（`search-engine-v2/scripts/news-platform-v8/` + `scripts/news_intel/` + `knowledge_base/`）+ 现有 Wiki 文档 + 记忆。
> 相关文档: [knowledge-base.md](knowledge-base.md) · [entity-kb.md](entity-kb.md) · [entity-relationships.md](entity-relationships.md) · [business-process.md](business-process.md) · [database.md](database.md)

---

## 一、核心结论（先给答案）

**配置中心"实体管理/实体关系"管理的是"展示层画像库 + DB 关系表"；而 Pipeline 抽取决策真正依赖的是另一套 `knowledge_base/*.yaml`（KB V1）。两者之间存在单向数据流（KB→DB→画像），但没有"配置中心改实体→影响线上抽取"的回流通道。**

- **实体管理 Tab** 管理 `entity-network.json`（静态画像 KB，13 国深度关系）——下游是实体画像页与 DB 回填，**不影响 Pipeline 归一**。
- **实体关系 Tab** 管理 PG 四张表（`entities/entity_alias/entity_relationship/event_relations`）——其中**实体名确实来自业务流程**（事件 subject/object/actors 派生），是流程实体真实回流的一环。
- **Pipeline 实体归一**（Fact 抽取、本体验证）用 `knowledge_base/*.yaml`（KB V1，249 国/~8300 公司/~18800 人物）——由 AI 工作流(wiki+git)维护，**配置中心 UI 够不到**。

三套实体数据源互相独立，靠 `backfill_entity_model.py` / `sync_kb_to_db.py` / `fill_entity_kb.py` 三个脚本单向桥接。

**关系库使用现状（新增核查）**：整个项目中"关系"数据（`knowledge_base/relations.yaml` 106 种、`entity-network.json` associations、DB `entity_relationship` 表）**在生产 Pipeline 里几乎不被使用**——仅 `ontology_validator.py` 用 REL_ 前缀做关系类型白名单校验（不读关系内容）；真正的实体-实体关系只服务展示层（画像页关系网络 + 配置中心实体关系 Tab）。`relations.yaml` 的关系语义（competitor/investor/part_of 等）尚无任何事件/fact 生成逻辑消费。

---

## 二、配置中心实体管理的实现

### 2.1 「实体管理」Tab（🧩，管理 JSON KB）

- **前端**: `frontend/src/app/config/page.tsx:888` — 按国家三栏（国家领导/商界人物/企业机构）+ 关联网络(associations)，操作流 = 校验 → 保存(热生效) → 同步 Git。
- **后端**: `routes/entities.py` — `GET/POST /admin/entities`(+save/dry_run)、`POST /admin/entities/git-sync`。
  - `_load_kb()`: **文件优先**（`/host/references/entity-network.json` 热更新），import 失败才回退内嵌 `data_entity_kb.py`。
  - `validate_kb()`: 悬空引用（associations 的 from/to 不在 known 集）、跨国家重名、缺 name 条目标记。
  - `_write_kb()` + `_regen_py()`: 保存=写 JSON + 重新生成 py，**下次请求即生效，无需重建镜像**。
  - `git-sync`: 容器内 git `safe.directory` + 显式身份，**只 add 实体 2 个文件**（规避 VPS 顶层陈旧 frontend/nginx.conf 误提交）。

### 2.2 「实体关系」Tab（🕸️，管理 DB 表）

- **前端**: `page.tsx:1056` — 实体列表(搜索/类型/别名) + 实体关系 CRUD + 事件关系管理 + "从KB重新生成"按钮。
- **后端**: `routes/entity_relations.py`:
  - `GET /admin/entity-relations`: 全量 `entities` + 别名 map + `entity_relationship`(join 名) + `event_relations`。
  - `POST` 新增关系（按 name/alias 反查 entity_id，FK 校验）；`DELETE` 删除实体/事件关系。
  - `POST /admin/entity-relations/regenerate`: 容器内跑 `backfill_entity_model.py`（120s 超时）。
- **ORM 模型**（`models.py:96-153`）: `Entity`(id/name/type/country/importance/aliases/confidence/first_seen/last_seen)、`EntityAlias`(entity_id/alias/lang 唯一)、`EntityRelationship`(from/to/relation_type/confidence/desc/evidence_count)、`EventRelation`(parent/child/relation_type/start/end_time)。

---

## 三、整个工作流程：实体/关系库的使用环节与具体实现逻辑

> 总览图（哪些环节用了"实体"，哪些用了"关系库"）：
>
> ```
> 采集 → 评分 → Fact抽取 → 事件聚合 → 推送 → 云端DB → 展示/Story
>  │      │        │           │        │       │         │
>  │    ①文章实体  ②KB V1归一  ③实体ID   ④落库   ⑤关系回填  ⑥画像/Story
>  │    清单        +本体验证   +actors   +fact    (assoc)   +关系网络
> 不用实体库   用entity_weights  用knowledge_base  不用关系库   用associations
> ```
>
> **关键结论先行**：实体知识库（KB V1 / entity_weights / GLiNER）在**采集→评分→Fact→聚合**四个生产环节被频繁使用；而**关系库（relations.yaml REL_ 前缀、entity-network associations、entity_relationship 表）在 Pipeline 生产中几乎不被使用**——只在三层归一的第三层（本体验证）做了 REL_ 前缀白名单，真正的实体-实体关系（entity_relationship / 画像关联网络）纯属展示层数据。

### 环节 0 — 采集（rss-scanner）｜ 不直接用实体库

- 只做 RSS 抓取 + SHA256 去重，实体无关。文章级实体清单**不在采集时生成**，而在下一环评分时附带产出。

### 环节 1 — 评分（scorer.py）｜ 用 `entity_weights.json`（第三套实体清单）

**用途**：五维评分中的"实体重要性"维度（满分 20 分），同时产出文章级实体清单供下游。

**具体逻辑**（`scorer.py`）：
- `score_entities(title, description)`（:125）：把标题+摘要拼成 `text`，遍历 `entity_weights.json` 三个分组 `companies/persons/countries` 的每个实体名，用 `_entity_in_text(name, text)`（:109）匹配——
  - **CJK 名 → 子串匹配**（无词边界）；**拉丁名 → 词边界 `\b`**；**≤3 字符短名（US/BP/UK）→ 大小写敏感**（防 'Xi' 命中希腊字母 xi、'US' 命中任意 us 子串）。
  - 命中即取该实体权重，`max_score` 取最大值，`return min(max_score, 20)`。
- 返回 `(分数, {companies:[...], persons:[...], countries:[...]})` → `score_article()`（:248）放入总分 `entity` 维 → `upsert_intelligence()`（`db.py:275`）把 `entities` JSON 存进本地 `news_intelligence.entities`。
- 该 `entities` 清单随文章推送到云端 `articles.entities`（JSONB `{companies, persons, countries}`）——**它是后续聚合器事件聚类的实体输入源之一**。

### 环节 2 — Fact 抽取（fact_pipeline + canonicalizer + knowledge_base/loader + ontology_validator）｜ 用 KB V1（唯一真正用知识库的环节）

**用途**：把 LLM(Qwen noThink)/GLiNER 抽出的 Raw Fact 规范化为稳定 Entity ID + Role 模型。这是"实体库影响 Pipeline 决策"的唯一关口。

**三层归一逻辑**（Wiki `knowledge-base.md` 三层图）：
```
原始新闻 → GLiNER/LLM 抽取 → AliasResolver(knowledge_base/loader) → Canonicalizer(Entity ID) → OntologyValidator → fact/fact_entity
```

1. **GLiNER 实体锚定**（`fact_pipeline.py`）：`ground(p, ents)` 从 GLiNER 实体列表中找含该主语/客语的项取最长标签，供类型推断；`entities_payload()`（:156）对每个拆分实体调 `resolve_entity(p, g["label"])`，先 `is_media_source()` 过滤新闻来源名（防 "Al Jazeera→US" 误判），产出 `{"entity_id", "entity_name", "entity_type", "role"}`。
2. **Canonicalizer `resolve_entity(name, gliner_type)`**（`canonicalizer.py:283`）优先级：
   - 先剥 `EXCHANGE:TICKER` 前缀（`NASDAQ:NVDA→NVDA`）。
   - **① KB V1 优先**：`knowledge_base/loader.resolve(lookup)` 命中 → 返回 `(entity_id, canonical_name, type)`。`loader._build_index`（`knowledge_base/loader.py:87`）规则：**`entity_alias.yaml`（curated，含转喻/缩写/中文）先建索引 → 覆盖 section YAML 自动条目**；每条映射 `别名小写 → (cid, canon, type)`。例：`特朗普→('PERS_TRUMP','Trump','Person')`、`中国→('CTRY_CHN','China','Country')`、`英伟达→('COMP_NVIDIA','NVIDIA','Company')`。
   - **② 回退本地本体**：`_load_aliases()` 读 `entity_weights.json` 建 `_ALIAS_MAP`（取最长的英文名当 canonical）；然后 `CITY_TO_COUNTRY`（33 城→国家：Beijing→China）；最后 `_infer_type()`（政府/军队/人物头衔/国名关键词）定类型。
   - **③ ID 生成**：按类型前缀 `_ID_PREFIX`（Country→CTRY/Person→PERS/Company→COMP/…）拼 `前缀_大写去空格下划线`。**未命中 KB 的实体也是规范生成 ID**（如 `ENT_XXX`/`COMP_XXX`），只是非 KB 权威 ID。
3. **OntologyValidator**（`ontology_validator.py`，G7）：`validate_entities()` 校验 `entity_id` 前缀↔`entity_type` 一致性（`COMP_→Company/PERS_→Person`…）+ 关系 REL_ 前缀白名单；输出 `validation` 诊断字段**不阻断**聚合。⚠️ 这里是**关系库 relations.yaml 在 Pipeline 中的唯一用处**——仅校验 REL_ 前缀，不读取具体关系数据。
4. **产出/落点**：`canonicalize()` 输出 `{action, time, location, entities:[{name,id,type,role}], validation}` → Fact payload → 推送 `/internal/facts/batch` → 云端 **`fact_entity` 表存 KB V1 稳定 ID**。

### 环节 3 — 事件聚合（aggregator.py）｜ 用文章实体清单 + GLiNER + Fact 实体；**不用关系库**

**用途**：把多篇文章聚成事件，subject/object/actors/related_entities 全部是实体运算。实体知识库在这里以"归一化函数"形式间接参与。

**具体逻辑**（`aggregator.py`）：
- **实体规范化 `_canonicalize(name)`**（:85）：内部调 `canonicalizer.resolve_entity`，命中返回 canonical（英伟达→NVIDIA），KB 统一归一，支持中英聚合。
- **实体 IDF `_compute_entity_idf(articles)`**（:289）：统计每篇文章 `entities{companies,persons,countries}` 的规范化名在全集/主题内的频率 → `global_idf`/`topic_idf`/`hub_entities`（频率占比 > `HUB_RATIO` 且 ≥5 次的"hub 实体"）。
- **主体/客体权重 `_entity_weight(name)`**（:326）：`type_w(类型权重) × (0.2 + 0.4×global_idf + 0.4×topic_idf)`。
- **指纹构建 `build_fingerprint`**（:387）：
  - subject：对文章 entities 的 company/person 名算权重 → hub 实体 ×0.3 降权、**标题出现实体 ×2 显著性提升** → 权重最高者且 ≥ `MIN_SUBJECT_WEIGHT` 才当 subject。
  - object：country/company 候选（排除 subject）取权重最高。
  - participants = `_extract_participants`（entities countries + `COUNTRIES` 词表正则）。
  - `_known_entity_types`（:757）从文章 entities 分组构建 `名→类型`，供事件 subject/object 打类型。
- **Fused 融合 `build_fused_fingerprint`**（:682，生产默认）：每字段取最优源——subject/object ← fact（且 `_name_in_text` 校验实体确实在文章文本，**中文 CJK 直接信任**）、action/event_type ← fact 否则 legacy、country ← legacy 优先、participants 并集、anchor 重算。
- **合并打分 `fingerprint_score`**（:484）：location/主题硬约束 → anchor 完全一致=100 → action+25 / **subject 完全同实体+25（KB 中英归一后支持跨语言）** / object 稀有度加权 10~30 / topic+10 / event_type+10 / participants 重叠加分。
- **事件实体 ID `_entity_name_to_id`**（:1195）：**本地生成方案**（`前缀_{大写清理名}`，前缀取 `_known_entity_types`）——**不查 KB**，与 Fact 层的 KB V1 ID 是两套体系。写入 `event.subject.entity_id / object.entity_id / related_entities[].entity_id`。
- **actors** `_infer_actor_roles`（:583）：entity_refs 前 5 个 → 第 1 个 Initiator、等于 obj 的 Target、其余 Participant → `{entity, type, role}`。
- **本地注册** `upsert_entity`（:1168）：把相关实体写进 SQLite `entity_registry`（57 条），供本地 Dossier/画像。
- **产出**：事件 Dossier（subject/object/action/actors/related_entities）→ 推送。

### 环节 4 — 推送/云端入库（pusher.py → internal.py）｜ 实体名 + ID 落库

- 事件：`_event_to_push_format`（`pusher.py:144`）发送 `subject/object`（含 name+entity_id）、`actors`、`related_entities` 原始结构 → `internal.py` 写 `events` 表 `subject_name/object_name/actors(JSONB {entity,type,role})`（**云端事件只存实体名，不存事件级 entity_id**）。
- Fact：`fact_pipeline.py:274` 推 `/internal/facts/batch` → `fact_entity` 存 **entity_id（KB V1）+ entity_name + entity_type + role**。

### 环节 5 — 知识加工/DB 关系库回填（backfill_entity_model.py / sync_kb_to_db.py / fill_entity_kb.py）｜ 实体与关系表在这里生成

**用途**：把"流程实体"与"KB 实体"合并进云端 `entities/entity_alias/entity_relationship/event_relations` 四表——**这是配置中心"实体关系"Tab 的数据来源，也是流程实体与关系库交汇点**。

| 脚本 | 逻辑 | 产出 |
|---|---|---|
| `backfill_entity_model.py`（容器内跑，幂等） | ① `collect_kb_entities`（KB entity-network 149 实体）+ `collect_event_entities`（events 表 subject/object/actors 派生 **35** 实体）→ 用 `CANON_NAME` 硬编码 canonical（Donald Trump→Trump）合并去重 → upsert `entities`；② `entity_alias` 重建（KB aliases + `CANON_ALIASES` 中英别名表）；③ `entity_relationship` 重建（**KB associations + in_segment**，223 条）；④ `event_relations` 重建（**同 subject 事件按 first_seen 时间序 → precedes 边**，28 条） | 云端 4 张实体/关系表 |
| `sync_kb_to_db.py`（容器内跑） | 把 `knowledge_base/*.yaml` 的 **KB V1 全量**（~18800 人物/~8300 公司/249 国）upsert 进 `entities` + 别名进 `entity_alias`（27176 实体/41110 别名） | entities/entity_alias 补齐 |
| `fill_entity_kb.py`（本地跑） | 把事件派生但 KB 缺失的实体补进 `entity-network.json`（如 Anthropic/SpaceX→US companies）+ 类型修正（Buffett→Person）+ 重新生成 `data_entity_kb.py` | entity-network.json 反向吸收流程实体 |

### 环节 6 — 展示（entities 画像 + stories）｜ 合并 KB + DB + 事件

- **实体列表** `/api/v1/entities`：对 `events` 表 subject/object/actors 去重计数排序（top 100），用 `_find_entity`（entity-network KB，含别名）补 country/category/type。
- **实体画像** `/api/v1/entities/{name}`（`routes/entities.py:272`）三层合并：
  1. KB 查 `_find_entity`（entity-network.json：国家/类别/角色）→ 基础信息；
  2. DB 查 `Entity`（按原名→别名反查 canonical，修 Trump/Donald Trump 不一致）→ aliases + **entity_relationship in/out 方向**（`db_relationships`，即画像页"关系网络"）；
  3. `_entity_filter` 匹配 `events.subject_name/object_name/actors` → 相关事件/event_count/article_count；`related_entities`（同国家 companies/leaders）。
  - 画像页前端（`entities/[name]/page.tsx`）渲染：关系网络（DB entity_relationship）+ 关联网络（KB associations）+ 相关事件 + 同国家实体。
- **Story 派生** `stories.py`（`derive_dimension` :69）：按 `STORY_DIMENSIONS`（subject→subject_name / action→action_type / object→object_name / location→location_country）分组事件（各 ≥2 事件成故事），`story_id` 前缀 `STORY_/ACT_/OBJ_/LOC_`，重建幂等 + 并发锁。**subject 维度即实体维度**（STORY_Trump=特朗普相关事件时间线）。

### 环节 7 — 配置中心（实体管理 / 实体关系 Tab）｜ 管理入口（见 §二）

**产出落点总结**：
| 环节 | 用到的实体/关系库 | 实体落点 |
|---|---|---|
| 0 采集 | 无 | — |
| 1 评分 | `entity_weights.json` | `articles.entities`（清单）+ 评分 entity 维 |
| 2 Fact | **KB V1**（knowledge_base/loader）| `fact_entity`（KB V1 稳定 ID）|
| 3 聚合 | 文章实体清单 + GLiNER + Fact 实体（经 `_canonicalize`）| 事件 subject/object/actors/related_entities（**本地 ID**）+ SQLite `entity_registry` |
| 4 入库 | — | `events`（实体名）、`fact_entity`（KB ID）|
| 5 回填 | entity-network associations + events + KB V1 | `entities/entity_alias/entity_relationship/event_relations` |
| 6 展示 | entity-network + DB 关系表 | 画像页 / Story（subject 维度）|
| 7 配置中心 | entity-network.json + DB 4 表 | UI 编辑入口（见 §二）|

---

## 四、关联性矩阵（打通点 vs 断裂点）

### ✅ 已打通的关联（配置中心 ←→ 业务流程实体）

1. **事件派生实体 → DB entities**: Pipeline 事件的 subject/object/actors 名 → `events` 表 → `backfill_entity_model.py` 的 `collect_event_entities()` 提取 35 个事件派生实体，与 KB 149 实体合并 upsert 进 `entities` 表（云端 **27,176 实体 / 41,110 别名**）。"实体关系"Tab 里能看到真实流程实体。
2. **KB associations → entity_relationship**: 实体管理 Tab 编辑的 associations → 回填 `entity_relationship`（223 条）→ 画像页"关系网络"。配置中心→展示闭环。
3. **同 subject 事件 → event_relations**: backfill 按 `subject_name` 分组、按 first_seen 时间序派生 `precedes` 边（28 条）→ 实体关系 Tab + `/events/{id}/relations`。
4. **fill_entity_kb.py 反向补齐**: 事件派生的新实体可一键并入 entity-network.json（`fill_entity_kb.py:17 KB_ADD`，如 Anthropic/SpaceX→US companies），再经 UI 校验/保存/同步 Git。**这是事件→KB 的唯一回流口，但仍是手动触发、只补展示库。**

### ❌ 断裂点（结构性风险）

1. **两套知识库不互通**: Pipeline 实体归一只认 `knowledge_base/*.yaml`；配置中心实体管理只写 `entity-network.json`。grep 证实 entity-network 仅被后端 `entities.py` 引用，Pipeline 四模块（canonicalizer/scorer/aggregator/ontology_validator）零引用。**配置中心加实体 → 不影响新事件/Fact 的实体解析。**
2. **事件/Fact 实体 ID 双轨**: 见 §三⑤，云端无法用 ID 跨表关联实体。
3. **评分实体清单与 KB 无同步**: entity_weights.json 手改、非 UI 管理，`generate_kb.py` 只从它迁一次种子，之后各自漂移。
4. **KB V1 的维护通道**: `knowledge-base.md` 明确种子生成/扩量/补别名走 `scripts/knowledge_base/*.py`（import_seed/import_wikidata_people/generate_kb），**配置中心 UI 管不到**。
5. **同名不同 canonical**: backfill 用 `CANON_NAME` 硬编码映射（`backfill_entity_model.py:29-54`，如 Donald Trump→Trump）做归一去重；entity_weights 与 KB V1 的 canonical 又可能不同——多处手工维护 canonical 表，极易不一致（已出现 Trump/Donald Trump 分裂、v1.2 生成丢日本领导人的坑）。

---

## 五、实体数据源全景与管理方式

| 实体库 | 规模（实测） | 用途 | 管理入口 | 配置中心 UI 能改？ | 影响 Pipeline 抽取？ |
|---|---|---|---|---|---|
| `knowledge_base/*.yaml` (KB V1) | 249国/~8300公司/~18800人物/81动作/106关系/29事件类型 + 85别名 | Fact 归一 / 本体验证 / 中英统一 | AI 工作流(wiki+git+generate/import 脚本) | ❌ | ✅ **是（唯一源头）** |
| `config/entity_weights.json` | 340公司+84人物+34国+101机构 | 评分实体维度 | 手改文件 | ❌ | ✅ 是（评分） |
| `references/entity-network.json` + `data_entity_kb.py` | 13国深度关系 + 8组织 + 26关联 | 画像元数据/关系网络 | **配置中心"实体管理"Tab** | ✅ | ❌ 否（仅画像/回填） |
| PG `entities/entity_alias/entity_relationship/event_relations` | 27176/41110/223/83 | 画像关系/事件关系 | **配置中心"实体关系"Tab** + backfill | ✅ | ❌ 否（读侧） |
| 本地 SQLite `entity_registry` | 57 | 事件聚合过程登记 | 自动 | ❌ | 中间态 |

```
[KB V1 YAML] ──canonicalizer──→ Fact/事件 实体名+ID ──internal──→ PG events/fact_entity
    │                                                              │
    │  sync_kb_to_db.py (一键)                                       │ backfill (事件派生 35)
    └──────────────→ PG entities/entity_alias ←─────────────────────┘
                                 ↑
[entity-network.json] ──实体管理Tab编辑──→ 校验/保存/热生效 → backfill → entity_relationship
    │                                     └─ git-sync ──→ search-engine-v2 仓库
    └───────── fill_entity_kb.py (事件派生实体并入, 手动) ─────────────┘
```

---

## 六、升级方案（供决策）

> 目标: 让"配置中心改实体"与"Pipeline 实体抽取决策"形成闭环，或消除 ID/canonical 双轨。按成本从低到高列出，可独立或组合实施。

### 方案 A：entity-network ↔ knowledge_base YAML 双向同步（打通回流通道）

**目标**: 配置中心"实体管理"Tab 保存时，同时把实体同步进 Pipeline 用的 `knowledge_base/companies.yaml/people.yaml`，使 UI 改实体 → 下次 Pipeline 实体归一生效。

- **改动点**: `routes/entities.py:admin_save_entities` 保存后追加一步——把 `entity-network.json` 的 leaders/business/companies 实体 upsert 进 `knowledge_base/people.yaml/companies.yaml`（带 aliases），再调 `knowledge_base/generate_kb.py` 重建 loader 索引（或增量重建）。
- **同步面**: 新实体 → YAML section；已有实体只改 country/type 等元数据 → 不覆盖 KB V1 已有的 ~18800 人物/~8300 公司，仅 upsert 交集。
- **生效**: 下次 Pipeline 运行（loader 懒加载；需同步 profile 副本 `knowledge_base/` + `canonicalizer.py` 到生产目录）。
- **风险**: loader 索引 30K 条重建 ~8.7s；需处理 UI 保存的 name 与 KB canonical 不一致（如 "Donald Trump" vs "Trump"）。
- **工作量**: 中（后端单文件 + 生成脚本调用 + 回归）。

### 方案 B：统一事件/Fact 实体 ID（消除双轨）

**目标**: 让 `aggregator._entity_name_to_id` 改走 `knowledge_base/loader.resolve()`（与 canonicalizer 一致），使事件 subject/object/actors 的 entity_id 与 fact_entity 的 entity_id 同源同规。

- **改动点**: `aggregator.py:1195` 替换 `_entity_name_to_id` 实现——先 `loader.resolve()`，未命中再回退现有本地生成逻辑。
- **收益**: 云端可按 entity_id 跨 events/fact_entity 关联；画像页"相关事件"可从 name 匹配升级为 ID 匹配；跨语言聚合天然增强。
- **影响面**: 需要**重聚合全量事件**（`reaggregate_all.py`）以刷新已入库事件的 entity_id；`_known_entity_types` 前缀推断可保留为兜底。
- **风险**: 回填/归一逻辑、Story subject 维度依赖 subject_name 不受影响（ID 与 name 并存）。
- **工作量**: 小-中（单函数替换 + 全量重聚合回归）。

### 方案 C：收敛 canonical 表（消除三处手工维护漂移）

**目标**: 把 backfill 的 `CANON_NAME`（`backfill_entity_model.py:29-54`）、`entity_weights.json` 的别名、KB V1 的 canonical 统一到单一权威源。

- **做法**: 以 KB V1 `entity_alias.yaml`（curated，含中英/简称）为唯一权威；`generate_kb.py` 从它生成 canonical 对照；backfill 的 CANON_NAME 改为运行时读 `loader.resolve()` 而非硬编码；entity_weights 保留为评分权重（仅权重值，不含别名语义）。
- **收益**: 消除三处各自漂移的 canonical 表，Trump/Donald Trump 分裂、v1.2 丢领导人这类坑根治。
- **工作量**: 中（三个脚本改造 + 全量回归）。

---

## 七、决策点

| 决策项 | 选项 | 影响 |
|---|---|---|
| 是否打通配置中心→Pipeline 回流 | A / 暂不（保持现状） | A 使 UI 改实体即影响抽取；现状仅影响画像 |
| 是否统一事件/Fact 实体 ID | B / 暂不 | B 解锁 ID 级跨表关联；需全量重聚合 |
| 是否收敛 canonical 权威源 | C / 暂不 | C 根治 canonical 漂移；改造 3 脚本 |
| 实施顺序 | A→B→C / B→A→C / 单项 | 若做多选，建议 A→B→C |

> **推荐**: 若以"实体库可持续运维"为优先，选 **A + C**（打通回流 + 根治漂移）；若以"实体图谱精度"为优先，选 **B**（统一 ID 后再做 A 更顺）。

---

## 八、决策后待办（选定后执行，遵循 doc-first）

- [ ] 选定方案（更新本文档 §六 勾选 + 状态改 🟢 实施中）
- [ ] 按方案更新对应子文档（knowledge-base.md / entity-kb.md / backend.md / database.md）
- [ ] 写代码 + `python demo.py` 回归 + 全量重聚合（如涉及）
- [ ] git 提交（search-engine-v2，文档+代码同 commit）
- [ ] VPS 部署 + curl 验证（实体画像 / 新事件实体 ID）
