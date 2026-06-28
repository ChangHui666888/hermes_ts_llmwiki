---
title: Automate with Cron
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [cron, automation, scheduling, jobs, scripting]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/automate-with-cron
confidence: high
---

**Source:** [Automate with Cron - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/automate-with-cron)

## Overview

Hermes cron jobs let you run agent-powered or script-powered tasks on a recurring schedule. Each cron entry tells Hermes what prompt to send (or what script to run), when to fire, and where to deliver the result.

## Cron Patterns

### Website Change Monitor

Watch a URL for content changes and get notified:

```yaml
# ~/.hermes/cron/website-watch.yaml
schedule: "*/30 * * * *"
prompt: >
  Fetch https://example.com/pricing. Compare it with the snapshot stored
  in memory key "pricing_snapshot". If changed, store the new version
  and report differences.
deliver:
  target: stdout
```

### Weekly Report Generator

Summarise activity and deliver to a configured target:

```yaml
schedule: "0 9 * * 1"
prompt: >
  Review this week's git log in /path/to/repo. Summarise:
  - Major features merged
  - Bug fixes
  - Contributors
  Format as markdown.
deliver:
  target: slack
  channel: "#team-updates"
```

### GitHub Repo Watcher

Monitor open issues and PRs needing attention:

```yaml
schedule: "*/15 * * * *"
prompt: >
  Check repo user/repo for:
  - Issues with no response in 48h
  - PRs waiting on review for >24h
  - Stale drafts older than 7 days
  Summarise in a table.
deliver:
  target: discord
  webhook: "https://discord.com/api/webhooks/..."
```

### Data Pipeline

Run a data processing step on a cadence:

```yaml
schedule: "0 3 * * *"
prompt: >
  1. Download CSV from https://data.example.com/daily/export
  2. Run cleanup transformation (see /scripts/clean.py)
  3. Load into database at postgresql://localhost/mydb
  4. Report row counts and any errors
deliver:
  target: email
  to: "team@example.com"
```

## Self-Contained Prompts

Cron prompts must be **self-contained** — the agent has no conversational context. Include all context in the prompt:

```yaml
# BAD — assumes the agent knows your project
prompt: "Run the tests and report."

# GOOD — explicit context
prompt: >
  You are in /home/user/project/my-app. This is a Node.js project.
  Run `npm test` and report: (a) pass/fail count, (b) any error
  messages, (c) duration.
```

## The `[SILENT]` Trick

Prepended `[SILENT]` suppresses the result from being displayed/logged. Useful for maintenance tasks where you only want to know about failures:

```yaml
prompt: "[SILENT] Check disk usage on /var/log. If above 85% send an alert."
```

Combine with a delivery target that only fires on errors for clean operation.

## See also

- [[hermes-cron-script-only]] — Running cron jobs without LLM cost
- [[hermes-cron-troubleshooting]] — Debugging cron jobs that don't fire
- [[hermes-automation-blueprints]] — Ready-to-use automation patterns
