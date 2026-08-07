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

## 当前 Cron 状态（2026-08 已稳定）

| 任务 | 频率 | 脚本 | 状态 |
|------|:--:|------|:--:|
| rss-scanner | 每5分钟 | rss-scanner.py | ✅ |
| auto-pipeline | 每15分钟 | auto-pipeline.py | ✅ |
| config-agent | 后台常驻 | config-agent.py | ✅ 保活 (60s 轮询) |

### 创建命令

```powershell
hermes cron create "every 5m"  --script "rss-scanner.py"   --no-agent --deliver "local" --name "rss-scanner"
hermes cron create "every 15m" --script "auto-pipeline.py" --no-agent --deliver "local" --name "auto-pipeline"
```

### 注意事项

- `once in X` ≠ `every X`，创建时必须用 `"every X"`
- `--repeat 99999` 在 `every` 模式下无效（已经是无限重复）
- 脚本和 workdir 必须在 `~/.hermes/scripts/` 下，与其他 cron 一致
- 旧 `news-pipeline`（30m）已由 `auto-pipeline`（15m）取代；`news-pipeline.py` 仅作手动简版入口
