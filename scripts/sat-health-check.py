#!/usr/bin/env python3
"""
SAT (System Acceptance Test) — 六层验收 + Recall Test
=====================================================
遵循 ChatGPT 建议的验收框架：
  Hermes → SQLite → LLM Wiki → Obsidian → Git → Graph

Usage:
  python scripts/sat-health-check.py               # 全量测试
  python scripts/sat-health-check.py --quick        # 快速模式（跳过 Recall）
  python scripts/sat-health-check.py --fix          # 自动修复可修复项
"""

import json, os, re, sys, subprocess, datetime, time
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
WIKI_DIR = Path("C:/Users/ChangHui/wiki")
STATE_DB = Path("C:/Users/ChangHui/AppData/Local/hermes/state.db")
HERMES_DIR = Path("C:/Users/ChangHui/AppData/Local/hermes")
LOG_FILE = WIKI_DIR / "sat-report.json"

RESULTS = []  # accumulated test results

def log_result(layer: str, test: str, status: str, detail: str = ""):
    """Record a test result."""
    entry = {
        "layer": layer, "test": test, "status": status,
        "detail": detail, "timestamp": datetime.datetime.now().isoformat()[:19]
    }
    RESULTS.append(entry)
    icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌", "skip": "⏭️ "}.get(status, "❓")
    print(f"  {icon} [{layer}] {test}")
    if detail:
        print(f"     └─ {detail}")
    return status == "pass"

# ═══════════════════════════════════════════════════════════════════════════
# Layer 1: Hermes Runtime
# ═══════════════════════════════════════════════════════════════════════════
def test_hermes_runtime():
    print(f"\n{'='*60}")
    print(f" Layer 1: Hermes Runtime（执行层）")
    print(f"{'='*60}")

    all_pass = True

    # 1a. Hermes 进程/服务是否在运行
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hermes.exe", "/NH"],
            capture_output=True, timeout=10
        )
        stdout_decoded = proc.stdout.decode("utf-8", errors="replace")
        running = "hermes.exe" in stdout_decoded
    except Exception:
        running = False
    all_pass &= log_result("Hermes", "进程运行中",
        "pass" if running else "warn",
        "hermes.exe" if running else "Hermes 进程未独立运行（可能在当前 session 中）")

    # 1b. 检查 state.db 最近更新时间（证明有活动）
    if STATE_DB.exists():
        mtime = datetime.datetime.fromtimestamp(STATE_DB.stat().st_mtime)
        hours_ago = (datetime.datetime.now() - mtime).total_seconds() / 3600
        recent = hours_ago < 24
        all_pass &= log_result("Hermes", "state.db 活跃",
            "pass" if recent else "warn",
            f"最后更新: {mtime.strftime('%Y-%m-%d %H:%M')} ({hours_ago:.1f}h 前)")

    # 1c. Skill 目录是否存在
    skills_dir = HERMES_DIR / "skills"
    skill_exists = skills_dir.exists() and any(skills_dir.iterdir())
    all_pass &= log_result("Hermes", "Skill 目录",
        "pass" if skill_exists else "warn",
        f"{skills_dir}" if skill_exists else "无 skill 目录")

    # 1d. Config 是否可读
    config = HERMES_DIR / "config.yaml"
    config_ok = config.exists()
    all_pass &= log_result("Hermes", "配置文件",
        "pass" if config_ok else "fail",
        f"{config}" if config_ok else "config.yaml 不存在")

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 2: SQLite
# ═══════════════════════════════════════════════════════════════════════════
def test_sqlite():
    print(f"\n{'='*60}")
    print(f" Layer 2: SQLite（状态层）")
    print(f"{'='*60}")

    all_pass = True
    import sqlite3

    # 2a. 数据库文件存在且可读
    db_ok = STATE_DB.exists()
    all_pass &= log_result("SQLite", "数据库文件",
        "pass" if db_ok else "fail",
        f"{STATE_DB} ({STATE_DB.stat().st_size / 1024:.0f} KB)" if db_ok else "state.db 不存在")

    if not db_ok:
        return False

    try:
        conn = sqlite3.connect(str(STATE_DB))
        cur = conn.cursor()

        # 2b. 查询表结构
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        has_sessions = "sessions" in tables
        has_messages = "messages" in tables
        all_pass &= log_result("SQLite", "核心表存在",
            "pass" if has_sessions and has_messages else "fail",
            f"sessions={'✅' if has_sessions else '❌'}, messages={'✅' if has_messages else '❌'}")

        # 2c. 统计记录数
        cur.execute("SELECT COUNT(*) FROM sessions")
        session_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM messages")
        msg_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT model) FROM sessions WHERE model IS NOT NULL")
        model_count = cur.fetchone()[0]
        all_pass &= log_result("SQLite", "数据完整性",
            "pass" if session_count > 0 else "warn",
            f"{session_count} sessions, {msg_count} messages, {model_count} models")

        # 2d. WAL 模式状态
        cur.execute("PRAGMA journal_mode")
        jmode = cur.fetchone()[0]
        all_pass &= log_result("SQLite", "WAL 模式",
            "pass" if jmode == "wal" else "info",
            f"journal_mode = {jmode}")

        conn.close()

        # 2e. sqlite3 CLI 是否可调用
        cli_test = subprocess.run(
            ["where", "sqlite3"],
            capture_output=True, timeout=5
        )
        cli_path = cli_test.stdout.decode("utf-8", errors="replace").strip()
        if cli_path:
            cli_ver = subprocess.run(
                [cli_path.split("\n")[0].strip(), "--version"],
                capture_output=True, timeout=5
            )
            cli_ok = cli_ver.returncode == 0
            all_pass &= log_result("SQLite", "CLI 可用",
                "pass" if cli_ok else "warn",
                cli_ver.stdout.decode("utf-8", errors="replace").strip() if cli_ok else "sqlite3 不可用")
        else:
            all_pass &= log_result("SQLite", "CLI 可用", "warn", "sqlite3 不在 PATH 中")

    except Exception as e:
        all_pass &= log_result("SQLite", "连接测试", "fail", str(e))

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 3: LLM Wiki
# ═══════════════════════════════════════════════════════════════════════════
def test_wiki():
    print(f"\n{'='*60}")
    print(f" Layer 3: LLM Wiki（知识层）")
    print(f"{'='*60}")

    all_pass = True
    wiki = WIKI_DIR

    # 3a. Wiki 目录结构完整
    dirs = ["raw/articles", "raw/papers", "raw/transcripts", "raw/assets",
            "entities", "concepts", "comparisons", "queries"]
    missing_dirs = [d for d in dirs if not (wiki / d).exists()]
    all_pass &= log_result("Wiki", "目录结构",
        "pass" if not missing_dirs else "warn",
        f"完整" if not missing_dirs else f"缺少: {', '.join(missing_dirs)}")

    # 3b. 核心文件存在
    core_files = ["SCHEMA.md", "index.md", "log.md", "graph.json"]
    missing = [f for f in core_files if not (wiki / f).exists()]
    all_pass &= log_result("Wiki", "核心文件",
        "pass" if not missing else "fail",
        f"完整" if not missing else f"缺少: {', '.join(missing)}")

    # 3c. Wiki 节点数量
    md_files = list(wiki.rglob("*.md"))
    page_count = len([f for f in md_files
                      if not f.name.startswith(("SCHEMA", "index", "log"))
                      and ".obsidian" not in str(f)])
    all_pass &= log_result("Wiki", "知识节点",
        "pass" if page_count >= 3 else "warn",
        f"{page_count} 个维基页面")

    # 3d. 前端元数据完整性
    RE_FM = re.compile(r"^---\n([\s\S]*?)\n---", re.MULTILINE)
    bad_pages = 0
    for f in md_files:
        if ".obsidian" in str(f) or f.name in ("SCHEMA.md", "index.md", "log.md", "SCHEMA-GRAPH.md"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        m = RE_FM.match(content)
        if not m:
            bad_pages += 1
    all_pass &= log_result("Wiki", "元数据完整性",
        "pass" if bad_pages == 0 else "warn",
        f"所有页面都有 frontmatter" if bad_pages == 0 else f"{bad_pages} 页缺少 frontmatter")

    # 3e. Wikilink 连通率
    RE_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    total_links = 0
    for f in md_files:
        if ".obsidian" in str(f):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        total_links += len(RE_LINK.findall(content))
    all_pass &= log_result("Wiki", "Wikilink 连通",
        "pass" if total_links >= 3 else "warn",
        f"{total_links} 条 wikilink 引用")

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 4: Obsidian
# ═══════════════════════════════════════════════════════════════════════════
def test_obsidian():
    print(f"\n{'='*60}")
    print(f" Layer 4: Obsidian（认知层）")
    print(f"{'='*60}")

    all_pass = True
    obsidian_dir = WIKI_DIR / ".obsidian"

    # 4a. Obsidian 配置存在
    configs = ["app.json", "obsidian.json"]
    missing = [f for f in configs if not (obsidian_dir / f).exists()]
    all_pass &= log_result("Obsidian", "Vault 配置",
        "pass" if not missing else "warn",
        f"完整" if not missing else f"缺少: {', '.join(missing)}")

    # 4b. Wikilinks 语法兼容性 (检查 SCHEMA 是否声明兼容)
    schema = WIKI_DIR / "SCHEMA.md"
    has_wikilink_convention = False
    if schema.exists():
        s_content = schema.read_text(encoding="utf-8")
        has_wikilink_convention = "wikilink" in s_content.lower() or "[[" in s_content
    all_pass &= log_result("Obsidian", "Wikilink 兼容",
        "pass" if has_wikilink_convention else "warn",
        "SCHEMA.md 声明了 wikilink 约定" if has_wikilink_convention else "SCHEMA 未声明 wikilink 约定")

    # 4c. Vault 根目录有可读的 .md 文件
    root_md = list(WIKI_DIR.glob("*.md"))
    all_pass &= log_result("Obsidian", "Vault 可读性",
        "pass" if len(root_md) >= 3 else "warn",
        f"根目录 {len(root_md)} 个 markdown 文件 (index, SCHEMA, log)")

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 5: Git
# ═══════════════════════════════════════════════════════════════════════════
def test_git():
    print(f"\n{'='*60}")
    print(f" Layer 5: Git（版本层）")
    print(f"{'='*60}")

    all_pass = True

    # 5a. Git 仓库存在
    git_dir = WIKI_DIR / ".git"
    is_repo = git_dir.exists()
    all_pass &= log_result("Git", "仓库存在",
        "pass" if is_repo else "fail",
        f"{git_dir}" if is_repo else "不是 Git 仓库")

    if not is_repo:
        return False

    # 5b. Git 历史
    result = subprocess.run(
        ["git", "log", "--oneline", "--all"],
        cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=10
    )
    commit_count = len([l for l in result.stdout.strip().split("\n") if l.strip()])
    all_pass &= log_result("Git", "提交历史",
        "pass" if commit_count >= 3 else "warn",
        f"{commit_count} 次提交")

    # 5c. 是否有未提交变更
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=10
    )
    unstaged = len([l for l in result.stdout.strip().split("\n") if l.strip()])
    all_pass &= log_result("Git", "工作区干净",
        "pass" if unstaged == 0 else "warn",
        "干净" if unstaged == 0 else f"{unstaged} 个未提交文件")

    # 5d. 能否成功 commit（模拟测试）
    test_file = WIKI_DIR / ".sat-heartbeat"
    test_file.write_text(f"Heartbeat: {datetime.datetime.now().isoformat()}", encoding="utf-8")
    subprocess.run(["git", "add", ".sat-heartbeat"], cwd=str(WIKI_DIR), capture_output=True, timeout=5)
    commit_result = subprocess.run(
        ["git", "commit", "-m", "sat: heartbeat test", "--allow-empty"],
        cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=10
    )
    commit_ok = commit_result.returncode == 0
    # Clean up
    subprocess.run(["git", "reset", "--soft", "HEAD~1"], cwd=str(WIKI_DIR), capture_output=True, timeout=5)
    subprocess.run(["git", "checkout", "--", ".sat-heartbeat"], cwd=str(WIKI_DIR), capture_output=True, timeout=5)
    if test_file.exists():
        test_file.unlink()
    all_pass &= log_result("Git", "提交能力",
        "pass" if commit_ok else "fail",
        "可以创建和撤销 commit" if commit_ok else f"commit 失败: {commit_result.stderr.strip()}")

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 6: Graph
# ═══════════════════════════════════════════════════════════════════════════
def test_graph():
    print(f"\n{'='*60}")
    print(f" Layer 6: Graph（关系层）")
    print(f"{'='*60}")

    all_pass = True
    graph_path = WIKI_DIR / "graph.json"
    data_path = WIKI_DIR / "data.json"

    # 6a. Graph 文件存在
    graph_ok = graph_path.exists() and data_path.exists()
    all_pass &= log_result("Graph", "图数据文件",
        "pass" if graph_ok else "fail",
        f"graph.json ({graph_path.stat().st_size}B), data.json ({data_path.stat().st_size}B)" if graph_ok else "缺少图文件")

    if not graph_ok:
        return False

    # 6b. 节点和边
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        nodes = len(graph.get("nodes", []))
        edges = len(graph.get("edges", []))
        all_pass &= log_result("Graph", "节点数",
            "pass" if nodes >= 5 else "warn",
            f"{nodes} 个节点")

        all_pass &= log_result("Graph", "边数",
            "pass" if edges >= 5 else "warn",
            f"{edges} 条边")

        # 6c. 语义类型多样性
        types = set(n.get("type", "unknown") for n in graph.get("nodes", []))
        all_pass &= log_result("Graph", "语义类型",
            "pass" if len(types) >= 2 else "warn",
            f"{', '.join(sorted(types))}")

        # 6d. wiki-graph.py 可运行
        script = WIKI_DIR / "scripts" / "wiki-graph.py"
        if script.exists():
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(WIKI_DIR), capture_output=True, text=True, timeout=15
            )
            rebuild_ok = result.returncode == 0
            all_pass &= log_result("Graph", "图谱自动重建",
                "pass" if rebuild_ok else "fail",
                result.stdout.strip() if rebuild_ok else result.stderr.strip())
        else:
            all_pass &= log_result("Graph", "图谱自动重建", "skip", "wiki-graph.py 不存在")

    except Exception as e:
        all_pass &= log_result("Graph", "Graph 解析", "fail", str(e))

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 7: Recall Test
# ═══════════════════════════════════════════════════════════════════════════
def test_recall():
    print(f"\n{'='*60}")
    print(f" Layer 7: Recall Test（知识召回 — 进阶）")
    print(f"{'='*60}")

    all_pass = True

    # 7a. Wiki 页面包含可检索内容
    md_files = list(WIKI_DIR.rglob("*.md"))
    pages_with_tags = 0
    pages_with_links = 0
    RE_FM = re.compile(r"^---\n([\s\S]*?)\n---", re.MULTILINE)
    RE_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

    for f in md_files:
        if ".obsidian" in str(f) or f.name in ("SCHEMA.md", "index.md", "log.md"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        m = RE_FM.match(content)
        if m and "tags:" in m.group(1):
            pages_with_tags += 1
        if RE_LINK.search(content):
            pages_with_links += 1

    all_pass &= log_result("Recall", "页面可检索",
        "pass" if pages_with_tags >= 2 else "warn",
        f"{pages_with_tags} 页有标签, {pages_with_links} 页有 wikilink 引用")

    # 7b. 管线脚本支持自动检索
    pipeline_script = WIKI_DIR / "scripts" / "llm-wiki-pipeline.py"
    script_ok = pipeline_script.exists()
    all_pass &= log_result("Recall", "管线脚本存在",
        "pass" if script_ok else "fail",
        f"{pipeline_script}" if script_ok else "不存在")

    # 7c. data.json 可作为检索索引
    data_file = WIKI_DIR / "data.json"
    if data_file.exists():
        try:
            data = json.loads(data_file.read_text(encoding="utf-8"))
            pages = data.get("files", {})
            with_titles = sum(1 for v in pages.values() if v.get("title"))
            all_pass &= log_result("Recall", "检索索引",
                "pass" if with_titles >= 2 else "warn",
                f"data.json 包含 {len(pages)} 页索引, {with_titles} 页有标题")
        except:
            all_pass &= log_result("Recall", "检索索引", "fail", "data.json 解析失败")
    else:
        all_pass &= log_result("Recall", "检索索引", "skip", "data.json 不存在")

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 8: Knowledge Evolution Test
# ═══════════════════════════════════════════════════════════════════════════
def test_knowledge_evolution():
    print(f"\n{'='*60}")
    print(f" Layer 8: Knowledge Evolution（知识演化 — 进阶）")
    print(f"{'='*60}")

    all_pass = True

    # 8a. Graph has concept nodes
    graph_path = WIKI_DIR / "graph.json"
    if graph_path.exists():
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            concept_nodes = [n for n in graph["nodes"] if n["type"] == "concept"]
            pattern_nodes = [n for n in graph["nodes"] if n["type"] == "pattern"]

            all_pass &= log_result("K-Evolution", "概念节点",
                "pass" if len(concept_nodes) >= 5 else "warn",
                f"{len(concept_nodes)} concepts (目标 ≥5)")

            all_pass &= log_result("K-Evolution", "模式节点",
                "pass" if len(pattern_nodes) >= 3 else "warn",
                f"{len(pattern_nodes)} patterns (目标 ≥3)")

            # 8b. Edge types include semantic relationships
            edge_types = {e["type"] for e in graph["edges"]}
            semantic_types = {"is_a", "requires", "depends_on", "implements"}
            found_semantic = semantic_types & edge_types
            missing_semantic = semantic_types - edge_types

            all_pass &= log_result("K-Evolution", "语义边类型",
                "pass" if len(found_semantic) >= 3 else "warn",
                f"找到: {', '.join(sorted(found_semantic))}" if found_semantic else "无语义边")

            # 8c. Knowledge→Capability cross-layer edges
            cross_edges = [e for e in graph["edges"] if e["type"] in ("requires", "has_pattern")]
            all_pass &= log_result("K-Evolution", "跨层关联",
                "pass" if len(cross_edges) >= 3 else "warn",
                f"{len(cross_edges)} 跨层边 (Skill→Concept, Pattern→Concept)")

            # 8d. Entity→Concept implements edges
            impl_edges = [e for e in graph["edges"] if e["type"] == "implements"]
            all_pass &= log_result("K-Evolution", "实体实现关系",
                "pass" if len(impl_edges) >= 2 else "warn",
                f"{len(impl_edges)} implements 边 (Entity→Concept)")

        except Exception as e:
            all_pass &= log_result("K-Evolution", "Graph 解析", "fail", str(e))
    else:
        all_pass &= log_result("K-Evolution", "Graph 文件", "fail", "graph.json 不存在")

    # 8e. Pattern nodes have success_rate metadata
    if graph_path.exists():
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            patterns_with_rate = [n for n in graph["nodes"]
                                  if n["type"] == "pattern" and "success_rate" in n]
            all_pass &= log_result("K-Evolution", "模式成功率",
                "pass" if patterns_with_rate else "warn",
                f"{len(patterns_with_rate)} patterns 有成功率数据" if patterns_with_rate else "无成功率数据")
        except:
            pass

    return all_pass

# ═══════════════════════════════════════════════════════════════════════════
# Layer 9: Skill Evolution Test
# ═══════════════════════════════════════════════════════════════════════════
def test_skill_evolution():
    print(f"\n{'='*60}")
    print(f" Layer 9: Skill Evolution（技能演化 — 进阶）")
    print(f"{'='*60}")

    all_pass = True
    graph_path = WIKI_DIR / "graph.json"

    if not graph_path.exists():
        all_pass &= log_result("S-Evolution", "Graph 文件", "fail", "graph.json 不存在")
        return False

    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))

        # 9a. Skill nodes exist
        skill_nodes = [n for n in graph["nodes"] if n["type"] == "skill"]
        all_pass &= log_result("S-Evolution", "技能节点",
            "pass" if len(skill_nodes) >= 2 else "warn",
            f"{len(skill_nodes)} skills")

        # 9b. Skills have requires edges to concepts
        requires_edges = [e for e in graph["edges"] if e["type"] == "requires"]
        all_pass &= log_result("S-Evolution", "技能依赖 (requires)",
            "pass" if len(requires_edges) >= 2 else "warn",
            f"{len(requires_edges)} requires 边 (Skill→Concept)")

        # 9c. Skills used by sessions
        uses_edges = [e for e in graph["edges"] if e["type"] == "uses"]
        all_pass &= log_result("S-Evolution", "技能使用 (uses)",
            "pass" if len(uses_edges) >= 2 else "warn",
            f"{len(uses_edges)} uses 边 (Session→Skill)")

        # 9d. Pipeline supports skill evolution (check for version field in config)
        pipeline_script = WIKI_DIR / "scripts" / "llm-wiki-pipeline.py"
        if pipeline_script.exists():
            content = pipeline_script.read_text(encoding="utf-8")
            has_domain_concepts = "DOMAIN_CONCEPTS" in content
            all_pass &= log_result("S-Evolution", "管线支持知识演化",
                "pass" if has_domain_concepts else "warn",
                "DOMAIN_CONCEPTS 知识库已定义" if has_domain_concepts else "缺少知识库")

        # 9e. SCHEMA-GRAPH.md exists (evolution rules defined)
        schema_graph = WIKI_DIR / "SCHEMA-GRAPH.md"
        schema_ok = schema_graph.exists()
        all_pass &= log_result("S-Evolution", "演化规则文档",
            "pass" if schema_ok else "warn",
            "SCHEMA-GRAPH.md 定义了演化规则" if schema_ok else "缺少 SCHEMA-GRAPH.md")

    except Exception as e:
        all_pass &= log_result("S-Evolution", "测试异常", "fail", str(e))

    return all_pass


def main():
    quick = "--quick" in sys.argv
    auto_fix = "--fix" in sys.argv

    print(f"\n{'#'*60}")
    print(f"#  Hermes Cognitive Pipeline — SAT 健康检查")
    print(f"#  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    layers = [
        ("Hermes", test_hermes_runtime),
        ("SQLite", test_sqlite),
        ("Wiki",   test_wiki),
        ("Obsidian", test_obsidian),
        ("Git",    test_git),
        ("Graph",  test_graph),
    ]

    if not quick:
        layers.append(("Recall", test_recall))
        layers.append(("Knowledge Evolution", test_knowledge_evolution))
        layers.append(("Skill Evolution", test_skill_evolution))

    passed = 0
    failed = 0
    layer_results = []

    for name, fn in layers:
        try:
            ok = fn()
        except Exception as e:
            print(f"  ❌ [{name}] 异常: {e}")
            ok = False
        layer_results.append((name, ok))
        if ok:
            passed += 1
        else:
            failed += 1
        print()

    # Summary
    total = passed + failed
    print(f"\n{'='*60}")
    print(f" 📊 SAT 健康检查总结")
    print(f"{'='*60}")
    for name, ok in layer_results:
        icon = "✅" if ok else "⚠️ "
        print(f"  {icon} {name}")
    print(f"\n  PASS: {passed}/{total}  |  WARN/FAIL: {failed}/{total}")

    # 生成 JSON 报告
    report = {
        "timestamp": datetime.datetime.now().isoformat()[:19],
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.0f}%"
        },
        "results": RESULTS
    }
    LOG_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  报告已保存: {LOG_FILE}")

    if auto_fix and failed > 0:
        print(f"\n🔧 自动修复模式 — 请使用 python scripts/llm-wiki-pipeline.py 重新生成")

    # 结论
    if failed == 0:
        print(f"\n{'#'*60}")
        print(f"#  ✅ System Healthy — 全线贯通")
        print(f"{'#'*60}")
    else:
        print(f"\n{'#'*60}")
        print(f"#  ⚠️  {failed} 层需关注 — 建议修复后重测")
        print(f"{'#'*60}")

if __name__ == "__main__":
    main()
