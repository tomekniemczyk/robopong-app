## Task Management

Standards for task tracking, project map maintenance, and documentation of findings in the AcePad project.

### GitHub Issues for Tasks

When user says "dodaj zadanie", "nowe zadanie", "task:", "TODO:" -- ALWAYS create a GitHub Issue.

```bash
gh issue create --repo tomekniemczyk/robopong-app \
  --title "..." --body "..." --label "backlog,PRIORITY"
```

Priorities (labels): `wysoki`, `sredni` (default), `niski`. New tasks always get the `backlog` label.

### Project Map Maintenance

When adding or removing source files, modules, or directories -- update the "Mapa projektu" section in CLAUDE.md. When a key file's line count changes by more than 20%, update the parenthesized number. Do not update the map for minor internal changes within existing files.

### Document Protocol and UX Findings

Every finding about protocol values, UX behavior, or hardware behavior must be saved to both memory files and CLAUDE.md. Live test findings take priority over reverse engineering documentation.
