#!/usr/bin/env bash
# Setup: install dependencies and build the custom blogger-gemma4 Ollama model.
set -euo pipefail
cd "$(dirname "$0")"

# Python venv + packages
if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
python3 -m playwright install chromium

# mermaid CLI (mmdc) — used by preprocess.py for diagram rendering
if ! command -v mmdc &>/dev/null; then
  echo "Installing @mermaid-js/mermaid-cli globally..."
  npm install -g @mermaid-js/mermaid-cli
fi

# Ollama model
ollama pull gemma4:e4b
ollama create blogger-gemma4 -f Modelfile
