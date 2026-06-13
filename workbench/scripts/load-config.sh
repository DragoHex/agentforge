#!/usr/bin/env bash
# load-config.sh — Source this file to load workbench/config.json into shell variables.
#
# Usage (in any script under workbench/scripts/):
#   source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"
#
# After sourcing, the following variables are available:
#   JIRA_HOST, GH_HOST, GH_ORG, GH_REPO_DEV, GH_REPO_TEST
#   DSR_HOST, WORKSPACE, TD_DOCS_BASE, WORKBENCH_DIR
#   SERVER_PORT, API_PORT
#   AVI_DEV_REMOTE, AVI_TEST_REMOTE  (derived: git@GH_HOST:GH_ORG/GH_REPO_*.git)

_WB_CFG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config.json"

if [[ ! -f "$_WB_CFG" ]]; then
    echo "ERROR: workbench config not found at $_WB_CFG" >&2
    exit 1
fi

# Parse all values in one python3 call and eval into the current shell.
# Keys with ~/ paths are expanded to absolute paths.
eval "$(python3 - "$_WB_CFG" <<'PYEOF'
import json, os, sys

cfg  = json.load(open(sys.argv[1]))
home = os.path.expanduser('~')

def expand(v):
    return home + v[1:] if isinstance(v, str) and v.startswith('~/') else str(v)

# (shell_var_name, config_key)
mappings = [
    ('JIRA_HOST',    'jira_host'),
    ('GH_HOST',      'gh_host'),
    ('GH_ORG',       'gh_org'),
    ('GH_REPO_DEV',  'gh_repo_dev'),
    ('GH_REPO_TEST', 'gh_repo_test'),
    ('DSR_HOST',     'dsr_host'),
    ('WORKSPACE',    'workspace_dir'),
    ('TD_DOCS_BASE', 'td_docs_base'),
    ('WORKBENCH_DIR','workbench_dir'),
    ('SERVER_PORT',  'server_port'),
    ('API_PORT',     'api_port'),
]
for var, key in mappings:
    print(f"{var}={expand(cfg.get(key, ''))!r}")
PYEOF
)"

# Derive composite Git remote values from component parts
AVI_DEV_REMOTE="git@${GH_HOST}:${GH_ORG}/${GH_REPO_DEV}.git"
AVI_TEST_REMOTE="git@${GH_HOST}:${GH_ORG}/${GH_REPO_TEST}.git"

unset _WB_CFG
