---
title: Use SOUL.md with Hermes
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [guide, soul, hermes, identity, persona]
sources: [https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes]
confidence: high
---

# Use SOUL.md with Hermes

**Source:** [Hermes Agent Docs – Use SOUL.md](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes)

## Overview

`SOUL.md` is the **primary identity** for a Hermes instance. It defines the agent's persona, tone, communication style, and constraints — placed as the first item in the system prompt.

> *"If you want Hermes to feel like the same assistant every time you talk to it — or if you want to replace the Hermes persona entirely with your own — this is the file to use."*

## What SOUL.md is For

- Tone, personality, communication style
- How direct or warm Hermes should be
- What Hermes should avoid stylistically
- How Hermes relates to uncertainty, disagreement, and ambiguity

**In short:** *"SOUL.md is about who Hermes is and how Hermes speaks."*

## What SOUL.md is NOT For

- Repo-specific coding conventions → put in `AGENTS.md`
- File paths, commands, service ports → put in `AGENTS.md`
- Architecture notes, project workflow → put in `AGENTS.md`

**Rule of thumb:**
- **If it should apply everywhere → SOUL.md**
- **If it only belongs to one project → AGENTS.md**

## File Location & Behavior

- **Default:** `~/.hermes/SOUL.md`
- **First-run:** Hermes auto-seeds a starter SOUL.md if none exists
- **Existing file:** Never overwritten. If empty, adds nothing to the prompt

## How Hermes Uses It

1. Reads `SOUL.md` from `HERMES_HOME`
2. Scans for prompt-injection patterns
3. Truncates if too long
4. Uses it as **agent identity** — slot #1 in the system prompt (replaces built-in default)
5. Falls back to built-in identity if missing/empty

## Example Styles

### Pragmatic Engineer
```markdown
You are a pragmatic senior engineer.
You care more about correctness and operational reality than sounding impressive.
## Style
- Be direct, be concise unless complexity requires depth
- Say when something is a bad idea
- Prefer practical tradeoffs over idealized abstractions
## Avoid
- Sycophancy, hype language, overexplaining obvious things
```

### Research Partner
```markdown
You are a thoughtful research collaborator.
You are curious, honest about uncertainty, and excited by unusual ideas.
## Style
- Explore possibilities without pretending certainty
- Distinguish speculation from evidence
- Ask clarifying questions when underspecified
- Prefer conceptual depth over shallow completeness
```

### Teacher / Explainer
```markdown
You are a patient technical teacher.
You care about understanding, not performance.
- Explain clearly, use examples when helpful
- Don't assume prior knowledge unless signalled
- Build from intuition to details
```

### Tough Reviewer
```markdown
You are a rigorous reviewer. You are fair, but do not soften important criticism.
- Point out weak assumptions directly
- Prioritize correctness over harmony
- Be explicit about risks and tradeoffs
- Prefer blunt clarity to vague diplomacy
```

## SOUL.md vs /personality

| Feature | SOUL.md | `/personality` |
|---------|---------|----------------|
| Role | Durable baseline | Temporary mode switches |
| Persistence | Permanent until edited | Lasts one session |

See [[hermes-prompt-assembly]], [[hermes-build-plugin]], [[hermes-creating-skills]].
