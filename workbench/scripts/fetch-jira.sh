#!/usr/bin/env bash
# fetch-jira.sh
# Fetches active sprint tickets and groups them by status category.

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"

OUT_DIR="$(dirname "$0")/../data"
OUT_FILE="$OUT_DIR/sprint.json"

mkdir -p "$OUT_DIR"

echo "Fetching JIRA sprint tickets..."
TMPFILE=$(mktemp /tmp/sprint_XXXXXX.json)
jira sprint --output json --export "$TMPFILE" >/dev/null 2>&1 || { echo "ERROR: jira sprint failed"; exit 1; }
[[ -s "$TMPFILE" ]] || { echo "ERROR: jira sprint returned empty output"; exit 1; }

python3 - <<PYEOF "$TMPFILE" "$OUT_FILE" "$JIRA_HOST"
import json, sys, re
from datetime import datetime, timezone

raw_file  = sys.argv[1]
out_file  = sys.argv[2]
jira_host = sys.argv[3]

with open(raw_file) as f:
    data = json.load(f)
issues = data.get("issues", [])

todo        = []
in_progress = []
done        = []

STATUS_DONE = {"done", "closed", "resolved", "open"}   # "Open" = won't-re-open; treat as done
STATUS_IP   = {"in progress", "indeterminate"}

for issue in issues:
    fields = issue.get("fields", {})
    status = fields.get("status", {})
    cat_key  = status.get("statusCategory", {}).get("key", "").lower()
    cat_name = status.get("statusCategory", {}).get("name", "").lower()
    status_name = status.get("name", "").lower()

    record = {
        "key":      issue["key"],
        "summary":  fields.get("summary", ""),
        "status":   fields.get("status", {}).get("name", ""),
        "type":     fields.get("issuetype", {}).get("name", ""),
        "priority": fields.get("priority", {}).get("name", ""),
        "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "",
        "updated":  fields.get("updated", ""),
        "created":  fields.get("created", ""),
        "url":      f"{jira_host}/browse/{issue['key']}",
    }

    if cat_key in ("done", "new") and status_name in ("open",):
        # "Open" in JIRA often means filed but not closed — keep separate
        todo.append(record)
    elif cat_key == "new" or status_name == "to do":
        todo.append(record)
    elif cat_key in ("indeterminate",) or "progress" in status_name:
        in_progress.append(record)
    else:
        done.append(record)

output = {
    "generated": datetime.now(timezone.utc).isoformat(),
    "total": len(issues),
    "todo":        todo,
    "in_progress": in_progress,
    "done":        done,
}

with open(out_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Sprint data written: {len(todo)} todo, {len(in_progress)} in-progress, {len(done)} done")
PYEOF
