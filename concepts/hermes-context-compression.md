---
title: Context Compression and Caching
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, compression, caching, hermes, context-management]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching]
confidence: high
---

# Context Compression and Caching

Hermes uses a **pluggable context engine** with a built-in `ContextCompressor` that implements lossy summarization, and `PromptCaching` for Anthropic API.

## Pluggable Context Engine

- Built on `ContextEngine` ABC
- Config-driven via `context.engine` in `config.yaml`
- Resolution order: plugins/context_engine/ → general plugin system → built-in `ContextCompressor`
- Plugin engines never auto-activated — must set `context.engine` explicitly

## Dual Compression System

Two independent layers work in concert:

```
Incoming message → Gateway Session Hygiene (85% threshold, safety net)
                → Agent ContextCompressor (50% threshold default, primary)
```

### 1. Gateway Session Hygiene (85% threshold)
- Safety net — prevents API failures from large inter-turn growth (overnight sessions)
- In `gateway/run.py`, prefers API-reported tokens, falls back to `estimate_messages_tokens_rough`
- Intentionally set higher than agent's compressor to avoid premature compression

### 2. Agent ContextCompressor (50% threshold)
- In `agent/context_compressor.py`
- Runs inside the agent's tool loop with accurate API-reported token counts

## Configuration

```yaml
compression:
  enabled: true
  threshold: 0.50              # fraction of context window
  target_ratio: 0.20           # how much of threshold to keep as tail
  protect_last_n: 20           # minimum protected tail messages
  codex_gpt55_autoraise: true  # raise trigger to 85% for gpt-5.5 on Codex

  auxilliary:
    compression:
      model: null               # override model for summaries
      provider: auto            # auto/openrouter/nous/main/etc.
      base_url: null            # custom OpenAI-compatible endpoint
```

### Key Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `threshold` | 0.50 | 0.0-1.0 | Trigger when prompt ≥ threshold × context_length |
| `target_ratio` | 0.20 | 0.10-0.80 | Tail token budget = threshold_tokens × target_ratio |
| `protect_last_n` | 20 | ≥1 | Minimum recent messages preserved |
| `protect_first_n` | 3 | (hardcoded) | System prompt + first exchange preserved |

### Codex gpt-5.5 Threshold Autoraise
- Codex OAuth hard-caps gpt-5.5 at 272K context (vs 1.05M direct API)
- Default 50% trigger would fire at ~136K — wasting half the window
- Route `provider: openai-codex` + model gpt-5.5 → auto-raise to 85% (~231K)

## Compression Algorithm (4 Phases)

### Phase 1: Prune Old Tool Results (cheap, no LLM)
Replace old tool results (>200 chars) outside the tail with:
```
[Old tool output cleared to save context space]
```

### Phase 2: Determine Boundaries
- `[0..2]` — protect_first_n (system prompt + first exchange)
- `[3..N]` — middle turns → SUMMARIZED
- `[N..end]` — tail (by token budget, protect_last_n)

### Phase 3: Summarize Middle
LLM call to auxiliary model generates a summary of the middle section, preserving:
- Decisions made and their reasoning
- Files created or modified (paths)
- Commands run and their results
- Key findings or blockers

### Phase 4: Reconstruct
Replaces middle section with:
```json
{"role": "user", "content": "[Summary of previous turns...]"}
```

## Prompt Caching (Anthropic)

For Anthropic Messages API, Hermes applies caching markers to:
- The **system prompt** (static layers) — survives session compaction
- The **conversation history** — bookended with `ephemeral: true` markers
- Cache granularity: system prompt block (static tool schemas) and message blocks

When compression runs, the **system prompt is NOT invalidated** — only the message portion changes. This means Anthropic's prompt cache stays warm across compactions.

## Computed Values Example (200K context model)

```
context_length       = 200,000
threshold_tokens     = 200,000 × 0.50 = 100,000
tail_token_budget    = 100,000 × 0.20 = 20,000
max_summary_tokens   = min(200,000 × 0.05, 12,000) = 10,000
```

Threshold is based on the **main agent model's** context window, never the auxiliary model's.

See [[hermes-agent-loop]], [[hermes-prompt-assembly]], [[hermes-architecture]].
