# 实体与实体关系 — 入库数据文档

> 版本: v0.2 · 2026-08-05 · 依据: `references/data-model-upgrade-plan.md`（Schema V0.1）
> 说明: 本文档记录**已入库（云端 PostgreSQL）**的实体 / 实体别名 / 实体关系 / 事件关系。

---

## 1. Schema（4 张实体相关表）

| 表 | 字段 | 说明 |
|----|------|------|
| **entities** | id, name, type, country, importance, aliases(JSONB), confidence, first_seen, last_seen, created_at | 实体主数据（KB + 事件派生合并） |
| **entity_alias** | id, entity_id(FK), alias, lang, created_at | 结构化别名（中英/简称），`entity_id+alias` 唯一 |
| **entity_relationship** | id, from_entity_id(FK), to_entity_id(FK), relation_type, confidence, description, evidence_count, first_seen, last_seen, created_at | 实体-实体关系（KB associations 接入，一等公民） |
| **event_relations** | id, parent_event_id, child_event_id, relation_type, confidence, start_time, end_time, evidence_count, created_at | 事件-事件关系（同 subject 时间序派生 `precedes`） |

迁移: `migrations/versions/0002_entity_upgrade.py`（Alembic，部署时自动执行）。

---

## 2. 入库实体（182 个）

类型分布: **Company 127 / Person 35 / Country 12 / 全球组织 8**

### 2.1 公司（127）— 按国家

| 国家 | 公司 |
|------|------|
| China (50) | AMEC, Alibaba, BYD, ByteDance, CATL, GigaDevice, Huatian Technology, Huawei, ICBC, JCET, Naura, SJ Semiconductor, SMIC, Tencent, Tongfu Microelectronics, YMTC, 中信证券, 中信集团, 中国平安, 中国移动, 中国航发, 中国船舶, 中国软件, 中央汇金投资, 中望软件, 中金公司, 全国社会保障基金理事会, 北方稀土, 华海清科, 国家外汇管理局, 国家集成电路产业投资基金一期/二期/三期, 复星国际, 宝钢股份, 小米集团, 恒瑞医药, 招商银行, 晶科能源, 汇川技术, 沪硅产业, 澜起科技, 网易, 贵州茅台, 达梦数据, 迈瑞医疗, 通威股份, 金风科技, 隆基绿能, 韦尔股份 |
| United States (22) | Amazon, Anthropic, Apple, Applied Materials, Boeing, Broadcom, Chevron, ExxonMobil, Federal Reserve, Goldman Sachs, Google, Intel, JPMorgan, Meta, Micron Technology, Microsoft, NVIDIA, OpenAI, Pfizer, Qualcomm, SEC, SpaceX, Tesla |
| Japan (10) | Bank of Japan, FANUC, Mitsubishi UFJ Financial Group, NTT, Nintendo, Panasonic, SoftBank, Sony, Takeda Pharmaceutical, Tokyo Electron, Toyota |
| South Korea (10) | Coupang, Hyundai Motor, LG Energy Solution, NCSoft, POSCO Holdings, SK Hynix, SK Telecom, Samsung, Samsung Biologics, Samsung Electronics |
| France (4) | Airbus, BNP Paribas, LVMH, TotalEnergies |
| Germany (4) | BMW, Deutsche Bank, Mercedes, Siemens, Volkswagen |
| India (6) | HDFC Bank, ITC Limited, Infosys, Reliance, Sun Pharmaceutical, Tata |
| Russian Federation (4) | Gazprom, Rosneft, Sberbank, Yandex |
| Taiwan (5) | ASE Technology, Foxconn, MediaTek, TSMC |
| United Kingdom (5) | AstraZeneca, BP, Bank of England, HSBC, Shell |
| Iran (1) | Islamic Revolutionary Guard Corps |
| Israel (2) | IDF, Mobileye |
| Netherlands (1) | ASML |
| Saudi Arabia (1) | Saudi Aramco |

### 2.2 人物（35）

| 国家 | 人物 |
|------|------|
| China | Li Qiang, Xi, 蔡奇 |
| United States | Buffett, Gates, J.D. Vance, Jamie Dimon, Jeff Bezos, Jensen Huang, Kevin Warsh, Marco Rubio, Mark Zuckerberg, Musk, Sam Altman, Satya Nadella, Sundar Pichai, Tim Cook, Trump, Warren Buffett, Warsh |
| Iran | Ali Khamenei, Masoud Pezeshkian |
| Israel | Netanyahu |
| Japan | Takaichi Sanae |
| Russian Federation | Mikhail Mishustin, Putin, Sergei Lavrov, Sergei Shoigu |
| Saudi Arabia | Mohammed bin Salman |
| South Korea | Lee Jae Myung |
| Ukraine | Zelensky |
| United Kingdom | Andy Burnham |
| India | Modi |
| France | Macron |
| Germany | Friedrich Merz |

### 2.3 国家（12）
China, France, Germany, India, Iran, Israel, Japan, Russian Federation, Taiwan, Ukraine, United Kingdom, United States

### 2.4 全球组织（8）
European Central Bank, International Monetary Fund, World Bank, WHO, United Nations, NATO, OPEC, European Union

### 2.5 结构化别名（55 条，示例）
Trump: Donald Trump / 特朗普 / 川普 / President Trump · Putin: Владимир Путин / 普京 · Xi: Xi Jinping / 习近平 · Musk: Elon Musk / 马斯克 · Zelensky: 泽连斯基 / Zelenskyy · United States: US / USA / U.S. / America · United Kingdom: UK / Britain · 等

---

## 3. 实体-实体关系（223 条，KB associations 接入）

| 从 | 关系 | 到 |
|----|------|----|
| Trump | appoints | J.D. Vance / Kevin Warsh |
| Trump | works_with | Musk |
| Jensen Huang | leads | NVIDIA |
| Sam Altman | leads | OpenAI |
| Microsoft | invests | OpenAI |
| Apple | partners | OpenAI |
| Huawei | partners / competes | 澜起科技 / Apple / SMIC |
| TSMC | supplies | United States |
| ASML | supplies / export_control | TSMC / SMIC |
| NVIDIA | supplies | TSMC |
| Tesla | competes | BYD |
| SK Hynix / Samsung Electronics | competes | Samsung Electronics / TSMC |
| Iran | conflicts | Israel / United States |
| Iran | member_of | OPEC |
| NATO | conflicts | Russian Federation |
| Putin | conflicts | Zelensky |
| 中信集团 | controls | 中信证券 |
| 中央汇金投资 | invests | 招商银行 |
| 国家集成电路产业投资基金三期 | invests | Naura / SMIC |

---

## 4. 事件-事件关系（28 条，同 subject 时间序派生）

- 关系类型: 全部 `precedes`（事件 A 先于事件 B，同主体时间链，保守无因果断言）
- 覆盖: 20 个 subject 组（如 Trump/Iran/Apple 等多次出现的主体）
- 来源: `backfill_entity_model.py` 从 `events` 表按 `subject_name` 分组、按 `first_seen` 排序派生
- 端点: `GET /api/v1/events/{event_id}/relations` → `{total, relations:[{event_id, direction, relation_type, start_time, end_time}]}`

---

## 5. 数据流与维护

```
entity-network.json (KB, 实体管理UI编辑)
   │ 1) fill_entity_kb.py 补齐事件派生实体
   ▼
data_entity_kb.py (内嵌, 勿手改)
   │ 2) backfill_entity_model.py (backend 容器内跑)
   ▼
云端 PG: entities + entity_alias + entity_relationship + event_relations
   │ 3) API: /api/v1/entities/{name} (aliases+relationships) · /api/v1/events/{id}/relations
   ▼
前端实体画像 / 事件 Dossier
```

**重跑回填**（实体/关系变化后同步 DB）:
```bash
docker compose exec backend python /host/scripts/news-platform-v8/backfill_entity_model.py
```

**补齐 KB**（新事件派生实体并入 KB）:
```bash
python scripts/news-platform-v8/fill_entity_kb.py
```

---

## 6. 已知缺口 / 关联分析（2026-08-07）

- **关系库在生产中几乎不使用**：`relations.yaml`（106 种关系）、`associations`、`entity_relationship` 表在生产 Pipeline 仅被 `ontology_validator.py` 做 REL_ 前缀白名单校验（不读关系内容）；真正的实体-实体关系纯展示层（画像页关系网络 + 配置中心"实体关系"Tab）。
- **配置中心↔Pipeline 回流断裂**：实体管理 Tab 编辑的 `entity-network.json` 不影响 Pipeline 抽取归一（源头是 `knowledge_base/*.yaml`）；本表（DB entities/entity_relationship）为读侧产物。
- 完整分析与升级方案（A 双向同步 / B 统一 ID / C 收敛 canonical，**待决策**）：见 [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)。
