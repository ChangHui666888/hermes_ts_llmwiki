# 备份与恢复

## 备份体系

| 类型 | 调度器 | 频率 | 目标 | 保留 | 脚本 |
|------|------|:--:|------|:--:|------|
| Git 远程 | Task Scheduler | 每日 12:00 | GitHub | 永久 | `git-backup.sh` |
| 全量本地 | Task Scheduler | 每日 18:00 | F:\hermes-backup | 14天 | `full-backup.sh` |

## 调度分工

| 任务 | 调度器 | 频率 |
|------|------|:--:|
| rss-scan | Hermes Cron | 5min |
| news-pipeline | Hermes Cron | 30min |
| git-backup | **Windows Task Scheduler** | 每日 12:00 |
| full-backup | **Windows Task Scheduler** | 每日 18:00 |

循环任务 → Hermes Cron；固定时间 → Task Scheduler。

## Windows Task Scheduler 创建

```powershell
# 管理员 PowerShell 执行
schtasks /create /tn "Hermes-Git-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\git-backup.sh" /sc daily /st 12:00 /f
schtasks /create /tn "Hermes-Full-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\full-backup.sh" /sc daily /st 18:00 /f
```

## 备份产物位置

```
F:\hermes-backup\
├── restore.bat                   ← 一键恢复脚本 (常驻备份盘, 每次备份自动刷新)
├── hermes_YYYY-MM-DD_HH-MM\      ← 每个备份为一个日期目录
│   ├── backup.ok                 ← 完成标记 (恢复时只认带此标记的备份)
│   ├── config.yaml               ← 配置
│   ├── .env                      ← 环境变量/密钥
│   ├── scripts\                  ← 全部脚本
│   ├── .hermes-home\             ← ~/.hermes 用户目录 (rss-archive.db + config-agent 配置)
│   └── ...                       ← hermes 全目录镜像 (已排除 node/cache/.git 等)
├── logs\
│   └── full-backup.log           ← 全量备份日志
└── state\
    └── last-success              ← 最近成功时间
```

> full-backup 排除项：`node, cache, audio_cache, image_cache, sessions, sandboxes, lsp, mcp-installs, gateway-service, hermes-agent, bin, .git, __pycache__, bk, 新建文件夹`；文件：`*.pyc *.log *.lock *.pid *.rar state.db-shm state.db-wal` 等。
> `.env`、`auth.json`、`config.yaml` **会**被备份，恢复后无需重新配置。

## 备份内容清单（源项目备份了哪些文件）

> 依据最新备份实测（`hermes_2026-08-02_13-50`，324MB / 3258 文件）。恢复目标为 `%LOCALAPPDATA%\hermes`，与源目录 `C:\Users\ChangHui\AppData\Local\hermes` 结构一致。

### 顶层备份的文件

| 文件 | 说明 | 大小 |
|------|------|:--:|
| `config.yaml` / `.bak` / `config.yaml.corrupt.*.bak` | 主配置 + 历史配置备份 | ~50KB |
| `.env` | 环境变量/密钥（**会**备份，恢复后无需重配） | 24KB |
| `auth.json` | 认证凭据池 | 2KB |
| `state.db` | 主状态库（WAL 模式，备份前已 checkpoint） | 39MB |
| `kanban.db` / `rss-archive.db` / `verification_evidence.db` | 各业务库 | ~150KB |
| `channel_directory.json`、`processes.json`、`gateway_state.json` | 运行时配置/状态 | <1KB |
| `SOUL.md`、`.gitignore`、`.hermes_history`、`backup.ok` | 系统文件/完成标记 | — |

### 顶层备份的目录

| 目录 | 说明 | 大小 |
|------|------|:--:|
| `profiles/` | **4 个 profile**（c0orchestrator/devteam/medteam/outside-deepdeek），含各 profile 的 config.yaml、auth.json、state.db、news_intel.db、cron/、memories/ 等 | 200MB |
| `workspace/` | 工作区（system/pipelines 等） | 55MB |
| `skills/` | 技能库（search-engine-v2 等） | 17MB |
| `state-snapshots/` | 历史状态快照 | 14MB |
| `cron/`、`kanban/`、`memories/`、`plugins/`、`pending/` | 调度/看板/记忆/插件/待处理 | <1MB |
| `scripts/`、`hooks/`、`platforms/`、`pairing/`、`runtime/`、`logs/`、`backup-state/` | 脚本/钩子/平台/配对/运行时/日志/备份状态 | <200KB |

### 被排除的内容（不备份）

| 类型 | 项目 |
|------|------|
| 可重装/可再生成 | `node`、`node_modules`、`cache`、`audio_cache`、`image_cache`、`sessions`、`sandboxes`、`lsp`、`mcp-installs`、`gateway-service`、`hermes-agent`(venv)、`bin`、`__pycache__`、`.git` |
| 运行时 churn | `*.lock`、`*.pid`、`*.log`、`*.pyc`、`gateway.lock/pid`、`.update_check` |
| 数据库 sidecar | `*.db-shm`、`*.db-wal`（一致性由 WAL checkpoint 保证） |
| 临时/冗余 | `*.rar`（`search-engine-v2.rar` 与解压目录重复）、`bk/`、`新建文件夹/` |
| 模型缓存 | `models_dev_cache.json`、`provider_models_cache.json`、`ollama_cloud_models_cache.json` |

> 注意：`hermes-agent/`（Python venv）不备份。本机恢复无碍（venv 还在），但**迁移到新机器**需先重装 Hermes 本体再恢复此备份。

### 用户目录 `~/.hermes`（v5 起纳入备份）

备份到每个备份目录内的 `.hermes-home\` 子目录，恢复时还原到 `%USERPROFILE%\.hermes`。

| 内容 | 说明 |
|------|------|
| `rss-archive.db` | RSS 归档库（27MB，delete 模式，拷贝即一致） |
| `rss-scanner-state.json` / `rss-scanner-report.json` | RSS 扫描去重/健康状态 |
| `config.yaml` / `.env` / `pipeline-config.json` | config-agent 配置与凭据 |
| `scripts/`、`skills/`、`plans/`、`logs/` 等 | 用户目录下的其它数据 |

## 日志

```
C:\Users\ChangHui\AppData\Local\hermes\scripts\logs\
├── git-backup.log       ← Git 备份日志 (12:00)
├── restore.log          ← 恢复操作日志 (restore.bat)
F:\hermes-backup\logs\
└── full-backup.log      ← 全量备份日志 (18:00)
```

## 备份校验

- 全量备份完成后生成 `backup.ok` 标记，恢复时仅选择有此标记的备份。
- `full-backup.sh` 在 robocopy 前会对所有 WAL 模式的 `.db`（state.db、kanban.db、news_intel.db 等）执行 `wal_checkpoint(TRUNCATE)`，确保拷出的数据库完整；`*.db-shm / *.db-wal` 一律不备份。
- 校验备份内数据库完整性（`immutable=1` 只读，不会改写备份）：
  ```powershell
  python -c "import sqlite3;c=sqlite3.connect('file:F:/hermes-backup/hermes_2026-08-02_13-40/state.db?immutable=1',uri=True);print(c.execute('PRAGMA integrity_check').fetchone()[0]);c.close()"
  ```
- 快速体检：
  ```powershell
  Get-ChildItem F:\hermes-backup\hermes_* -Directory |
    ForEach-Object { "{0}  {1}" -f $_.Name, (Test-Path "$($_.FullName)\backup.ok") }
  ```

## 恢复

> ⚠️ 恢复会**覆盖当前 Hermes**，是破坏性操作。恢复前先确认备份健康，恢复前会先把当前版本挪到 `hermes_old_yyyyMMdd` 作为回退。

### 方案 A：一键恢复（推荐）

双击：**`F:\hermes-backup\restore.bat`**（常驻备份盘，主目录被删后也能用；脚本目录内的副本 `C:\Users\ChangHui\AppData\Local\hermes\scripts\restore.bat` 亦可）

v3 恢复主目录 **和** 用户目录 `~/.hermes`：

1. 自动定位最新有效备份（有 `backup.ok`）
2. **第一次确认**：输入 `YES`
3. **第二次确认**：再次输入 `YES`
4. 停止 `hermes-gateway.exe`
5. 备份当前主目录 → `%LOCALAPPDATA%\hermes_old_yyyyMMdd`
6. `/MIR` 镜像恢复主目录（删除多余文件，排除 `.hermes-home`）
7. 备份当前用户目录 → `%USERPROFILE%\.hermes_old_yyyyMMdd`
8. 恢复 `.hermes-home` → `%USERPROFILE%\.hermes`（rss-archive.db + config-agent 配置）
9. 手动重启 Hermes

> 若两目录已被整体删除：主目录 venv（`hermes-agent/`）不在备份内，需**先重装 Hermes 本体**，再执行本恢复；`~/.hermes` 由步骤 8 恢复。

### 方案 B：命令行全量恢复（可脚本化/远程）

```powershell
# 0. 彻底关闭所有 Hermes 进程（比 restore.bat 更干净）
taskkill /f /im hermes-gateway.exe 2>$null
taskkill /f /im hermes-agent.exe   2>$null
taskkill /f /im hermes.exe         2>$null
taskkill /f /im pythonw.exe        2>$null
Start-Sleep 3

# 1. 取最新有效备份
$bk = Get-ChildItem "F:\hermes-backup\hermes_*" -Directory |
      Where-Object { Test-Path "$($_.FullName)\backup.ok" } |
      Sort-Object Name -Descending | Select-Object -First 1
if (-not $bk) { throw "未找到有效备份" }
"用备份: $($bk.FullName)"

# 2. 备份当前版本（回退点）
robocopy "$env:LOCALAPPDATA\hermes" "$env:LOCALAPPDATA\hermes_old_$(Get-Date -Format yyyyMMdd)" /E /R:3 /W:5

# 3. 镜像恢复（/MIR = 增量+删除多余，robocopy 退出码 0-7 均为成功）
robocopy "$($bk.FullName)" "$env:LOCALAPPDATA\hermes" /MIR /R:3 /W:5
if ($LASTEXITCODE -ge 8) { throw "robocopy 失败 code=$LASTEXITCODE" }
"恢复完成，重启 Hermes。"
```

### 方案 C：部分恢复（仅配置 / 仅脚本）

```powershell
$bk = "F:\hermes-backup\hermes_2026-08-02_12-16"   # 换成实际备份名

# 只恢复核心配置
robocopy "$bk" "$env:LOCALAPPDATA\hermes" /E /R:3 /W:5 `
    config.yaml .env auth.json channel_directory.json

# 只恢复全部脚本
robocopy "$bk\scripts" "$env:LOCALAPPDATA\hermes\scripts" /E /R:3 /W:5
```

### 方案 D：从 Git 恢复（仅跟踪文件，不含数据库/缓存）

```bash
cd /c/Users/ChangHui/AppData/Local/hermes
git fetch origin
git reset --hard origin/master
```

> 用 `reset --hard` 而非 `pull`，可避免本地冲突导致半途失败。只恢复 Git 跟踪文件（配置、脚本），不含 `state.db`、`.env`（未跟踪）。

### 方案 E：恢复到另一台机器

1. 在新机器装好 Hermes，**先关闭 gateway**。
2. 挂载/拷贝 `F:\hermes-backup` 或最新 `hermes_YYYY-MM-DD_HH-MM` 目录。
3. 把该目录内容整体镜像到新的 `%LOCALAPPDATA%\hermes`（同方案 B 第 3 步）。
4. 按需替换 `config.yaml`、`.env` 中的本机路径/地址。
5. 启动 Hermes 验证。

## 恢复后验证

```powershell
# 1. 配置可读
Get-Content "$env:LOCALAPPDATA\hermes\config.yaml" -TotalCount 5
# 2. 关键文件在位
Test-Path "$env:LOCALAPPDATA\hermes\scripts\git-backup.sh"
# 3. 启动 Hermes 并确认相关端口监听
hermes gateway start        # 或 hermes 主程序
Test-NetConnection 127.0.0.1 -Port 8890    # config-agent 健康检查端口
Test-NetConnection 127.0.0.1 -Port 9119    # dashboard 端口
```

## 常见问题

| 现象 | 处理 |
|------|------|
| robocopy 退出码 ≥8 | 备份/恢复失败，看日志尾部 `FATAL` 行 |
| 找不到有效备份（无 `backup.ok`） | 说明该备份未完整完成，选更早日期目录 |
| 恢复后 gateway 起不来 | 端口被占用 → `netstat -ano \| findstr 8890` 找 PID 结束；或 `state.db` 损坏（数据库恢复见下） |
| 只需恢复数据库 | 主库从备份根目录拷 `state.db`、`kanban.db`；RSS 库在 `\.hermes-home\rss-archive.db` → 拷回 `%USERPROFILE%\.hermes\` |
