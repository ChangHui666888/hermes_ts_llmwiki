---
title: Adding Tools (Built-in Core Tools)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, tools, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools]
confidence: high
---

# Adding Built-in Core Tools

## Skill vs Tool Decision

| Criteria | **Skill** | **Tool** |
|----------|-----------|----------|
| When to use | Instructions + shell + existing tools; wraps CLI/API via `terminal` or `web_extract` | End-to-end integration with API keys, custom logic, binary data, streaming |
| Examples | arXiv search, git workflows, Docker, PDF, email via CLI | Browser automation, TTS, vision analysis |

> **Default to plugins** for most custom tools. Only follow this guide for **built-in core tools** (in `tools/` and `toolsets.py`).

## Overview — Two Files

| File | Purpose |
|------|---------|
| `tools/your_tool.py` | Handler, schema, check function, `registry.register()` call |
| `toolsets.py` | Add tool name to `_HERMES_CORE_TOOLS` (or a specific toolset) |

> **Auto-discovery:** Any `tools/*.py` with a top-level `registry.register()` is automatically discovered — no manual import list.

## Tool File Structure

### Required Elements

```python
# tools/weather_tool.py
"""Weather Tool — look up current weather for a location."""
import json, os, logging
logger = logging.getLogger(__name__)

# --- Availability check ---
def check_weather_requirements() -> bool:
    return bool(os.getenv("WEATHER_API_KEY"))

# --- Handler ---
def weather_tool(location: str, units: str = "metric") -> str:
    """Fetch weather for a location. Returns JSON string."""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return json.dumps({"error": "WEATHER_API_KEY not configured"})
    try:
        return json.dumps({"location": location, "temp": 22, "units": units})
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- Schema ---
WEATHER_SCHEMA = {
    "name": "weather",
    "description": "Get current weather for a location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name..."},
            "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
        },
        "required": ["location"]
    }
}

# --- Registration ---
from tools.registry import registry
registry.register(
    name="weather",
    toolset="weather",
    schema=WEATHER_SCHEMA,
    handler=lambda args, **kw: weather_tool(
        location=args.get("location",""),
        units=args.get("units","metric")),
    check_fn=check_weather_requirements,
    requires_env=["WEATHER_API_KEY"],
)
```

### Key Rules

- **Handlers MUST return a JSON string** (via `json.dumps()`), never raw dicts.
- **Errors MUST be returned as `{"error": "message"}`**, never raised as exceptions.
- `check_fn` is called when building tool definitions — if it returns `False`, the tool is silently excluded.
- `handler` receives `(args: dict, **kwargs)`.

## Registering in Toolset

In `toolsets.py`:

```python
_HERMES_CORE_TOOLS = [
    ...
    "weather",   # make available on all platforms
]

# Or create a new standalone toolset:
"weather": {
    "description": "Weather lookup tools",
    "tools": ["weather"],
    "includes": []
},
```

## Async Handlers

Use `is_async=True`:

```python
registry.register(
    name="weather",
    ...,
    handler=lambda args, **kw: weather_tool_async(args.get("location","")),
    is_async=True,   # registry calls _run_async() automatically
)
```

The registry handles async bridging — never call `asyncio.run()` yourself.

## Setup Wizard Integration

Add API key config to `hermes_cli/config.py`:

```python
OPTIONAL_ENV_VARS = {
    "WEATHER_API_KEY": {
        "description": "Weather API key",
        "prompt": "Weather API key",
        "url": "https://weatherapi.com/",
        "tools": ["weather"],
        "password": True,
    },
}
```

## Checklist

- Tool file created with handler, schema, check function, registry.register()
- Returns `json.dumps()` string, errors as `{"error": "..."}` 
- Added to `_HERMES_CORE_TOOLS` or a named toolset in `toolsets.py`
- `requires_env` in registry.register() for required env vars
- Optional: env var wizard entry in `OPTIONAL_ENV_VARS`
- Tests and docs

See [[hermes-architecture]], [[hermes-memory-provider-plugin]], [[hermes-plugin-llm-access]].
