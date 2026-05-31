#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${PI_MODEL:-blogger-gemma4}"
PROVIDER="${PI_PROVIDER:-ollama}"
THINKING="${PI_THINKING:-medium}"
# ollama is built-in; disable extensions to skip MCP startup delay.
# Other providers (nvidia-nim, etc.) may be extension-registered — keep extensions on.
[[ "$PROVIDER" == "ollama" ]] && NO_EXT="--no-extensions" || NO_EXT=""

# Run pi in RPC mode. /skill:name commands are expanded by Pi before reaching the LLM.
# Streams text deltas to stdout. If the model doesn't call write, saves captured output.
run_pi() {
    local message="$1" output_file="$2"
    PI_MODEL="$MODEL" PI_PROVIDER="$PROVIDER" PI_THINKING="$THINKING" \
    PI_OUT="$output_file" PI_NO_EXT="$NO_EXT" python3 - "$message" <<'PYEOF'
import subprocess, json, sys, os, re

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
            text = delta["delta"]
            accumulated.append(text)
            print(text, end="", flush=True)
    if event.get("type") == "agent_end":
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

case "${1:-}" in
  ingest)   # ./run.sh ingest SkillOpt.pdf
    source venv/bin/activate
    if [[ "${2:?Usage: ./run.sh ingest <file-or-url>}" == http* ]]; then
        python3 .pi/skills/ingest-content/extract_webpage.py "$2" --output output/extracted-source.md
    else
        python3 .pi/skills/ingest-content/extract_pdf.py "$2" --output output/extracted-source.md
    fi
    ;;
  teaching) run_pi "/skill:generate-teaching-article Source is at output/extracted-source.md. Read it and generate the article now." \
                   output/teaching-article.md ;;  # ./run.sh teaching
  substack) run_pi "/skill:generate-substack-article Input is at output/teaching-article.md. Read it and generate the article now." \
                   output/substack-article.md ;;  # ./run.sh substack
  linkedin) run_pi "/skill:generate-linkedin-post Input is at output/substack-article.md. Read it and generate the post now." \
                   output/linkedin-post.md    ;;  # ./run.sh linkedin
  all)      # ./run.sh all SkillOpt.pdf
    bash "$0" ingest "${2:-SkillOpt.pdf}"
    bash "$0" teaching
    bash "$0" substack
    bash "$0" linkedin
    ;;
esac
