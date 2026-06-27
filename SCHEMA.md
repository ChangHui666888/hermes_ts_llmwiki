# Wiki Schema

## Domain

通用知识库 (General-purpose knowledge base) — AI/ML、编程、技术、个人学习笔记、项目文档等所有领域。

## Conventions

- File names: lowercase, hyphens, no spaces (e.g., `transformer-architecture.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/articles/source-file.md]` at the end of paragraphs whose claims come from a specific source.

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true                        # set when the page has unresolved contradictions
contradictions: [other-page-slug]      # pages this one conflicts with
---
```

### raw/ Frontmatter

```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of the body below frontmatter>
---
```

## Tag Taxonomy

- **AI/ML:** ai, machine-learning, deep-learning, llm, nlp, computer-vision, reinforcement-learning
- **Programming:** programming, python, javascript, typescript, rust, go, frontend, backend, database, devops, security
- **Tools:** tool, editor, cli, git, docker, kubernetes
- **People/Orgs:** person, company, lab, open-source, research-group
- **Meta:** comparison, tutorial, reference, best-practice, timeline, controversy, prediction
- **Domain-specific:** (add new tags here BEFORE using them on pages)

Rule: every tag on a page must appear in this taxonomy. If a new tag is needed, add it here first, then use it.

## Page Thresholds

- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages

One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

## Concept Pages

One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

## Comparison Pages

Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

## Update Policy

When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

## Obsidian Settings

This wiki IS an Obsidian vault:
- Attachment folder: `raw/assets/`
- Enable Wikilinks (already on by default)
- Install Dataview plugin for queries like `TABLE tags FROM "entities"`

## Git Workflow

- Commit message format: `type: concise description`
- Types: `feat:` (new page), `update:` (page update), `ingest:` (new source), `fix:` (correction), `chore:` (maintenance)
- Commit after every meaningful change (ingest, new page, batch update)
- Push periodically (manual)
