# 流水线监控看板 — 指标设计与诊断导向

> 版本: v1.0 · 2026-08-08 · 状态: 🟢 已设计
> 目的: **发现异常、定位瓶颈、指向修复/优化/配置**，为系统功能与性能提升提供导向。
> 数据源: 本地 `rss-scanner-report.json` + `pipeline.log` + `news_intel.db` + VPS PG/dashboard。
> 相关: [business-process.md](../01-architecture/business-process.md) · [pipeline-l0-l7-rules.md](../01-architecture/pipeline-l0-l7-rules.md)

---

## 1. 监控目的分层

| 层 | 功能 | 示例 |
|----|------|------|
| ① 健康层 | 系统是否存活 | 成功率 / API 可用 / 是否 DONE |
| ② 异常层 | 哪里不对劲 | 阈值告警 + 异常含义 |
| ③ 定位层 | 具体在哪 | 下钻: 环节→源/域名/文章/队列 |
| ④ 瓶颈层 | 卡在哪个环节 | 步骤耗时对比 + 吞吐 |
| ⑤ 导向层 | 怎么修 | 指标→建议动作 |

## 2. 数据源

| 源 | 位置 | 环节 |
|----|------|------|
| `rss-scanner-report.json` | 本地 `~/.hermes/` | 采集 |
| `pipeline.log` | 生产 profile `scripts/pipeline.log` | 评分/Fact/聚合/归一/推送 |
| `news_intel.db` | 生产 profile `scripts/news_intel/` | 评分/事件 |
| `fetch_stats` 表 | VPS PG | 抓取 |
| PostgreSQL | VPS | articles/events/fact/story |
| `/api/v1/dashboard` | VPS | 整体 KPI |

## 3. 核心环节诊断矩阵（异常阈值→定位→优化）

### 采集（rss-scanner）
| 指标 | 异常阈值 | 指向 | 下钻定位 | 优化导向 |
|------|---------|------|----------|----------|
| 采集成功率 | <95% | 网络/源失效 | feeds_detail 失败源+error(SSL/超时/404) | 隔离/修URL/换源 |
| 隔离源数 | 突增>10 | 代理故障 | 隔离源清单 | 查代理 |
| ETag 未变率 | <30% | 源不支持304 | 未变源 | 流量大→调tier |
| 新增文章 | 骤降 | 源限流 | 按源新增曲线 | 查限流 |

### 评分（scorer）
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| Tier A 占比 | <2% | 高分文章少/配置 | score_breakdown 各维 | 调权重 |
| 某维骤降 | 降>30% | 对应维度数据源 | 分维曲线 | 检查 entity_weights 等 |
| 评分耗时 | >180s | sync慢/量大 | 单轮明细 | 增量优化 |

### 抓取（batch）
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| 抓取成功率 | <80% | 反爬/付费墙/失效 | fetch_stats 按域名 | 调 domain_profiles |
| browser 占比 | >30% | 策略链低效 | 策略分布 | 优化策略顺序 |
| 失败域名 TOP | 持续>50% | 该源反爬 | 具体域名 | 降级/排除 |

### Fact 抽取（核心质量）
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| 抽取成功率 | <90% | Qwen/GLiNER 故障 | FACT_45 明细 | 查模型服务 |
| OTHER 动作占比 | >50% | 抽取质量差 | 哪些文章 OTHER | prompt/抽取器 |
| 主体落地率 | <90% | canonicalizer/KB | 未落地实体 | 补KB |
| Qwen 耗时 | >15s | 硬件瓶颈 | avg/max | noThink/降B占比 |

### 聚合（核心瓶颈）
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| marked=0 | 连续2轮 | 聚合停产 | 阈值/指纹/源分散 | 调 event_threshold/查指纹 |
| 聚合耗时 | >60s | 量大 | 每轮明细 | 增量/分块 |
| 事件合并率 | deleted>10% | 重复标题 | 重复清单 | 归一逻辑 |

### 推送（可靠性）
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| 推送失败 | >0 | 网络/后端 | 哪个chunk/端点 | 重试/查后端 |
| 推送量骤降 | >50% | 上游减产 | 产量链 | 定位上游 |

### 整体
| 指标 | 异常阈值 | 指向 | 下钻 | 优化导向 |
|------|---------|------|------|----------|
| pipeline 未DONE | 超时>15min | 某步卡死 | 日志时间戳断点 | 定位环节 |
| 步骤耗时占比 | 某步>40% | 瓶颈环节 | 各步骤耗时 | 优化该环节 |
| API 健康 | ≠200 | Web故障 | curl各端点 | 查nginx/后端 |

## 4. 交叉关联（链路级联诊断）

```
新增文章少 → 评分少 → Fact少 → 聚合marked低   （采集源头问题）
抓取失败多 → 正文缺失 → Fact质量差(OTHER高)  （抓取→Fact 传导）
源分散 → 聚合覆盖低                          （ISS-008 观察项）
Qwen耗时高 → 单轮总时长涨 → pipeline慢        （硬件瓶颈）
```

## 5. 看板视图（6 张）

| 视图 | 内容 |
|------|------|
| ① 健康总览 | 4 核心成功率 + API 健康 + 是否 DONE |
| ② 成功率 | 采集/抓取/Fact/聚合/推送 各成功率 + 告警 |
| ③ 产量趋势 | 新增文章/事件/fact/story 时序 |
| ④ 质量 | Tier A 占比 / OTHER 占比 / 主体落地 / 重复率 |
| ⑤ 瓶颈耗时 | 各步骤耗时对比 + 单轮总时长 |
| ⑥ 源健康 | 隔离源 / ETag未变率 / 失败源 TOP / 16类分布 |

## 6. 告警规则（核心）

| 规则 | 触发 |
|------|------|
| 成功率告警 | 采集<95% / 抓取<80% / Fact<90% / 推送 fail>0 |
| 聚合停产 | marked=0 连续 2 轮 |
| 卡死告警 | pipeline 未 DONE 且超时>15min |
| 质量告警 | OTHER>50% / Tier A<2% |
| 健康告警 | API ≠200 |

## 7. 实现

- 采集: `scripts/monitor_pipeline.py`（解析本地 report + pipeline.log 尾部 + news_intel.db → 指标 JSON，**实测 0-16ms 轻量**）
- 推送: `monitor_pipeline.py --push` → VPS `/internal/monitor`（INTERNAL_TOKEN）
- **定时任务**: `monitor-pipeline` **every 15m**（2026-08-09 建成）— cron wrapper `~/AppData/Local/hermes/scripts/monitor-pipeline.py` dispatch 到生产 profile，jobs.json 注册。⚠️ 依赖已纳入 `sync_profile.py` SYNC_LIST + `deploy-cron.py` DEPLOY_MAP（新脚本必加，否则生产无此脚本——2026-08-09 教训: 曾致看板数据停更 08-08T12:25）。
- **Web 看板**: **`http://100.107.117.23/admin`**（管理后台 "流水线监控"板块）— 后端 `GET /api/v1/monitor`，前端 admin 页 MonitorSection + SVG 趋势图（2026-08-08 已浏览器验证 ✅）
- 本地 HTML 备用: `monitor_dashboard.py` → `~/.hermes/monitor.html`
- **变化跟踪**: 每轮追加富快照 `~/.hermes/monitor-history.jsonl`（events/articles/tier），输出 `变化` 增量
- **时间轴图**: 事件总数 / 评分文章 / Tier A 占比 3 张 SVG 折线图（无依赖、离线、轻量）

## 8. 诊断增强（2026-08-08 v1.1 / v1.2）

| 增强 | 解决挑战 |
|------|---------|
| **步骤耗时**（pipeline.log 各 Step 间隔）| 瓶颈层：Fact 145s 可定位最大耗时环节 |
| **聚合输入关联**（unassigned/facts/marked）| C1：marked=0 需 `unassigned>0` 才告警（区分"无输入"vs"聚合失败"） |
| **抓取统计**（VPS fetch_stats by_strategy + 失败域名 + browser占比 + 成功率）| 抓取环节：direct/browser/jina 成功率 + 失败域名定位 |
| **VPS 全局计数**（articles/events/fact/story）| 整体规模 + 各库变化 |
| **评分分维度**（五维均分 source/impact/entity/market/velocity）| "某维 score 骤降" 监控 |
| **推送量骤降**（history cloud_sync 对比）| 推送可靠性 |
| **API 健康** | Web 可用性 |

**看板 v1.2（业务流顺序）**：⑦ 阶段按 采集→评分→抓取→Fact→聚合→推送→整体 编排，每阶段卡片含 监控项/当前值/异常判定(🟢🔴)/阈值提示。浏览器验证 ✅ 顺序正确。

**实测**：步骤耗时 Fact 145s（瓶颈）· 聚合 unassigned=492/facts=50/marked=0（真实异常）· 抓取 direct 1240ok/10fail · 评分五维 source 10.5/impact 14/entity 5.4/market 5.5/velocity 0.3 · VPS events 259/fact 4832/story 74。
- 展示: HTML 看板 / 前端 `/monitoring` 页（后续可选）
- 告警: 定时运行脚本比对阈值 → 输出异常清单

> ⚠️ **轻量原则**: 只读 pipeline.log 尾部 150KB + 3 条 SQLite 查询 + 小 JSON，按需运行不驻留，不拖累系统。DB 变化用增量（本轮 vs 上轮），历史 jsonl 每轮追加一条。
