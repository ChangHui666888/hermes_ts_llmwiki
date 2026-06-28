---
title: Provider Runtime Resolution
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, provider, hermes, runtime, auth]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/provider-runtime]
confidence: high
---

# Provider Runtime Resolution

Hermes has a **shared provider runtime resolver** used across CLI, gateway, cron jobs, ACP, and auxiliary model calls.

## Key Files

| File | Purpose |
|------|---------|
| `hermes_cli/runtime_provider.py` | Credential resolution, `_resolve_custom_runtime()` |
| `hermes_cli/auth.py` | Provider registry, `resolve_provider()` |
| `hermes_cli/model_switch.py` | Shared `/model` switch pipeline (CLI + gateway) |
| `agent/auxiliary_client.py` | Auxiliary model routing |
| `providers/` | ABC + registry entry points |
| `plugins/model-providers/<name>/` | Per-provider plugins (bundled + user override) |

`get_provider_profile()` returns a `ProviderProfile` for a given provider ID — canonical `base_url`, `env_vars` priority list, `api_mode`, and `fallback_models`. Adding a new plugin under `plugins/model-providers/` that calls `register_provider()` is enough for the resolver to pick it up.

## Resolution Precedence

1. Explicit CLI/runtime request
2. `config.yaml` model/provider config
3. Environment variables
4. Provider-specific defaults or auto resolution

This ordering prevents a stale shell export from silently overriding the endpoint a user last selected in `hermes model`.

## Supported Providers

Complete set includes (but not limited to):

- OpenRouter | Nous Portal | OpenAI Codex
- Copilot / Copilot ACP
- Anthropic (native Messages API)
- Google / Gemini
- Alibaba / DashScope (`alibaba`, `alibaba-coding-plan`)
- DeepSeek | Z.AI
- Kimi / Moonshot (`kimi-coding`, `kimi-coding-cn`)
- MiniMax (`minimax`, `minimax-cn`, `minimax-oauth`)
- Kilo Code | Hugging Face
- OpenCode Zen / OpenCode Go
- AWS Bedrock | Azure Foundry
- NVIDIA NIM | xAI (Grok)
- Arcee | GMI Cloud | StepFun
- Qwen OAuth | Xiaomi
- Ollama Cloud | LM Studio
- Tencent TokenHub
- **Custom** (`provider: custom`) — first-class provider for any OpenAI-compatible endpoint
- Named custom providers (`custom_providers` list in config.yaml)

## Output of Runtime Resolution

The resolver returns:
- `provider` — resolved provider name
- `api_mode` — chat_completions / codex_responses / anthropic_messages
- `base_url` — API endpoint URL
- `api_key` — resolved credential
- `source` — where the config came from
- Provider-specific metadata (expiry/refresh info)

This shared logic enables consistent auth across `hermes chat`, gateway message handling, cron jobs, ACP sessions, and auxiliary model tasks.

## OpenRouter and Custom Base URLs

Hermes avoids leaking the wrong API key to custom endpoints:
- `OPENROUTER_API_KEY` is only sent to `openrouter.ai` endpoints
- `OPENAI_API_KEY` is used for custom endpoints and as a fallback

Hermes distinguishes between:
- A real custom endpoint selected by the user
- The OpenRouter fallback path (no custom endpoint configured)

This matters for local model servers, non-OpenRouter compatibile APIs, and switching providers without re-running setup.

## Native Anthropic Path

When provider resolution selects `anthropic`:
- `api_mode = anthropic_messages`
- Uses native Anthropic Messages API
- `agent/anthropic_adapter.py` for message format translation
- Prefers **refreshable Claude Code credentials** over copied env tokens
- Manual `ANTHROPIC_TOKEN` / `CLAUDE_CODE_OAUTH_TOKEN` still work as overrides
- Preflights credential refresh before native calls
- Retries once on 401 after rebuilding the client

## OpenAI Codex Path

- `api_mode = codex_responses`
- Uses Responses API (separate format from Chat Completions)
- Dedicated credential resolution and auth store support

## Auxiliary Model Routing

Auxiliary tasks (vision, web extraction summarization, context compression, skills hub, MCP helper, memory flushes) can use their own provider/model routing:
- `provider: auto` — use the main agent's provider
- `provider: main` — resolve through the main provider pipeline
- Explicit provider name — use a different provider
- `model: null` — auto-detect a capable model for the task

See [[hermes-architecture]], [[hermes-agent-loop]], [[hermes-gateway-internals]].
