# 本地开发环境

> 最后更新: 2026-08-08

## 工作站信息

| 项目 | 值 |
|------|-----|
| OS | Windows 11 Pro |
| 版本号 | 10.0.26100 |
| 用户名 | ChangHui |
| Tailscale IP | `100.126.188.44` (desktop-iu8hlao) |
| Node.js | v24.16.0 |
| Python | 3.11.9 |
| Git | 2.54.0.windows.1 |
| Shell | Git Bash (MSYS2) |

---

## Hermes Agent

| 项目 | 值 |
|------|-----|
| 版本 | v0.17.0 (2026.6.19) |
| 安装路径 | `C:\Users\ChangHui\AppData\Local\hermes\hermes-agent` |
| 配置文件 | `C:\Users\ChangHui\AppData\Local\hermes\config.yaml` |
| 密钥文件 | `C:\Users\ChangHui\AppData\Local\hermes\.env` |
| Python 虚拟环境 | `C:\Users\ChangHui\AppData\Local\hermes\hermes-agent\venv` |

---

## 三环境路径拓扑（2026-08-08 确认）

| 环境 | 路径 |
|------|------|
| **开发** | `C:\Users\ChangHui\.hermes-web-ui\coding-agent\workspace\default\global\search-engine-v2`（git 仓库，改代码处） |
| **生产** | `C:\Users\ChangHui\AppData\Local\hermes\profiles\outside-deepdeek\skills\research\search-engine-v2`（auto-pipeline 真实运行处：news_intel/config 等） |
| **生产 cron** | `C:\Users\ChangHui\AppData\Local\hermes\scripts`（rss-scanner.py / auto-pipeline.py wrapper / config-agent 执行处） |

**部署流向**：
- cron 脚本（wrapper）→ `deploy-cron.py --apply` → **生产 cron** 目录。
- 生产 cron 的 `auto-pipeline.py`/`rss-scanner.py`(wrapper) → dispatch 到 **生产 profile** 的真实脚本。
- **config/ 包**：留**生产 profile**（scanner 的 sys.path 指向生产 scripts/ 导入 config.loader），**不复制到 cron**（2026-08-08 修正）。
- ⚠️ 修改 pipeline 代码（scorer/canonicalizer/aggregator/sync 等）或 **评分配置 JSON**（config/*.json）后，必须 `python scripts/sync_profile.py --apply` 同步生产 profile，并 `--check` 确认差异=0。
  - `sync_profile` 已纳入 `config/*.json`（v2.3 修复，勿再手动 cp）；`git push` **不会**自动到生产 profile。

## 部署必查清单（2026-08-08 教训, ISS-009）

1. **改任何配置/代码 → `sync_profile.py --apply`**（git push ≠ 已部署到生产）。
2. **部署后验证生产实际生效**：查 `pipeline.log` 新逻辑特征（如 sync 修复后 `SYNC+SCORE` 不再 0）、`sync_state.rss_last_synced_at` 是否推进。
3. **文章不涨时**：先查 `sync_state.rss_last_synced_at` 是否卡旧时刻 + `pipeline.log` `SYNC+SCORE: 0 ok` → 游标 tie 卡死（已用复合游标 `created_at|id` 修复）。
4. **游标同步一律复合游标 (created_at, id)**，勿用单时间戳 `>=`。

## 开发规则：计划任务入口文件迁移（2026-08-08 新增）

**涉及计划任务入口文件时，提交同步到本地生产后，需从生产环境迁移到计划任务入口 `C:\Users\ChangHui\AppData\Local\hermes\scripts`：**
1. **只迁移入口文件**（wrapper/薄脚本），**不迁移依赖文件**（config/news_intel 等留生产 profile）。
2. 迁移时检查入口文件的**引用/依赖路径**——必须指向**生产环境** `C:\Users\ChangHui\AppData\Local\hermes\profiles\outside-deepdeek\skills\research\search-engine-v2\scripts\...`（非测试/开发）。
3. 检查冲突；原路径不够明确已修正。

**cron 入口文件模式**（薄 wrapper dispatch 到生产 profile）：
- `auto-pipeline.py` → `../profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/auto-pipeline.py`
- `rss-scanner.py` → `../profiles/outside-deepdeek/skills/research/search-engine-v2/scripts/hermes-cron/rss-scanner.py`（2026-08-08 改 wrapper，移除 cron/config/ 副本）
- `config-agent-keepalive.py` → 生产 profile 的 `hermes-cron/config-agent.py`

**部署**：`deploy-cron.py --apply` 只部署入口文件（DEPLOY_MAP 用 wrapper）；依赖留生产 profile。

### 模型配置

| 配置项 | 值 |
|--------|-----|
| 默认模型 | `qwen3-1.7b-instruct` |
| Provider | `lmstudio` (本地) |
| 当前会话模型 | DeepSeek v4 Flash (Coding Agent) |

### Cron 任务

| 名称 | 频率 | 脚本 | 状态 |
|------|:----:|------|:----:|
| rss-scanner | every 5m | `rss-scanner.py` | ✅ 活跃 |
| auto-pipeline | every 15m | `auto-pipeline.py` | ✅ 活跃 |
| config-agent | every 5m | `config-agent.py` | ✅ 活跃 (keepalive) |

> 注意：Hermes Cron 在 `~/.hermes/scripts/` 按文件名引用脚本，不支持完整路径。
> 开发版脚本在项目 `scripts/hermes-cron/` 中，改完后需用 `deploy-cron.py --apply` 部署回去。
> cron 验证: `hermes cron list`（rss-scanner 5m / auto-pipeline 15m / config-agent 保活）。

### 脚本统一管理（2026-08-02 优化）

> 约定：**所有 Hermes 相关脚本统一放在 `C:\Users\ChangHui\AppData\Local\hermes\scripts\`**，不再散落到用户主目录根。
> 主目录根（`C:\Users\ChangHui\`）只保留系统/工具点目录与数据目录（如 `wiki\`），不放任何脚本。

| 脚本 | 用途 | 备份覆盖 |
|------|------|:--:|
| `scripts\hermes-start.cmd` | 开机自启：Gateway + Dashboard（后台） | ✅ git + F: 全量 |
| `scripts\hermes-wiki.cmd` | Wiki+Hermes 启动中心（更新图谱 + 注册 wiki-sync cron + 启动 hermes） | ✅ git + F: 全量 |
| `scripts\wiki-start.cmd` | 更新图谱 + 打开 Obsidian + Graph | ✅ git + F: 全量 |
| `scripts\wiki-push.cmd` | 一键推送 wiki 到 git | ✅ git + F: 全量 |
| `scripts\git-backup.sh` / `full-backup.sh` / `restore.bat` 等 | 备份/恢复体系 | ✅ git + F: 全量 |

**开机自启链路**：Startup 文件夹 `hermes-start.vbs` → `%LOCALAPPDATA%\hermes\scripts\hermes-start.cmd`
（若调整脚本路径，必须同步更新该 vbs。）

> 备注：`content-factory/` 个人项目已移至 `Documents\content-factory\`。

---

## Python 环境

### 核心依赖包

| 包 | 版本 | 用途 |
|---|:----:|------|
| httpx | 0.28.1 | HTTP 客户端 (连接池 + HTTP/2) |
| fastapi | 0.133.1 | Web API 框架 |
| uvicorn | 0.41.0 | ASGI 服务器 |
| feedparser | 6.0.12 | RSS/Atom 解析 |
| trafilatura | 2.1.0 | HTML 正文抽取 |
| playwright | 1.60.0 | 浏览器自动化 |
| scrapling | 0.4.9 | TLS 指纹浏览器 |
| paramiko | - | SSH 客户端 |
| sqlalchemy | - | ORM |
| psycopg2-binary | - | PostgreSQL 驱动 |

---

## 项目位置

### 主要项目

| 项目 | 路径 | 说明 |
|------|------|------|
| **search-engine-v2** (开发版) | `~/.hermes-web-ui/coding-agent/workspace/default/global/search-engine-v2/` | Coding Agent 工作区，所有开发在此进行 |
| **search-engine-v2** (部署版) | `C:\Users\ChangHui\AppData\Local\hermes\profiles\outside-deepdeek\skills\research\search-engine-v2\` | Hermes Profile 中的正式版本 |
| **news-platform-v8** | 云主机 `/home/administrator/news-platform-v8/` | Web 可视化平台 (Next.js 16 + FastAPI) |

### Git 仓库

- 主仓库: `https://github.com/ChangHui666888/hermes-agent-backup`
- Web 独立: `https://github.com/ChangHui666888/sentinel-intelligence`

---

## BOSS_Doc Wiki

| 项目 | 值 |
|------|-----|
| 路径 | `C:\Users\ChangHui\wiki\BOSS_Doc\` |
| 文件数 | 27 个 |
| 归档记录 | 18 个 (在 `02-deployment/过程记录/`) |

---

## 数据存储 (本地)

### RSS 数据库

| 文件 | 路径 | 说明 |
|------|------|------|
| RSS 数据库 | `~/.hermes/rss-archive.db` | 197 源原始 RSS 文章 (V4 Feed Registry, 2026-08-08) |
| 状态文件 | `~/.hermes/rss-scanner-state.json` | 死源隔离 + 去重游标 |
| 报告文件 | `~/.hermes/rss-scanner-report.json` | 每次扫描统计 |

### Pipeline 数据库

| 文件 | 路径 | 说明 |
|------|------|------|
| 主数据库 | `profiles/.../search-engine-v2/scripts/news_intel/news_intel.db` | 评分 + 抓取 + 事件聚合 |
| Pipeline 日志 | `profiles/.../search-engine-v2/scripts/pipeline.log` | auto-pipeline 运行日志 |
| Backlog 清理 | `scripts/news_intel/cleanup_backlog.py` | C 级老文章归档清理（`--dry-run` 安全） |

### RSS 日报

```
~/wiki/RSS-Digest/{YYYY-MM-DD}.md
```

---

## 数据流总览

```
┌─────────────────────────────────────────────────────────────┐
│  本地 Windows                                               │
├─────────────────────────────────────────────────────────────┤
│  rss-scanner.py (cron 5m)                                    │
│    → httpx + feedparser → ~/.hermes/rss-archive.db          │
│                                                              │
│  auto-pipeline.py (cron 15m)                                 │
│    Step1 sync.py: rss-archive.db → 评分 → news_intel.db     │
│    Step2 RSS 描述兜底 + Step3 batch.py 全文抓取 (级联)       │
│    Step4 fact_pipeline: GLiNER+Qwen 事实抽取 (payload 文件)  │
│    Step4.5 aggregator: 事件聚类 (fused 指纹)                 │
│    Step5/6: HTTP POST → 云主机 (events + news content)       │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP (Tailscale 内网 + Internal Token)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  云主机 Ubuntu 24.04                                        │
├─────────────────────────────────────────────────────────────┤
│  Nginx (:80)                                                │
│    ├── /api/* → FastAPI (:8000)                             │
│    ├── /internal/* → FastAPI (:8000)  ← Pipeline 推送入口   │
│    └── /* → Next.js (:3000)                                 │
│                                                              │
│  FastAPI (60 endpoints) → PostgreSQL (27 ORM 表)             │
│                                                              │
│  辅助服务: SearXNG (:8080) + sing-box VPN (:443)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 常用命令

```bash
# 本地开发
cd ~/.hermes-web-ui/coding-agent/workspace/default/global/search-engine-v2

# Demo 验证
python scripts/demo.py

# 部署 Cron 脚本回 Hermes 目录
python scripts/hermes-cron/deploy-cron.py --apply

# 查看 Cron 差异
python scripts/hermes-cron/deploy-cron.py --check

# SSH 到云主机
ssh administrator@100.107.117.23

# RSS 手动扫描
python ~/.hermes/scripts/rss-scanner.py

# 查看 RSS 数据库
sqlite3 ~/.hermes/rss-archive.db "SELECT count(*) FROM rss_articles"
```

---

## SSH 配置

| 项目 | 值 |
|------|-----|
| 主机 | `100.107.117.23` |
| 用户 | `administrator` |
| 密码 | `root123root!@` |
| 密钥 | `~/.ssh/id_ed25519` (**已注册到云主机**) |
| 连接 | **Tailscale 直连** (SSH config 无代理) |
| Host Key | ED25519 + RSA + ECDSA (已记录在 known_hosts) |

> 密码存储位置: `C:\Users\ChangHui\AppData\Local\hermes\.env` → `CLOUD_SSH_PASS`
> SSH 密钥已注册, 免密登录。SOCKS 代理不稳定时用直连。

---

## 测试与部署验证（2026-08-08 补全）

### 测试决策表（改 X → 跑哪些测试）

| 改动环节 | 测试命令 |
|---------|---------|
| Pipeline 编排 (`auto-pipeline.py`) | `python demo.py`（8 场景 Mock） |
| 评分 (`scorer.py`) | `python demo.py` + 跑一轮 auto-pipeline |
| 抓取 (`core/` `batch.py`) | `python test_fetch.py` |
| 视频抓取 (Step 3.6) | `python test_video_fetch.py` |
| Fact 抽取 | `python demo.py` + 查 fact 日志 |
| 聚合 (`aggregator.py`) | `python test_aggregator.py` |
| 中文聚合 (v4.4.3) | `python test_chinese_aggregation.py` |
| 域名画像 | `python test_profiles.py` |
| 后端 API | `python scripts/news-platform-v8/test_api.py` |
| 端到端 | `python test_e2e.py` |
| 前端 | VPS 浏览器检查 + `curl /api/v1/*` |

### 部署验证步骤

```bash
# ① dev → 本地生产 profile 同步
python scripts/sync_profile.py --check   # 看差异 (应为 0)
python scripts/sync_profile.py --apply   # 同步 (自动备份)

# ② cron 入口同步 (wrapper 指向生产 profile)
python scripts/hermes-cron/deploy-cron.py --apply

# ③ 云端 Web 部署
ssh administrator@100.107.117.23
cd /home/administrator/news-platform-v8 && git pull
cd scripts/news-platform-v8 && docker compose up -d --build
curl http://100.107.117.23/api/v1/dashboard   # 验证 200

# ④ 流水线健康
tail -20 ~/AppData/Local/hermes/profiles/outside-deepdeek/.../scripts/pipeline.log  # 最近 DONE in
```
