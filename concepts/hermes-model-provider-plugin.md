---
title: Model Provider Plugins (Plugin Path)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, provider, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/model-provider-plugin]
confidence: high
---

# Model Provider Plugins

Model provider plugins declare an inference backend that Hermes routes `AIAgent` calls through. Every built-in provider ships as one of these plugins. Third parties add their own by dropping a directory under `$HERMES_HOME/plugins/model-providers/` with **zero repo changes**.

This is the third kind of **provider plugin** (alongside Memory Provider and Context Engine plugins). All three follow the same "drop a directory, declare a profile, no repo edits" pattern.

## Discovery Order

1. **Bundled** — `<repo>/plugins/model-providers/<name>/` (ship with Hermes)
2. **User** — `$HERMES_HOME/plugins/model-providers/<name>/`
3. **Legacy single-file** — `<repo>/providers/<name>.py` (back-compat)

> **User plugins override bundled plugins of the same name** (last-writer-wins).

## Directory Structure

```
plugins/model-providers/my-provider/
    __init__.py       # Calls register_provider(profile) at module-level
    plugin.yaml       # kind: model-provider + metadata (optional but recommended)
    README.md         # Setup instructions (optional)
```

Only `__init__.py` is required.

## Minimal Example

```python
# plugins/model-providers/acme-inference/__init__.py
from providers import register_provider
from providers.base import ProviderProfile

acme = ProviderProfile(
    name="acme-inference",
    aliases=("acme",),
    display_name="Acme Inference",
    description="Acme — OpenAI-compatible direct API",
    signup_url="https://acme.example.com/keys",
    env_vars=("ACME_API_KEY", "ACME_BASE_URL"),
    base_url="https://api.acme.example.com/v1",
    auth_type="api_key",
    default_aux_model="acme-small-fast",
    fallback_models=("acme-large-v3", "acme-medium-v3", "acme-small-fast"),
)
register_provider(acme)
```

```yaml
# plugin.yaml
name: acme-inference
kind: model-provider
version: 1.0.0
description: Acme Inference — OpenAI-compatible direct API
author: Your Name
```

## What Auto-Wires (No Other Edits)

| Integration | Where | What it gets |
|-------------|-------|--------------|
| Credential resolution | `auth.py` | PROVIDER_REGISTRY populated from profile |
| `--provider` CLI flag | `main.py` | Accepts `acme-inference` |
| `hermes model` picker | `models.py` | Appears in CANONICAL_PROVIDERS |
| `hermes doctor` | `doctor.py` | Health check for API key + endpoint probe |
| `hermes setup` | `config.py` | Env vars appear in wizard |
| Auxiliary model | `auxiliary_client.py` | Uses default_aux_model |
| Runtime resolution | `runtime_provider.py` | Returns correct base_url, api_key, api_mode |
| Transport | `chat_completions.py` | Profile path generates kwargs |

## ProviderProfile Fields (key)

| Field | Type | Purpose |
|-------|------|---------|
| `name` | `str` | Canonical id, matches `model.provider` in config.yaml |
| `aliases` | `tuple[str]` | Alternative names (e.g., `grok` → `xai`) |
| `api_mode` | `str` | `chat_completions` / `codex_responses` / `anthropic_messages` / `bedrock_converse` |
| `display_name` | `str` | Human label in `hermes model` picker |
| `description` | `str` | Picker subtitle |
| `signup_url` | `str` | "Get an API key here" link |
| `env_vars` | `tuple[str]` | API-key env vars in priority order; final `*_BASE_URL` entry as base URL override |
| `base_url` | `str` | Default inference endpoint |
| `models_url` | `str` | Explicit catalog URL (falls back to `{base_url}/models`) |
| `auth_type` | `str` | `api_key` / `oauth_device_code` / `oauth_external` / `copilot` / `aws_sdk` / `external_process` |
| `fallback_models` | `tuple[str]` | Curated list shown when live catalog unavailable |

See [[hermes-adding-providers]], [[hermes-provider-runtime]], [[hermes-architecture]].
