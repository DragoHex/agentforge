#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${PI_MODEL:-blogger-gemma4-12b}"
PROVIDER="${PI_PROVIDER:-ollama}"
THINKING="${PI_THINKING:-medium}"
# ollama is built-in; disable extensions to skip MCP startup delay.
# Other providers (nvidia-nim, etc.) may be extension-registered — keep extensions on.
[[ "$PROVIDER" == "ollama" ]] && NO_EXT="--no-extensions" || NO_EXT=""

# ── Terminal helpers ──────────────────────────────────────────────────────────
log_step() { printf "\n\033[1;36m==> %s\033[0m\n" "$*" >&2; }
log_done() { printf "\033[1;32m✓\033[0m  %s\n" "$*" >&2; }
log_info() { printf "\033[2m    %s\033[0m\n" "$*" >&2; }

_SPIN_PID=""
start_spinner() {
    local msg="$1" i=0
    local -a f=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    ( while true; do
          printf "\r   \033[36m%s\033[0m  %s" "${f[$((i % 10))]}" "$msg" >&2
          i=$((i+1)); sleep 0.08
      done ) &
    _SPIN_PID=$!
}
stop_spinner() {
    [[ -z "${_SPIN_PID:-}" ]] && return
    kill "$_SPIN_PID" 2>/dev/null; wait "$_SPIN_PID" 2>/dev/null || true
    printf "\r\033[K" >&2; _SPIN_PID=""
}

# ── Core helpers ──────────────────────────────────────────────────────────────

# Run pi in RPC mode. /skill:name commands are expanded by Pi before reaching the LLM.
# Streams text deltas to stdout. If the model doesn't call write, saves captured output.
run_pi() {
    local message="$1" output_file="$2"
    PI_MODEL="$MODEL" PI_PROVIDER="$PROVIDER" PI_THINKING="$THINKING" \
    PI_OUT="$output_file" PI_NO_EXT="$NO_EXT" python3 - "$message" <<'PYEOF'
import subprocess, json, sys, os, re, threading, time

message     = sys.argv[1]
output_file = os.environ["PI_OUT"]
no_ext      = os.environ.get("PI_NO_EXT", "").split()  # empty list or ["--no-extensions"]

proc = subprocess.Popen(
    ["pi", "--mode", "rpc",
     "--provider", os.environ["PI_PROVIDER"],
     "--model",    os.environ["PI_MODEL"],
     "--thinking", os.environ["PI_THINKING"],
     "--no-session"] + no_ext,
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)

proc.stdin.write(json.dumps({"type": "prompt", "message": message}) + "\n")
proc.stdin.flush()

# Spinner runs until the first text delta arrives from the model.
_spinning = True
def _spin():
    frames = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
    i = 0
    while _spinning:
        print(f"\r   \033[36m{frames[i % 10]}\033[0m  Model thinking...",
              end='', file=sys.stderr, flush=True)
        i += 1
        time.sleep(0.08)
    print('\r\033[K', end='', file=sys.stderr, flush=True)

threading.Thread(target=_spin, daemon=True).start()

accumulated = []
for line in proc.stdout:
    line = line.strip()
    if not line:
        continue
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        continue
    if event.get("type") == "message_update":
        delta = event.get("assistantMessageEvent", {})
        if delta.get("type") == "text_delta":
            if _spinning:
                _spinning = False
                time.sleep(0.1)  # let spinner thread clear its line
            text = delta["delta"]
            accumulated.append(text)
            print(text, end="", flush=True)
    if event.get("type") == "agent_end":
        _spinning = False
        break

print()
proc.stdin.close()
proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
    proc.wait()

# If model used write tool the file is already on disk — done.
if os.path.exists(output_file):
    with open(output_file) as f:
        lines = sum(1 for _ in f)
    print(f"\nSaved: {output_file} ({lines} lines)", file=sys.stderr)
    sys.exit(0)

# Otherwise extract markdown from streamed text (from first # heading).
full_text = "".join(accumulated)
match = re.search(r'^#\s', full_text, re.MULTILINE)
if not match:
    print(f"\nERROR: No markdown content captured for {output_file}", file=sys.stderr)
    sys.exit(1)

content = full_text[match.start():]
os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
with open(output_file, "w") as f:
    f.write(content)
lines = content.count("\n") + 1
print(f"\nSaved from stdout: {output_file} ({lines} lines)", file=sys.stderr)
sys.exit(0)
PYEOF
}

ensure_model_warm() {
    [[ "$PROVIDER" != "ollama" ]] && return 0
    if ollama ps 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${MODEL}"; then
        log_info "${MODEL}: already in memory."
    else
        start_spinner "${MODEL}: loading into memory..."
        curl -sf http://localhost:11434/api/generate \
            -d "{\"model\":\"${MODEL}\",\"prompt\":\"\",\"keep_alive\":\"30m\"}" \
            > /dev/null
        stop_spinner
        log_done "${MODEL} loaded."
    fi
}

activate_venv() { source venv/bin/activate; }

render_visuals() {
    activate_venv
    log_info "Rendering visuals for $(basename "$1")..."
    python3 .pi/skills/publish-draft/preprocess.py --input "$1" --render-only
    log_done "Visuals done."
}

ingest_source() {
    activate_venv
    local src="${1:?Usage: ingest_source <file.pdf|url>}"
    log_step "Ingesting: $src"
    if [[ "$src" == http* ]]; then
        python3 .pi/skills/ingest-content/extract_webpage.py "$src" --output output/extracted-source.md
    else
        python3 .pi/skills/ingest-content/extract_pdf.py "$src" --output output/extracted-source.md
    fi
    log_done "Ingestion complete → output/extracted-source.md"
}

# ── Commands ──────────────────────────────────────────────────────────────────
case "${1:-}" in
  ingest)   # ./run.sh ingest <file.pdf|url>
    ingest_source "${2:?Usage: ./run.sh ingest <file.pdf|url>}"
    ;;
  teaching) # ./run.sh teaching [file.pdf|url]
    [[ -n "${2:-}" ]] && ingest_source "$2"
    ensure_model_warm
    log_step "Generating teaching article..."
    run_pi "/skill:generate-teaching-article Source is at output/extracted-source.md. Read it and generate the article now." \
           output/teaching-article.md
    log_done "Teaching article → output/teaching-article.md"
    render_visuals output/teaching-article.md
    ;;
  substack) # ./run.sh substack [file.pdf|url]
    [[ -n "${2:-}" ]] && ingest_source "$2"
    ensure_model_warm
    log_step "Generating Substack article..."
    run_pi "/skill:generate-substack-article Input is at output/teaching-article.md. Read it and generate the article now." \
           output/substack-article.md
    log_done "Substack article → output/substack-article.md"
    render_visuals output/substack-article.md
    ;;
  linkedin) # ./run.sh linkedin [file.pdf|url]
    [[ -n "${2:-}" ]] && ingest_source "$2"
    ensure_model_warm
    log_step "Generating LinkedIn post..."
    run_pi "/skill:generate-linkedin-post Input is at output/substack-article.md. Read it and generate the post now." \
           output/linkedin-post.md
    log_done "LinkedIn post → output/linkedin-post.md"
    render_visuals output/linkedin-post.md
    ;;
  render)   # ./run.sh render <markdown-file>
    render_visuals "${2:?Usage: ./run.sh render <markdown-file>}"
    ;;
  all)      # ./run.sh all <file.pdf|url>
    ingest_source "${2:?Usage: ./run.sh all <file.pdf|url>}"
    bash "$0" teaching
    bash "$0" substack
    bash "$0" linkedin
    ;;
  draft)    # ./run.sh draft [markdown-file]
    activate_venv
    log_step "Preparing Substack draft..."
    python3 -u .pi/skills/publish-draft/preprocess.py \
      --input "${2:-output/substack-article.md}" \
      --output output/draft-preprocessed.json
    python3 -u .pi/skills/publish-draft/publish_substack.py \
      --preprocessed output/draft-preprocessed.json
    log_done "Draft created."
    ;;
  draft-linkedin)  # ./run.sh draft-linkedin [markdown-file]
    activate_venv
    log_step "Preparing LinkedIn draft..."
    python3 -u .pi/skills/publish-linkedin-draft/publish_linkedin.py \
      --input "${2:-output/linkedin-post.md}"
    log_done "Draft ready — follow the instructions above."
    ;;
esac
