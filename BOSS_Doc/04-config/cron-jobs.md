# Cron 计划任务

> **生产定时任务脚本统一目录**：`C:\Users\ChangHui\AppData\Local\hermes\scripts\`（2026-08-08 约定）
> 该目录为 Hermes cron 实际执行脚本的位置；`deploy-cron.py --apply` 即部署到此目录。
> ⚠️ 修改 cron 脚本后必须同步该目录（`python scripts/hermes-cron/deploy-cron.py --apply`）。

## 调度分工

| 类型 | 调度器 | 适用场景 |
|------|------|------|
| 循环任务 | Hermes Cron | 每N分钟/小时重复 |
| 固定时间 | Windows Task Scheduler | 每天12:00、18:00 |

## Hermes Cron（循环任务）

| 名称 | 频率 | 脚本 | 状态 |
|------|:--:|------|:--:|
| rss-scanner | every 5m | rss-scanner.py | ✅ |
| auto-pipeline | every 15m | auto-pipeline.py | ✅ |
| **monitor-pipeline** | **every 15m** | **monitor-pipeline.py** | ✅ (2026-08-09 新建, 推送监控指标) |
| config-agent | 后台常驻 | config-agent.py | ✅ 保活 (60s 轮询) |

> 📖 rss-scanner 的 tier 分级扫描/隔离/增量限流规则见 [rss-scanner-rate-limit.md](rss-scanner-rate-limit.md)。
> **monitor-pipeline**：本地采集 pipeline.log + news_intel.db → 推送 VPS `/internal/monitor` → admin 看板展示。wrapper dispatch 到生产 profile（`~/AppData/Local/hermes/scripts/monitor-pipeline.py`）。

```powershell
hermes cron create "every 5m"  --script "rss-scanner.py"   --no-agent --deliver "local" --name "rss-scanner"
hermes cron create "every 15m" --script "auto-pipeline.py" --no-agent --deliver "local" --name "auto-pipeline"
hermes cron create "every 15m" --script "monitor-pipeline.py" --no-agent --deliver "local" --name "monitor-pipeline"
# config-agent 为后台常驻进程, 非 cron
```

> ⚠️ 旧 `news-pipeline`（every 30m）已由 `auto-pipeline`（every 15m）取代；`news-pipeline.py` 仍可作为手动简版入口。

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

## 中文源接入 + sync 水印边界修复 (2026-08-06)

- **rss-scanner 中文源调整**：清理 404/英文失效源（新华网/央视/环球网/中国日报），保留 人民网/中新网（cn 直连），新增国际中文源 BBC中文/DW中文/RFI中文（intl 走代理）。`deploy-cron.py --apply` 已部署。
- **过期归档清理**：rss-archive 中 100 篇人民网文章为 2025-06 旧内容（2026-07-05 入库），判定为过期归档，已从 `~/.hermes/rss-archive.db` 清理，不进 news_intel.db。
- **sync.py 水印边界 bug 修复**：游标查询 `created_at > ?` → `created_at >= ?`。原 `>` 会跳过与批次 `max(created_at)` 同刻的全部文章（曾致 DW中文/RFI中文 87 篇入库被漏）。`sync_catchup` 增加无进展保护防死循环。
- **数据修复**：水印重置到 `2026-08-05 18:21:09` 后重跑 catchup，87 篇新鲜中文（DW中文 57 + RFI中文 30）已入 news_intel.db。

## 日志

| Job | 日志路径 |
|------|------|
| rss-scan | `~/.hermes/cron/output/<id>/` |
| auto-pipeline | `scripts/pipeline.log` |
| git-backup | `scripts/logs/git-backup.log` |
| full-backup | `scripts/logs/full-backup.log` |
