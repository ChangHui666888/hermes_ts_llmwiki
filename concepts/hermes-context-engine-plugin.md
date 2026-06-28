---
title: Context Engine Plugins
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, context, hermes, plugin, compression]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/context-engine-plugin]
confidence: high
---

# Context Engine Plugins

Replaces the built-in `ContextCompressor` with an alternative strategy (e.g., Lossless Context Management via a knowledge DAG).

- **Only one** context engine can be active at a time
- Selected via config: `context.engine: "lcm"` (default: `"compressor"`)
- Plugin engines are **never auto-activated** — user must explicitly set `context.engine`

## Directory Structure

```
plugins/context_engine/lcm/
    __init__.py      # exports the ContextEngine subclass
    plugin.yaml      # metadata (name, description, version)
```

## The ContextEngine ABC

Implement from `agent.context_engine`:

```python
from agent.context_engine import ContextEngine

class LCMEngine(ContextEngine):
    @property
    def name(self) -> str:
        return "lcm"

    def update_from_response(self, usage: dict) -> None:
        """Called after every LLM call with usage dict.
        Update: self.last_prompt_tokens, self.last_completion_tokens,
                self.last_total_tokens"""

    def should_compress(self, prompt_tokens: int = None) -> bool:
        """Return True if compaction should fire this turn."""

    def compress(self, messages: list, current_tokens: int = None,
                 focus_topic: str = None) -> list:
        """Compact message list and return new (possibly shorter) list.
        Must be valid OpenAI-format message sequence."""
```

### Class Attributes to Maintain

```python
last_prompt_tokens: int = 0
last_completion_tokens: int = 0
last_total_tokens: int = 0
threshold_tokens: int = 0          # when compression triggers
context_length: int = 0            # model's full context window
compression_count: int = 0         # how many times compress() has run
```

## Optional Methods

| Method | Default | Override when… |
|--------|---------|----------------|
| `on_session_start(session_id, **kwargs)` | No-op | Load persisted state (DAG, DB) |
| `on_session_end(session_id, messages)` | No-op | Flush state, close connections |
| `on_session_reset()` | Reset token counters | Clear per-session state |
| `update_model(model, context_length, …)` | Updates context_length + threshold | Recalculate budgets on model switch |
| `get_tool_schemas()` | Returns `[]` | Engine provides agent-callable tools |
| `handle_tool_call(name, args, **kwargs)` | Returns error JSON | Implement tool handlers |
| `should_compress_preflight(messages)` | Returns `False` | Cheap pre-API-call estimate |
| `get_status()` | Standard dict | Custom metrics |

## Engine Tools

Context engines can expose tools without registry registration:

```python
def get_tool_schemas(self):
    return [{
        "name": "lcm_grep",
        "description": "Search the context knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"],
        },
    }]

def handle_tool_call(self, name, args, **kwargs):
    if name == "lcm_grep":
        return json.dumps({"results": self._search_dag(args["query"])})
    return json.dumps({"error": f"Unknown tool: {name}"})
```

Engine tools are **injected into the agent's tool list at startup** and dispatched automatically.

## Registration

```python
# Via directory discovery (recommended)
# Just drop in plugins/context_engine/<name>/ with __init__.py + plugin.yaml

# Via general plugin system
def register(ctx):
    engine = LCMEngine(context_length=200000)
    ctx.register_context_engine(engine)
```

> Only one engine can be registered. A second is rejected with a warning.

## Lifecycle

1. Engine instantiated (plugin load or directory discovery)
2. `on_session_start()` — conversation begins
3. `update_from_response()` — after each API call
4. `should_compress()` — checked before each turn
5. `compress(messages)` — compacts when triggered
6. `on_session_end()` — cleanup

See [[hermes-context-compression]], [[hermes-memory-provider-plugin]], [[hermes-agent-loop]].
