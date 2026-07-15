# Cron Job 排障记录

## news-pipeline 反复失败的根因

### 问题 1：Schedule 类型错误

```
# ❌ 错误（只执行一次）
Schedule: once in 30m
Repeat: 0/1

# ✅ 正确（每30分钟循环）
Schedule: every 30m
Repeat: ∞
```

`hermes cron create "30m"` 默认创建 `once in 30m`，需用 `"every 30m"`。

### 问题 2：缺少生产级日志

旧 wrapper 只有 `logging.basicConfig(level=logging.INFO)` — 无文件日志、无 traceback、无 exit code。`Ran now: failed` 但无法定位根因。

### 修复

在 `news-pipeline.py` 增加：

- 文件日志 → `logs/news-pipeline.log`
- Runtime 信息（Python版本、路径、环境变量）
- traceback 落盘
- exit code 记录
- `PIPELINE_RESULT` 结构化输出

### 日志位置

```
C:\Users\ChangHui\AppData\Local\hermes\scripts\logs\news-pipeline.log
```

```powershell
Get-Content .\logs\news-pipeline.log -Tail 100
```

## 当前 Cron 状态（已稳定）

| 任务 | 频率 | 脚本 | 状态 |
|------|:--:|------|:--:|
| token-breaker | 每10分钟 | token-breaker-cron.py | ✅ |
| rss-scan | 每5分钟 | rss-scanner.py | ✅ |
| news-pipeline | 每30分钟 | news-pipeline.py | ✅ |

### 创建命令

```powershell
hermes cron add "every 5m"  --name rss-scan --script rss-scanner.py --workdir "C:\Users\ChangHui\AppData\Local\hermes\scripts" --no-agent
hermes cron add "every 30m" --name news-pipeline --script news-pipeline.py --workdir "C:\Users\ChangHui\AppData\Local\hermes\scripts" --no-agent
```

### 运行顺序

```
00:00 rss-scan
00:05 rss-scan
00:10 rss-scan + token-breaker
00:15 rss-scan
00:20 rss-scan + token-breaker
00:25 rss-scan
00:30 rss-scan + token-breaker + news-pipeline  ← 三方重叠
```

### 注意事项

- `once in 30m` ≠ `every 30m`，创建时必须用 `"every 30m"`
- `--repeat 99999` 在 `every` 模式下无效（已经是无限重复）
- 脚本和 workdir 必须在 `~/.hermes/scripts/` 下，与其他 cron 一致
