#!/usr/bin/env python3
"""List all wiki pages with title, type, and summary for index.md generation."""
import os, re, sys
from pathlib import Path

WIKI_DIR = Path(os.environ.get("WIKI_PATH", "C:/Users/ChangHui/wiki"))

# Minimal YAML parser (no dependency)
def parse_frontmatter(content):
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip().strip("\"'")
        if key in ("title", "type", "summary", "tags"):
            meta[key] = val
    return meta

exclude = {"SCHEMA.md", "SCHEMA-GRAPH.md", "index.md", "log.md", "data.json", "graph.json", "sat-report.json"}
exclude_prefixes = (".obsidian/", "raw/", "_archive/", "scripts/", ".git/")

pages = {"entities": [], "concepts": [], "comparisons": [], "queries": [], "topics": []}

for fpath in sorted(WIKI_DIR.rglob("*.md")):
    rel = fpath.relative_to(WIKI_DIR).as_posix()
    # Skip excluded files and directories
    if fpath.name in exclude or any(rel.startswith(p) for p in exclude_prefixes):
        continue
    content = fpath.read_text(encoding="utf-8", errors="replace")
    meta = parse_frontmatter(content)
    title = meta.get("title", fpath.stem)
    page_type = meta.get("type", "other")
    summary = meta.get("summary", "")

    # Determine section by directory
    section = rel.split("/")[0] if "/" in rel else "other"
    if section not in pages:
        section = "other"
    pages[section].append({"path": rel, "title": title, "type": page_type, "summary": summary})

for section, items in pages.items():
    print(f"\n### {section.capitalize()} ({len(items)} pages)")
    for p in items:
        s = f"  - [{p['title']}]({p['path']})"
        if p["summary"]:
            s += f" — {p['summary']}"
        print(s)
