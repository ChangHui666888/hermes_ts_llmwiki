---
title: Video Generation Provider Plugins
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, video-gen, hermes, plugin]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/video-gen-provider-plugin]
confidence: high
---

# Video Generation Provider Plugins

Mirrors Image Generation Provider Plugins almost line-for-line. Register a backend that services every `video_generate` tool call. Built-in providers (xAI, FAL) ship as plugins.

## One Tool, Two Modalities

The `video_generate` tool exposes two modalities through one parameter:

- **Text-to-video** — `prompt` only → provider routes to text-to-video endpoint
- **Image-to-video** — `prompt` + `image_url` → provider routes to image-to-video endpoint

Edit and extend are out of scope (most backends don't support them consistently).

## Discovery (3 Locations)

Same as image-gen: Bundled → User (`~/.hermes/plugins/video_gen/`) → Pip entry points.

## Directory Structure

```
plugins/video_gen/my-backend/
    __init__.py      # VideoGenProvider subclass + register()
    plugin.yaml      # Manifest with kind: backend
```

## The VideoGenProvider ABC

```python
from agent.video_gen_provider import VideoGenProvider, success_response, error_response

class MyBackendVideoGenProvider(VideoGenProvider):
    @property
    def name(self) -> str:
        return "my-backend"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def list_models(self) -> list:
        """List model families. User picks one; generate() routes within it."""
        return [{"id": "my-family", "display": "My Video Family", ...}]

    def default_model(self) -> str:
        return "my-family"

    def capabilities(self) -> dict:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": ["16:9", "9:16", "1:1"],
            "resolutions": ["480p", "720p", "1080p"],
            "min_duration": 5,
            "max_duration": 30,
            "supports_audio": True,
            "supports_negative_prompt": False,
            "max_reference_images": 0,
        }

    def generate(self, prompt, *, model=None, image_url=None,
                 reference_image_urls=None, duration=None,
                 aspect_ratio=None, resolution=None,
                 negative_prompt=None, audio=None, seed=None, **kwargs):
        # Route based on image_url presence
        if image_url:
            endpoint = "my-backend/image-to-video"
            modality_used = "image"
        else:
            endpoint = "my-backend/text-to-video"
            modality_used = "text"
        # ... API call ...
        return success_response(video=..., model=..., prompt=...,
                                modality=modality_used, duration=...)
```

### Routing Pattern (FAL)

When a backend has multiple endpoints per "model family", represent each **family** as one catalog entry:

```python
FAMILIES = {
    "veo3.1": {
        "text_endpoint": "fal-ai/veo3.1",
        "image_endpoint": "fal-ai/veo3.1/image-to-video",
    },
}

def generate(self, prompt, *, image_url=None, model=None, **kwargs):
    family_id, family = _resolve_family(model)
    endpoint = family["image_endpoint"] if image_url else family["text_endpoint"]
```

### Response Format

- **Success:** `{"success": True, "video": <URL or path>, "model": ..., "prompt": ..., "modality": ..., "aspect_ratio": ..., "duration": ..., "provider": ...}`
- **Error:** `{"success": False, "video": None, "error": "...", "error_type": "...", ...}`

## plugin.yaml

```yaml
name: my-backend
version: 1.0.0
description: My video generation backend
author: Your Name
kind: backend
requires_env:
  - MY_API_KEY
```

See [[hermes-image-gen-provider]], [[hermes-web-search-provider]], [[hermes-plugin-llm-access]].
