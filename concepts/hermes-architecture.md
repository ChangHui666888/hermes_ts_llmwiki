---
title: Hermes Agent Architecture
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, hermes, system-design]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/architecture]
confidence: high
---

# Hermes Agent Architecture

Hermes Agent's internal architecture is organized around a central **AIAgent** loop, with pluggable entry points, a layered prompt system, provider abstraction, and an extensible tool ecosystem.

## System Overview

```
Entry Points: CLI (cli.py) | Gateway (gateway/run.py) | ACP (acp_adapter/) | API Server | Python Library
        |                    |                            |                       |
        ▼                    ▼                            ▼                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           AIAgent (run_agent.py)                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                   │
│  │ Prompt Builder │  │ Provider       │  │ Tool Dispatch  │                   │
│  │ (prompt_       │  │ Resolution     │  │ (model_tools,  │                   │
│  │  builder.py)   │  │ (runtime_      │  │ registry.py)   │                   │
│  │                │  │  provider.py)  │  │ 70+ tools      │                   │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                  │
│  ┌───────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐                  │
│  │ Compression    │  │ 3 API Modes    │  │ Tool Registry  │                   │
│  │ & Caching      │  │ chat_complet.  │  │ (registry.py)  │                   │
│  │                │  │ codex_resp.    │  │ 28 toolsets    │                   │
│  │                │  │ anthropic      │  │                │                   │
│  └────────────────┘  └────────────────┘  └────────────────┘                   │
└──────────────────────────┬────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────┐                    ┌──────────────────────┐
│ Session Storage  │                    │ Tool Backends         │
│ (SQLite + FTS5)  │                    │ Terminal (6 backends) │
│ hermes_state.py  │                    │ Browser (5 backends)  │
│ session.py       │                    │ Web (4 backends)      │
└──────────────────┘                    │ MCP (dynamic)         │
                                        │ File, Vision, etc.    │
                                        └──────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `run_agent.py` | AIAgent — core conversation loop |
| `cli.py` | HermesCLI — interactive terminal UI |
| `model_tools.py` | Tool discovery, schema collection, dispatch |
| `toolsets.py` | Tool groupings and platform presets |
| `hermes_state.py` | SQLite session/state database with FTS5 |
| `batch_runner.py` | Batch trajectory generation |

### Agent Internals (`agent/`)

- **`prompt_builder.py`** — System prompt assembly (multi-layer caching)
- **`context_engine.py`** — ContextEngine ABC (pluggable)
- **`context_compressor.py`** — Default engine: lossy summarization
- **`prompt_caching.py`** — Anthropic prompt caching markers
- **`auxiliary_client.py`** — Auxiliary LLM for side tasks
- **`model_metadata.py`** — Model context lengths, token estimation
- **`anthropic_adapter.py`** — Anthropic Messages API format conversion
- **`display.py`** — KawaiiSpinner, tool preview formatting
- **`memory_manager.py`** — Memory manager orchestration
- **`memory_provider.py`** — Memory provider ABC
- **`trajectory.py`** — Trajectory saving helpers

### CLI Subcommands (`hermes_cli/`)

- `main.py` — Entry point for all `hermes` subcommands
- `config.py` — DEFAULT_CONFIG, migration
- `commands.py` — COMMAND_REGISTRY, slash command definitions
- `auth.py` — PROVIDER_REGISTRY, credential resolution
- `runtime_provider.py` — Provider → api_mode + credentials
- `models.py` — Model catalog
- `model_switch.py` — `/model` command logic
- `setup.py` — Interactive setup wizard
- `skin_engine.py` — CLI theming
- `skills_config.py` — Skills enable/disable
- `tools_config.py` — Tools enable/disable
- `plugins.py` — PluginManager
- `callbacks.py` — Terminal callbacks (clarify, sudo, approval)
- `gateway.py` — hermes gateway start/stop

See [[hermes-agent-loop]], [[hermes-prompt-assembly]], [[hermes-gateway-internals]], [[hermes-session-storage]] for deep dives.
