---
title: Delegation & Parallel Work
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [delegation, parallel, subagents, workflows, efficiency]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns
confidence: high
---

**Source:** [Delegation & Parallel Work - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns)

## Overview

Hermes can delegate sub-tasks to focused sub-agents that run in parallel. This dramatically reduces wall-clock time for multi-step workflows and lets the primary agent maintain context while specialised agents handle the details.

## When to Delegate

| ✅ Delegate | ❌ Keep Inline |
|------------|---------------|
| Research three unrelated topics | Simple data lookup |
| Code review across 10+ files | Single file edit |
| Compare N competing approaches | Known single answer |
| Gather-and-analyse pattern | Quick calculation |
| Multi-file refactoring | Single rename |

## Pattern: Parallel Research

The primary agent dispatches N sub-agents, each researching one topic:

```
Main Agent
 ├── Sub-agent A: Research vector databases
 ├── Sub-agent B: Research embedding models
 └── Sub-agent C: Research orchestration frameworks
      ↓ (all run in parallel)
 Main Agent synthesises results
```

**Prompt pattern** — each sub-agent gets a focused, self-contained brief:

> "You are a focused subagent working on a specific delegated task. YOUR TASK: Research [specific topic]. Find: (1) top 3 options, (2) pros/cons per option, (3) recommendation. Return structured markdown. Be thorough but concise — your response is returned to the parent agent as a summary."

## Pattern: Parallel Code Review

Review multiple files simultaneously:

```
Main Agent
 ├── Sub-agent A: Review auth.py for security issues
 ├── Sub-agent B: Review api.py for correctness
 └── Sub-agent C: Review models.py for type safety
```

Each sub-agent receives the file content inline and returns findings as structured markdown. The primary agent collates the report.

## Pattern: Compare Alternatives

Evaluate competing tools or approaches:

```yaml
# The primary agent sends the same brief to multiple sub-agents,
# each with a different focus:
Sub-agent A: "Argue FOR approach X — list strengths"
Sub-agent B: "Argue AGAINST approach X — list weaknesses"
Sub-agent C: "Compare X to Y factually, no bias"
```

The primary agent then weighs all perspectives to make a balanced decision.

## Pattern: Multi-File Refactoring

Break a large refactor into parallel chunks:

```
Main Agent
 ├── Sub-agent A: Refactor database layer
 ├── Sub-agent B: Refactor API endpoints
 ├── Sub-agent C: Update tests
 └── Sub-agent D: Update documentation
```

Each sub-agent works on a clean subset. The primary agent handles integration and conflict resolution.

## Pattern: Gather Then Analyse

A two-phase pattern — gather data in parallel, then analyse serially:

**Phase 1 (Parallel):**
- Sub-agent A: Collect sales data from CRM
- Sub-agent B: Collect support tickets from Zendesk
- Sub-agent C: Collect git commit history

**Phase 2 (Serial):**
- Main agent: Correlate, analyse trends, produce report

## Best Practices

1. **Self-contained briefs** — Each sub-agent should have everything it needs in its prompt
2. **Structured output** — Ask for markdown or YAML output, not freeform prose
3. **Clear return contract** — Specify format upfront so the parent can parse results
4. **Limit fan-out** — 3–5 parallel agents is the sweet spot; beyond that coordination overhead grows
5. **No shared mutable state** — Sub-agents shouldn't write to the same files concurrently

## See also

- [[hermes-architecture]] — How Hermes manages multi-agent workflows
- [[hermes-prompt-assembly]] — How prompts are assembled for sub-agents
- [[hermes-soul]] — Persistent identity across delegations
