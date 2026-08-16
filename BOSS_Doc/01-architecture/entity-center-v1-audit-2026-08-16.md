# Entity Center V1 基线符合度审计报告

> **审计日期**: 2026-08-16 · **审计基准**: 《Entity Center V1 总体规划与设计规范》(2026-08-12 锁定基线)
> **审计对象**: `entity_center` 仓库 (Schema/API/同步) + `search-engine-v2` (集成) + VPS 生产库实测
> **方法**: 3 路并行代码审计 (Schema / API / 同步与集成) + 生产数据核对

---

## 1. 总体结论

| 维度 | 完成度 | 摘要 |
|------|:---:|------|
| 阶段 1 Schema | ✅ 95% | 20/20 表/视图全建, 少量细节缺失 |
| 阶段 2 初始数据 | ✅ 100% | 16 类型/17 关系/139 动作/137 映射全齐 |
| 阶段 3 同步服务 | ✅ 80% | 触发器+daemon+mirror 齐全, 缺全量校验/daemon 调度存疑 |
| 阶段 4 核心查询 API | ✅ 85% | resolve/relations/observation 齐, 性能 SLO 未达 |
| 阶段 5 集成接入 | ❌ 10% | **L1/L2/Extraction/Aggregator 全部未接入** |
| 阶段 6 治理界面 | ✅ 95% | 审批/merge/config/CSV/前端全齐 |
| 阶段 7 验证 | ✅ 80% | 37 pytest + Golden Set 100%, 性能/一致性未达标 |
| §8 信号与智能 | ❌ 5% | **Signal Engine / Evolution / stats 任务全部缺失** |

> **一句话**: 数据基础设施 (Schema/种子/治理/同步) 高度完成甚至超前, 但 **§8 信号与智能 + §11 对外集成 两大块几乎空白** —— 当前 entity_center 是"独立的数据中心/管理台", 尚未成为"接入新闻流水线的信号基础设施"。

---

## 2. ✅ 已完成（符合规范）

### 2.1 Schema（§6）— 20/20 表/视图
全部表存在, 字段/约束/索引与规范一致:
`entity_types` `entity_subtypes` `entities`(复合FK+merged) `entity_aliases` `entity_identifiers` `relation_types`(GIN) `actions` `relation_action_mappings` `entity_relationships`(chk_superseded+uq_active_relation partial unique) `relation_evidence` `relation_observations`(effect六枚举+复合索引) `v_symmetric_relations`视图 `relation_candidates`(effect默认confirm) `relation_multihop_rules`(GIN) `relation_observation_stats` `sync_outbox` `config_versions`(唯一active) `data_revisions` `audit_log`

### 2.2 种子数据（§13）— 100%
| 种子 | 规范 | 实际 |
|------|:---:|:---:|
| entity_types | 16 | 16 ✅ |
| entity_subtypes | 覆盖5类 | 27 ✅ |
| relation_types | 17 | 17 ✅ |
| actions | 139 | 139 ✅ |
| relation_action_mappings | N:N | 137 ✅ |
| config_defaults | 5项 | 5项 ✅ |

YAML 权威源 (ontology/*.yaml) + `generate_seed_sql.py` (--check CI 校验) 齐全。

### 2.3 UUIDv7（§6.1）
`app/uuidv7.py` 纯应用层生成 (RFC 9562, 毫秒内单调), 全部主键 `default=uuid7`, 无 server_default。种子用 `seed_uuid()` 确定性派生。

### 2.4 核心查询 API（阶段4）
- **Entity Resolution** (§11.4): `POST /api/v1/resolve` — candidates+selected+status(resolved/ambiguous/unresolved), `ambiguous_threshold=0.60` 经 config_versions 可覆盖 (60s TTL)
- **Relation Lookup / Observation Query / Symmetric View**: 实体关系/详情/观测/timeline/7d30d统计(实时回退)/批量, directed 走表 + symmetric 走视图 (无重复计数)

### 2.5 治理流程（阶段6）— 完整实现
- **Candidate 审批 §7.2 全链路**: Evidence 创建 → `FOR UPDATE SKIP LOCKED` 并发 → terminate 分支(关系inactive+valid_to) / 其他(追加observation+EWMA α=0.3) / 新建(关系+observation+stats) → **每候选独立 data_revision**
- **Entity Merge §9.4**: aliases/identifiers 迁移 + **链式合并禁止校验** (target 已 merged 拒绝)
- **config_versions 全生命周期**: current / switch / versions / rollback (唯一 active 部分唯一索引 + 先归档后插入)
- **角色矩阵基础**: `require_role` + ROLE_ORDER, JWT level→role 映射

### 2.6 PG→SQLite 同步（阶段3/§10）
- 触发器 10 表全覆盖 (AFTER INSERT/UPDATE/DEACTIVATE/DELETE → sync_outbox, 同事务 ACID)
- daemon 30s 轮询 + FOR UPDATE SKIP LOCKED + 失败重试 (sync_attempts/last_error/阈值告警)
- Mirror schema 类型映射 (TIMESTAMPTZ→TEXT, GIN→不迁移)
- 全量重建 + 延迟监控脚本

### 2.7 验证（阶段7）
- **37 pytest** (uuidv7 5 / resolution 11 / approve flow 5 / upsert 5 / candidate ingest 1 / relation query 1 / governance 4 / api 5) 覆盖核心流程
- **Golden Set 80 条 100%** (生产验证, 含 71/71 治理后回归)

---

## 3. ⚠️ 部分完成 / 有缺陷

| # | 项 | 现状 | 差距 |
|---|----|------|------|
| 1 | **性能 SLO** (§11.4) | resolve P99<50ms / 消歧<200ms 仅为文档目标+脚本测量 | dev 环境 P50≈634ms (VPS 网络 RTT 主导), **未达标、无运行时强制/监控** |
| 2 | **角色矩阵** (§9.1) | `require_operator/llm_agent/readonly` 已定义但**零使用**; 实际全部 admin-only | 注释声称 operator 可审批但实际不能; llm_agent 角色未落地 |
| 3 | **Semantic Extraction 入口** (§7.1) | `POST /api/v1/relations/candidates` 实现接收 (effect默认confirm/对称标准化/from==to拒绝/1h幂等) | 仅"接收", **识别逻辑在 EC 外部**; **端点无鉴权** (匿名可提交) |
| 4 | **stats 表结构** (§8.1) | 表只有 7d/30d计数+trend_score | **缺 R/I/C_historical/Δ_historical 列**, §8.1 Pre-Fetch 输入在数据层无法满足 |
| 5 | **sync 触发器 DEACTIVATE 窄化** (§10) | 只对 status→'inactive' 产生 tombstone | entities 的 merged/deprecated、ontology 的 deprecated 只产生 UPDATE (mirror 保留) |
| 6 | **Mirror 二级索引** (§10.5) | mirror 只建 PRIMARY KEY | partial unique `uq_active_relation` 等**未迁移为普通索引** |
| 7 | **生产 daemon 调度** (§10) | 代码齐全, 镜像产物证明曾运行 | **无计划任务注册证据** (仅 .bat 注释); Docker 容器不含 daemon; 持续运行存疑 |

---

## 4. ❌ 未完成（规范要求但缺失）

### 4.1 §8 信号与智能 — 几乎全部空白（最大差距区）
| 项 | 规范 | 现状 |
|----|------|------|
| **Signal Engine** (Pre-Fetch + Post-Extract) | §8.1/8.2 | **零代码** — 无 signal service, 仅 README 目录注释残留 |
| **Evolution** (不存储) | §8.3 | **零代码** |
| **relation_observation_stats 5min 后台更新** | §8.1 | **零代码** — trend_score 仅新建时写死 0.50; `trend_score_multiplier`/`min_entity_importance_for_signal`/`event_enabled_min_weight` 均为**死配置** |

### 4.2 §11 集成接入 — 全部未接入（search-engine-v2 零引用）
| 集成点 | 规范 | 现状 |
|--------|------|------|
| **L1 Scorer** (§11.1) | Mention→Resolution→importance | ❌ scorer.py 用本地 JSON 打分, 不调 resolve; **resolve 输出不含 importance** |
| **L2 Router** (§11.2) | Pre-Fetch Signal → Tier A/B/C | ❌ router.py 走本地 enhancers, 只有 `/relationships/batch` 数据源, 无 Signal 层 |
| **Semantic Extraction 统一入口** (§11.3) | 识别→Candidate | ❌ fact_pipeline 走本地 canonicalizer + KB V1 YAML 自产自销, **不 POST candidates** |
| **Event Aggregator** | 接入 | ❌ aggregator 用本地 canonicalizer/KB |
| **SQLite Mirror 消费端** | §10 供本地读取 | ❌ search-engine-v2 无任何代码读 `entity_center_mirror.db` |
| **公开 config/ontology 只读端点** | §11 前置 | ❌ config/ontology 全在 `/admin/*` (需 admin JWT), 外部 L1/L2 无法读 |

> **证据**: search-engine-v2/scripts 下 `entity_center / relation_candidates / create_candidate` **零命中**。entity_center 仅通过 nginx 反代 + docker-compose + 前端 admin 页接入, **与新闻流水线无数据交互**。

### 4.3 其他缺失
- **每周全量一致性校验** (§10.4): 只有重建, 无 PG↔SQLite row-count/checksum 比对
- **`valid_to` 仅 terminate 的 DB 级 CHECK**: 仅应用层约定 (规范未强制, 记为缺口)

---

## 5. 🟢 超前完成（超出规范基线的实现）

| # | 超前项 | 说明 |
|---|--------|------|
| 1 | **`ontology_versions` 表 + 版本快照/回滚** | 规范只要求 config_versions; 实际额外为每个 ontology 条目建版本历史+changes 明细+回滚 (含种子基线 v0) |
| 2 | **CSV 导出/导入** (实体/关系/动作/类型/子类型) | 规范 §13 只要求 seed SQL; 实际实现完整 CSV 双向 + 冲突报告/强制/只允许新增字段规则 |
| 3 | **实体数据批量导入** | 规范"空库启动+人工审视", 实际经脚本导入 **759 实体 / 2803 别名 / 220 标识符** (15国/105公司/49政府/40国际机构/26领导人/116军队/63城/191国/30商品/17货币/36金融机构...) — 用户驱动, 但偏离"空库启动"原则 |
| 4 | **前端治理增强** | 实体画像弹窗(图谱拓扑+时间线)/批量审批/多选排序/仅显示已选/导出导入按钮/实体编辑弹窗 — 规范阶段6只要求 Entity Profile+Admin 审核 |
| 5 | **config_versions 列表+回退** | 规范只要求 current/switch; 实际补 versions 列表(含 snapshot 参数显示)+rollback 端点+前端记录列表/回退按钮 |
| 6 | **create_candidate 幂等去重 (1h)** | 同 article+from/to/type/action 1h 去重, 返回已存在候选 |
| 7 | **批量审批独立 data_revision + 幂等** | 重复审批返回已审批状态, 不重复创建 |
| 8 | **audit JSON Patch + polarity×effect 一致性校验** | 超出规范 §9.3 基础审计要求 |

> **超前完成的定位**: 除 #3 (数据导入) 外, 其余均属合理增强, 不违反规范约束。规范 §12 "不做"清单 逐项核对均未违反 (Signal 不存DB ✅ / L1 只读 ✅ / 不解析新闻 ✅ / 无链式合并 ✅)。

---

## 6. 偏离规范项（需要关注）

| # | 偏离 | 严重 | 说明 |
|---|------|:---:|------|
| 1 | **迁移 0001/0002 漂移** | 高 | `0001` 用 `create_all()` 全量建表 (含 ontology_versions), `0002` 再显式 `create_table("ontology_versions")` → **全新库按序迁移会在 0002 报 already exists** |
| 2 | **`config_versions.status` 缺 CHECK** | 低 | 其余 status 列均有 CHECK, 该列只有部分唯一索引, 写法不一致 |
| 3 | **`relation_action_mappings.context` 可空** | 低 | 规范 context 受控词表应非空; 可空导致 NULL 绕过 UNIQUE (种子恒 default, 影响有限) |
| 4 | **`ACTOR_TYPES` 常量未用** | 低 | 定义了但未用于任何约束 |
| 5 | **候选提交端点无鉴权** | 中 | `/api/v1/relations/candidates` 匿名可提交, 与 §9.1 "llm_agent 可创建" 角色未落实矛盾 |
| 6 | **Docker 部署不含 sync daemon** | 中 | 镜像只跑 uvicorn API, 同步需外部计划任务 |

---

## 7. 生产数据实测（2026-08-16）

```
entities 759 | aliases 2803 | identifiers 220 | active_rels 23 | candidates 23 | observations 23 | outbox_pending 0
```

- 关系库仅 23 条 (来自 KB entity-network.json 导入), **几乎无自然观测增长** — 因 §11 集成未接入, 新闻流水线不产生 candidate
- outbox 0 积压 = 同步链路空闲 (无新写入)

---

## 8. 建议优先级

| 优先级 | 项 | 理由 |
|:---:|-----|------|
| P0 | **L1/L2/Semantic Extraction 集成** (§11) | 让 entity_center 真正接入流水线, 关系库才有数据增长 |
| P0 | **Signal Engine + stats 后台任务** (§8) | 规范核心智能层, 当前零代码; 先建 stats 任务再实现 signal |
| P1 | **候选提交端点鉴权** | 安全缺口, 匿名可写 |
| P1 | **resolve 返回 importance** | L1 契约 (§11.1) 前置依赖 |
| P1 | **公开 config/ontology 只读端点** | 外部读取前置 |
| P2 | **每周全量一致性校验** | §10 缺失项 |
| P2 | **迁移 0001/0002 漂移修复** | 全新环境部署会失败 |
| P2 | **性能 SLO 达标/监控** | 需同机部署 + 运行时 P99 上报 |
| P3 | context 非空 / config_versions CHECK / Mirror 二级索引 / DEACTIVATE 宽化 | 细节收尾 |

---

## 相关
- [entity-center-v1.md](entity-center-v1.md) — 完整实现报告
- 设计基线: 《Entity Center V1 总体规划与设计规范》(锁定 2026-08-12)
- 相关: [[entity-center-v1]] [[entity-management-analysis]]
