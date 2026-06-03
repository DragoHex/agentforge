#!/usr/bin/env python3
"""
LinkedIn Draft Helper — clipboard-based semi-automation.

LinkedIn's web app now uses Next.js RSC server actions for all post creation.
The old Voyager API endpoints (/voyager/api/shares, /ugcPosts, normShares, etc.)
are fully removed. The post-creation modal requires real user clicks (isTrusted=true);
programmatic JS clicks are ignored by LinkedIn's framework.

What this script does:
  1. Parses the markdown: extracts plain text, strips image refs and placeholders.
  2. Copies the text to the macOS clipboard via pbcopy.
  3. Opens linkedin.com/feed/ in Arc's active window.
  4. Prints numbered step-by-step instructions for the user to complete the draft.

The user completes the draft in ~10 seconds:
  - Click "Start a post"
  - Cmd+V to paste
  - Attach image(s) if desired
  - Click X to close the dialog (LinkedIn auto-saves as draft)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"


# ── Content parsing ───────────────────────────────────────────────────────────

def parse_linkedin_markdown(md: str, input_dir: Path) -> tuple[str, list[str]]:
    """
    Parse the LinkedIn markdown file.
    Returns (plain_text, image_paths).
    - Strips image markdown refs from the text body; collects them as attachment paths.
    - Strips <!-- SUBSTACK_URL --> placeholder and the line containing it.
    - Strips any other HTML comments.
    - Strips markdown link syntax, keeping display text only.
    """
    # Collect image paths before stripping them from text
    image_paths = []
    image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    for m in image_pattern.finditer(md):
        ref = m.group(2)
        if ref.startswith("http"):
            continue
        path = (input_dir / ref).resolve()
        if path.exists():
            image_paths.append(str(path))
        else:
            print(f"[linkedin] WARNING: image not found: {path}", file=sys.stderr)

    # Strip image markdown refs from the text
    text = image_pattern.sub("", md)

    # Strip lines containing the Substack URL placeholder
    text = re.sub(r".*<!--\s*SUBSTACK_URL\s*-->.*\n?", "", text)

    # Strip any remaining HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Strip markdown link syntax — keep display text only
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Collapse multiple blank lines to two at most
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip(), image_paths


# ── Arc helpers ───────────────────────────────────────────────────────────────

def arc_open_url(url: str):
    """Open a URL in a new Arc tab (becomes the active tab)."""
    script = f'''
    tell application "Arc"
        activate
        tell front window
            make new tab with properties {{URL:"{url}"}}
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prepare a LinkedIn post draft from a markdown file. "
                    "Copies the text to the clipboard and opens Arc on the LinkedIn feed."
    )
    parser.add_argument(
        "--input",
        default="output/linkedin-post.md",
        help="Markdown file to draft (default: output/linkedin-post.md)",
    )
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    input_dir = input_file.parent
    md = input_file.read_text(encoding="utf-8")

    print(f"[linkedin] Parsing: {input_file.name}", flush=True)
    text, image_paths = parse_linkedin_markdown(md, input_dir)

    if not text.strip():
        print("ERROR: No text content extracted from the markdown file.", file=sys.stderr)
        sys.exit(1)

    print(f"[linkedin] Text length: {len(text)} chars", flush=True)
    print(f"[linkedin] Images found: {len(image_paths)}", flush=True)

    # Copy text to clipboard
    try:
        proc = subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            print("[linkedin] Post text copied to clipboard.", flush=True)
        else:
            print("[linkedin] WARNING: pbcopy failed — copy the text manually.", file=sys.stderr)
    except Exception as e:
        print(f"[linkedin] WARNING: Could not copy to clipboard: {e}", file=sys.stderr)

    # Open LinkedIn feed in Arc
    print(f"[linkedin] Opening LinkedIn feed in Arc: {LINKEDIN_FEED_URL}", flush=True)
    arc_open_url(LINKEDIN_FEED_URL)

    # Print instructions
    print()
    print("=" * 60)
    print("COMPLETE THE DRAFT IN ARC (3 steps):")
    print("=" * 60)
    print()
    print("  1. Click  'Start a post'  in the LinkedIn feed")
    print("  2. Press  Cmd+V  to paste the post text")
    if image_paths:
        print("  3. Click  the image/media icon  and attach:")
        for i, p in enumerate(image_paths, 1):
            print(f"       [{i}] {p}")
    else:
        print("  3. (No images to attach)")
    print()
    print("  To save as DRAFT: click the  X  to close the dialog.")
    print("  LinkedIn will ask 'Save as draft?' — click Save.")
    print()
    print("  DO NOT click 'Post'.")
    print()
    print("  Your post text is in the clipboard and ready to paste.")
    print("=" * 60)


if __name__ == "__main__":
    main()
