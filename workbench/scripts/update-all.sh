#!/usr/bin/env bash
# update-all.sh
# Master refresh script: fetches worktrees, sprint, and per-ticket details.
# Run this to fully refresh workbench data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/load-config.sh" "${PROJECT_ID:-}"

# WORKBENCH_DATA_DIR is now set by load-config.sh
DATA_DIR="$WORKBENCH_DATA_DIR"
LOG_FILE="$DATA_DIR/update.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$DATA_DIR/jira"
: > "$LOG_FILE"

log "=== Workbench data refresh started ==="

log "--- Step 1/4: Fetching worktrees ---"
bash "$SCRIPT_DIR/fetch-worktrees.sh" 2>&1 | tee -a "$LOG_FILE"

log "--- Step 2/4: Fetching JIRA sprint ---"
bash "$SCRIPT_DIR/fetch-jira.sh" 2>&1 | tee -a "$LOG_FILE"

log "--- Step 3/4: Fetching JIRA ticket details ---"
PROJECT_ID="${PROJECT_ID:-}" bash "$SCRIPT_DIR/fetch-jira-detail.sh" --all 2>&1 | tee -a "$LOG_FILE"

log "--- Step 4/4: Fetching active PRs ---"
PROJECT_ID="${PROJECT_ID:-}" bash "$SCRIPT_DIR/fetch-prs.sh" 2>&1 | tee -a "$LOG_FILE"

# Write a metadata file so the UI can show last-updated time
python3 - "$DATA_DIR" <<'PYEOF'
import json, os, sys
from datetime import datetime, timezone

data_dir = os.path.abspath(sys.argv[1])

sprint_file = os.path.join(data_dir, 'sprint.json')
wt_file     = os.path.join(data_dir, 'worktrees.json')

sprint_stats = {'todo': 0, 'in_progress': 0, 'done': 0}
if os.path.exists(sprint_file):
    d = json.load(open(sprint_file))
    sprint_stats = {k: len(d.get(k, [])) for k in ('todo', 'in_progress', 'done')}

wt_count = 0
if os.path.exists(wt_file):
    wt_count = len(json.load(open(wt_file)))

pr_count = 0
pr_file = os.path.join(data_dir, 'prs.json')
if os.path.exists(pr_file):
    pr_count = len(json.load(open(pr_file)).get('prs', []))

meta = {
    'last_updated': datetime.now(timezone.utc).isoformat(),
    'worktrees':    wt_count,
    'sprint':       sprint_stats,
    'pr_count':     pr_count,
}
with open(os.path.join(data_dir, 'meta.json'), 'w') as f:
    json.dump(meta, f, indent=2)
print(f"meta.json written: {meta}")
PYEOF

log "=== Refresh complete ==="
echo ""
echo "Workbench data at: $DATA_DIR/"
echo "  worktrees.json  last updated: $(date -r "$DATA_DIR/worktrees.json" '+%Y-%m-%d %H:%M:%S')"
echo "  sprint.json     last updated: $(date -r "$DATA_DIR/sprint.json" '+%Y-%m-%d %H:%M:%S')"
