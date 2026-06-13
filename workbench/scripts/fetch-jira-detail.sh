#!/usr/bin/env bash
# fetch-jira-detail.sh <AV-ID> [--worktree <name>] | --all
# Fetches per-ticket detail: td-docs content, GitHub PR status, DSR/DFR status.
#
# --worktree <name>  Override auto-detection; use this worktree name from ~/workspace/

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../data"
TARGET_REMOTE="$AVI_DEV_REMOTE"
GH_TOKEN=$(grep -A5 "${GH_HOST}:" "$HOME/.config/gh/hosts.yml" 2>/dev/null \
    | grep oauth_token | head -1 | awk '{print $2}' || echo "")

process_ticket() {
    local JIRA_ID="$1"
    local FORCE_WORKTREE="${2:-}"   # optional: worktree name override
    local OUT_FILE="$DATA_DIR/jira/${JIRA_ID}.json"
    mkdir -p "$DATA_DIR/jira"

    echo "Processing $JIRA_ID${FORCE_WORKTREE:+ (worktree: $FORCE_WORKTREE)}..."

    # ── Temp dir for intermediate data ────────────────────────────────────────
    TMPDIR_TICKET=$(mktemp -d /tmp/workbench_XXXXXX)
    trap 'rm -rf "$TMPDIR_TICKET"' RETURN

    # ── 1. Find assigned worktree ──────────────────────────────────────────────
    WORKTREE_PATH=""
    WORKTREE_NAME=""
    BRANCH=""

    if [[ -n "$FORCE_WORKTREE" ]]; then
        # Use explicitly chosen worktree
        forced_dir="$WORKSPACE/$FORCE_WORKTREE"
        if [[ -d "$forced_dir" ]]; then
            remote=$(git -C "$forced_dir" remote get-url origin 2>/dev/null || echo "")
            if [[ "$remote" == "$TARGET_REMOTE" ]]; then
                WORKTREE_PATH="$forced_dir/"
                WORKTREE_NAME="$FORCE_WORKTREE"
                BRANCH=$(git -C "$forced_dir" branch --show-current 2>/dev/null || echo "")
            else
                echo "  WARNING: $FORCE_WORKTREE remote does not match avi-dev — using anyway"
                WORKTREE_PATH="$forced_dir/"
                WORKTREE_NAME="$FORCE_WORKTREE"
                BRANCH=$(git -C "$forced_dir" branch --show-current 2>/dev/null || echo "")
            fi
        else
            echo "  ERROR: Worktree $FORCE_WORKTREE not found at $forced_dir"
        fi
    else
        # Auto-detect: match by branch name or td-docs file presence
        for dir in "$WORKSPACE"/*/; do
            [[ -d "$dir/.git" ]] || [[ -f "$dir/.git" ]] || continue
            remote=$(git -C "$dir" remote get-url origin 2>/dev/null || echo "")
            [[ "$remote" == "$TARGET_REMOTE" ]] || continue
            b=$(git -C "$dir" branch --show-current 2>/dev/null || echo "")
            wt_n=$(basename "$dir")
            td_file="$TD_DOCS_BASE/$wt_n/${JIRA_ID}.md"
            if echo "$b" | grep -qiE "${JIRA_ID}" || [[ -f "$td_file" ]]; then
                WORKTREE_PATH="$dir"
                WORKTREE_NAME=$(basename "$dir")
                BRANCH="$b"
                break
            fi
        done
    fi

    # ── 1b. Create/link td-docs ───────────────────────────────────────────────
    # Canonical location : ~/.dev-work/td-docs/<worktree>/<jira_id>.md
    # Symlink location   : <worktree>/.cursor/td-docs/<jira_id>.md -> canonical
    if [[ -n "$WORKTREE_PATH" ]]; then
        _canonical_dir="$TD_DOCS_BASE/$WORKTREE_NAME"
        _canonical="$_canonical_dir/${JIRA_ID}.md"
        _link_dir="$WORKTREE_PATH/.cursor/td-docs"
        _link="$_link_dir/${JIRA_ID}.md"

        mkdir -p "$_canonical_dir"
        mkdir -p "$_link_dir"

        # ── Phase 1: resolve worktree file into canonical ─────────────────────
        if [[ -L "$_link" ]]; then
            # Remove any existing symlink — will be replaced with a hard link
            rm -f "$_link"
            echo "  Removed old symlink (replacing with hard link)"
        elif [[ -f "$_link" ]]; then
            _li=$(stat -c '%i' "$_link")
            _ci=$(stat -c '%i' "$_canonical" 2>/dev/null || echo "none")
            if [[ "$_li" == "$_ci" ]]; then
                : # already the same inode — correct hard link, nothing to do
            elif [[ ! -f "$_canonical" ]]; then
                # Scenario A: canonical missing → move worktree file there
                mv "$_link" "$_canonical"
                echo "  Migrated td-docs: $_link -> $_canonical"
            else
                # Scenario B: canonical exists → it wins; drop the worktree copy
                rm -f "$_link"
                echo "  Removed duplicate in worktree (canonical already exists)"
            fi
        fi

        # ── Phase 2: create canonical from template if still missing ──────────
        if [[ ! -f "$_canonical" ]]; then
            cat > "$_canonical" <<TDTEMPLATE
# ${JIRA_ID}

## Approaches

### Approach 1: <Name>
<description>

Pros:
- 

Cons:
- 

### Approach 2: <Name>
<description>

Pros:
- 

Cons:
- 

### Approach 3: <Name>
<description>

Pros:
- 

Cons:
- 

## Implementation Plan

### Milestones
1. 

### Risk Table
| Risk | Severity | Mitigation |
|------|----------|------------|
|      | LOW      |            |

## PR Annotations

<!-- Notes about the PR, key decisions, review comments -->

TDTEMPLATE
            echo "  Created td-docs: $_canonical"
        fi

        # ── Phase 3: ensure hard link in worktree points to canonical inode ───
        if [[ ! -f "$_link" ]]; then
            ln "$_canonical" "$_link"
            echo "  Hard linked: $_link"
        elif [[ "$(stat -c '%i' "$_link")" != "$(stat -c '%i' "$_canonical")" ]]; then
            rm -f "$_link"
            ln "$_canonical" "$_link"
            echo "  Fixed hard link: $_link"
        fi
    fi

    # ── 2. Parse td-docs markdown ──────────────────────────────────────────────
    TD_DOCS_PATH=""
    TD_DOCS_EXISTS="false"
    if [[ -n "$WORKTREE_PATH" ]]; then
        # Read from canonical path directly (symlink also works via [[ -f ]])
        cand="$TD_DOCS_BASE/$WORKTREE_NAME/${JIRA_ID}.md"
        if [[ -f "$cand" ]]; then
            TD_DOCS_PATH="$cand"
            TD_DOCS_EXISTS="true"
            cp "$cand" "$TMPDIR_TICKET/td-docs.md"
            python3 - "$TMPDIR_TICKET" <<'PYEOF'
import sys, re, json, os
tmpdir = sys.argv[1]
text   = open(os.path.join(tmpdir, "td-docs.md")).read()

def extract(heading_pattern):
    m = re.search(
        r'##\s*(?:' + heading_pattern + r')\s*\n(.*?)(?=\n##\s|\Z)',
        text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ''

sections = {
    'approaches':      extract(r'(?:Code\s+)?Approaches?'),
    'impl_plan':       extract(r'Implementation\s+Plan'),
    'pr_annotations':  extract(r'PR\s+Annotations?'),
    'full_text':       text,
}
with open(os.path.join(tmpdir, 'td-docs.json'), 'w') as f:
    json.dump(sections, f)
PYEOF
        fi
    fi

    # ── 3. GitHub PR data ──────────────────────────────────────────────────────
    echo '{"number":"","title":"","state":"","url":"","merged_at":"","body":""}' \
        > "$TMPDIR_TICKET/pr.json"
    if [[ -n "$BRANCH" && -n "$GH_TOKEN" ]]; then
        PR_RESP=$(curl -sf \
            -H "Authorization: token $GH_TOKEN" \
            "https://${GH_HOST}/api/v3/repos/${GH_ORG}/${GH_REPO_DEV}/pulls?state=all&head=${GH_ORG}:${BRANCH}&per_page=5" \
            2>/dev/null || echo "[]")
        python3 - "$PR_RESP" "$TMPDIR_TICKET/pr.json" <<'PYEOF'
import json, sys
resp_str = sys.argv[1]
out_file = sys.argv[2]
try:
    data = json.loads(resp_str)
    if isinstance(data, list) and len(data) > 0:
        p = data[0]
        result = {
            'number':    str(p['number']),
            'title':     p['title'],
            'state':     p['state'],
            'url':       p['html_url'],
            'merged_at': p.get('merged_at') or '',
            'body':      (p.get('body') or '')[:2000],
        }
        with open(out_file, 'w') as f:
            json.dump(result, f)
except Exception as e:
    pass  # keep default empty json
PYEOF
    fi

    # Fallback: extract PR number from git log
    PR_DATA=$(cat "$TMPDIR_TICKET/pr.json")
    PR_NUMBER=$(echo "$PR_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin)['number'])")
    if [[ -z "$PR_NUMBER" && -n "$WORKTREE_PATH" ]]; then
        GIT_PR=$(git -C "$WORKTREE_PATH" log --oneline --all \
            --format="%s" 2>/dev/null | grep -E "${JIRA_ID}" | \
            grep -oE '#[0-9]+' | head -1 | tr -d '#' || echo "")
        if [[ -n "$GIT_PR" ]]; then
            python3 - "$GIT_PR" "$TMPDIR_TICKET/pr.json" "$BRANCH" "$GH_HOST" "$GH_ORG" "$GH_REPO_DEV" <<'PYEOF'
import json, sys
num      = sys.argv[1]
fpath    = sys.argv[2]
branch   = sys.argv[3]
host     = sys.argv[4]
org      = sys.argv[5]
repo_dev = sys.argv[6]
result = {'number': num, 'title': '', 'state': 'unknown', 'merged_at': '',
          'url': f'https://{host}/{org}/{repo_dev}/pull/{num}', 'body': ''}
with open(fpath, 'w') as f:
    json.dump(result, f)
PYEOF
        fi
    fi

    # ── 4. DSR / DFR status ────────────────────────────────────────────────────
    echo "[]" > "$TMPDIR_TICKET/dsr.json"
    if [[ -n "$BRANCH" ]]; then
        RAW_DSR=$(dsr list --count 50 --duration 30 2>/dev/null || echo "[]")
        python3 - "$RAW_DSR" "$BRANCH" "$JIRA_ID" "$TMPDIR_TICKET/dsr.json" <<'PYEOF'
import json, sys, subprocess

raw_str  = sys.argv[1]
branch   = sys.argv[2]
jira_id  = sys.argv[3]
out_file = sys.argv[4]

try:
    runs = json.loads(raw_str)
except:
    runs = []

matched = [r for r in runs
           if branch in r.get('Branch', '') or jira_id in r.get('Branch', '')]

enriched = []
for r in matched[:5]:
    rid = r.get('Request_ID')
    if rid:
        try:
            result = subprocess.run(['dsr', 'get', str(rid)],
                                    capture_output=True, text=True, timeout=15)
            detail = json.loads(result.stdout)
            r['detail'] = {
                'status':        detail.get('Info', {}).get('status', ''),
                'test_branch':   detail.get('Info', {}).get('test_branch', ''),
                'sha':           detail.get('Info', {}).get('sha_value', ''),
                'build_jobs': [
                    {'name': j.get('job_name'), 'status_id': j.get('status_id'),
                     'comments': j.get('comments', ''), 'url': j.get('url', '')}
                    for j in detail.get('Build jobs', [])
                ],
                'platform_jobs': [
                    {'name': j.get('job_name'), 'status_id': j.get('status_id'),
                     'platform': j.get('platform', ''), 'link': j.get('job_link', '')}
                    for j in detail.get('Platform jobs', [])
                ],
            }
        except Exception as e:
            r['detail'] = {'error': str(e)}
    enriched.append(r)

with open(out_file, 'w') as f:
    json.dump(enriched, f)
PYEOF
    fi

    # ── 5. JIRA ticket details ─────────────────────────────────────────────────
    JIRA_TMPFILE=$(mktemp /tmp/jira_XXXXXX.json)
    echo "{}" > "$TMPDIR_TICKET/jira.json"
    if jira fetch --ids "$JIRA_ID" --output json --export "$JIRA_TMPFILE" >/dev/null 2>&1 && [[ -s "$JIRA_TMPFILE" ]]; then
        python3 - "$JIRA_TMPFILE" "$TMPDIR_TICKET/jira.json" "$JIRA_HOST" <<'PYEOF'
import json, sys
data      = json.load(open(sys.argv[1]))
jira_host = sys.argv[3]
issues    = data.get('issues', [])
if issues:
    i = issues[0]
    f = i['fields']
    result = {
        'key':         i['key'],
        'summary':     f.get('summary', ''),
        'status':      f.get('status', {}).get('name', ''),
        'type':        f.get('issuetype', {}).get('name', ''),
        'assignee':    (f.get('assignee') or {}).get('displayName', ''),
        'description': (f.get('description') or '')[:3000],
        'url':         f'{jira_host}/browse/{i["key"]}',
        'labels':      f.get('labels', []),
        'priority':    f.get('priority', {}).get('name', ''),
    }
    with open(sys.argv[2], 'w') as out:
        json.dump(result, out)
PYEOF
    fi
    rm -f "$JIRA_TMPFILE"

    # ── 6. Assemble final JSON ─────────────────────────────────────────────────
    python3 - "$OUT_FILE" "$JIRA_ID" \
              "$WORKTREE_NAME" "$WORKTREE_PATH" "$BRANCH" \
              "$TD_DOCS_PATH" "$TD_DOCS_EXISTS" \
              "$TMPDIR_TICKET" <<'PYEOF'
import json, sys, os
from datetime import datetime, timezone

out_file      = sys.argv[1]
jira_id       = sys.argv[2]
wt_name       = sys.argv[3]
wt_path       = sys.argv[4]
branch        = sys.argv[5]
td_docs_path  = sys.argv[6]
td_docs_exists= sys.argv[7] == 'true'
tmpdir        = sys.argv[8]

def load(name):
    p = os.path.join(tmpdir, name)
    if os.path.exists(p):
        return json.load(open(p))
    return {} if name.endswith('.json') and name != 'dsr.json' else []

td_data   = load('td-docs.json') if td_docs_exists else {}
pr_data   = load('pr.json')
dsr_data  = json.load(open(os.path.join(tmpdir, 'dsr.json')))
jira_data = load('jira.json')

output = {
    'generated':   datetime.now(timezone.utc).isoformat(),
    'jira_id':     jira_id,
    'jira_detail': jira_data,
    'worktree': {
        'name':   wt_name,
        'path':   wt_path,
        'branch': branch,
    },
    'td_docs': {
        'path':           td_docs_path,
        'exists':         td_docs_exists,
        'approaches':     td_data.get('approaches', ''),
        'impl_plan':      td_data.get('impl_plan', ''),
        'pr_annotations': td_data.get('pr_annotations', ''),
        'full_text':      td_data.get('full_text', ''),
    },
    'github_pr': pr_data,
    'dsr_runs':  dsr_data,
}

with open(out_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f'  Written → {out_file}')
print(f'  Worktree : {wt_name or "not found"} [{branch}]')
print(f'  td-docs  : {"found" if td_docs_exists else "not found"}')
pr_num = pr_data.get('number', '')
print(f'  PR       : {"#" + pr_num + " (" + pr_data.get("state","") + ")" if pr_num else "none"}')
print(f'  DSR runs : {len(dsr_data)}')
PYEOF
}

# ── Entry point ────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--all" ]]; then
    SPRINT_FILE="$DATA_DIR/sprint.json"
    [[ -f "$SPRINT_FILE" ]] || { echo "ERROR: $SPRINT_FILE not found. Run fetch-jira.sh first."; exit 1; }
    IDS=$(python3 -c "
import json
data = json.load(open('$SPRINT_FILE'))
ids = [t['key'] for t in data.get('in_progress',[])] + [t['key'] for t in data.get('done',[])]
print(' '.join(ids))
")
    for id in $IDS; do
        process_ticket "$id"
    done
else
    [[ -n "${1:-}" ]] || { echo "Usage: $0 <AV-ID> [--worktree <name>] | --all"; exit 1; }
    JIRA_ID="${1}"
    FORCE_WT=""
    shift
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --worktree) FORCE_WT="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    process_ticket "$JIRA_ID" "$FORCE_WT"
fi
