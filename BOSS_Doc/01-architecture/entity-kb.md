# 实体知识库 (Entity KB) 维护手册

> 最后更新: 2026-08-02
> 适用: `/entities` 实体中心 / `/api/v1/entities*` 接口
> 维护方式: **wiki + git 双轨管理** — 本文档为运维前端，权威数据与变更记录在 git 仓库：
>   - 数据源: `references/entity-network.json`
>   - 内嵌副本: `apps/api/data_entity_kb.py`
>   - git 版手册: `references/entity-kb-maintenance.md`
>   - 变更日志: `references/entity-kb-changelog.md`（每次变更追加，与数据同 commit）

---

## 1. 定位与架构（双源）

`/entities` 实体中心的数据来自两个来源，维护方式完全不同：

| 来源 | 内容 | 维护方式 |
|:-----|:-----|:--------|
| **事件派生**（自动） | 实体列表 + 事件数：从 `events` 表的 subject/object/actors 实时统计 | **自动**，Pipeline 每 15 分钟更新，无需人工 |
| **静态知识库 KB**（手动） | 实体的国家归属 / 类型(leaders/business/company/org) / 角色 / 关联网络 / 全球组织 | **手动**，改文件 + 部署 |

```
/entities 列表 = 事件派生实体 (COUNT distinct events) ← 自动
                + KB enrich (country/type/role)       ← 手动
/entities/[name] 画像 = KB 元数据 + 事件 subject/object/actors 匹配
```

**数据流**: Pipeline → events 表 → `/api/v1/entities*`（实时统计 + KB 合并）→ 前端。

## 2. 静态 KB 文件（维护对象）

### 2.1 位置（**两个文件必须同步改**）

| 文件 | 作用 | 加载优先级 |
|:-----|:-----|:----------|
| `references/entity-network.json` | 源文件（编辑用） | 备选 |
| `apps/api/data_entity_kb.py` | **内嵌副本**（打进后端镜像） | **优先** |

> ⚠️ `entities.py:_load_kb()` 先 `from apps.api.data_entity_kb import ENTITY_KB`，成功即用内嵌 py；只有 import 失败才回退 JSON 文件。**只改 JSON、不同步 py，部署后不生效。**

### 2.2 相关数据集（"全世界国家"覆盖的 3 处粒度，2026-08-02 核实）

| 数据集 | 覆盖 | 用途 |
|:-----|:-----|:-----|
| `frontend/src/lib/country-coords.ts` | **195 国 + 别名 (209 条目)** | 地图坐标（全部联合国成员） |
| `scripts/news_intel/config/entity_weights.json` | **340 公司 + 84 人物 + 34 国 + 101 机构**（含中英别名） | 实体识别权重 |
| `references/entity-network.json` + `data_entity_kb.py` | **13 国深度关系** + 8 全球组织 + 16 关联 | 实体画像（领导人/企业/关联） |

> ⚠️ **"全世界所有国家"（195 国）覆盖的是地图坐标库；实体关系画像目前只深度覆盖 13 个关键国家。** 其余 ~182 国只有坐标/权重、无深度实体关系。若需实体关系覆盖全部国家，需扩展 entity-network.json（大工程，列入待办）。

### 2.3 结构

```json
{
  "version": "1.0",
  "generated": "2026-08-02",
  "entities": {
    "United States": {
      "country_code": "US",
      "leaders":    [{"name": "Donald Trump", "role": "President", "importance": 100}],
      "business":   [{"name": "Elon Musk", "company": "Tesla/SpaceX/xAI", "importance": 95}],
      "companies":  [{"name": "Apple", "type": "tech", "importance": 95}]
    }
  },
  "global_orgs": {"NATO": {"type": "military_alliance", "importance": 90}},
  "associations": [{"from": "Donald Trump", "to": "Kevin Warsh", "type": "appoints", "desc": "美联储主席任命"}]
}
```

当前规模: 13 国家 / 8 全球组织 / 16 关联。实体按国家分组，leader/business 是人物、companies 是企业。

## 3. 维护步骤（wiki + git 双轨）

```
① 先更新本文档（记录本次变更：新增/修改了哪些实体）
② 改 references/entity-network.json        ← 加实体 / 改角色 / 加关联
③ 跑 python scripts/news-platform-v8/generate_entity_kb.py  ← 自动同步 py（勿手改 py）
④ 追加 references/entity-kb-changelog.md   ← 变更日志（git 版本化）
⑤ git add + commit + push                 ← 仓库: search-engine-v2（数据+日志同 commit）
⑥ VPS: git pull + docker compose up -d --build backend
   （子目录: /home/administrator/news-platform-v8/scripts/news-platform-v8）
⑦ 验证: curl http://100.107.117.23/api/v1/entities/[name]
```

**别名**: `_find_entity` 已支持 `e.get("aliases", [])`，在实体条目加 `"aliases": ["川普"]` 即可启用中英文别名匹配（当前 KB 无别名数据）。

## 4. AI 维护工作流（wiki + git 双轨）

后续收到"实体库维护 / 加实体 / 改实体信息"需求时，按此流程执行：

```
① 先更新本文档（记录本次变更说明）
② 改 references/entity-network.json
③ 同步 apps/api/data_entity_kb.py
④ 追加 references/entity-kb-changelog.md（变更条目）
⑤ 同一 git commit 提交（wiki 留痕 + git 数据/日志版本化）
⑥ push → VPS 部署 → curl 验证
```

**遵守项目 doc-first 规则**：文档先行，数据+变更日志进 git（wiki 本身不进 git，但变更在本文档与 git changelog 双向留痕）。

## 5. 已知缺口 / 待办

- [x] **实体管理 UI**：已上线 — 配置中心"实体管理"Tab（编辑→校验→保存热生效→同步Git）。
- [ ] **别名数据填充**：代码支持 aliases，目前仅日本有别名（高市早苗）。
- [ ] **自动文章 URL 完整度**：50/168 事件 evidence URL 为空，影响实体→事件关联完整性（聚合器优化）。
- [ ] **配置中心↔Pipeline 实体回流断裂（2026-08-07 分析）**：实体管理 Tab 编辑的 `entity-network.json` 只影响画像/回填，**不影响 Pipeline 抽取归一**——抽取源头是 `knowledge_base/*.yaml`（KB V1）。升级方案 A（双向同步）/B（统一事件-Fact 实体 ID）/C（收敛 canonical）**待决策**，见 [entity-management-pipeline-analysis.md](entity-management-pipeline-analysis.md)。
- [ ] **事件/Fact 实体 ID 双轨（2026-08-07）**：事件层用 `aggregator._entity_name_to_id` 本地生成 ID，Fact 层用 KB V1 稳定 ID，云端无法按 entity_id 跨表关联，只能 name 匹配。方案 B 统一。
