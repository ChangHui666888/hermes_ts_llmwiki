# 实体管理链路分析 + 升级方案 — 配置中心 ↔ 业务流程

> 版本: v1.0 · 2026-08-07 · **状态: 🟡 待决策**
> 定位: 梳理"配置中心实体管理/实体关系"与"项目业务流程实际使用的实体"之间的关联，并提出升级方案供决策。
> 依据: 代码逐行核实（`search-engine-v2/scripts/news-platform-v8/` + `scripts/news_intel/` + `knowledge_base/`）+ 现有 Wiki 文档 + 记忆。
> 相关文档: [knowledge-base.md](knowledge-base.md) · [entity-kb.md](entity-kb.md) · [entity-relationships.md](entity-relationships.md) · [business-process.md](business-process.md) · [database.md](database.md)

---

## 一、核心结论（先给答案）

**配置中心"实体管理/实体关系"管理的是"展示层画像库 + DB 关系表"；而 Pipeline 抽取决策真正依赖的是另一套 `knowledge_base/*.yaml`（KB V1）。两者之间存在单向数据流（KB→DB→画像），但没有"配置中心改实体→影响线上抽取"的回流通道。**

- **实体管理 Tab** 管理 `entity-network.json`（静态画像 KB，13 国深度关系）——下游是实体画像页与 DB 回填，**不影响 Pipeline 归一**。
- **实体关系 Tab** 管理 PG 四张表（`entities/entity_alias/entity_relationship/event_relations`）——其中**实体名确实来自业务流程**（事件 subject/object/actors 派生），是流程实体真实回流的一环。
- **Pipeline 实体归一**（Fact 抽取、本体验证）用 `knowledge_base/*.yaml`（KB V1，249 国/8038 公司/18790 人物）——由 AI 工作流(wiki+git)维护，**配置中心 UI 够不到**。

三套实体数据源互相独立，靠 `backfill_entity_model.py` / `sync_kb_to_db.py` / `fill_entity_kb.py` 三个脚本单向桥接。

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

## 三、项目业务流程中实体的完整使用链路（7 个环节）

```
RSS采集 → 评分 → Fact抽取 → 事件聚合 → 推送 → PG → FastAPI → Next.js
              │        │        │        │                │
           ①权重   ②KB V1归一  ③本地ID  ④facts/events   ⑥画像/⑦Story
```

| # | 环节 | 模块 | 实体如何被使用 |
|---|------|------|----------------|
| ① | 评分 | `scorer.py:106-186` | `entity_weights.json`（34国/79人物/88公司权重）查表打"实体重要性"分（满分20）。**与 KB V1 / entity-network 都不同，是第三套清单**，静态文件 |
| ② | Fact 抽取归一 | `canonicalizer.py:283 resolve_entity` | **唯一真正查知识库处**：优先 `knowledge_base/loader.resolve()`（中英别名→稳定 ID：`特朗普→PERS_TRUMP`、`中国→CTRY_CHN`、`英伟达→COMP_NVIDIA`），未命中回退 entity_weights + 本地本体 + 城市→国家 33 城 |
| ③ | 本体验证 | `ontology_validator.py` (G7) | 三层归一第三层：Entity ID 前缀↔类型一致性（COMP_→Company…）+ REL_ 白名单，输出 validation 诊断不阻断 |
| ④ | 事件聚合 | `aggregator.py:1049` | subject/object/actors 的 entity_id 用**本地生成** `_entity_name_to_id`（`aggregator.py:1195`，按 `_known_entity_types` 拼前缀，**不查 KB**）；`upsert_entity` 写本地 SQLite `entity_registry`（57 条） |
| ⑤ | 云端入库 | `pusher.py:160-182` → `internal.py` | Event 存 `subject_name/object_name/actors(JSONB,{entity,type,role})`；facts 推 `/internal/facts/batch` → `fact_entity` 表存 **KB V1 ID** |
| ⑥ | 实体画像 | `routes/entities.py` + 前端 `/entities` | 列表=事件派生实体按事件数排序+KB enrich；画像页=KB(entity-network)+DB(entities/alias/relationship)+相关事件 合并 |
| ⑦ | Story 打包 | `stories.py` / `backfill` | 按 subject/action/object/location 四维分组事件 → `STORY_(subject)` 等前缀 |

**关键发现**: Fact 层实体用 **KB V1 稳定 ID**（PERS_TRUMP），事件层实体用 **aggregator 本地 ID**（COMP_NVIDIA 式）——**同一实体在 fact 与 event 里是两个 ID 体系**，云端无法靠 entity_id 关联，只能按 name 匹配。

---

## 四、关联性矩阵（打通点 vs 断裂点）

### ✅ 已打通的关联（配置中心 ←→ 业务流程实体）

1. **事件派生实体 → DB entities**: Pipeline 事件的 subject/object/actors 名 → `events` 表 → `backfill_entity_model.py` 的 `collect_event_entities()` 提取 35 个事件派生实体，与 KB 149 实体合并 upsert 进 `entities` 表（云端 **27,176 实体 / 41,110 别名**）。"实体关系"Tab 里能看到真实流程实体。
2. **KB associations → entity_relationship**: 实体管理 Tab 编辑的 associations → 回填 `entity_relationship`（26 条）→ 画像页"关系网络"。配置中心→展示闭环。
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
| `knowledge_base/*.yaml` (KB V1) | 249国/8038公司/18790人物/81动作/106关系/29事件类型 + 85别名 | Fact 归一 / 本体验证 / 中英统一 | AI 工作流(wiki+git+generate/import 脚本) | ❌ | ✅ **是（唯一源头）** |
| `config/entity_weights.json` | 34国+79人物+88公司 | 评分实体维度 | 手改文件 | ❌ | ✅ 是（评分） |
| `references/entity-network.json` + `data_entity_kb.py` | 13国深度关系 + 8组织 + 26关联 | 画像元数据/关系网络 | **配置中心"实体管理"Tab** | ✅ | ❌ 否（仅画像/回填） |
| PG `entities/entity_alias/entity_relationship/event_relations` | 27176/41110/26/28 | 画像关系/事件关系 | **配置中心"实体关系"Tab** + backfill | ✅ | ❌ 否（读侧） |
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
- **同步面**: 新实体 → YAML section；已有实体只改 country/type 等元数据 → 不覆盖 KB V1 已有的 18790 人物/8038 公司，仅 upsert 交集。
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
