---
title: Hermes Prompt Assembly
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, prompt, hermes, caching]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly]
confidence: high
---

# Prompt Assembly

Hermes separates **cached system prompt state** from **ephemeral API-call-time additions** to optimize token usage, prompt caching effectiveness, session continuity, and memory correctness.

## Cached System Prompt Layers (3 Tiers)

Assembled in order from `agent/prompt_builder.py`:

1. **Stable** — identity (`SOUL.md` or fallback), tool/model guidance, skills prompt, environment/platform hints
2. **Context** — caller-supplied `system_message` + project context files (`.hermes.md` / `AGENTS.md` / `CLAUDE.md` / `.cursorrules`)
3. **Volatile** — built-in memory snapshot (`MEMORY.md`), user profile (`USER.md`), external memory-provider block, timestamp/session/model/provider line

**Final prompt:** `stable` → `context` → `volatile`

### Concrete Prompt Layering (Simplified)

```
# Layer 1: Agent Identity (from ~/.hermes/SOUL.md or DEFAULT_AGENT_IDENTITY)
You are Hermes, an AI assistant created by Nous Research.

# Layer 2: Tool-aware behavior guidance
You have persistent memory across sessions...

# Layer 3: Honcho static block (when active)

# Layer 4: Optional system message (from config or API)

# Layer 5: Frozen MEMORY snapshot
## Persistent Memory
- User prefers Python 3.12, uses pyproject.toml

# Layer 6: Frozen USER profile snapshot
## User Profile
- Name: Alice

# Layer 7: Skills index
## Skills (mandatory)
<available_skills>
  software-development:
    - code-review: Structured code review workflow
</available_skills>

# Layer 8: Context files (from project directory)
## AGENTS.md
This is the atlas project. Use pytest for testing...

# Layer 9: Timestamp + session info
Current time: 2026-03-30T14:30:00-07:00

# Layer 10: Platform hint
You are a CLI AI Agent. Try not to use markdown but simple text...
```

## Customizing Platform Hints

Platform hints can be overridden in `config.yaml`:

```yaml
platform_hints:
  whatsapp:
    append: >               # keep built-in + add after
      When tabular output is needed, invoke the table_formatting skill.
  slack:
    replace: "You are on Slack. Keep responses tight."  # full replace
  telegram: "Prefer short messages."  # shorthand = append
```

- `append` — keep built-in hint and add text after
- `replace` — substitute entirely
- Bare string — shorthand for `append`
- `replace` wins over `append` when both present

## SOUL.md

- Lives at `~/.hermes/SOUL.md` (per-profile)
- Replaces hardcoded `DEFAULT_AGENT_IDENTITY`
- Security scanned (invisible unicode, injection patterns, credential exfiltration)
- Truncated to `context_file_max_chars` (default 20k chars)
- When loaded, `build_context_files_prompt(skip_soul=True)` prevents duplicate injection

## Context File Injection — Priority System

`build_context_files_prompt()` uses **first match wins**:

| Priority | Files | Search Scope |
|----------|-------|--------------|
| 1 | `.hermes.md`, `HERMES.md` | CWD up to git root |
| 2 | `AGENTS.md` | CWD only |
| 3 | `CLAUDE.md` | CWD only |
| 4 | `.cursorrules`, `.cursor/rules/*.mdc` | CWD only |

All context files are security scanned, truncated (default 20k chars, 70/20 head/tail ratio), and have YAML frontmatter stripped.

## Ephemeral Prompt Layers (Not Cached)

Injected at each API call:
- `ephemeral_system_prompt` (from API caller)
- Budget warnings (`max_steps` / `max_depth` remaining)
- Context pressure warnings (near limit)
- Interrupt detection cues

## Frozen Memory & Profile

Memory and profile are captured at the start of each conversation turn. A snapshot is built (not a live view) to avoid mid-conversation drift. The memory block includes context-window warnings about how much content is available vs. what's included.

Multiple memory providers: built-in (disk), Honcho, exo, MCP.

See [[hermes-architecture]], [[hermes-agent-loop]], [[hermes-context-compression]].
