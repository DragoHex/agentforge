#!/usr/bin/env bash
# Pull the base model then build the custom blogger-gemma4 model.
# ollama create will also auto-pull if the base is missing, but pulling
# first gives clean progress output.
set -euo pipefail
cd "$(dirname "$0")"

ollama pull gemma4:e4b
ollama create blogger-gemma4 -f Modelfile
