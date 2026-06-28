---
title: Hermes Gateway Internals
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, gateway, hermes, messaging]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-internals]
confidence: high
---

# Gateway Internals

The messaging gateway is the long-running process connecting Hermes to 20+ external messaging platforms through a unified architecture.

## Key Files

| File | Purpose |
|------|---------|
| `gateway/run.py` | GatewayRunner — main loop, slash commands, message dispatch |
| `gateway/session.py` | SessionStore — conversation persistence and session key construction |
| `gateway/delivery.py` | Outbound message delivery to targets |
| `gateway/pairing.py` | DM pairing flow for user authorization |
| `gateway/channel_directory.py` | Maps chat IDs to human-readable names |
| `gateway/hooks.py` | Hook discovery, loading, lifecycle events |
| `gateway/mirror.py` | Cross-session message mirroring for send_message |
| `gateway/status.py` | Token lock management for profile-scoped gateways |
| `gateway/builtin_hooks/` | Extension point (none shipped) |
| `gateway/platforms/` | Platform adapters (one per messaging platform) |

## Architecture Overview

```
GatewayRunner
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Telegram │  │ Discord  │  │  Slack   │   ← Platform adapters
  │ Adapter  │  │ Adapter  │  │ Adapter  │
  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │             │             │
       └─────────────┼─────────────┘
                     ▼
              _handle_message()
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
  Slash command   AIAgent    Queue/BG
    dispatch     creation    sessions
                     │
                     ▼
                 SessionStore
              (SQLite persistence)
```

## Message Flow

1. **Platform adapter** receives raw event → normalizes into `MessageEvent`
2. **Base adapter** checks active session guard:
   - If agent running → queue message, set interrupt event
   - If `/approve`, `/deny`, `/stop` → bypass guard (inline dispatch)
3. **GatewayRunner._handle_message()** receives event:
   - Resolve session key: `agent:main:{platform}:{chat_type}:{chat_id}`
   - Check slash command → dispatch to handler
   - Check if agent running → intercept `/stop`, `/status`, etc.
   - Otherwise → create AIAgent and run conversation
4. **Response** sent back through platform adapter

### Session Key Format
```
agent:main:{platform}:{chat_type}:{chat_id}
```
Example: `agent:main:telegram:private:123456789`

### Two-Level Message Guard
- **Level 1 — Base adapter**: Checks `_active_sessions`, queues message + interrupt
- **Level 2 — Gateway runner**: Checks `_running_agents`, intercepts specific commands

## Authorization

Multi-layer check, evaluated in order:

1. Per-platform allow-all flag (e.g., `TELEGRAM_ALLOW_ALL_USERS`)
2. Platform allowlist (comma-separated user IDs)
3. DM pairing (authenticated users pair new users via code)
4. Global allow-all (`GATEWAY_ALLOW_ALL_USERS`)
5. **Default: deny**

### DM Pairing Flow
```
Admin: /pair
Gateway: "Pairing code: ABC123. Share with the user."
New user: ABC123
Gateway: "Paired! You're now authorized."
```

## Slash Command Dispatch

1. `resolve_command()` maps input to canonical name (handles aliases, prefix matching)
2. Canonical name checked against `GATEWAY_KNOWN_COMMANDS`
3. Handler dispatches based on canonical name
4. Some commands gated on config (`gateway_config_gate` on CommandDef)
5. Commands during running agent are rejected early or handled specially

## Hooks System

Gateway hooks observe lifecycle events:
- `pre_handle_message` — before message is dispatched
- `post_handle_message` — after response is sent
- `on_session_start` — new session created
- `on_session_end` — session ended
- `on_bot_start`, `on_bot_stop` — gateway lifecycle

Hooks are synchronous and blocking. Discovered via `pkg_resources` entry points or the hooks directory.

## Cron Bridge

The gateway polls `~/.hermes/cron/jobs.json` every tick (`GATEWAY_TICK_SECONDS`, default 10s). When a job is due:
- **With agent**: creates a child agent and evaluates prompt
- **Script only** (`no-agent`): runs the script and delivers stdout
- Jobs survive gateway restarts (persistent in jobs.json)

## Deployment

- **Manual:** `hermes gateway run` (foreground)
- **Windows:** `hermes gateway install` (Scheduled Task)
- **Linux:** `hermes gateway install` (systemd user service)
- **Profile-scoped:** each profile runs its own gateway instance
- **Token lock:** prevents multiple gateways sharing the same profile

See [[hermes-architecture]], [[hermes-session-storage]], [[hermes-agent-loop]].
