# 问题记录跟踪表 (Issue Tracker)

> 版本: v1.0 · 2026-08-07 · **状态: 🟢 启用**
> 定位: **全项目唯一的问题注册表** — 所有问题（bug/坑/待改进/待决策项）及其生命周期在此统一记录管理。
> 原则: 发现问题先登记（doc-first），状态变更随同一 git commit 更新；`05-troubleshooting/` 专题文档与 `references/*-fixes.md` 为**归档详情库**，本表为主索引。
> 相关: [cron-debug.md](cron-debug.md) · [rss-quarantine.md](rss-quarantine.md) · [实体链路分析](entity-management-pipeline-analysis.md)

---

## 1. 主表（Master Table）

> 每问题一行，按发现日期倒序；状态用徽章。点击 ID 跳转 §4 详情节。

| ID | 发现 | 严重 | 分类 | 标题 | 模块/文件 | 状态 | 根因 | 修复/方案 | 验证 | 关闭 |
|----|------|:----:|------|------|-----------|:--------:|------|-----------|:----:|:----:|
| [ISS-20260807-001](#iss-20260807-001) | 08-07 | P1 | 实体库 | 配置中心实体管理↔Pipeline 回流断裂 | `entities.py`/`knowledge_base` | 🟡 待决策 | 两套 KB 不互通，UI 只写 entity-network | 方案A 双向同步 | — | — |
| [ISS-20260807-002](#iss-20260807-002) | 08-07 | P2 | 实体库 | 事件/Fact 实体 ID 双轨 | `aggregator.py:1195`/`canonicalizer.py` | 🟡 待决策 | 事件本地 ID vs Fact KB V1 ID | 方案B 统一 loader | — | — |
| [ISS-20260807-003](#iss-20260807-003) | 08-07 | P2 | 实体库 | backfill CANON_NAME 硬编码 canonical 漂移 | `backfill_entity_model.py:29-54` | 🟡 待决策 | 三处 canonical 手工维护 | 方案C 收敛 entity_alias | — | — |
| [ISS-20260807-004](#iss-20260807-004) | 08-07 | P3 | 实体库 | 关系库在生产中几乎不使用 | `relations.yaml`/`entity_relationship` | 📋 观察 | 关系仅展示层 + REL_ 白名单 | 评估关系图谱接入生产 | — | — |
| [ISS-20260711-101](#iss-20260711-101) | 07-11 | P1 | Pipeline | db.close() 后查询崩溃 | `news_intel/pipeline.py:141-150` | ✅ 已关闭 | close 后仍执行查询 | 统计移到 close 前 | 运行通过 | 07-11 |

---

## 2. 生命周期状态机

```
NEW(待处理) ─→ ANALYZING(分析中) ─→ FIXING(修复中) ─→ VERIFYING(验证中) ─→ CLOSED(已关闭)
     │               │                  │                  │
     └───────────────┴──────────────────┴──────────────────┴── 回归复现 → REOPENED(重新打开) ──→ 回到 ANALYZING
CLOSED ──稳定一段时间──→ ARCHIVED(已归档)  → 细节整理进 05-troubleshooting/ 或 references/ 专题文档
```

| 状态 | 含义 | 进入条件 |
|------|------|----------|
| 🆕 NEW 待处理 | 已登记，未分析 | 发现问题即登记（doc-first） |
| 🔍 ANALYZING 分析中 | 根因定位中 | 开始排查 |
| 🔧 FIXING 修复中 | 根因已定，开发中 | 根因定位完成 |
| 🧪 VERIFYING 验证中 | 回归验证中 | 代码改完（demo.py / test_api / curl） |
| ✅ CLOSED 已关闭 | 验证通过 + 部署 | 验证通过并部署 |
| 🔁 REOPENED 重新打开 | 回归复现 | 关闭后问题重现 |
| 📋 ARCHIVED 已归档 | 长期稳定，详情进专题文档 | 关闭稳定 ≥1 周（或定期整理） |
| 📌 观察 | 待评估的改进/待决策项 | 非缺陷，需后续决策 |

> 附加标记：**待决策**（需人工决策方案的项，挂在 NEW/观察 下）。

---

## 3. 字段设计说明

### 3.1 主表字段

| 字段 | 规则 | 示例 |
|------|------|------|
| **ID** | `ISS-YYYYMMDD-NNN`（发现日 + 三位日序；跨日不重排） | ISS-20260807-001 |
| **发现** | 发现日期 `MM-DD`（完整日期见详情节） | 08-07 |
| **严重** | P0 紧急（阻塞生产/数据丢失）/ P1 高（功能或数据错误）/ P2 中（边界/体验）/ P3 低（改进/待办） | P1 |
| **分类** | 采集 / 评分 / Fact / 聚合 / 推送 / DB / 后端API / 前端 / 配置中心 / 实体库 / 部署 / 性能 / 安全 / 其他 | 实体库 |
| **标题** | 一句话问题描述 | 事件/Fact 实体 ID 双轨 |
| **模块/文件** | 主要涉及代码文件（file:line 优先） | aggregator.py:1195 |
| **状态** | §2 状态机徽章 | 🟡 待决策 |
| **根因** | 一句话根因 | 两套 ID 生成方案 |
| **修复/方案** | 修复内容或方案名 | 方案B 统一 loader |
| **验证** | 验证方式 | demo.py / curl |
| **关闭** | 关闭日期 `MM-DD` | 07-11 |

### 3.2 详情节字段（§4，非平凡问题必填）

| 字段 | 说明 |
|------|------|
| **现象** | 具体症状（错误信息/截图/复现输出） |
| **复现** | 复现步骤或触发条件 |
| **根因** | 深入分析（含代码定位） |
| **解决** | 修复实现 / 待选方案 |
| **验证** | 回归结果（命令 + 输出） |
| **关联** | 相关问题 ID / 文档链接 / commit |

---

## 4. 详情节（Detail）

### ISS-20260807-001 配置中心实体管理↔Pipeline 回流断裂
- **发现**: 2026-08-07 · **严重**: P1 · **分类**: 实体库 · **状态**: 🟡 待决策
- **现象**: 配置中心"实体管理"Tab 编辑实体热生效，但新事件/Fact 的实体解析不变。
- **复现**: 改 entity-network.json 加实体 → 跑 Pipeline → 该实体未被 canonicalizer 解析。
- **根因**: `entities.py` 只读/写 entity-network.json；`canonicalizer.resolve_entity` 只查 `knowledge_base/*.yaml`（KB V1）。两库无回流通道。
- **解决**: 方案A —— `admin_save_entities` 保存时把实体 upsert 进 knowledge_base YAML + 调 generate_kb.py 重建索引（待决策）。
- **验证**: — · **关联**: [entity-management-pipeline-analysis.md](../01-architecture/entity-management-pipeline-analysis.md) §六方案A

### ISS-20260807-002 事件/Fact 实体 ID 双轨
- **发现**: 2026-08-07 · **严重**: P2 · **分类**: 实体库 · **状态**: 🟡 待决策
- **现象**: 云端无法按 entity_id 跨 events/fact_entity 关联实体。
- **根因**: `aggregator._entity_name_to_id`（本地生成）与 Fact 层 KB V1 ID（PERS_/COMP_）两套方案。
- **解决**: 方案B —— `_entity_name_to_id` 改走 `loader.resolve()`（待决策，需全量重聚合）。
- **验证**: — · **关联**: [entity-management-pipeline-analysis.md](../01-architecture/entity-management-pipeline-analysis.md) §六方案B

### ISS-20260807-003 backfill CANON_NAME 硬编码 canonical 漂移
- **发现**: 2026-08-07 · **严重**: P2 · **分类**: 实体库 · **状态**: 🟡 待决策
- **现象**: Trump/Donald Trump、中英名等 canonical 多处不一致（历史出现过 v1.2 丢日本领导人）。
- **根因**: `backfill_entity_model.py:29-54` CANON_NAME 硬编码，与 entity_weights、KB V1 各自漂移。
- **解决**: 方案C —— 以 `entity_alias.yaml` 为唯一权威，backfill 运行时读 loader（待决策）。
- **验证**: — · **关联**: [entity-management-pipeline-analysis.md](../01-architecture/entity-management-pipeline-analysis.md) §六方案C

### ISS-20260807-004 关系库在生产中几乎不使用
- **发现**: 2026-08-07 · **严重**: P3 · **分类**: 实体库 · **状态**: 📋 观察
- **现象**: relations.yaml(106)/associations/entity_relationship 仅展示层 + ontology_validator REL_ 前缀白名单。
- **解决**: 评估关系图谱（competitor/investor/part_of）接入事件/fact 生成的路径（待决策是否立项）。
- **验证**: — · **关联**: [entity-management-pipeline-analysis.md](../01-architecture/entity-management-pipeline-analysis.md) §一

### ISS-20260711-101 db.close() 后查询崩溃
- **发现**: 2026-07-11 · **严重**: P1 · **分类**: Pipeline · **状态**: ✅ 已关闭
- **现象**: `sqlite3.ProgrammingError: Cannot operate on a closed database.`
- **根因**: `db.close()` 之后仍执行累计统计查询。
- **解决**: 统计查询移到 `db.close()` 之前（`news_intel/pipeline.py:141-150`）。
- **验证**: 全量运行通过 · **关联**: [pipeline-bugfixes.md](https://github.com/ChangHui666888/search-engine-v2/blob/main/references/pipeline-bugfixes.md)（git 版）

---

## 5. 维护流程（AI 工作流）

```
① 发现问题 → 登记主表一行（NEW，填 ID/日期/严重/分类/标题/模块）→ git commit
② 分析 → 状态改 ANALYZING + 详情节补现象/复现/根因 → git commit
③ 修复 → 状态改 FIXING → 代码完成 → git commit（message 带 ISS-xxxx）
④ 验证 → 状态改 VERIFYING → demo.py / test_api / curl 通过
⑤ 关闭 → 状态改 CLOSED + 填验证结果/关闭日期 → git commit
⑥ 回归复现 → 改 REOPENED → 回 ②
⑦ 归档 → 定期把 CLOSED 稳定项整理进 05-troubleshooting/ 专题或 references/ → 状态 ARCHIVED
```

**提交规范**：问题登记/状态变更与代码修复放**同一 commit**；commit message 含 `ISS-YYYYMMDD-NNN`。

---

## 6. 与现有文档的关系

| 现有文档 | 角色 |
|----------|------|
| `05-troubleshooting/cron-debug.md` / `rss-quarantine.md` | 排障**操作手册**（how-to），不记生命周期 |
| `references/pipeline-bugfixes.md` / `*-fixes-round*.md` | 修复轮次**归档详情库**（现象/原因/修复） |
| `references/entity-kb-changelog.md` | 实体库**变更日志**（数据变更，非问题） |
| `history/过程记录/` | 历史过程归档（不再新增，新问题统一进本表） |
| **本表（issue-tracking.md）** | **唯一主注册表**：状态 + 生命周期 + 详情入口 |

> 新增问题一律先进本表；历史已关闭问题可从上述归档文档**按需迁移**（保持 ID 日期原样）。

---

## 7. 新增条目模板

### 主表行
```
| [ISS-YYYYMMDD-NNN](#iss-yyyymmdd-nnn) | MM-DD | P1 | 分类 | 标题 | 文件 | 🆕 NEW | 根因 | 方案 | — | — |
```

### 详情节
```
### ISS-YYYYMMDD-NNN 标题
- **发现**: YYYY-MM-DD · **严重**: P1 · **分类**: 分类 · **状态**: 🆕 NEW
- **现象**: ...
- **复现**: ...
- **根因**: ...
- **解决**: ...
- **验证**: ...
- **关联**: ...
```
