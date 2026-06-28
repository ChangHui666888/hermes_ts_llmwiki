# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-28 | Total pages: 44

## Entities

- [AI Agent发展趋势与工作流革命](entities/ai-agent发展趋势与工作流革命.md) — Session: AI Agent development trends and workflow revolution
- [Hermes-agent 搜索抓取工具汇总](entities/hermes-agent-搜索抓取工具汇总.md) — Session: Hermes Agent search & fetch tool summary
- [SQLite 本地状态检查](entities/sqlite-本地状态检查.md) — Session: SQLite local state inspection
- [The user has provided a detailed outline of an industrial-grade workflow for ...](entities/the-user-has-provided-a-detailed-outline.md) — Session: Industrial-grade workflow outline
- [了解我的身份和能力](entities/了解我的身份和能力.md) — Session: Understanding my identity and capabilities

## Concepts

- [Context Compression and Caching](concepts/hermes-context-compression.md) — Dual compression system, 4-phase algorithm, prompt caching markers, configuration
- [Hermes Agent Architecture](concepts/hermes-architecture.md) — Top-level system architecture, key files, component overview
- [Hermes Agent Loop Internals](concepts/hermes-agent-loop.md) — Core AIAgent conversation loop, API modes, turn lifecycle, tool execution
- [Hermes Creating Skills](concepts/hermes-creating-skills.md) — SKILL.md format, frontmatter, conditional activation, blueprints, secure setup
- [Hermes Extending the CLI](concepts/hermes-extending-cli.md) — 5 TUI extension hooks, wrapper CLI, widgets, keybindings, slash commands
- [Hermes Gateway Internals](concepts/hermes-gateway-internals.md) — Gateway architecture, message flow, authorization, hooks, cron bridge, deployment
- [Hermes Programmatic Integration](concepts/hermes-programmatic-integration.md) — ACP, TUI Gateway JSON-RPC, OpenAI-compatible API server protocols
- [Hermes Prompt Assembly](concepts/hermes-prompt-assembly.md) — Cached system prompt layers, SOUL.md, context files, platform hints, ephemeral layers
- [Hermes Session Storage](concepts/hermes-session-storage.md) — SQLite schema (sessions/messages/FTS5), migrations, session lineage, cost tracking

### Extending Hermes

- [Adding Tools (Built-in)](concepts/hermes-adding-tools.md) — Tool structure, schema, registry, async handlers, toolset integration
- [Adding Inference Providers](concepts/hermes-adding-providers.md) — Built-in provider layers, api_mode abstraction, file checklist
- [Adding Platform Adapters](concepts/hermes-platform-adapters.md) — Messaging platform plugins, BasePlatformAdapter, register_platform()
- [Memory Provider Plugins](concepts/hermes-memory-provider-plugin.md) — MemoryProvider ABC, lifecycle hooks, config schema, plugin entry point
- [Context Engine Plugins](concepts/hermes-context-engine-plugin.md) — ContextEngine ABC, engine tools, compression lifecycle
- [Model Provider Plugins](concepts/hermes-model-provider-plugin.md) — Plugin path, ProviderProfile, auto-wiring, discovery order
- [Image Gen Provider Plugins](concepts/hermes-image-gen-provider.md) — ImageGenProvider ABC, text/image-to-image, generate() pattern
- [Video Gen Provider Plugins](concepts/hermes-video-gen-provider.md) — VideoGenProvider ABC, text/image-to-video routing, FAL family pattern
- [Web Search Provider Plugins](concepts/hermes-web-search-provider.md) — WebSearchProvider ABC, search/extract, fixed response shape
- [Plugin LLM Access (ctx.llm)](concepts/hermes-plugin-llm-access.md) — 4 methods, structured extraction, trust gate security, audit logging
- [Provider Runtime Resolution](concepts/hermes-provider-runtime.md) — Provider resolution precedence, supported providers, Anthropic/Codex paths, auxiliary routing

## Comparisons

<!-- No comparisons yet -->

## Guides

- [Use MCP with Hermes](guides/hermes-mcp.md) — MCP server setup, tool filtering, WSL2 Chrome bridge
- [Use SOUL.md with Hermes](guides/hermes-soul.md) — Agent identity/persona, example styles, SOUL vs AGENTS.md
- [Use Voice Mode with Hermes](guides/hermes-voice-mode.md) — CLI mic loop, Telegram/Discord voice replies, STT/TTS providers
- [Build a Hermes Plugin](guides/hermes-build-plugin.md) — Plugin structure, schemas/handlers, hooks, bundled skills, shipped data
- [Automate with Cron](guides/hermes-cron-automation.md) — Agent-powered cron, 5 real-world patterns, [SILENT] trick
- [Script-Only Cron Jobs](guides/hermes-cron-script-only.md) — Zero-LLM-cost scripts, memory/disk watchdogs, delivery mapping
- [Automation Blueprints](guides/hermes-automation-blueprints.md) — 3 trigger types, 8 blueprints (PR review, uptime, security audit, etc.)
- [Cron Troubleshooting](guides/hermes-cron-troubleshooting.md) — Jobs not firing, delivery failures, skill loading issues
- [Working with Skills](guides/hermes-skills-guide.md) — Finding, installing, creating, per-platform management, skills vs memory
- [Delegation Patterns](guides/hermes-delegation-patterns.md) — Parallel research, code review, alternative comparison, multi-file refactoring
- [GitHub PR Review Agent](guides/hermes-github-pr-review.md) — Tutorial: cron + gh CLI + skill + memory for automated PR review
- [Webhook GitHub PR Review](guides/hermes-webhook-pr-review.md) — Real-time PR comments via GitHub webhooks, ngrok, security notes
- [Migrate from OpenClaw](guides/hermes-migrate-openclaw.md) — hermes claw migrate, persona/memory/skills/config mapping

## Queries

<!-- No queries yet -->

## Topics

- [AI Agent](topics/ai-agent.md) — Aggregated knowledge: AI Agent concepts, tools, and providers
- [Hermes Agent](topics/hermes-agent.md) — Aggregated knowledge: Hermes Agent capabilities and configuration
- [Research](topics/research.md) — Aggregated knowledge: Research topics and findings
- [SQLite](topics/sqlite.md) — Aggregated knowledge: SQLite state and inspection
- [Topic: 了解我的身份和能力](topics/topic-了解我的身份和能力.md) — Aggregated knowledge: Identity and capabilities
