# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**agentforge** is a personal collection of Claude Code skills and a developer workbench dashboard. It has two distinct subsystems:

1. **Skills** (`html-*` directories) — Claude Code skill definitions for generating single-file HTML artifacts
2. **Workbench** (`workbench/`) — A live developer dashboard (Jira, GitHub PRs, git worktrees) with a Python backend

---

## Skills (`html-*` directories)

Each skill directory contains a `SKILL.md` (the skill definition read by the agent) and a `templates/` folder with HTML reference files. Skills output **single-file, self-contained HTML** — no build step, no external dependencies, all CSS/JS inline.

### Available skills

| Directory | Purpose |
|-----------|---------|
| `html-document` | Structured documents: comparisons, plans, slide decks, status reports, post-mortems, explainers |
| `html-diagram` | SVG illustrations: flowcharts, architecture maps, figure sheets |
| `html-editor` | Interactive editors: kanban triage boards, config editors, prompt tuners |
| `html-code-review` | Code review artifacts: annotated diffs, PR writeups, module maps |
| `html-design` | Design artifacts: design system references, component variant matrices, prototypes |

### Shared design system

All skills import `assets/palette.css`. When generating HTML for any skill, this palette **must** be applied:

- **Colors**: `--clay` (#D97757) = focus/emphasis, `--olive` (#788C5D) = success/done, `--ivory` (#FAF9F5) = page background, `--oat` (#E3DACC) = card backgrounds
- **Typography**: `--font-sans` (system-ui stack), `--font-mono` (ui-monospace stack). Use `var(--text-body)`, `var(--text-h1)`, etc.
- **Spacing**: `--sp-1` (4px) through `--sp-8` (64px)
- **Components**: `.card`, `.btn`, `.btn-primary`, `.btn-clay`, `.btn-olive`, `.badge`, `.badge-clay`, etc.

For standalone output HTML, inline the palette CSS (it won't be served from disk).

### Skill constraints (apply to all skills)
- Single file only — all CSS and JS inline
- System fonts only (no Google Fonts or CDN)
- No network calls; all SVG inline
- Always read the relevant `templates/*.html` before generating output

---

## Workbench (`workbench/`)

See `workbench/CLAUDE.md` for full details. Summary:

### Starting the server
```bash
cd workbench
bash scripts/start-api.sh          # Start Python server on port 8000
bash scripts/update-all.sh         # Refresh all data for current project
```

### Architecture
- **`server.py`** — single-file Python HTTP server (stdlib + `pyyaml` only). Handles project registry, a background job system, and SSE streaming. Do not add other dependencies.
- **`index.html`** — self-contained SPA (no framework, no build step). Reads `/api/projects` for the sidebar, streams job logs via `EventSource`.
- **`scripts/`** — shell scripts invoked by the job dispatcher; all `source load-config.sh`.
- **Config**: per-project YAML files at `~/.config/workbench/projects/<project-id>.yaml`; data lands in `~/.config/workbench/data/<project-id>/`.

### Tests
```bash
# Shell script integration test
bash workbench/scripts/tests/test-transition-ticket.sh

# Legacy Go server tests (server/ directory, superseded by server.py)
cd workbench/server && go test ./...
```

### Key constraints
- `server.py` stdlib + `pyyaml` only — no additional deps
- All user-supplied route segments validated against strict regexes
- Jobs time out at 180 s; server never blocks on subprocess
- Do not add features to the legacy Go server (`server/main.go`)
