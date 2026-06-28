---
title: Creating Skills (SKILL.md)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, skills, hermes]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills]
confidence: high
---

# Creating Skills (SKILL.md)

## Skill vs Tool Distinction

| Criteria | **Skill** | **Tool** |
|----------|-----------|----------|
| When to use | Instructions + shell + existing tools; wraps CLI/API via terminal/web_extract | End-to-end integration with API keys, custom logic, binary data, streaming |
| Examples | arXiv search, git workflows, Docker, PDF, email via CLI | Browser automation, TTS, vision analysis |

## Directory Structure

```
skills/
 ├── research/
 │   └── arxiv/
 │       ├── SKILL.md
 │       └── scripts/
 │           └── search_arxiv.py
 ├── productivity/
 │   └── ocr-and-documents/
 │       ├── SKILL.md
 │       ├── scripts/
 │       └── references/
 └── ...
```

Bundled skills: `skills/`. Official optional: `optional-skills/`.

## SKILL.md Format

### Frontmatter

```yaml
---
name: my-skill
description: Brief description
version: 1.0.0
author: Your Name
license: MIT
platforms: [macos, linux]               # Omit = all platforms
metadata:
  hermes:
    tags: [Category, Keywords]
    related_skills: [other-skill-name]
    requires_toolsets: [web]            # Only show when these toolsets active
    requires_tools: [web_search]        # Only show when these tools available
    fallback_for_toolsets: [browser]    # Hide when these toolsets available
    fallback_for_tools: [browser_navigate]  # Hide when these tools exist
    config:                             # Non-secret settings
      - key: my.setting
        description: "What this controls"
        default: "sensible-default"
        prompt: "Display prompt for setup"
    blueprint:                          # Runnable automation
      schedule: "0 9 * * *"
      deliver: origin
      prompt: "Task instruction for each run"
      no_agent: false
required_environment_variables:
  - name: MY_API_KEY
    prompt: "Enter your API key"
    help: "Get one at https://example.com"
    required_for: "API access"
---
```

### Body Sections

```markdown
# Skill Title
Brief intro.

## When to Use
Trigger conditions — when should the agent load this skill?

## Quick Reference
Table of common commands or API calls.

## Procedure
Step-by-step instructions the agent follows.

## Pitfalls
Known failure modes and how to handle them.

## Verification
How the agent confirms it worked.
```

## Conditional Skill Activation

| Field | Behavior |
|-------|----------|
| `requires_toolsets` | Hidden when **any** listed toolset is **not** available |
| `requires_tools` | Hidden when **any** listed tool is **not** available |
| `fallback_for_toolsets` | Hidden when **any** listed toolset **is** available |
| `fallback_for_tools` | Hidden when **any** listed tool **is** available |

**Use case:** `duckduckgo-search` with `fallback_for_tools: [web_search]` shows only when web search is missing.

## Config: Secrets vs Settings

| Storage | For | Where |
|---------|-----|-------|
| `required_environment_variables` | **Secrets** (API keys, tokens) | `~/.hermes/.env` |
| `metadata.hermes.config` | **Non-secret** (paths, preferences) | `config.yaml` under `skills.config.<key>` |

`hermes config migrate` scans all enabled skills, prompts for unconfigured settings. Values injected at runtime:

```
[Skill config (from ~/.hermes/config.yaml):
   myplugin.path = /home/user/my-data
]
```

## Blueprint (Runnable Automation)

Skills can declare a cron blueprint for recurring tasks:

```yaml
metadata:
  hermes:
    blueprint:
      schedule: "0 9 * * 1"    # every Monday at 9am
      deliver: origin
      prompt: "Run weekly report generation"
      no_agent: false
```

The blueprint is activated via the `hermes cron` or chatter interface — the user confirms before scheduling.

## Credential File Requirements

For OAuth token files or other file-based credentials:

```yaml
required_credential_files:
  - path: google_token.json
    description: Google OAuth2 token
  - path: google_client_secret.json
    description: Google OAuth2 client secret
    optional: true
```

See [[hermes-adding-tools]], [[hermes-plugin-llm-access]], [[hermes-extending-cli]].
