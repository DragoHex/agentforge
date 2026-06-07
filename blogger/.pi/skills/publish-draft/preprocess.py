#!/usr/bin/env python3
"""
Pre-process a markdown article for Substack publishing.
Renders mermaid code blocks to PNG, converts markdown to HTML,
and converts HTML to Substack's Prosemirror JSON format.
Writes a JSON manifest consumed by publish_substack.py.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def render_mermaid_blocks(md: str, input_dir: Path, asset_dir: Path) -> str:
    """Replace ```mermaid blocks with PNG image references via mmdc or mermaid.ink."""
    pattern = r"```mermaid\n(.*?)\n```"

    def replace(match):
        code = match.group(1)
        slug = hashlib.md5(code.encode()).hexdigest()[:8]
        png_path = asset_dir / f"mermaid-{slug}.png"
        rel = os.path.relpath(png_path, input_dir)

        if png_path.exists():
            return f"![Diagram]({rel})"

        rendered = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                ["mmdc", "-i", tmp, "-o", str(png_path), "-b", "white", "-w", "1200"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                rendered = True
            else:
                print(f"[preprocess] mmdc error: {r.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print("[preprocess] mmdc not found; falling back to mermaid.ink", file=sys.stderr)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

        if not rendered:
            try:
                import base64
                import urllib.request
                encoded = base64.urlsafe_b64encode(code.encode()).decode()
                url = f"https://mermaid.ink/img/{encoded}?type=png"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    png_path.write_bytes(resp.read())
                rendered = True
                print(f"[preprocess] mermaid.ink rendered: {png_path.name}", file=sys.stderr)
            except Exception as e:
                print(f"[preprocess] mermaid.ink failed: {e}. Block kept as-is.", file=sys.stderr)
                return match.group(0)

        if not rendered:
            return match.group(0)
        return f"![Diagram]({rel})"

    return re.sub(pattern, replace, md, flags=re.DOTALL)


def render_mermaid_file_refs(md: str, input_dir: Path, asset_dir: Path) -> str:
    """Replace ![caption](*.mermaid) file references with rendered PNG references."""
    pattern = r"!\[([^\]]*)\]\(([^)]+\.mermaid)\)"

    def replace(match):
        caption = match.group(1)
        ref_path = match.group(2)
        # Resolve relative to input_dir, falling back to its parent
        candidates = [
            input_dir / ref_path,
            input_dir.parent / ref_path,
        ]
        mermaid_file = next((p for p in candidates if p.exists()), None)
        if mermaid_file is None:
            print(f"[preprocess] WARNING: .mermaid file not found: {ref_path}", file=sys.stderr)
            return match.group(0)

        code = mermaid_file.read_text().strip()
        slug = hashlib.md5(code.encode()).hexdigest()[:8]
        png_path = asset_dir / f"mermaid-{slug}.png"
        rel = os.path.relpath(png_path, input_dir)

        if png_path.exists():
            return f"![{caption}]({rel})"

        rendered = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                ["mmdc", "-i", tmp, "-o", str(png_path), "-b", "white", "-w", "1200"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                rendered = True
            else:
                print(f"[preprocess] mmdc error: {r.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print("[preprocess] mmdc not found; falling back to mermaid.ink", file=sys.stderr)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

        if not rendered:
            try:
                import base64
                import urllib.request
                encoded = base64.urlsafe_b64encode(code.encode()).decode()
                url = f"https://mermaid.ink/img/{encoded}?type=png"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    png_path.write_bytes(resp.read())
                rendered = True
                print(f"[preprocess] mermaid.ink rendered: {png_path.name}", file=sys.stderr)
            except Exception as e:
                print(f"[preprocess] mermaid.ink failed: {e}. Reference kept as-is.", file=sys.stderr)
                return match.group(0)

        if not rendered:
            return match.group(0)
        return f"![{caption}]({rel})"

    return re.sub(pattern, replace, md)


def render_missing_charts(md: str, input_dir: Path) -> str:
    """
    For any local PNG reference that is missing, check for a .params.json sidecar
    written by generate_graph.py and re-run the script to regenerate the chart.
    Mermaid PNGs are handled separately by render_mermaid_blocks / render_mermaid_file_refs.
    """
    generate_graph = (
        Path(__file__).parent.parent / "create-visualization" / "generate_graph.py"
    ).resolve()

    pattern = r"!\[([^\]]*)\]\(([^)]+\.(?:png|jpg|jpeg))\)"

    def replace(match):
        ref = match.group(2)
        if ref.startswith("http"):
            return match.group(0)
        target = (input_dir / ref).resolve()
        if target.exists():
            return match.group(0)

        sidecar = target.with_suffix(".params.json")
        if not sidecar.exists():
            print(f"[preprocess] WARNING: missing image, no sidecar: {ref}", file=sys.stderr)
            return match.group(0)

        params = json.loads(sidecar.read_text())
        cmd = [sys.executable, str(generate_graph),
               "--type", params["type"],
               "--title", params.get("title", "Chart"),
               "--output", str(target)]
        if "data_file" in params:
            cmd += ["--data-file", params["data_file"]]
        else:
            cmd += ["--data", json.dumps(params["data"])]

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[preprocess] Regenerated chart: {target.name}", file=sys.stderr)
        else:
            print(f"[preprocess] Chart regen failed for {target.name}: {r.stderr.strip()}",
                  file=sys.stderr)
        return match.group(0)

    return re.sub(pattern, replace, md)


def strip_ai_image_placeholders(md: str) -> str:
    """Remove <!-- AI-IMAGE: ... --> comments before draft publishing. They are invisible
    in rendered HTML anyway, but removing them keeps the Prosemirror doc clean."""
    return re.sub(r"<!--\s*AI-IMAGE:.*?-->", "", md, flags=re.DOTALL)


def strip_excalidraw_refs(md: str) -> str:
    """Replace .excalidraw image references with italic placeholder text."""
    def replace(m):
        label = m.group(1) or Path(m.group(2)).stem
        print(f"[preprocess] Skipping excalidraw (not auto-convertible): {m.group(2)}", file=sys.stderr)
        return f"*[Diagram: {label}]*"
    return re.sub(r"!\[([^\]]*)\]\(([^)]+\.excalidraw)\)", replace, md)


def download_http_images(md: str, input_dir: Path, asset_dir: Path) -> str:
    """Download http/https image URLs and replace with local relative paths."""
    import urllib.request as _urlreq
    from urllib.parse import urlparse

    pattern = r"!\[([^\]]*)\]\((https?://[^)]+)\)"

    def replace(match):
        caption = match.group(1)
        url = match.group(2)
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix or ".png"
        slug = hashlib.md5(url.encode()).hexdigest()[:12]
        local_path = asset_dir / f"web-{slug}{ext}"
        rel = os.path.relpath(local_path, input_dir)

        if local_path.exists():
            return f"![{caption}]({rel})"

        try:
            req = _urlreq.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _urlreq.urlopen(req, timeout=20) as resp:
                local_path.write_bytes(resp.read())
            print(f"[preprocess] Downloaded: {local_path.name}  ← {url}", file=sys.stderr)
            return f"![{caption}]({rel})"
        except Exception as e:
            print(f"[preprocess] WARNING: could not download {url}: {e}", file=sys.stderr)
            return match.group(0)

    return re.sub(pattern, replace, md)


def extract_title_subtitle(md: str) -> tuple:
    title = subtitle = ""
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
        elif stripped.startswith("### ") and title and not subtitle:
            subtitle = stripped[4:].strip()
    return title, subtitle


def collect_image_paths(md: str, input_dir: Path) -> list:
    """Return absolute paths of all local PNG images referenced in the markdown."""
    refs = re.findall(r"!\[.*?\]\(([^)]+)\)", md)
    paths = []
    for ref in refs:
        if ref.startswith("http"):
            continue
        path = (input_dir / ref).resolve()
        if path.exists():
            paths.append(str(path))
        else:
            print(f"[preprocess] WARNING: image not found: {path}", file=sys.stderr)
    return paths


def html_to_prosemirror(html: str) -> dict:
    """
    Convert HTML to Substack's Prosemirror JSON document format.
    Handles: headings, paragraphs, strong, em, links, images (captionedImage/image2),
    bullet_list, ordered_list, list_item, blockquote, code_block, horizontal_rule.
    """
    from html.parser import HTMLParser

    class _Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.doc = {"type": "doc", "content": []}
            self.stack = [self.doc["content"]]
            self.marks: list = []
            self._in_pre = False

        def _cur(self):
            return self.stack[-1]

        def _push(self, node):
            self._cur().append(node)
            self.stack.append(node["content"])

        def _pop(self):
            if len(self.stack) > 1:
                self.stack.pop()

        def _text(self, text):
            if not text:
                return
            node: dict = {"type": "text", "text": text}
            if self.marks:
                node["marks"] = list(self.marks)
            self._cur().append(node)

        def _remove_mark(self, type_):
            for i in range(len(self.marks) - 1, -1, -1):
                if self.marks[i]["type"] == type_:
                    self.marks.pop(i)
                    break

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            a = dict(attrs)
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._push({"type": "heading", "attrs": {"level": int(tag[1])}, "content": []})
            elif tag == "p":
                self._push({"type": "paragraph", "content": []})
            elif tag == "blockquote":
                self._push({"type": "blockquote", "content": []})
            elif tag == "ul":
                self._push({"type": "bullet_list", "content": []})
            elif tag == "ol":
                self._push({"type": "ordered_list",
                             "attrs": {"start": 1, "type": None, "order": 1},
                             "content": []})
            elif tag == "li":
                para = {"type": "paragraph", "content": []}
                node = {"type": "list_item", "content": [para]}
                self._cur().append(node)
                self.stack.append(para["content"])
            elif tag == "pre":
                self._in_pre = True
                self._push({"type": "code_block", "content": []})
            elif tag == "code" and not self._in_pre:
                self.marks.append({"type": "code"})
            elif tag == "img":
                src = a.get("src", "")
                alt = a.get("alt", "") or None
                self._cur().append({
                    "type": "captionedImage",
                    "content": [{
                        "type": "image2",
                        "attrs": {
                            "src": src, "srcNoWatermark": None, "fullscreen": None,
                            "imageSize": None, "height": None, "width": None,
                            "resizeWidth": None, "bytes": None, "alt": alt,
                            "title": None, "type": None, "href": None,
                            "belowTheFold": False, "topImage": False,
                            "internalRedirect": None, "isProcessing": False,
                            "align": None, "offset": False,
                        },
                    }],
                })
            elif tag == "hr":
                self._cur().append({"type": "horizontal_rule"})
            elif tag == "br":
                self._cur().append({"type": "hard_break"})
            elif tag in ("strong", "b"):
                self.marks.append({"type": "strong"})
            elif tag in ("em", "i"):
                self.marks.append({"type": "em"})
            elif tag == "a":
                self.marks.append({
                    "type": "link",
                    "attrs": {
                        "href": a.get("href", ""),
                        "target": "_blank",
                        "rel": "noopener noreferrer nofollow",
                        "class": None,
                    },
                })

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p",
                        "blockquote", "ul", "ol", "li", "pre"):
                if tag == "pre":
                    self._in_pre = False
                self._pop()
            elif tag in ("strong", "b"):
                self._remove_mark("strong")
            elif tag in ("em", "i"):
                self._remove_mark("em")
            elif tag == "code":
                self._remove_mark("code")
            elif tag == "a":
                self._remove_mark("link")

        def handle_data(self, data):
            if self._in_pre:
                self._text(data)
                return
            stripped = data.strip()
            if not stripped:
                return
            text = " ".join(stripped.split())
            # Preserve a single boundary space so bold/em/link text isn't fused
            # with adjacent plain text (e.g. "The <strong>frozen</strong> model").
            if data and data[0].isspace():
                text = " " + text
            if data and data[-1].isspace():
                text = text + " "
            self._text(text)

    p = _Parser()
    p.feed(html)

    # Wrap any stray top-level text nodes in a paragraph
    cleaned = []
    for node in p.doc["content"]:
        if node.get("type") == "text":
            if cleaned and cleaned[-1].get("type") == "paragraph":
                cleaned[-1]["content"].append(node)
            else:
                cleaned.append({"type": "paragraph", "content": [node]})
        elif node.get("type"):
            if node.get("type") in ("paragraph", "heading") and not node.get("content"):
                continue
            cleaned.append(node)
    p.doc["content"] = cleaned
    return p.doc


def markdown_to_html(md: str) -> str:
    try:
        import markdown as md_lib
        return md_lib.markdown(md, extensions=["fenced_code", "tables", "nl2br"])
    except ImportError:
        print("[preprocess] WARNING: 'markdown' package not installed. Install: pip install Markdown",
              file=sys.stderr)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", md, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', html)
        paragraphs = [
            f"<p>{p.strip()}</p>"
            for p in re.split(r"\n{2,}", html)
            if p.strip() and not p.strip().startswith("<")
        ]
        return "\n".join(paragraphs)


def main():
    parser = argparse.ArgumentParser(description="Pre-process markdown for Substack draft")
    parser.add_argument("--input", required=True, help="Input markdown file")
    parser.add_argument("--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--asset-dir", help="Dir for generated PNG assets")
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Only render mermaid/images and update the markdown in-place. Skip HTML/JSON conversion.",
    )
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    input_dir = input_file.parent

    if args.render_only:
        # Derive a per-article visuals directory from the file stem, e.g.
        # output/teaching-article.md  → output/teaching-visuals/
        # output/substack-article.md  → output/substack-visuals/
        # output/linkedin-post.md     → output/linkedin-visuals/
        stem = input_file.stem                        # "teaching-article"
        section = stem.split("-")[0]                  # "teaching"
        default_asset_dir = input_dir / f"{section}-visuals"
        asset_dir = Path(args.asset_dir).resolve() if args.asset_dir else default_asset_dir
        asset_dir.mkdir(parents=True, exist_ok=True)

        md = input_file.read_text()
        md = download_http_images(md, input_dir, asset_dir)
        md = render_mermaid_file_refs(md, input_dir, asset_dir)
        md = render_mermaid_blocks(md, input_dir, asset_dir)
        render_missing_charts(md, input_dir)
        input_file.write_text(md)
        images = collect_image_paths(md, input_dir)
        print(f"[preprocess] render-only: updated {input_file.name}", file=sys.stderr)
        print(f"[preprocess] Images found: {len(images)}", file=sys.stderr)
        return

    asset_dir = Path(args.asset_dir).resolve() if args.asset_dir else input_dir / "draft-assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    md = input_file.read_text()
    md = download_http_images(md, input_dir, asset_dir)
    md = render_mermaid_file_refs(md, input_dir, asset_dir)
    md = render_mermaid_blocks(md, input_dir, asset_dir)
    render_missing_charts(md, input_dir)
    md = strip_excalidraw_refs(md)
    md = strip_ai_image_placeholders(md)

    title, subtitle = extract_title_subtitle(md)
    images = collect_image_paths(md, input_dir)
    html = markdown_to_html(md)
    prosemirror = html_to_prosemirror(html)

    result = {
        "input_file": str(input_file),
        "input_dir": str(input_dir),
        "source_dir": str(input_dir),
        "title": title,
        "subtitle": subtitle,
        "html": html,
        "prosemirror": prosemirror,
        "images": images,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2))
        print(f"[preprocess] Written: {args.output}", file=sys.stderr)
        print(f"[preprocess] Title: {title}", file=sys.stderr)
        print(f"[preprocess] Images: {len(images)}", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
