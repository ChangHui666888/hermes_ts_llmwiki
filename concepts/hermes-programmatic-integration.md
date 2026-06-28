---
title: Programmatic Integration (ACP / TUI Gateway / API Server)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, integration, hermes, api, acp]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration]
confidence: high
---

# Programmatic Integration

Hermes provides three protocols to drive the agent from external programs — IDE plugins, custom UIs, CI pipelines, and embedded sub-agents. All drive the same `AIAgent` core; they differ only in wire format and feature exposure.

## Protocol Comparison

| Protocol | Transport | Best for |
|----------|-----------|----------|
| **ACP** | JSON-RPC over stdio | IDE clients (VS Code, Zed, JetBrains) speaking Agent Client Protocol |
| **TUI gateway** | JSON-RPC over stdio or WebSocket | Custom hosts wanting fine-grained session/command/approval control |
| **API server** | HTTP + SSE | OpenAI-compatible frontends, curl-driven CI, non-Python consumers |

## 1. ACP (Agent Client Protocol)

`hermes acp` starts a stdio JSON-RPC server speaking ACP. Used in production by VS Code (Zed Industries' ACP extension), Zed, and JetBrains IDEs.

**Capabilities:** session creation, prompt submission, streaming message chunks, tool-call events, permission requests, session fork, cancel, authentication. Tool output rendered into ACP `Diff`/`ToolCall` content blocks.

```bash
hermes acp                 # serve ACP on stdio
hermes acp --bootstrap     # print install snippet for ACP-capable IDE
```

## 2. TUI Gateway JSON-RPC

`tui_gateway/server.py` powers the Ink TUI (`hermes --tui`) and embedded dashboard PTY bridge. External hosts can speak the same protocol over stdio or WebSocket.

### Method Catalog (Selected)

| Method | Purpose |
|--------|---------|
| `prompt.submit` | Submit a message |
| `prompt.background` | Background prompt |
| `session.steer` | Steer session direction |
| `session.create/list/activate/close/interrupt` | Session lifecycle |
| `session.history/compress/branch/title/usage/status` | Session inspection |
| `clarify.respond` / `sudo.respond` / `approval.respond` | User interaction |
| `config.set / config.get` | Configuration |
| `command.resolve / command.dispatch` | Slash commands |
| `cli.exec` | Run CLI commands |
| `reload.mcp / reload.env` | Runtime reload |
| `delegation.status / subagent.interrupt` | Subagent management |
| `spawn_tree.save / list / load` | Spawn tree persistence |
| `terminal.resize / clipboard.paste / image.attach` | UI helpers |

### Events Streamed Back

`message.delta`, `message.complete`, `tool.start`, `tool.progress`, `tool.complete`, `approval.request`, `clarify.request`, `sudo.request`, `secret.request`, `gateway.ready`, plus session lifecycle and error events.

### Pi-style RPC Mapping

Every command in the Pi-mono RPC spec has a TUI-gateway equivalent:

| Pi command | Hermes equivalent |
|------------|-------------------|
| `prompt` | `prompt.submit` (or ACP `session/prompt`) |
| `steer` | `session.steer` |
| `follow_up` | `prompt.submit` queued after current turn |
| `abort` | `session.interrupt` |
| `set_model` | `command.dispatch` for `/model <provider:model>` |
| `compact` | `session.compress` |
| `get_state` | `session.status` |
| `get_messages` | `session.history` |
| `switch_session` | `session.resume` |
| `fork` | `session.branch` |
| `ui_request/response` | `clarify/sudo/secret/approval.respond` |

## 3. OpenAI-Compatible API Server

`gateway/platforms/api_server.py` exposes Hermes over HTTP for any client speaking the OpenAI format.

### Endpoints

```
POST /v1/chat/completions        OpenAI Chat Completions (streaming via SSE)
POST /v1/responses               OpenAI Responses API (stateful)
POST /v1/runs                    Start a run, returns run_id (202)
GET  /v1/runs/{id}               Run status
GET  /v1/runs/{id}/events        SSE stream of lifecycle events
POST /v1/runs/{id}/approval      Resolve a pending approval
POST /v1/runs/{id}/stop          Interrupt the run
GET  /v1/capabilities            Machine-readable feature flags
GET  /v1/models                  List hermes-agent
GET  /health, /health/detailed   Health checks
```

### Custom Headers

- `X-Hermes-Session-Id` — attach to an existing session (session ID from a prior `POST /v1/chat/completions`)
- `X-Hermes-Session-Key` — advance a session (moves the turn counter forward)
- `X-Hermes-Profile` — select a non-default profile

## Which One to Use?

- **IDE plugin that already speaks ACP** → ACP. Zero protocol work.
- **Custom desktop/web app** → TUI Gateway (most feature-complete protocol).
- **Language-agnostic / curl / web frontend** → API Server (OpenAI-compatible HTTP).
- **Want all three** → Hermes can run the gateway + API server simultaneously.

See [[hermes-gateway-internals]], [[hermes-agent-loop]], [[hermes-architecture]].
