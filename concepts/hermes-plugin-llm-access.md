---
title: Plugin LLM Access (ctx.llm)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, hermes, plugin, llm, api]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access]
confidence: high
---

# Plugin LLM Access (ctx.llm)

`ctx.llm` is the canonical way for a Hermes plugin to make an LLM call **out of band** — outside the agent's conversation loop. Supports chat completion, structured JSON extraction, sync/async, with or without images.

## Core API Surface

### Four Methods

| Method | Use Case |
|--------|----------|
| `ctx.llm.complete()` | Free-form text response (translation, summary, rewrite) |
| `ctx.llm.complete_structured()` | Typed dict back, validated against schema |
| `ctx.llm.acomplete()` | Async version of `complete()` (gateway adapters, async hooks) |
| `ctx.llm.acomplete_structured()` | Async version of `complete_structured()` |

All accept: messages, provider, model, temperature, max_tokens, timeout, agent_id, profile, purpose.
Structured also accepts: instructions, input (text/image blocks), json_schema, json_mode, schema_name, system_prompt.

### Minimal Example (Sync)

```python
result = ctx.llm.complete(messages=[{"role": "user", "content": "ping"}])
return result.text
```

### Structured Example

```python
result = ctx.llm.complete_structured(
    instructions="Score this support reply for urgency (0–1).",
    input=[{"type": "text", "text": message_body}],
    json_schema=TRIAGE_SCHEMA,
    purpose="support.triage",
    temperature=0.0,
    max_tokens=128,
)
if result.parsed and result.parsed["urgency"] > 0.8:
    await dispatch_to_oncall(...)
```

## Result Dataclasses

### PluginLlmCompleteResult

```python
text: str                    # assistant's response
provider: str                # e.g. "openrouter"
model: str                   # model string
agent_id: str                # whose model/auth was used
usage: PluginLlmUsage        # tokens + cache + cost estimate
audit: Dict[str, Any]        # plugin_id, purpose, profile
```

### PluginLlmStructuredResult (extends CompleteResult)

```python
parsed: Optional[Any]        # JSON object when content_type == "json"
content_type: str            # "json" or "text"
```

- `result.usage` includes `input_tokens`, `output_tokens`, `total_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_usd`
- When `json_schema` is provided and `jsonschema` is installed, validation is performed

## Trust Gate (Security)

**Default: fail-closed.** Without `plugins.entries` config, a plugin can only use the user's active provider and model.

### Overrides Requiring Opt-in

| Override | Config Key | Default |
|----------|------------|---------|
| `provider=` | `allow_provider_override: true` | denied |
| `model=` | `allow_model_override: true` | denied |
| `agent_id=` | `allow_agent_id_override: true` | denied |
| `profile=` | `allow_profile_override: true` | denied |

Each is independently gated. You can also restrict to specific providers/models via `allowed_providers` / `allowed_models`.

### Always Allowed (No Override Needed)

temperature, max_tokens, timeout, system_prompt, purpose, messages, instructions, input, json_schema, schema_name, json_mode — these don't pick credentials or routes.

## What the Host Owns (Automatic)

| Feature | Description |
|---------|-------------|
| Provider resolution | Reads `model.provider` + `model.model` from user config |
| Auth | Pulls credentials from auth store; plugin never sees tokens |
| Vision routing | Falls back to vision model if text model is text-only |
| Fallback chain | Aggregator-aware fallback on 5xx/429 |
| Timeout | Honours `timeout=` argument, falls back to config defaults |
| JSON shaping | Sends `response_format`; re-parses code-fenced responses |
| Schema validation | Validates against `json_schema` if `jsonschema` installed |
| Audit logging | One INFO line per call with plugin_id, provider/model, purpose, tokens |

## What the Plugin Owns

| Responsibility | Details |
|----------------|---------|
| Request shape | Build `messages` or `instructions` + `input` |
| Schema | Whatever JSON shape you want back |
| Error handling | ValueError on empty inputs; PluginLlmTrustError on denied overrides |
| Cost | Every call uses the user's paid provider — don't loop carelessly |

See [[hermes-memory-provider-plugin]], [[hermes-context-engine-plugin]], [[hermes-adding-tools]].
