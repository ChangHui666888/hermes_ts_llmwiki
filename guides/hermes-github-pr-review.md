---
title: GitHub PR Review Agent
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [github, pr-review, cron, skills, memory, automation]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/github-pr-review-agent
confidence: high
---

**Source:** [GitHub PR Review Agent - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/github-pr-review-agent)

## Overview

Build an automated PR review agent using Hermes that checks open pull requests, reviews diffs, and posts structured feedback — all on a cron schedule. The architecture combines four components:

- **Cron** — Schedule-driven execution
- **gh CLI** — GitHub interaction
- **Skills** — Code review expertise
- **Memory** — Project conventions and past reviews

## Architecture

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌────────┐
│  Cron   │────▶│  Agent   │────▶│  gh CLI  │────▶│ GitHub │
│  Job    │     │  + Skill │     │  + Tools  │     │  API   │
└─────────┘     └────┬─────┘     └──────────┘     └────────┘
                     │
                     ▼
               ┌──────────┐
               │  Memory  │
               │  (Convs) │
               └──────────┘
```

## Step 1: Verify Setup

```bash
# Ensure gh CLI is installed and authenticated
gh auth status

# Create the cron job directory
mkdir -p ~/.hermes/cron
```

## Step 2: Manual Review (Test the Flow)

```yaml
# ~/.hermes/cron/pr-review-manual.yaml
schedule: "*/10 * * * *"  # Every 10 min for testing
prompt: >
  Check all open PRs in user/repo. For each PR:
  1. Fetch the diff using `gh pr view <number> --json body,additions,deletions,files,changedFiles`
  2. Fetch diff content with `gh pr diff <number>`
  3. Review for: logic errors, security issues, style violations, missing tests
  4. Post a review summary
deliver:
  target: stdout
```

## Step 3: Create a Review Skill

```markdown
# ~/.hermes/skills/pr-review.md
---
title: PR Review
slug: pr-review
description: Guidelines for automated code review
---

## Review Checklist

For every PR, check:
1. **Correctness** — Does the code do what the description claims?
2. **Security** — Any injection vectors, hardcoded secrets, or unsafe eval?
3. **Tests** — Are new functions covered? Do existing tests still pass?
4. **Style** — Follows project conventions (use memory to learn these)?
5. **Performance** — Any N+1 queries, unnecessary allocations, or sync-in-loop?

## Output Format

Return findings as a structured markdown table:

| File | Severity | Issue | Suggestion |
|------|----------|-------|------------|
| auth.py | high | Hardcoded API key | Use env var |
```

## Step 4: Teach Conventions via Memory

```bash
# Tell Hermes about your project conventions once
echo "This project uses: Google-style Python, pytest, mypy strict mode" \
  | hermes memory add --key project-conventions
```

## Step 5: Automated Cron Job

```yaml
# ~/.hermes/cron/pr-review.yaml
schedule: "0 9,14 * * 1-5"  # Twice daily weekdays
prompt: >
  Use the pr-review skill to review open PRs in user/repo.
  For each open PR, fetch and analyse the diff.
  Post a review comment on the PR if new issues are found.
  Skip PRs already reviewed today (check memory).
skills:
  - pr-review
deliver:
  target: stdout
```

## Step 6: Post Reviews to GitHub

Configure delivery to post comments directly:

```yaml
deliver:
  target: github_comment
  repo: user/repo
```

## Step 7: Weekly Dashboard

```yaml
schedule: "0 10 * * 1"
prompt: >
  Summarise all PR reviews from last week:
  - Total PRs reviewed
  - Issues found (by severity)
  - PRs merged vs still open
  Store in memory key "weekly_pr_summary".
```

## See also

- [[hermes-webhook-pr-review]] — Real-time PR reviews via webhook
- [[hermes-cron-automation]] — Cron job fundamentals
- [[hermes-skills-guide]] — Working with skills
