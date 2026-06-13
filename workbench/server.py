#!/usr/bin/env python3
"""
Workbench unified server — multi-project, SSE streaming.
Replaces both api.py (port 8081) and server/main.go (port 1337).

Usage:
    python3 server.py [port]          # default: 8000
    PROJECT_ID=avi-network python3 server.py

Endpoints:
    GET  /api/status
    GET  /api/projects
    GET  /api/llm-providers
    GET  /api/<project>/config
    GET  /api/<project>/data/<resource>     (sprint|worktrees|prs|meta|jira/<AV-ID>)
    GET  /api/<project>/jobs
    GET  /api/<project>/jobs/<job_id>
    GET  /api/<project>/jobs/stream/<job_id>  (SSE)
    POST /api/<project>/jobs  {action, params}

Actions: update-all | update-sprint | update-ticket | update-prs | transition-ticket
"""

import glob
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────

_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR  = os.path.join(_THIS_DIR, "scripts")
PROJECTS_DIR = os.path.expanduser("~/.config/workbench/projects")
DEFAULT_PORT = 8000

# ── Input validation ──────────────────────────────────────────────────────────

_RE_JIRA    = re.compile(r'^[A-Z]{2,10}-\d{1,6}$')
_RE_WKTREE  = re.compile(r'^[a-zA-Z0-9_\-\.]{1,64}$')
_RE_PROJECT = re.compile(r'^[a-z0-9\-]{1,32}$')
_RE_JOB_ID  = re.compile(r'^[a-z0-9\-]{4,64}$')
_RE_COLOR   = re.compile(r'^#[0-9A-Fa-f]{6}$')
_RE_DISPLAY = re.compile(r'^[^\x00-\x1f]{1,64}$')
_STATUSES   = frozenset(('todo', 'in_progress', 'done'))

# ── Project config helpers ─────────────────────────────────────────────────────

def _build_yaml_dict(body: dict) -> dict:
    """Reconstruct nested YAML structure from a flat API request body."""
    return {
        "project_id":   body["project_id"],
        "display_name": body["display_name"],
        "color":        body.get("color", "#888888"),
        "enabled":      True,
        "workspace": {
            "dir":      body.get("workspace_dir", ""),
            "data_dir": body.get("data_dir", ""),
        },
        "integrations": {
            "jira": {
                "host":        body.get("jira_host", ""),
                "project_key": body.get("jira_project_key", ""),
            },
            "github": {
                "host": body.get("gh_host", ""),
                "org":  body.get("gh_org", ""),
                "repos": {
                    "dev":  body.get("repo_dev", ""),
                    "test": body.get("repo_test", ""),
                },
            },
            "dsr": {"host": body.get("dsr_host", "")},
        },
        "llm": {
            "provider": body.get("llm_provider", ""),
            "model":    body.get("llm_model", ""),
        },
        "ports": {
            "api_port":    int(body["api_port"])    if body.get("api_port")    else 8081,
            "server_port": int(body["server_port"]) if body.get("server_port") else 1337,
        },
    }


def _validate_project_body(body: dict):
    """Validate a flat project body. Returns (cleaned_dict, None) or (None, error_str)."""
    pid     = body.get("project_id", "")
    display = body.get("display_name", "")
    color   = body.get("color", "#888888")
    errors  = []
    if not _RE_PROJECT.match(pid):
        errors.append("project_id must match [a-z0-9-]{1,32}")
    if not display or not _RE_DISPLAY.match(display):
        errors.append("display_name required, max 64 printable chars")
    if not _RE_COLOR.match(color):
        errors.append("color must be a hex #RRGGBB value")
    if errors:
        return None, "; ".join(errors)
    return _build_yaml_dict(body), None


# ── LLM provider detection ─────────────────────────────────────────────────────

def _detect_llm_providers() -> list:
    """Detect available LLM providers on this system."""
    import shutil, socket as _socket

    providers = []

    # Anthropic — Claude Code CLI or API key / config dir
    if shutil.which("claude") or os.environ.get("ANTHROPIC_API_KEY") or \
            os.path.isdir(os.path.expanduser("~/.config/anthropic")):
        label = "Anthropic (Claude Code)" if shutil.which("claude") else "Anthropic"
        providers.append({
            "id":     "anthropic",
            "name":   label,
            "models": [
                "claude-sonnet-4-6",
                "claude-opus-4-8",
                "claude-haiku-4-5-20251001",
                "claude-fable-5",
            ],
        })

    # Cursor Agent — `agent` CLI
    if shutil.which("agent"):
        cursor_models = []
        try:
            result = subprocess.run(
                ["agent", "models"], capture_output=True, text=True, timeout=8
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    # Each line: "<model-id> - <Human Name>" or blank/header
                    if " - " in line:
                        model_id = line.split(" - ", 1)[0].strip()
                        if model_id:
                            cursor_models.append(model_id)
        except Exception:
            pass
        providers.append({
            "id":     "cursor",
            "name":   "Cursor Agent",
            "models": cursor_models,
        })

    # OpenAI — API key or CLI
    if os.environ.get("OPENAI_API_KEY") or shutil.which("openai"):
        providers.append({
            "id":     "openai",
            "name":   "OpenAI",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini", "o3-mini"],
        })

    # Google — API key or gemini CLI
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or shutil.which("gemini"):
        providers.append({
            "id":     "google",
            "name":   "Google",
            "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
        })

    # Ollama — CLI or port 11434 open
    ollama_models = []
    if shutil.which("ollama"):
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines()[1:]:  # skip header
                    parts = line.split()
                    if parts:
                        ollama_models.append(parts[0])
        except Exception:
            pass
    if not ollama_models:
        try:
            s = _socket.create_connection(("127.0.0.1", 11434), timeout=1)
            s.close()
            ollama_models = []  # running but list failed; still surface the provider
        except Exception:
            pass
    if shutil.which("ollama") or ollama_models:
        providers.append({
            "id":     "ollama",
            "name":   "Ollama (local)",
            "models": ollama_models,
        })

    # AWS Bedrock — aws CLI + credentials
    if shutil.which("aws") and (
        os.path.exists(os.path.expanduser("~/.aws/credentials")) or
        os.environ.get("AWS_ACCESS_KEY_ID")
    ):
        providers.append({
            "id":     "bedrock",
            "name":   "AWS Bedrock",
            "models": [
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "anthropic.claude-3-opus-20240229-v1:0",
                "amazon.titan-text-express-v1",
            ],
        })

    # LM Studio — port 1234
    try:
        s = _socket.create_connection(("127.0.0.1", 1234), timeout=1)
        s.close()
        providers.append({
            "id":     "lm-studio",
            "name":   "LM Studio (local)",
            "models": [],  # dynamic; user must enter model name
        })
    except Exception:
        pass

    return providers


# ── Project registry ──────────────────────────────────────────────────────────

_registry_lock = threading.Lock()
_registry: dict = {}   # project_id -> parsed config dict


def _load_project_file(path: str) -> dict | None:
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict) or not cfg.get("enabled", True):
            return None
        pid = cfg.get("project_id") or os.path.splitext(os.path.basename(path))[0]
        cfg["project_id"] = pid
        ws = cfg.get("workspace") or {}
        cfg["_data_dir"] = os.path.expanduser(
            ws.get("data_dir") or f"~/.config/workbench/data/{pid}"
        )
        return cfg
    except Exception as e:
        print(f"[registry] Error loading {path}: {e}", file=sys.stderr)
        return None


def reload_registry():
    projects = {}
    for path in sorted(glob.glob(os.path.join(PROJECTS_DIR, "*.yaml"))):
        cfg = _load_project_file(path)
        if cfg:
            projects[cfg["project_id"]] = cfg
    with _registry_lock:
        _registry.clear()
        _registry.update(projects)
    print(f"[registry] {len(projects)} project(s): {list(projects)}")


def get_project(pid: str) -> dict | None:
    with _registry_lock:
        return _registry.get(pid)


def list_projects() -> list:
    with _registry_lock:
        return [
            {
                "id":           p["project_id"],
                "display_name": p.get("display_name", p["project_id"]),
                "color":        p.get("color", "#888888"),
            }
            for p in _registry.values()
            if p.get("enabled", True)
        ]


# ── Job store ─────────────────────────────────────────────────────────────────

_jobs_lock  = threading.Lock()
_jobs: dict = {}       # job_id -> job dict
_job_qs: dict = {}     # job_id -> queue.Queue (None sentinel = done)


def _make_env(project_id: str) -> dict:
    env = dict(os.environ)
    env["PROJECT_ID"] = project_id
    return env


def _run_job(job_id: str, cmd: list, env: dict) -> None:
    q = _job_qs.get(job_id)
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"

    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, close_fds=True
        )
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            if q:
                q.put(("log", line))
        try:
            proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise TimeoutError("job timed out after 180s")

        status = "done" if proc.returncode == 0 else "failed"
        with _jobs_lock:
            _jobs[job_id].update({
                "status":      status,
                "returncode":  proc.returncode,
                "stdout":      "\n".join(lines),
                "finished_at": time.time(),
            })
        if q:
            q.put(("status", {"status": status, "returncode": proc.returncode}))

    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id].update({
                "status":      "error",
                "stderr":      str(exc),
                "finished_at": time.time(),
            })
        if q:
            q.put(("status", {"status": "error", "returncode": -1}))
    finally:
        if q:
            q.put(None)   # sentinel: stream finished


def _dispatch(job_id: str, cmd: list, project_id: str, action: str) -> None:
    job = {
        "job_id":      job_id,
        "project_id":  project_id,
        "action":      action,
        "status":      "queued",
        "cmd":         " ".join(cmd),
        "started_at":  time.time(),
        "finished_at": None,
        "returncode":  None,
        "stdout":      "",
        "stderr":      "",
    }
    q = queue.Queue()
    with _jobs_lock:
        _jobs[job_id]  = job
        _job_qs[job_id] = q
    threading.Thread(
        target=_run_job, args=(job_id, cmd, _make_env(project_id)), daemon=True
    ).start()


def _build_command(project_id: str, action: str, params: dict, qparams: dict):
    ts = int(time.time())

    def p(k):
        return (params.get(k) or qparams.get(k, [""])[0]).strip()

    match action:
        case "update-all":
            return f"all-{project_id}-{ts}", ["bash", f"{SCRIPTS_DIR}/update-all.sh"]
        case "update-sprint":
            return f"sprint-{project_id}-{ts}", ["bash", f"{SCRIPTS_DIR}/fetch-jira.sh"]
        case "update-prs":
            return f"prs-{project_id}-{ts}", ["bash", f"{SCRIPTS_DIR}/fetch-prs.sh"]
        case "update-ticket":
            jira_id  = p("jira_id")
            worktree = p("worktree")
            if not jira_id or not _RE_JIRA.match(jira_id):
                return None, "invalid or missing jira_id"
            if worktree and not _RE_WKTREE.match(worktree):
                return None, "invalid worktree name"
            cmd = ["bash", f"{SCRIPTS_DIR}/fetch-jira-detail.sh", jira_id]
            if worktree:
                cmd += ["--worktree", worktree]
            return f"ticket-{jira_id}-{ts}", cmd
        case "transition-ticket":
            ticket_id = p("ticket_id")
            target    = p("target_status")
            if not ticket_id or not _RE_JIRA.match(ticket_id):
                return None, "invalid or missing ticket_id"
            if target not in _STATUSES:
                return None, f"target_status must be one of: {sorted(_STATUSES)}"
            return (f"trans-{ticket_id}-{ts}",
                    ["bash", f"{SCRIPTS_DIR}/transition-ticket.sh", ticket_id, target])
        case _:
            return None, f"unknown action: {action!r}"


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-WB-Project")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, code: int, data) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, job_id: str) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def write(data: str):
            try:
                self.wfile.write(data.encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                return False
            return True

        q = _job_qs.get(job_id)
        if q is None:
            # Already done — replay from stored stdout
            with _jobs_lock:
                job = _jobs.get(job_id)
            if job:
                for line in (job.get("stdout") or "").split("\n"):
                    write(f"event: log\ndata: {json.dumps({'line': line})}\n\n")
                write(f"event: status\ndata: {json.dumps({'status': job['status'], 'returncode': job.get('returncode')})}\n\n")
            return

        # Stream live
        while True:
            try:
                item = q.get(timeout=30)
            except queue.Empty:
                if not write(": keepalive\n\n"):
                    break
                continue
            if item is None:
                break
            event, payload = item
            if event == "log":
                if not write(f"event: log\ndata: {json.dumps({'line': payload})}\n\n"):
                    break
            elif event == "status":
                write(f"event: status\ndata: {json.dumps(payload)}\n\n")
                break

    def _route_get(self, path: str, params: dict) -> None:
        # Serve static files from the workbench directory
        if path in ("", "/", "/index.html"):
            fpath = os.path.join(_THIS_DIR, "index.html")
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if path == "/jira-detail.html":
            fpath = os.path.join(_THIS_DIR, "jira-detail.html")
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        # Global routes
        if path in ("/api/status", "/api"):
            return self._json(200, {"status": "ok", "projects": len(_registry)})

        if path == "/api/projects":
            return self._json(200, list_projects())

        if path == "/api/llm-providers":
            return self._json(200, _detect_llm_providers())

        # Project-scoped
        m = re.match(r'^/api/([a-z0-9\-]{1,32})(/.+)$', path)
        if not m:
            return self._json(404, {"error": "not found"})

        pid, sub = m.group(1), m.group(2).rstrip("/")

        if not _RE_PROJECT.match(pid):
            return self._json(400, {"error": "invalid project_id"})
        project = get_project(pid)
        if not project:
            return self._json(404, {"error": f"project {pid!r} not found"})

        data_dir = project["_data_dir"]

        # /data/<resource>
        dm = re.match(r'^/data/(.+)$', sub)
        if dm:
            resource = dm.group(1)
            allowed  = {"sprint", "worktrees", "prs", "meta"}
            ticket_m = re.match(r'^jira/([A-Z]{2,10}-\d{1,6})$', resource)
            if resource in allowed:
                fpath = os.path.join(data_dir, f"{resource}.json")
            elif ticket_m:
                fpath = os.path.join(data_dir, "jira", f"{ticket_m.group(1)}.json")
            else:
                return self._json(400, {"error": f"unknown resource: {resource!r}"})
            if os.path.exists(fpath):
                with open(fpath) as f:
                    return self._json(200, json.load(f))
            return self._json(404, {"error": f"{resource} not found — run update-all first"})

        # /config
        if sub == "/config":
            integ  = project.get("integrations") or {}
            github = integ.get("github") or {}
            return self._json(200, {
                "project_id":       project["project_id"],
                "display_name":     project.get("display_name", ""),
                "color":            project.get("color", ""),
                "jira_host":        (integ.get("jira") or {}).get("host", ""),
                "jira_project_key": (integ.get("jira") or {}).get("project_key", ""),
                "gh_host":          github.get("host", ""),
                "gh_org":           github.get("org", ""),
                "repos":            github.get("repos") or {},
                "repo_dev":         (github.get("repos") or {}).get("dev", ""),
                "repo_test":        (github.get("repos") or {}).get("test", ""),
                "dsr_host":         (integ.get("dsr") or {}).get("host", ""),
                "workspace_dir":    project.get("workspace", {}).get("dir", ""),
                "data_dir":         project.get("workspace", {}).get("data_dir", ""),
                "llm_provider":     (project.get("llm") or {}).get("provider", ""),
                "llm_model":        (project.get("llm") or {}).get("model", ""),
                "api_port":         (project.get("ports") or {}).get("api_port", 8081),
                "server_port":      (project.get("ports") or {}).get("server_port", 1337),
            })

        # /worktrees (legacy compat)
        if sub == "/worktrees":
            wt = os.path.join(data_dir, "worktrees.json")
            if os.path.exists(wt):
                with open(wt) as f:
                    return self._json(200, json.load(f))
            return self._json(404, {"error": "worktrees not found"})

        # /jobs
        if sub == "/jobs":
            limit = int(params.get("limit", ["20"])[0])
            with _jobs_lock:
                result = [
                    {k: v for k, v in j.items() if k != "stdout"}
                    for j in _jobs.values()
                    if j.get("project_id") == pid
                ]
            return self._json(200, result[-limit:])

        # /jobs/<job_id>
        jm = re.match(r'^/jobs/([a-z0-9\-]{4,64})$', sub)
        if jm:
            with _jobs_lock:
                job = _jobs.get(jm.group(1))
            if job:
                return self._json(200, job)
            return self._json(404, {"error": "job not found"})

        # /jobs/stream/<job_id>
        sm = re.match(r'^/jobs/stream/([a-z0-9\-]{4,64})$', sub)
        if sm:
            with _jobs_lock:
                job = _jobs.get(sm.group(1))
            if not job:
                return self._json(404, {"error": "job not found"})
            return self._sse(sm.group(1))

        return self._json(404, {"error": "not found"})

    def _route_put(self, path: str, params: dict) -> None:
        m = re.match(r'^/api/([a-z0-9\-]{1,32})/config$', path)
        if not m:
            return self._json(404, {"error": "not found"})
        pid   = m.group(1)
        fpath = os.path.join(PROJECTS_DIR, f"{pid}.yaml")
        if not os.path.exists(fpath):
            return self._json(404, {"error": f"project {pid!r} not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid JSON body"})
        body["project_id"] = pid  # lock pid to URL
        cleaned, err = _validate_project_body(body)
        if err:
            return self._json(400, {"error": err})
        with open(fpath, "w") as f:
            yaml.dump(cleaned, f, default_flow_style=False, allow_unicode=True)
        reload_registry()
        return self._json(200, {"project_id": pid})

    def _route_delete(self, path: str, params: dict) -> None:
        m = re.match(r'^/api/([a-z0-9\-]{1,32})$', path)
        if not m:
            return self._json(404, {"error": "not found"})
        pid   = m.group(1)
        fpath = os.path.join(PROJECTS_DIR, f"{pid}.yaml")
        if not os.path.exists(fpath):
            return self._json(404, {"error": f"project {pid!r} not found"})
        os.remove(fpath)
        reload_registry()
        return self._json(200, {"deleted": pid})

    def _route_post(self, path: str, params: dict) -> None:
        # Create a new project
        if path == "/api/projects":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length)) if length else {}
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid JSON body"})
            cleaned, err = _validate_project_body(body)
            if err:
                return self._json(400, {"error": err})
            pid   = cleaned["project_id"]
            fpath = os.path.join(PROJECTS_DIR, f"{pid}.yaml")
            if os.path.exists(fpath):
                return self._json(409, {"error": f"project {pid!r} already exists"})
            os.makedirs(PROJECTS_DIR, exist_ok=True)
            with open(fpath, "w") as f:
                yaml.dump(cleaned, f, default_flow_style=False, allow_unicode=True)
            reload_registry()
            return self._json(201, {"project_id": pid})

        m = re.match(r'^/api/([a-z0-9\-]{1,32})/jobs$', path)
        if not m:
            return self._json(404, {"error": "not found"})

        pid = m.group(1)
        if not _RE_PROJECT.match(pid):
            return self._json(400, {"error": "invalid project_id"})
        project = get_project(pid)
        if not project:
            return self._json(404, {"error": f"project {pid!r} not found"})

        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}
        action = (body.get("action") or "").strip()
        bparams = body.get("params") or {}

        job_id, cmd_or_err = _build_command(pid, action, bparams, params)
        if job_id is None:
            return self._json(400, {"error": cmd_or_err})

        _dispatch(job_id, cmd_or_err, pid, action)
        return self._json(202, {"job_id": job_id, "status": "queued"})

    def do_GET(self):
        parsed = urlparse(self.path)
        self._route_get(parsed.path.rstrip("/"), parse_qs(parsed.query))

    def do_POST(self):
        parsed = urlparse(self.path)
        self._route_post(parsed.path.rstrip("/"), parse_qs(parsed.query))

    def do_PUT(self):
        parsed = urlparse(self.path)
        self._route_put(parsed.path.rstrip("/"), parse_qs(parsed.query))

    def do_DELETE(self):
        parsed = urlparse(self.path)
        self._route_delete(parsed.path.rstrip("/"), parse_qs(parsed.query))

    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {fmt % args}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    if not os.path.isdir(PROJECTS_DIR):
        print(f"[warn] projects dir not found: {PROJECTS_DIR}", file=sys.stderr)
    reload_registry()
    srv = ThreadedHTTPServer(("127.0.0.1", port), Handler)
    print(f"Workbench server → http://127.0.0.1:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
