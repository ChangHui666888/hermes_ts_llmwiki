---
title: Cron Troubleshooting
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [cron, troubleshooting, debugging, jobs, scheduling]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting
confidence: high
---

**Source:** [Cron Troubleshooting - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting)

## Overview

When a cron job doesn't fire, delivers to the wrong place, or fails to load a skill, follow this systematic debug flow.

## Jobs Not Firing

### 1. Gateway Check

Verify the Hermes gateway is running — cron jobs are dispatched through it:

```bash
# Check if gateway is alive
hermes gateway status

# Restart if needed
hermes gateway restart

# Check gateway logs for cron dispatch entries
hermes gateway logs | grep cron
```

### 2. Schedule Syntax

Common cron syntax errors:

| ❌ Wrong | ✅ Correct | Issue |
|----------|-----------|-------|
| `*` in minute field | `0 * * * *` | Missing minute value |
| `*/60 * * * *` | `0 * * * *` | 60 is outside 0-59 range |
| `0 9 * * 1-7` | `0 9 * * 1-5` | Day-of-week range exceeds |
| `"0 0 * * *"` (quoted in YAML) | `0 0 * * *` | Quoted strings work but can hide issues |

Test your schedule with the debug command:

```bash
hermes cron test my-job --dry-run
```

### 3. Timezone Mismatch

By default, cron uses the system timezone. Check and override if needed:

```yaml
# ~/.hermes/cron/my-job.yaml
schedule: "0 9 * * *"
timezone: "America/New_York"  # Override system timezone
prompt: "Good morning briefing"
```

```bash
# Check system timezone
timedatectl show --property=Timezone --value
```

## Delivery Failures

### Target Configuration

| Target | Common Issues |
|--------|--------------|
| `stdout` | Always works — good for testing |
| `slack` | Token expired, wrong channel ID |
| `discord` | Webhook URL revoked, rate limited |
| `email` | SMTP not configured, spam filtered |
| `github_comment` | Token scopes insufficient, repo wrong |

### `[SILENT]` Is Too Effective

If `[SILENT]` is prepended and there's no error handling, output goes nowhere:

```yaml
# Will produce no visible output
prompt: "[SILENT] Run cleanup script"

# Better — only suppress on success
prompt: "[SILENT] Run cleanup script. If anything fails, report details."
```

### Platform Token Issues

```bash
# Check if tokens are set
hermes config get SLACK_BOT_TOKEN
hermes config get DISCORD_WEBHOOK_URL

# Re-authenticate
hermes auth slack
```

## Skill Loading Problems

### Skill Not Installed

```bash
# Verify skill is installed
hermes skill list

# Install from hub
hermes skill install pr-review
```

### Wrong Skill Name

Cron jobs reference skills by their exact slug. Check the skill's frontmatter:

```yaml
# In the skill file header
---
slug: pr-review  # ← Use this name in cron skill: field
---
```

### Interactive Tools in Cron

Cron jobs run headless — tools that require interactivity (prompts, confirmations) will hang. Replace with non-interactive alternatives.

### Multi-Skill Ordering

If a cron entry loads multiple skills, ordering matters:

```yaml
skills:
  - data-fetch     # Runs first
  - data-analyse   # Runs second — can reference first's output
  - report-build   # Runs third
```

If a skill depends on data from another, list them in dependency order.

## Diagnostic Commands

```bash
# List all cron jobs with their next fire time
hermes cron list

# Run a job immediately (dry run)
hermes cron test my-job --dry-run

# View cron logs
hermes cron logs my-job

# Check gateway health
hermes gateway status
```

## See also

- [[hermes-cron-automation]] — Setting up agent-powered cron jobs
- [[hermes-cron-script-only]] — Script-only cron jobs without LLM cost
- [[hermes-automation-blueprints]] — Pre-built automation patterns
