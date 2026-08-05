# Knowledge Base V1 — 全球实体关系知识库

> 版本: V1 (Phase 1) · 2026-08-05
> 定位: 所有新闻 (Reuters/Bloomberg/BBC/新华社/人民日报...) → Article → Fact → Canonicalizer → **Knowledge Base (统一世界)**
> 目标: 中英统一、所有聚合/画像/关系建立在稳定 **Entity ID** 之上

## 目录结构

```
knowledge_base/
  countries.yaml      国家本体 (ISO ID: CTRY_CHN/USA/RUS...)
  organizations.yaml  组织本体 (Federal Reserve/UN/NATO/国务院...)
  companies.yaml      公司本体 (COMP_NVIDIA/TSMC/HUAWEI...)
  people.yaml         人物本体 (PERS_TRUMP/XI/PUTIN...)
  locations.yaml      位置本体 (LOC_BEIJING/Wall Street/Gaza...)
  industries.yaml     行业本体 (GICS + AI/Semiconductor/Space...)
  actions.yaml        动作本体 (ACT_ATTACKS/SANCTIONS/EXPORT_CONTROL...)
  relations.yaml      关系本体 (REL_PART_OF/COMPETITOR/INVESTOR...)
  event_types.yaml    事件类型 (EVT_MILITARY + subtypes)
  entity_alias.yaml   中英别名映射 (特朗普→PERS_TRUMP, 中国→CTRY_CHN)
  loader.py           YAML 加载器 + 别名→Entity ID 解析
  generate_kb.py      (scripts/knowledge_base/) 种子生成器
```

## Entity ID 规范

```
CTRY_  国家(ISO alpha3)  COMP_  公司     PERS_  人物
ORG_   组织             LOC_   位置     IND_   行业
ACT_   动作             REL_   关系     EVT_   事件类型
MODEL_ AI模型           TECH_  技术     LAW_   法律
```

例: `CTRY_CHN` / `COMP_NVIDIA` / `PERS_DONALD_TRUMP` / `ORG_FEDERAL_RESERVE` / `LOC_BEIJING`

## 中英统一解析（三层归一）

```
原始新闻(中/英) → GLiNER/LLM 实体抽取 → AliasResolver(knowledge_base.loader) → Canonicalizer(Entity ID) → OntologyValidator → Fact
```

`loader.resolve("特朗普")` → `('PERS_TRUMP', 'Trump', 'Person')`
`loader.resolve("中国")`   → `('CTRY_CHN', 'China', 'Country')`
`loader.resolve("英伟达")`  → `('COMP_NVIDIA', 'NVIDIA', 'Company')`

**G7 (2026-08-06)**: `news_intel/ontology_validator.py` 独立第三层 — 实体 ID 前缀↔类型一致性 (COMP_→Company/PERS_→Person...) + 关系 REL_ 白名单; canonicalize 输出带 `validation` 诊断字段 (不阻断聚合)

## Canonicalizer 接入

- `news_intel/canonicalizer.resolve_entity` 已接入 KB：KB 别名命中 → 返回稳定 ID；未命中回退本地本体 (entity_weights.json + _ID_PREFIX)
- **G1 (2026-08-06) `EXCHANGE:TICKER` 前缀剥离**: 输入含 `XXX:YYYY` (交易所代码:代号) 时剥离前缀用代号解析 → `NASDAQ:NVDA`→`COMP_NVIDIA`、`NYSE:AAPL`→`COMP_APPLE`；公司解析不再被交易所前缀污染
- `aggregator._canonicalize` 兼容：`英伟达`→`NVIDIA`（跨语言聚合基础）

## 维护

- 种子生成: `python scripts/knowledge_base/generate_kb.py`（从 KB/ENTITY_CANONICAL/canonicalizer 迁移）
- 扩量: 5000 公司 / 3000 人物 / 250 国家需后续 Wikidata/ISO 数据导入
- **G1 (2026-08-06)**: `import_seed.py` 给既有 SEC 公司回填主 ticker (最短作主) + exchange，companies.yaml 7,972/8,038 带 ticker
- **G6 (2026-08-06)**: locations 40 项全补 lat/lon (`generate_kb.LOC_COORDS` curated + locations.yaml 同步)，地图/画像可用坐标
- **G3 (2026-08-06)**: actions 26→**81** (`generate_kb.ACTION_CATALOG`, 含 zh/past/noun); 引擎识别扩 46/44, `_OBJECT_JOINT` 加 RATE_CUT/HIKE; 回归 20+10 通过
- **G7 (2026-08-06)**: `ontology_validator.py` 三层归一第三层 — ID 前缀↔类型 + 关系白名单, canonicalize 输出 `validation` 字段
- **G2 (2026-08-06)**: `import_seed.COMPANY_HIERARCHY` 20 家核心公司补 parent/subsidiaries (Alphabet→Google/YouTube/Waymo/DeepMind, 阿里→蚂蚁/云, 字节→TikTok/抖音)
- **G4 (2026-08-06)**: event_types 12→**29 主题/157 细分** (`EVENT_TYPES_CATALOG`, 含 zh)
- **G5 (2026-08-06)**: relations 36→**106 种** (`RELATIONS_CATALOG`, 含 zh/inverse/description)
- **G8 (2026-08-06)**: countries 43 大国补 government + ally/rival 关系 (`COUNTRY_ENRICH`)
- 生产 profile 需同步 `knowledge_base/` + `canonicalizer.py`（dev-deploy-workflow）

## 现状种子规模 (Phase 1 + 扩种)

| 文件 | 数量 | 数据源 |
|------|-----|--------|
| countries | **249** | ISO 3166 + G8 43 国政体/联盟关系 |
| organizations | 12 | KB + 政府/军事转喻 |
| companies | **8038** | SEC 10K美股(ticker 7972 回填) + KB 全球, G2 补 20 家层级 |
| people | **18,790** | Wikidata 30国×6职业×DOB (两次导入并集) + 精选 128; **3,670 含中文别名** |
| locations | 40 (全带坐标) | canonicalizer 33城 + 地缘, G6 补 lat/lon |
| industries | 25 | GICS + 扩展 |
| actions | **81** | ACTION_CATALOG (G3 扩充, 含 zh/past/noun), 引擎识别 46 |
| relations | **106** | G5 RELATIONS_CATALOG, 含 zh/inverse/desc |
| event_types | **29** (157 细分) | G4 EVENT_TYPES_CATALOG, 含 zh |
| entity_alias | 85 | 中英别名 + 政府转喻 |

扩种工具: `scripts/knowledge_base/import_seed.py` (ISO + SEC 下载, 幂等重跑)

## 路线

- **Phase 1 ✅** 本体 YAML + loader + Canonicalizer Entity ID
- **Phase 2 ✅** ENTITY_CANONICAL 迁入知识库 (73/73 回归) + Aggregator 中英统一聚合
  - ACTION_MAP 补中文模式 (发布/制裁/攻击/加息/出口管制) + 新增 APPOINTS/MEETS/RESIGNS/SIGNS/EXPORT_CONTROL
  - fingerprint_score: 完全同主体(KB归一)+25; country/topic 硬约束对同主体放宽
  - 实测 NVIDIA(EN)+英伟达(CN) 合并1事件; Fed+Iran 保护不破
  - GOV 统一短 ID: Washington→ORG_US_GOVERNMENT, IRGC→ORG_IRGC, ECB→ORG_ECB
- **Phase 3** 实体画像(国家/公司/人物/组织) + 关系网络 + Story 演化 + 跨语言聚合

## ⚠️ 已知限制
- 中文动作检测已支持 (英文regex + 中文模式); 中英聚合需实体+动作都命中
- 主题分类对短英文标题有噪声 (GPU 无 chip → Diplomacy), 已通过同主体+25 缓解
- loader 用 threading.RLock (Lock 会死锁); entity_alias(curated) 优先于 section

## 实验验证 (2026-08-06) — KB 可行性 A/B

`experiments/kb_exp_001/` 四阶段验证 (不改生产逻辑, 107 别名/59 动作/6 事件组黄金集):

| 阶段 | 指标 | KB OFF | KB ON | 提升 |
|---|---|---|---|---|
| Phase1 Alias | 总归一率 | 33.6% | **89.7%** | +56.1pp |
| Phase1 Alias | 中文归一率 | 0% | **78.3%** | +78.3pp |
| Phase2 Action | 动作归一(59变体) | — | **100%** | 中文动作补齐 |
| Phase3 Event | 组内唯一ID(理想6) | 15 | **6** | 归并翻倍 |

**实验发现并修复**: entity_alias 6 人物 CTRY_→PERS_ 前缀错; Federal Reserve 前缀+别名缺 Fed; Iran 双 ID; canonicalizer 中文动作归一失效 (_CN_ACTION)。

**结论**: KB 对实体归并/动作归一/中文聚合提升显著, 可接入生产。
