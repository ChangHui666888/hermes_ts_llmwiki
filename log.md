# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

## [2026-06-27] create | Wiki initialized
- Domain: Personal knowledge base (AI/ML, coding, projects)
- Structure created: SCHEMA.md, index.md, log.md, graph.json
- Directories: raw/, entities/, concepts/, comparisons/, queries/

## [2026-06-28] update | Index, Schema, and Cron fix
- Updated `index.md` — added all 11 existing pages (5 entities, 5 topics)
- Updated `SCHEMA.md` — added `session`, `topic` types and Sessions/Topics tags to taxonomy
- Re-registered `wiki-sync` cron job (every 30m, no-agent) — previous job failed due to Windows path encoding
