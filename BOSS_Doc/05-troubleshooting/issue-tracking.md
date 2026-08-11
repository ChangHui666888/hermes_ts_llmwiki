# 问题记录跟踪表 (Issue Tracker)

> 版本: v1.0 · 2026-08-07 · **状态: 🟢 启用**
> 定位: **全项目唯一的问题注册表** — 所有问题（bug/坑/待改进/待决策项）及其生命周期在此统一记录管理。
> 原则: 发现问题先登记（doc-first），状态变更随同一 git commit 更新；`05-troubleshooting/` 专题文档与 `references/*-fixes.md` 为**归档详情库**，本表为主索引。
> 相关: [cron-debug.md](cron-debug.md) · [rss-quarantine.md](rss-quarantine.md) · [实体链路分析](entity-management-pipeline-analysis.md)

---

## 1. 主表（活跃 / 待处理 + 近例）

> 当前开放问题主视图（活跃/待处理/待决策/观察）；**已关闭历史问题统一在 §8 历史迁移（git）**。状态用徽章，点击 ID 跳转 §4 详情节。

| ID                                    | 发现    | 严重  | 分类       | 标题                                                                        | 模块/文件                                   |   状态   | 根因                                                                                               | 修复/方案                                                   |                             验证                             |  关闭   |
| ------------------------------------- | ----- | :-: | -------- | ------------------------------------------------------------------------- | --------------------------------------- | :----: | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------- | :--------------------------------------------------------: | :---: |
| [ISS-20260807-001](#iss-20260807-001) | 08-07 | P1  | 实体库      | 配置中心实体管理↔Pipeline 回流断裂                                                    | `entities.py`/`knowledge_base`          | 🟡 待决策 | 两套 KB 不互通，UI 只写 entity-network                                                                   | 方案A 双向同步                                                |                             —                              |   —   |
| [ISS-20260807-002](#iss-20260807-002) | 08-07 | P2  | 实体库      | 事件/Fact 实体 ID 双轨                                                          | `aggregator.py:1195`/`canonicalizer.py` | 🟡 待决策 | 事件本地 ID vs Fact KB V1 ID                                                                         | 方案B 统一 loader                                           |                             —                              |   —   |
| [ISS-20260807-003](#iss-20260807-003) | 08-07 | P2  | 实体库      | backfill CANON_NAME 硬编码 canonical 漂移                                      | `backfill_entity_model.py:29-54`        | 🟡 待决策 | 三处 canonical 手工维护                                                                                | 方案C 收敛 entity_alias                                     |                             —                              |   —   |
| [ISS-20260807-004](#iss-20260807-004) | 08-07 | P3  | 实体库      | 关系库在生产中几乎不使用                                                              | `relations.yaml`/`entity_relationship`  | 📋 观察  | 关系仅展示层 + REL_ 白名单                                                                                | 评估关系图谱接入生产                                              |                             —                              |   —   |
| [ISS-20260807-006](#iss-20260807-006) | 08-07 | P3  | Fact     | Fact 抽取硬编码参数需配置化                                                          | `fact_pipeline.py:39-42/132/252`        | 📋 观察  | GLiNER 阈值/Qwen max_tokens/FACT_PROMPT 写死                                                         | 挂到配置中心「AI增强」Tab                                         |                             —                              |   —   |
| [ISS-20260808-001](#iss-20260808-001) | 08-08 | P3  | 聚合       | 新分散源聚合覆盖偏低 (0 marked)                                                     | `aggregator.py`                         | 📋 观察  | 新增源每源文章少, 未达 event_threshold(60)                                                                 | 观察/调低阈值或查 fused 指纹                                      |                             —                              |   —   |
| [ISS-20260808-002](#iss-20260808-002) | 08-08 | P2  | Pipeline | 存活源但文章=0 — sync 批次积压致 70+ 大源文章未推送                                         | `news_intel/sync.py`                    | 📋 观察  | 游标批次 LIMIT 积压 + 旧文在水印前                                                                           | 提高 LIMIT/按源均衡/查 AP 采集                                   |                             —                              |   —   |
| [ISS-20260808-002](#iss-20260808-002) | 08-08 | P2  | 采集       | rss-scanner 优化后时效下降 (4缺陷)                                                 | `hermes-cron/rss-scanner.py`            | ✅ 已关闭  | tier门控+304不更新last_scan+非2xx记OK+bk共用state                                                         | 修复①-④+--full开关+follow_redirects                         |                    限流233篇 / --full 140篇                    | 08-08 |
| [ISS-20260808-003](#iss-20260808-003) | 08-08 | P2  | 配置       | 配置中心 ~61 源死链(404/403) 静默0抓                                                | `rss.feeds` 配置中心                        | 🆕 待处理 | URL失效/Nitter封禁/防爬403                                                                             | 配置中心批量禁用/换URL                                           |                             —                              |   —   |
| [ISS-20260808-004](#iss-20260808-004) | 08-08 | P1  | 聚合       | 同主体跨主题错并 — Trump(伊朗战争)+Trump(古巴) 并成1事件                                    | `aggregator.py` `fingerprint_score`     | 🆕 待处理 | 同主体绕过主题硬约束, 实体对重叠≥60即并                                                                           | 内容相似度门 + coherence 下限拒绝                                 |                             —                              |   —   |
| [ISS-20260808-005](#iss-20260808-005) | 08-08 | P2  | 评分       | 英文关键词子串误标系统性存在（election⊂Selection/nuclear⊂模型名/market⊂marketing 等）         | `scorer.py` `_kw_match_mode`            | 🆕 待处理 | 点状修补 word_boundary, 无系统性碰撞扫描                                                                     | 系统性子串碰撞检测 → 批量转 word_boundary                           |                       500篇/5000篇测试暴露                       |   —   |
| [ISS-20260808-006](#iss-20260808-006) | 08-08 | P2  | 评分       | 评分整体偏保守 — A=0/B=4.6%/平均27.9, LLM增强覆盖低                                     | `scorer.py` `score_article`             | 🟡 待决策 | impact不累加 + 词边界去虚高 + 来源分主导                                                                       | 降B级门槛/impact适度累加/权威源加权                                  |                             —                              |   —   |
| [ISS-20260808-007](#iss-20260808-007) | 08-08 | P3  | 聚合       | 中文粗分词致 velocity Jaccard 低 + 跨语言零匹配                                        | `scorer.py` `_make_fingerprint_set`     | 🟡 待决策 | 中文整串1token + 无跨语言归一                                                                              | jieba/实体短语指纹 + KB实体ID跨语言                                |                             —                              |   —   |
| [ISS-20260808-008](#iss-20260808-008) | 08-08 | P3  | 性能       | velocity O(n²) — 5000篇需123s                                               | `scorer.py` `compute_velocity`          | 📋 观察  | 全量两两比较                                                                                           | 指纹倒排索引 + 时间桶                                            |                             —                              |   —   |
| [ISS-20260808-009](#iss-20260808-009) | 08-08 | P1  | 采集       | sync 游标卡死 — 391篇同刻时间戳占满LIMIT致文章不再入库/推送                                    | `sync.py` `_fetch_batch`                | ✅ 已关闭  | scanner批量写入同秒时间戳, `created_at>=水印`游标被同刻重复占满                                                      | 复合游标(created_at,id) + 旧水印严格大于                           |                 catchup 1254篇, 水印推进到23:22                  | 08-08 |
| [ISS-20260809-010](#iss-20260809-010) | 08-09 | P1  | 聚合       | 增量聚合漏选 article_url — 新事件 evidence/source_chain 空 URL + 去重折叠               | `auto-pipeline.py`/`aggregator.py`      | ✅ 已关闭  | 增量 SELECT 缺 `rr.article_url`, 聚合器 `a.get("url","")` 恒空 → View 按钮/完整链路缺失 + evidence/timeline 去重折叠 | SELECT 补 `rr.article_url as url` (与 reaggregate_all 对齐) | 生产 fused 只读 100事件: evidence url 99/100 + chain url 100/100 | 08-09 |
| [ISS-20260810-012](#iss-20260810-012) | 08-10 | P1  | Fact     | Fact Schema 升级 — 单fact→facts[] + Action(type/status/polarity) + 值/短语实体化门控 | `fact_pipeline.py`/`canonicalizer.py`   | 🔧 修复中 | 生产后处理破坏 Qwen 输出(动作落OTHER/客体切碎ENT_垃圾); 单fact丢多事实; 值($0.22)被实体化                                    | facts[]+结构化SAO+action状态/极性+实体门控                         |                             —                              |   —   |
| [ISS-20260811-013](#iss-20260811-013) | 08-11 | P2  | 配置       | tier 阈值配置漂移 — `ai.tier_a_threshold=95` 未被 scorer 消费(硬编码 A≥90/B≥60/C<60)   | `scorer.py:348`                         | 🆕 待处理 | 配置中心有 `ai.tier_a_threshold=95`, scorer 未读, 用硬编码 90/60                                            | scorer 读配置中心阈值                                          |                             —                              |   —   |
| [ISS-20260811-014](#iss-20260811-014) | 08-11 | P1  | Fact     | VPS facts/batch 推送全量绕过验证门 — REJECT 垃圾进 fact 表                             | `fact_pipeline.py` main 推送              | 🆕 待处理 | 验证门仅用于 A/B+聚合, 推送 /internal/facts/batch 送全量 payloads                                             | 推送前过 validate_facts, 只送 PASS/REPAIR                     |                             —                              |   —   |
| [ISS-20260811-015](#iss-20260811-015) | 08-11 | P2  | Fact     | Fact AI 提取失败静默降级 — 无重试/无失败指标/永久丢失                                         | `fact_pipeline.py` qwen_fact            | 🆕 待处理 | qwen_fact 异常→返回[], 文章无 fact 且被标记不重抽                                                              | AI 失败重试 + 失败指标 + 重抽队列                                   |                             —                              |   —   |
| [ISS-20260811-016](#iss-20260811-016) | 08-11 | P3  | 实体       | 中文人名类型标签错误(高市早苗→CTRY, 应 Person)                                           | `canonicalizer.py`                      | 🆕 待处理 | KB miss 后类型猜测未覆盖中文人名                                                                             | CJK 人名启发式(姓氏库/称谓)                                       |                             —                              |   —   |
| [ISS-20260811-017](#iss-20260811-017) | 08-11 | P3  | Fact     | LLM 垃圾短语主体(Negotiation with Iran 当 subject)                               | `fact_pipeline.py`                      | 🆕 待处理 | LLM 提取把整句/短语当 subject, 未过质量门                                                                     | 主体短语质量门(复用 _is_value_phrase)                            |                             —                              |   —   |
| [ISS-20260811-018](#iss-20260811-018) | 08-11 | P3  | 聚合       | 增量聚合已标记文章不重聚(事件不刷新)                                                       | `auto-pipeline.py` Step 4.5             | 📋 观察  | 只聚 event_id 为空文章, 标记后不再重聚                                                                        | 需重聚合机制(按需 re-aggregate)                                 |                             —                              |   —   |
| [ISS-20260811-019](#iss-20260811-019) | 08-11 | P3  | 文档       | CLAUDE.md 文档漂移(RSS 98源→实际196; 评分缺价值奖励描述)                                  | `CLAUDE.md`                             | ✅ 已关闭 | 文档快照未随 扩源/评分奖励 更新                                                                                | 更新 CLAUDE.md 到实际(196源/价值奖励)                             | CLAUDE.md 7b8fca5 已修(196源/价值奖励)                          | 08-11 |
| [ISS-20260711-001](#iss-20260711-001) | 07-11 | P1  | Pipeline | db.close() 后查询崩溃                                                          | `news_intel/pipeline.py:141-150`        | ✅ 已关闭  | close 后仍执行查询                                                                                     | 统计移到 close 前                                            |                            运行通过                            | 07-11 |

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

### ISS-20260807-006 Fact 抽取硬编码参数需配置化
- **发现**: 2026-08-07 · **严重**: P3 · **分类**: Fact · **状态**: 📋 观察
- **现象**: GLiNER 实体阈值(0.35)、Qwen noThink `max_tokens=300`、`FACT_PROMPT` 写死在代码里，配置中心无法热调（改「AI 增强」Tab 不影响事实抽取）。
- **根因**: `fact_pipeline.py:39-42`（GLINER_MODEL/FALLBACK/FACT_PROMPT）、`:132`（max_tokens=300）、`:252/309`（GLiNER threshold=0.35）为硬编码常量，未走 config loader。
- **解决**: 方案——新增 `ai.fact_gliner_threshold` / `ai.fact_qwen_max_tokens` / `ai.fact_prompt` 挂到配置中心「AI 增强」Tab，`fact_pipeline.py` 改走 `_agg_cfg`/loader 读取（待评估是否立项）。
- **验证**: — · **关联**: [entity-workflow-usage.md](../01-architecture/entity-workflow-usage.md) §2 环节2 配置参数

### ISS-20260808-002 存活源但文章=0 — sync 批次积压致大源文章未推送
- **发现**: 2026-08-08 · **严重**: P2 · **分类**: Pipeline · **状态**: 📋 观察
- **现象**: `/admin/sources` 显示 116 源存活，但 **77 源 article_total=0**，含 AP/CNN/NBC/ABC/NYT/NPR 等大源；Al Jazeera/CBS/France24 正常。
- **根因**: ① AP 采集=0（scanner 未抓到，URL/隔离待查）；② CNN 50 篇全是水印(09:34:55)前旧文 → sync 永远跳过；③ NYT 水印后有 25 篇，但 sync 按 `created_at ASC + LIMIT` 分批，积压源(PNAS84/SeekingAlpha82/Dev.to79...)占满批次 → NYT 等被挤出未同步。
- **解决**: 提高 sync LIMIT / 按源均衡 / 补同步水印前旧文 / 查 AP 采集（待研究）。
- **验证**: — · **关联**: [monitoring.md](../04-config/monitoring.md)（看板 ③抓取/源健康）

### ISS-20260808-001 新分散源聚合覆盖偏低
- **发现**: 2026-08-08 · **严重**: P3 · **分类**: 聚合 · **状态**: 📋 观察
- **现象**: RSS 升级(196 源)后，某轮 `AGGREGATE: 0 marked`（300 unassigned/50 facts 0 标记）；24h 仍新建 17 事件，整体正常。
- **根因**: 新增大量分散 feed 每源文章少，可能未达 `aggregate.event_threshold`(60)。
- **解决**: 观察后续覆盖；若持续偏低可调低阈值或检查 fused 指纹（待评估）。
- **验证**: — · **关联**: [feed-registry-v4.md](../04-config/feed-registry-v4.md) §9

### ISS-20260808-002 rss-scanner 优化后时效下降 (4缺陷)
- **发现**: 2026-08-08 · **严重**: P2 · **分类**: 采集 · **状态**: ✅ 已关闭
- **现象**: 5 项优化(perf `af3087f`)后单轮新增 0–2 篇，老文件 `bk/rss-scanner.py` 全扫 14 篇 —— 疑"无法获取"。
- **根因**: ①tier 门控冷源 60min 积压；②304 源不更新 `last_scan` 恒到期；③非 2xx(404/403) 被记 OK 永不隔离；④bk 与生产共用 state/report 互相覆盖；另 httpx 0.28 默认不跟重定向致 NYT 等 301 源 0 抓。
- **解决**: 修复①-④ + `follow_redirects=True` + 新增 `--full` 不限流开关 + tier 间隔 config 可配（`rss.tier_*_interval`）。
- **验证**: 限流跑新增 **233** 篇 / `--full` 全量 **140** 篇（远超老文件 14）；死链自动隔离生效。详情 [rss-scanner-rate-limit.md](../04-config/rss-scanner-rate-limit.md)。

### ISS-20260808-004 同主体跨主题错并 — Trump(伊朗战争) + Trump(古巴) 并成 1 事件
- **发现**: 2026-08-08 · **严重**: P1 · **分类**: 聚合 · **状态**: 🆕 待处理
- **现象**: `EVT-20260807-082`（http://100.107.117.23/events/EVT-20260807-082）把两篇不相关文章并成 1 事件，summary 用 `|` 硬拼接两个故事。doc_refs 实锤：① "Trump says war 'can't go much longer' – what's the latest on talks?"（Al Jazeera，伊朗-美国战争谈判）② **"Cuba: What does Trump really want?"**（France 24，古巴）。coherence=65、confidence=0.57（偏低）。
- **复现**: 任何两篇**主体相同但故事不同**的文章（如特朗普谈伊朗 + 特朗普谈古巴）在 24h 窗口内聚合。
- **根因**: `aggregator.py` `fingerprint_score()` 基于**实体对重叠**（subject/object/action/topic/event_type）。两篇 subject 同为 Trump → **主题硬约束被绕过**（`if primary_topic 不同 and subject 不同 → 0`，subject 相同时不阻断）；再叠加 object(United States)/action/event_type 相同 → 分数 65 ≥ `EVENT_THRESHOLD(60)` → Phase 1 并入同一事件。anchor（`subject|action|object|primary`）若完全一致更直接 +100 强制合并。**无 coherence 下限拒绝机制**——coherence < MERGE_THRESHOLD 只降 impact（line 893），不拆事件。
- **解决**: 待方案——① 加**内容相似度门**：同主体但主主题不同的成员需标题词集 Jaccard ≥ 阈值才允许并入（防 Trump+伊朗 与 Trump+古巴 错并）；② coherence 下限拒绝：coherence < 55 的事件拆分/标记；③ anchor 100 分强制合并加内容校验；④ 事件内标题多样性检查。
- **验证**: — · **关联**: [pipeline-l0-l7-rules.md](../01-architecture/pipeline-l0-l7-rules.md) L5 事件聚合 / [event-dedup-fix](../event-dedup-fix.md)

### ISS-20260808-005 英文关键词子串误标系统性存在
- **发现**: 2026-08-08 · **严重**: P2 · **分类**: 评分 · **状态**: 🆕 待处理
- **现象**: `election`⊂`Selection`（LLM 论文 "Agent Selection" 误判政治）、`nuclear`⊂`NuclearDiffusion`（ML 模型名误判核能）、`war`⊂`hardware`/`forward`、`EV`⊂`every`/`event`、`oil`⊂`soil`、`market`⊂`marketing`、`rate`⊂`corporate` 等同类风险仍潜伏。
- **复现**: 5000 篇测试（政治关键词 94→32 因 election 修复）。
- **根因**: `_kw_match_mode` 仅点状修补（`_WORD_BOUNDARY_FORCE`），未对全部英文关键词做子串碰撞检测。
- **解决**: 系统性子串碰撞扫描 → 碰撞词批量转 word_boundary（S1，见 [scoring-v2-analysis.md](scoring-v2-analysis.md)）。
- **验证**: — · **关联**: [scoring-v2-analysis.md](scoring-v2-analysis.md) §二.2

### ISS-20260808-006 评分整体偏保守
- **发现**: 2026-08-08 · **严重**: P2 · **分类**: 评分 · **状态**: 🟡 待决策
- **现象**: 5000 篇 A=0、B=4.6%(232)、C=95.4%，平均 27.9 中位 20，最高 87。
- **根因**: impact 跨类取最高不累加 + 词边界修复去虚高 + 来源分(~15)占比主导。
- **解决**: 待决策——①B 级门槛 60→50（+4% LLM 覆盖）②impact 跨类适度累加 ③来源权威度加权。
- **验证**: — · **关联**: [scoring-v2-analysis.md](scoring-v2-analysis.md) §二.3

### ISS-20260808-007 中文粗分词致 velocity 判同偏低
- **发现**: 2026-08-08 · **严重**: P3 · **分类**: 聚合 · **状态**: 🟡 待决策
- **现象**: "美联储宣布降息" 为 1 token，相似中文标题 Jaccard 0.33<0.5 漏判；中英同事件零匹配。
- **根因**: `_make_fingerprint_set` 中文整串 1 token + 无跨语言实体归一。
- **解决**: 待决策——jieba/实体短语指纹 + KB 实体 ID 跨语言匹配（L1）。
- **验证**: — · **关联**: [scoring-v2-analysis.md](scoring-v2-analysis.md) §二.6

### ISS-20260808-008 velocity O(n²) 性能
- **发现**: 2026-08-08 · **严重**: P3 · **分类**: 性能 · **状态**: 📋 观察
- **现象**: 5000 篇 velocity 计算 123s。
- **根因**: `compute_velocity` 全量两两比较。
- **解决**: 指纹词倒排索引 + 30min 时间桶（L2）。
- **验证**: — · **关联**: [scoring-v2-analysis.md](scoring-v2-analysis.md) §二.7

### ISS-20260808-009 sync 游标卡死 — 同刻时间戳并列致文章不再入库/推送
- **发现**: 2026-08-08 · **严重**: P1 · **分类**: 采集 · **状态**: ✅ 已关闭
- **现象**: VPS `/admin/sources` 近几小时文章=0。实际 VPS 最新文章 02:08，本地 sync 水印 `rss_last_synced_at` 卡在 `09:34:55` 不动，pipeline 每轮 `SYNC+SCORE: 0 ok`。
- **复现**: scanner 批量写入导致 **391 篇共享 `09:34:55` 同秒时间戳**；`_fetch_batch` 查询 `created_at >= 水印 ORDER BY created_at ASC LIMIT 200` 被同刻重复文章占满 → 水印推进到 max=同刻（无进展）→ 卡死，永远取不到其后新文章。
- **根因**: `created_at >= watermark` 单值游标无法跨过同刻并列时间戳（游标 tie bug）。scanner 批量写入用同一秒时间戳是诱因。
- **解决**: `_fetch_batch` 改**复合游标 (created_at, id)** `WHERE (created_at > ?) OR (created_at = ? AND id > ?) ORDER BY created_at,id`；`set_sync_watermark` 存 `"created_at|id"`；旧格式水印(仅时间)回退 `created_at > w_time` 跨过同刻。同步 prod + catchup **追平 1254 篇**（A=36/B=94/C=1124），水印推进到 23:22:43。
- **验证**: 修复后 `_fetch_batch` 返回 200 篇全为新文章（0 重复）；VPS 待下一轮 pipeline 抓取推送后恢复入库。
- **关联**: [rss-scanner-rate-limit.md](../04-config/rss-scanner-rate-limit.md) · [cron-debug.md](cron-debug.md)

### ISS-20260809-010 增量聚合漏选 article_url — 新事件 evidence/source_chain 空 URL + 去重折叠
- **发现**: 2026-08-09 · **严重**: P1 · **分类**: 聚合 · **状态**: ✅ 已关闭
- **现象**: `EVT-20260809-140` 等所有近期新事件详情页 Evidence / Evolution / Information Flow 区块无 "View Source →" / "View →" 按钮、链路短且不可点；旧事件 `EVT-20260728-218` 完整。API 对比: 新事件 `evidence[].url` 0/1、`source_chain[].url` 0/2；旧事件 5/5、10/10。
- **根因**: 增量入口 `auto-pipeline.py` Step 4.5 的 SELECT 漏 `rr.article_url`, 传给 `aggregate_events()` 的文章 dict 无 `url` 键 → `aggregator.py:1068/1101/1154` 的 `a.get("url","")` 恒空; 且 `url` 是 evidence(1069)/timeline(1111) 去重键, 空串折叠致各只留 1 条。全量 `reaggregate_all.py` 含 url, 故旧事件/全量重算正常。
- **解决**: `auto-pipeline.py` SELECT 追加 `rr.article_url as url`（与 reaggregate_all 对齐）；`cron-sync.py`/`test_aggregator.py` 同步修复。仅修复前进（存量空 URL 事件不回填）。
- **验证**: 生产 profile 已同步 (sync diff=0) + 只读验证: ①默认聚合 6/6 事件带 url; ②真实 fused 模式(50 facts + 全量未分配) 100 事件: evidence url 99/100、chain url 100/100、evidence≥2 91/100, 样本 `EVT-20260809-396` evidence 5/chain 9/timeline 12 全带 url, 形状与 `EVT-20260728-218` 一致。新事件 URL 随下一轮 pipeline 生效。
- **关联**: [data-flow-fields.md](../01-architecture/data-flow-fields.md) L5

### ISS-20260810-012 Fact Schema 升级 — 单fact→facts[] + Action(type/status/polarity) + 值/短语实体化门控
- **发现**: 2026-08-10 · **严重**: P1 · **分类**: Fact · **状态**: 🔧 修复中
- **现象**: 生产提取全对仅 6%(50 篇抽样), Qwen 原始 38%。`rejects/tests/tops/calls` 动作被落 OTHER; 客体 `Trump's 15-point Gaza Plan` 被切碎成 `ENT_15_POINT_GAZA_PLAN`; `$0.22`/`81st anniversary`/`AI chip fears ease` 被错误实体化。单篇只出 1 条 fact, 多事实文章(如 OpenAI acquire + integrate)丢事实。
- **根因**: `canonicalize_action` 词表外动词全落 OTHER; `split_entities`+`resolve_entity` 为任何短语生成临时 `ENT_` id; 单 fact 结构限制。
- **解决**: ① Fact Schema 升级为 `facts[]`(每条 subject/action/object/time/location 结构化 + confidence/evidence); ② Action 增加 `type/status/polarity`(含 UNKNOWN); ③ Object 实体化门控(值/数字/日期/短语不再生成 ENT_ 实体); ④ fact_validator Quality Gate(PASS/REPAIR/REJECT, 不重新推理); ⑤ Event Relevance Filter(非事件→facts=[]); ⑥ aggregator 只消费 PASS/REPAIR。
- **验证**: **P0 Gate1(结构)+Gate2(Eligibility) PASS**; **P1 FACT CLOSE(2026-08-10)**: 70篇(50英+20中)验证 **错误Fact进聚合=0**(中文 eligibility 修复后)、结构正确;精度 baseline 总体 S60/A50/O52/T48/L47(90/85 降为长期指标)。生产提取方案冻结: 逐篇并行+路由(CJK→Qwen/Gemma)+Context B+max_tokens1500。契约 `references/fact-schema-v2.md` §11。**生产部署待定**。
- **下一阶段**: Entity Grounding(最小可用)→ A/B Event Aggregator(高精度 A / 宽松 B)。
- **P1 规划**: Time/Location 规范化(LLM+规则) · Confidence 拆分 · C-tier Rule Engine 完整实现 · Qwen Context 优化(扩上下文, A/B 已验证+2~11pp) · Entity Grounding(KB miss→Candidate) · Action 语义归一(verb+negation+modal+status) · 达标 90/85/85/90/90。
- **关联**: [pipeline-l0-l7-rules.md](../01-architecture/pipeline-l0-l7-rules.md) L4.5 · [data-flow-fields.md](../01-architecture/data-flow-fields.md) L4 · `references/fact-schema-v2.md`

### ISS-20260811-013 tier 阈值配置漂移 — `ai.tier_a_threshold=95` 未被 scorer 消费
- **发现**: 2026-08-11 · **严重**: P2 · **分类**: 配置 · **状态**: 🆕 待处理
- **现象**: 配置中心 `ai.tier_a_threshold=95`, 但代码 grep 无消费; scorer 分级用硬编码 `total≥90→A / ≥60→B / else→C`(`scorer.py:348-353`)。
- **根因**: scorer tier 阈值写死, 未接配置中心 `score.*/ai.tier_a_threshold`。
- **解决**: 让 scorer 读配置中心阈值(A/B/C 分界), 或删无用配置键。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节2

### ISS-20260811-014 VPS facts/batch 推送全量绕过验证门 — REJECT 垃圾进 fact 表
- **发现**: 2026-08-11 · **严重**: P1 · **分类**: Fact · **状态**: 🆕 待处理
- **现象**: `fact_pipeline.py` main() 推 `/internal/facts/batch` 送**全量 payloads**(含验证门 REJECT 的垃圾), 而 A/B+聚合只用 PASS/REPAIR。实证: 20篇→facts/batch ok=23, A/B 仅 _passed=16(7 条 REJECT/未达标仍入库)。
- **根因**: 验证门(fact_validator)未在推送层应用; REPAIR 修复后版本也未用于推送。
- **解决**: 推送前 `validate_facts(payloads)`, 只送 PASS/REPAIR(修复后版本)。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节4/6

### ISS-20260811-015 Fact AI 提取失败静默降级 — 无重试/无失败指标/永久丢失
- **发现**: 2026-08-11 · **严重**: P2 · **分类**: Fact · **状态**: 🆕 待处理
- **现象**: `qwen_fact` 任何异常→返回 `[]`(无重试); 该文章无 fact 且被 `assign_articles_to_event` 标记 → 下轮不重抽 → **永久无 AI Fact**。无失败指标, pipeline.log 不区分"AI失败"与"本来无fact"。
- **根因**: 单次调用无重试; 失败不标记/不统计; 增量标记机制导致不重抽。
- **解决**: AI 失败重试(1-2次) + 失败计数指标 + 失败文章重抽队列。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节4

### ISS-20260811-016 中文人名类型标签错误(高市早苗→CTRY, 应 Person)
- **发现**: 2026-08-11 · **严重**: P3 · **分类**: 实体 · **状态**: 🆕 待处理
- **现象**: `resolve_entity("高市早苗")` → `CTRY_TAKAICHI_SANAE`(type=Country, 应 Person)。id 一致可匹配, 但类型标签错 → 画像/图谱分类错误。
- **根因**: KB miss 后类型猜测未覆盖中文人名。
- **解决**: CJK 人名启发式(姓氏库/称谓 判断 Person)。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节4

### ISS-20260811-017 LLM 垃圾短语主体(Negotiation with Iran 当 subject)
- **发现**: 2026-08-11 · **严重**: P3 · **分类**: Fact · **状态**: 🆕 待处理
- **现象**: A 事件出现 "Negotiation with Iran"/"Observation of Iran" 短语主体。
- **根因**: LLM 提取把整句/短语当 subject, 未过主体质量门。
- **解决**: 主体短语质量门(复用 `_is_value_phrase`), 并入 validator。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节4

### ISS-20260811-018 增量聚合已标记文章不重聚(事件不刷新)
- **发现**: 2026-08-11 · **严重**: P3 · **分类**: 聚合 · **状态**: 📋 观察
- **现象**: Step 4.5 只聚 `event_id` 为空文章, 聚合后标记; 已标记文章不再重聚 → 若新 fact 到, 事件不刷新。
- **根因**: 增量语义(防重复事件)牺牲了事件刷新。
- **解决**: 按需 re-aggregate 机制(对关键实体/事件), 或事件刷新策略。
- **验证**: — · **关联**: `pipeline-e2e-review-2026-08-10.md` 环节5

### ISS-20260811-019 CLAUDE.md 文档漂移(RSS 98源→实际196; 评分缺价值奖励描述)
- **发现**: 2026-08-11 · **严重**: P3 · **分类**: 文档 · **状态**: ✅ 已关闭
- **现象**: CLAUDE.md 写 "RSS(98源)"、"五维评分", 实际 196 源、评分含 v2.2 价值奖励(0-30)。
- **根因**: 文档快照未随 扩源/评分奖励 更新; 报告曾据此出错(98源)。
- **解决**: 更新 CLAUDE.md 到实际(196源/价值奖励/Step0-6)。记忆文件同步: cron-flow 98→196, MEMORY.md 197→196。
- **验证**: CLAUDE.md `7b8fca5`(196源/价值奖励/tier硬编码说明); 记忆已核对。 · **关联**: `pipeline-e2e-review-2026-08-10.md`

### ISS-20260808-003 配置中心 ~61 源死链(404/403) 静默0抓
- **发现**: 2026-08-08 · **严重**: P2 · **分类**: 配置 · **状态**: 🆕 待处理
- **现象**: 修复②上线首轮暴露 61 个 HTTP 4xx（此前全部被静默记为 OK、0 抓、永不隔离）。含 18 Nitter 全 403 + 27 个 404（White House/AFP/新华网/央视/Anthropic/Google AI…）+ 11 个 403（SEC/Politico/OpenAI/Economist/NASA…）。
- **根因**: 配置中心 `rss.feeds` 中 URL 失效 / Nitter 实例封禁 / 目标站防爬 403。
- **解决**: 待配置中心「源列表」批量禁用/换 URL（`enabled=false` 或更新 url），config-agent 60s 同步后生效（预计活跃 192→~130）。
- **验证**: — · **关联**: [rss-scanner-rate-limit.md](../04-config/rss-scanner-rate-limit.md) §6

### ISS-20260711-001 db.close() 后查询崩溃
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

---

## 8. 历史已关闭（git 提交迁移，2026-07-29 ~ 08-07）

> 从 `search-engine-v2` 仓库 git 历史提取的 fix/修复/回退类提交，全部为**已关闭**状态（代码已提交修复）。
> 编号按发现日期自动续编（08-07 从 005 起，避开 §1 当前种子 001-004）。标题取自 commit message；分类/严重为关键词自动推断，可按需人工修正。
> 追溯: `git show <hash>` 查看具体修复内容；更早（<07-29）的问题归档在 `references/*-fixes.md`。

| ID | 发现 | 严重 | 分类 | 标题（commit message） | commit | 状态 |
|----|------|:----:|------|------------------------|:------:|:----:|
| ISS-20260807-005 | 08-07 | P2 | 后端API | fix: 后端启用应用级日志 → docker logs 可见审计 (2026-08-07) | `0739c09` | ✅ |
| ISS-20260806-001 | 08-06 | P1 | Fact | tune: GLiNER 回退 gliner_small-v1 (多语言版对中文边界不精准, 中文抽取已由 Qwen 兜底) | `aedb6a6` | ✅ |
| ISS-20260806-002 | 08-06 | P2 | Fact | fix: 中文事实抽取走 Qwen 防 GLiNER multi 边界不精准/幻觉 | `14e9054` | ✅ |
| ISS-20260806-003 | 08-06 | P2 | 采集 | fix: sync 水印边界 >= 修复 + 中文源接入(清理404/加BBC/DW/RFI) + 部署cron | `25d1a05` | ✅ |
| ISS-20260806-004 | 08-06 | P2 | 实体库 | feat: KB 可行性实验 — 四阶段 A/B 验证 + 3 处 KB 质量修复 | `3e599b7` | ✅ |
| ISS-20260806-005 | 08-06 | P2 | 其他 | fix: G1 EXCHANGE:TICKER 解析 — NASDAQ:NVDA → COMP_NVIDIA | `f1544bf` | ✅ |
| ISS-20260806-006 | 08-06 | P1 | 采集 | feat: C级 backlog 清理脚本 — 18K 低分文章积压治理 | `dafbc9b` | ✅ |
| ISS-20260806-007 | 08-06 | P3 | 推送 | fix: Cloud Sync 推送失败重试(幂等) + chunk 收缩 + 超时细分 | `bba45ff` | ✅ |
| ISS-20260805-001 | 08-05 | P2 | 实体库 | fix: 实体画像 canonical 解析优先 DB — Trump/乔·拜登 关系别名不丢 (旧KB canonical 不一致) | `7c656e6` | ✅ |
| ISS-20260805-002 | 08-05 | P2 | DB | fix: 迁移补 event_relations.created_at — 与 EventRelation 模型一致 | `915afbf` | ✅ |
| ISS-20260805-003 | 08-05 | P3 | 实体库 | fix: backfill 合并逻辑 — canonicalize 键后合并 + KB 类型优先 + 人物/国家类型推断 | `7348ca4` | ✅ |
| ISS-20260805-004 | 08-05 | P2 | 实体库 | fix: backfill 清理别名行移到关系重建后 — 避免 FK 冲突 | `ef2ce3f` | ✅ |
| ISS-20260805-005 | 08-05 | P2 | DB | fix: backfill 脚本 jsonb cast 语法 — CAST(:al AS jsonb) | `883dc2a` | ✅ |
| ISS-20260805-006 | 08-05 | P1 | 实体库 | fix: Entity 模型移除 metadata 列映射 — 'metadata' 为 Declarative 保留名致后端崩溃 | `7b06a3c` | ✅ |
| ISS-20260805-007 | 08-05 | P2 | 实体库 | feat: Phase 3 事件脏属性根治 — 实体匹配修复 + 主体显著性 + 存量清理 | `7cf985d` | ✅ |
| ISS-20260805-008 | 08-05 | P3 | 实体库 | fix: /internal/events/delete 引用表类型区分 — event_article/entity/insights 按 events.id | `4a65968` | ✅ |
| ISS-20260805-009 | 08-05 | P3 | DB | fix: /internal/events/delete 引用表按 events.id (INTEGER) 清理 — 修复 event_id 字符串类型不匹配 | `1f43c3d` | ✅ |
| ISS-20260805-010 | 08-05 | P2 | 后端API | fix: /internal/events/delete 逐条删除+失败回滚 — 修复共享 expanding bindparam 污染会话 | `ad2dfbc` | ✅ |
| ISS-20260805-011 | 08-05 | P2 | 聚合 | fix: 事件列表读层去重 — /events 按 lower(title) 折叠重复事件 (止血) | `0db77e9` | ✅ |
| ISS-20260803-001 | 08-03 | P2 | 聚合 | fix: 排除新闻来源名当事件主体 — is_media_source (Al Jazeera→US 误判) | `7a0ff5e` | ✅ |
| ISS-20260803-002 | 08-03 | P2 | DB | fix: 配置中心数据模型Tab — B耗时更新为noThink 2.2s/篇 + 进度列表更新 | `63f0893` | ✅ |
| ISS-20260803-003 | 08-03 | P2 | Fact | fix: Fact入库 — 去article_id FK + 加article_url + event_time清洗 + 错误日志 | `5b3c783` | ✅ |
| ISS-20260803-004 | 08-03 | P2 | 实体库 | feat: Canonicalizer v0.3 — 标题上下文修复 B 截断 action 漏判 | `da078d8` | ✅ |
| ISS-20260803-005 | 08-03 | P2 | 实体库 | fix: 清理实体管理误提交 + git-sync 只提交实体文件 | `f749b5a` | ✅ |
| ISS-20260803-006 | 08-03 | P2 | 实体库 | fix: 实体管理 git-sync 提交时指定 git 身份(容器无user.name/email) | `672f02e` | ✅ |
| ISS-20260803-007 | 08-03 | P2 | 实体库 | fix: 实体管理 git-sync 加 safe.directory=/host (容器内git dubious ownership) | `37aec08` | ✅ |
| ISS-20260802-001 | 08-02 | P2 | 实体库 | fix: 实体列表计数改为去重事件数 (与画像页一致) | `448d6c1` | ✅ |
| ISS-20260802-002 | 08-02 | P2 | 推送 | fix: pusher 双重编码 — _event_to_push_format 改发原始结构, 由后端统一 json 入库 | `c46ab54` | ✅ |
| ISS-20260802-003 | 08-02 | P3 | 前端 | fix: articles/list SSR window is not defined → useSearchParams + Suspense 模式 | `24e9372` | ✅ |
| ISS-20260802-004 | 08-02 | P1 | 聚合 | feat: Phase1 基线 — 事件数统一(全量口径) + 新闻/事件时间排序 + last_updated 时间回退 | `7daeebf` | ✅ |
| ISS-20260801-001 | 08-01 | P1 | 采集 | revert: 回退到 7791563 状态 (撤销视频合并/greenlet修复/每线程浏览器) | `8050016` | ✅ |
| ISS-20260801-002 | 08-01 | P2 | 采集 | revert: 恢复 Step 3.6 视频最后兜底 (撤销并入 Step 3) | `c0cbcdb` | ✅ |
| ISS-20260801-003 | 08-01 | P2 | 其他 | fix: Playwright sync greenlet 线程冲突 → 浏览器操作专用单线程 executor | `6d6ec6f` | ✅ |
| ISS-20260731-001 | 07-31 | P2 | 配置 | fix: get_profile 恢复未知域名配置中心覆盖 (重构回归) | `7791563` | ✅ |
| ISS-20260731-002 | 07-31 | P3 | 采集 | fix: 源列表标签动态显示总数 (98 硬编码 → 实时 sourcesTotal) | `83169f3` | ✅ |
| ISS-20260731-003 | 07-31 | P1 | 聚合 | fix: settings TEXT 列 JSON 字符串归一化为 list (修复域名标签 e.strategy.map 崩溃) | `d96836b` | ✅ |
| ISS-20260731-004 | 07-31 | P3 | 采集 | fix: web 域名标签显示源 rss_sources.DOMAIN_PROFILES 对齐配置中心 | `25a3f49` | ✅ |
| ISS-20260731-005 | 07-31 | P1 | 采集 | fix: Step 3.6 视频查询参数顺序错位导致永远 0 候选 + Step 3.5 恢复排除视频 | `2781171` | ✅ |
| ISS-20260731-006 | 07-31 | P2 | 推送 | fix: config-agent list 校验放宽到域名键, 支持 video_patterns 同步 | `555086d` | ✅ |
| ISS-20260731-007 | 07-31 | P2 | 实体库 | fix: 实体关联用规范化名匹配(支持别名) | `9c35150` | ✅ |
| ISS-20260731-008 | 07-31 | P2 | 实体库 | fix: 实体API actors JSONB cast为String查询 | `0cfd3d9` | ✅ |
| ISS-20260731-009 | 07-31 | P2 | 聚合 | fix: internal.py ON CONFLICT更新全部事件字段(含location_country) | `1dbba84` | ✅ |
| ISS-20260731-010 | 07-31 | P3 | 配置 | fix: loader按默认类型强转配置值(字符串数字→int/float) | `0099aab` | ✅ |
| ISS-20260731-011 | 07-31 | P2 | 聚合 | feat: 聚合优化 — 主题硬约束+best_title修复+SAO质心+阈值60+证据/去重 | `8b4ec56` | ✅ |
| ISS-20260731-012 | 07-31 | P2 | 其他 | fix: searxng_alt内容标题相关性校验防抓错内容 | `10d33b1` | ✅ |
| ISS-20260731-013 | 07-31 | P3 | 其他 | fix: 未评分文章Tier显示为'未评分'而非Tnull | `babcc1d` | ✅ |
| ISS-20260731-014 | 07-31 | P2 | 后端API | fix: /admin/status API移到/admin/pipeline/status避免路径冲突 | `ed587b6` | ✅ |
| ISS-20260731-015 | 07-31 | P2 | 后端API | feat: Pipeline状态页(运行日志+统计) + 修复/admin/pipeline认证竞态 | `2b6a7ff` | ✅ |
| ISS-20260731-016 | 07-31 | P2 | 前端 | fix: nginx加/admin/带斜杠精确匹配 | `62658f6` | ✅ |
| ISS-20260731-017 | 07-31 | P2 | 前端 | fix: 认证竞态 — admin页等待auth初始化避免闪退/跳登录 | `8073fe9` | ✅ |
| ISS-20260731-018 | 07-31 | P2 | 前端 | fix: nginx精确匹配/admin避免301到后端 | `9fb164d` | ✅ |
| ISS-20260731-019 | 07-31 | P2 | 前端 | fix: nginx精确匹配/admin/sources等前端管理页 | `42670bc` | ✅ |
| ISS-20260731-020 | 07-31 | P2 | 采集 | fix: rss.feeds JSON字符串解析 + 全部链路验证 | `e330f9b` | ✅ |
| ISS-20260731-021 | 07-31 | P2 | 配置 | fix: agent轮询token修正(INTERNAL_TOKEN) + 缓冲日志 | `b986b32` | ✅ |
| ISS-20260731-022 | 07-31 | P2 | 前端 | fix: 配置中心从/admin/config移至/config解决nginx路由冲突 | `1793648` | ✅ |
| ISS-20260730-001 | 07-30 | P3 | 前端 | fix: select下拉选项显式背景色 #1E293B + 白色文字 | `6248f41` | ✅ |
| ISS-20260730-002 | 07-30 | P3 | 前端 | fix: select下拉框暗色主题 color-scheme:dark | `52818f5` | ✅ |
| ISS-20260730-003 | 07-30 | P2 | 前端 | fix: 登录会员查看全文改为可点击链接→/login | `04a4193` | ✅ |
| ISS-20260730-004 | 07-30 | P2 | 前端 | fix: 登录成功跳转 /admin→/(404修复) + 错误信息优化 | `34027a3` | ✅ |
| ISS-20260730-005 | 07-30 | P2 | 其他 | fix: summary_cn为空时从正文content_md截取前200字作为摘要 | `465ecab` | ✅ |
| ISS-20260729-001 | 07-29 | P2 | 后端API | fix: test_api.py 禁用 httpx 代理（Tailscale 直连不走 SOCKS5） | `befc350` | ✅ |
| ISS-20260729-002 | 07-29 | P3 | 后端API | fix: test_api.py 修复认证方式 + 超时30s | `29c3d1b` | ✅ |
| ISS-20260729-003 | 07-29 | P2 | 采集 | fix: sources authority 增加 RSS→6 映射（DB type 为 rss 非 MEDIA） | `a4eeb01` | ✅ |
| ISS-20260729-004 | 07-29 | P2 | Fact | feat: V1 standard refactoring — Depends(get_db), fix data correctness, security | `5008b89` | ✅ |
| ISS-20260729-005 | 07-29 | P3 | 推送 | tune#4: 修复 Sync 超时 + Nginx 超时 + Cloud Sync 分块优化 | `45fcc06` | ✅ |
| ISS-20260729-006 | 07-29 | P3 | 前端 | feat: Wiki 文档体系 + API 测试 + 修复前端类型 | `921dc81` | ✅ |
