#!/usr/bin/env bash
# fetch-worktrees.sh
# Scans $WORKSPACE/*/; includes only dirs whose git remote matches avi-dev.

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh" "${PROJECT_ID:-}"

OUT_DIR="$WORKBENCH_DATA_DIR"
OUT_FILE="$OUT_DIR/worktrees.json"
TARGET_REMOTE="$AVI_DEV_REMOTE"

mkdir -p "$OUT_DIR"

echo "[" > "$OUT_FILE.tmp"
first=1

for dir in "$WORKSPACE"/*/; do
    [[ -d "$dir/.git" ]] || [[ -f "$dir/.git" ]] || continue

    remote=$(git -C "$dir" remote get-url origin 2>/dev/null || echo "")
    [[ "$remote" == "$TARGET_REMOTE" ]] || continue

    name=$(basename "$dir")
    branch=$(git -C "$dir" branch --show-current 2>/dev/null || echo "detached")
    last_hash=$(git -C "$dir" log -1 --format="%h" 2>/dev/null || echo "")
    last_msg=$(git -C "$dir" log -1 --format="%s" 2>/dev/null | sed 's/"/\\"/g' || echo "")
    last_author=$(git -C "$dir" log -1 --format="%an" 2>/dev/null | sed 's/"/\\"/g' || echo "")
    last_date=$(git -C "$dir" log -1 --format="%ci" 2>/dev/null || echo "")

    # Check for td-docs directory
    has_td_docs="false"
    td_docs_dir="$dir/.cursor/td-docs"
    [[ -d "$td_docs_dir" ]] && has_td_docs="true"

    # Extract JIRA IDs from branch name (pattern: AV-NNNNN)
    jira_ids=$(echo "$branch" | grep -oE 'AV-[0-9]+' | python3 -c "
import sys, json
ids = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(ids))
" 2>/dev/null || echo "[]")

    # List td-docs files if directory exists
    td_docs_files="[]"
    if [[ -d "$td_docs_dir" ]]; then
        td_docs_files=$(ls "$td_docs_dir"/*.md 2>/dev/null | xargs -I{} basename {} .md | python3 -c "
import sys, json
files = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(files))
" 2>/dev/null || echo "[]")
    fi

    # Merge jira_ids with td-docs file names (may have IDs not in branch)
    all_jira=$(python3 -c "
import json
branch_ids = $jira_ids
td_ids = $td_docs_files
all_ids = list(dict.fromkeys(branch_ids + td_ids))
print(json.dumps(all_ids))
" 2>/dev/null || echo "$jira_ids")

    [[ $first -eq 1 ]] || echo "," >> "$OUT_FILE.tmp"
    first=0

    cat >> "$OUT_FILE.tmp" <<ENTRY
  {
    "name": "$name",
    "path": "$dir",
    "branch": "$branch",
    "last_commit": {
      "hash": "$last_hash",
      "message": "$last_msg",
      "author": "$last_author",
      "date": "$last_date"
    },
    "has_td_docs": $has_td_docs,
    "jira_ids": $all_jira,
    "remote": "$TARGET_REMOTE"
  }
ENTRY
done

echo "]" >> "$OUT_FILE.tmp"

# Validate JSON before replacing
python3 -c "import json,sys; json.load(open('$OUT_FILE.tmp')); print('JSON valid')" && \
    mv "$OUT_FILE.tmp" "$OUT_FILE" || { echo "ERROR: Invalid JSON generated"; cat "$OUT_FILE.tmp"; exit 1; }

echo "Worktrees written to $OUT_FILE"
python3 -c "
import json
data = json.load(open('$OUT_FILE'))
print(f'  Found {len(data)} matching worktree(s):')
for w in data:
    print(f'    - {w[\"name\"]} [{w[\"branch\"]}] jira={w[\"jira_ids\"]}')
"
