#!/usr/bin/env python3
"""
Hermes → SQLite → Wiki → Obsidian → Git 管线脚本

Usage:
  python scripts/llm-wiki-pipeline.py [--db PATH] [--dry-run]

Flow:
  1. Connect to Hermes state.db (SQLite)
  2. Query recent session data
  3. Generate/update wiki pages (Markdown)
  4. Update graph.json (JSON knowledge graph)
  5. Git commit (version control)
  6. Trigger wiki-graph.py for full rebuild
"""

import json, os, re, sys, subprocess, datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
WIKI_DIR = Path(os.environ.get("WIKI_PATH", "C:/Users/ChangHui/wiki"))
STATE_DB = Path(os.environ.get("HERMES_STATE_DB",
    "C:/Users/ChangHui/AppData/Local/hermes/state.db"))
SCRIPTS_DIR = WIKI_DIR / "scripts"
GRAPH_SCRIPT = SCRIPTS_DIR / "wiki-graph.py"

# ── SQLite Connection ──────────────────────────────────────────────────────
def connect_db(db_path: Path) -> tuple:
    """Connect to SQLite database and return (conn, cursor)."""
    import sqlite3
    print(f"🔌 Connecting to SQLite: {db_path} ({db_path.stat().st_size / 1024:.0f} KB)")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def query_recent_sessions(cur, limit: int = 5) -> list[dict]:
    """Query recent sessions from Hermes state.db."""
    try:
        # Try sessions table (standard Hermes schema)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  📊 Tables found: {', '.join(tables[:15])}{'...' if len(tables) > 15 else ''}")

        if "sessions" in tables:
            cur.execute(f"""
                SELECT id, title, created_at, updated_at, message_count
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT {limit}
            """)
            rows = cur.fetchall()
            if rows:
                return [dict(r) for r in rows]

        if "conversations" in tables:
            cur.execute(f"""
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT {limit}
            """)
            rows = cur.fetchall()
            if rows:
                return [dict(r) for r in rows]

        # Fallback: count + sample
        print("  ℹ️  No standard session tables found, generating wiki from DB stats")
        cur.execute("SELECT COUNT(*) as cnt FROM sqlite_master")
        table_count = cur.fetchone()["cnt"]
        return [{"id": "stats", "title": "Database Stats", "tables": table_count}]

    except Exception as e:
        print(f"  ⚠️  Query error: {e}")
        return []

# ── Wiki Page Generator ─────────────────────────────────────────────────────
def generate_wiki_page(session: dict) -> str:
    """Generate a markdown wiki page from a session record."""
    title = session.get("title", "Untitled Session") or "Untitled Session"
    safe_name = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40] or f"session-{session.get('id', 'unknown')}"

    created = session.get("created_at", "2026-06-27")[:10]
    updated = session.get("updated_at", "2026-06-27")[:10]
    msg_count = session.get("message_count", session.get("tables", "?"))

    return f"""---
title: "{title}"
created: {created}
updated: {updated}
type: query
tags: [hermes, session]
sources: []
---

# {title}

**Source:** Hermes session `{session.get('id')}`
**Messages:** {msg_count}
**Last updated:** {updated}

## Summary

This page was auto-generated from a Hermes session stored in state.db.
Links to related [[SCHEMA|Wiki Schema]].

## Content

> Session data extracted via Hermes → SQLite pipeline.
> Edit this page with meaningful content for the wiki.
"""

def write_wiki_page(content: str, session: dict) -> Path:
    """Write a wiki page to the entities/ directory."""
    title = session.get("title", "Untitled Session") or "Untitled"
    safe_name = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40] or f"session-{session.get('id', 'unknown')}"
    page_path = WIKI_DIR / "entities" / f"{safe_name}.md"
    page_path.write_text(content, encoding="utf-8")
    print(f"  📝 Wrote: {page_path.relative_to(WIKI_DIR)}")
    return page_path

# ── Graph JSON Updater ──────────────────────────────────────────────────────
def update_graph_json(page_paths: list[Path]):
    """Update graph.json with new nodes and edges."""
    graph_path = WIKI_DIR / "graph.json"
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    else:
        graph = {"meta": {
            "type": "knowledge-graph",
            "last_updated": datetime.date.today().isoformat(),
            "version": "1.0.0"
        }, "nodes": [], "edges": []}

    existing_ids = {n["id"] for n in graph["nodes"]}

    for p in page_paths:
        node_id = p.stem
        if node_id not in existing_ids:
            graph["nodes"].append({
                "id": node_id,
                "type": "entity",
                "title": p.stem.replace("-", " ").title(),
                "path": str(p.relative_to(WIKI_DIR)).replace("\\", "/"),
                "tags": ["hermes", "session"]
            })
            graph["edges"].append({
                "source": node_id,
                "target": "SCHEMA",
                "type": "references"
            })

    graph["meta"]["last_updated"] = datetime.date.today().isoformat()
    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  📊 Updated graph.json: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

# ── Git Operations ──────────────────────────────────────────────────────────
def git_commit(message: str, dry_run: bool = False):
    """Stage all changes and commit."""
    if dry_run:
        print(f"  🏃 Dry-run: would commit '{message}'")
        return

    # git add
    result = subprocess.run(
        ["git", "add", "-A"],
        cwd=str(WIKI_DIR),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  git add failed: {result.stderr.strip()}")
        return

    # Check if anything changed
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(WIKI_DIR),
        capture_output=True
    )
    if result.returncode == 0:
        print("  ✅ No changes to commit")
        return

    # git commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(WIKI_DIR),
        capture_output=True, text=True
    )
    if result.returncode == 0:
        summary = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else "committed"
        print(f"  ✅ {summary}")
    else:
        print(f"  ⚠️  git commit: {result.stderr.strip()}")

# ── Main Pipeline ──────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv
    db_path = STATE_DB

    # Parse --db override
    for i, arg in enumerate(sys.argv):
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = Path(sys.argv[i + 1])

    print(f"\n{'='*60}")
    print(f" 🚀 Hermes → SQLite → Wiki → Obsidian → Git Pipeline")
    print(f"{'='*60}")
    print(f"  Wiki: {WIKI_DIR}")
    if dry_run:
        print(f"  Mode: DRY RUN (no files written, no git)")

    # Step 1: Connect to SQLite
    print(f"\n📡 Step 1: SQLite Connection")
    try:
        conn, cur = connect_db(db_path)
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"  💡 Try: --db path/to/other.db")
        sys.exit(1)

    # Step 2: Query data
    print(f"\n🔍 Step 2: Query Data")
    sessions = query_recent_sessions(cur)
    conn.close()

    if not sessions:
        print("  ℹ️  No sessions found, creating a sample wiki entry")
        sessions = [{
            "id": "pipeline-test",
            "title": "Hermes SQLite Pipeline Test",
            "created_at": "2026-06-27",
            "updated_at": datetime.datetime.now().isoformat()[:10],
            "message_count": 1
        }]

    for s in sessions:
        print(f"  - [{s.get('id')}] {s.get('title', 'Untitled')}")

    # Step 3: Generate wiki pages
    print(f"\n✍️  Step 3: Generate Wiki Pages")
    page_paths = []
    for session in sessions:
        if dry_run:
            print(f"  📝 Would write: entities/{re.sub(r'[^a-z0-9]+', '-', (session.get('title') or 'untitled').lower()).strip('-')[:40]}.md")
            continue
        content = generate_wiki_page(session)
        path = write_wiki_page(content, session)
        page_paths.append(path)

    # Step 4: Update graph.json
    print(f"\n📊 Step 4: Update Graph JSON")
    if not dry_run:
        update_graph_json(page_paths)

    # Step 5: Run wiki-graph.py for full rebuild
    if GRAPH_SCRIPT.exists() and not dry_run:
        print(f"\n🔄 Step 5: Full Graph Rebuild")
        result = subprocess.run(
            [sys.executable, str(GRAPH_SCRIPT)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  ⚠️  {result.stderr.strip()}")

    # Step 6: Git commit
    print(f"\n🔖 Step 6: Git Version")
    if not dry_run:
        git_commit(
            f"pipeline: auto-sync wiki from Hermes state.db [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}]",
            dry_run=False
        )

    # Summary
    print(f"\n{'='*60}")
    print(f" ✅ Pipeline Complete")
    print(f"{'='*60}")
    print(f"  SQLite   →  {db_path}")
    print(f"  Wiki     →  {WIKI_DIR}")
    print(f"  Graph    →  {WIKI_DIR}/graph.json")
    print(f"  Obsidian →  {WIKI_DIR}/.obsidian/")
    print(f"  Git      →  {WIKI_DIR}/.git/")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
