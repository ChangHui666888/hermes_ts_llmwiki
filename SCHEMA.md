---
title: Wiki Schema
created: 2026-06-27
updated: 2026-06-27
---

# Wiki Schema

## Domain
Personal knowledge base — AI/ML concepts, coding notes, and project intelligence.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `transformer-architecture.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy]
sources: [raw/articles/source-name.md]
---
```

## Graph JSON
The file `graph.json` at the wiki root contains a machine-readable graph of all pages
and their `[[wikilinks]]` connections. Updated automatically after each wiki change.

## Tag Taxonomy
- Models: model, architecture, benchmark, training
- People/Orgs: person, company, lab, open-source
- Techniques: optimization, fine-tuning, inference, alignment, data
- Meta: comparison, timeline, controversy, prediction

## Integration
This wiki is backed by Git and viewable in Obsidian. Changes are tracked via Git commits.
