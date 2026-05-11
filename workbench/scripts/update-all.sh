#!/usr/bin/env bash
# update-all.sh
# Master refresh script: fetches worktrees, sprint, and per-ticket details.
# Run this to fully refresh workbench data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../data/update.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$SCRIPT_DIR/../data/jira"
: > "$LOG_FILE"

log "=== Workbench data refresh started ==="

log "--- Step 1/3: Fetching worktrees ---"
bash "$SCRIPT_DIR/fetch-worktrees.sh" 2>&1 | tee -a "$LOG_FILE"

log "--- Step 2/3: Fetching JIRA sprint ---"
bash "$SCRIPT_DIR/fetch-jira.sh" 2>&1 | tee -a "$LOG_FILE"

log "--- Step 3/3: Fetching JIRA ticket details ---"
bash "$SCRIPT_DIR/fetch-jira-detail.sh" --all 2>&1 | tee -a "$LOG_FILE"

# Write a metadata file so the UI can show last-updated time
python3 - "$SCRIPT_DIR/../data" <<'PYEOF'
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

meta = {
    'last_updated': datetime.now(timezone.utc).isoformat(),
    'worktrees':    wt_count,
    'sprint':       sprint_stats,
}
with open(os.path.join(data_dir, 'meta.json'), 'w') as f:
    json.dump(meta, f, indent=2)
print(f"meta.json written: {meta}")
PYEOF

log "=== Refresh complete ==="
echo ""
echo "Workbench data at: $SCRIPT_DIR/../data/"
echo "  worktrees.json  last updated: $(date -r "$SCRIPT_DIR/../data/worktrees.json" '+%Y-%m-%d %H:%M:%S')"
echo "  sprint.json     last updated: $(date -r "$SCRIPT_DIR/../data/sprint.json" '+%Y-%m-%d %H:%M:%S')"
