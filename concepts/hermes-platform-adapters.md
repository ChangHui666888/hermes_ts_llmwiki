---
title: Adding Platform Adapters (Messaging)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, gateway, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/adding-platform-adapters]
confidence: high
---

# Adding Messaging Platform Adapters

## Architecture

```
User ↔ Messaging Platform ↔ Platform Adapter ↔ Gateway Runner ↔ AIAgent
```

Every adapter extends `BasePlatformAdapter` from `gateway/platforms/base.py`.

## Required Methods

| Method | Purpose |
|--------|---------|
| `connect()` | Establish connection (WebSocket, long-poll, HTTP server) — **abstract** |
| `disconnect()` | Clean shutdown — **abstract** |
| `send(chat_id, content, ...)` | Send a text message — **abstract** |
| `send_typing(chat_id)` | Show typing indicator (optional override) |
| `get_chat_info(chat_id)` | Return chat metadata (optional override) |

Inbound messages are forwarded via `self.handle_message(event)`.

## Plugin Path (Recommended)

Drop a plugin directory into `~/.hermes/plugins/` — no core code changes needed:

```
~/.hermes/plugins/my-platform/
    plugin.yaml      # Plugin metadata
    adapter.py       # Adapter class + register() entry point
```

### plugin.yaml

```yaml
name: my-platform
label: My Platform
kind: platform
version: 1.0.0
description: My custom messaging platform adapter
author: Your Name
requires_env:
  - MY_PLATFORM_TOKEN
  - name: MY_PLATFORM_CHANNEL
    description: "Channel to join"
    prompt: "Channel"
    password: false
```

### adapter.py

```python
from gateway.platforms.base import (
    BasePlatformAdapter, SendResult, MessageEvent, MessageType,
)

class MyPlatformAdapter(BasePlatformAdapter):
    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform("my_platform"))
        extra = config.extra or {}
        self.token = os.getenv("MY_PLATFORM_TOKEN") or extra.get("token", "")

    async def connect(self) -> bool:
        self._mark_connected()
        return True

    async def disconnect(self) -> None:
        self._mark_disconnected()

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        return SendResult(success=True, message_id="...")

def register(ctx):
    ctx.register_platform(
        name="my_platform",
        label="My Platform",
        adapter_factory=lambda cfg: MyPlatformAdapter(cfg),
        check_fn=check_requirements,
        validate_config=validate_config,
        required_env=["MY_PLATFORM_TOKEN"],
        install_hint="pip install my-platform-sdk",
        env_enablement_fn=_env_enablement,
        cron_deliver_env_var="MY_PLATFORM_HOME_CHANNEL",
        allowed_users_env="MY_PLATFORM_ALLOWED_USERS",
        allow_all_env="MY_PLATFORM_ALLOW_ALL_USERS",
        max_message_length=4000,
        platform_hint="You are chatting via My Platform. It supports markdown formatting.",
        emoji="💬",
    )
```

## What the Plugin System Handles Automatically

| Integration | How it works |
|-------------|--------------|
| Gateway adapter creation | Registry checked before built-in if/elif chain |
| Config parsing | Platform._missing_() accepts any platform name |
| User authorization | allowed_users_env / allow_all_env checked |
| Env-only auto-enable | env_enablement_fn seeds PlatformConfig.extra + home_channel |
| hermes tools | Discovers and prompts for missing credentials |
| hermes doctor | Validates adapter connectivity |

## Built-in Path (for Core Distribution)

Add to `Gateways` in gateway/platforms/:

1. Create `gateway/platforms/my_platform.py`
2. Add entry to `gateway/platforms/__init__.py` platform list
3. Add to `BUILTIN_PLATFORM_CLASSES` in `gateway/platforms/base.py`
4. Register env vars in `hermes_cli/config.py`

See [[hermes-gateway-internals]], [[hermes-architecture]], [[hermes-model-provider-plugin]].
