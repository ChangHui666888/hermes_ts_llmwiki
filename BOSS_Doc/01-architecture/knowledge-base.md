# Knowledge Base V1 — 全球实体关系知识库

> 版本: V1 (Phase 1) · 最后刷新 2026-08-12（对照代码 + loader 实测）
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

## Entity ID 规范（loader._PREFIX_TYPE 完整 24 前缀）

```
CTRY_ 国家(ISO alpha3)  COMP_ 公司       PERS_ 人物      ORG_  组织
LOC_  位置             IND_  行业       IND_SUB_ 细分赛道 ACT_  动作
REL_  关系             EVT_  事件类型   MODEL_ AI模型    TECH_ 技术
LAW_  法律             CUR_  货币       IDX_  指数      ETF_  ETF
CMD_  大宗商品         SHIP_ 舰船       AIR_  飞行器    SAT_  卫星
MISSILE_ 导弹          WPN_  武器       PROD_ 产品      STORY_ 故事
ENT_  兜底实体
```

例: `CTRY_CHN` / `COMP_NVIDIA` / `PERS_DONALD_TRUMP` / `ORG_FEDERAL_RESERVE` / `LOC_BEIJING` / `IND_SUB_半导体`
> ⚠️ `MODEL_/TECH_/LAW_/CUR_/IDX_/ETF_/CMD_/SHIP_/AIR_/SAT_/MISSILE_/WPN_/PROD_/STORY_` 已在 loader 注册但当前 YAML 尚未收录条目，供运行时动态生成/未来扩展。

### loader.py API

| 函数 | 签名 | 行为 |
|------|------|------|
| `get_kb()` | `→ dict` | 懒加载 10 YAML，返回 `{countries, organizations, companies, people, locations, industries, actions, relations, event_types, aliases}`；线程安全 (RLock) |
| `resolve(name)` | `(str) → (entity_id, canonical, type) \| None` | 小写别名查索引 → 稳定三元组（`特朗普 → ('PERS_TRUMP','Trump','Person')`） |
| `entity_id(name, etype)` | `(str,str) → str` | KB 命中返回稳定 ID；未命中按 `前缀_大写下划线` 生成（兼容 aggregator 本地方案） |
| `entity_type(cid)` | `(str) → str` | 前缀→类型推断（`CTRY_CHN → Country`） |
| `action_lookup(id)` / `relation_lookup(id)` | `(str) → dict\|None` | actions.yaml / relations.yaml 条目查询 |

索引构建优先级: **① `entity_alias.yaml`（curated，含转喻/缩写/中文）先建 → ② 本体 section 条目填 gap**；键=`别名小写`，值=`(cid, canonical_en, type)`。覆盖范围 countries/organizations/companies/people/locations/industries。

### 本体字段 Schema（2026-08-09 实测扫描）

| 本体 | ID 格式 | 关键字段 | 示例 |
|------|---------|---------|------|
| countries (249) | `CTRY_{ISO3}` | `name.{en,zh}`, `aliases[]`, `iso.alpha2/3`, `capital.{en,zh}`, `continent`, `currency`, `government`, `relations.{ally[],rival[]}` | `CTRY_CHN` |
| organizations (58) | `ORG_{NAME}` | `name.{en,zh}`, `aliases[]`, `type`(Central Bank/Government/Military/International Org), `country` | `ORG_FEDERAL_RESERVE` |
| companies (8,145) | `COMP_{NAME}` | `name.{en,zh}`, `aliases[]`(含 ticker/中文), `industry`, `country`, `ticker`, `exchange`, `parent`, `subsidiaries[]`, `sub_segments[]` | `COMP_NVIDIA` |
| people (18,800) | `PERS_{NAME}` | `name.{en,zh}`, `aliases[]`, `country`, `organization`, `position` | `PERS_TRUMP` |
| locations (245) | `LOC_{NAME}` | `name.{en,zh}`, `aliases[]`, `country`, `province`, `lat`, `lon` | `LOC_BEIJING` |
| industries (69) | `IND_{NAME}` / `IND_SUB_{NAME}` | `name.{en,zh}`, `description`, `sub_of`(细分赛道→父行业) | `IND_SEMICONDUCTOR` |
| actions (137) | `ACT_{ACTION_ID}` | `action_id`, `en/zh/past/noun`, `event_type`, `priority`, `patterns.{en[],zh[]}` | `ACT_EXPORT_CONTROL` |
| relations (108) | `REL_{NAME}` | `name.{en,zh}`, `inverse`, `description` | `REL_SUBSIDIARY_OF` |
| event_types (29+13) | `EVT_{NAME}` | `name.{en,zh}`, `subtypes[]` + 顶层 `topic_signals.{topic}.{en[],zh[]}` | `EVT_MILITARY` |
| entity_alias (89) | 源前缀 | `{cid}.{canonical, aliases[]}`（curated 转喻/缩写/中文） | `CTRY_USA → ["US","USA","U.S.","America"]` |

## 中英统一解析（三层归一）

```
原始新闻(中/英) → GLiNER/LLM 实体抽取 → AliasResolver(knowledge_base.loader) → Canonicalizer(Entity ID) → OntologyValidator → Fact
```

`loader.resolve("特朗普")` → `('PERS_TRUMP', 'Trump', 'Person')`
`loader.resolve("中国")`   → `('CTRY_CHN', 'China', 'Country')`
`loader.resolve("英伟达")`  → `('COMP_NVIDIA', 'NVIDIA', 'Company')`

**G7 (2026-08-06)**: `news_intel/ontology_validator.py` 独立第三层 — 实体 ID 前缀↔类型一致性 (COMP_→Company/PERS_→Person...) + 关系 REL_ 白名单; canonicalize 输出带 `validation` 诊断字段 (不阻断聚合)。ID 白名单 13 前缀: `CTRY/COMP/PERS/ORG/LOC/IND/ACT/REL/EVT/MODEL/TECH/LAW/ENT`（正则 `^([A-Z][A-Z_]*)_`），非白名单前缀或类型不匹配 → issues 标记（不阻断）

## Canonicalizer 接入

- `news_intel/canonicalizer.resolve_entity` 已接入 KB：KB 别名命中 → 返回稳定 ID；未命中回退本地本体 (entity_weights.json + _ID_PREFIX)
- **G1 (2026-08-06) `EXCHANGE:TICKER` 前缀剥离**: 输入含 `XXX:YYYY` (交易所代码:代号) 时剥离前缀用代号解析 → `NASDAQ:NVDA`→`COMP_NVIDIA`、`NYSE:AAPL`→`COMP_APPLE`；公司解析不再被交易所前缀污染
- **Schema V2 输出**（2026-08-10）: `resolve_entity` 产出 `{name, id, type, role}`；canonicalize 顶层带 `action{type,status,polarity,event_type,detail}` + `validation{ok, issues[], valid_count}`（动作状态 completed/ongoing/planned/denied/proposed/rumored，极性 positive/negative/neutral）
- `aggregator._canonicalize` 兼容：`英伟达`→`NVIDIA`（跨语言聚合基础）

## v2.4 动态加载（2026-08-09, aggregator 从 KB 读动作/主题）

| 数据 | KB 源文件 | 加载函数 | 回退 |
|------|-----------|----------|------|
| `ACTION_MAP`（动作正则） | `actions.yaml` `patterns.{en,zh}` | `_get_action_map()` | 硬编码 `ACTION_MAP` |
| `TOPIC_SIGNALS`（主题关键词） | `event_types.yaml` `topic_signals.{topic}.{en,zh}` | `_get_topic_signals()` | 硬编码 `TOPIC_SIGNALS` |

解决了 Canonicalizer 与 Aggregator 两份动作词表不同步的问题——KB 成为单一事实来源，补动作只需改 actions.yaml。

## 维护

- 种子生成: `python scripts/knowledge_base/generate_kb.py`（从 KB/ENTITY_CANONICAL/canonicalizer 迁移）
- 扩量工具: `scripts/knowledge_base/import_seed.py`（ISO 3166 + SEC ticker, 幂等重跑）· `import_wikidata_people.py`（SPARQL 采人）· `add_locations.py`（高频地理位置）· `enrich_company_industry.py`（行业富化）· `add_actions.py`
- **G1 (2026-08-06)**: `import_seed.py` 给既有 SEC 公司回填主 ticker (最短作主) + exchange，companies.yaml 7,972/8,038 带 ticker
- **G6 (2026-08-06)**: locations 40 项全补 lat/lon (`generate_kb.LOC_COORDS` curated + locations.yaml 同步)，地图/画像可用坐标
- **G3 (2026-08-06)**: actions 26→**81** (`generate_kb.ACTION_CATALOG`, 含 zh/past/noun); 引擎识别扩 46/44, `_OBJECT_JOINT` 加 RATE_CUT/HIKE; 回归 20+10 通过
- **G7 (2026-08-06)**: `ontology_validator.py` 三层归一第三层 — ID 前缀↔类型 + 关系白名单, canonicalize 输出 `validation` 字段
- **G2 (2026-08-06)**: `import_seed.COMPANY_HIERARCHY` 20 家核心公司补 parent/subsidiaries (Alphabet→Google/YouTube/Waymo/DeepMind, 阿里→蚂蚁/云, 字节→TikTok/抖音)
- **G4 (2026-08-06)**: event_types 12→**29 主题/157 细分** (`EVENT_TYPES_CATALOG`, 含 zh)
- **G5 (2026-08-06)**: relations 36→**106 种** (`RELATIONS_CATALOG`, 含 zh/inverse/description)
- **G8 (2026-08-06)**: countries 43 大国补 government + ally/rival 关系 (`COUNTRY_ENRICH`)
- **G9 (2026-08-09)**: locations 40→**245** 新闻高频地理位置大扩充（`scripts/knowledge_base/add_locations.py`，幂等）— 中国主要城市/亚太/中东/欧洲/北美/拉美/非洲/大洋洲 + 冲突热点（俄乌 Zaporizhzhia/Donbas/Kursk、加沙 Rafah/Khan Younis、也门 Sanaa/Hodeidah、苏丹 Khartoum/El Fasher、刚果 Goma）、地缘航道（东海/黄海）；**存量 40 项补全中文名**（北京/基辅/莫斯科…）；`entity_alias` 加 `LOC_KYIV` 覆盖 COMP_KYIVSTAR 别名冲突（Kyiv/基辅→城市）
- 生产 profile 需同步 `knowledge_base/` + `canonicalizer.py`（dev-deploy-workflow）

## 现状种子规模 (Phase 1 + 扩种)

| 文件 | 数量 | 数据源 |
|------|-----|--------|
| countries | **249** | ISO 3166 + G8 43 国政体/联盟关系 |
| organizations | **58** | KB + 央行/政府机构/国际组织 (2026-08-09 富化: 美联储/证监会/白宫/东盟等) |
| companies | **8,145** | SEC 10K美股 + KB 全球 + **国产替代/光通信/机器人/供应链公司** (2026-08-09 +130) |
| people | **18,800** | Wikidata + 精选 + 蔡奇/卢拉等 (2026-08-09) |
| locations | **245** (全带坐标) | canonicalizer 33城 + 地缘, G6 补 lat/lon, **G9 +205 扩充 + 存量补中文名** |
| industries | **69** | GICS 25 + **44 细分赛道 IND_SUB_** (先进封装/光通信/机器人/EDA/磷化铟等, 2026-08-09) |
| actions | **137** | ACTION_CATALOG (G3 扩充) + **56 商业/经营/财报/资本市场/科技/能源/军事/外交/法律/市场/供应链/政策/预期动作** (2026-08-09) |
| relations | **108** | RELATIONS_CATALOG + **IN_SEGMENT/IN_INDUSTRY** (2026-08-09) |
| event_types | **29** (157 细分) | G4 EVENT_TYPES_CATALOG, 含 zh |
| entity_alias | **89** | 中英别名 + 政府转喻 |

> **2026-08-09 富化**: 561 评分实体 100% 映射 KB（companies +130/organizations +39/people +2）+ **44 细分赛道** + 130 公司→赛道 sub_segments + IN_SEGMENT 多维关系。详见 [entity-scoring-mapping.md](entity-scoring-mapping.md)。
> **2026-08-09 实测扫描**（`knowledge_base/` 目录）: countries 249 / organizations **58** / companies **8,145** / people **18,800** / locations **245**（205 中文名） / industries **69**(44 细分赛道) / actions **137** / relations 108 / event_types 29 / entity_alias **89**。

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

---

## v4.4.3 中英别名补充 (2026-08-06)

- **CTRY_USA canonical 统一为 `United States`**（与 CTRY_UNITED_STATES 一致, 解锁中英同主体 +25 分）。
- **ORG_EU canonical 置 `European Union`**。
- 新增中文别名: 五角大楼/美国国防部→ORG_US_DOD, 华盛顿/白宫→ORG_US_GOVERNMENT, 商务部/工信部→ORG_CN_GOVERNMENT, 三星电子→COMP_SAMSUNG, SK海力士→COMP_SK_HYNIX, 中微→COMP_AMEC, 宝马→COMP_BMW, 阿斯麦→COMP_ASML。
- 约定: curated `entity_alias.yaml` 别名优先于 section YAML 的 `name`; 中英归一以 canonical 名为准（fingerprint_score 按 canonical 字符串比较）。
