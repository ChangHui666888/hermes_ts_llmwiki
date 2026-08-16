# Entity Center V1 — 系统开发提示词（权威开发基线）

> **版本**: v1.0 · **定稿日期**: 2026-08-17 · **性质**: Entity Graph 增量开发不可违背约束
> **关联**: [开发任务书](entity-center-entity-graph-v1-dev-plan.md) · [PHASE 0/1 审计](entity-center-entity-graph-v1-phase0-1-audit.md) · [Gap 分析](entity-center-relation-graph-gap-analysis-2026-08-16.md)

---

## 一、项目定位（不可违背）

Entity Center 是新闻情报系统中的**统一实体与关系基础设施**，独立 `entity_center` schema，与 `news_intel` 系统**零耦合**。

核心职责（七大能力）：Identity · Ontology · Resolution · Relation · Observation · Evidence · Signal Input。

## 二、现有 Schema 冻结清单（21 表 + 1 视图，绝对不可修改）

以下表结构、字段、约束、索引已锁定为不可变基线（2026-08-12），**任何新增需求不得修改这些表，只能新增独立表（ADD ONLY）**：

| 表名 | 核心字段 | 状态 |
|------|---------|------|
| `entity_types` | 16 种一级类型 | 冻结 |
| `entity_subtypes` | 27 种子类，复合 FK | 冻结 |
| `entities` | 759 实体，复合 FK(subtype_id,entity_type_id)，merged 状态 | 冻结 |
| `entity_aliases` | 2803 别名，normalized 索引 | 冻结 |
| `entity_identifiers` | 220 标识符，scheme+identifier 唯一 | 冻结 |
| `relation_types` | 17 种关系，from/to_entity_type_ids JSONB，directionality | 冻结 |
| `actions` | 139 种动作，metadata JSONB | 冻结 |
| `relation_action_mappings` | 137 条 N:N 映射，context 受控词表 | 冻结 |
| `entity_relationships` | **关系实例唯一事实表**，Partial Unique Index(uq_active_relation)，superseded_by | 冻结 |
| `relation_observations` | 时点观测，effect 六枚举，metadata JSONB | 冻结 |
| `relation_evidence` | 证据源，source_type | 冻结 |
| `relation_candidates` | 审批队列，status pending/approved/rejected | 冻结 |
| `relation_observation_stats` | 预聚合统计，trend_score | 冻结 |
| `relation_multihop_rules` | 多跳规则，仅建表 | 冻结 |
| `sync_outbox` | 同步变更日志，operation CHECK | 冻结 |
| `config_versions` | 配置版本，唯一 active 部分索引 | 冻结 |
| `data_revisions` | 数据版本，每 Candidate 独立 | 冻结 |
| `audit_log` | 统一审计，JSON Patch | 冻结 |
| `ontology_versions` | Ontology 修改版本，changes JSONB | 冻结 |
| `v_symmetric_relations` | Symmetric 双向还原视图 | 冻结 |

## 三、核心设计原则（19 条语义冻结）

1. Relation Type = 稳定关系语义大类；Action = 可观测行为（独立）
2. Relation Type Weight ≠ Action Weight（敏感度 vs 强度，正交）
3. Relationship Fact 是唯一稳定事实源；Signal/Evolution 派生不写回 `entity_relationships`
4. Relation Observation = 一次时点观测，六种效果：EMERGE/STRENGTHEN/CONFIRM/MAINTAIN/WEAKEN/TERMINATE
5. Polarity = 方向性影响（-1/0/1），Observation 级可覆盖
6. 同一 Entity Pair 允许多个 Relation Type 并存
7. Action ↔ Relation Type = N:N（`relation_action_mappings` + context 消歧）
8. 关系保留方向（from → to）；Symmetric 用 `min(id)→max(id)` 存储 + `v_symmetric_relations` 视图还原
9. LLM/自动抽取只能创建 Candidate，必须经 Admin 审批才能成为 Active Relation
10. Confidence 更新用 EWMA（α=0.3，可配置）
11. 软删除统一状态语义：active/inactive/deprecated/merged
12. `valid_from` 取 `event_at`（实际发生时间）而非 `published_at`
13. Semantic Extraction 是新闻级事实观察的唯一标准化入口
14. Signal 公式不冻结，只冻结输入维度（R, A_eff, I, C, P, Δ）
15. Effective Action Weight = COALESCE(mapping.weight, action.weight)
16. Symmetric Relation 业务代码必须使用视图查询，不得自行拼接双向逻辑
17. Entity Center 不直接解析新闻，所有语义提取经由 Semantic Extraction 统一入口
18. `entity_relationships` 的历史追溯通过 `superseded_by`，status='inactive'
19. 禁止链式实体合并（target.merged_into_entity_id 必须为 NULL）

## 四、明确禁止（V1 不做清单）

- ❌ 新建与 `entity_relationships` 功能重复的关系实例表
- ❌ 新建与 `relation_evidence` + `relation_observations` 重复的证据绑定表
- ❌ 修改 `entity_types` / `entity_subtypes` / `relation_types` / `actions` / `relation_action_mappings` 结构
- ❌ 在 `entity_relationships` 中存储 Signal / Evolution / 事件权重
- ❌ 自动高置信度 LLM 事实直写（必须经 Candidate → Admin 审批）
- ❌ 物理删除任何记录（仅 status='inactive' 软删除）
- ❌ SQLite Mirror 双向写入（严格只读）
- ❌ 链式实体合并
- ❌ 新增 Action / Relation Type（V1 冻结 139 / 17）
- ❌ 冻结 Signal 计算公式（由 Signal Engine 策略化）

## 五、新增表规范（ADD ONLY）

若需扩展，只能新增独立表，且必须满足：
1. 外键必须引用现有冻结表（如 `action_id → actions.id`）
2. 不得与现有表功能重叠（关系实例必须用 `entity_relationships`，证据必须用 `relation_evidence`）
3. 必须通过 `relation_candidates` 进入审批流，不得直接写 `entity_relationships`
4. 必须记录 `audit_log`：Ontology 变更记 `config_version`，数据变更记 `data_revision`
5. 配置参数必须纳入 `config_versions.config_snapshot`（不硬编码）
6. 同步表需评估是否创建 `sync_outbox` 触发器（当前 Mirror 无消费者，可暂缓）
7. 必须提供 Alembic 迁移脚本 + pytest 测试

## 六、审批流程强制路径

任何关系实例的创建/变更必须走：
```
LLM/抽取/共现/模式匹配
  ↓
relation_candidates (status='pending')
  ↓
Admin 审批 (FOR UPDATE SKIP LOCKED 并发控制)
  ↓
[存在 active] → 追加 observation + EWMA confidence / terminate → inactive
[不存在] → 新建 entity_relationships + observation + evidence + stats
  ↓
data_revision (每 Candidate 独立) → audit_log → sync_outbox (触发器) → SQLite Mirror
```

## 七、代码规范

- ORM: SQLAlchemy 2.0 async + asyncpg
- 迁移: Alembic（当前 0002，新增为 0003+）
- 测试: pytest asyncio，37 项基线测试不得破坏
- UUID: 应用层 `uuidv7()`，全部主键 `default=uuid7`
- 时间戳: `TIMESTAMPTZ`，全部 `DEFAULT now()`
- JSONB: 复杂结构存 JSONB，需建 GIN 索引若用于过滤
- 状态: 统一 CHECK 约束，禁止物理删除

## 八、常见陷阱（必须避免）

| 陷阱 | 正确做法 |
|------|---------|
| "需要一张新表存关系实例" | 复用 `entity_relationships`（已存在，含 uq_active_relation / superseded_by） |
| "证据应该直接绑到关系" | 复用 `relation_evidence` + `relation_observations.evidence_id`（解耦设计） |
| "需要类型约束表替代 JSONB" | V1 先读取 `relation_types.from/to_entity_type_ids` JSONB + 应用层校验，V2 再评估独立表 |
| "动作不够，新增 INVESTS/PARTNERS_WITH" | V1 冻结 139 Action，前端显示标签映射到现有 Action（如 ACQUIRES / SIGNS_CONTRACT） |
| "Signal 公式可以写回 confidence" | Signal 是运行时派生，不写回；`entity_relationships.confidence` 是 EWMA 存在置信度 |
| "valid_to 可以人工写任期结束" | `valid_to` 仅由 `effect='terminate'` 的 Observation 触发自动写入 |
| "Symmetric 关系存两条记录" | 统一 `min(id)→max(id)` 存储，查询用 `v_symmetric_relations` |

## 九、数据量参考（2026-08-17）

entities 759 | aliases 2803 | identifiers 220 | active_rels 23 | candidates 23 | observations 23
entity_types 16 | entity_subtypes 27 | relation_types 17 | actions 139 | relation_action_mappings 137
config_versions 4 | ontology_versions 229 | sync_outbox 4905

## 十、文档索引

- 基线规范：《Entity Center V1 总体规划与设计规范》(2026-08-12 锁定)
- 实现报告：`entity-center-v1.md`
- 审计报告：`entity-center-v1-audit-2026-08-16.md`
- 数据库 Schema：`entity-center-database-schema.md`

---

## ⚡ 本基线与 PHASE 0/1 审计冲突项的解决方案（已确认）

| 审计 CONFLICT | 基线裁决 | 开发动作 |
|---|---|---|
| CONFLICT-1 `entity_relations` | §四 ❌禁止重复表 → **复用 `entity_relationships`** | 不建表，Graph 查询读 entity_relationships + 视图 |
| CONFLICT-2 `relation_entity_type_rules` | §八 → **V1 用现有 `from/to_entity_type_ids` JSONB + 应用层校验** | 在 create_candidate + approve 落地校验逻辑，不建表 |
| CONFLICT-3 `entity_relation_evidence` | §四 ❌禁止重复证据表 → **复用 `relation_evidence` + observations.evidence_id** | 不建表 |
| 动作缺口 INVESTS/PARTNERS_WITH | §八 → **前端标签映射到现有动作** | 不新增动作，用 ACQUIRES/SIGNS_CONTRACT 等 |

**V1 实际新增范围收敛为**：应用层类型/角色校验 + Graph 查询 API + 100~300 种子关系（经审批流）+ 迁移/测试。
