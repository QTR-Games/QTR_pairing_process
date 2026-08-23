# QTR skills

Skills are small, task-focused instructions that supplement the repository-wide
agent guide. Each skill lives in its own folder:

```text
.github/skills/
  add-a-test/
    SKILL.md
```

Every `SKILL.md` starts with simple frontmatter:

```markdown
---
name: add-a-test
description: Use when adding or fixing a focused QTR test.
---

# Skill instructions
```

The `name` must match its folder and match
`^[a-z0-9][a-z0-9-]*$`. The description must be trimmed and 10 to 300
characters. The Markdown body must not be empty, and each skill name must be
unique.

Validate skills locally with:

```powershell
python skill_schema_check.py
```

Write skills around a concrete task, decision, or workflow. State when the
skill applies, use repository-specific commands and conventions, and keep the
guidance actionable. Put broad project policy in
[`../copilot-instructions.md`](../copilot-instructions.md), not in every
skill.
