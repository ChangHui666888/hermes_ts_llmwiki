# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

## [2026-06-27] create | Wiki initialized
- Domain: Personal knowledge base (AI/ML, coding, projects)
- Structure created: SCHEMA.md, index.md, log.md, graph.json
- Directories: raw/, entities/, concepts/, comparisons/, queries/

## [2026-06-28] ingest | Hermes Agent Developer Guide — Architecture Knowledge Base
- Created 8 concept pages from Hermes Agent developer docs:
  - `concepts/hermes-architecture.md` — System architecture overview
  - `concepts/hermes-agent-loop.md` — Agent loop internals
  - `concepts/hermes-prompt-assembly.md` — Prompt assembly system
  - `concepts/hermes-context-compression.md` — Context compression & caching
  - `concepts/hermes-gateway-internals.md` — Gateway internals
  - `concepts/hermes-session-storage.md` — Session storage (SQLite + FTS5)
  - `concepts/hermes-provider-runtime.md` — Provider runtime resolution
  - `concepts/hermes-programmatic-integration.md` — ACP / TUI Gateway / API Server
- Updated `index.md` — Concepts section now lists 8 pages, total pages: 19
- Sources: hermes-agent.nousresearch.com/docs/developer-guide/ (8 pages)
