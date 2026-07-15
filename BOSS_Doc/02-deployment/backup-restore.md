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

## 日志

```
C:\Users\ChangHui\AppData\Local\hermes\scripts\logs\
├── full-backup.log      ← 全量备份日志
├── git-backup.log       ← Git 备份日志
└── restore.log          ← 恢复操作日志
```

## 备份校验

全量备份完成后生成 `backup.ok` 标记文件。恢复时仅选择有此标记的备份。

## 恢复

### 一键恢复

双击：`C:\Users\ChangHui\AppData\Local\hermes\scripts\restore.bat`

1. 显示最新有效备份（有 `backup.ok` 标记）
2. **第一次确认**：输入 `YES`
3. **第二次确认**：再次输入 `YES`
4. 仅停止 `hermes-gateway.exe`
5. 备份当前版本 → `hermes_old_yyyyMMdd`
6. `/MIR` 镜像恢复（删除多余文件）
7. 提示手动重启 Hermes

### 从 Git 恢复

```bash
cd ~/AppData/Local/hermes
git pull origin master
```

仅恢复 Git 跟踪文件，不含数据库和缓存。

## 仓库

```
https://github.com/ChangHui666888/hermes-agent-backup
```
