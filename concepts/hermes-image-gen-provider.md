---
title: Image Generation Provider Plugins
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, image-gen, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin]
confidence: high
---

# Image Generation Provider Plugins

Image-gen provider plugins register a backend that services every `image_generate` tool call. Built-in providers (OpenAI, OpenAI-Codex, xAI) ship as plugins.

## Plugin Discovery (3 Locations)

1. **Bundled** — `<repo>/plugins/image_gen/<name>/` (auto-loaded, always available)
2. **User** — `~/.hermes/plugins/image_gen/<name>/` (opt-in via `plugins.enabled`)
3. **Pip** — packages declaring a `hermes_agent.plugins` entry point

Active provider selected via `image_gen.provider` in `config.yaml`. `hermes tools` walks users through selection.

## Directory Structure

```
plugins/image_gen/my-backend/
    __init__.py      # ImageGenProvider subclass + register()
    plugin.yaml      # Manifest with kind: backend
```

## The ImageGenProvider ABC

Subclass `agent.image_gen_provider.ImageGenProvider`:

```python
from agent.image_gen_provider import (
    ImageGenProvider, success_response, error_response,
    resolve_aspect_ratio, save_b64_image
)

class MyBackendImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "my-backend"

    @property
    def display_name(self) -> str:
        return "My Backend"

    def is_available(self) -> bool:
        if not os.environ.get("MY_BACKEND_API_KEY"):
            return False
        try:
            import my_backend_sdk
        except ImportError:
            return False
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "my-model-fast", "display": "My Model (Fast)",
             "speed": "~5s", "strengths": "Quick iteration", "price": "$0.01/image"},
        ]

    def default_model(self) -> Optional[str]:
        return "my-model-fast"

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text", "image"], "max_reference_images": 4}

    def generate(self, prompt, aspect_ratio=DEFAULT_ASPECT_RATIO,
                 *, image_url=None, reference_image_urls=None, **kwargs):
        prompt = (prompt or "").strip()
        aspect_ratio = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return error_response(error="Prompt is required", ...)
        # API call, save image, return success_response(image=..., model=..., prompt=...)
```

### Key Details

- `resolve_aspect_ratio()` normalizes the aspect ratio string
- For base64 output: use `save_b64_image()` → returns absolute `Path`
- For URL output: return the URL string directly
- Model selection precedence: env var → config → default
- Supports both text-to-image and image-to-image/edit mode

### ABC Reference

| Member | Required | Default | Purpose |
|--------|----------|---------|---------|
| `name` | ✅ | — | Stable id for `image_gen.provider` config |
| `display_name` | — | `name.title()` | Label in `hermes tools` |
| `is_available()` | — | `True` | Gate for missing creds/deps |
| `list_models()` | — | `[]` | Catalog for model picker |
| `default_model()` | — | first from list | Fallback model |
| `get_setup_schema()` | — | minimal | Picker metadata + env-var prompts |
| `generate(prompt, aspect_ratio, **kwargs)` | ✅ | — | The call (must return dict) |

## Response Format

- **Success:** `success_response(image=..., model=..., prompt=..., provider=..., extra=...)` → `{"success": True, "image": "...", ...}`
- **Error:** `error_response(error=..., error_type=..., ...)` → `{"success": False, "error": "...", ...}`

## plugin.yaml

```yaml
name: my-backend
version: 1.0.0
description: My image backend
author: Your Name
kind: backend
requires_env:
  - MY_BACKEND_API_KEY
```

`kind: backend` routes to image-gen registration path.

See [[hermes-video-gen-provider]], [[hermes-web-search-provider]], [[hermes-plugin-llm-access]].
