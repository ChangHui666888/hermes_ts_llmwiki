# BOSS_Doc 索引

News Intelligence Platform 操作手册。

## 目录

### 01-architecture — 架构设计

| 文档 | 说明 |
|------|------|
| [系统架构](01-architecture/system-architecture.md) | 整体架构：Hermes → FastAPI → PostgreSQL → Vue |
| [Phase 1 事件资产](01-architecture/phase1-event-asset.md) | 第一阶段定位、Schema、8大卖点、7模块、KPI |
| [数据流](01-architecture/data-flow.md) | 八层流水线：RSS → 评分 → 分流 → 抓取 → 抽取 → 校验 → 增强 → 入库 |
| [评分规则](01-architecture/scoring-rules.md) | 五维评分细则（Source/Impact/Entity/Market/Velocity） |
| [安全架构](01-architecture/security.md) | UFW + DOCKER-USER + IP白名单 |

### 02-deployment — 部署运维

| 文档 | 说明 |
|------|------|
| [云主机部署](02-deployment/cloud-deploy.md) | Docker Compose 部署 PostgreSQL + FastAPI + Vue |
| [本地环境](02-deployment/local-setup.md) | Hermes 配置、Python 环境、Git 仓库 |
| [安全加固](02-deployment/security-hardening.md) | UFW 配置、DOCKER-USER 链、端口管理 |
| [备份与恢复](02-deployment/backup-restore.md) | Git + 全量备份策略、一键恢复 |

### 03-commands — 命令速查

| 文档 | 说明 |
|------|------|
| [Hermes 命令](03-commands/hermes-commands.md) | config / cron / model 等常用命令 |
| [RSS 命令](03-commands/rss-commands.md) | RSS 扫描器操作 |
| [Pipeline 命令](03-commands/pipeline-commands.md) | news-pipeline 评分/增强/推送 |
| [Docker 命令](03-commands/docker-commands.md) | 云主机 Docker 管理 |
| [数据库查询](03-commands/db-queries.md) | SQLite / PostgreSQL 常用查询 |

### 04-config — 配置文件

| 文档 | 说明 |
|------|------|
| [Hermes 模型配置](04-config/hermes-model.md) | 模型切换 deepseek-v4-pro |
| [评分配置](04-config/scoring-config.md) | source_scores / event_keywords / entity_weights / asset_graph |
| [Cron 配置](04-config/cron-jobs.md) | rss-scan + news-pipeline 计划任务 |
| [Docker Compose](04-config/docker-compose.md) | docker-compose.yml 详解 |

### 05-troubleshooting — 排障

| 文档 | 说明 |
|------|------|
| [RSS 源隔离](05-troubleshooting/rss-quarantine.md) | 隔离规则、重置方法 |
| [Qwen 超时](05-troubleshooting/qwen-timeout.md) | 本地模型超时处理 |
| [端口冲突](05-troubleshooting/port-conflict.md) | 8000/8001/8080 端口占用 |
| [cron 日志](05-troubleshooting/cron-logs.md) | 日志位置和解读 |
