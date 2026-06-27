# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete

## [2026-06-27] create | Wiki initialized
- Domain: 通用知识库 (General-purpose)
- Structure created with SCHEMA.md, index.md, log.md
- Locations: entities/, concepts/, comparisons/, queries/, raw/ (articles, papers, transcripts, assets), _archive/
- Git repository initialized
- WIKI_PATH env var configured in Hermes profile
- OBSIDIAN_VAULT_PATH env var configured in Hermes profile
- Remote: https://github.com/ChangHui666888/hermes_ts_llmwiki.git

## [2026-06-27] feat | Obsidian + Graph layer integrated
- **Obsidian 1.12.7** installed at D:\Program Files\Obsidian
- Wiki configured as Obsidian vault (.obsidian/app.json with attachment path)
- Graph visualization: `graph.html` — D3.js interactive knowledge graph
- Graph data builder: `scripts/wiki-graph.py` — scans .md files, extracts [[wikilinks]]
- Start script: `wiki-start.cmd` — one-click launch Obsidian + Graph
- Run: `hermes wiki` in git-bash to open graph
