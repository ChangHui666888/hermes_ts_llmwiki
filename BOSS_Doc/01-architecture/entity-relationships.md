# 实体与实体关系 — 入库数据文档

> 版本: v0.3 · 2026-08-12 · 依据: `references/data-model-upgrade-plan.md`（Schema V0.1）+ VPS PG 实查
> 说明: 本文档记录**已入库（云端 PostgreSQL）**的实体 / 实体别名 / 实体关系 / 事件关系，及本地 SQLite 中间态。
> ⚠️ **注意 ID 双轨**：云端 `entities.id` 是 PG 自增整数；`fact_entity.entity_id` 存 **KB V1 字符串 ID**（`PERS_TRUMP`），两者不同源，跨表只能按 name 匹配（ISS-002）。

---

## 1. Schema（实体相关表全量）

| 表 | 字段 | 说明 |
|----|------|------|
| **entities** | id(PK), name(NOT NULL), type, country, importance(default 50), aliases(JSONB), confidence, first_seen, last_seen, created_at | 实体主数据（KB V1 全量 sync + 事件派生合并）。物理列另有 `metadata` JSONB（Declarative 保留名不映射 ORM，无人读） |
| **entity_alias** | id(PK), entity_id(FK→entities.id), alias(NOT NULL), lang(default 'en'), created_at；UNIQUE(entity_id, alias) | 结构化别名（中英/简称） |
| **entity_relationship** | id(PK), from_entity_id(FK), to_entity_id(FK), relation_type(NOT NULL), confidence, description, evidence_count, first_seen, last_seen, created_at | 实体-实体关系（backfill 从 KB V1 派生） |
| **event_relations** | id(PK), parent_event_id, child_event_id, relation_type, confidence, start_time, end_time, evidence_count, created_at | 事件-事件关系（同 subject 时间序派生 `precedes`） |
| **event_entity** | event_id(FK→events.id), entity_id(FK→entities.id) 复合 PK | 事件-实体 M:N（指向整数 id） |
| **article_entity** | article_id(FK), entity_id(FK), relevance_score | 文章-实体 M:N（指向整数 id） |
| **fact_entity** | fact_id(FK→fact.id), entity_id(VARCHAR, **KB 字符串 ID**), entity_name, entity_type, role；UNIQUE(fact_id, entity_id, role) | Fact 参与者（Role 模型） |

迁移: `migrations/versions/0001_fact_tables.py`（fact/fact_entity）· `0002_entity_upgrade.py`（entities 补 country/importance/first_seen/last_seen/confidence + 新建 entity_alias/entity_relationship + event_relations 扩展 start/end_time/evidence_count）· `0003_story.py` · `0004_story_dimension.py`。

---

## 2. 云端数据量（2026-08-12 VPS 实查）

| 表 | 行数 | 说明 |
|----|:----:|------|
| entities | **27,366** | Person 18,792 / Company 8,206 / Country 247 / Industry 42 / Location 39 / Government 17 / International Org 7 / Central Bank 5 / Military 3 + 少量杂类（KB V1 sync_kb_to_db 全量导入 + backfill 事件派生） |
| entity_alias | **41,089** | 全部 `lang='en'`（KB V1 中英别名均标 en，`lang` 未区分 zh） |
| entity_relationship | **223** | **in_segment 218**（公司→细分赛道）/ subsidiary_of 3 / parent_of 1 / in_industry 1 |
| event_relations | **83** | 全部 `precedes`（同 subject 事件时间序） |
| fact_entity | **25,512** | Fact 参与者（KB 稳定 ID） |
| event_entity / article_entity | (空/增长) | 关联表（当前未填充） |

> ⚠️ **entity_relationship 结构变化（2026-08-09）**：backfill 改读 KB V1 后，关系从"配置中心 associations 的 12 类"变为 **KB V1 公司→细分赛道 `in_segment` 为主**。旧 12 类（appoints/works_with/partners/competes…）实例不再回填，`/admin/entity-relations/types` 下拉仍提供 KB 108 种 + 旧 12 种。

---

## 3. 实体类型分布与画像（2026-08-12 实查）

`entities` 表 = **KB V1 全量**（sync_kb_to_db 导入） + **事件派生实体**（backfill `collect_event_entities`，~35 个）。KB V1 规模见 [knowledge-base.md](knowledge-base.md)。

### 3.1 类型分布（top）

| 类型 | 数量 |
|------|:----:|
| Person | 18,792 |
| Company | 8,206 |
| Country | 247 |
| Industry（含 IND_SUB_ 细分赛道） | 42 |
| Location | 39 |
| Government | 17 |
| International Org | 7 |
| Central Bank | 5 |
| Military | 3 |

### 3.2 事件级实体（events 表 SAO，非 entities 表）

`events.subject_type` 分布（500 事件）: **Other 303 / Company 105 / Person 91**。事件 subject/object 只存**实体名**（`subject_name/object_name`），不存 entity_id——这是事件层与 Fact 层 ID 双轨的直接体现。

### 3.3 画像合并（/api/v1/entities/{name}）

三层：① KB entity-network（`_find_entity`，国家/类别/角色）→ ② DB entities 反查 canonical + entity_relationship in/out → ③ events subject/object/actors 匹配相关事件。

---

## 4. 实体-实体关系（223 条，backfill 从 KB V1 派生）

| 关系类型 | 数量 | 来源 |
|---------|:----:|------|
| in_segment | 218 | `company.sub_segments` → 细分赛道（NVIDIA→GPU/AI芯片/出口管制…） |
| subsidiary_of | 3 | `parent` 字段 |
| parent_of | 1 | 子公司反向 |
| in_industry | 1 | `industry` 字段 |

> 配置中心 associations（entity-network.json）的 27 条（appoints/competes/conflicts…）**不再**由 backfill 写入 `entity_relationship`；如需要需改回 backfill 逻辑或手动 CRUD（`POST /admin/entity-relations`）。

---

## 5. 事件-事件关系（83 条，同 subject 时间序派生）

- 关系类型: 全部 `precedes`（事件 A 先于事件 B，同主体时间链，保守无因果断言）
- 来源: `backfill_entity_model.py` 从 `events` 表按 `subject_name` 分组、按 `first_seen` 排序派生
- 端点: `GET /api/v1/events/{id}/relations` → `{total, relations:[{event_id, direction, relation_type, start_time, end_time}]}`

---

## 6. 数据流与维护

```
knowledge_base/*.yaml (KB V1, 权威源)
   │ 1) sync_kb_to_db.py (backend 容器内) — KB V1 全量 → entities/entity_alias
   │ 2) backfill_entity_model.py (backend 容器内) — KB V1 关联 + 事件派生 → entity_relationship/event_relations + entities 事件派生
   ▼
云端 PG: entities(27,366) + entity_alias(41,089) + entity_relationship(223) + event_relations(83)
   │ 3) API: /api/v1/entities/{name} (aliases+relationships) · /api/v1/events/{id}/relations
   ▼
前端实体画像 / 事件 Dossier

（entity-network.json 仅服务展示层画像，不走 sync_kb_to_db；见 entity-kb.md）
```

**重跑回填**（实体/关系变化后同步 DB，幂等）:
```bash
docker compose exec backend python /host/scripts/news-platform-v8/backfill_entity_model.py
docker compose exec backend python /host/scripts/news-platform-v8/sync_kb_to_db.py
```

**补齐展示 KB**（事件派生新实体并入 entity-network）:
```bash
python scripts/news-platform-v8/fill_entity_kb.py
```

---

## 7. 本地 SQLite 中间态（entity_registry）

| 表 | 行数 | 说明 |
|----|:----:|------|
| entity_registry | **94** | 聚合过程登记（Company 46 / Person 25 / Country 23），`entity_id` 为 KB 风格字符串 ID |

> `entity_registry` 由 aggregator `_register_event_entities` 写入（`upsert_entity`，上限 10 条/事件），本地画像用；**不是云端 entities 的来源**（云端由 sync_kb_to_db + backfill 维护）。

---

## 8. 已知缺口 / 关联分析（2026-08-07 起持续）

- **关系库在生产 Pipeline 仍几乎不使用**：`relations.yaml`（108 种）仅被 `ontology_validator.py` 做 REL_ 前缀白名单（不读关系内容）；`entity_relationship` 的 in_segment 关系是**展示层**数据（画像/配置中心），无事件/fact 生成逻辑消费。
- **配置中心↔Pipeline 回流断裂**：实体管理 Tab 编辑的 `entity-network.json` 不影响 Pipeline 抽取归一（源头是 `knowledge_base/*.yaml`）；DB 实体表为读侧产物。
- **事件/Fact 实体 ID 双轨**：事件 subject/object 不存 entity_id；fact_entity 存 KB ID；entities.id 是 PG 整数。云端无法按 ID 跨 events↔fact_entity 关联。
- 完整分析与升级方案（A 双向同步 / B 统一 ID / C 收敛 canonical，**待决策**）：见 [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)。
