---
title: Automation Blueprints
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [automation, blueprints, cron, webhooks, triggers]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/automation-blueprints
confidence: high
---

**Source:** [Automation Blueprints - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/automation-blueprints)

## Overview

Automation blueprints are pre-built patterns that combine a trigger type with a prompt to solve a recurring problem. Three trigger types are supported: scheduled (cron), GitHub events, and API calls.

## Trigger Types

| Trigger | When It Fires | Config Entry |
|---------|--------------|-------------|
| `schedule` | Time-based (cron expression) | `cron/` directory |
| `github` | GitHub webhook event (PR, issue, push) | `webhooks/` directory |
| `api` | HTTP POST to a webhook endpoint | `webhooks/` directory |

## Blueprint: Backlog Triage

```yaml
# cron/backlog-triage.yaml
schedule: "0 8 * * 1"
prompt: >
  Review open issues in the repo with no assignee and no activity for 7+ days.
  Categorise each as: (a) needs repro, (b) needs decision, (c) stale/close.
  Tag them with labels accordingly via the GitHub API.
deliver:
  target: stdout
```

## Blueprint: Automated PR Review

```yaml
# cron/pr-review-daily.yaml
schedule: "0 10 * * 1-5"
prompt: >
  Check all open PRs in user/repo. For each PR:
  1. Read the diff
  2. Check tests pass
  3. Verify description matches changes
  4. Post a review summary as a comment
deliver:
  target: stdout
```

See [[hermes-github-pr-review]] for a complete walkthrough.

## Blueprint: Docs Drift Detector

```yaml
schedule: "0 6 * * 1"
prompt: >
  Compare the README.md with the actual CLI --help output. Report any flags,
  arguments, or commands documented differently than implemented.
```

## Blueprint: Security Audit

```yaml
schedule: "0 2 * * 0"
prompt: >
  Run `npm audit` (or `pip audit`) on the project. Report:
  - Critical / High vulnerabilities
  - Patched versions available
  - Steps to remediate
```

## Blueprint: Deploy Verification

```yaml
# webhooks/deploy-verify.yaml
route: /webhook/deploy
trigger: api
prompt: >
  The payload indicates a deploy to {{ production }}.
  Verify: (1) health endpoint returns 200,
  (2) latest commit matches expected SHA,
  (3) error rate hasn't spiked.
  Summarise pass/fail per check.
deliver:
  target: slack
  channel: "#deployments"
```

## Blueprint: Alert Triage

```yaml
route: /webhook/alerts
trigger: api
prompt: >
  Triage this alert payload from {{ source }}:
  {{ payload | tojson }}
  Determine: severity (critical/warning/info), likely cause,
  and recommended next step.
deliver:
  target: pagerduty
  routing_key: "{{ PAGERDUTY_KEY }}"
```

## Blueprint: Uptime Monitor

```yaml
schedule: "*/5 * * * *"
prompt: >
  Ping these endpoints and report response times:
  - https://api.example.com/health
  - https://app.example.com/health
  Any endpoint with >5s response or non-200 status is DOWN.
```

## Blueprint: Competitive Scout

```yaml
schedule: "0 9 * * 1"
prompt: >
  Visit https://competitor.com/changelog and summarise:
  - New features released this week
  - Pricing changes
  - Any mentions relevant to our product area
  Store in memory key "competitive_intel".
deliver:
  target: email***@example.com"
```

## See also

- [[hermes-cron-automation]] — Cron job fundamentals
- [[hermes-webhook-pr-review]] — Real-time webhook PR review
- [[hermes-cron-troubleshooting]] — Debugging automation issues
