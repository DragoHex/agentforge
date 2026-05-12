#!/usr/bin/env bash
# transition-ticket.sh <JIRA-ID> <todo|in_progress|done>
# Updates a Jira ticket's workflow status via the REST API.

set -euo pipefail

JIRA_ID="${1:-}"
TARGET="${2:-}"    # todo | in_progress | done

[[ -z "$JIRA_ID" || -z "$TARGET" ]] && {
  echo "Usage: $0 <JIRA-ID> <todo|in_progress|done>"
  exit 1
}

# ── Read credentials from ~/.jira-cli.yaml ────────────────────────────────────
CONFIG="$HOME/.jira-cli.yaml"
[[ ! -f "$CONFIG" ]] && { echo "ERROR: jira config not found at $CONFIG"; exit 1; }

JIRA_HOST=$(grep "^host:" "$CONFIG" | awk '{print $2}' | tr -d '[:space:]')
JIRA_TOKEN=$(grep "^token:" "$CONFIG" | awk '{print $2}' | tr -d '[:space:]')

[[ -z "$JIRA_HOST" || -z "$JIRA_TOKEN" ]] && {
  echo "ERROR: Could not read host/token from $CONFIG"
  exit 1
}

# ── Map target column to Jira status name patterns ───────────────────────────
case "$TARGET" in
  todo)        STATUS_PATTERN="To Do|Open|Backlog|Reopened" ;;
  in_progress) STATUS_PATTERN="In Progress" ;;
  done)        STATUS_PATTERN="Done|Resolved|Closed" ;;
  *)           echo "ERROR: Unknown target status '$TARGET'"; exit 1 ;;
esac

# ── Fetch available transitions ───────────────────────────────────────────────
TRANSITIONS_FILE=$(mktemp /tmp/jira-transitions-XXXXXX.json)
trap 'rm -f "$TRANSITIONS_FILE"' EXIT

HTTP_CODE=$(curl -sf \
  -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Accept: application/json" \
  -o "$TRANSITIONS_FILE" \
  -w "%{http_code}" \
  "$JIRA_HOST/rest/api/2/issue/$JIRA_ID/transitions")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "ERROR: Could not fetch transitions for $JIRA_ID (HTTP $HTTP_CODE)"
  cat "$TRANSITIONS_FILE"
  exit 1
fi

# ── Find matching transition ID ───────────────────────────────────────────────
TRANSITION_ID=$(python3 - <<PYEOF
import json, re, sys

with open("$TRANSITIONS_FILE") as f:
    data = json.load(f)

pattern = re.compile(r"$STATUS_PATTERN", re.IGNORECASE)
for t in data.get("transitions", []):
    if pattern.search(t["to"]["name"]):
        print(t["id"])
        sys.exit(0)

# No match — print available to stderr for debugging
print("NONE", end="")
for t in data.get("transitions", []):
    print(f"  {t['id']}: {t['name']} -> {t['to']['name']}", file=sys.stderr)
PYEOF
)

if [[ "$TRANSITION_ID" == "NONE" || -z "$TRANSITION_ID" ]]; then
  echo "ERROR: No transition found matching '$TARGET' for $JIRA_ID"
  echo "Available transitions:"
  python3 -c "
import json
with open('$TRANSITIONS_FILE') as f:
    d = json.load(f)
for t in d.get('transitions', []):
    print(f'  {t[\"id\"]}: {t[\"name\"]} -> {t[\"to\"][\"name\"]}')
"
  exit 1
fi

echo "Transitioning $JIRA_ID → $TARGET (transition_id=$TRANSITION_ID)..."

# ── Apply the transition ──────────────────────────────────────────────────────
BODY_FILE=$(mktemp /tmp/jira-body-XXXXXX.txt)
trap 'rm -f "$TRANSITIONS_FILE" "$BODY_FILE"' EXIT

HTTP_CODE=$(curl -s -X POST \
  -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Content-Type: application/json" \
  -o "$BODY_FILE" \
  -w "%{http_code}" \
  -d "{\"transition\":{\"id\":\"$TRANSITION_ID\"}}" \
  "$JIRA_HOST/rest/api/2/issue/$JIRA_ID/transitions")

if [[ "$HTTP_CODE" == "204" || "$HTTP_CODE" == "200" ]]; then
  echo "SUCCESS: $JIRA_ID moved to $TARGET"
  # Refresh sprint data so the JSON cache reflects the new status
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  bash "$SCRIPT_DIR/fetch-jira.sh" > /dev/null 2>&1 || true
  echo "Sprint data refreshed"
else
  echo "ERROR: Transition failed (HTTP $HTTP_CODE)"
  cat "$BODY_FILE"
  exit 1
fi
