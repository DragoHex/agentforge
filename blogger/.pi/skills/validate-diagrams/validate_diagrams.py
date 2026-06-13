#!/usr/bin/env python3
"""
Validate diagrams embedded in markdown article files.

Checks:
  - Mermaid: syntax rules that commonly cause parse failures
  - Excalidraw: JSON validity and required field presence

Usage:
    python3 .pi/skills/validate-diagrams/validate_diagrams.py output/teaching-article.md
    python3 .pi/skills/validate-diagrams/validate_diagrams.py output/*.md
"""

import sys
import os
import re
import json
import subprocess
import argparse

MERMAID_RESERVED_NODE_IDS = {
    "end", "subgraph", "graph", "flowchart", "classDef",
    "click", "style", "linkStyle", "direction",
}

EXCALIDRAW_REQUIRED_ELEMENT_FIELDS = {
    "id", "type", "x", "y", "width", "height",
    "strokeColor", "fillStyle", "opacity",
}

EXCALIDRAW_VALID_TYPES = {
    "rectangle", "ellipse", "diamond", "arrow",
    "line", "text", "freedraw", "image",
}


def extract_mermaid_blocks(text):
    """Return list of (start_line, code) for each ```mermaid block."""
    blocks = []
    lines = text.splitlines()
    in_block = False
    start_line = 0
    current = []
    for i, line in enumerate(lines, 1):
        if line.strip() == "```mermaid" and not in_block:
            in_block = True
            start_line = i
            current = []
        elif line.strip() == "```" and in_block:
            in_block = False
            blocks.append((start_line, "\n".join(current)))
        elif in_block:
            current.append(line)
    return blocks


def extract_excalidraw_refs(text):
    """Return list of .excalidraw file paths referenced in the markdown."""
    return re.findall(r'\(([^)]+\.excalidraw)\)', text)


def validate_mermaid_syntax(code, start_line, filepath):
    """Rule-based mermaid syntax check. Returns list of error strings."""
    errors = []
    lines = code.splitlines()

    for rel, line in enumerate(lines, 1):
        abs_line = start_line + rel
        prefix = f"  {filepath}:{abs_line}"

        # Non-ASCII characters in node labels (wrong language bleed-through)
        if re.search(r'[^\x00-\x7F]', line):
            errors.append(f"{prefix}: non-ASCII characters in diagram — likely language bleed-through: {line.strip()!r}")

        # Unquoted parentheses inside node labels: A[text (with parens)]
        # Correct form: A["text (with parens)"]
        if re.search(r'\[([^\]"]*\([^\]]*\)[^\]"]*)\]', line):
            errors.append(f"{prefix}: unquoted parentheses in node label — wrap label in double quotes: {line.strip()!r}")

        # Reserved word used as a node ID at start of line (e.g. "end[End]")
        match = re.match(r'^\s*(\w+)\[', line)
        if match and match.group(1).lower() in MERMAID_RESERVED_NODE_IDS:
            errors.append(f"{prefix}: reserved keyword '{match.group(1)}' used as node ID — rename to e.g. '{match.group(1)}Node'")

        # Unquoted edge label with special chars: -->|label(x)| or -->|label,x|
        edge_label = re.search(r'\|([^|"]+)\|', line)
        if edge_label:
            label = edge_label.group(1)
            if re.search(r'[(),]', label):
                errors.append(f"{prefix}: edge label with special chars needs quoting — use |\"{label}\"| : {line.strip()!r}")

        # classDef or class keyword — these trigger rendering failures in some renderers
        if re.match(r'^\s*classDef\s', line) or re.match(r'^\s*class\s+\w+\s+\w+', line):
            errors.append(f"{prefix}: classDef/class styling may fail in some renderers — use default theme instead: {line.strip()!r}")

    return errors


def validate_mermaid_with_mmdc(code, filepath):
    """Try mmdc for authoritative parse check. Returns list of errors."""
    mmdc = os.path.join(os.path.dirname(__file__), "..", "node_modules", ".bin", "mmdc")
    mmdc = os.path.normpath(mmdc)
    if not os.path.exists(mmdc):
        return []

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
        f.write(code)
        tmp_in = f.name
    tmp_out = tmp_in.replace(".mmd", ".svg")
    try:
        result = subprocess.run(
            [mmdc, "-i", tmp_in, "-o", tmp_out, "--quiet"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            return [f"  {filepath}: mmdc parse error: {stderr[:200]}"]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    finally:
        for p in (tmp_in, tmp_out):
            try:
                os.unlink(p)
            except FileNotFoundError:
                pass
    return []


def validate_excalidraw_file(path, base_dir):
    """Validate an .excalidraw JSON file. Returns list of error strings."""
    full_path = os.path.join(base_dir, path)
    if not os.path.exists(full_path):
        return [f"  {path}: file not found"]

    errors = []
    try:
        with open(full_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"  {path}: invalid JSON — {e}"]

    if data.get("type") != "excalidraw":
        errors.append(f"  {path}: missing 'type': 'excalidraw' at root")
    if not isinstance(data.get("elements"), list):
        errors.append(f"  {path}: 'elements' must be a list")
        return errors

    for i, el in enumerate(data["elements"]):
        missing = EXCALIDRAW_REQUIRED_ELEMENT_FIELDS - set(el.keys())
        if missing:
            errors.append(f"  {path}: element[{i}] missing fields: {sorted(missing)}")
        if el.get("type") not in EXCALIDRAW_VALID_TYPES:
            errors.append(f"  {path}: element[{i}] unknown type '{el.get('type')}'")
        if el.get("type") == "arrow" and "points" not in el:
            errors.append(f"  {path}: arrow element[{i}] missing 'points' array")

    return errors


def validate_file(filepath):
    """Validate all diagrams in a markdown file. Returns (ok, errors)."""
    try:
        with open(filepath) as f:
            text = f.read()
    except FileNotFoundError:
        return False, [f"{filepath}: file not found"]

    base_dir = os.path.dirname(filepath)
    errors = []

    mermaid_blocks = extract_mermaid_blocks(text)
    for start_line, code in mermaid_blocks:
        rule_errors = validate_mermaid_syntax(code, start_line, filepath)
        errors.extend(rule_errors)
        mmdc_errors = validate_mermaid_with_mmdc(code, filepath)
        errors.extend(mmdc_errors)

    excalidraw_refs = extract_excalidraw_refs(text)
    for ref in excalidraw_refs:
        errors.extend(validate_excalidraw_file(ref, base_dir))

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate diagrams in markdown files")
    parser.add_argument("files", nargs="+", help="Markdown files to validate")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with non-zero code if any warnings found")
    args = parser.parse_args()

    all_clean = True
    for filepath in args.files:
        ok, errors = validate_file(filepath)
        mermaid_count = 0
        excalidraw_count = 0
        try:
            with open(filepath) as f:
                text = f.read()
            mermaid_count = len(extract_mermaid_blocks(text))
            excalidraw_count = len(extract_excalidraw_refs(text))
        except FileNotFoundError:
            pass

        status = "OK" if ok else "ISSUES"
        print(f"[{status}] {filepath}  ({mermaid_count} mermaid, {excalidraw_count} excalidraw)")
        for err in errors:
            print(err)
            all_clean = False

    if not all_clean:
        print("\nFix the issues above and re-run the validation.")
        if args.strict:
            sys.exit(1)
    else:
        print("\nAll diagrams passed validation.")


if __name__ == "__main__":
    main()
