---
title: Hermes Agent Loop Internals
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, agent-loop, hermes]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop]
confidence: high
---

# Agent Loop Internals

`AIAgent` (in `run_agent.py`) orchestrates the entire agent conversation loop — prompt assembly, provider selection, model calls, tool execution, compression, retries, and memory flushing.

## Two Entry Points

```python
# Simple — returns final response string
response = agent.chat("Fix the bug in main.py")

# Full — returns dict with messages, metadata, usage stats
result = agent.run_conversation(
    user_message="Fix the bug in main.py",
    system_message=None,           # auto-built if omitted
    conversation_history=None,     # auto-loaded from session if omitted
    task_id="task_abc123"
)
```

`chat()` is a thin wrapper around `run_conversation()`.

## API Modes

| Mode | Used for | Client |
|------|----------|--------|
| `chat_completions` | OpenAI-compatible endpoints (OpenRouter, custom, most providers) | `openai.OpenAI` |
| `codex_responses` | OpenAI Codex / Responses API | `openai.OpenAI` (Responses format) |
| `anthropic_messages` | Native Anthropic Messages API | `anthropic.Anthropic` via adapter |

**Resolution order:** explicit arg → provider-specific detection → base URL heuristics → default `chat_completions`.

All three converge to the same internal OpenAI-style message format.

## Turn Lifecycle

```
run_conversation()
  1. Generate task_id if not provided
  2. Append user message to conversation history
  3. Build or reuse cached system prompt (prompt_builder.py)
  4. Check if preflight compression is needed (>50% context)
  5. Build API messages from conversation history
  6. Inject ephemeral prompt layers (budget warnings, context pressure)
  7. Apply prompt caching markers if on Anthropic
  8. Make interruptible API call (_interruptible_api_call)
  9. Parse response:
     - If tool_calls: execute them, append results, loop back to step 5
     - If text response: persist session, flush memory if needed, return
```

### Message Format (Internal)

```json
{ "role": "system", "content": "..." }
{ "role": "user", "content": "..." }
{ "role": "assistant", "content": "...", "tool_calls": [...] }
{ "role": "tool", "tool_call_id": "...", "content": "..." }
```

Reasoning content stored in `assistant_msg["reasoning"]`, optionally displayed via `reasoning_callback`.

### Message Alternation Rules

- After system: `User → Assistant → User → Assistant → ...`
- During tool calls: `Assistant (with tool_calls) → Tool → Tool → ... → Assistant`
- Never two assistant messages in a row, never two user messages in a row
- Only `tool` role can have consecutive entries (parallel tool results)

## Interruptible API Calls

Wrapped in `_interruptible_api_call()`. HTTP POST runs in a background thread while the main thread monitors interrupt events. On interrupt (new user message, `/stop`, signal): API thread abandoned, response discarded, no partial response injected.

## Tool Execution

- **Single tool call** → main thread
- **Multiple tool calls** → `ThreadPoolExecutor` (except `interactive` tools like `clarify` which force sequential)
- Results reinserted in original tool call order

### Agent-Level Tools (Intercepted Before Registry)

| Tool | Why Intercepted |
|------|-----------------|
| `todo` | Reads/writes agent-local task state |
| `memory` | Writes to persistent memory files |
| `session_search` | Queries session history via session DB |
| `delegate_task` | Spawns subagent(s) with isolated context |

## Budget Tracking

- `max_steps`: maximum tool call rounds per agent invocation
- `max_depth`: maximum delegation depth
- Passed to subagents via `remaining_steps` / `remaining_depth` in their context
- `/status` command displays remaining budget

## Memory Flushing

Memory provider's flush is called when: (1) session ends, (2) agent hits `max_steps` budget, (3) turn completes (if changed).

See [[hermes-architecture]], [[hermes-context-compression]], [[hermes-prompt-assembly]].
