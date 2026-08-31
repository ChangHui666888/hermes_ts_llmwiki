# Entity Center 数据库 Schema 参考（entity_center schema）

> **核对日期**: 2026-08-31 · **来源**: VPS 生产库实测（`news-platform-v8-entity-center-postgres-1` :5432）
> **库**: `entity_center` · **Schema**: `entity_center` · **Migration**: Alembic 0003（Entity Graph V1 新增 1 表）
> **规模**: 22 表 + 1 视图 · **1359 实体（1348 active）** / **3996 别名** / **1497 标识符** / **248 active 关系**（KB V1 数据迁移后, 2026-08-31）

---

## 连接命令

```bash
# 生产 (:5432, VPS)
cd /home/administrator/news-platform-v8/scripts/news-platform-v8
docker compose exec -T entity-center-postgres psql -U entity_center -d entity_center

# 开发 (:5433, 独立容器)
docker exec entity-center-postgres psql -U entity_center -d entity_center

# 测试库 (开发容器内)
docker exec entity-center-postgres psql -U entity_center -d entity_center_test
```

---

## 0. 三库拓扑（2026-08-17 实测）

VPS 上共有 **3 个 postgres:16 容器**，职责分离（Entity Center 与 news_intel 零耦合）：

```
┌─ compose (news-platform-v8) ─────────────────────────────────────────────┐
│                                                                          │
│  news-platform-v8-entity-center-postgres-1   news-platform-v8-postgres-1 │
│  ┌─────────────────────────────┐            ┌─────────────────────────┐  │
│  │ entity_center (生产EC)      │            │ news_intel (主情报库)   │  │
│  │ 759实体/2803别名/69关系/22表 │            │ 27 ORM表/articles/events│  │
│  │ 0.0.0.0:5432 (Tailscale)    │            │ 内部5432 (无宿主映射)   │  │
│  │ ↑ entity-center-backend     │            │ ↑ backend (FastAPI)    │  │
│  └─────────────────────────────┘            └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

  独立容器 (非 compose, 早期遗留)
  entity-center-postgres
  ┌──────────────────────────────────┐
  │ entity_center (开发EC)  :5433     │ ← 本地 .env EC_DATABASE_URL
  │ entity_center_test (测试) :5433   │ ← pytest conftest 指向
  │ 100.107.117.23:5433              │
  └──────────────────────────────────┘
```

| 容器 | 端口 | 数据库 | 用途 | 使用者 |
|------|:---:|--------|------|--------|
| `news-platform-v8-entity-center-postgres-1` | 0.0.0.0:**5432** | `entity_center` | **生产** Entity Center | entity-center-backend (Web `/entity-center` 管理台) |
| `news-platform-v8-postgres-1` | 内部 5432（无宿主映射） | `news_intel` | **主新闻情报库**（新闻流水线全链路） | backend (FastAPI, `/api/v1/*`、`/news`、`/events`) |
| `entity-center-postgres` | 100.107.117.23:**5433** | `entity_center` + `entity_center_test` | **开发/测试** Entity Center | 本地开发 `.env` + pytest conftest |

**关键点**：
- 生产 EC（:5432）与开发 EC（:5433）是**两个独立实例**，数据需分别维护（实体导入/迁移/种子两边都跑）
- 生产 Web 只读 :5432；本地开发/测试用 :5433
- `news_intel` 与 `entity_center` **零耦合**（独立库/schema，互不引用）

---

## 1. 表清单 + 字段

> 类型说明：`varying(N)`=character varying · 时间戳均为 `timestamp with time zone`（TIMESTAMPTZ）

### 1.1 实体域

**`entity_types`**（7）— 16 种一级类型
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| code | varying(32) | UNIQUE `uq_entity_types_code` |
| name | varying(64) | NOT NULL |
| description | text | |
| status | varying(20) | CHECK active/deprecated, DEFAULT 'active' |
| created_at / updated_at | timestamptz | DEFAULT now() |

**`entity_subtypes`**（8）— 27 种子类
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| entity_type_id | uuid | FK→entity_types, UNIQUE(id,entity_type_id) `uq_subtype_id_type` |
| code | varying(64) | UNIQUE(entity_type_id,code) `uq_subtype_type_code` |
| name | varying(128) | NOT NULL |
| description | text | |
| status | varying(20) | CHECK, DEFAULT 'active' |
| created_at / updated_at | timestamptz | |

**`entities`**（12）— 1359 实体（1348 active / 11 deprecated）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| canonical_name | varying(255) | NOT NULL |
| entity_type_id | uuid | FK→entity_types |
| subtype_id | uuid | 复合FK(subtype_id,entity_type_id)→entity_subtypes(id,entity_type_id) |
| importance | numeric | CHECK 0-100, DEFAULT 0.00 |
| importance_source | varying(32) | DEFAULT 'system' |
| status | varying(20) | CHECK active/inactive/merged/deprecated, DEFAULT 'active' |
| merged_into_entity_id | uuid | FK→entities(自引用) |
| description | text | |
| metadata | jsonb | DEFAULT '{}' |
| created_at / updated_at | timestamptz | |
| 索引 | | `idx_entities_type` `idx_entities_importance` `idx_entities_status` |

**`entity_aliases`**（11）— 3996 条
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| entity_id | uuid | FK→entities, 索引 `idx_aliases_entity` |
| alias / normalized | varying(255) | NOT NULL, 索引 `idx_aliases_normalized` |
| language | varying(16) | |
| alias_type | varying(32) | NOT NULL |
| is_preferred | boolean | DEFAULT false |
| confidence | numeric | DEFAULT 1.0 |
| valid_from / valid_to | timestamptz | |
| created_at | timestamptz | |

**`entity_identifiers`**（7）— 1497 条（kb_v1_id 991 / ticker 256 / iso_alpha3 247 / isin 3）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| entity_id | uuid | FK, 索引 `idx_identifiers_entity` |
| scheme | varying(64) | kb_v1_id/ticker/iso_alpha3/isin 等 |
| identifier | varying(255) | UNIQUE(scheme,identifier) `uq_identifier_scheme_value` |
| source | varying(64) | |
| confidence | numeric | DEFAULT 1.0 |
| created_at | timestamptz | |

### 1.2 Ontology 域

**`relation_types`**（13）— 17 种关系
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| code | varying(64) | UNIQUE |
| name | varying(128) | NOT NULL |
| description | text | |
| weight | numeric | CHECK 0-1, DEFAULT 0.50（关系敏感度） |
| directionality | varying(16) | CHECK directed/symmetric |
| inverse_code | varying(64) | |
| from_entity_type_ids / to_entity_type_ids | jsonb | GIN 索引 `idx_relation_types_from_types` `idx_relation_types_to_types` |
| event_enabled | boolean | DEFAULT false |
| status | varying(20) | CHECK active/deprecated |
| created_at / updated_at | timestamptz | |

**`actions`**（11）— 139 种动作
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| code | varying(64) | UNIQUE `uq_actions_code` |
| name | varying(128) | NOT NULL |
| event_type | varying(32) | NOT NULL |
| weight | numeric | CHECK 0-1, DEFAULT 0.50（动作强度） |
| polarity | smallint | CHECK -1/0/1 |
| description | text | |
| metadata | jsonb | DEFAULT '{}'（en/zh/past/noun/patterns） |
| status | varying(20) | CHECK active/deprecated |
| created_at / updated_at | timestamptz | |

**`relation_action_mappings`**（7）— 137 条
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| relation_type_id | uuid | FK→relation_types |
| action_id | uuid | FK→actions |
| context | varying(64) | CHECK default/financial/military/legal/corporate/diplomatic |
| weight | numeric | CHECK 0-1（mapping 级权重） |
| priority | integer | DEFAULT 0 |
| created_at | timestamptz | |
| UNIQUE | | (relation_type_id, action_id, context) `uq_mapping_rel_act_ctx` |

**`config_versions`**（7）— 配置版本
| 字段 | 类型 | 约束 |
|------|------|------|
| version | bigint | PK, SEQUENCE `config_version_seq` |
| config_hash | varying(128) | NOT NULL |
| config_snapshot | jsonb | NOT NULL |
| description | text | |
| created_by | uuid | |
| status | varying(20) | CHECK active/archived, 部分唯一索引 `idx_config_active`(仅一 active) |
| created_at | timestamptz | |

**`ontology_versions`**（9）— Ontology 修改版本
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| kind / code / version | varying(32)/varying(64)/integer | UNIQUE(kind,code,version) `uq_ontology_version` |
| action | varying(16) | create/update/status/rollback/seed |
| item_snapshot | jsonb | NOT NULL |
| changes | jsonb | [{field,old,new}] |
| created_by | uuid | |
| created_at | timestamptz | |

### 1.3 Entity Graph 新增表（2026-08-17, migration 0003）

**`action_entity_role_rules`**（11）— 动作主体/对象实体类型+语义角色约束
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| action_id | uuid | FK→actions, 索引 `idx_action_role_action` |
| subject_entity_type_id / object_entity_type_id | uuid | FK→entity_types, 索引 `idx_action_role_subject`/`idx_action_role_object` |
| subject_role / object_role | varying(64) | acquirer/acquired/sanctioner/target 等 |
| priority | integer | DEFAULT 0 |
| allowed | boolean | DEFAULT true |
| description | text | |
| status | varying(20) | CHECK active/deprecated |
| created_at / updated_at | timestamptz | |
| UNIQUE | | (action_id, subject_type, object_type) `uq_action_role_rule` |

### 1.3 关系/观测域

**`entity_relationships`**（13）— 关系实例（248 active）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| from_entity_id / to_entity_id | uuid | FK→entities |
| relation_type_id | uuid | FK→relation_types |
| confidence | numeric | CHECK 0-1, DEFAULT 0.50 |
| status | varying(20) | CHECK active/inactive |
| valid_from / valid_to | timestamptz | valid_to 仅 terminate 写入 |
| superseded_by | uuid | FK→自身, CHECK 要求 inactive |
| first_seen_at / last_seen_at | timestamptz | DEFAULT now() |
| created_at / updated_at | timestamptz | |
| UNIQUE | | `uq_active_relation`(from,to,type) WHERE active（部分唯一） |
| 索引 | | `idx_relations_pair` `idx_relations_superseded` |

**`relation_observations`**（14）— 时点观测（255）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| relationship_id | uuid | FK→entity_relationships, 索引 `idx_observations_relationship` |
| action_id | uuid | FK→actions, 索引 `idx_observations_action` |
| effect | varying(16) | CHECK emerge/strengthen/confirm/maintain/weaken/terminate, 索引 |
| polarity | smallint | CHECK -1/0/1 |
| event_at | timestamptz | NOT NULL |
| published_at | timestamptz | |
| extracted_at | timestamptz | DEFAULT now() |
| article_id | uuid | opaque, 无 FK |
| evidence_id | uuid | FK→relation_evidence |
| confidence | numeric | CHECK 0-1, DEFAULT 0.50 |
| extracted_by | varying(32) | DEFAULT 'system' |
| metadata | jsonb | DEFAULT '{}' |
| created_at | timestamptz | |
| 复合索引 | | `idx_observations_relation_time`(relationship_id,event_at DESC) `idx_observations_article` |

**`relation_evidence`**（8）— 证据
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| source_type | varying(32) | rss/article/llm_inference/manual/api |
| source_url | text | |
| article_id | uuid | opaque, 索引 `idx_evidence_article` |
| evidence_text | text | |
| evidence_language | varying(16) | |
| extracted_by | varying(32) | DEFAULT 'system' |
| created_at | timestamptz | |

**`relation_candidates`**（18）— 候选审批（255）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| from_entity_id / to_entity_id | uuid | FK→entities, 索引 `idx_candidates_entities` |
| relation_type_id | uuid | FK→relation_types |
| action_id | uuid | FK→actions, 可空 |
| effect | varying(16) | CHECK, DEFAULT 'confirm' |
| polarity_override | smallint | CHECK -1/0/1 |
| confidence | numeric | CHECK 0-1, DEFAULT 0.50 |
| article_id | uuid | opaque |
| event_at | timestamptz | |
| evidence_text | text | |
| model_name | varying(128) | |
| status | varying(20) | CHECK pending/approved/rejected, 索引 `idx_candidates_status` |
| reviewed_by / reviewed_at | uuid / timestamptz | |
| rejection_reason | text | |
| created_at | timestamptz | |
| metadata | jsonb | DEFAULT '{}' |

**`relation_observation_stats`**（7）— 预聚合统计
| 字段 | 类型 | 约束 |
|------|------|------|
| relationship_id | uuid | PK, FK→entity_relationships |
| observation_count_7d / 30d | integer | DEFAULT 0 |
| last_observation_at | timestamptz | |
| trend_score | numeric | DEFAULT 0.50 |
| updated_at / created_at | timestamptz | |

**`relation_multihop_rules`**（10）— 多跳规则（仅建表）
| 字段 | 类型 | 约束 |
|------|------|------|
| id | uuid | PK |
| from_relation_type_id / to_relation_type_id / signal_relation_type_id | uuid | FK→relation_types |
| from_allowed_entity_type_ids / to_allowed_entity_type_ids | jsonb | GIN 索引 |
| max_hops | integer | DEFAULT 2 |
| weight_multiplier | numeric | DEFAULT 0.50 |
| enabled | boolean | DEFAULT true |
| created_at | timestamptz | |

### 1.4 治理/同步域

**`audit_log`**（13）
`id` · `target_type`(32) · `target_id`(uuid) · `operation`(32) · `field`(64) · `old_value`(text) · `new_value`(text) · `actor_type`(16) · `actor_id`(uuid) · `reason`(text) · `config_version`(bigint FK) · `data_revision`(bigint FK) · `created_at`
索引：`idx_audit_target` `idx_audit_created`

**`data_revisions`**（5）
`revision`(bigint PK SEQUENCE `data_revision_seq`) · `description`(text) · `affected_tables`(jsonb) · `created_by`(uuid) · `created_at`

**`sync_outbox`**（9）
`id`(uuid PK) · `table_name`(64) · `record_id`(uuid) · `operation`(16 CHECK INSERT/UPDATE/DEACTIVATE/DELETE) · `payload`(jsonb) · `synced_at`(timestamptz) · `sync_attempts`(int DEFAULT 0) · `last_error`(text) · `created_at`
索引：`idx_sync_outbox_pending`(created_at WHERE synced_at IS NULL) `idx_sync_outbox_table_record`

**`alembic_version`**（1）：`version_num`（当前 0003）

### 1.5 视图

**`v_symmetric_relations`**（8）：`id` · `from_entity_id` · `to_entity_id` · `relation_type_id` · `confidence` · `status` · `valid_from` · `valid_to`
（symmetric 关系按 `canonical_from=min(id)` `canonical_to=max(id)` 双向还原，另有 `is_reversed` 标记列）

---

## 2. 索引总表（pg_indexes 实测）

| 表 | 索引 |
|----|------|
| actions | pk_actions · uq_actions_code |
| audit_log | idx_audit_created · idx_audit_target |
| config_versions | pk_config_versions · idx_config_active(partial unique) |
| data_revisions | pk_data_revisions |
| entities | pk_entities · idx_entities_type · idx_entities_importance · idx_entities_status |
| entity_aliases | idx_aliases_normalized · idx_aliases_entity · pk_entity_aliases |
| entity_identifiers | uq_identifier_scheme_value · idx_identifiers_entity · pk_entity_identifiers |
| entity_relationships | idx_relations_pair · uq_active_relation(partial unique) · pk_entity_relationships · idx_relations_superseded |
| entity_subtypes | uq_subtype_id_type · pk_entity_subtypes · uq_subtype_type_code |
| entity_types | pk_entity_types · uq_entity_types_code |
| ontology_versions | pk_ontology_versions · idx_ontology_versions_item · uq_ontology_version |
| relation_action_mappings | uq_mapping_rel_act_ctx · pk_relation_action_mappings |
| relation_candidates | idx_candidates_status · pk_relation_candidates · idx_candidates_entities |
| relation_evidence | idx_evidence_article · pk_relation_evidence |
| relation_multihop_rules | pk_relation_multihop_rules · idx_multihop_to_types(GIN) · idx_multihop_from_types(GIN) |
| relation_observation_stats | pk_relation_observation_stats |
| relation_observations | pk_relation_observations · idx_observations_relation_time · idx_observations_article · idx_observations_relationship · idx_observations_effect · idx_observations_action |
| relation_types | idx_relation_types_from_types(GIN) · idx_relation_types_to_types(GIN) |

---

## 3. 数据量（2026-08-31，KB V1 数据迁移后）

```
entities 1359(active 1348) · entity_aliases 3996 · entity_identifiers 1497
entity_types 16 · entity_subtypes 27 · relation_types 17 · actions 139 · relation_action_mappings 137
entity_relationships 248(active) · relation_observations 255 · relation_evidence 255 · relation_candidates 255
audit_log 400 · data_revisions 255 · sync_outbox ~10398
```

**实体按类型（active）**：COMPANY 368 · COUNTRY 248 · LOCATION 241 · PERSON 121 · MILITARY_ORGANIZATION 119 · INDUSTRY 66 · GOVERNMENT 63 · INTERNATIONAL_ORGANIZATION 41 · COMMODITY 30 · FINANCIAL_INSTITUTION 30 · CURRENCY 17 · ORGANIZATION 4

**关系按类型（active）**：STRATEGIC_PARTNERSHIP 68 · INDUSTRY_AFFILIATION 66 · ORGANIZATION_MEMBER 29 · SUPPLY_CHAIN 18 · POLITICAL_HOSTILITY 14 · MARKET_COMPETITION 11 · ECONOMIC_SANCTION 8 · MILITARY_CONFLICT 7 · TRADE_RESTRICTION 7 · MAJOR_INVESTMENT 6 · FINANCIAL_RELATION 4 · TERRITORIAL_DISPUTE 4 · REGULATORY_PENALTY 2 · PERSONNEL_MOVEMENT 2 · GENERAL_RELATION 1 · CORPORATE_CONTROL 1

**⚠️ 数据来源说明（2026-08-31）**：国家/机构/城市/行业（KB 全量）+ 公司/人物（KB 精选）+ 原 771 精选实体；关系含国家 ally/rival、公司→行业归属（KB 迁移）与策划关系。迁移脚本 `scripts/migrate_kb_v1.py`（幂等），详见 [entity-center-v1.md §21](entity-center-v1.md)。

---

## 4. 查询命令

> 💡 **可直接运行脚本**：`entity_center/scripts/entity_center_queries.sql`（git 仓库内）含 35 条查询，支持 psql `\set` 可调参数，一条命令跑完全部：
> ```bash
> # 生产
> cd /home/administrator/news-platform-v8/scripts/news-platform-v8
> docker compose exec -T entity-center-postgres psql -U entity_center -d entity_center -f entity_center_queries.sql
> # 开发 (本地已 clone entity_center)
> docker exec entity-center-postgres psql -U entity_center -d entity_center -f scripts/entity_center_queries.sql
> ```

### 4.1 结构查询（Schema 元数据）

```bash
# 全部表+字段
SELECT c.table_name, c.column_name, c.data_type, c.is_nullable, c.column_default
FROM information_schema.columns c WHERE c.table_schema='entity_center'
ORDER BY c.table_name, c.ordinal_position;

# 索引
SELECT tablename, indexname FROM pg_indexes WHERE schemaname='entity_center';

# 约束
SELECT conrelid::regclass AS tbl, conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint WHERE connamespace='entity_center'::regnamespace;

# 表大小
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables WHERE schemaname='entity_center' ORDER BY pg_total_relation_size(relid) DESC;

# 行数（n_live_tup 为统计估算值，小表可能为 0；准确数用 COUNT）
SELECT relname, n_live_tup FROM pg_stat_user_tables WHERE schemaname='entity_center' ORDER BY relname;
```

### 4.2 数据查询命令

```bash
# ── 实体查询 ──
# 按类型+搜索（关键词可中文/英文，匹配 canonical 或别名）
SELECT e.canonical_name, t.code AS type, e.importance, e.status
FROM entity_center.entities e
JOIN entity_center.entity_types t ON t.id = e.entity_type_id
WHERE t.code = 'COMPANY' AND e.canonical_name ILIKE '%nvidia%'
ORDER BY e.importance DESC LIMIT 20;

# 别名查询（含中文，如 "宁德时代" → CATL）
SELECT e.canonical_name, a.alias, a.language, a.alias_type, a.is_preferred
FROM entity_center.entity_aliases a
JOIN entity_center.entities e ON e.id = a.entity_id
WHERE a.alias = '宁德时代';

# 标识符查询（kb_v1_id / ticker / iso_alpha3 / isin）
SELECT e.canonical_name, i.scheme, i.identifier
FROM entity_center.entity_identifiers i
JOIN entity_center.entities e ON e.id = i.entity_id
WHERE i.scheme = 'ticker' AND i.identifier = 'NVDA';

# 按重要性排序（Top 重要实体）
SELECT canonical_name, importance, importance_source
FROM entity_center.entities WHERE status = 'active'
ORDER BY importance DESC LIMIT 50;

# 实体数按类型聚合
SELECT t.code, COUNT(*) FROM entity_center.entities e
JOIN entity_center.entity_types t ON t.id = e.entity_type_id
WHERE e.status = 'active' GROUP BY t.code ORDER BY 2 DESC;

# 查某实体的完整画像（meta 全部字段）
SELECT canonical_name, t.code AS type, s.name AS subtype, importance,
       e.metadata, e.description
FROM entity_center.entities e
JOIN entity_center.entity_types t ON t.id = e.entity_type_id
LEFT JOIN entity_center.entity_subtypes s ON s.id = e.subtype_id
WHERE e.canonical_name = 'NVIDIA';

# ── 关系查询 ──
# 某实体的全部关系（出入站, 1 跳）
SELECT f.canonical_name AS from_entity, rt.name AS relation,
       t.canonical_name AS to_entity, er.confidence
FROM entity_center.entity_relationships er
JOIN entity_center.entities f ON f.id = er.from_entity_id
JOIN entity_center.entities t ON t.id = er.to_entity_id
JOIN entity_center.relation_types rt ON rt.id = er.relation_type_id
WHERE er.status = 'active' AND (f.canonical_name = 'NVIDIA' OR t.canonical_name = 'NVIDIA')
ORDER BY er.confidence DESC;

# 关系数按类型聚合
SELECT rt.code, COUNT(*) FROM entity_center.entity_relationships er
JOIN entity_center.relation_types rt ON rt.id = er.relation_type_id
WHERE er.status = 'active' GROUP BY rt.code ORDER BY 2 DESC;

# 全部国家→国家关系（如战略合作/制裁/冲突）
SELECT f.canonical_name, rt.code, t.canonical_name
FROM entity_center.entity_relationships er
JOIN entity_center.entities f ON f.id = er.from_entity_id
JOIN entity_center.entities t ON t.id = er.to_entity_id
JOIN entity_center.relation_types rt ON rt.id = er.relation_type_id
WHERE er.status = 'active'
  AND rt.code IN ('STRATEGIC_PARTNERSHIP','POLITICAL_HOSTILITY','ECONOMIC_SANCTION','MILITARY_CONFLICT')
ORDER BY rt.code, f.canonical_name;

# 公司→行业归属
SELECT f.canonical_name AS company, t.canonical_name AS industry
FROM entity_center.entity_relationships er
JOIN entity_center.entities f ON f.id = er.from_entity_id
JOIN entity_center.entities t ON t.id = er.to_entity_id
JOIN entity_center.relation_types rt ON rt.id = er.relation_type_id
WHERE er.status = 'active' AND rt.code = 'INDUSTRY_AFFILIATION' LIMIT 30;

# ── 候选审批/观测/证据 ──
# 待审批候选（pending）
SELECT c.id, f.canonical_name, rt.code, t.canonical_name, c.confidence, c.evidence_text
FROM entity_center.relation_candidates c
JOIN entity_center.entities f ON f.id = c.from_entity_id
JOIN entity_center.entities t ON t.id = c.to_entity_id
JOIN entity_center.relation_types rt ON rt.id = c.relation_type_id
WHERE c.status = 'pending' ORDER BY c.created_at DESC;

# 关系时点观测（某关系的动态）
SELECT o.effect, o.polarity, o.event_at, o.confidence, ac.code AS action
FROM entity_center.relation_observations o
JOIN entity_center.actions ac ON ac.id = o.action_id
WHERE o.relationship_id = '<关系UUID>'
ORDER BY o.event_at DESC;

# ── 审计/变更 ──
# 最近审计（实体/关系变更）
SELECT target_type, operation, field, new_value, created_at
FROM entity_center.audit_log ORDER BY created_at DESC LIMIT 50;

# sync_outbox 积压检查（同步镜像滞后排查）
SELECT COUNT(*) AS backlog FROM entity_center.sync_outbox WHERE synced_at IS NULL;

# ── Ontology ──
# 关系类型清单（含方向/权重/实体类型白名单）
SELECT code, name, weight, directionality, event_enabled, from_entity_type_ids, to_entity_type_ids
FROM entity_center.relation_types WHERE status = 'active' ORDER BY weight DESC;

# 动作→关系映射（context 词表）
SELECT rt.code AS relation, ac.code AS action, ram.context, ram.weight
FROM entity_center.relation_action_mappings ram
JOIN entity_center.relation_types rt ON rt.id = ram.relation_type_id
JOIN entity_center.actions ac ON ac.id = ram.action_id
WHERE rt.code = 'ECONOMIC_SANCTION';
```

---

## 5. 主库 news_intel（另一套 postgres :5432）

```bash
docker compose exec -T postgres psql -U news_admin -d news_intel -c \
"SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position;"
```

---

## 相关
- [entity-center-v1.md](entity-center-v1.md) — 完整实现报告
- [entity-center-entity-graph-v1-dev-plan.md](entity-center-entity-graph-v1-dev-plan.md) — Entity Graph 开发任务书
- [entity-center-v1-audit-2026-08-16.md](entity-center-v1-audit-2026-08-16.md) — 基线审计
