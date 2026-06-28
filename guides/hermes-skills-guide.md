---
title: Working with Skills
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [skills, prompts, memory, configuration, plugins]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/work-with-skills
confidence: high
---

**Source:** [Working with Skills - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)

## Overview

Skills are reusable instruction files that shape how Hermes behaves in a session. They function like system prompts or curated knowledge — loaded contextually to give the agent expertise in a domain without retraining.

## Finding Skills

```bash
# List installed skills
hermes skill list

# Search the skill hub
hermes skill search "code review"

# Show skill details
hermes skill show pr-review
```

## Using Skills

Skills are loaded at session start via the profile configuration:

```yaml
# ~/.hermes/profiles/default/skills.yaml
skills:
  - pr-review      # Loaded from installed skills
  - data-analysis
  - custom/my-skill  # Custom skill alias
```

## Progressive Disclosure

Skills follow a progressive disclosure pattern — they don't dictate behaviour upfront but define capabilities the agent can reference when needed. A skill file might contain:

- Domain knowledge and conventions
- Tool usage patterns
- Response formatting rules
- Checklist-style instructions

## Installing from Hub

```bash
# Install a single skill
hermes skill install web-research

# Install from a community source
hermes skill install user/web-research --source community

# Install a bundle
hermes skill install starter-pack
```

## Plugin-Provided Skills

When you install a plugin that bundles skills, they auto-register:

```bash
# Install plugin with bundled skills
hermes plugin install ./my-plugin

# Skills appear automatically
hermes skill list
# → my-plugin/web-research
# → my-plugin/data-analysis
```

See [[hermes-build-plugin]] for packaging skills inside plugins.

## Configuration

Skills can expose configuration parameters:

```yaml
# ~/.hermes/profiles/default/skills.yaml
skills:
  - name: web-research
    config:
      max_results: 10
      preferred_sources: ["docs", "github"]
```

The skill file declares its config schema in frontmatter:

```yaml
---
title: Web Research
config:
  max_results:
    type: integer
    default: 5
  preferred_sources:
    type: list
    default: []
---
```

## Creating Your Own

```markdown
# ~/.hermes/skills/my-custom-skill.md
---
title: My Custom Skill
slug: my-custom-skill
description: Helps with Python code review
config:
  strict_mode:
    type: boolean
    default: false
---

## Behaviour

When reviewing Python code, enforce these rules:
- Type hints required on all function signatures
- Docstrings in Google format
- Line length max 100 characters
```

See [[hermes-creating-skills]] for the full authoring guide.

## Per-Platform Management

Skills can be bound to specific platforms:

```yaml
# profiles/default/skills.yaml
skills:
  - name: terminal-expert
    platforms: [terminal]      # Only loads in terminal sessions
  - name: voice-shortcuts
    platforms: [voice]         # Only loads in voice sessions
  - name: always-active
    platforms: [terminal, voice, api]  # Loads everywhere
```

## Skills vs Memory

| Aspect | Skills | Memory |
|--------|--------|--------|
| **Persistence** | Static file, loaded per-session | Dynamic, grows over time |
| **Source** | Curated by author | Built from interactions |
| **Use case** | Behaviour & expertise | Facts, preferences, history |
| **Updates** | Manual edit | Automatic learning |

Skills define *how* the agent should act; memory tracks *what* it has learned about the user and their projects.

## See also

- [[hermes-creating-skills]] — Writing skill files from scratch
- [[hermes-build-plugin]] — Bundling skills in a plugin
- [[hermes-soul]] — The agent's persistent identity layer
