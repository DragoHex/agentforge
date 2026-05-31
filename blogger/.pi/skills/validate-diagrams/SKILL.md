---
name: validate-diagrams
description: Validate mermaid diagram syntax and Excalidraw JSON structure in markdown output files. Checks for unquoted parentheses in node labels, reserved node IDs, non-ASCII characters, and invalid Excalidraw JSON.
---

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py <file.md>
```

Fix any reported issues then re-run to confirm.
