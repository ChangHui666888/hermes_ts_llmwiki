# 本地开发环境

> 最后更新: 2026-08-02

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
| RSS 数据库 | `~/.hermes/rss-archive.db` | 94 源原始 RSS 文章 |
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
│  FastAPI (23 endpoints) → PostgreSQL (512 events, 936 文章)  │
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
