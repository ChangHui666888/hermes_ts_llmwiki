# BOSS_Doc 索引

News Intelligence Platform 操作手册。

## 目录

### 01-architecture — 架构设计

| 文档 | 说明 |
|------|------|
| [系统架构](01-architecture/system-architecture.md) | 整体架构：Pipeline → FastAPI → PostgreSQL → Next.js |
| [🎨 前端](01-architecture/frontend.md) | **最新** Next.js 16 页面/组件/API调用/认证 |
| [⚙️ 后端](01-architecture/backend.md) | **最新** FastAPI 23端点/数据模型/认证机制 |
| [🗄️ 数据库](01-architecture/database.md) | **最新** PostgreSQL 20表/ER图/常用查询 |
| [Phase 1 事件资产](01-architecture/phase1-event-asset.md) | 第一阶段定位、Schema、8大卖点、7模块、KPI |
| [五维评分规则](01-architecture/scoring-rules.md) | 五维评分细则 (Source/Impact/Entity/Market/Velocity) |
| [数据流-字段映射](01-architecture/data-flow-fields.md) | 每环节产生哪些字段 + 表关系图 |
| [Pipeline L0-L7 规则](01-architecture/pipeline-l0-l7-rules.md) | 基于代码的加工规则/参数/阈值 |
| [🧩 实体库维护](01-architecture/entity-kb.md) | **最新** 实体库双源架构 + AI维护工作流 (wiki→JSON+py→部署) |

### 02-deployment — 部署运维

| 文档 | 说明 |
|------|------|
| [☁️ 云主机环境](02-deployment/cloud-env.md) | **最新** VPS、Docker、nginx、PostgreSQL |
| [💻 本地开发环境](02-deployment/local-env.md) | **最新** Hermes、Python、项目路径、数据流 |
| [☁️ 云主机部署](02-deployment/cloud-deploy.md) | Docker Compose 部署 (Next.js + FastAPI + PostgreSQL) |
| [备份与恢复](02-deployment/backup-restore.md) | Git + 全量备份策略、一键恢复 |

### 03-commands — 命令速查

| 文档 | 说明 |
|------|------|
| [全部命令速查](03-commands/all-commands.md) | Hermes / Cron / RSS / Pipeline / Docker / 备份 / DB |

### 04-config — 配置文件

| 文档 | 说明 |
|------|------|
| [Cron 配置](04-config/cron-jobs.md) | rss-scan + auto-pipeline 计划任务 |

### 05-troubleshooting — 排障

| 文档 | 说明 |
|------|------|
| [RSS 源隔离](05-troubleshooting/rss-quarantine.md) | 隔离规则、重置方法 |
| [Cron 排障](05-troubleshooting/cron-debug.md) | 日志位置和解读 |

### 📦 history — 过程记录归档

| 说明 |
|------|
| [📂 18 份历史开发笔记](history/README.md) | Phase 1 升级、V4.1-V4.3 聚合规则、评分详解等 |

## Git 仓库

| 仓库 | URL | 可见性 |
|------|-----|:------:|
| search-engine-v2 | `https://github.com/ChangHui666888/search-engine-v2` | 🔒 私有 |
| 主备份 | `https://github.com/ChangHui666888/hermes-agent-backup` | 🌐 公开 |

**每次开发必须提交 git**，文档与代码放在同一个 commit。

## 📋 快速参考

| 说明 |
|------|
| [API 全量测试](../scripts/news-platform-v8/test_api.py) | 全量端点测试 (25/25 通过, 支持 --mock) |
| [自动部署](../scripts/news-platform-v8/deploy-vps.py) | SSH 自动部署 (git pull + docker compose) |
| [Cron 部署](../scripts/hermes-cron/deploy-cron.py) | 项目→Hermes 脚本部署 |
| [完全重跑聚合](../scripts/reaggregate_all.py) | 备份→清空→重聚合→推送 |
| [配置同步](../scripts/hermes-cron/config-agent.py) | 本地配置接收 agent (:8890) |
| [实体知识库](../references/entity-knowledge-base.md) | 全球关键实体按国家+关联 |
| [Demo 验证](../scripts/demo.py) | Pipeline 8 场景 Mock 验证 |
