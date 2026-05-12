#!/usr/bin/env bash
# Unit tests for transition-ticket.sh
# Uses a mock curl binary injected via PATH to avoid real Jira API calls.

set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/transition-ticket.sh"
PASS=0; FAIL=0

ok()   { echo "  PASS: $1"; ((PASS++)) || true; }
fail() { echo "  FAIL: $1 — $2"; ((FAIL++)) || true; }

# ── Test environment setup ────────────────────────────────────────────────────
MOCK_DIR=$(mktemp -d)
trap 'rm -rf "$MOCK_DIR"' EXIT

# Fake ~/.jira-cli.yaml
cat > "$MOCK_DIR/.jira-cli.yaml" <<'YAML'
host: https://mock-jira.test
username: testuser
token: mock-token
project: AV
YAML

# Default mock curl: GET → transitions JSON, POST → 204
write_mock_curl() {
  cat > "$MOCK_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
OUT_FILE=""; IS_POST=false; PREV=""
for arg in "$@"; do
  case "$PREV" in
    -o) OUT_FILE="$arg" ;;
    -X) [[ "$arg" == "POST" ]] && IS_POST=true ;;
  esac
  PREV="$arg"
done
if $IS_POST; then
  [[ -n "$OUT_FILE" ]] && printf '' > "$OUT_FILE"
  printf '204'
else
  RESP='{"transitions":[{"id":"51","name":"In Progress","to":{"id":"3","name":"In Progress"}},{"id":"71","name":"To Do","to":{"id":"1","name":"To Do"}},{"id":"111","name":"Done (2)","to":{"id":"5","name":"Done"}}]}'
  [[ -n "$OUT_FILE" ]] && printf '%s' "$RESP" > "$OUT_FILE"
  printf '200'
fi
MOCK
  chmod +x "$MOCK_DIR/curl"
}
write_mock_curl

# Mock fetch-jira.sh (called after successful transition; side-effect only)
cat > "$MOCK_DIR/fetch-jira.sh" <<'MOCK'
#!/usr/bin/env bash
echo "mock:fetch-jira.sh"
MOCK
chmod +x "$MOCK_DIR/fetch-jira.sh"

export PATH="$MOCK_DIR:$PATH"
export HOME="$MOCK_DIR"

# ── Tests ─────────────────────────────────────────────────────────────────────

echo "── Argument validation (no network calls) ────────────────────────────────"

# T1: no arguments — capture to variable to avoid pipefail swallowing exit code
out=$(bash "$SCRIPT" 2>&1 || true)
echo "$out" | grep -q "Usage:" && ok "T1: no args → shows Usage" || \
  fail "T1: no args" "expected 'Usage:' in output, got: $out"
bash "$SCRIPT" >/dev/null 2>&1 && fail "T1: no args → wrong exit code" "expected non-zero" || \
  ok "T1: no args → exits non-zero"

# T2: one argument (missing target)
out=$(bash "$SCRIPT" "AV-1234" 2>&1 || true)
echo "$out" | grep -q "Usage:" && ok "T2: one arg → shows Usage" || \
  fail "T2: one arg" "expected 'Usage:' in output, got: $out"

# T3: unknown target status
if out=$(bash "$SCRIPT" "AV-1234" "invalid_status" 2>&1); then
  fail "T3: unknown target" "expected exit 1"
else
  echo "$out" | grep -qi "Unknown" && ok "T3: unknown status → error" || \
    fail "T3: unknown status" "expected 'Unknown' in output, got: $out"
fi

echo ""
echo "── Successful transitions (mock curl) ────────────────────────────────────"

# T4: in_progress transition
if out=$(bash "$SCRIPT" "AV-1234" "in_progress" 2>&1); then
  echo "$out" | grep -q "SUCCESS" && ok "T4: in_progress → SUCCESS" || \
    fail "T4: in_progress" "no SUCCESS in output: $out"
else
  fail "T4: in_progress" "exited non-zero: $out"
fi

# T5: todo transition
if out=$(bash "$SCRIPT" "AV-1234" "todo" 2>&1); then
  echo "$out" | grep -q "SUCCESS" && ok "T5: todo → SUCCESS" || \
    fail "T5: todo" "no SUCCESS: $out"
else
  fail "T5: todo" "exited non-zero: $out"
fi

# T6: done transition
if out=$(bash "$SCRIPT" "AV-1234" "done" 2>&1); then
  echo "$out" | grep -q "SUCCESS" && ok "T6: done → SUCCESS" || \
    fail "T6: done" "no SUCCESS: $out"
else
  fail "T6: done" "exited non-zero: $out"
fi

echo ""
echo "── Edge cases ────────────────────────────────────────────────────────────"

# T7: no matching transition available
cat > "$MOCK_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
OUT_FILE=""; PREV=""
for arg in "$@"; do
  [[ "$PREV" == "-o" ]] && OUT_FILE="$arg"
  PREV="$arg"
done
RESP='{"transitions":[{"id":"99","name":"Deferred","to":{"id":"9","name":"Deferred - Avi"}}]}'
[[ -n "$OUT_FILE" ]] && printf '%s' "$RESP" > "$OUT_FILE"
printf '200'
MOCK
chmod +x "$MOCK_DIR/curl"

if out=$(bash "$SCRIPT" "AV-1234" "done" 2>&1); then
  fail "T7: no match" "expected exit 1 when no transition matches"
else
  echo "$out" | grep -q "ERROR" && ok "T7: no match → ERROR" || \
    fail "T7: no match" "expected 'ERROR' in output: $out"
fi

# T8: Jira API returns non-204 on POST (server error)
cat > "$MOCK_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
OUT_FILE=""; IS_POST=false; PREV=""
for arg in "$@"; do
  case "$PREV" in
    -o) OUT_FILE="$arg" ;;
    -X) [[ "$arg" == "POST" ]] && IS_POST=true ;;
  esac
  PREV="$arg"
done
if $IS_POST; then
  [[ -n "$OUT_FILE" ]] && printf '{"errorMessages":["Forbidden"]}' > "$OUT_FILE"
  printf '403'
else
  RESP='{"transitions":[{"id":"51","name":"In Progress","to":{"id":"3","name":"In Progress"}}]}'
  [[ -n "$OUT_FILE" ]] && printf '%s' "$RESP" > "$OUT_FILE"
  printf '200'
fi
MOCK
chmod +x "$MOCK_DIR/curl"

if out=$(bash "$SCRIPT" "AV-1234" "in_progress" 2>&1); then
  fail "T8: API 403" "expected exit 1 on forbidden"
else
  echo "$out" | grep -q "ERROR" && ok "T8: API 403 → ERROR" || \
    fail "T8: API 403" "expected 'ERROR' in output: $out"
fi

# T9: transitions endpoint itself returns non-200
write_mock_curl   # reset to default
cat > "$MOCK_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
OUT_FILE=""; PREV=""
for arg in "$@"; do [[ "$PREV" == "-o" ]] && OUT_FILE="$arg"; PREV="$arg"; done
[[ -n "$OUT_FILE" ]] && printf '{"message":"Not Found"}' > "$OUT_FILE"
printf '404'
MOCK
chmod +x "$MOCK_DIR/curl"

if out=$(bash "$SCRIPT" "AV-5678" "done" 2>&1); then
  fail "T9: GET 404" "expected exit 1 when transitions endpoint fails"
else
  echo "$out" | grep -q "ERROR" && ok "T9: GET 404 → ERROR" || \
    fail "T9: GET 404" "expected 'ERROR' in output: $out"
fi

# T10: correct transition ID is picked for each target
write_mock_curl   # all three transitions available
for target in todo in_progress done; do
  out=$(bash "$SCRIPT" "AV-X" "$target" 2>&1) || true
  id=$(echo "$out" | grep -oP 'transition_id=\K[0-9]+')
  case "$target" in
    todo)        [[ "$id" == "71" ]]  && ok "T10: $target picks id=71"  || fail "T10: $target id" "got id=$id" ;;
    in_progress) [[ "$id" == "51" ]]  && ok "T10: $target picks id=51"  || fail "T10: $target id" "got id=$id" ;;
    done)        [[ "$id" == "111" ]] && ok "T10: $target picks id=111" || fail "T10: $target id" "got id=$id" ;;
  esac
done

echo ""
TOTAL=$((PASS + FAIL))
echo "$TOTAL tests — $PASS passed, $FAIL failed"
exit $((FAIL > 0 ? 1 : 0))
