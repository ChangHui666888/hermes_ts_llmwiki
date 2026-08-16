# Entity Center 「关系实例层（Entity Graph）」方案 Gap 分析

> **分析日期**: 2026-08-16 · **性质**: 纯分析，禁止开发
> **分析对象**: 用户提出的"关系语义层→关系实例层"扩展方案 vs 现有 `entity_center` 实现
> **结论先行**: **方案的最大前提（"缺关系实例层"）已经被现有实现覆盖了约 80%**；真正的缺口集中在"规则/约束层未落地"，而不是"缺实例表"。

---

## 1. 方案 6 张新表 vs 现状对照（核心）

| 方案表 | 必须性 | 现状 | 结论 |
|--------|:---:|------|------|
| `entity_relations` | 🔴 | ✅ **已存在 = `entity_relationships`**（from/to_entity_id, relation_type_id, confidence, status, valid_from/to, **superseded_by**, first/last_seen_at, **uq_active_relation 部分唯一索引**） | 无需新增 |
| `entity_relation_evidence` | 🔴 | ⚠️ **已存在 = `relation_evidence`**（source_type/source_url/article_id/evidence_text/extracted_by），经 `relation_observations.evidence_id` 关联到关系 | 基本覆盖，缺直接 relation 外键 + confidence 字段 |
| `relation_entity_type_rules` | 🔴 | ⚠️ **数据已存在** = `relation_types.from_entity_type_ids`/`to_entity_type_ids`（JSONB+GIN，**17 个关系类型种子全填**，如 MILITARY_CONFLICT→[国家,政府,军事组织]）；**但无任何代码校验** | 有数据无逻辑 → 真缺口 |
| `action_entity_role_rules` | 🔴 | ❌ 不存在 | **真缺口** |
| `relation_source_rules` | 🟡 | ❌ 不存在 | 真缺口（推荐级） |
| `relation_type_subtype_rules` | 🟢 | ❌ 不存在 | 方案自认后置，符合 |

**对照结论**: 方案 6 表中 **2 张已存在、1 张数据已存在但未强制**，真正全新的是 3 张规则表（action_entity_role_rules / relation_source_rules / 后置的 subtype_rules）。

---

## 2. 方案其他主张 vs 现状

| 方案主张 | 现状 | 一致? |
|---------|------|:---:|
| "不要建 company_company_relations 等，实体类型决定语义不决定物理表" | ✅ 现有统一 `entity_relationships`，无按类型分表 | ✅ 一致 |
| "relation_actions"（关系↔动作映射） | 实际名 **`relation_action_mappings`**（含 `context` 受控词表 default/financial/military/legal/corporate/diplomatic + weight + priority） | ✅ 概念一致，名不同且更丰富 |
| "News→Event→Fact→Action→Relation，不直接绑定 News" | ✅ `relation_observations.article_id` 为 opaque UUID 零耦合，证据经 observation 关联 | ✅ 一致 |
| confidence = extraction_confidence × action_weight × relation_type_weight | ⚠️ 当前为**单一存在置信 EWMA**（α=0.3，D2 决策），观测不存分解权重 | ⚠️ 设计分歧 |
| 17 个关系类型已够，不新增 | ✅ 一致 | ✅ 一致 |
| 阶段1 人工建稳定基础关系（几千条） | ⚠️ 现有仅 23 条 active 关系（KB 导入），远未达"基础图谱" | ✅ 方向一致 |

---

## 3. 真正的 Gaps（按优先级）

### Gap 1（P0）：关系类型 ↔ 实体类型约束 **未强制** — 方案核心诉求
- **数据在**：`relation_types.from/to_entity_type_ids`（17 全填，种子 `relation_types.yaml`）
- **逻辑缺**：`create_candidate`（app/api/relations.py）与 `approve_candidate`（app/services/upsert.py:51）**均不校验** from/to 实体类型是否落在 `from/to_entity_type_ids` 白名单
- **后果**：无法阻止 "NVIDIA → MILITARY_CONFLICT → TSMC" 这种非法关系进入候选/关系表（方案 §3 场景）
- **方案对应**：`relation_entity_type_rules` —— 但不需要新建表，**复用现有 JSONB 字段 + 在校验点落地**即可（校验 candidate 提交 + 审批两个入口）

### Gap 2（P1）：动作 ↔ 实体角色规则缺失（`action_entity_role_rules`）
- 现状：`actions` 只有 polarity/weight/metadata，无 subject/object 类型与语义角色约束
- 后果：ACQUIRES 的主体/对象无类型约束（无法区分 acquirer/acquired、sanctioner/target）
- 方案价值：约束"谁对谁执行什么动作"，是语义抽取→候选的类型门
- **注意**：方案建议 action 级角色表，但更贴合现状的是**依赖 relation_action_mappings 的 context 消歧 + relation 级 from/to 类型**（动作角色是派生约束，可经 relation→action→mapping→from/to 类型推导）

### Gap 3（P2）：关系来源规则缺失（`relation_source_rules`）
- 现状：evidence.source_type 有枚举（rss/article/llm_inference/manual/api）但**无每关系类型的最小置信度/优先级控制**
- 后果：一篇自媒体文章即可建立 CORPORATE_CONTROL（方案 §12 场景）
- 可在 approve 时校验 source_type→min_confidence，或留待 Signal Engine 阶段

### Gap 4（P2）：confidence 未分解
- 现状：单值 EWMA 存在置信（D2 冻结决策），观测 metadata 可扩展存分解
- 方案：extraction_confidence × action_weight × relation_type_weight
- **建议**：不推翻 EWMA（已冻结），可在 `relation_observations.metadata` 加存 action_weight/relation_type_weight/extraction_confidence 供审计/信号用，关系主置信仍用 EWMA

### Gap 5（后置）：relation_type_subtype_rules
- 方案自认"类型不够精确时再增加"，当前 27 子类型 + type 级约束已够 V1，**同意后置**

---

## 4. 现有实现已具备（方案误以为缺失的）

| 能力 | 现状 |
|------|------|
| **关系实例层** | `entity_relationships` 完整（含时间有效 valid_from/to + superseded_by 历史追溯 + active 唯一约束） |
| **时间演化** | `relation_observations` 六 effect（emerge/strengthen/confirm/maintain/weaken/terminate）+ event_at + timeline 查询 |
| **证据链** | `relation_evidence` + observation.evidence_id（一观测一主证据，V1 符合规范） |
| **审批门** | `relation_candidates` + approve 全流程（FOR UPDATE SKIP LOCKED / terminate / EWMA / 独立 revision） |
| **双向语义** | `v_symmetric_relations` 视图还原 symmetric |
| **关系查询** | 实体关系/详情/观测时间线/7d30d 统计/批量（L2 Pre-Fetch 数据源） |

**结论**: 方案 §2-§14 描述的"关系实例 + 证据 + 时间演化"设计，现有实现已基本全部落地（甚至更完整，如 superseded_by/valid_from 仅 terminate 写入）。

---

## 5. 建议的落地路径（分析结论，非开发）

### 不改表（或最小改）
1. **Gap 1 落地**：在 `create_candidate` + `approve_candidate` 两个入口加 from/to 实体类型白名单校验（读 `relation_types.from/to_entity_type_ids`，null=不限）。**纯逻辑，无需建表**。这是方案最核心的价值点。
2. **Gap 4 落地**：观测 metadata 存分解权重（action_weight/relation_type_weight/extraction_confidence），关系主置信保持 EWMA。

### 可选新增 1 表
3. **Gap 2 落地**：`action_entity_role_rules`（subject_type/object_type/subject_role/object_role）—— 若语义抽取需要严格角色门。**或用更轻的方案**：在 relation_action_mappings 补 role 语义，或依赖 relation 级类型约束推导。

### 后置
4. **Gap 3**：relation_source_rules 留到 Signal Engine 阶段（与 trend_score/stats 一起）
5. **Gap 5**：subtype_rules 后置

---

## 6. 与锁定基线的兼容性

- 方案主张"现有实体表全不改，只新增映射/实例表" — ✅ 与现状一致（entity_relationships 等本就是新增实例表）
- 方案 6 表中有 2 张已存在，不产生冗余（避免建 `entity_relations` 与 `entity_relationships` 并存导致双轨）
- 关系主置信 EWMA 为 D2 冻结决策，不推翻

---

## 相关
- [entity-center-v1.md](entity-center-v1.md) — 完整实现报告
- [entity-center-v1-audit-2026-08-16.md](entity-center-v1-audit-2026-08-16.md) — 基线符合度审计
- 锁定基线: 《Entity Center V1 总体规划与设计规范》
