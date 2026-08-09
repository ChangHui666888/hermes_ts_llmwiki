# 会话交接 — 2026-08-05 全量升级过程 / 状态 / 遗留问题

> 本文件供**下次会话**接手使用。记录了本次会话的全部升级、当前系统状态、待办遗留。
> 提交: 最新 `master` = `4f4a1fc`（本会话共 ~20 个 commit）。

---

## 一、本次会话完成的工作（按时间线）

### 1. 事件列表雷同问题（根因 + 根治）
- **根因**: 聚合器 `aggregator.py` 用 `EVT-{date}-{run局部idx}` 生成事件号（非幂等），每 ~15 分钟对同一滑窗 `top-300 news_content` 全量重聚，本地/云端去重键只有 event_id → 同标题堆积（云 503 条→154 个标题）
- **修复**:
  - 读层去重: `/api/v1/events` 按 `lower(title)` 分组保留最佳行
  - 存量清理: 云 503→158（按空白折叠标题保留最早）
  - **增量聚合**: `news_content` 加 `event_id` 列，只聚合未标记文章 + 标记
  - **归一**: `news_intel/event_normalizer.py` 同标题合并到最早事件（保留最早 event_id），云删端点 `/internal/events/delete`
- **坑**: 云 events 引用表类型不一致（`event_article/entity/insights.event_id`=INTEGER→events.id；`event_relations.parent/child_event_id`=VARCHAR→events.event_id）

### 2. Phase 3 事件脏属性修复
- **根因**: `scorer.py score_entities` 子串匹配 `name in text` → `Xi` 命中所有 ML 论文希腊字母 ξ/xi、`BP`/`US` 短名误标
- **修复**: 词边界匹配（短名≤3 大小写敏感）+ 主体显著性（标题实体×2 + `_subject_is_prominent` 事件级门）+ fact subject 文本校验 + `cleanup_dirty_events.py` 一次性清理

### 3. 实体/实体关系升级（data-model-upgrade-plan.md）
- **迁移 0002**: `entities` 补 country/importance/first_seen/last_seen/confidence；`entity_alias`(entity_id/alias/lang)；`entity_relationship`(from/to/type/conf/desc)；`event_relations` 扩展 start/end_time/evidence_count
- **配置中心"实体关系"Tab**: GET/POST/DELETE /admin/entity-relations + /admin/event-relations + regenerate
- **坑**: SQLAlchemy Declarative `metadata` 是保留名（Entity 模型不能映射该列）；`:al::jsonb` 要 `CAST(:al AS jsonb)`

### 4. Knowledge Base V1（全球实体关系知识库）
- **Phase 1**: `knowledge_base/` 9+1 本体 YAML + `loader.py`（中英别名→稳定 Entity ID）
- **Phase 2**: ENTITY_CANONICAL 73 条迁入 KB（回归 73/73）；ACTION_MAP 补中文模式；fingerprint 同主体 +25；country/topic 硬约束对同主体放宽 → **中英统一聚合**（NVIDIA+英伟达→1 事件实测）
- **扩种子**: `import_seed.py` ISO 249 国 + SEC ~8,300 公司（法定名归一去重幂等）
- **Wikidata 人物**: `import_wikidata_people.py` 30国×6职业×DOB 窄查询分页 → people.yaml；中文别名 rdfs:label 捕获 → **~18,800 人 / 3,670 含中文别名**
- **SEC 行业富化**: `enrich_company_industry.py` 精选映射 ~168 家（Wikidata 批量 P249+P452 不可靠）

### 5. Phase 3 实体画像 / 关系网络 / Story
- **实体画像增强**: 前端别名 chips + 关系网络；`get_entity` canonical 优先 DB（修 Trump/Donald Trump 不一致）；`sync_kb_to_db.py`（27,176 实体 / 41,110 别名入库）
- **Story 演化层**: 迁移 0003 `story`+`story_event`；`stories.py` API（列表/详情/derive）；派生=同 subject 事件→故事（12 个）；前端 `/stories` + 时间线

---

## 二、当前系统状态

### 知识库规模
| 本体 | 数量 | 数据源 |
|---|---|---|
| 国家 | 249 | ISO 3166 |
| 公司 | 8,038 | SEC 10K + KB 全球（~168 带行业） |
| 人物 | **~18,800** | Wikidata（3,670 含中文别名）+ 精选 |
| 位置 | 40 | canonicalizer 33 城 + 地缘 |
| 行业/动作/关系/事件类型 | 25 / 26 / 36 / 12 | GICS + canonicalizer + KB |
| 实体别名 | 85+（KB）+ 41,110（DB） | 中英 + Wikidata zh |

### 云端 DB（VPS PG）
- entities **27,176** / entity_alias **41,110** / entity_relationship 223 / event_relations 83
- story **12** / story_event ~90
- events ~158 / articles 1,349

### 已部署
- 后端: 实体画像（别名/关系）、关系网络、Stories API、事件去重读层
- 前端: 实体画像增强、`/stories` 时间线、配置中心 13 Tab（含实体关系）
- 迁移: 0001(fact) / 0002(entity) / 0003(story) 全部应用
- profile 副本已同步（knowledge_base/ + aggregator/canonicalizer/event_normalizer/cleanup_dirty_events）

---

## 三、遗留问题（按优先级）

### P0 — 环境/网络
| 问题 | 说明 | 建议 |
|---|---|---|
| **Tailscale 中继慢** | 外部访问 VPS 3-7s/请求，ping 336ms（DERP 中继 `173.208.218.154:41641`）。系统自身 API 12-46ms 快 | ① `tailscale ping` 打洞直连 ② 换公网/VPN 出口 ③ 前端 CDN 缓存 |

### P1 — 数据/功能细节
| 问题 | 说明 | 建议 |
|---|---|---|
| `NASDAQ:NVDA` 无法解析 | KB 存 "NVDA" 无交易所前缀 | import_seed 给 SEC 公司加 `{EXCHANGE}:{TICKER}` 别名 |
| `拜登`（短名）→ None | Wikidata zh 标 "乔·拜登" | 加中文短名别名映射 |
| 画像 category 部分 unknown | 旧 KB（entity-network.json）未覆盖 Wikidata 实体 | `_find_entity` 兜底用 DB type/category |
| SEC 行业只 ~168 家 | Wikidata 批量查询不可靠 | 后续接行业数据集（如 stock-sectors）批量富化 |

### P2 — 功能扩展（未开始）
| 项 | 说明 |
|---|---|
| **主题型 Story** | 当前派生按 subject（实体为中心）；"芯片战"这类跨实体主题需按关键词/主题聚类（如 title 含 "chip/export control" → "US-China Chip War"） |
| **Story 手动聚合** | 配置中心加 Story 管理 Tab（类似事件校对），人工把事件归入故事 |
| **跨语言检索** | 按 Entity ID 的多语言搜索（中文搜"英伟达"命中 NVIDIA 实体及其事件） |
| **人物 3000 目标** | 已超（~18,800），但含部分冷门；如需精选 notable 集可加 notability 过滤（sitelinks 查询慢，需分批） |
| **国家富化** | 249 国中仅 40+ 大国含 capital/currency，其余为空（ISO CSV 无此字段） |

### P3 — 已知限制
- 中文动作检测已支持，但动作本体仍英文 regex + 中文模式（未建独立 action_category/synonym 表）
- `event_relations` 是保守 `precedes`（时间序），未断言因果
- 宽 Wikidata SPARQL 查询易超时（需 国家+职业+DOB 三限定 窄查询）
- LIMIT-100-per-combo 顺序非确定 → 不同子集（需并集去重）

---

## 四、建议下次会话起点

1. **处理 Tailscale 网络**（P0，影响所有 Web 体验）
2. **主题型 Story 派生**（P2，价值最高，把事件聚成"芯片战/伊朗冲突"等主题故事）
3. **跨语言检索**（P2，KB Entity ID 的价值落地）
4. 修 P1 细节（NVDA 前缀、拜登短名、category 兜底）

## 关键文件索引
```
knowledge_base/                    KB YAML + loader.py + __init__.py
scripts/knowledge_base/            generate_kb.py / import_seed.py / import_wikidata_people.py / enrich_company_industry.py / cleanup_dirty_events.py(在news_intel/)
scripts/news_intel/                aggregator.py / canonicalizer.py / event_normalizer.py / scorer.py / db.py
scripts/news-platform-v8/apps/api/routes/   entities.py / events_v1.py / entity_relations.py / stories.py / internal.py
scripts/news-platform-v8/migrations/versions/  0001/0002/0003
```
相关记忆: `knowledge-base-v1.md` / `data-model-upgrade.md` / `event-dedup-fix.md` / `entity-kb-maintenance.md` / `dev-deploy-workflow.md`
