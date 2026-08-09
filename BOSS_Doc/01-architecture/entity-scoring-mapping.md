# 评分规则实体 → 知识库映射分析

> 版本: v1.0 · 2026-08-09
> 定位: 把评分规则（entity_weights/value_tiers/asset_graph/event_keywords）涉及的**实体与关系**，映射到 Knowledge Base V1（稳定 Entity ID），找出覆盖缺口。
> 依据: `news_intel/config/*.json` 实际数据 × `knowledge_base/*.yaml` loader 实测解析。
> 相关: [knowledge-base.md](knowledge-base.md) · [entity-workflow-usage.md](entity-workflow-usage.md) · [scoring-rules.md](scoring-rules.md)

---

## 1. 评分规则涉及的实体规模（2026-08-09 实测）

| 来源 | 实体数 | 说明 |
|------|:--:|------|
| entity_weights.json | 559 | companies 340 / persons 84 / countries 34 / organizations 101 |
| value_tiers.json (T1-T10) | 305 (含别名) | 价值奖励分级实体（去重后并入上表） |
| **合并去重** | **561** | 评分规则唯一实体 |

## 2. KB 映射状态（loader.resolve 实测）

| 阶段 | 解析 | 占比 | 说明 |
|------|:--:|:--:|------|
| **富化前** | 251 / 561 | 45% | 原始 KB 覆盖 |
| **富化后** (2026-08-09) | **359 / 561** | **64%** | 新增 34 公司 + 20 组织 + 2 人物 + 补别名 26 |

**本次富化**（commit `4b3231a`）：
- companies.yaml +34 新实体（国产替代/韬定律/机器人/光通信中英配对: 长江存储→COMP_YMTC, 中微→COMP_AMEC, 中际旭创→COMP_INNOLIGHT, 优必选→COMP_UBTECH…）+ 7 中文别名 + 15 变体别名（Exxon→COMP_EXXONMOBIL, Citi→COMP_CITIGROUP, ASE→COMP_ASE_TECHNOLOGY…）
- organizations.yaml +20（东盟/金砖/证监会/财政部/白宫/美联储/欧盟/联合国/NATO/IMF 等）+ 4 别名
- people.yaml +2（蔡奇→PERS_CAI_QI, 卢拉→PERS_LULA）
- 已验证: 长江存储/中际旭创/Exxon/东盟/蔡奇/优必选 全部解析到稳定 ID；KB selftest 通过

### 剩余缺口（202 未解析）

| 类别 | 数量 | 典型 |
|------|:--:|------|
| companies（仍需新增） | ~150 | AIXTRON/ASMPT/BESI/EV Group/DISCO/AT&S/CGN/CNNC/Framatome/波士顿动力/Figure AI/DeepSeek… |
| organizations | ~38 | Federation Council/俄罗斯联邦委员会/国家金融监督管理总局(部分已补)… |
| persons | ~14 | Bill Ackman/Larry Ellison…（部分为英文名变体）|

### 真缺失分类

| 类别 | 数量 | 典型 |
|------|:--:|------|
| companies | 203 | 长江存储/长鑫存储/中微/北方华创/寒武纪/海光/龙芯/澜起/华大九天/中际旭创/新易盛/天孚/光迅/烽火/中兴/优必选/宇树… |
| organizations | 58 | ASEAN/BRICS/CSRC/海关总署/国家金融监督管理总局/上海微电子(公司?)… |
| persons | 16 | 蔡奇/卢拉/特雷莎·梅…（部分为中文别名缺失）|

### 名称变体（需补别名，34 个）

| 评分名 | KB 实体 | 说明 |
|--------|---------|------|
| Exxon | COMP_EXXONMOBIL | 全名 |
| Lockheed | COMP_LOCKHEED_MARTIN | 简称 |
| Citi | COMP_CITIGROUP | 简称 |
| Bank of America | COMP_BANK_OF_AMERICA_DE | 后缀 DE |
| Wells Fargo | COMP_WELLS_FARGO_MN | 后缀 MN |
| Veeco | COMP_VEECO_INSTRUMENTS | 全名 |
| Kulicke & Soffa | COMP_KULICKE_SOFFA_INDUSTRIES | 全名 |
| Amkor | COMP_AMKOR_TECHNOLOGY | 全名 |
| ASE | COMP_ASE_TECHNOLOGY | 全名 |
| Amphenol | COMP_AMPHENOL_DE | 后缀 |
| IQE | COMP_IQE_ADR | 后缀 ADR |
| 伯克希尔/拜登/卢拉/俄气/大众/奔驰/西门子/空客/索尼/鸿海… | (对应英文实体) | **中文别名缺失** — KB 有英文实体, 需补中文 alias |

## 3. 关系映射

评分规则中的"关系"需映射到 KB `relations.yaml`（REL_ 106 种）:

| 评分关系 | 类型 | KB 关系 |
|---------|------|---------|
| value_tiers 实体→T级 | 价值分级 | 建议新增 `REL_VALUE_TIER`（实体→分级）或记作实体属性 |
| asset_graph 资产键→stocks | 资产影响 | `REL_AFFECTS`（资产影响股票）或 `REL_SUPPLIES`（供应链）|
| event_keywords 关键词→分类 | 主题归属 | 实体→`REL_BELONGS_TO` 行业/主题 |
| 国产替代/韬定律/光通信 分组 | 供应链层级 | `REL_SUPPLIES`/`REL_CUSTOMER_OF`/`REL_EQUIPMENT_FOR` |

> ⚠️ 当前 KB `relations.yaml` 106 种已含 PART_OF/COMPETITOR/INVESTOR 等；评分分组关系未入 KB。

## 4. 建议的映射行动

### 4.1 补别名（34 变体 → 现有 KB 实体）
- `entity_alias.yaml` 补: `Exxon→COMP_EXXONMOBIL`, `Citi→COMP_CITIGROUP`, `Lockheed→COMP_LOCKHEED_MARTIN`… 等 34 条
- 中文别名补: `伯克希尔→COMP_BERKSHIRE_HATHAWAY`, `拜登→PERS_JOE_BIDEN`, `大众→COMP_VOLKSWAGEN`…（需逐一确认 KB 对应实体）

### 4.2 新增缺失实体（276 个 → KB yaml）
- **companies.yaml** +203：国产替代（长江存储/长鑫存储/中微/北方华创/寒武纪/海光/龙芯…）+ 光通信（中际旭创/新易盛/天孚/光迅/烽火/中兴…）+ 机器人（优必选/宇树/埃斯顿…），每条含 `name.{en,zh}` + aliases
- **organizations.yaml** +58：ASEAN/BRICS/CSRC/NFRA/海关总署 等政府/国际组织
- **people.yaml** +16：蔡奇/卢拉 等（多数为中文别名缺失，应归 4.1）

### 4.3 关系补录
- `relations.yaml` 新增 `REL_VALUE_TIER`（价值分级）、`REL_SUPPLIES`（供应链）语义（若需）

## 5. 结论

- **45% 评分实体已获 KB 稳定 ID**（251/561），跨语言聚合/画像可用。
- **49% 缺失**（276）：以中国科技供应链公司为主（SEC 美股数据未覆盖），是 KB 扩种的重点。
- **6% 变体**（34）：补别名即可让评分名解析到 KB。
- 建议分批：先补 34 别名（小）+ 新增最高价值 T6-T10 分级实体（国产替代/光通信/机器人核心公司）。

---

## 6. 多维映射模型（2026-08-09, 实体×行业×细分赛道）

> 把评分实体按 **类型 × 行业 × 细分赛道** 建模，关系基数 1:N / N:M / M:1。已入 KB（commit 见下）。

### 6.1 实体类型维度（M:1 → 实体库分类）

| 类型 | 数量 | 入 KB 位置 | 示例 |
|------|:--:|------|------|
| **国家** | 34 | countries.yaml | CTRY_CHN/USA/RUS |
| **组织/机构** | 101 | organizations.yaml | ORG_美联储/东盟/证监会 |
| **公司** | 340 | companies.yaml | COMP_中芯/台积电/NVIDIA |
| **个人** | 84 | people.yaml | PERS_习近平/Trump/鲍威尔 |

### 6.2 行业维度（M:1, 公司→行业）

细分赛道归并到 **9 个行业**（部分已在 GICS 25 类）:

| 行业 | 细分赛道 |
|------|---------|
| **半导体** | GPU/AI芯片/HBM/先进封装/Chiplet/晶圆键合/出口管制/国产替代 |
| **光通信** | 光芯片/激光器芯片/光模块 |
| **算力基础设施** | 服务器/液冷 |
| **机器人** | 机器人/机械臂 |
| **能源** | 石油/核能/核电/反应堆 |
| **军工** | 国防/战争 |
| **金融** | 降息/加息/加密货币 |
| **汽车** | 电动车 |
| **医疗** | 制药 |

### 6.3 细分赛道维度（N:M, 公司 ↔ 赛道）

**28 个细分赛道**已建模为 `IND_SUB_*` 实体（industries.yaml, `sub_of` 指向父行业）：

| 细分赛道 | 公司数 | 代表公司 |
|---------|:--:|---------|
| 先进封装 | 41 | ASMPT/库力索法/EVG/长电/通富/日月光 |
| 光通信 | 40 | 中际旭创/新易盛/天孚/光迅/烽火/中兴 |
| 机器人 | 32 | 优必选/宇树/埃斯顿/ABB/发那科 |
| AI巨头 | 30 | NVIDIA/OpenAI/Anthropic/谷歌/微软 |
| 国产替代 | 30 | 华为/中芯/长江存储/中微/寒武纪 |
| 光芯片 | 9 | 源杰/长光华芯/光库/仕佳光子 |
| 核能 | 9 | 上海电气/东方电气/Kazatomprom |
| HBM | 7 | SK海力士/美光/沪电/深南 |

### 6.4 关系基数

| 关系 | 基数 | 实现 |
|------|------|------|
| **国家 → 公司** | 1:N | company.country 字段 |
| **公司 → 行业** | M:1 | company.industry 字段 |
| **公司 → 细分赛道** | **N:M** | company.sub_segments 字段（已写 150 条关联）|
| **细分赛道 → 父行业** | M:1 | IND_SUB_*.sub_of |
| 组织/机构 → 国家 | M:1 | org.country 字段 |

**N:M 示例**（公司跨多赛道）:
- **TSMC**（6 赛道）: 先进封装/Chiplet/AI芯片/GPU/半导体/出口管制
- **NVIDIA**（5）: GPU/AI芯片/HBM/出口管制/AI巨头
- **中微公司**（3）: 国产替代/先进封装/半导体设备

### 6.5 KB 富化落地（commit `待定`）

- industries.yaml: **+26 细分赛道 IND_SUB_***（中文 ID, sub_of 父行业）→ 25+26=55 行业实体
- companies.yaml: **+150 公司→细分赛道 sub_segments 关联**
- ⚠️ 注意: 细分赛道名与公司名可冲突（如 `HBM` 也解析到 COMP_HUDBAY_MINERALS 股票代码）——评分关键词用赛道、实体识别用公司，分层消费。
