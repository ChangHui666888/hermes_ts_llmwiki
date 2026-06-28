---
title: Build a Hermes Plugin
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [plugins, development, skills, packaging, tools]
sources:
  - https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
confidence: high
---

**Source:** [Build a Hermes Plugin - Official Docs](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin)

## Overview

A Hermes Plugin packages tools, skills, and configuration into a sharable, installable unit. Plugins extend what the agent can do — from shell commands and API integrations to bundled knowledge skills.

## Plugin Directory Structure

Every plugin follows this convention:

```
my-plugin/
├── __init__.py          # Plugin metadata + hooks
├── schemas.py           # Pydantic models for config & tools
├── tools.py             # Tool implementations
├── skills/              # Bundled skills (optional)
│   └── my-skill.md
├── data/                # Shipped data files (optional)
└── pyproject.toml       # or setup.py via pip install
```

## Core Files

### `__init__.py` — Entry Point

Defines plugin identity and optional lifecycle hooks:

```python
from hermes.plugin import HermesPlugin

class MyPlugin(HermesPlugin):
    name = "my-plugin"
    version = "0.1.0"
    description = "Does something useful"

    def on_load(self):
        """Called when the plugin is loaded (install, start)."""
        pass

    def on_unload(self):
        """Called when the plugin is removed (uninstall, shutdown)."""
        pass
```

### `schemas.py` — Configuration Models

Pydantic models for user-facing config and tool parameters:

```python
from pydantic import BaseModel, Field

class MyToolParams(BaseModel):
    query: str = Field(..., description="Search query string")
    max_results: int = Field(5, ge=1, le=100)

class MyPluginConfig(BaseModel):
    api_key: str = Field("", description="API key for external service")
    endpoint: str = Field("https://default.example.com")
```

### `tools.py` — Tool Implementations

Register tools that the agent can invoke:

```python
from hermes.tool import tool
from .schemas import MyToolParams

@tool
def my_search(params: MyToolParams) -> str:
    """Execute a search against the configured endpoint."""
    # Implementation here
    return f"Results for: {params.query}"
```

Tools can also be registered using the `TOOLS` list in `__init__.py` for finer control.

## Hooks

| Hook | When It Fires | Use Case |
|------|--------------|----------|
| `on_load` | Plugin loaded / agent starts | Initialise clients, validate config |
| `on_unload` | Plugin removed / agent stops | Clean up connections, flush buffers |
| `on_session_start` | Each agent session begins | Set up per-session state |
| `on_session_end` | Each agent session ends | Teardown per-session state |

## Bundling Skills

Place `.md` skill files in a `skills/` directory inside your plugin. Hermes auto-discovers them on install:

```
my-plugin/skills/
├── web-research.md
└── data-analysis.md
```

Each skill follows the standard skill format (see [[hermes-creating-skills]]).

## Shipped Data

The `data/` directory holds assets the plugin needs at runtime — reference files, templates, embeddings, or seed content. Access them at runtime via:

```python
from importlib.resources import files
data_path = files("my_plugin.data").joinpath("reference.json")
```

## Installation

Plugins are installed from a local path or a Git repo:

```bash
# From local directory
hermes plugin install ./my-plugin

# From a Git URL
hermes plugin install https://github.com/user/my-plugin.git
```

## See also

- [[hermes-adding-tools]] — Adding tools without a full plugin
- [[hermes-creating-skills]] — Writing standalone skill files
- [[hermes-skills-guide]] — Working with skills generally
