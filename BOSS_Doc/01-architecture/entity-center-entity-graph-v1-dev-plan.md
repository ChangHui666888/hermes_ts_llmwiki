# Entity Center V1 — Entity Graph 增量开发任务书

> **任务状态**: ✅ **已完成**（2026-08-17，commit entity_center `f5105eb`）
> **创建日期**: 2026-08-16
> **目标**: 在不破坏现有 Entity Center V1 的前提下，增加"实体 ↔ 实体关系网络（Entity Graph）"能力
> **核心原则**: 现有核心表为 Source of Truth，**不改语义 / 不重命名 / 不删除 / 不迁移**（已全部遵守）

---

> ## ✅ 交付摘要（2026-08-17）
> - **新增 1 表**：`action_entity_role_rules`（migration 0003，FK actions+entity_types，11 规则）
> - **新增 API**：`GET /entities/{id}/relations/{outgoing,incoming}` + `GET /entities/{id}/graph` + `POST /relations/validate`
> - **新增校验**：`validate_entity_relation`（复用 `relation_types.from/to_entity_type_ids`）+ `validate_action_role`
> - **种子**：46 条基础关系（生产 active 23→69），经完整审批流
> - **测试**：test_graph.py 12 项 + 基线 37 = 49 全过
> - **冻结表 0 修改**（ADD ONLY）；详见 [实现报告](entity-center-entity-graph-v1-report.md)

---

## 1. 任务定位

已有：
```
Entity → Entity Type → Entity Subtype
Action → Relation Type → Relation ↔ Action Mapping (relation_action_mappings)
```

本次新增：
```
Entity Type → Relation Entity Type Rules      (关系类型↔实体类型约束)
Action → Action Entity Role Rules             (动作主体/对象类型+角色约束)
Entity A + Action + Entity B
    → Relation Type
    → Entity Relation Instance                (entity_relations)
    → Relation Evidence                       (entity_relation_evidence)
```

最终形成 **Entity → Entity Graph**。

## 2. 最高优先级原则

- **不重新设计 / 不推翻现有 Entity Center V1**
- 不修改、重命名、删除、迁移现有核心表：`entity_types` `entity_subtypes` `entities` `entity_aliases` `relation_types` `actions` `relation_action_mappings`
- `relation_types.weight`（关系敏感度）与 `relation_action_mappings.weight`（动作映射权重）**是不同维度，不得合并/删除/重解释**
- 所有数据库变更 **ADD ONLY / NON-DESTRUCTIVE**
- 若发现冲突：停止 → 记录 `CONFLICT/CURRENT/EXPECTED/IMPACT/RECOMMENDATION` → 选兼容方案，不得擅自重构

## 3. 禁止项（保护现有环境）

- 禁止删除表 / DROP DATABASE / DROP SCHEMA / TRUNCATE / 重建 PG
- 禁止修改已有 UUID / canonical_name / 主键 / aliases / importance / entity_type / subtype
- 禁止批量重建实体、修改 relation_types/actions 语义、破坏既有映射
- 禁止占用其他项目端口、停止无关服务、改其他项目配置
- 禁止 destructive migration

## 4. 新增数据模型（6 张候选表）

| 表 | 必须性 | 作用 |
|---|:---:|---|
| `relation_entity_type_rules` | 🔴 必须 | 关系类型允许连接哪些实体类型（source/target type + direction + allowed） |
| `action_entity_role_rules` | 🔴 必须 | 动作主体/对象类型 + 语义角色（acquirer/acquired/sanctioner/target…） |
| `entity_relations` | 🔴 必须 | 关系实例（source→target + relation_type + status + confidence + valid_from/to + first/last_seen） |
| `entity_relation_evidence` | 🔴 必须 | 关系证据（relation_id + evidence_type + source_id + confidence + observed_at） |
| `relation_source_rules` | 🟡 推荐 | 不同来源对关系类型的 min_confidence/priority |
| `relation_type_subtype_rules` | 🟢 后置 | 类型不够精确时再增（V1 不做） |

> ⚠️ 现有 `entity_relationships`（from/to/relation_type/confidence/status/valid_from-to/superseded_by/first-last_seen + uq_active_relation）已是"关系实例"的既有实现。**本次需先审计其与 `entity_relations` 方案的关系，避免双轨**（见 gap 分析：`entity_relations` 方案 ≈ 现有 `entity_relationships`）。

## 5. 关系生成链

```
Entity + Action + Entity
  → Action Entity Role Rule 校验 (subject/object 类型)
  → relation_action_mappings → Relation Type
  → Relation Entity Type Rule 校验 (source/target 类型)
  → Entity Relation 创建
  → Evidence 记录
```

示例：Microsoft + PARTNERS_WITH + OpenAI → STRATEGIC_PARTNERSHIP(COMPANY→COMPANY VALID) → 创建关系。

## 6. 严禁 News 直接当 Relation

保持 `News → Event → Fact → Action → Relation → Entity Relation`，不直绑。同一关系可多证据（多个 News/Event 指向一条 entity_relation）。

## 7. 关系生命周期

支持 `valid_from/valid_to`，历史关系用 valid_to 关闭（不 DELETE），查询 active 时排除过期。

## 8. Confidence 分层（不合并 weight）

1. `relation_types.weight` = 关系敏感度（现有）
2. `relation_action_mappings.weight` = 动作映射权重（现有）
3. `extraction_confidence` = 抽取可信度（观测级）
4. `evidence_confidence` = 证据可信度（证据级）

## 9. 数据库约束与索引

新增表须有 PK/FK/NOT NULL/CHECK/UNIQUE/INDEX。重点索引：
- `entity_relations(source_entity_id) (target_entity_id) (relation_type_id) (source,target)`
- `entity_relation_evidence(relation_id)`
- 规则表 relation_type_id / entity_type_id 索引
- 组合唯一性考虑：`(source, target, relation_type)` + 时间模型（不简单 UNIQUE(source,target)）

## 10. Repository / Service / Validator / API

按现有架构（SQLAlchemy 2.0 async + service 层）增加：
- Model/ORM + Service + Validator + API
- API: create relation / get entity relations / incoming / outgoing / related entities / validate relation / get evidence / graph neighbors
- 路径遵循现有 `/entity-center/api/v1/*` 命名，不强行改架构

## 11. 校验器

`validate_entity_relation(source, relation_type, target)` → VALID / INVALID + reason：
`INVALID_RELATION_TYPE / INVALID_SOURCE_ENTITY_TYPE / INVALID_TARGET_ENTITY_TYPE / RELATION_NOT_ALLOWED / SELF_RELATION_NOT_ALLOWED / DUPLICATE_RELATION / INVALID_DATE_RANGE`

## 12. 种子数据策略

- 第一阶段 100~300 条人工确认的高质量关系（美国/中国/日/韩/台湾/印度/俄 + Top 公司/政府/金融机构/科技/AI/半导体）
- 实体必须已存在、relation/action 必须已存在、类型规则必须允许、有明确来源
- aliases 只能用于 Resolution，**不等于关系证据**

## 13. 禁止过度设计

不做：Neo4j / GraphQL / PageRank / 社区发现 / Embedding / 推理引擎 / 自动关系发现 / 全量历史重建 / 全球关系一次性导入。PostgreSQL = Source of Truth。V1 查询仅 1-hop（必要时 2-hop）。

## 14. 开发阶段（PHASE 0-17）

```
PHASE 0 环境检查 → 1 读 Schema → 2 读 entity_types → 3 读 relation_types
→ 4 读 actions → 5 读 relation_action_mappings → 6 设计 Migration
→ 7 建 4 表 → 8 Validator → 9 Repository → 10 Service → 11 API
→ 12 导入规则 → 13 建立 100-300 关系 → 14 测试 → 15 回归 → 16 性能 → 17 报告
```

## 15. STOP 条件（BLOCKER REPORT）

遇到以下必须停止输出 BLOCKER，不得擅自解决：
relation_types/relation_actions 与设计冲突、Entity/Action 名称不同、DB 无法无损扩展、migration 无法安全执行、发现生产库被其他项目共用、需改核心表才能继续、需删数据才能迁移。

## 16. 验收标准

- 未改核心表语义 / 未删实体 / 未改 relation_types / actions / relation_action_mappings
- 4 张新表建成（entity_relations / evidence / relation_entity_type_rules / action_entity_role_rules）
- 类型约束 / 动作角色约束 / Validator / CRUD / Graph 查询 / Evidence / 时间有效 / Duplicate 控制 / Direction 正确
- 100-300 条真实关系验证成功
- 现有测试全过 + migration 安全 + 未占用其他端口

---

## 相关
- [entity-center-v1.md](entity-center-v1.md) — 现有实现
- [entity-center-relation-graph-gap-analysis-2026-08-16.md](entity-center-relation-graph-gap-analysis-2026-08-16.md) — 方案 gap 分析
- [entity-center-v1-audit-2026-08-16.md](entity-center-v1-audit-2026-08-16.md) — 基线审计
