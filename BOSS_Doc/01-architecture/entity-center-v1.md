# Entity Center V1 — 完整报告

> 版本: v1.0 · 2026-08-12 · Clean Slate 实现完成
> 定位: 统一实体与关系基础设施，独立 `entity_center` schema，与 news_intel 系统**零耦合**
> 相关: [knowledge-base.md](knowledge-base.md) · [entity-relationships.md](entity-relationships.md) · [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)

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
              Semantic Extraction (统一入口, 未来接)
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
| `entities` | id(PK), canonical_name, entity_type_id FK, subtype_id(复合FK), importance(0-100), importance_source, status(active/inactive/merged/deprecated), merged_into_entity_id(自引用FK), description, metadata JSONB | 实体主表（100 人工导入） |
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

### 4.6 数据量（2026-08-13 生产实测）

| 项 | 生产 |
|----|:---:|
| entity_types | 16 |
| entity_subtypes | 27 |
| relation_types | 17 |
| actions | 139 |
| relation_action_mappings | 137 |
| **实体总数** | **759** |
| entity_aliases | ~4000（全实体中英别名） |
| entity_identifiers | 含 kb_v1_id + ticker（105 公司股票代码） |
| ontology_versions | 199+（含 v0 种子基线） |
| config_versions | 1 |

### 4.7 实体库构成（2026-08-13，759 实体）

| 类型 | 数量 | 内容 |
|------|:--:|------|
| COMPANY | 199 | 世界500强105 + 产业链龙头59 + 原始公司 |
| COUNTRY | 192 | 全球国家（六维评分：军事/金融/科技/矿产/能源/地理） |
| MILITARY_ORGANIZATION | 116 | 全球武装力量（中英/本地语别名） |
| LOCATION | 63 | 重要城市（首都≥70/核心<100） |
| GOVERNMENT | 48 | 核心国家金融监管/国防/科技/工业机构 |
| INTERNATIONAL_ORGANIZATION | 40 | 国际机构（联合国/NATO/IMF等） |
| FINANCIAL_INSTITUTION | 31 | 央行/商业银行/投行 |
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
mention + context → ① 精确匹配 alias.normalized==mention (0.95)
                   → ② 双向前缀/短名匹配 (mention≥4: alias 开头 / mention 以 alias 开头, 0.70)
                   → ③ 上下文消歧 adjacent_entities 交集 (+0.05)
                   → 状态: resolved(≥0.60) / ambiguous / unresolved
```

性能: 精确 P99<50ms 目标（需 DB 与应用同机；当前远程 VPS DB 网络主导）。

### 5.3 PG → SQLite Mirror 同步

- 触发器自动写 `sync_outbox`（INSERT/UPDATE/DEACTIVATE）
- 同步守护 `run_sync_daemon.py` 每 30s 轮询 → SQLite 只读 mirror（10 表，Tombstone）

---

## 6. API 契约

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:---:|------|
| POST | `/api/v1/resolve` | 公开 | mention → candidates + selected + status |
| GET | `/api/v1/entities/{id}/relationships` | 公开 | 实体所有关系（directed + symmetric 统一） |
| GET | `/api/v1/relationships/{id}` | 公开 | 关系详情 + 观测时间线 |
| GET | `/admin/candidates?status=` | Admin | 候选列表 |
| POST | `/admin/candidates/{id}/approve` | Admin | 审批（含 TERMINATE 分支） |
| POST | `/admin/candidates/{id}/reject` | Admin | 拒绝 |
| GET | `/admin/ontology` | Admin | Ontology 只读浏览 |
| GET | `/admin-ui` | Admin | Admin 管理页（静态） |
| GET | `/health` | 公开 | 健康检查 |

**鉴权**: 复用现有 web JWT（HS256，payload.level='admin'）+ `X-Admin-Token` 静态兜底。

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
| DB | VPS `entity-center-postgres` 容器 :5433 | 同容器 `entity_center_test` 库 | compose 内 `entity-center-postgres` |
| 连接 | `EC_DATABASE_URL` (.env) | conftest | 容器内 env |

---

## 8. 前端集成（并入 Next.js）

- `frontend/src/app/entity-center/page.tsx`: 候选审批/实体解析/Ontology 三 Tab，Bearer JWT 复用现有登录
- `Sidebar.tsx` ADMIN 段 + `🧬 Entity Center` 导航
- 页面调用 `/entity-center/api/*`（nginx 代理到 entity_center 后端）

---

## 9. 实体导入（先 100 条）

`scripts/import_entities.py`：从 `references/entity-network.json` 精选 100 实体（15 国 + 8 组织 + 高分公司/人物），幂等批量 upsert。

**已导入生产 100 实体 + 100 别名**（canonical 为唯一别名）。

---

## 10. 测试与验收

### 10.1 pytest（20 项全过）

| 模块 | 覆盖 |
|------|------|
| test_uuidv7 (5) | 版本/变体/单调/可注入时钟 |
| test_resolution (5) | 精确/unresolved/空/上下文/阈值 |
| test_upsert (5) | 新建关系/EWMA+TERMINATE/追加观测/幂等+拒绝/缺 action |
| test_api (5) | health/resolve/鉴权/Ontology |

### 10.2 Golden Set（LLM 辅助标注）

- `scripts/generate_golden_set.py`: 本地 qwen3 生成变体 mention → **97 条**（auto 52 + llm-draft 45，标 `source` 待人工校验）
- `scripts/score_golden_set.py`: 评分 **88.7%**（53.6% → 88.7%，靠双向前缀匹配改进）
- 剩余失败 = 中文/拼音/简称**别名缺口**（华为/阿里巴巴/CSC 等）

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

1. **Golden Set 人工校验**：核对 45 条 llm-draft（含 `China Ping An→China` 假阳性）
2. **别名缺口**：Lanqi/CSC/Ping An 等具体公司别名未导入（运营补录）
3. **多跳推理**：`relation_multihop_rules` 仅建表，V2 实现
4. **Signal Engine**：Pre/Post-Extract Signal 公式不冻结，V1 策略化实验
5. **Semantic Extraction 接入**：实体观测的新闻级事实提取（统一入口）待接
6. **entity_types/subtypes 管理 UI**：当前仅 relation_types/actions 可编辑，实体类型待接
