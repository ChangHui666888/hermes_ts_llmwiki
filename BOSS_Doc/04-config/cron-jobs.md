# Cron 计划任务

## 调度分工

| 类型 | 调度器 | 适用场景 |
|------|------|------|
| 循环任务 | Hermes Cron | 每N分钟/小时重复 |
| 固定时间 | Windows Task Scheduler | 每天12:00、18:00 |

## Hermes Cron（循环任务）

| 名称 | 频率 | 脚本 | 状态 |
|------|:--:|------|:--:|
| rss-scan | every 5m | rss-scanner.py | ✅ |
| news-pipeline | every 30m | news-pipeline.py | ✅ |
| token-breaker | every 10m | token-breaker-cron.py | disabled |

```powershell
hermes cron add "every 5m"  --name rss-scan --script rss-scanner.py --workdir "C:\Users\ChangHui\AppData\Local\hermes\scripts" --no-agent
hermes cron add "every 30m" --name news-pipeline --script news-pipeline.py --workdir "C:\Users\ChangHui\AppData\Local\hermes\scripts" --no-agent


hermes cron create "every 15m" --script "auto-pipeline.py" --no-agent --deliver "local" --name "auto-pipeline"


hermes cron create "every 5m" --script "rss-scanner.py" --no-agent --deliver "local" --name "rss-scanner"
```

## Windows Task Scheduler（固定时间）

| 名称 | 频率 | 脚本 | 状态 |
|------|:--:|------|:--:|
| Hermes-Git-Backup | 每日 12:00 | git-backup.sh | ✅ |
| Hermes-Full-Backup | 每日 18:00 | full-backup.sh | ✅ |

```powershell
schtasks /create /tn "Hermes-Git-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\git-backup.sh" /sc daily /st 12:00 /f
schtasks /create /tn "Hermes-Full-Backup" /tr "C:\Users\ChangHui\AppData\Local\hermes\scripts\full-backup.sh" /sc daily /st 18:00 /f
```

## ⚠️ 关键陷阱

```
# ❌ 错误 — 只执行一次
hermes cron create "30m" ...
# → Schedule: once in 30m

# ✅ 正确 — 循环执行
hermes cron add "every 30m" ...
# → Schedule: every 30m
```

## 管理命令

```bash
hermes cron list / run / remove / pause / resume
schtasks /query /tn "Hermes-Git-Backup"
schtasks /run  /tn "Hermes-Git-Backup"
```

## Pipeline 推送可靠性 (2026-08-06)

本地 auto-pipeline Step 5+6 推送 VPS 增加可靠性：

- **失败重试 2 次**（3s/6s 退避）——VPS 按 event_id upsert，重试幂等安全
- **超时细分**：`httpx.Timeout(connect=20, read=90, write=20)`，避免整请求 60s 一刀切
- **chunk 收缩**：events 50→20、content 200→100，降低跨太平洋链路上的单请求超时概率

## C 级 Backlog 清理 (2026-08-06)

- 脚本: `scripts/news_intel/cleanup_backlog.py`
- 作用: 清理 N 天前 C 级 (<60 分) 文章，减小 news_intel.db 体积、加速 Step 1 全量统计
- 安全: 删除前备份（`VACUUM INTO` 到 .bak）+ 默认 `--dry-run`
- 用法: `python news_intel/cleanup_backlog.py --days 7 [--dry-run]`

## 日志

| Job | 日志路径 |
|------|------|
| rss-scan | `~/.hermes/cron/output/<id>/` |
| news-pipeline | `scripts/logs/news-pipeline.log` |
| git-backup | `scripts/logs/git-backup.log` |
| full-backup | `scripts/logs/full-backup.log` |
