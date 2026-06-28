---
title: Migrate from OpenClaw
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [migration, openclaw, setup, configuration, claude]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw
confidence: high
---

**Source:** [Migrate from OpenClaw - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw)

## Overview

If you're coming from **OpenClaw** (an open-source Claude Code wrapper), the `hermes claw migrate` command transfers your existing configuration, memory, skills, and agent settings into Hermes's native format. This lets you switch agents without losing your customisations.

## The Migration Command

```bash
hermes claw migrate
```

Run this from the directory containing your OpenClaw config, or specify a source path:

```bash
hermes claw migrate --from /path/to/openclaw/config
```

## What Gets Migrated

| OpenClaw Artifact | Hermes Destination | Notes |
|-------------------|--------------------|-------|
| `persona` | `profiles/*/persona.md` | Agent identity and voice |
| `memory/` | `memories/` | Per-key memory entries |
| `skills/` | `skills/` | Skill files (converted to .md) |
| `model_config` | `profiles/*/config.yaml` | Model provider, temperature, tokens |
| `agent_behavior` | `profiles/*/soul.yaml` | Behavioural preferences |

### Persona

OpenClaw's persona definition (`persona.md` or `persona.json`) maps to Hermes's persona file in the active profile:

```bash
# Migrated to:
~/.hermes/profiles/default/persona.md
```

### Memory

OpenClaw memory entries are per-key mapped to Hermes's memory store:

```bash
# Migrated to:
~/.hermes/memories/<key>.md
```

### Skills

OpenClaw skills get frontmatter added and converted to the Hermes markdown skill format:

```yaml
# Before (OpenClaw plain YAML):
name: code-review
instructions: Review Python code for...

# After (Hermes .md):
---
title: Code Review
slug: code-review
---
Review Python code for...
```

### Model Configuration

Provider, model name, temperature, and token limits are mapped to the profile config:

```yaml
# ~/.hermes/profiles/default/config.yaml
model:
  provider: anthropic
  name: claude-sonnet-4-20250514
  temperature: 0.7
  max_tokens: 4096
```

### Agent Behavior

Behavioral settings (verbosity, proactiveness, tool-use preferences) map to the soul profile:

```bash
# Migrated to:
~/.hermes/profiles/default/soul.yaml
```

See [[hermes-soul]] for details on the soul configuration system.

## Session Reset Policies

After migration, session state is handled according to these policies:

| Artifact | Reset on Migrate? | Notes |
|----------|-------------------|-------|
| Persona | No | Preserved and transferred |
| Memory | No | All entries copied |
| Skills | No | Converted and copied |
| Model config | No | Transferred as-is |
| Active sessions | Yes | Old sessions don't carry over |
| Plugin state | Yes | Plugins must be re-installed |

## Skill Conflict Handling

If a skill name already exists in Hermes, the migrator:

1. Compares content hashes — identical skills are skipped (no duplicate)
2. Renames conflicting skills with a `-openclaw` suffix
3. Logs all conflicts to stdout

```bash
# Example conflict resolution output
⚠ Skill 'code-review' already exists in Hermes
  → Renamed to 'code-review-openclaw'
  → Review and merge manually if needed
```

Manually resolve merged skills by editing the `.md` files in `~/.hermes/skills/`.

## Post-Migration Checklist

```bash
# 1. Verify migrated skills
hermes skill list

# 2. Check migrated memory
hermes memory list

# 3. Review profile config
hermes config show

# 4. Start a session to validate
hermes

# 5. Re-install any plugins
hermes plugin list  # Should be empty after migration
```

## See also

- [[hermes-skills-guide]] — Working with skills after migration
- [[hermes-soul]] — Configuring agent behaviour
- [[hermes-architecture]] — Understanding the Hermes system
