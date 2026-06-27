# LLM Wiki Graph Schema v3

> 定义 Hermes 知识图谱的节点类型、边类型、元数据规范和演化规则。
> 遵循 4 层架构：
>   Knowledge Layer → Capability Layer → Execution Layer → Artifact Layer
> 
> 在 Schema 稳定之前，不急于引入 Neo4j/Qdrant/PostgreSQL。
> 当前存储：graph.json (Markdown + JSON)，未来可低成本迁移。

---

## 1. 架构总览

```
Knowledge Layer              Capability Layer        Execution Layer      Artifact Layer
╔══════════════════════╗     ╔═══════════════════╗   ╔═════════════════╗   ╔══════════════════╗
║  Topic               ║     ║  Skill            ║   ║  Session        ║   ║  Content         ║
║  Concept             ║ ──▶ ║  Workflow         ║──▶║  Task           ║──▶║  Report          ║
║  Entity              ║     ║  Prompt           ║   ║  Run            ║   ║  Summary         ║
║  Pattern             ║     ║  Tool             ║   ║  Result         ║   ║  Media           ║
║  Evidence            ║     ╚═══════════════════╝   ╚═════════════════╝   ╚══════════════════╝
╚══════════════════════╝
         │                       │                        │                       │
         └────── Knowledge ──────┴────── Capability ──────┴────── Execution ──────┴────── Artifact
```

---

## 2. 节点类型 (Node Types)

### 2.1 Knowledge Layer

| 节点类型 | ID 前缀 | 说明 | 必需字段 |
|---------|--------|------|---------|
| `topic` | `t_` | 知识主题，如 "AI Agent"、"SQLite" | id, title, type, created, tags |
| `concept` | `c_` | 核心概念，如 "Planning"、"Reflection" | id, title, type, created, parent_topic |
| `entity` | `e_` | 命名实体，如 "Hermes"、"Obsidian" | id, title, type, created, aliases[] |
| `pattern` | `p_` | 可复用模式，如 "hook_conflict_v1" | id, title, type, created, success_rate, applies_to[] |
| `evidence` | `ev_` | 数据/事实支撑，如 "benchmark_2026" | id, title, type, created, source, confidence |

**示例 — Pattern 节点：**
```json
{
  "id": "p_hook_conflict_v1",
  "type": "pattern",
  "title": "冲突式开头模式",
  "success_rate": 0.82,
  "applies_to": ["财经", "科技", "公众号"],
  "created": "2026-06-27"
}
```

### 2.2 Capability Layer

| 节点类型 | ID 前缀 | 说明 | 必需字段 |
|---------|--------|------|---------|
| `skill` | `s_` | 可执行能力，如 "content_writer" | id, title, type, version, requires[] |
| `workflow` | `w_` | 多步流程，如 "write→review→publish" | id, title, type, steps[] |
| `prompt` | `pr_` | 提示词模板 | id, title, type, version |
| `tool` | `tl_` | 外部工具，如 "web_search" | id, title, type, provider |

**示例 — Skill 节点：**
```json
{
  "id": "s_content_writer_v2",
  "type": "skill",
  "title": "内容写作 v2",
  "version": 2,
  "requires": ["c_planning", "p_hook_conflict_v1"],
  "patterns": ["p_hook_conflict_v1", "p_trend_analysis"]
}
```

### 2.3 Execution Layer

| 节点类型 | ID 前缀 | 说明 | 必需字段 |
|---------|--------|------|---------|
| `session` | `ses_` | Hermes 会话 | id, title, type, started_at, model |
| `task` | `tsk_` | 具体任务 | id, title, type, status, session_id |
| `run` | `r_` | 单次执行 | id, type, task_id, duration_ms |
| `result` | `res_` | 执行结果 | id, type, run_id, status, output_summary |

### 2.4 Artifact Layer

| 节点类型 | ID 前缀 | 说明 | 必需字段 |
|---------|--------|------|---------|
| `content` | `ct_` | 生成内容（文章/消息） | id, title, type, created, path |
| `report` | `rp_` | 结构化报告 | id, title, type, created, sections[] |
| `summary` | `sm_` | 摘要 | id, title, type, source_ids[] |
| `media` | `m_` | 图片/视频 | id, title, type, format, path |

---

## 3. 边类型 (Edge Types)

| 边类型 | 源→目标 | 含义 | 示例 |
|--------|---------|------|------|
| `is_a` | Concept → Topic | 概念属于某主题 | Planning → AI Agent |
| `contains` | Topic → Concept | 主题包含概念 | AI Agent → Reflection |
| `requires` | Skill → Concept | 能力依赖概念 | content_writer → Planning |
| `uses` | Workflow → Skill | 流程使用能力 | write_article → content_writer |
| `references` | Session → Topic | 会话引用主题 | ses_xxx → AI Agent |
| `evolved_from` | Node → Node (same type) | 演化关系 | v2 → v1 |
| `has_pattern` | Content → Pattern | 内容使用了模式 | article_123 → hook_conflict_v1 |
| `implements` | Entity → Concept | 实体实现了概念 | Hermes → Reflection |
| `produces` | Run → Content | 执行产生内容 | r_456 → ct_789 |
| `evidence_for` | Evidence → Concept | 证据支持概念 | benchmark → Planning |
| `depends_on` | Concept → Concept | 概念间依赖 | Reflection → Planning |
| `success_rate` | Pattern → (float) | 模式成功率 | (node attribute, not edge) |

---

## 4. 演化规则 (Evolution Rules)

### 4.1 Knowledge Evolution

当一个新概念出现时，系统应自动：
1. 检查已有 Concept 节点中是否覆盖
2. 如为新概念 → 创建 Concept 节点，关联到 Topic
3. 检查与已有概念的关系 → 自动补边
4. 当某个 Topic 下 Concept 数量 > 10 → 触发子 Topic 拆分

### 4.2 Skill Evolution

当某个 Skill 被连续成功执行 N 次后：
1. 分析执行结果中的 Pattern 使用率
2. 如果新 Pattern 出现频率 > 阈值 → 创建 Pattern 节点
3. 当 Pattern 节点积累到一定数量 → 触发 Skill 版本升级
4. v1 → v2 通过 `evolved_from` 边关联

### 4.3 Pattern Mining

- 从 Content 节点中自动提取写作/回答模式
- 每个 Pattern 节点记录：success_rate, applies_to[], first_seen, last_used
- Pattern 节点应支持交叉引用（一个文章可用多个模式）

---

## 5. 存储格式 (graph.json)

```json
{
  "meta": {
    "type": "knowledge-graph",
    "version": "3.0.0",
    "schema": "4-layer",
    "node_types": ["topic", "concept", "entity", "pattern", "evidence",
                   "skill", "workflow", "prompt", "tool",
                   "session", "task", "run", "result",
                   "content", "report", "summary", "media"],
    "edge_types": ["is_a", "contains", "requires", "uses", "references",
                   "evolved_from", "has_pattern", "implements", "produces",
                   "evidence_for", "depends_on"]
  },
  "nodes": [...],
  "edges": [...]
}
```

---

## 6. 迁移路线

```
Phase 1 (当前)     Phase 2 (下一步)     Phase 3 (未来)
Markdown + JSON    Markdown + JSON      Neo4j / Qdrant
File Graph         Knowledge Graph      Knowledge Graph
Manual export      Auto-evolution       Real-time query
```

**当前在 Phase 1→2 过渡阶段。** 先稳定 Schema，不急于换存储引擎。
