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
├── hermes_YYYY-MM-DD_HH-MM\      ← 每个备份为一个日期目录
│   ├── backup.ok                 ← 完成标记 (恢复时只认带此标记的备份)
│   ├── config.yaml               ← 配置
│   ├── .env                      ← 环境变量/密钥
│   ├── scripts\                  ← 全部脚本
│   └── ...                       ← hermes 全目录镜像 (已排除 node/cache/.git 等)
├── logs\
│   └── full-backup.log           ← 全量备份日志
└── state\
    └── last-success              ← 最近成功时间
```

> full-backup 排除项：`node, cache, audio_cache, image_cache, sessions, sandboxes, lsp, mcp-installs, gateway-service, hermes-agent, bin, .git, __pycache__, bk, 新建文件夹`；文件：`*.pyc *.log *.lock *.pid *.rar state.db-shm state.db-wal` 等。
> `.env`、`auth.json`、`config.yaml` **会**被备份，恢复后无需重新配置。

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

双击：`C:\Users\ChangHui\AppData\Local\hermes\scripts\restore.bat`

1. 自动定位最新有效备份（有 `backup.ok`）
2. **第一次确认**：输入 `YES`
3. **第二次确认**：再次输入 `YES`
4. 仅停止 `hermes-gateway.exe`
5. 备份当前版本 → `%LOCALAPPDATA%\hermes_old_yyyyMMdd`
6. `/MIR` 镜像恢复（删除多余文件）
7. 手动重启 Hermes

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
| 只需恢复数据库 | 从备份拷 `state.db`、`kanban.db`、`rss-archive.db` 到对应位置即可 |
