#!/usr/bin/env bash
# load-config.sh — Source this file to load workbench config into shell variables.
#
# Usage (in any script under workbench/scripts/):
#   source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"           # legacy JSON
#   source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh" avi-network  # YAML project
#
# After sourcing, the following variables are available:
#   JIRA_HOST, GH_HOST, GH_ORG, GH_REPO_DEV, GH_REPO_TEST
#   DSR_HOST, WORKSPACE, TD_DOCS_BASE, WORKBENCH_DIR, WORKBENCH_DATA_DIR
#   SERVER_PORT, API_PORT
#   AVI_DEV_REMOTE, AVI_TEST_REMOTE  (derived: git@GH_HOST:GH_ORG/GH_REPO_*.git)

_PROJECT_SLUG="${1:-}"

if [[ -n "$_PROJECT_SLUG" ]]; then
    _WB_CFG="$HOME/.config/workbench/projects/${_PROJECT_SLUG}.yaml"
    _CFG_FORMAT="yaml"
else
    _WB_CFG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config.json"
    _CFG_FORMAT="json"
fi

if [[ ! -f "$_WB_CFG" ]]; then
    echo "ERROR: workbench config not found at $_WB_CFG" >&2
    exit 1
fi

# Parse all values in one python3 call and eval into the current shell.
# Keys with ~/ paths are expanded to absolute paths.
eval "$(python3 - "$_WB_CFG" "$_CFG_FORMAT" <<'PYEOF'
import os, sys

cfg_file   = sys.argv[1]
cfg_format = sys.argv[2]
home       = os.path.expanduser('~')

def expand(v):
    if not isinstance(v, str): return str(v)
    return home + v[1:] if v.startswith('~/') else v

if cfg_format == "yaml":
    # Minimal YAML parser for our known schema (avoids pyyaml dependency).
    # Handles key: value, nested keys, and quoted strings.
    try:
        import yaml
        with open(cfg_file) as f:
            doc = yaml.safe_load(f)
    except ImportError:
        # Fallback: parse with regex for the flat fields we need
        import re
        doc = {}
        with open(cfg_file) as f:
            text = f.read()
        # Extract top-level and nested scalar values
        for m in re.finditer(r'^(\s*)(\w+):\s+"?([^"\n]+?)"?\s*$', text, re.MULTILINE):
            indent, key, val = m.group(1), m.group(2), m.group(3).strip()
            doc[key] = val

    ws      = doc.get("workspace", {})
    integ   = doc.get("integrations", {})
    jira    = integ.get("jira", {})
    github  = integ.get("github", {})
    dsr     = integ.get("dsr", {}) or {}
    repos   = github.get("repos", {})
    ports   = doc.get("ports", {})

    mappings_vals = {
        'JIRA_HOST':           expand(jira.get("host", "")),
        'GH_HOST':             expand(github.get("host", "")),
        'GH_ORG':              expand(github.get("org", "")),
        'GH_REPO_DEV':         expand(repos.get("dev", "")),
        'GH_REPO_TEST':        expand(repos.get("test", "")),
        'DSR_HOST':            expand(dsr.get("host", "")),
        'WORKSPACE':           expand(ws.get("dir", "")),
        'TD_DOCS_BASE':        expand(ws.get("td_docs_base", "")),
        'WORKBENCH_DIR':       expand(ws.get("data_dir") or f"~/.config/workbench/data/{doc.get('project_id', '')}"),
        'WORKBENCH_DATA_DIR':  expand(ws.get("data_dir") or f"~/.config/workbench/data/{doc.get('project_id', '')}"),
        'SERVER_PORT':         str(ports.get("server_port", 1337)),
        'API_PORT':            str(ports.get("api_port", 8081)),
    }
else:
    import json
    cfg = json.load(open(cfg_file))
    legacy_data_dir = expand(cfg.get("workbench_dir", "")) + "/data"
    mappings_vals = {
        'JIRA_HOST':           expand(cfg.get("jira_host", "")),
        'GH_HOST':             expand(cfg.get("gh_host", "")),
        'GH_ORG':              expand(cfg.get("gh_org", "")),
        'GH_REPO_DEV':         expand(cfg.get("gh_repo_dev", "")),
        'GH_REPO_TEST':        expand(cfg.get("gh_repo_test", "")),
        'DSR_HOST':            expand(cfg.get("dsr_host", "")),
        'WORKSPACE':           expand(cfg.get("workspace_dir", "")),
        'TD_DOCS_BASE':        expand(cfg.get("td_docs_base", "")),
        'WORKBENCH_DIR':       expand(cfg.get("workbench_dir", "")),
        'WORKBENCH_DATA_DIR':  legacy_data_dir,
        'SERVER_PORT':         str(cfg.get("server_port", 1337)),
        'API_PORT':            str(cfg.get("api_port", 8081)),
    }

for var, val in mappings_vals.items():
    print(f"{var}={val!r}")
PYEOF
)"

# Derive composite Git remote values from component parts
AVI_DEV_REMOTE="git@${GH_HOST}:${GH_ORG}/${GH_REPO_DEV}.git"
AVI_TEST_REMOTE="git@${GH_HOST}:${GH_ORG}/${GH_REPO_TEST}.git"

unset _WB_CFG _CFG_FORMAT _PROJECT_SLUG
