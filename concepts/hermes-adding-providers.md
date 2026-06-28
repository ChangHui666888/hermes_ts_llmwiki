---
title: Adding Inference Providers (Built-in)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, provider, hermes]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/adding-providers]
confidence: high
---

# Adding Built-in Inference Providers

## When to Add a Built-in Provider

Hermes can already talk to any OpenAI-compatible endpoint through the custom provider path. **Do not add a built-in provider unless you want first-class UX:**

- Provider-specific auth or token refresh
- A curated model catalog
- Setup / `hermes model` menu entries
- Provider aliases for `provider:model` syntax
- A non-OpenAI API shape needing an adapter

## The `api_mode` Abstraction

| Mode | Used for |
|------|----------|
| `chat_completions` | Most providers (OpenAI-compatible) |
| `codex_responses` | OpenAI Codex / Responses API |
| `anthropic_messages` | Native Anthropic Messages API |

## Fast Path — Simple API-key Providers

If your provider is just an OpenAI-compatible endpoint with a single API key, **you only need a plugin**:

```text
plugins/model-providers/<your-provider>/
    __init__.py     # calls register_provider(profile)
    plugin.yaml     # manifest
```

That's it. Auto-wires: PROVIDER_REGISTRY, `api_mode=chat_completions`, `base_url`, `env_vars`, fallback_models, CLI flags, menu entries, `provider:model` aliases, runtime resolver.

See [[hermes-model-provider-plugin]] for details.

## Full Path — Built-in Provider (5 Layers)

A built-in provider must align across five layers:

| Layer | File | Responsibility |
|-------|------|----------------|
| 1 | `hermes_cli/auth.py` | Credential discovery, PROVIDER_REGISTRY |
| 2 | `hermes_cli/runtime_provider.py` | Runtime data: provider, api_mode, base_url, api_key, source |
| 3 | `run_agent.py` | Uses `api_mode` to build/send requests |
| 4 | `hermes_cli/models.py`, `main.py` | CLI visibility, model catalog, provider:model aliases |
| 5 | `agent/auxiliary_client.py`, `model_metadata.py` | Side tasks, token budgeting |

### Required File Checklist

1. `hermes_cli/auth.py` — Add ProviderConfig to PROVIDER_REGISTRY
2. `hermes_cli/models.py` — Update _PROVIDER_MODELS, _PROVIDER_LABELS, _PROVIDER_ALIASES
3. `hermes_cli/runtime_provider.py` — Add branch in `resolve_runtime_provider()`
4. `hermes_cli/main.py` — CLI integration
5. `agent/auxiliary_client.py` — Auxiliary model defaults
6. `agent/model_metadata.py` — Token context length
7. Tests
8. User docs under `website/docs/`

### Additional for Native Providers (non-OpenAI)

1. `agent/<provider>_adapter.py` — Message format translation
2. `run_agent.py` — Branches for request building, dispatch, usage extraction, interrupt handling
3. `pyproject.toml` — Provider SDK dependency

## Runtime Resolution Output

```python
{
    "provider": "your-provider",
    "api_mode": "chat_completions",
    "base_url": "https://...",
    "api_key": "...",
    "source": "env|portal|auth-store|explicit",
    "requested_provider": requested_provider,
}
```

## Live Verification

```bash
hermes chat -q "Say hello" --provider your-provider --model your-model
hermes model
hermes setup
```

See [[hermes-model-provider-plugin]], [[hermes-provider-runtime]], [[hermes-architecture]].
