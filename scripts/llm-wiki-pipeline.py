#!/usr/bin/env python3
"""
Hermes → SQLite → Wiki → Obsidian → Git 管线脚本 v2
========================================================
遵循 ChatGPT SAT 框架，生成两层维基结构：
  topics/       ← 知识主题层（可检索、可关联）
  entities/     ← 会话追溯层（原始来源）

Usage:
  python scripts/llm-wiki-pipeline.py              # 正常运行
  python scripts/llm-wiki-pipeline.py --dry-run    # 试跑不写入
  python scripts/llm-wiki-pipeline.py --recall     # 模拟知识召回测试

Flow:
  1. Connect to Hermes state.db
  2. Query recent sessions
  3. Extract topics → generate topics/*.md (知识节点)
  4. Generate entities/*.md (追溯节点)
  5. Build semantic graph.json
  6. Rebuild data.json via wiki-graph.py
  7. Git commit (version)
"""

import json, os, re, sys, subprocess, datetime
from pathlib import Path
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────
WIKI_DIR = Path(os.environ.get("WIKI_PATH", "C:/Users/ChangHui/wiki"))
STATE_DB = Path(os.environ.get("HERMES_STATE_DB",
    "C:/Users/ChangHui/AppData/Local/hermes/state.db"))
SCRIPTS_DIR = WIKI_DIR / "scripts"
GRAPH_SCRIPT = SCRIPTS_DIR / "wiki-graph.py"

# ── Topic taxonomy: extract semantic keywords from session titles ──────────
TOPIC_KEYWORDS = {
    "Hermes Agent":           ["hermes", "agent", "skill", "tool", "plugin", "profile",
                                "hermes-agent", "mcp", "gateway", "cron"],
    "AI Agent":               ["ai agent", "agent", "autonomous", "multi-agent", "workflow",
                                "codex", "claude code", "opencode"],
    "SQLite":                 ["sqlite", "database", "db", "state.db", "wal", "fts"],
    "Knowledge Graph":        ["graph", "wiki", "knowledge", "节点", "图谱", "link",
                                "wikilink", "node"],
    "LLM / Model":            ["llm", "model", "gemma", "deepseek", "transformer",
                                "gpt", "inference", "训练"],
    "Development":            ["python", "git", "deploy", "install", "代码", "debug",
                                "test", "pipeline", "ci/cd"],
    "Obsidian / Note-taking": ["obsidian", "vault", "note", "笔记", "日记"],
    "Research":               ["paper", "arxiv", "research", "分析", "趋势", "梳理",
                                "review", "survey"],
    "Content Production":     ["content", "factory", "生成", "writing", "essay",
                                "article", "创作"],
    "System / DevOps":        ["system", "config", "setup", "安装", "环境",
                                "windows", "linux", "network"],
}

def extract_topics(session: dict) -> list[str]:
    """Extract relevant topic names from a session title."""
    title = (session.get("title") or "").lower()
    matched = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title:
                matched.append(topic)
                break
    # Default fallback
    if not matched:
        first_word = (session.get("title") or "").split()[0] if (session.get("title") or "") else "General"
        matched = [f"Topic: {first_word[:20]}"]
    return matched

def extract_skills_from_model(model: str) -> list[str]:
    """Extract skill/pattern from model name."""
    if not model:
        return []
    skills = []
    m = model.lower()
    if "gemma" in m:
        skills.extend(["Gemma", "Google AI"])
    if "deepseek" in m:
        skills.extend(["DeepSeek", "MoE Inference"])
    if "gpt" in m or "chatgpt" in m:
        skills.append("OpenAI GPT")
    if "claude" in m or "sonnet" in m:
        skills.append("Claude")
    if "llama" in m:
        skills.extend(["LLaMA", "Local Inference"])
    if "/" in model:
        provider = model.split("/")[0]
        skills.append(f"Provider: {provider}")
    return skills

def safe_slug(text: str, max_len: int = 40) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', text.lower()).strip('-')
    # Keep Chinese characters
    return slug[:max_len].rstrip('-') or "untitled"

# ── SQLite Connection ──────────────────────────────────────────────────────
def connect_db(db_path: Path) -> tuple:
    import sqlite3
    print(f"🔌 Connecting to SQLite: {db_path} ({db_path.stat().st_size / 1024:.0f} KB)")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def query_recent_sessions(cur, limit: int = 5) -> list[dict]:
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  📊 Tables: {', '.join(tables[:12])}{'...' if len(tables) > 12 else ''}")

        if "sessions" in tables:
            cur.execute(f"""
                SELECT id, title, started_at, ended_at, message_count,
                       input_tokens, output_tokens, model
                FROM sessions
                WHERE title IS NOT NULL AND title != ''
                ORDER BY started_at DESC
                LIMIT {limit}
            """)
            rows = cur.fetchall()
            if rows:
                result = []
                for r in rows:
                    d = dict(r)
                    if d.get("started_at"):
                        d["started_at"] = datetime.datetime.fromtimestamp(
                            d["started_at"]).strftime("%Y-%m-%d %H:%M")
                    if d.get("ended_at"):
                        d["ended_at"] = datetime.datetime.fromtimestamp(
                            d["ended_at"]).strftime("%Y-%m-%d %H:%M")
                    result.append(d)
                return result

        print("  ℹ️  No sessions found")
        return []

    except Exception as e:
        print(f"  ⚠️  Query error: {e}")
        return []

# ── Wiki Page Generators ───────────────────────────────────────────────────

def generate_topic_page(topic: str, sessions: list[dict]) -> tuple[str, str]:
    """Generate a topic-level wiki page in topics/. Returns (slug, content)."""
    slug = safe_slug(topic)
    today = datetime.date.today().isoformat()

    # Collect all linked entities and skills from sessions under this topic
    linked_entities = set()
    linked_skills = set()
    for s in sessions:
        slug_session = safe_slug(s.get("title", "")[:40])
        linked_entities.add(slug_session)
        for skill in extract_skills_from_model(s.get("model", "")):
            linked_skills.add(skill)

    skill_links = "\n".join(f"  - [[{s}]]" for s in sorted(linked_skills)) if linked_skills else "  - (待补充)"
    entity_links = "\n".join(f"  - [[entities/{e}|{e}]]" for e in sorted(linked_entities)) if linked_entities else "  - (待补充)"

    # Build links YAML
    links_yaml_list = []
    for e in sorted(linked_entities):
        links_yaml_list.append(f"  - entities/{e}")
    for s in sorted(linked_skills):
        links_yaml_list.append(f"  - skill:{s}")
    links_yaml = "\n" + "\n".join(links_yaml_list) if links_yaml_list else " []"

    content = f"""---
id: topic_{slug}
title: "{topic}"
created: {today}
updated: {today}
type: topic
tags: [hermes, topic, knowledge]
links:{links_yaml}
session_count: {len(sessions)}
---

# {topic}

> **Knowledge Layer — 自动生成的主题节点**

## 概述

本主题自动从 Hermes 会话数据中提取生成。
关联 {len(sessions)} 个会话，涵盖以下技能和实体。

## 关联技能 (Skills)

{skill_links}

## 关联会话 (Sessions)

{entity_links}

## 来源

- 数据源: Hermes state.db (SQLite)
- 生成管线: llm-wiki-pipeline.py v2
- 生成时间: {today}

> 编辑此页面以完善知识内容并添加更多 [[SCHEMA|交叉引用]]。
"""

    return slug, content

def generate_session_page(session: dict) -> tuple[str, str]:
    """Generate a session traceability page in entities/."""
    title = session.get("title", "Untitled Session") or "Untitled Session"
    slug = safe_slug(title[:40]) or f"session-{session.get('id', 'unknown')}"
    started = session.get("started_at", "unknown")[:10]
    ended = session.get("ended_at", "in progress")[:10] if session.get("ended_at") else "in progress"
    model = session.get("model", "unknown")
    tokens_total = (session.get("input_tokens", 0) or 0) + (session.get("output_tokens", 0) or 0)
    topics = extract_topics(session)

    topic_links = "\n".join(f"  - [[{safe_slug(t)}|{t}]]" for t in topics) if topics else "  - (待归类)"

    content = f"""---
title: "{title}"
session_id: "{session.get('id')}"
started: {started}
ended: {ended}
type: session
model: {model}
tokens: {tokens_total}
messages: {session.get('message_count', 0)}
tags: [hermes, session, {model.split('/')[0] if '/' in model else model}]
topics: [{', '.join('"' + t + '"' for t in topics)}]
---

# {title}

**Session:** `{session.get('id')}` | **Model:** {model}
**Messages:** {session.get('message_count', 0)} | **Tokens:** {tokens_total:,}
**Started:** {started} | **Ended:** {ended}

## 关联主题 (Topics)

{topic_links}

## Raw Data

- 数据源: Hermes state.db
- 生成管线: llm-wiki-pipeline.py v2
"""

    return slug, content

def write_page(content: str, slug: str, subdir: str) -> Path:
    """Write a wiki page and return its path."""
    path = WIKI_DIR / subdir / f"{slug}.md"
    path.write_text(content, encoding="utf-8")
    print(f"  📝 {path.relative_to(WIKI_DIR)}")
    return path

# ── Knowledge Base: Domain Concepts ──────────────────────────────────────
# Pre-defined concept/pattern/entity hierarchies for auto-extraction
DOMAIN_CONCEPTS = {
    "ai-agent": {
        "title": "AI Agent",
        "concepts": [
            ("c_planning",        "Planning",        "任务规划与分解"),
            ("c_reflection",      "Reflection",      "自我反思与修正"),
            ("c_memory",          "Memory",          "长期/短期记忆管理"),
            ("c_tool_calling",    "Tool Calling",    "工具调用与编排"),
            ("c_reasoning",       "Reasoning",       "推理与思维链"),
            ("c_multi_agent",     "Multi-Agent",     "多智能体协作"),
            ("c_feedback",        "Feedback Loop",   "反馈循环与迭代"),
            ("c_autonomy",        "Autonomy",        "自主决策与执行"),
        ],
        "patterns": [
            ("p_trend_analysis",   "趋势分析模式",    0.85, ["科技", "财经"]),
            ("p_reflection_loop",  "反思循环模式",    0.78, ["写作", "编程"]),
            ("p_tool_orchestrate", "工具编排模式",    0.80, ["自动化"]),
        ],
        "entities": [
            ("e_hermes",    "Hermes",    "Hermes Agent by Nous Research"),
            ("e_openai",    "OpenAI",    "OpenAI GPT models"),
            ("e_anthropic", "Anthropic", "Anthropic Claude models"),
            ("e_deepseek",  "DeepSeek",  "DeepSeek models (MoE)"),
            ("e_google",    "Google",    "Google Gemini / Gemma models"),
        ]
    },
    "sqlite": {
        "title": "SQLite",
        "concepts": [
            ("c_wal_mode",          "WAL Mode",         "预写日志模式"),
            ("c_fts5",              "FTS5",             "全文搜索引擎"),
            ("c_rtree",             "RTree",            "空间索引"),
            ("c_transaction",       "Transaction",      "事务与ACID"),
            ("c_vacuum",            "Vacuum",           "空间回收"),
        ],
        "patterns": [
            ("p_wal_optimize",      "WAL 优化模式",     0.90, ["高写入场景"]),
            ("p_fts_query",         "FTS 查询模式",     0.85, ["全文搜索"]),
        ],
        "entities": [
            ("e_sqlite",  "SQLite",   "嵌入式关系数据库"),
            ("e_dbeaver", "DBeaver",  "数据库管理工具"),
        ]
    },
    "hermes-agent": {
        "title": "Hermes Agent",
        "concepts": [
            ("c_skill_system",      "Skill System",    "技能与Skill体系"),
            ("c_tool_system",       "Tool System",     "工具调用系统"),
            ("c_state_db",          "State DB",        "Hermes状态数据库"),
            ("c_pipeline",          "Pipeline",        "数据管线"),
            ("c_cron",              "Cron Jobs",       "定时任务"),
            ("c_gateway",           "Gateway",         "消息网关"),
        ],
        "patterns": [
            ("p_skill_chain",       "Skill 链模式",    0.75, ["知识工作流"]),
            ("p_cron_sync",         "定时同步模式",    0.88, ["数据备份"]),
        ],
        "entities": [
            ("e_nous",     "Nous Research", "Hermes Agent 开发团队"),
        ]
    },
    "research": {
        "title": "Research",
        "concepts": [
            ("c_paper_analysis",    "Paper Analysis",   "论文分析"),
            ("c_literature_review", "Literature Review", "文献综述"),
            ("c_benchmark",         "Benchmark",        "基准测试"),
        ],
        "patterns": [
            ("p_paper_summary",     "论文摘要模式",    0.80, ["学术"]),
        ],
        "entities": []
    }
}

def build_knowledge_graph(topic_pages: list[tuple], session_pages: list[tuple],
                          topic_map: dict[str, list[dict]]):
    """Build v3 knowledge graph with 4-layer architecture.

    Knowledge Layer:  topic → concept → entity → pattern → evidence
    Capability Layer: skill → workflow → prompt → tool
    Execution Layer:  session → task → run → result
    Artifact Layer:   content → report → summary → media
    """
    graph_path = WIKI_DIR / "graph.json"
    today = datetime.date.today().isoformat()

    nodes = []
    edges = []
    seen_ids = set()

    # ── Seed meta nodes ──
    for mid, mtype in [("SCHEMA", "meta"), ("index", "meta"), ("log", "meta"),
                       ("SCHEMA-GRAPH", "meta")]:
        nodes.append({"id": mid, "type": mtype, "title": mid,
                      "path": f"{mid.lower()}.md", "tags": ["hermes", "meta"]})
        seen_ids.add(mid)
    edges.append({"source": "index", "target": "SCHEMA", "type": "navigates"})
    edges.append({"source": "log", "target": "SCHEMA", "type": "references"})
    edges.append({"source": "SCHEMA-GRAPH", "target": "SCHEMA", "type": "references"})

    # ── Knowledge Layer: Topic nodes ──
    for slug, content in topic_pages:
        if slug not in seen_ids:
            nodes.append({
                "id": slug, "type": "topic",
                "title": slug.replace("-", " ").title(),
                "path": f"topics/{slug}.md",
                "tags": ["hermes", "topic", "knowledge"]
            })
            seen_ids.add(slug)

    # ── Knowledge Layer: Concept + Entity + Pattern nodes ──
    for slug, _ in topic_pages:
        # Find domain data for this slug
        domain = DOMAIN_CONCEPTS.get(slug, {})
        if not domain:
            continue

        # Concepts
        for cid, cname, cdesc in domain.get("concepts", []):
            if cid not in seen_ids:
                nodes.append({
                    "id": cid, "type": "concept",
                    "title": cname,
                    "description": cdesc,
                    "tags": ["knowledge", slug]
                })
                seen_ids.add(cid)
            # is_a: Concept → Topic
            edges.append({"source": cid, "target": slug, "type": "is_a"})

        # Patterns
        for pid, pname, rate, applies in domain.get("patterns", []):
            if pid not in seen_ids:
                nodes.append({
                    "id": pid, "type": "pattern",
                    "title": pname,
                    "success_rate": rate,
                    "applies_to": applies,
                    "tags": ["knowledge", slug]
                })
                seen_ids.add(pid)
            # belongs_to: Pattern → Topic
            edges.append({"source": pid, "target": slug, "type": "belongs_to"})

        # Entities
        for eid, ename, edesc in domain.get("entities", []):
            if eid not in seen_ids:
                nodes.append({
                    "id": eid, "type": "entity",
                    "title": ename,
                    "description": edesc,
                    "tags": ["knowledge", slug]
                })
                seen_ids.add(eid)
            # belongs_to: Entity → Topic
            edges.append({"source": eid, "target": slug, "type": "belongs_to"})

    # ── Capability Layer: Skill nodes (extracted from models) ──
    for slug, content in session_pages:
        m = re.search(r"model: (.+)", content)
        if m:
            model = m.group(1).strip()
            for skill in extract_skills_from_model(model):
                sid = safe_slug(f"s_{skill}")
                if sid not in seen_ids:
                    nodes.append({
                        "id": sid, "type": "skill",
                        "title": skill,
                        "tags": ["capability", "skill"]
                    })
                    seen_ids.add(sid)
                edges.append({"source": slug, "target": sid, "type": "uses"})

    # ── Knowledge→Capability edges: Skill requires Concepts ──
    # e.g. skill_google_ai → c_reasoning, c_tool_calling
    skill_concept_map = {
        "s-google-ai":         ["c_reasoning", "c_tool_calling", "c_memory"],
        "s-deepseek":          ["c_reasoning", "c_multi_agent"],
        "s-claude":            ["c_reflection", "c_reasoning"],
        "s-llama":             ["c_reasoning"],
        "s-local-inference":   ["c_reasoning", "c_memory"],
        "s-provider-deepseek": ["c_multi_agent", "c_reasoning"],
        "s-provider-google":   ["c_tool_calling", "c_reasoning"],
    }
    for sid, concept_ids in skill_concept_map.items():
        if sid in seen_ids:
            for cid in concept_ids:
                if cid in seen_ids:
                    edges.append({"source": sid, "target": cid, "type": "requires"})

    # ── Capability→Knowledge: Pattern→Concept (has_pattern) ──
    pattern_concept_map = {
        "p_trend_analysis":    ["c_reasoning", "c_planning"],
        "p_reflection_loop":   ["c_reflection", "c_feedback"],
        "p_tool_orchestrate":  ["c_tool_calling"],
        "p_wal_optimize":      ["c_wal_mode"],
        "p_fts_query":         ["c_fts5"],
        "p_skill_chain":       ["c_skill_system", "c_pipeline"],
        "p_cron_sync":         ["c_cron"],
    }
    for pid, concept_ids in pattern_concept_map.items():
        if pid in seen_ids:
            for cid in concept_ids:
                if cid in seen_ids:
                    edges.append({"source": pid, "target": cid, "type": "has_pattern"})

    # ── Knowledge→Knowledge: Concept depends_on Concept ──
    concept_deps = [
        ("c_multi_agent", "c_planning"),
        ("c_reflection",  "c_reasoning"),
        ("c_memory",      "c_tool_calling"),
        ("c_autonomy",    "c_planning"),
        ("c_feedback",    "c_reflection"),
        ("c_tool_calling","c_reasoning"),
    ]
    for src, tgt in concept_deps:
        if src in seen_ids and tgt in seen_ids:
            edges.append({"source": src, "target": tgt, "type": "depends_on"})

    # ── Entity implements Concept ──
    entity_implements = {
        "e_hermes":   ["c_skill_system", "c_tool_system", "c_state_db", "c_gateway"],
        "e_openai":   ["c_reasoning"],
        "e_anthropic": ["c_reflection"],
        "e_deepseek":  ["c_multi_agent", "c_reasoning"],
        "e_google":    ["c_tool_calling"],
    }
    for eid, concept_ids in entity_implements.items():
        if eid in seen_ids:
            for cid in concept_ids:
                if cid in seen_ids:
                    edges.append({"source": eid, "target": cid, "type": "implements"})

    # ── Execution Layer: Session nodes ──
    for slug, content in session_pages:
        if slug not in seen_ids:
            # Extract model from frontmatter
            m = re.search(r"model: (.+)", content)
            model_info = m.group(1).strip() if m else "unknown"
            nodes.append({
                "id": slug, "type": "session",
                "title": slug.replace("-", " ").title(),
                "path": f"entities/{slug}.md",
                "model": model_info,
                "tags": ["hermes", "session", "execution"]
            })
            seen_ids.add(slug)

    # ── Execution→Knowledge: Session references Topic ──
    for topic_name, sessions in topic_map.items():
        t_slug = safe_slug(topic_name)
        if t_slug not in seen_ids:
            continue
        for s in sessions:
            s_slug = safe_slug((s.get("title") or "")[:40])
            if s_slug in seen_ids:
                edges.append({"source": s_slug, "target": t_slug, "type": "references"})

    # ── Build graph ──
    graph = {
        "meta": {
            "type": "knowledge-graph",
            "version": "3.0.0",
            "schema": "4-layer",
            "description": "4-layer knowledge graph: Knowledge→Capability→Execution→Artifact",
            "last_updated": today,
            "node_types": sorted(set(n["type"] for n in nodes)),
            "edge_types": sorted(set(e["type"] for e in edges))
        },
        "nodes": nodes,
        "edges": edges
    }

    # Remove duplicates (same source+target+type)
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = (e["source"], e["target"], e["type"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)
    graph["edges"] = unique_edges

    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  📊 graph.json v3: {len(nodes)} nodes ({len(graph['meta']['node_types'])} types), "
          f"{len(unique_edges)} edges ({len(graph['meta']['edge_types'])} types)")
    return graph

# ── Git Operations ──────────────────────────────────────────────────────────
def git_commit(message: str, dry_run: bool = False):
    if dry_run:
        print(f"  🏃 Dry-run: '{message}'")
        return

    subprocess.run(["git", "add", "-A"], cwd=str(WIKI_DIR),
                   capture_output=True, timeout=15)

    result = subprocess.run(["git", "diff", "--cached", "--quiet"],
                            cwd=str(WIKI_DIR), capture_output=True, timeout=10)
    if result.returncode == 0:
        print("  ✅ No changes to commit")
        return

    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        summary = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else "committed"
        print(f"  ✅ {summary}")
    else:
        print(f"  ⚠️  {result.stderr.strip()}")

# ── Recall Test ────────────────────────────────────────────────────────────
def run_recall_test():
    """Simulate the Recall Test: verify existing wiki pages are retrievable."""
    print(f"\n🔁 Recall Test (知识召回验证)")
    all_pass = True

    # Check if topics exist
    topic_files = list((WIKI_DIR / "topics").glob("*.md"))
    print(f"  📂 Found {len(topic_files)} topic pages")

    if not topic_files:
        print("  ⚠️  No topic pages found for recall")
        return False

    # Verify each topic has frontmatter with links
    RE_FM = re.compile(r"^---\n([\s\S]*?)\n---", re.MULTILINE)
    for tf in topic_files:
        content = tf.read_text(encoding="utf-8")
        m = RE_FM.match(content)
        if m:
            fm = m.group(1)
            has_links = "links:" in fm
            has_session = "session_count:" in fm
            status = "✅" if (has_links and has_session) else "⚠️ "
            print(f"  {status} {tf.name} — links={'✅' if has_links else '❌'} sessions={'✅' if has_session else '❌'}")
        else:
            print(f"  ⚠️  {tf.name} — no frontmatter (NOT recallable)")

    # Verify graph can be queried
    graph_path = WIKI_DIR / "graph.json"
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        topic_nodes = [n for n in graph["nodes"] if n["type"] == "topic"]
        topic_edges = [e for e in graph["edges"] if e["type"] == "contains"]
        print(f"  📊 Graph queryable: {len(topic_nodes)} topics, {len(topic_edges)} topic→session edges")
        if topic_nodes:
            print(f"  ✅ Recall ready — topics can be found via graph.json index")
        else:
            print(f"  ⚠️  No topic nodes in graph")
            all_pass = False

    print(f"  {'✅ Recall test passed' if all_pass else '⚠️  Some checks need attention'}")
    return all_pass

# ── Main Pipeline ──────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv
    recall_mode = "--recall" in sys.argv
    db_path = STATE_DB

    for i, arg in enumerate(sys.argv):
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = Path(sys.argv[i + 1])

    print(f"\n{'='*60}")
    print(f" 🚀 Hermes → SQLite → Wiki → Obsidian → Git Pipeline v2")
    print(f"{'='*60}")
    print(f"  Wiki: {WIKI_DIR}")

    if recall_mode:
        print(f"  Mode: RECALL TEST")
        run_recall_test()
        return

    if dry_run:
        print(f"  Mode: DRY RUN")

    # Step 1: SQLite
    print(f"\n📡 Step 1: SQLite Connection")
    try:
        conn, cur = connect_db(db_path)
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        sys.exit(1)

    # Step 2: Query sessions
    print(f"\n🔍 Step 2: Query Data")
    sessions = query_recent_sessions(cur)
    conn.close()

    if not sessions:
        print("  ℹ️  No sessions, creating sample data")
        sessions = [{
            "id": "demo", "title": "AI Agent 趋势分析",
            "started_at": "2026-06-27 10:00", "ended_at": "2026-06-27 10:30",
            "message_count": 15, "input_tokens": 5000, "output_tokens": 3000,
            "model": "deepseek/deepseek-v4-flash"
        }]

    for s in sessions:
        print(f"  - [{s.get('id')[:8]}...] {s.get('title', 'Untitled')[:50]}")

    # Step 3: Group sessions by topic
    print(f"\n✍️  Step 3: Semantic Topic Extraction")
    topic_map = defaultdict(list)
    for s in sessions:
        topics = extract_topics(s)
        for t in topics:
            topic_map[t].append(s)

    print(f"  📊 Extracted {len(topic_map)} topics from {len(sessions)} sessions")
    for t, ss in sorted(topic_map.items()):
        print(f"     └─ {t}: {len(ss)} sessions")

    # Step 4: Generate topic pages
    print(f"\n📄 Step 4: Generate Topic Pages (Knowledge Layer)")
    topic_pages = []
    if not dry_run:
        for topic, ss in topic_map.items():
            slug, content = generate_topic_page(topic, ss)
            path = write_page(content, slug, "topics")
            topic_pages.append((slug, content))

    # Step 5: Generate session pages (Traceability Layer)
    print(f"\n📄 Step 5: Generate Session Pages (Traceability Layer)")
    session_pages = []
    if not dry_run:
        for s in sessions:
            slug, content = generate_session_page(s)
            path = write_page(content, slug, "entities")
            session_pages.append((slug, content))

    # Step 6: Build semantic graph
    print(f"\n🔗 Step 6: Build Semantic Graph")
    if not dry_run:
        graph = build_knowledge_graph(topic_pages, session_pages, dict(topic_map))

    # Step 7: Rebuild data.json via wiki-graph.py
    if GRAPH_SCRIPT.exists() and not dry_run:
        print(f"\n🔄 Step 7: Full Graph Rebuild")
        result = subprocess.run(
            [sys.executable, str(GRAPH_SCRIPT)],
            cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  ⚠️  {result.stderr.strip()}")

    # Step 8: Git commit
    print(f"\n🔖 Step 8: Git Version")
    if not dry_run:
        git_commit(
            f"pipeline: wiki sync [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] "
            f"({len(topic_pages)} topics, {len(session_pages)} sessions)",
            dry_run=False
        )

    # Step 9: Run recall test
    print(f"\n🔁 Step 9: Recall Test")
    if not dry_run:
        run_recall_test()

    # Summary
    print(f"\n{'='*60}")
    print(f" ✅ Pipeline v2 Complete")
    print(f"{'='*60}")
    print(f"  SQLite   →  {db_path}")
    print(f"  Topics   →  {WIKI_DIR}/topics/ ({len(topic_pages)} pages)")
    print(f"  Sessions →  {WIKI_DIR}/entities/ ({len(session_pages)} pages)")
    print(f"  Graph    →  graph.json ({len(graph.get('nodes', []))} nodes)" if not dry_run else "  Graph    →  (dry-run)")
    print(f"  Obsidian →  {WIKI_DIR}/.obsidian/")
    print(f"  Git      →  {WIKI_DIR}/.git/")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
