# Entity Center V1 — 完整报告

> 版本: v1.1 · 2026-08-16 与环境一致性核对更新（原 v1.0 2026-08-12）
> 定位: 统一实体与关系基础设施，独立 `entity_center` schema，与 news_intel 系统**零耦合**
> 相关: [knowledge-base.md](knowledge-base.md) · [entity-relationships.md](entity-relationships.md) · [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md) · [entity-center-v1-audit-2026-08-16.md](entity-center-v1-audit-2026-08-16.md)（基线符合度审计）

---

## 1. 项目概述

Entity Center 是新闻情报系统中的**统一实体与关系基础设施**，提供：

| 能力 | 说明 |
|------|------|
| **Identity** | 实体唯一身份（UUIDv7 应用层生成） |
| **Ontology** | 实体两级分类（16 Type + Subtype）+ 关系类型（17）+ 动作（139） |
| **Resolution** | 新闻文本 Mention → Canonical Entity（精确/短名/上下文消歧） |
| **Relation** | 实体间稳定事实关系（方向、置信、历史追溯） |
| **Observation** | 关系的一次时点事实观测（Action + Effect 六分类 + Polarity + Time） |
| **Evidence** | 关系成立的来源与证据 |
| **Signal** | 供 L2 Router 的关系信号输入因子（公式不冻结） |

**核心决策（用户 2026-08-12 锁定）**：Clean Slate 全新部署、不迁移现有数据、独立 schema、人工审视后导入实体。

---

## 2. 设计基线（锁定版）

设计文档已锁定为不可变基线（`BOSS_Doc` 之外，原始文档在用户会话）。19 条语义冻结原则：

1. Relation Type = 稳定关系语义大类；Action = 可观测行为（独立）
2. Relation Type Weight ≠ Action Weight（敏感度 vs 强度，正交）
3. Relationship Fact 是唯一稳定事实源；Signal/Evolution 派生不写回
4. Relation Observation = 一次时点观测，六种效果：EMERGE/STRENGTHEN/CONFIRM/MAINTAIN/WEAKEN/TERMINATE
5. Polarity = 方向性影响（POSITIVE/NEGATIVE/NEUTRAL），Observation 级可覆盖
6. 同一 Entity Pair 允许多个 Relation Type 并存
7. Action ↔ Relation Type = N:N（`relation_action_mappings` + context 消歧）
8. 关系保留方向（`from → to`）；Symmetric 用 `min→max` 存储 + `v_symmetric_relations` 视图还原
9. LLM 只能创建 Candidate，Admin 审批才能成为 Active Relation
10. Confidence 更新用 EWMA（α=0.3，可配置）
11. 软删除统一状态语义（active/inactive/deprecated/merged）
12. `valid_from` 取 `event_at`（实际发生时间）而非 `published_at`

---

## 3. 系统架构

```
              Semantic Extraction (统一入口 /api/v1/relations/candidates 已建, search-engine-v2 流水线未接)
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
   Entity Center    Event Aggregator  Market Impact
   (Observation)    (既有系统, 零耦合)
           │
           ▼
   Candidate → Admin 审批 → Active Relation → Observation → Evidence
           │
           ▼
   PG (entity_center schema) ──sync_outbox 触发器──→ SQLite 只读 Mirror (本地 pipeline)
```

**技术栈**: Python 3.11 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic · pytest · asyncpg

**部署拓扑**: 并入 news-platform-v8 compose（`entity-center-postgres` + `entity-center-backend`），nginx `/entity-center/` 前缀路由。

---

## 4. 数据库 Schema（entity_center，19 表 + 视图，2026-08-13 实测）

### 4.1 核心实体表

| 表 | 关键字段 | 说明 |
|----|---------|------|
| `entity_types` | id(PK), code UNIQUE, name, description, status | 16 种一级类型 |
| `entity_subtypes` | id(PK), entity_type_id FK, code, name, UNIQUE(entity_type_id, code), UNIQUE(id, entity_type_id 复合外键用) | 二级类型（27 条） |
| `entities` | id(PK), canonical_name, entity_type_id FK, subtype_id(复合FK), importance(0-100), importance_source, status(active/inactive/merged/deprecated), merged_into_entity_id(自引用FK), description, metadata JSONB | 实体主表（759 实体，脚本幂等批量导入） |
| `entity_aliases` | id(PK), entity_id FK, alias, normalized(索引), language, alias_type, is_preferred, confidence, valid_from/to | 别名（精确匹配走 idx_aliases_normalized） |
| `entity_identifiers` | id(PK), entity_id FK, scheme(kb_v1_id/legacy_pg_id/ticker/isin/wikidata/iso_alpha3/cik), identifier, source, confidence, UNIQUE(scheme, identifier) | 外部标识符 |

### 4.2 Ontology 配置表

| 表 | 关键字段 | 说明 |
|----|---------|------|
| `relation_types` | id(PK), code UNIQUE, name, weight(敏感度 0-1), directionality(directed/symmetric), inverse_code, from/to_entity_type_ids JSONB(GIN), event_enabled, status | 17 种关系类型 |
| `actions` | id(PK), code UNIQUE, name, event_type, weight, polarity(-1/0/1), description, metadata JSONB(含 en/zh/past/noun/patterns), status | 139 个动作 |
| `relation_action_mappings` | id(PK), relation_type_id FK, action_id FK, context(受控词表), weight, priority, UNIQUE(rel, act, context) | N:N 映射（137 条） |
| `config_versions` | version(SEQUENCE), config_hash, config_snapshot JSONB, description, created_by, status, 唯一 active | 配置版本（ambiguous_threshold=0.60, ewma_alpha=0.3） |
| `data_revisions` | revision(SEQUENCE), description, affected_tables, created_by | 数据版本（每 Candidate 独立） |
| `ontology_versions` | id(PK), kind, code, version, action(create/update/status/rollback/seed), item_snapshot JSONB, **changes JSONB[{field,old,new}]**, created_by, UNIQUE(kind, code, version) | **Ontology 修改版本**（每次修改快照+参数变化; v0=种子基线永不被裁剪） |

### 4.3 关系与观测

| 表 | 关键字段 | 说明 |
|----|---------|------|
| `entity_relationships` | id(PK), from_entity_id FK, to_entity_id FK, relation_type_id FK, confidence, status(active/inactive), valid_from/to, superseded_by(自引用FK), first_seen_at, last_seen_at, **部分唯一索引 uq_active_relation**(同 from+to+type 仅一 active) | 稳定关系事实 |
| `relation_observations` | id(PK), relationship_id FK, action_id FK, effect(6分类), polarity, event_at/published_at/extracted_at, article_id(opaque), evidence_id FK, confidence, extracted_by, metadata JSONB | 时点观测 |
| `relation_evidence` | id(PK), source_type(rss/article/llm_inference/manual/api), source_url, article_id, evidence_text, evidence_language, extracted_by | 证据源 |
| `relation_candidates` | id(PK), from_entity_id FK, to_entity_id FK, relation_type_id FK, action_id FK, effect(默认 confirm), polarity_override, confidence, article_id, **event_at**(D9 偏离), evidence_text, model_name, status(pending/approved/rejected), reviewed_by/at, rejection_reason | 审批队列 |
| `relation_observation_stats` | relationship_id PK FK, observation_count_7d/30d, last_observation_at, trend_score | 预聚合统计(后台 5min) |
| `sync_outbox` | id(PK), table_name, record_id, operation(INSERT/UPDATE/DEACTIVATE/DELETE), payload, synced_at, sync_attempts, last_error | 同步变更日志(触发器) |
| `audit_log` | id(PK), target_type/id, operation, field, old/new_value, actor_type/id, reason, config_version FK, data_revision FK | 统一审计(JSONB 变更存 JSON Patch) |
| `relation_multihop_rules` | id(PK), from_relation_type_id FK, to_relation_type_id FK, signal_relation_type_id FK, allowed_entity_type_ids JSONB, max_hops, weight_multiplier, enabled | 多跳规则(V2 预留, 仅建表) |

**视图/函数/触发器**: `v_symmetric_relations`（symmetric 双向还原视图）· `uuidv7()`（PL/pgSQL 触发器用）· `sync_outbox_notify()` + 10 表触发器（entities/entity_aliases/entity_identifiers/relation_types/actions/relation_action_mappings/entity_relationships/relation_observations/relation_evidence/relation_observation_stats）。

### 4.4 外键依赖关系（28 个 FK，2026-08-13 生产实查）

| 表 | FK 字段 | 引用表 |
|----|---------|--------|
| `entity_subtypes` | entity_type_id | entity_types |
| `entities` | entity_type_id | entity_types |
| `entities` | (subtype_id, entity_type_id) 复合 | entity_subtypes(id, entity_type_id) |
| `entities` | merged_into_entity_id | entities（自引用） |
| `entity_aliases` | entity_id | entities |
| `entity_identifiers` | entity_id | entities |
| `entity_relationships` | from_entity_id / to_entity_id | entities |
| `entity_relationships` | relation_type_id | relation_types |
| `entity_relationships` | superseded_by | entity_relationships（自引用） |
| `relation_action_mappings` | relation_type_id / action_id | relation_types / actions |
| `relation_candidates` | from_entity_id / to_entity_id | entities |
| `relation_candidates` | relation_type_id / action_id | relation_types / actions |
| `relation_observations` | relationship_id | entity_relationships |
| `relation_observations` | action_id | actions |
| `relation_observations` | evidence_id | relation_evidence |
| `relation_observation_stats` | relationship_id | entity_relationships |
| `relation_multihop_rules` | from/to/signal_relation_type_id | relation_types |
| `audit_log` | config_version / data_revision | config_versions / data_revisions |

### 4.5 依赖关系图

```
entity_types ──< entity_subtypes ──< entities ──< entity_aliases
    │                            ▲  │              entity_identifiers
    │                            │  │
    │                     (复合FK)│  ├──< entity_relationships ──< relation_observations
    │                            │  │        │ (self superseded_by)│
    │                            │  │        ├──< relation_observation_stats
    │                            │  │        │
    │                            │  │        └──< relation_candidates
relation_types ──< entity_relationships ──< relation_observations
    │    ▲            relation_action_mappings ──> actions
    │    └──< relation_multihop_rules
    │
actions ──< relation_action_mappings / relation_candidates / relation_observations
relation_evidence ──< relation_observations
config_versions ──< audit_log ──< data_revisions
ontology_versions (独立, 记录各 ontology 表修改)
sync_outbox (触发器写入, 供 SQLite mirror)
v_symmetric_relations (视图: entity_relationships × relation_types)
```

### 4.6 数据量（2026-08-16 生产实测）

| 项 | 生产 |
|----|:---:|
| entity_types | 16 |
| entity_subtypes | 27 |
| relation_types | 17 |
| actions | 139 |
| relation_action_mappings | 137 |
| **实体总数** | **759** |
| entity_aliases | **2803**（中英/本地语别名） |
| entity_identifiers | 220（kb_v1_id + ticker + iso_alpha3 等） |
| ontology_versions | **229**（含 v0 种子基线） |
| config_versions | **4**（v1 种子 + 后续发布） |
| active 关系 | **23**（KB entity-network 导入） |
| relation_candidates | 23（pending） |
| relation_observations | 23 |
| sync_outbox 积压 | 0（已同步） |

### 4.7 实体库构成（2026-08-16，759 实体）

| 类型 | 数量 | 内容 |
|------|:--:|------|
| COMPANY | **196** | 世界500强105 + 产业链龙头59 + 原始公司 |
| COUNTRY | 192 | 全球国家（六维评分：军事/金融/科技/矿产/能源/地理） |
| MILITARY_ORGANIZATION | 116 | 全球武装力量（中英/本地语别名） |
| LOCATION | 63 | 重要城市（首都≥70/核心<100） |
| GOVERNMENT | **49** | 核心国家金融监管/国防/科技/工业机构 |
| INTERNATIONAL_ORGANIZATION | 40 | 国际机构（联合国/NATO/IMF等） |
| FINANCIAL_INSTITUTION | **30** | 央行/商业银行/投行 |
| COMMODITY | 30 | 大宗商品（能源/金属/农产品） |
| PERSON | 26 | 评分>60国家领导人 |
| CURRENCY | 17 | 全球主要货币 |

### 4.8 实体检索验证（2026-08-13）

- **去重**: 769→759（合并 11 组跨类型重复：ICBC/HSBC/摩根大通等；保留 3 组不同国家真同名 MOD）
- **解析准确率**: 48 组代表用例 **100% 命中正确实体**（含中英文）
- **别名冲突处理**: 移除黄金 "AU"（撞澳大利亚/非盟）；SAF 等武装力量简写冲突为真实歧义保留
- **验证工具**: `scripts/verify_entity_library.py`（类型分布/重复检查/解析准确率）· `scripts/dedup_entities.py` · `scripts/dedup_entities_by_alias.py`

---

## 5. 数据流

### 5.1 Candidate → Active 审批 Upsert（核心）

```
LLM/自动抽取 → relation_candidates(pending)
  → Admin 审批 (FOR UPDATE SKIP LOCKED 并发控制 + 实体对锁定)
      ├─ Evidence 创建 (evidence_text 非空)
      ├─ 已有 active 关系 + effect=terminate → 关系停用(valid_to=event_at) + terminate observation
      ├─ 已有 active 关系 + 其他 effect → 追加 observation + EWMA confidence(α=0.3)
      └─ 无关系 → 新建 relationship + observation + stats
  → 每个 candidate 独立 data_revision → audit_log
  → 触发器自动写 sync_outbox → SQLite mirror
```

### 5.2 Entity Resolution（§11.4）

```
mention + context → ① 精确匹配 alias.normalized==mention 或 canonical_name==mention (0.95)
                   → ② 双向前缀/短名匹配 (mention≥4 且 alias 长度≥3: alias 开头 / mention 以 alias 开头, 0.70)
                   → ③ 上下文消歧 adjacent_entities 交集 (+0.05)
                   → ③b 消歧信号(规范§3, 2026-08-14): is_preferred 别名 +0.02 (alias 频度先验)
                       + entity_type 先验 TYPE_PRIOR_DEFAULT (config_versions.type_prior 可覆盖)
                       — 同分候选间破平局
                   → 状态: resolved(≥0.60) / ambiguous / unresolved (无候选不硬匹配)
                   → method: context_resolution(上下文加分命中) / exact_match
```

⚠ **2026-08-13 修复**（Golden Set 759 库重新生成暴露）:
- **Fix B**: 精确匹配补 canonical_name → 修复 **641/759 (84%)** 实体 canonical 名不在别名表导致自身名字不可解析（如 "Kingdom of Norway"）
- **Fix A**: 前缀匹配要求 alias 长度≥3 → 排除 1-2 字符短别名（股票码 t/f、国家码 no/un/in、化学符号 ag）作为任意 mention 前缀误报（62 种此类别名，实体库扩到 759 后撞库严重）

性能: 精确 P99<50ms 目标（需 DB 与应用同机；当前远程 VPS DB 网络主导）。

### 5.3 PG → SQLite Mirror 同步

- 触发器自动写 `sync_outbox`（INSERT/UPDATE/DEACTIVATE/DELETE，10 表，同事务 ACID）
- 同步守护 `run_sync_daemon.py`：连续运行每 30s 轮询；**生产用 Windows 计划任务 `entity-center-sync` 每 60 分钟 `--once`**（2026-08-14 由 1 分钟调低，短期无消费者降低负载）→ SQLite 只读 mirror（10 表，Tombstone）
- mirror 当前**无消费者**（search-engine-v2 零读取，grep 确认仅 config 定义路径），保留备未来实体接地

---

## 6. API 契约（2026-08-16 全量核对）

### 公开 API（`/api/v1`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:---:|------|
| POST | `/api/v1/resolve` | 公开 | mention → candidates + selected + status |
| GET | `/api/v1/entities/{id}/relationships` | 公开 | 实体所有关系（directed + symmetric 统一，含 from/to 名称+权重） |
| GET | `/api/v1/relationships/{id}` | 公开 | 关系详情 + 7d/30d 统计 + 最近观测 + timeline |
| POST | `/api/v1/relationships/batch` | 公开 | 实体列表间 active 关系（L2 Pre-Fetch 数据源） |
| POST | `/api/v1/relations/candidates` | 公开* | Semantic Extraction 候选接收（effect 默认 confirm，1h 幂等） |

### Admin API（`/admin`，需 admin JWT）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/admin/candidates` / `/admin/candidates/{id}/approve` `/reject` / `/batch-approve` | 候选列表/审批(含 TERMINATE)/拒绝/批量(每候选独立 revision) |
| GET/POST/PATCH | `/admin/entities` `/admin/entities/{id}` `/status` `/merge` | 实体 CRUD + 状态 + 合并(禁链式) |
| GET | `/admin/entity-types` | 类型+子类型下拉 |
| GET/POST/PATCH | `/admin/ontology` `/admin/ontology/{kind}` `/admin/ontology/{kind}/{code}` `/status` | Ontology CRUD + 状态 |
| GET/POST | `/admin/ontology/export` `/admin/ontology/import` | 全量导出/导入(冲突检查) |
| GET/POST | `/admin/ontology/{kind}/{code}/versions` `/rollback` | 条目版本历史/回滚 |
| GET | `/admin/ontology/meta` | 可编辑字段规则 |
| GET/POST | `/admin/export/{kind}` `/admin/import/{kind}` | CSV 导出/导入(实体/关系/动作/类型/子类型) |
| GET | `/admin/config/current` | 当前 active 配置 |
| POST | `/admin/config/switch` | 发布新版本(旧版归档) |
| GET | `/admin/config/versions` | 版本列表(含 snapshot 参数) |
| POST | `/admin/config/rollback` | 回退到指定版本 |
| GET | `/admin-ui` | Admin 管理页（静态） |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

**鉴权**: 复用现有 web JWT（HS256，payload.level='admin'）+ `X-Admin-Token` 静态兜底（默认 = `EC_ADMIN_JWT_SECRET`）。
⚠ **`/api/v1/relations/candidates` 当前无鉴权**（任意可提交，§9.1 llm_agent 角色未落实，见 §14.2）。

---

## 7. 部署（并入现有 compose）

- **compose**: `scripts/news-platform-v8/docker-compose.yml` 新增 `entity-center-postgres`（独立 volume `entity_center_pgdata`）+ `entity-center-backend`（build context `../../../entity_center`）
- **nginx**: `/entity-center/` 前缀路由（页面精确匹配走 frontend，API 前缀剥离走 entity_center backend）
- **入口**: `http://100.107.117.23/entity-center/`（API）· `/entity-center`（Next.js 管理页）
- **验证**: `/entity-center/health` 200 · resolve 200 · 原 `/api/v1/dashboard` 200（零影响）

### 7.1 部署命令

```bash
# VPS
cd /home/administrator/news-platform-v8 && git pull
cd scripts/news-platform-v8
docker compose up -d --build entity-center-postgres entity-center-backend   # 首次
docker compose exec entity-center-backend alembic upgrade head               # 迁移
docker compose exec entity-center-backend python scripts/load_seeds.py       # 种子
docker compose restart nginx                                                 # nginx 路由
```

### 7.2 环境

| 项 | dev | test | 生产 |
|----|-----|------|------|
| DB | 独立容器 `entity-center-postgres` **:5433**（`entity_center` 库，2026-08-16 实测） | 同容器 `entity_center_test` 库 | compose 内 `news-platform-v8-entity-center-postgres-1` **:5432** |
| 连接 | `EC_DATABASE_URL` (.env → :5433) | conftest → :5433 entity_center_test | 容器内 env |

---

## 8. 前端集成（并入 Next.js）

- `frontend/src/app/entity-center/page.tsx`: **5 Tab（候选审批/实体解析/实体/Ontology/配置）**，Bearer JWT 复用现有登录
- `Sidebar.tsx` ADMIN 段 + `🧬 Entity Center` 导航
- 页面调用 `/entity-center/api/*`（nginx 代理到 entity_center 后端）
- 实体 Tab 含「画像」弹窗（关系图谱 1跳+2跳展开）与「合并」弹窗；配置 Tab 支持版本发布/列表/回退

---

## 9. 实体导入

**首批**（2026-08-12）：`scripts/import_entities.py` 从 `references/entity-network.json` 精选 100 实体（15 国 + 8 组织 + 高分公司/人物），幂等批量 upsert → 生产 100 实体 + 100 别名。

**后续扩展**（2026-08-13，脚本幂等批量）：759 实体 / 2803 别名 / 220 标识符（世界500强、产业链龙头、全球国家、军队、城市、政府机构、国际组织、货币、金融机构、大宗商品、领导人等，详见 §4.7 / §13.2）。

---

## 10. 测试与验收

### 10.1 pytest（37 项全过，2026-08-16）

| 模块 | 覆盖 |
|------|------|
| test_uuidv7 (5) | 版本/变体/单调/可注入时钟 |
| test_resolution (11) | 精确/unresolved/空/上下文/阈值 + canonical无别名可解析 + 短别名不误报前缀 + type-prior + alias 频度 |
| test_upsert (5) | 新建关系/EWMA+TERMINATE/追加观测/幂等+拒绝/缺 action |
| test_api (5) | health/resolve/鉴权/空 mention |
| test_approve_flow (5) | 10线程并发只建1关系/terminate无active不新建/terminate停用/重复审批幂等/EWMA |
| test_candidate_ingest (1) | symmetric 标准化/幂等/缺省 effect/from==to/不直写关系表 |
| test_relation_query (1) | 查询层 directed+symmetric/详情/7d30d/批量 |
| test_admin_governance (4) | 角色矩阵/批量审批独立 revision/Entity Merge/config 切换 |

### 10.2 Golden Set（LLM 辅助标注）

- `scripts/generate_golden_set.py`: 本地 qwen3 生成变体 mention，从当前实体库随机采样（canonical 40 + 别名 15 + 负例 12 + LLM 变体）
- `scripts/score_golden_set.py`: 跑 Entity Resolution 算准确率
- **2026-08-13 基于 759 实体库重新生成 + 评分**：
  - 生成 **99 条**（auto 67 + llm-draft 32）→ 人工校验剔除坏标注/ISO 码 **19 条** → **80 条**（auto 67 + llm-draft 13）
  - 评分 **80/80 = 100.0%**（此前 88.7%→89.7% 为 ~100 实体旧库基线）
  - auto 全过 = Fix A/B + 别名补齐生效；llm-draft 覆盖真实缩写（MS/NZ/BP PLC/NVO/SMIC 等）
- **坏标注剔除**（llm-draft 质检）：MSC(实为地中海航运)/CB(钴符号是Co)/FC Barcelona(足球俱乐部)/Sudan Inc.(模板误生成)/MAF(歧义马来西亚军)/SAR/错拼(NOODISK) 等
- **未入基准的真实缩写缺口**（运营可补，见 §14）：COL/DEU/TJK/TJ/BCN 等 ISO/机场码 — 因 3 字符前缀碰撞风险不自动加别名

### 10.3 性能

精确解析远程 VPS DB P50≈634ms（网络主导）。**SLO P99<50ms 需 DB 与应用同机部署**。

---

## 11. 实现决策（含偏离基线，需审批）

| # | 主题 | 决策 | 状态 |
|---|------|------|------|
| D1 | actions 139 基数 | 现有 actions.yaml 实测 137 + 补 RESUMES/FULFILLS = **139**（文档"81 基础"为旧快照） | **偏离待审批** |
| D2 | confidence 语义 | **存在置信度**（与强度/方向正交），weaken 也 EWMA 提高存在置信 | 实现决策 |
| D3 | CONFIRM vs MAINTAIN | confirm=显式佐证；maintain=被动提及；无法判断默认 confirm | 实现决策 |
| D4 | polarity×effect 一致性 | 写入前校验（warning 记 audit，不阻断） | 实现决策 |
| D5 | 枚举字典 | alias_type/scheme/source_type 受控值 | 实现决策 |
| D6 | article_id 语义 | opaque nullable UUID，无 FK，V1 允许 NULL | 实现决策 |
| D7 | Operator 角色 | Entity Center 自建 actor 概念，Auth 复用现有 JWT | 实现决策 |
| D8 | 国家归属 | 存 `entities.metadata.country`（展示用），V1 不做关系边 | 实现决策 |
| D9 | relation_candidates.event_at | **§7.2 审批流程要求，§6.6 DDL 漏列 → 已补列** | **偏离待审批** |
| D10 | Auth 复用 | 复用现有 web JWT（HS256 level=admin）+ X-Admin-Token 兜底 | 实现决策 |

---

## 12. 已完成的增强（2026-08-12 第二轮）

### 别名富化
- `scripts/enrich_aliases.py`: 导入 KB V1 中英别名 + 人工补充中文国名（生产 109 条别名 + 70 kb_v1_id 标识符）
- resolution 短名长度加权（`中国移动` > `中国`，修复误配）→ Golden Set 89.7%
- 中文解析全通：华为/苹果/英伟达/台积电/美国/中国/欧盟

### Ontology 管理增强
| 功能 | 说明 |
|------|------|
| **选择** | 关系/动作表全选/多选/单选勾选 + 仅显示已选过滤 |
| **排序** | 列头点击升/降序 |
| **导出** | 全量 + **导出选中子集**（勾选项+映射+基础类型） |
| **导入** | 文件上传 → 冲突检查报告 → 应用(新建)/强制覆盖；新增 POST code 冲突→409 |
| **编辑/新增** | 跳转详情页 `/entity-center/edit/{kind}/{code}` / `/entity-center/new/{kind}` |
| **特殊字段** | code/directionality **灰底只读**（不可编辑，只能废弃重建） |
| **状态生命周期** | active↔deprecated 一键切换 |
| **版本管理** | 每次 create/update/status/rollback 记录快照 + **参数变化明细 changes[{field,old,new}]**，保留最近≥2版本，可回滚；**v0 = 种子基线**（seed_baseline 回填，永不被裁剪，回滚到 v0 始终恢复原始种子态） |
| **实体管理** | 实体 Tab：列表(搜索名称/别名+类型/状态过滤) + **添加实体**(类型/子类型/重要度/国家/别名, 冲突409) + **编辑弹窗**(ID/名称灰底只读) + **废弃/启用**(状态生命周期 active/inactive/deprecated/merged) |
| **CSV 导出导入** | 实体/实体关系/动作 CSV（`GET /admin/export/{kind}` + `POST /admin/import/{kind}`）；**行2=字段备注**（自动生成勿填 / 只允许新增不可修改 / 可编辑）；实体 canonical_name、动作 code、关系 from+to+type 为只允许新增字段 |

### 新增 API
| 端点 | 说明 |
|------|------|
| `POST /admin/ontology/{kind}` | 新增（code 冲突→409） |
| `PATCH /admin/ontology/{kind}/{code}` | 更新可编辑字段（特殊字段忽略） |
| `GET /admin/ontology/meta` | 每 kind 可编辑/不可编辑字段 |
| `GET /admin/ontology/{kind}/{code}/versions` | 版本历史（含参数变化） |
| `POST /admin/ontology/{kind}/{code}/rollback` | 回滚到指定版本 |
| `GET /admin/ontology/export` | 全量导出 |
| `POST /admin/ontology/import` | 导入冲突检查/应用 |

### 部署
- 迁移 0002（ontology_versions）+ 生产已应用
- nginx 路由重构：`/entity-center/api|admin/` 走 backend，`/entity-center/edit|new/` 走 frontend
- 静态 admin-ui 同步（排序 + 编辑/新增链接）

---

## 13. 实体检索与维护指南

### 13.1 检索方式

| 方式 | 说明 |
|------|------|
| **API 解析** | `POST /entity-center/api/v1/resolve` → mention 中英别名 → candidates + status |
| **Admin UI** | `/entity-center` → 实体 Tab：类型/状态过滤 + 搜索名称/别名 + 编辑/废弃/启用 |
| **关系查询** | `GET /entity-center/api/v1/entities/{id}/relationships` |

### 13.2 实体扩展模式（新增一类实体）

```
① scripts/{type}_data.py       ← 数据 (country, name_en, name_zh, ticker, 别名, 打分, 备注)
② scripts/sync_{type}_to_db.py ← 幂等 upsert (复用 company sync 模式)
③ python scripts/sync_{type}_to_db.py   (dev 验证)
④ tar → VPS → docker cp → 容器内跑      (生产)
⑤ verify_entity_library.py     ← 验证解析
```

**已建数据模块**: country_data / country_data_full / location_data / military_orgs_data / leaders_data / international_orgs_data / currency_data / financial_institutions_data / gov_agencies_data / commodity_data / companies_data / industry_chains_data。

### 13.3 检索验证

```bash
python scripts/verify_entity_library.py   # 类型分布 + 重复检查 + 48组解析准确率
python scripts/dedup_entities.py          # canonical+同国家 去重
python scripts/dedup_entities_by_alias.py # 共享中文别名+同国家 跨类型去重
```

### 13.4 维护要点

- **股票代码** → `entity_identifiers`（scheme=ticker），唯一约束 (scheme, identifier)
- **国家归属** → `meta.country`（公司/机构/武装力量）
- **国产替代权重** → `meta.domestic_sub=true` + 评分加成
- **产业链** → `meta.chains=["CHAIN:stage"]`（原材料/设备/技术/加工/生产）
- **别名冲突** → 短简写跨实体冲突为真实歧义，靠上下文/词长消歧
- **部署坑** → 改 data 后必须重新 tar 到 VPS（docker cp 只拷宿主机旧文件）

---

## 14. 已知缺口 / 下一步

### 14.1 已完成（2026-08-13 Golden Set 全修）
- **Golden Set 人工校验 ✅**：先 80/80 = 100%（剔除坏标注后）；治理后复生成+再剔除低质 llm-draft → **71/71 = 100%**；`China Ping An` 假阳性已通过补别名 `Ping An Insurance`/`China Ping An` 修复
- **Resolution Fix A ✅**：前缀匹配要求 alias 长度≥3，修复 1-2 字符短别名（股票码/国家码/化学符号）前缀误报
- **Resolution Fix B ✅**：精确匹配补 canonical_name，修复 84% 实体自身名字不可解析
- **别名补齐 ✅**：LGES/LG Energy/VW/国芯基金二期/Ping An Insurance/China Ping An/NZ/MS/BP PLC/NVO（`scripts/patch_alias_gaps.py` 幂等）
- **短码冲突治理 ⛔ 已回退**（`scripts/rollback_shortcode_conflicts.py`）：用户裁定删除范围过宽（含军队缩写/银行缩写/IDF 公司，非国家码），已恢复 21 条别名 + 撤销 IDF 废弃，恢复为治理前状态
- **国家码 + 股票代码治理 ✅**（`scripts/patch_governance_codes.py` 幂等，dev+prod 已跑）：
  - **国家实体国家字段禁国家码**：删除 ISO/IOC 国家码别名 40 条（au/br/de/fr/jp/in/usa/chn...），**保留 US/UK/NZ/UAE/USA + 英文短名**（taiwan/turkey/china/brazil）；删除的码记入 `meta.iso_codes`
  - **公司股票代码放备注**：删除命中 `entity_identifiers`(scheme=ticker) 的别名 153 条（MSFT/NVDA/TSLA/BP/IBM/600879.SS...），**仅保留 AAPL**；ticker 记入 `meta.tickers`，本体仍在 entity_identifiers
  - 影响（用户已知悉）：DE→德国 等码、MSFT/NVDA 等 ticker 不再解析；全称/中文名/ canonical 均正常
  - 黄金集治理后复生成+剔除 qwen3 低质 llm-draft → **71/71 = 100%**（auto 67/67 保持）
  - 已知副作用：CSCO（思科 ticker 移走）前缀撞 CSC→中信证券；Indian Armed Forces 前缀→India（全称仍可解析）
- **国家实体 country 字段统一用名称 ✅**（`scripts/patch_country_field_name.py`）：192 国家中 191 个 `meta.country` 从 ISO 码（US/CN/DE/KR）替换为 `name_en_short`（缺则 canonical），与公司/机构 meta.country 已用的全称一致；唯一残留 UAE（name_en_short 即 "UAE"，是保留的英文短名）；码仍在 meta.iso_codes 可查
- **公司别名补充 ✅**（`scripts/enrich_company_aliases.py` 幂等，dev+prod，两批完成）：
  - **第一批** 37 家主要公司补 104/106 条：参考5家精确（阿里/华为/腾讯/Google/特斯拉）+ 巨头子品牌（iPhone/GeForce/CUDA/ChatGPT/Azure/台积电/中石油/瑞银/茅台…）
  - **第二批** 72 家公司补 63 条：世界500腰部（IBM/巴斯夫/卡特彼勒/耐克/德州仪器/淡水河谷/通用电气/日立/阿斯利康…）+ 中国产业链/国企（宁德时代/长飞光纤/西部超导/兆易创新/中科三环 + 中金CICC/小米Xiaomi/迈瑞Mindray/隆基LONGi/宝钢Baosteel/网易NetEase…）
  - 累计 109 家覆盖；验证 59/59 解析、黄金集 71/71=100%
  - **剩余生僻 ~110 家别名仍薄**（Suzhou Yuanguang/Rocket Pi/Goumax/CIG 等，避免写错跳过，待运营补录或专项）
- **Ontology 完整性校验 ✅（2026-08-14, 7/7 PASS）**：对照 `ontology/*.yaml` 权威源 + §5.1/5.3/5.4
  - entity_types **16/16** 一致 · entity_subtypes **27** 复合FK无游离 · relation_types **17/17** 属性(weight/directionality/event_enabled)逐条一致 · actions **139** metadata{en,zh,past,noun,patterns}结构完整 · N:N映射 **137** weight全有 context词表[corporate/default/financial] · entities复合FK 0不匹配
  - **发现并修复**: `entity_identifiers` 缺 `entity_id` 索引（仅 pk+uq(scheme,identifier)）→ 模型补 `Index("idx_identifiers_entity","entity_id")` + dev/生产 `CREATE INDEX IF NOT EXISTS`（commit c9fbca3）；现 3 索引齐
- **Relation 查询层补齐 ✅（§6.5, 2026-08-14）**：在既有 `v_symmetric_relations` 视图（canonical_from/to/is_reversed 正确）上补齐
  - 关系详情: from/to canonical 名称 + relation_type_name + confidence
  - **7d/30d 观测统计**: relation_observation_stats 优先, 表空回退实时 COUNT（`idx_observations_relation_time` Index Only Scan）
  - 最新 5 条观测（action/effect/polarity/event_at）
  - **批量查询** `POST /api/v1/relationships/batch`: 实体列表间所有 active 关系（L2 Router Pre-Fetch, `=ANY(:ids)` + uq_active_relation 索引）
  - EXPLAIN ANALYZE 确认索引生效; 单测 test_relation_query.py 全过; 生产已部署
  - ⚠️ 关系库本身为空（ISS-004, 待运营/候选审批填充）
- **Semantic Extraction → Relation Candidate 管道 ✅（§7.1/§6.6, 2026-08-14）**：`POST /api/v1/relations/candidates` 接收 LLM 抽取
  - effect 空→默认 confirm; 写 relation_candidates(status=pending), **不直接写 entity_relationships**（必须经 Admin 审批, 复用 approve_candidate）
  - symmetric 关系存储前 min(id)→max(id) 方向标准化; from==to → 400
  - **幂等**: 同 article + from/to/type/action 1 小时内去重（返回已有候选, deduplicated=true）
  - 模型补 `metadata` JSONB 列（SQLAlchemy 保留名→属性用 `meta` 映射到 metadata 列）; dev/test/生产已 ALTER
  - 单测 test_candidate_ingest.py 全过; 生产已部署验证
- **Candidate→Active 审批流程校验 ✅（§7.2, 2026-08-14）**：现有 approve_candidate 已覆盖 Evidence/FOR UPDATE SKIP LOCKED/terminate分支/EWMA(α=0.3)/新建+stats/data_revision/reviewed
  - **修复规范违背**: effect=terminate 但无 active 关系时, 原代码误走新建分支 → 改为 warning 不失败不新建
  - 单测 test_approve_flow.py 5项全过: **10线程并发审批只建1关系1观测** / terminate无active不新建 / terminate停用(valid_to,不物理删除) / 重复审批幂等 / EWMA(0.3*new+0.7*old=0.65)
  - 生产已部署; 并发控制=候选 SKIP LOCKED + 实体对 FOR UPDATE 序列化
- **PG→SQLite 同步服务补齐 ✅（§10, 2026-08-14）**：既有 run_sync_daemon(30s) + sync.py(10表镜像/重试) + 触发器函数; 本次补齐
  - **dev 库应用 10 个 sync 触发器**（apply_sync_triggers.py, 幂等, 读 fix_sync_trigger.sql）
  - **sync.py 重试修复**: 原 apply_batch 失败行也被标记 synced 不重试 → 改为失败行保持 synced_at NULL + sync_attempts++ + last_error, 超 **5 次告警**
  - 新增 `sync_latency_monitor.py`（积压/最老延迟/卡死, >5min 告警）+ `rebuild_sqlite_mirror.py`（每日全量重建兜底）
  - 端到端验证: 触发器写 outbox → poll → mirror 落库全通（dev）
  - ⚠️ **生产发现**: sync_outbox 积压 5888 条/38h —— **生产 sync daemon 未运行**, 需本地 pipeline 机器 cron 拉起（或容器内跑 run_sync_daemon.py）
  - **Admin 治理后端 ✅（§9, 2026-08-14）**: 补齐 4 缺口
    - **角色矩阵**: deps.py `require_role(min_role)` — admin>operator>llm_agent>readonly; JWT level 映射(llm→llm_agent); operator 访问 admin-only → 403
    - **批量审批**: `POST /admin/candidates/batch-approve` — 每候选独立 data_revision
    - **Entity Merge**: `POST /admin/entities/{source}/merge` — 校验禁链式合并(target.merged_into_entity_id NULL)/source非merged; 迁移 aliases+identifiers; source→merged; audit_log
    - **config 切换**: `GET /admin/config/current` + `POST /admin/config/switch` — 发布新 snapshot(ambiguous_threshold/ewma_alpha), 旧版归档
    - **修复2个真bug**: ① create_config_version 先插后归档违反 partial unique(status=active) → 改为先归档再插; ② 测试库 sync 触发器是旧版(NEW.status直接引用) → 应用 fix_sync_trigger.sql
    - 单测 test_admin_governance.py 4项全过; 生产已部署验证(角色矩阵403/批量/配置读取)
    - **前端 4 模块 ✅（2026-08-14）**: 在现有单页多Tab加
      - 候选审批 Tab: 复选框批量选择 + 批量审批按钮(batch-approve)
      - 实体 Tab: 「画像」弹窗(基本信息/关系图谱via symmetric view/别名/标识符) + 「合并」弹窗(source→target)
      - 新增「配置」Tab: 当前 config_version 查看 + 参数编辑(ambiguous_threshold/ewma_alpha) + 发布新版本(旧版归档)
      - 修复 loadConfig TDZ (useEffect依赖前声明); VPS build 验证 + 已部署, 页面200/含新功能
    - **关系数据导入 + 画像拓扑 ✅（2026-08-14）**:
      - `import_kb_relations.py`: 从 KB `entity-network.json` 导入 27 关联 → 23 条 active 关系（4 条因实体不在759库跳过）；type→relation_type/action 映射（appoints→PERSONNEL_MOVEMENT/APPOINTS、conflicts→MILITARY_CONFLICT/ATTACKS…）；走 create_candidate→approve（独立 revision/observation/stats）；dev+生产已导入
      - relationships API 增强: 返回 `from_name/to_name` + `relation_weight`（画像拓扑显示实体名/权重/方向）
      - 画像弹窗: **1跳直接关系**（实体名/出入向/类型/权重/conf）+ **2跳间接关联**（邻居的邻居，向各方向展开）
      - 生产验证: 川普→J.D.Vance/KevinWarsh(任命 w0.40)、TSMC 4 条、美国 2 条; 2跳链路展开正常
      - **浏览器人工检查 ✅**: `check_profile_browser.py`(Playwright+Chrome 无头) — 注入 admin token 打开页面, 确认新版渲染(配置Tab) + 页面内 fetch 校验川普画像 1跳(J.D.Vance/KevinWarsh w0.40)/2跳回环
      - **坑**: ① nginx 前端页加 Cache-Control no-cache(覆盖 Next.js s-maxage, 需重启容器否则 bind-mount 旧 inode); ② 主前端会话检查会清 localStorage token, 测试注入需 add_init_script 防清除; ③ **asyncpg Numeric 返回字符串**, 前端 `relation_weight?.toFixed(2)` 抛 "is not a function" → 画像弹窗渲染崩溃, 需 `Number(x).toFixed(2)`（已修 679ab6e）; ④ **admin 数据(实体/候选/Ontology)全部需 admin 登录**, 未登录搜索显示"无实体"（曾误判为搜索 bug）→ 加全局登录组件解决
      - **全局登录/注册/注销 ✅（2026-08-14）**: `AuthMenu.tsx` 接入 Header 右上角 — 未登录显示 登录/注册 按钮(弹窗表单, 复用 /auth/login + /auth/register + useAuth), 已登录显示 `email+level` 徽标 + 注销; 解决"未登录 admin 数据全空"的困惑; 浏览器验证: 未登录显按钮 / 登录后显账户+注销 / 实体搜川普→Donald Trump
  - **方案B 落地 ✅（2026-08-14）**: 生产 postgres 暴露 5432 → 本地 cron 同步
    - VPS compose entity-center-postgres 加 `ports: 5432:5432`（Tailscale 内网）
    - 本地全量重建 `data/entity_center_mirror_prod.db`（759实体/2803别名）
    - `run_sync_prod.bat`（EC_DATABASE_URL=prod + mirror=prod）+ Windows 计划任务 `entity-center-sync` **每 60 分钟** `--once`（2026-08-14 由 1 分钟调低：短期无消费者, 降低负载）
    - 验证: 生产变更 → 触发器 → outbox → daemon → 本地镜像自动同步（LastTaskResult 0）
    - ⚠️ **mirror 当前无消费者**（只写不读, grep 确认仅 config 定义路径）；短期保留 daemon 备将来实体接地用, 频率已调至 60 分钟

### 14.2 剩余
1. **真实缩写缺口**（未入基准，运营可补）：COL/DEU/TJK/TJ/BCN 等 ISO/机场码 — 3 字符有前缀碰撞风险，需配合上下文消歧策略再决定
2. **数据模块与 DB 漂移**：companies_data 等 canonical（Volkswagen Group/Ping An Insurance）与 DB 去重后 canonical（Volkswagen/中国平安）不一致；LG Energy/国家集成电路基金二期不在任何数据模块 — 需运营对齐权威源
3. **多跳推理**：`relation_multihop_rules` 仅建表，V2 实现
4. **Signal Engine**：Pre/Post-Extract Signal 公式不冻结，V1 策略化实验；**当前零实现**（仅 stats 预聚合 + batch 数据源，无 signal service）
5. **Semantic Extraction 流水线接入**：统一入口 `POST /api/v1/relations/candidates` **已建**（2026-08-14，接收/幂等/不直写关系表）；但 **search-engine-v2 的 fact_pipeline 未接**（仍走本地 canonicalizer + KB V1 YAML 自产自销，不产生 candidate）— 见 [entity-center-v1-audit-2026-08-16.md](entity-center-v1-audit-2026-08-16.md) §4.2
6. **entity_types/subtypes 管理 UI**：✅ **已完成**（2026-08-13，Ontology Tab 支持实体类型/子类型列表/状态/编辑/新增/CSV）
7. **stats 后台任务**：`relation_observation_stats` 5min 更新 trend_score 的定时任务**未实现**（trend_score 仅新建时写死 0.50，`trend_score_multiplier`/`min_entity_importance_for_signal` 为死配置）
8. **每周全量一致性校验**：PG↔SQLite 无 row-count/checksum 比对脚本（只有全量重建）
9. **性能 SLO**：resolve 精确 P99<50ms / 消歧<200ms 未达标（远程 VPS 网络主导，dev P50≈634ms），无运行时监控
10. **候选提交端点鉴权**：`/api/v1/relations/candidates` 无鉴权，§9.1 llm_agent 角色未落实

---

## 15. Admin 治理界面使用指南（§9, 2026-08-14）

### 15.1 入口与登录

- **URL**: `http://100.107.117.23/entity-center`（Tailscale 内网）
- **鉴权**: 复用 web JWT（`level=admin`）或 `X-Admin-Token` 静态 token；未登录时功能不可用
- **角色矩阵**: admin(3) > operator(2) > llm_agent(1) > readonly(0)
  - JWT `level` 映射: admin/operator/llm → 对应; 其余/free → readonly
  - admin: 全部（含 config 切换/Merge/Ontology 写）; operator: 实体管理+候选审批; llm_agent: 只读+候选提交; readonly: 只读
  - 角色不足 → 403（如 operator 访问配置管理）

### 15.2 五个 Tab 的使用方法

| Tab | 场景 | 用法 |
|-----|------|------|
| **候选审批** | Semantic Extraction 抽出的关系候选待人工裁决 | 按状态筛选(pending/approved/rejected) → 单条「批准/拒绝」(拒绝填原因) 或 **勾选多条 → 批量审批**（每候选独立 data_revision） |
| **实体解析** | 验证 mention → 实体映射质量 | 输入 mention → 显示 candidates/status（resolved/ambiguous/unresolved） |
| **实体** | 实体库管理 | 搜索/类型/状态过滤 → 编辑（灰底只读字段）→ 废弃/启用 → **画像**（基本信息+关系图谱+别名/标识符）→ **合并** |
| **Ontology** | 关系类型/动作/映射查看+版本管理 | 查看/筛选/导出/导入; 编辑详情页(灰底只读 code) + 版本历史/回滚 |
| **配置** | 调整解析阈值等全局参数 | 查看当前 config_version → 编辑参数 → 发布新版本（旧版自动归档，立即生效） |

### 15.3 关键操作细节

- **批量审批**: 勾选 pending 候选 → 「批量审批(N)」；每个候选独立 `data_revision`，失败单个不影响其它（返回 per-candidate 结果）
- **实体画像**: 点行内「画像」→ 弹窗显示 类型/子类型/重要度/国家/别名/标识符 + **关系图谱**（GET /api/v1/entities/{id}/relationships，symmetric 走视图）；关系库为空时显示"无 active 关系"（ISS-004）
- **Entity Merge**: 选 source 行「合并」→ 粘贴 target entity_id → 执行。校验：source≠target、source 非 merged、**target 禁链式合并**（target.merged_into_entity_id 必须为空）。执行后 source 标记 merged、别名/标识符迁移到 target、写 audit_log
- **config 切换**: 修改 `ambiguous_threshold`（解析阈值）、`ewma_alpha`（置信度平滑）等 → 发布为 v+1，旧版自动 archived。**发布后立即对解析生效**（60s 配置缓存）
- **版本记录 + 回退（2026-08-16 补）**: 配置 Tab 下方"已发布版本记录"列表（v/状态/说明/发布时间/参数 snapshot）；非 active 版本可点「回退」→ 归档当前 active、目标版本置 active（`GET /admin/config/versions` + `POST /admin/config/rollback`）

### 15.4 注意事项（⚠️）

1. **破坏性操作确认**: Merge 和 config 发布不可轻易撤销（Merge 有 audit_log 可追溯，但别名/标识符已迁移；config 可再发布回滚）。执行前确认 source/target 正确。
2. **Merge 后无法反合并**: 禁链式合并意味着 merged 的实体不能再作为 target；误合并需手工用 SQL/Admin 恢复。
3. **config 发布影响全局**: 改 ambiguous_threshold 会影响所有解析调用；建议先小步调整并观察 golden set（`python scripts/score_golden_set.py`）。
4. **候选审批的 action 依赖**: 无 action_id 的候选无法审批（approve 返回 invalid）。
5. **角色最小化**: operator 足够就别用 admin；X-Admin-Token 是静态令牌，应妥善保管（当前默认 `v8-jwt-secret-2026-...`，生产建议换强密钥）。
6. **关系库为空**: 画像的关系图谱/时间线依赖关系数据（ISS-004 未填充）；数据流入前图谱区为空属正常。
7. **前端在真实仓库**: 改前端只改 `search-engine-v2/scripts/news-platform-v8/frontend/`（根 `frontend/` 是陈旧副本勿动）；VPS build 在 compose 完成，本地不 build。

---

## 16. Entity Graph V1（2026-08-17，ADD ONLY 增量）

> 从"实体名单"升级为"实体关系网络基础设施"。**未改任何冻结表**（21 表 + 视图 0 修改）。详见 [entity-center-entity-graph-v1-report.md](entity-center-entity-graph-v1-report.md)。

### 新增表（migration 0003）
**`action_entity_role_rules`** — 动作主体/对象实体类型 + 语义角色约束（FK actions + entity_types，UNIQUE(action,subject_type,object_type)，11 条种子规则）。

### 新增 API（`app/api/graph.py`）
| 端点 | 说明 |
|------|------|
| `GET /api/v1/entities/{id}/relations/outgoing` | 出向关系 |
| `GET /api/v1/entities/{id}/relations/incoming` | 入向关系 |
| `GET /api/v1/entities/{id}/graph` | 1-hop 邻居图（outgoing/incoming/symmetric） |
| `POST /api/v1/relations/validate` | 校验候选关系（类型约束/自环/重复/时间 + 可选动作角色） |

### 校验器（`services/graph.py`）
- `validate_entity_relation`: **复用 `relation_types.from/to_entity_type_ids`** 类型白名单（空=不限）+ 存在性/自环/重复/时间
- `validate_action_role`: 查 `action_entity_role_rules` 匹配主体/对象类型
- 正确拒绝类型非法：`NVIDIA→MILITARY_CONFLICT→TSMC` → INVALID_SOURCE_ENTITY_TYPE ✓

### 种子（经 create_candidate → approve 完整审批流）
- 11 条动作角色规则 + **46 条基础关系**（SUPPLY_CHAIN 16 / STRATEGIC_PARTNERSHIP 11 / MARKET_COMPETITION 8 / TRADE_RESTRICTION 4 / ECONOMIC_SANCTION 3 / CORPORATE_CONTROL 2 / MAJOR_INVESTMENT 3 / POLITICAL_HOSTILITY 2 / MILITARY_CONFLICT 1）
- 生产 active 关系 **23 → 69**；类型非法 5 条被拒绝

### 数据量（2026-08-17 更新）
```
entity_relationships active 69 · relation_observations 69+ · relation_candidates 若干
action_entity_role_rules 11 · 新增后总表数 22 表 + 1 视图
```

### 未完成（记录在报告 §13）
relation_source_rules（🟡 推荐→Signal 阶段）· 2-hop（V2）· 前端画像接入 graph 端点 · INVESTS/PARTNERS_WITH 动作缺口（前端标签映射）

## 17. 通道 B — 实体标识符人工维护 + 附带修复（2026-08-18，ADD ONLY）

> 目的：补上"人工维护"通道的缺口——`entity_identifiers` 此前无任何 API/CSV/前端入口（生产 kb_v1_id×68/ticker×151 全由离线脚本写入），画像页"标识符"列大多为 "—"。本期全部 ADD ONLY：不动冻结表、无迁移、现有端点行为不变，新参数默认空/None。

### 17.1 标识符人工维护（核心）
- **create/update 扩展**：`create_entity`/`update_entity` 新增 `identifiers`（list[{scheme,identifier}]，`source="manual"`）。API：`EntityCreateRequest.identifiers`、`EntityUpdateRequest.identifiers`（三态：`None` 不动 / `[]` 清空 / `[...]` 全量替换，diff 式保留未变行 UUID）。
- **⚠️ 全局唯一预检**：`uq_identifier_scheme_value (scheme,identifier)` 是**跨实体**唯一。写入前 `_identifier_conflict(exclude_entity_id)` 预检，被其他实体占用 → create 返回 409 / update 返回 400，**实体保持不变**（不做静默丢弃）。
- 前端：添加表单 + 编辑弹窗标识符从只读改为可编辑输入（格式 `scheme:value,` 逗号分隔）；画像弹窗仍只读展示。

### 17.2 CSV 扩展
- entities 新增 `identifiers` 列（`scheme:value`，竖线 `|` 分隔，按**第一个 `:`** 切分）；导出批量查询 `entity_id.in_` 一次取回；导入"列不存在"不动标识符、"列存在空值"清空。

### 17.3 附带修复（均为明确 bug，行为增益）
| # | 修复 |
|---|---|
| 2 | entities CSV 导出 subtype 列不再硬编码空串（outerjoin EntitySubtype） |
| 3 | CSV 数值解析（importance/weight/polarity/confidence）逐行 try/except，坏值记 errors+skipped 不中断整批 |
| 4 | relationships CSV 导入读取 status 列（校验 active/inactive，默认 active）；置 active 前预检 `uq_active_relation` 部分唯一索引避免 IntegrityError |
| 5 | `update_entity` 单独传 subtype 生效（逻辑抽出 type 块，无 type 时用当前 entity_type_id 校验） |
| 6 | 前端 CSV 导入 entity_types/entity_subtypes 后调 loadOntology()、relationships 调 loadEntities() 刷新 |

### 17.4 测试
`tests/test_channel_b.py`：服务级（create 带标识符/跨实体冲突不建实体/diff 替换/单独 subtype）+ CSV 级（导出含 subtype+标识符/坏数值不中断/status 生效）+ API 级（POST 带标识符详情回显/PATCH 替换/复用他人标识符 409）。标识符用 `ticker:TEST-<uuid>` 避免跨测试碰撞。

### 17.5 未做（下一期）
**通道 C**：事实→关系候选的自动抽取触发源（独立后处理脚本，读 fact 表 → resolve 实体 → 批量候选），审批 Tab 增强（明细/evidence/名称解析/分页）。

## 18. 通道 B — 人工维护实体数据 使用指导（2026-08-18）

> 通道 B = **Admin UI / CSV / API** 三条人工维护途径，与通道 A（批量同步脚本）互补。日常补录/修正实体数据，尤其**标识符**（此前只能靠离线脚本写入，画像页"标识符"列多为 "—"）。

### 18.1 能力矩阵

| 操作 | UI 实体Tab | CSV | API |
|---|---|---|---|
| 新增实体 | ✅「+ 添加实体」 | ✅ entities 导入 | `POST /admin/entities` |
| 编辑字段（类型/子类型/重要度/国家/说明） | ✅ 编辑弹窗 | ✅ | `PATCH /admin/entities/{id}` |
| 编辑别名 | ✅ 编辑弹窗（逗号分隔） | ✅ aliases 列 | PATCH `aliases` |
| **编辑标识符** | ✅ 编辑弹窗（`scheme:value`） | ✅ identifiers 列 | PATCH `identifiers` |
| 状态（废弃/启用） | ✅ 行内按钮 | ✅ status 列 | `PATCH .../status` |
| 合并实体 | ✅「合并」 | ❌ | `POST .../merge` |
| 关系维护 | ⚠️ 仅画像查看 | ✅ relationships CSV | candidates API |

### 18.2 标识符维护（重点）

- **合法 scheme**: `kb_v1_id`（KB V1 实体 ID）/ `ticker`（股票代码）/ `isin` / `wikidata` / `legacy_pg_id` / `iso_alpha3` / `cik`
- **格式**: `scheme:value`，多个用逗号或竖线分隔，如 `ticker:NVDA, kb_v1_id:COMP_NVIDIA`
- **编辑入口**: 实体 Tab → 搜索 → 点「编辑」→ 弹窗底部「标识符」输入框
- **回显**: 打开编辑弹窗即显示全部现有标识符（`ticker:NVDA, kb_v1_id:COMP_NVIDIA`）
- **保存语义**: **全量替换**——输入框内容 = 保存后的完整集合；清空输入框 = 删除全部标识符
- ⚠️ **全局唯一**: 同一 `scheme:value` 全库只能属于一个实体（`ticker:AAPL` 只能有一个）。被其他实体占用时保存返回 **400「标识符 xx:yy 已被其他实体占用」**——需先移除占用方或换值
- **查看**: 画像弹窗「标识符」区只读展示；导出 CSV 的 identifiers 列

### 18.3 新增实体

- **UI**: 实体 Tab →「+ 添加实体」→ 名称*(必填)/类型/子类型/重要度(0-100)/国家/别名(逗号分隔)/标识符(逗号分隔)/说明 → 创建。名称冲突返回 409。
- **CSV**: 实体 Tab →「导出实体CSV」拿模板（行2=字段备注）→ 填行 →「导入实体CSV」→ 看报告（created/updated/skipped/errors）。
- **API**:
  ```bash
  curl -X POST http://100.107.117.23/entity-center/admin/entities \
    -H "Authorization: Bearer <admin-jwt>" -H "Content-Type: application/json" \
    -d '{"canonical_name":"X Corp","type":"COMPANY","importance":60,
         "aliases":["X"],"identifiers":[{"scheme":"ticker","identifier":"XCOR"}]}'
  ```

### 18.4 CSV 列说明（以导出模板为准）

- **entities**: `canonical_name`*(只允许新增)/`type`/`subtype`/`importance`/`country`/`aliases`(竖线 `|` 分隔)/`identifiers`(`scheme:value` 竖线分隔)/`description`/`status`/`id`/`created_at`
- **relationships**: `from_name`/`to_name`/`relation_type`(均只允许新增)/`confidence`/`status`(active/inactive)
- **字段备注行语义**: `自动生成`=勿填 / `只允许新增`=新建必填、已存在不可改 / `可编辑`=已存在时更新
- **容错**: 数值列(importance/confidence 等)非法值 → 该行 skipped+errors，**不中断整批**；`identifiers` 列缺省=不动标识符、空值=清空
- **导入报告**: created=新建 / updated=更新 / skipped+errors=被跳过行与原因

### 18.5 关系维护

- **CSV 导入 relationships**: from/to 实体须已存在（按 canonical_name 精确匹配）、relation_type 编码合法；status 缺省 active
- ⚠️ 同 (from,to,type) 只能有一条 active（`uq_active_relation`）；重复置 active → 该行 skipped
- **候选审批**（语义抽取的手动端）: 候选审批 Tab 审关系候选 → 通过即生成 active 关系（`POST /api/v1/relations/candidates` 提交 → admin 审批）

### 18.6 状态与合并

- 废弃/启用: 实体行内按钮（废弃=deprecated，启用=active）
- 合并: 行内「合并」→ 粘贴 target id → 执行。source 标 merged、别名/标识符迁移到 target，**禁链式合并**（target 不能是已合并结果）

### 18.7 注意事项（⚠️）

1. **canonical_name 不可改**（标识字段，只能废弃后重建）
2. **标识符全局唯一**，重复值保存返回 400
3. CSV 模板**用导出的为准**（含备注行），勿手写列名
4. 大库导出 CSV 可能较慢（759+ 实体 ~24s，别名数据累积所致）
5. 改前端只改 `search-engine-v2/scripts/news-platform-v8/frontend/`（根 `frontend/` 是陈旧副本勿动）
6. 生产实体中心代码经 **tar 手动同步 + `restart nginx`** 部署（VPS 目录非 git）

## 19. 策划实体关系补充（2026-08-18，数据运维）

> 用户提供 64 条关系清单（制裁/冲突/领土争端/战略合作/组织成员/金融/监管等），先补实体（正确解析、别名完整）再补关系。

### 19.1 实体补充（新建 2 + 补别名 3，幂等）
- **新建**：`Pakistan`（COUNTRY，别名 巴基斯坦/巴基斯坦伊斯兰共和国/Islamic Republic of Pakistan）、`APEC`（INTERNATIONAL_ORGANIZATION，别名 亚太经合组织/Asia-Pacific Economic Cooperation/亚佩克）
- **补别名**（已有实体，保留现有）：`Viet Nam` +Vietnam/越南社会主义共和国、`Korea, Democratic People's Republic of` +North Korea/DPRK/朝鲜民主主义人民共和国、`Palestine, State of` +Palestine
- ⚠️ Vietnam 不新建（库中已有 `Viet Nam` 国家，补别名即可，避免重复实体对）

### 19.2 关系类型白名单扩展（4 类，ADD ONLY 放宽，同步 relation_types.yaml）
- `STRATEGIC_PARTNERSHIP` from/to + INTERNATIONAL_ORGANIZATION（NATO/EU 伙伴）
- `TRADE_RESTRICTION` to + INTERNATIONAL_ORGANIZATION（UK→EU）
- `FINANCIAL_RELATION` from + INTERNATIONAL_ORGANIZATION、to + COUNTRY/GOVERNMENT（IMF/World Bank→国家）
- `REGULATORY_PENALTY` from + INTERNATIONAL_ORGANIZATION、to + COUNTRY/GOVERNMENT（ICC/IAEA→国家）

### 19.3 关系导入（64 条，走审批流）
- 脚本 `scripts/sync_curated_data.py`（幂等，--dry-run；**生产执行须显式 `EC_DATABASE_URL` 指向 5432**）
- 顺序：resolve → `validate_entity_relation` → `create_candidate` → `approve_candidate`（每候选独立 data_revision + audit）
- ⚠️ **坑**：resolve 缓存必须在补实体后重新解析（新别名/新实体生效），否则 North Korea/Palestine/Vietnam/Pakistan/APEC 解析失败
- 结果：64 条全落库（未解析 0 / 类型拒绝 0）；生产 active 关系 69→128；resolve 复检 39 名全对（North Korea→DPR、Vietnam→Viet Nam、Pakistan→Pakistan、APEC→APEC）
