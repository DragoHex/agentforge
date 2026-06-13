# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A developer workbench dashboard: a single-page HTML UI (`index.html`) backed by a unified Python HTTP server (`server.py`). It aggregates data from Jira, GitHub PRs, and git worktrees for one or more configured projects, with real-time job streaming via SSE.

## Starting the server

```bash
# Start/restart the Python server on port 8000
bash scripts/start-api.sh

# Refresh all data for the current project
bash scripts/update-all.sh

# Run a full data refresh via the API
curl -X POST http://127.0.0.1:8000/api/<project-id>/jobs -H 'Content-Type: application/json' \
  -d '{"action": "update-all"}'
```

The server writes a PID file to `/tmp/workbench-api.pid` and logs to `~/.config/workbench/server.log`.

## Running tests

```bash
# Go server unit tests (legacy — server/main.go is superseded by server.py)
cd server && go test ./...

# Shell script integration test
bash scripts/tests/test-transition-ticket.sh
```

## Configuration

**Legacy (single-project):** Copy `config.sample.json` → `config.json` and fill in values. `config.json` is gitignored.

**Multi-project (current):** Create per-project YAML files at `~/.config/workbench/projects/<project-id>.yaml`. `load-config.sh` accepts an optional project ID argument to load a YAML config instead of the JSON fallback. Project data lands in `~/.config/workbench/data/<project-id>/`.

```yaml
# ~/.config/workbench/projects/my-project.yaml
project_id: my-project
display_name: My Project
color: "#D97757"
enabled: true
workspace:
  dir: ~/workspace/my-project
  data_dir: ~/.config/workbench/data/my-project
integrations:
  jira:
    host: https://jira.example.com
  github:
    host: github.example.com
    org: MY_ORG
    repos:
      dev: dev-repo
      test: test-repo
  dsr:
    host: https://dsr.example.com
ports:
  server_port: 1337
  api_port: 8081
```

## Architecture

### server.py (primary backend)
Single-file Python HTTP server (stdlib only, plus `pyyaml`). Handles:
- **Project registry**: loads all `~/.config/workbench/projects/*.yaml` at startup
- **Job system**: dispatches shell scripts as background threads, streams output via SSE
- **Routes**: `GET /api/projects`, `GET /api/<pid>/config`, `GET /api/<pid>/data/<resource>`, `POST /api/<pid>/jobs`, `GET /api/<pid>/jobs/stream/<job_id>`
- Input validation via compiled regexes for all user-supplied identifiers (Jira IDs, worktree names, project IDs)

### scripts/
Shell scripts invoked by the server's job dispatcher. They all `source load-config.sh` to get environment variables. Key scripts:
- `update-all.sh` — master refresh: runs fetch-worktrees → fetch-jira → fetch-jira-detail → fetch-prs, then writes `meta.json`
- `fetch-jira.sh` — sprint data → `data/sprint.json`
- `fetch-prs.sh` — open PRs → `data/prs.json`
- `fetch-worktrees.sh` — git worktree list → `data/worktrees.json`
- `transition-ticket.sh <ticket-id> <status>` — Jira status transitions; valid statuses: `todo`, `in_progress`, `done`

### index.html
Self-contained single-file UI (no build step, no framework). The sidebar lists projects from `/api/projects`; clicking one loads its data. Uses `EventSource` to stream job logs. Supports dark mode via `localStorage` and a CSS `data-theme` attribute.

### server/ (legacy Go server)
The original `server/main.go` (Go 1.21) is kept for reference and its tests remain valid. It is superseded by `server.py` — do not add features to it.

### data/
Runtime-only JSON files written by the scripts. Not committed. Structure under `~/.config/workbench/data/<project-id>/`: `sprint.json`, `worktrees.json`, `prs.json`, `meta.json`, `jira/<AV-ID>.json`.

## Key constraints
- `server.py` uses only Python stdlib + `pyyaml` — do not add other dependencies.
- All user-supplied route segments are validated against strict regexes before use.
- Jobs time out at 180 seconds; the server never blocks on a subprocess.
- The `workbench/` subdirectory is a stale copy of the repo root — ignore it.
