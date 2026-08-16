# Entity Graph V1 Implementation Report

> **完成日期**: 2026-08-17 · **commit**: entity_center `f5105eb`
> **范围**: 在不破坏现有 Entity Center V1 前提下增加"实体↔实体关系网络"能力 · 全量 ADD ONLY

---

## 1. 环境检查

| 项 | 值 |
|----|----|
| 项目路径 | `C:\Users\ChangHui\...\entity_center`（独立 git, main 分支） |
| 数据库 | `entity_center`（生产 :5432 compose / 开发 :5433 独立容器 / 测试 entity_center_test） |
| Schema | `entity_center` |
| Migration | Alembic（0001 → 0002 → **0003**） |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| 测试 | pytest asyncio（**49 项全过**） |

## 2. 当前 Entity Center 状态（V1 冻结，未改）

```
entities 759 · aliases 2803 · identifiers 220
entity_types 16 · entity_subtypes 27 · relation_types 17 · actions 139 · relation_action_mappings 137
新增后 active_rels 69 · candidates 若干 · observations 若干
```

**核心冻结表 21 表 + 1 视图 0 修改**（ADD ONLY 原则，全部复用）。

## 3. 新增表（1 张，ADD ONLY）

**`action_entity_role_rules`**（migration 0003）— 动作主体/对象实体类型+语义角色约束
- 列: id · action_id(FK actions) · subject_entity_type_id(FK entity_types) · object_entity_type_id(FK entity_types) · subject_role · object_role · priority · allowed · description · status · created_at · updated_at
- 约束: UNIQUE(action_id, subject_type, object_type) · CHECK status · 3 索引

**未新建**（按基线裁决复用现有）：`entity_relations`→`entity_relationships` · `entity_relation_evidence`→`relation_evidence` · `relation_entity_type_rules`→`relation_types.from/to_entity_type_ids`

## 4. Migration

- `migrations/versions/0003_action_entity_role_rules.py` — 生产/开发/测试库均已 `alembic upgrade head` 执行成功（0002→0003）

## 5. 新增代码

| 层 | 文件 | 内容 |
|----|------|------|
| Model | `app/models/ontology.py` + `__init__.py` | `ActionEntityRoleRule` |
| Service | `app/services/graph.py` | `validate_entity_relation`（存在性/类型约束/自环/重复/时间）· `validate_action_role` · `get_outgoing/get_incoming/get_graph`(1-hop) |
| API | `app/api/graph.py` + `main.py` | GET `/api/v1/entities/{id}/relations/{outgoing,incoming}` · GET `/api/v1/entities/{id}/graph` · POST `/api/v1/relations/validate` |

**关键复用（未动冻结表）**：
- 关系实例 → 现有 `entity_relationships`（含 uq_active_relation / superseded_by）
- 证据 → 现有 `relation_evidence` + `relation_observations.evidence_id`
- 类型约束 → 现有 `relation_types.from/to_entity_type_ids`（JSONB）落地校验
- 审批流 → 现有 `relation_candidates` + `approve_candidate`（FOR UPDATE / EWMA / 独立 data_revision）

## 6. Seed Rules

`scripts/seed_action_role_rules.py` — **11 条**动作角色规则（生产+开发+测试）：
ACQUIRES/APPOINTS/EXPORT_CONTROL/SANCTIONS/SHIPS/SIGNS_CONTRACT/SUCCEEDS/SUPPLIES/TRAINS 各类型约束。
⚠ 方案引用的 `INVESTS`/`PARTNERS_WITH` 动作不存在于 139 冻结集 → **记录缺口不新增**（基线 §八）。

## 7. Seed Relations

`scripts/seed_base_relations.py` — **46 条**基础关系（经 create_candidate → approve 完整审批流）：
SUPPLY_CHAIN(16) · STRATEGIC_PARTNERSHIP(11) · MARKET_COMPETITION(8) · TRADE_RESTRICTION(4) · ECONOMIC_SANCTION(3) · POLITICAL_HOSTILITY(2) · CORPORATE_CONTROL(2) · MAJOR_INVESTMENT(3) · MILITARY_CONFLICT(1)
生产 **active 关系 23 → 69**。类型非法 5 条被正确拒绝（如 China→CORPORATE_CONTROL→SMIC 因 COUNTRY 不在白名单）。

## 8. 测试

| 项 | 数 |
|----|----|
| 新增 test_graph.py | **12 项**（类型规则/角色/创建/非法拒绝/重复/方向/自环/graph 邻居/历史可见） |
| 基线回归 | 37 项 → **49 项全过** |

**测试隔离修复**：`test_config_switch` 发布 ewma_alpha=0.2 后不恢复 → 污染后续 EWMA 测试 → 末尾加恢复默认配置（alpha=0.3）。

## 9. 回归测试

完整 pytest **49 passed**（0 failed），Tailscale 下耗时 ~22min（网络延迟主导）。

## 10. 数据库验证

- FK: action_entity_role_rules → actions/entity_types ✓
- INDEX: idx_action_role_action/subject/object + uq_action_role_rule ✓
- UNIQUE: (action_id, subject_type, object_type) ✓
- COUNT: action_entity_role_rules 11 · entity_relationships active 69 ✓

## 11. 性能

- Graph 1-hop 查询：生产实测返回 <100ms（10 邻居内，SQL 走 uq_active_relation/索引）
- 种子/测试慢因 Tailscale RTT（~300ms/往返），非查询问题
- V1 仅 1-hop（API depth 接受 1/2，2-hop 聚合待 V2）

## 12. 风险

| 风险 | 状态 |
|------|------|
| 冻结表被改 | ✅ 0 修改（ADD ONLY 验证） |
| 动作 INVESTS/PARTNERS_WITH 缺口 | ⚠ 记录，前端标签映射到现有动作（ACQUIRES/SIGNS_CONTRACT） |
| 2-hop 未真正实现 | ✅ V1 仅 1-hop，符合基线 |
| 种子关系 action 语义（如 MARKET_COMPETITION→WARNS） | ⚠ 观测动作语义不完全贴合，可后续调优 |

## 13. 未完成事项

1. `relation_source_rules`（🟡 推荐）未实现 — 留待 Signal Engine 阶段
2. 2-hop Graph 聚合（depth=2）未实现 — V2
3. 种子关系 ~46 条 < 目标 100-300（实体约束 + 审批流成本，后续可按需扩充）
4. 前端 Entity 画像接入 graph 端点（outgoing/incoming 展示）— 待前端开发
5. 生产 daemon 调度无消费者（镜像只读，仅配置定义路径）

## 14. 下一阶段建议（仅建议）

1. **前端接入**: 画像弹窗补 outgoing/incoming/graph 标签页（复用现有关系图谱）
2. **relation_source_rules + Signal**: 接入后做来源置信度门控
3. **扩充关系**: 按需新增高价值实体关系（金融机构/政府/更多公司），经候选审批流
4. **2-hop**: 实现 depth=2 邻居聚合（V2）

---

## 相关
- [开发任务书](entity-center-entity-graph-v1-dev-plan.md) · [开发基线](entity-center-entity-graph-v1-dev-baseline.md) · [PHASE 0/1 审计](entity-center-entity-graph-v1-phase0-1-audit.md) · [数据库 Schema](entity-center-database-schema.md)
