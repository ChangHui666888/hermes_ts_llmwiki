#!/usr/bin/env python3
"""Wiki graph data builder — scans wiki .md files and outputs graph-ready JSON.

Usage:
  python wiki-graph.py                     # writes C:/Users/ChangHui/wiki/data.json
  python wiki-graph.py --watch             # watch mode (auto-rebuild on file changes)
  python wiki-graph.py --output /path      # custom output path
"""
import json, os, re, sys, time, glob
from pathlib import Path

WIKI_DIR = Path(os.environ.get("WIKI_PATH", "C:/Users/ChangHui/wiki"))
OUTPUT = WIKI_DIR / "data.json"

RE_FRONTMATTER = re.compile(r"^---\n([\s\S]*?)\n---", re.MULTILINE)
RE_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

def parse_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter into a dict (no PyYAML dependency)."""
    result = {"title": "", "type": "other", "tags": [], "confidence": "medium"}
    m = RE_FRONTMATTER.match(content)
    if not m:
        return result
    yaml_text = m.group(1)
    for line in yaml_text.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if not val:
            continue
        if key == "title":
            result["title"] = val.strip("\"'")
        elif key == "type":
            result["type"] = val.strip("\"'").lower()
        elif key == "tags":
            # Tags: [tag1, tag2] or [tag1,tag2]
            inner = val.strip("[]\"'")
            result["tags"] = [t.strip().strip("\"'") for t in inner.split(",") if t.strip()]
        elif key == "confidence":
            result["confidence"] = val.strip("\"'").lower()
    return result

def extract_links(content: str) -> list[str]:
    """Extract all [[wikilinks]] from markdown content."""
    matches = RE_WIKILINK.findall(content)
    return list(dict.fromkeys(m.strip() for m in matches))  # unique, ordered

def scan_wiki() -> dict:
    """Scan wiki directory and build metadata."""
    files = {}
    md_files = list(WIKI_DIR.rglob("*.md"))
    # Exclude index.md, log.md, SCHEMA.md from the graph but still scan for links
    exclude_base = {"index.md", "log.md", "SCHEMA.md"}

    for fpath in md_files:
        rel = fpath.relative_to(WIKI_DIR).as_posix()
        if rel in exclude_base or rel.startswith("_archive/") or rel.startswith(".obsidian/"):
            continue
        if rel.startswith("raw/"):
            # Skip raw files — they're sources, not graph nodes
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        fm = parse_frontmatter(content)
        links = extract_links(content)

        # Get display name from filename if no title in frontmatter
        name = fm["title"] or fpath.stem

        files[rel] = {
            "title": name,
            "frontmatter": fm,
            "links": links,
            "size": len(content),
        }

    return {"files": files, "stats": {
        "total_pages": len(files),
        "nodes_with_type": {t: sum(1 for f in files.values() if f["frontmatter"]["type"] == t) for t in ["entity", "concept", "comparison", "query", "other"]},
    }}

def write_data(data: dict):
    """Write data to output file."""
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    s = data["stats"]
    print(f"✅ graph data written: {s['total_pages']} pages, {OUTPUT}")

def watch():
    """Watch for changes and rebuild."""
    known = {str(p): p.stat().st_mtime for p in WIKI_DIR.rglob("*.md")}
    print(f"👀 Watching {WIKI_DIR} for changes... (Ctrl+C to stop)")
    while True:
        time.sleep(2)
        changed = False
        for p in WIKI_DIR.rglob("*.md"):
            mtime = p.stat().st_mtime
            if str(p) not in known or known[str(p)] != mtime:
                known[str(p)] = mtime
                changed = True
        if changed:
            print(f"[{time.strftime('%H:%M:%S')}] change detected, rebuilding...")
            data = scan_wiki()
            write_data(data)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        data = scan_wiki()
        write_data(data)
        watch()
    else:
        data = scan_wiki()
        write_data(data)
