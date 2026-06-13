#!/usr/bin/env python3
"""
Workbench API server.
Provides HTTP endpoints to trigger data-refresh shell scripts.

Configuration is read from config.json in the same directory as this script.

Usage:
    python3 /var/www/html/workbench/api.py
    # or via start-api.sh

Endpoints:
    GET  /api/status                          — health check
    GET  /api/worktrees                       — list available worktrees
    POST /api/update?jira_id=AV-ID            — refresh one ticket (auto-detect worktree)
    POST /api/update?jira_id=AV-ID&worktree=X — refresh with specific worktree
    POST /api/update-sprint                   — refresh sprint.json only
    POST /api/update-all                      — full refresh (all scripts)
"""

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_cfg      = json.load(open(_cfg_path))

WORKBENCH_DIR = os.path.expanduser(_cfg["workbench_dir"])
SCRIPTS_DIR   = os.path.join(WORKBENCH_DIR, "scripts")
DATA_DIR      = os.path.join(WORKBENCH_DIR, "data")
PORT          = int(_cfg["api_port"])

# ── In-progress job tracking ──────────────────────────────────────────────────
_jobs_lock = threading.Lock()
_jobs: dict = {}   # job_id -> {status, stdout, stderr, started_at, finished_at}

def _run_job(job_id: str, cmd: list[str]) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=180, cwd=WORKBENCH_DIR
        )
        with _jobs_lock:
            _jobs[job_id].update({
                "status":      "done" if result.returncode == 0 else "failed",
                "stdout":      result.stdout,
                "stderr":      result.stderr,
                "returncode":  result.returncode,
                "finished_at": time.time(),
            })
    except subprocess.TimeoutExpired:
        with _jobs_lock:
            _jobs[job_id].update({"status": "timeout", "finished_at": time.time()})
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id].update({"status": "error", "stderr": str(e), "finished_at": time.time()})


class Handler(BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/status":
            self._json(200, {"status": "ok", "port": PORT})

        elif parsed.path == "/api/worktrees":
            wt_file = os.path.join(DATA_DIR, "worktrees.json")
            if os.path.exists(wt_file):
                with open(wt_file) as f:
                    self._json(200, json.load(f))
            else:
                self._json(404, {"error": "worktrees.json not found — run update-all.sh first"})

        elif parsed.path == "/api/job":
            job_id = params.get("id", [""])[0]
            with _jobs_lock:
                job = _jobs.get(job_id)
            if job:
                self._json(200, job)
            else:
                self._json(404, {"error": f"job {job_id!r} not found"})

        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/update":
            jira_id  = params.get("jira_id",  [""])[0].strip()
            worktree = params.get("worktree",  [""])[0].strip()
            if not jira_id:
                self._json(400, {"error": "jira_id query param required"})
                return
            cmd = ["bash", os.path.join(SCRIPTS_DIR, "fetch-jira-detail.sh"), jira_id]
            if worktree:
                cmd += ["--worktree", worktree]
            job_id = f"update-{jira_id}-{int(time.time())}"
            self._start_job(job_id, cmd, {"jira_id": jira_id, "worktree": worktree})

        elif parsed.path == "/api/update-sprint":
            cmd    = ["bash", os.path.join(SCRIPTS_DIR, "fetch-jira.sh")]
            job_id = f"sprint-{int(time.time())}"
            self._start_job(job_id, cmd, {})

        elif parsed.path == "/api/update-all":
            cmd    = ["bash", os.path.join(SCRIPTS_DIR, "update-all.sh")]
            job_id = f"all-{int(time.time())}"
            self._start_job(job_id, cmd, {})

        else:
            self._json(404, {"error": "not found"})

    def _start_job(self, job_id: str, cmd: list[str], meta: dict) -> None:
        with _jobs_lock:
            _jobs[job_id] = {
                "job_id":     job_id,
                "status":     "queued",
                "cmd":        " ".join(cmd),
                "started_at": time.time(),
                "finished_at": None,
                "stdout":     "",
                "stderr":     "",
                **meta,
            }
        t = threading.Thread(target=_run_job, args=(job_id, cmd), daemon=True)
        t.start()
        self._json(202, {"job_id": job_id, "status": "queued", "cmd": " ".join(cmd)})

    def log_message(self, fmt, *args):
        print(f"[API {time.strftime('%H:%M:%S')}] {self.address_string()} — {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Workbench API server → http://127.0.0.1:{PORT}")
    print(f"  GET  /api/status")
    print(f"  GET  /api/worktrees")
    print(f"  POST /api/update?jira_id=AV-ID[&worktree=name]")
    print(f"  POST /api/update-sprint")
    print(f"  POST /api/update-all")
    print(f"  GET  /api/job?id=<job_id>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
