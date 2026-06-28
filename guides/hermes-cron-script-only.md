---
title: Script-Only Cron Jobs
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [cron, scripts, bash, python, automation, cost-saving]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/cron-script-only
confidence: high
---

**Source:** [Script-Only Cron Jobs - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/cron-script-only)

## Overview

Script-only cron jobs run bash or Python scripts **without invoking the LLM**. This eliminates per-run token costs and is ideal for deterministic maintenance tasks that don't need agent reasoning.

## When to Use Script-Only

| Scenario | Use Agent Cron? | Use Script-Only? |
|----------|----------------|------------------|
| Summarise a week of git activity | ✅ Yes | ❌ |
| Check if disk is above 85% | ❌ | ✅ Yes |
| Triage new GitHub issues | ✅ Yes | ❌ |
| Restart a stalled service | ❌ | ✅ Yes |
| Compare scraped content | ❌ | ✅ Yes |

## Basic Syntax

```yaml
# ~/.hermes/cron/disk-watchdog.yaml
schedule: "*/5 * * * *"
script: /home/user/scripts/check_disk.sh
```

```bash
#!/usr/bin/env bash
# check_disk.sh — alert if disk usage exceeds threshold
THRESHOLD=85
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt "$THRESHOLD" ]; then
  echo "WARNING: Disk at ${USAGE}% (threshold: ${THRESHOLD}%)"
  exit 1
fi
echo "Disk OK: ${USAGE}%"
```

## Delivery Mapping

Script exit codes determine what delivery target fires:

| Exit Code | Meaning | Delivery |
|-----------|---------|----------|
| `0` | Success | No delivery (by default) |
| `1` | Warning / Soft failure | `on_warning` target |
| `2+` | Error / Hard failure | `on_error` target |

```yaml
schedule: "0 * * * *"
script: /home/user/scripts/check_memory.sh
deliver:
  on_warning:
    target: stdout
  on_error:
    target: slack
    channel: "#ops-alerts"
```

## Memory & Disk Watchdogs

```python
#!/usr/bin/env python3
# check_memory.py — warn if free memory is low
import psutil

mem = psutil.virtual_memory()
if mem.percent > 90:
    print(f"CRITICAL: {mem.percent}% memory used")
    exit(2)
elif mem.percent > 80:
    print(f"WARNING: {mem.percent}% memory used")
    exit(1)
else:
    print(f"OK: {mem.percent}% memory used")
```

```yaml
schedule: "*/5 * * * *"
script: /home/user/scripts/check_memory.py
deliver:
  on_warning:
    target: stdout
  on_error:
    target: email***@example.com"
```

## Script Rules

1. **Must be executable** — `chmod +x script.sh`
2. **Shebang required** — `#!/usr/bin/env bash` or `#!/usr/bin/env python3`
3. **Exit codes matter** — `0` = success, `1` = warning, `2+` = error
4. **Output is captured** — stdout and stderr are logged
5. **No interactive input** — scripts run headless

## Schedule Syntax

Standard 5-field cron syntax:

```
* * * * *
┬ ┬ ┬ ┬ ┬
│ │ │ │ └── Day of week (0-7, 0/7=Sun)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

Examples: `*/30 * * * *` (every 30 min), `0 9 * * 1-5` (weekdays at 9am), `0 0 1 * *` (1st of month).

## See also

- [[hermes-cron-automation]] — Agent-powered cron jobs
- [[hermes-cron-troubleshooting]] — Debugging cron issues
- [[hermes-automation-blueprints]] — Ready-to-use automation patterns
