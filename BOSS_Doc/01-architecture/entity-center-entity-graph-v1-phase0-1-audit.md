# Entity Graph V1 — PHASE 0 / PHASE 1 AUDIT REPORT

> **审计日期**: 2026-08-16 · **阶段**: PHASE 0（环境检查）+ PHASE 1（现有 Schema 读取）
> **状态**: ✅ 审计完成 · ✅ **后续开发已完成**（2026-08-17, commit `f5105eb`，见 [实现报告](entity-center-entity-graph-v1-report.md)）
> **依据**: 实际代码 + 生产数据库实测（VPS compose `news-platform-v8-entity-center-postgres-1` :5432）

> ## ⚡ 审计后开发裁决（已确认并执行）
> - **CONFLICT-1**（entity_relations）→ 复用 `entity_relationships`，未新建 ✓
> - **CONFLICT-2**（relation_entity_type_rules）→ 复用 `from/to_entity_type_ids` JSONB + 应用层校验（`validate_entity_relation`），未建表 ✓
> - **CONFLICT-3**（entity_relation_evidence）→ 复用 `relation_evidence`，未新建 ✓
> - **动作缺口**（INVESTS/PARTNERS_WITH）→ 不新增，前端标签映射 ✓
> - 仅新增 `action_entity_role_rules`（migration 0003）+ Graph 查询 API + 46 种子关系

---

## PHASE 0 — 环境检查

### 0.1 项目拓扑

| 项 | 实际值 |
|----|--------|
| 项目根目录 | `C:\Users\ChangHui\.hermes-web-ui\coding-agent\workspace\default\global\entity_center`（独立 git 仓库） |
| Entity Center 代码 | 该仓库 `app/`（models/services/api）+ `scripts/` + `migrations/` + `ontology/` |
| Web 集成代码 | `search-engine-v2/scripts/news-platform-v8/frontend`（Next.js 管理页）+ nginx 反代 |
| PostgreSQL 连接 | 本地 dev: `postgresql+asyncpg://entity_center:entity_center_dev@100.107.117.23:5433/entity_center`（.env） |
| 生产 DB | VPS compose 内 `news-platform-v8-entity-center-postgres-1` :5432（Tailscale 内网） |
| 数据库名 | dev+prod 均 `entity_center`；测试库 `entity_center_test`（dev 容器 5433） |
| Schema | `entity_center`（独立 schema） |
| Migration 工具 | **Alembic**（版本 0002） |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| 测试框架 | **pytest**（37 项，asyncio，conftest 隔离测试库） |
| 启动方式 | compose（`docker compose up -d --build`）+ nginx `/entity-center/` 路由 |

### 0.2 端口（不可占用）

| 端口 | 服务 | 说明 |
|:---:|---|---|
| 80 | nginx | Web 入口 |
| 5432 | prod entity-center-postgres | compose，方案B 起暴露 Tailscale |
| 5433 | **dev** entity-center-postgres | 独立容器，本地开发/测试用 |
| 3000 | frontend 容器内 | Next.js（不暴露宿主） |
| 8000 | backend/entity-center-backend 容器内 | FastAPI（不暴露宿主） |

> ⚠️ **5432 与 5433 已被 entity-center 占用**，新增服务不得使用。无其他项目占用冲突。

### 0.3 现有代码层（已确认存在）

Model（`app/models/`）· Service（`app/services/` 9 个）· API（`app/api/` 5 router + 32 端点）· Validator（`app/services/upsert.py` 审批校验）· Repository 模式（service 层内联）。

---

## PHASE 1 — 现有 Schema 读取

### 1.1 表清单（21 表 + 1 视图，2026-08-16 生产实测）

核心冻结表（本次不得修改）：
`entity_types`(16) · `entity_subtypes`(27) · `entities`(759) · `entity_aliases`(2803) · `entity_identifiers`(220)
`relation_types`(17) · `actions`(139) · `relation_action_mappings`(137)

关系/观测/治理表：
`entity_relationships`(23 active) · `relation_observations`(23) · `relation_evidence`(23) · `relation_candidates`(23)
`relation_observation_stats` · `relation_multihop_rules`(仅建表) · `sync_outbox`(4905) · `config_versions`(4) · `data_revisions` · `audit_log` · `ontology_versions`(229)
视图 `v_symmetric_relations`

### 1.2 实体数据量

```
entities 759 · aliases 2803 · identifiers 220 · active_rels 23 · candidates 23 · observations 23
```

### 1.3 entity_types（16 种）

`PERSON COMPANY GOVERNMENT COUNTRY ORGANIZATION INTERNATIONAL_ORGANIZATION FINANCIAL_INSTITUTION LOCATION INDUSTRY SEGMENT TECHNOLOGY PRODUCT COMMODITY CURRENCY MILITARY_ORGANIZATION MEDIA`

### 1.4 entity_subtypes（27 种，样例）

`public_company private_company state_owned_company subsidiary holding_company · politician executive founder investor central_banker military_leader · national_government local_government ministry agency regulator · commercial_bank investment_bank central_bank asset_manager exchange · ai semiconductor chip_architecture manufacturing_process network optical`

### 1.5 relation_types（17 种）

`MILITARY_CONFLICT TERRITORIAL_DISPUTE ECONOMIC_SANCTION TRADE_RESTRICTION POLITICAL_HOSTILITY REGULATORY_PENALTY CORPORATE_CONTROL MAJOR_INVESTMENT STRATEGIC_PARTNERSHIP SUPPLY_CHAIN FINANCIAL_RELATION PERSONNEL_MOVEMENT MARKET_COMPETITION TECHNOLOGY_RELATION INDUSTRY_AFFILIATION ORGANIZATION_MEMBER GENERAL_RELATION`

**每个均含 `from_entity_type_ids` / `to_entity_type_ids`（JSONB，种子全填）— 但当前无校验逻辑使用（Gap-1）**

### 1.6 actions（139 种）— 方案引用动作核对

方案引用的 11 个动作，**9 个存在**：

✅ `ACQUIRES APPOINTS EXPORT_CONTROL SANCTIONS SHIPS SIGNS_CONTRACT SUCCEEDS SUPPLIES TRAINS`
❌ **`INVESTS` / `PARTNERS_WITH` 不存在**（当前 139 动作中无）→ **记录缺口，不新增**（任务规则 §五）

### 1.7 relation_action_mappings（137 条）— 方案引用映射核对

✅ 关键映射均存在：`CORPORATE_CONTROL←ACQUIRES` · `ECONOMIC_SANCTION←SANCTIONS` · `SUPPLY_CHAIN←SUPPLIES`

（注：表名为 `relation_action_mappings`，含 `context` 受控词表，比方案 `relation_actions` 更丰富）

### 1.8 现有 relation/edge/graph 相关代码

- `entity_relationships` + `relation_observations` + `relation_evidence` + `v_symmetric_relations` —— **"关系实例"能力已存在**
- `GET /api/v1/entities/{id}/relationships` 存在（实体全部关系，directed+symmetric 统一）
- `GET /api/v1/relationships/{id}` 关系详情 + timeline + 7d/30d 统计
- `POST /api/v1/relationships/batch` 批量关系（L2 Pre-Fetch 数据源）
- `POST /api/v1/relations/candidates` 候选接收
- **无独立 Graph 查询端点**（1-hop/2-hop 无专门 API）

---

## ⚠️ 关键冲突 / 缺口（BLOCKER 预检）

### CONFLICT-1（高优先级）：`entity_relations` 方案 vs 现有 `entity_relationships`

- **CURRENT**: 现有 `entity_relationships` 已是"关系实例表"（from/to_entity_id + relation_type_id + confidence + status + valid_from/to + superseded_by + first/last_seen_at + uq_active_relation 部分唯一索引 + 审批流生成）
- **EXPECTED**: 任务书 §五建议新建 `entity_relations` 保存关系实例
- **IMPACT**: 若直接新建 `entity_relations` 会与 `entity_relationships` **双轨并存**，违背"不破坏现有设计"原则，产生维护/数据分裂风险
- **RECOMMENDATION**: **复用/扩展现有 `entity_relationships` 作为关系实例表**（它是既有实现，冻结的审批流/证据/观测都挂它）；本次真正新增的是 **规则/约束层**（relation_entity_type_rules / action_entity_role_rules / relation_source_rules）+ 校验逻辑。`entity_relations` 不新建，除非有强理由。

### CONFLICT-2：`relation_entity_type_rules` vs 现有 `relation_types.from/to_entity_type_ids`

- **CURRENT**: `from/to_entity_type_ids` JSONB 已含全部 17 关系的类型约束（种子），但**无校验逻辑**
- **EXPECTED**: 新建 `relation_entity_type_rules` 表
- **RECOMMENDATION**: 两种兼容方案——(a) **复用现有 JSONB 字段 + 在 candidate/approve 落地校验逻辑**（不建表，最小改动）；(b) 若需更强查询/审计能力，建 `relation_entity_type_rules` 并从现有 JSONB 回填（ADD ONLY）。**倾向 (a) 或先 (a) 后按需 (b)**。

### CONFLICT-3：`action_entity_role_rules` — 全新表，无冲突

- 动作无主体/对象类型约束，**真新增**。但方案引用的 `INVESTS`/`PARTNERS_WITH` 动作不存在 → 角色规则种子只能覆盖现有 9 个相关动作，缺 2 个记 gap。

### 其他确认项

- `relation_source_rules`（🟡 推荐）：全新表，无冲突；evidence.source_type 现有枚举 `rss/article/llm_inference/manual/api`
- `relation_type_subtype_rules`（🟢 后置）：不实现
- confidence 分层：现有 EWMA 单值（D2 冻结）保留，分解权重可存观测 metadata

---

## 审计结论

1. **现有环境完整、可无损扩展**：Alembic 0002 + 21 表 + SQLAlchemy 2.0 + pytest 37 + 独立 dev/prod 库
2. **方案的核心"关系实例"已存在**（entity_relationships），本次新增重点 = **规则/约束层 + 校验 + Graph 查询**
3. **3 个兼容性决策待定**（CONFLICT-1/2 复用现有，CONFLICT-3 真新增），已给推荐方案，均 ADD ONLY
4. **2 个动作缺口**（INVESTS/PARTNERS_WITH）记录，不新增
5. **未做任何代码/DB 修改** —— 等待方案确认后进入 PHASE 2-17

---

## 相关
- [entity-center-entity-graph-v1-dev-plan.md](entity-center-entity-graph-v1-dev-plan.md) — 开发任务书
- [entity-center-relation-graph-gap-analysis-2026-08-16.md](entity-center-relation-graph-gap-analysis-2026-08-16.md) — 方案 gap 分析
- [entity-center-v1.md](entity-center-v1.md) — 现有实现
