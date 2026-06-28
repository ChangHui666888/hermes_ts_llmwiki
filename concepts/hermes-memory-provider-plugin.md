---
title: Memory Provider Plugins
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, memory, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin]
confidence: high
---

# Memory Provider Plugins

Memory provider plugins give Hermes **persistent, cross-session knowledge** beyond the built-in `MEMORY.md` and `USER.md`. Memory providers and context engines are the two **provider plugin** types — both follow the same pattern: single-select, config-driven, managed via `hermes plugins`.

## Directory Structure

```
plugins/memory/my-provider/
    __init__.py      # MemoryProvider implementation + register() entry point
    plugin.yaml      # Metadata (name, description, hooks)
    README.md        # Setup instructions (optional)
```

## The MemoryProvider ABC

Implement from `agent/memory_provider.py`:

```python
from agent.memory_provider import MemoryProvider

class MyMemoryProvider(MemoryProvider):
    @property
    def name(self) -> str:
        return "my-provider"

    def is_available(self) -> bool:
        """NO network calls. Runs on every hermes tools paint."""
        return bool(os.environ.get("MY_API_KEY"))

    def initialize(self, session_id: str, **kwargs) -> None:
        """Called once at agent startup.
        kwargs: hermes_home (str) — active HERMES_HOME path."""
        self._api_key = os.environ.get("MY_API_KEY", "")
        self._session_id = session_id
```

## Required Methods

| Method | When Called | Must Implement? |
|--------|-------------|-----------------|
| `name` (property) | Always | **Yes** |
| `is_available()` | Agent init, before activation | **Yes** — no network calls |
| `initialize(session_id, **kwargs)` | Agent startup | **Yes** |
| `get_tool_schemas()` | After init, for tool injection | **Yes** |
| `handle_tool_call(name, args, **kwargs)` | When agent uses your tools | **Yes** (if you have tools) |

### Config Methods

| Method | Purpose |
|--------|---------|
| `get_config_schema()` | Declare config fields for `hermes memory setup` |
| `save_config(values, hermes_home)` | Write non-secret config to native location |

### Optional Hook Methods

| Method | When Called | Use Case |
|--------|-------------|----------|
| `system_prompt_block()` | System prompt assembly | Static provider info |
| `prefetch(query, *, session_id="")` | Before each API call | Return recalled context |
| `queue_prefetch(query)` | After each turn | Pre-warm for next turn |
| `sync_turn(user, assistant, *, session_id="")` | After each completed turn | Persist conversation |
| `on_session_end(messages)` | Conversation ends | Final extraction/flush |
| `on_pre_compress(messages)` | Before context compression | Save insights before discard |
| `on_memory_write(action, target, content)` | Built-in memory writes | Mirror to your backend |
| `shutdown()` | Process exit | Clean up connections |

## Config Schema

```python
def get_config_schema(self):
    return [
        {
            "key": "api_key",
            "description": "My Provider API key",
            "secret": True,            # → written to .env
            "required": True,
            "env_var": "MY_API_KEY",
            "url": "https://my-provider.com/keys",
        },
        {
            "key": "region",
            "description": "Server region",
            "default": "us-east",
            "choices": ["us-east", "eu-west"],
        },
    ]
```

- `secret: True` + `env_var` → written to `.env`.
- Non-secret fields → passed to `save_config()`.

## Plugin Entry Point

```python
def register(ctx) -> None:
    ctx.register_memory_provider(
        provider=MyMemoryProvider(),
        name="my-provider",
        label="My Memory Provider",
        description="...",
    )
```

See [[hermes-context-engine-plugin]], [[hermes-plugin-llm-access]], [[hermes-adding-tools]].
