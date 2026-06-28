---
title: Session Storage (SQLite + FTS5)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, database, hermes, sqlite, session]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage]
confidence: high
---

# Session Storage

Hermes Agent uses a SQLite database (`~/.hermes/state.db`) to persist session metadata, full message history, and model configuration across CLI and gateway sessions. **Key file:** `hermes_state.py`.

## Architecture

```
~/.hermes/state.db (SQLite, WAL mode)
 ├── sessions              — Session metadata, token counts, billing
 ├── messages              — Full message history per session
 ├── messages_fts          — FTS5 virtual table (content + tool_name + tool_calls)
 ├── messages_fts_trigram  — FTS5 virtual table with trigram tokenizer (CJK/substring)
 ├── state_meta            — Key/value metadata table
 └── schema_version        — Single-row migration tracker
```

**Key design decisions:**
- **WAL mode** for concurrent readers + one writer (gateway multi-platform)
- **FTS5 virtual table** for fast text search across all session messages
- **Session lineage** via `parent_session_id` chains (compression-triggered splits)
- **Source tagging** (`cli`, `telegram`, `discord`, etc.) for platform filtering

## Database Schema

### Sessions Table

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    cost_status TEXT,
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    api_call_count INTEGER DEFAULT 0,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);
```

### Messages Table

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,           -- JSON string
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_content TEXT,
    reasoning_details TEXT,    -- JSON string
    codex_reasoning_items TEXT, -- JSON string
    codex_message_items TEXT   -- JSON string
);
```

### FTS5 Full-Text Search

```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    content = messages,        -- external content table
    content_rowid = id
);
```

Kept in sync via triggers on INSERT, UPDATE, DELETE of the messages table.

## Schema Version & Migrations

**Current version: 11**

| Version | Change |
|---------|--------|
| 1 | Initial schema (sessions, messages, FTS5) |
| 2 | Add `finish_reason` to messages |
| 3 | Add `title` to sessions |
| 4 | Unique index on title (NULLs allowed) |
| 5 | Billing columns: cache_read/write tokens, reasoning_tokens, cost columns |
| 6 | Reasoning columns: reasoning, reasoning_details, codex_reasoning_items |
| 7 | reasoning_content column |
| 8 | api_call_count on sessions |
| 9 | codex_message_items column |
| 10 | Trigram FTS5 for CJK/substring search |
| 11 | (latest) |

Migrations are applied automatically on startup via `_apply_migrations()`. Each version is a function. The state is profile-scoped (each profile has its own state.db).

## Session Lineage

When compression splits a session:
- Original session's messages up to the compression point remain in the original session
- A new child session (with `parent_session_id` pointing back) continues the conversation
- FTS5 still indexes the parent session's messages, so search works across the full history

## Cost Tracking

Billing columns track estimated and actual costs per session:
- `estimated_cost_usd` — computed from token counts × model pricing
- `actual_cost_usd` — provider-reported (when available via API)
- `cost_status`, `cost_source`, `pricing_version` — audit trail

See [[hermes-architecture]], [[hermes-gateway-internals]], [[hermes-agent-loop]].
