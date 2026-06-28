---
title: Web Search Provider Plugins
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, search, hermes, plugin, web]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin]
confidence: high
---

# Web Search Provider Plugins

Web-search provider plugins register a backend that services `web_search`, `web_extract`, and optionally deep-crawl tool calls. Built-in providers (Firecrawl, SearXNG, Tavily, Exa, Parallel, Brave, xAI, DDGS) ship under `plugins/web/<name>/`.

## Discovery (3 Locations)

1. **Bundled** — `<repo>/plugins/web/<name>/` (auto-loaded, always available)
2. **User** — `~/.hermes/plugins/web/<name>/` (opt-in via `plugins.enabled`)
3. **Pip** — packages declaring a `hermes_agent.plugins` entry point

### Active Provider Selection

| Capability | Config key | Falls back to |
|------------|------------|---------------|
| `web_search` | `web.search_backend` | `web.backend` |
| `web_extract` | `web.extract_backend` | `web.backend` |
| Deep crawl | `web.extract_backend` | `web.backend` |

When no key is set, Hermes auto-detects the backend from whatever API key/URL is present. `hermes tools` walks through selection.

## Directory Structure

```
plugins/web/my-backend/
    __init__.py     # register() entry point
    provider.py     # WebSearchProvider subclass
    plugin.yaml     # Manifest with kind: backend and provides_web_providers
```

Smallest references: `brave_free/` (API-key-gated search-only), `ddgs/` (no-key, lazy-installs SDK).

## The WebSearchProvider ABC

Subclass `agent.web_search_provider.WebSearchProvider`:

```python
class MyBackendWebSearchProvider(WebSearchProvider):
    @property
    def name(self) -> str:
        return "my-backend"

    @property
    def display_name(self) -> str:
        return "My Backend"

    def is_available(self) -> bool:
        """Cheap check — env var present. MUST NOT make network calls."""
        return bool(os.getenv("MY_BACKEND_API_KEY", "").strip())

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Returns dict with fixed response shape."""
        import httpx
        api_key = os.environ["MY_BACKEND_API_KEY"]
        try:
            resp = httpx.get(
                "https://api.example.com/search",
                params={"q": query, "count": max(1, min(int(limit), 20))},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            return {"success": False, "error": str(exc)}

        return {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("snippet", ""),
                        "position": idx + 1,
                    }
                    for idx, item in enumerate(data.get("results", []))
                ],
            },
        }
```

### Response Shape (fixed)

```python
# Search response:
{"success": True, "data": {"web": [{"title": ..., "url": ..., "description": ..., "position": ...}]}}
# or
{"success": False, "error": "..."}

# Extract response:
{"success": True, "data": {"results": [{"url": ..., "title": ..., "content": ..., "error": ...}]}}
```

## Plugin Entry Point

```python
# __init__.py
def register(ctx) -> None:
    ctx.register_web_search_provider(MyBackendWebSearchProvider())
```

## plugin.yaml

```yaml
name: web-my-backend
version: 1.0.0
kind: backend
provides_web_providers: true
requires_env:
  - MY_BACKEND_API_KEY
```

See [[hermes-image-gen-provider]], [[hermes-video-gen-provider]], [[hermes-plugin-llm-access]].
