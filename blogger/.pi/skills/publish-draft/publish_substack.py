#!/usr/bin/env python3
"""
Create a Substack draft using Arc's existing browser session.
Uses the Substack API via synchronous XHR executed inside Arc via AppleScript.
No new browser, no cookie extraction, no authentication needed.
Arc must be running with dragohex.substack.com accessible.
Never publishes — saves as draft only.
"""

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

# The publication host — Substack API access is scoped to this domain
PUBLICATION_HOST = "dragohex.substack.com"
# Use the drafts list page — provides API context on the right domain without
# triggering Substack's SPA to auto-create an empty "Untitled" draft on load.
EDITOR_URL = f"https://{PUBLICATION_HOST}/publish/posts/drafts"


# ── AppleScript helpers ──────────────────────────────────────────────────────

def arc_js(js: str, timeout: int = 30) -> str:
    """Execute JS synchronously in Arc's active tab. Returns string result."""
    safe = js.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
    script = f'tell application "Arc" to tell front window to tell active tab to execute javascript "{safe}"'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"arc_js failed: {r.stderr.strip()}")
    raw = r.stdout.strip()
    # AppleScript wraps string results in outer quotes and escapes inner quotes.
    # json.loads correctly decodes this escaping back to the original string.
    try:
        decoded = json.loads(raw)
        return str(decoded) if not isinstance(decoded, str) else decoded
    except Exception:
        return raw.strip('"')


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


# ── Substack API calls via XHR in Arc's publication context ─────────────────

def get_author_id() -> int:
    """Return the publication author's user_id from existing draft bylines."""
    result = arc_js("""(function(){
var x=new XMLHttpRequest();
x.open('GET','/api/v1/drafts?limit=5',false);
x.send();
if(x.status!==200) return 'ERROR:'+x.status;
var posts=(JSON.parse(x.responseText).posts||[]);
if(!posts.length) return 'NO_DRAFTS';
var x2=new XMLHttpRequest();
x2.open('GET','/api/v1/drafts/'+posts[0].id,false);
x2.send();
if(x2.status!==200) return 'ERROR2:'+x2.status;
var d=JSON.parse(x2.responseText);
var bl=(d.postBylines||d.bylines||[]);
if(bl.length) return String(bl[0].user_id);
return 'NOT_FOUND';
})()""")
    if result.startswith("ERROR") or result in ("NOT_FOUND", "NO_DRAFTS"):
        raise RuntimeError(f"Could not determine author user_id: {result}")
    return int(result)


def upload_image(image_path: str) -> str:
    """Upload a local image to Substack CDN. Returns the CDN URL."""
    img_bytes = Path(image_path).read_bytes()
    b64 = base64.b64encode(img_bytes).decode()
    mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

    js = (
        "(function(){"
        f"var b64='{b64}';"
        f"var payload=JSON.stringify({{image:'data:{mime};base64,'+b64,mime_type:'{mime}'}});"
        "var x=new XMLHttpRequest();"
        "x.open('POST','/api/v1/image',false);"
        "x.setRequestHeader('Content-Type','application/json');"
        "x.send(payload);"
        "if(x.status!==200) return 'ERROR:'+x.status+'|'+x.responseText.substring(0,200);"
        "return JSON.parse(x.responseText).url||'NO_URL';"
        "})()"
    )
    result = arc_js(js, timeout=60)
    if result.startswith("ERROR"):
        raise RuntimeError(f"Image upload failed for {image_path}: {result}")
    return result


def substitute_images_in_prosemirror(pm: dict, cdn_map: dict) -> dict:
    """Walk the Prosemirror tree and replace local image src with CDN URLs."""
    if not cdn_map:
        return pm

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "image2":
                src = node.get("attrs", {}).get("src", "")
                # Try exact match, then basename match
                new_src = cdn_map.get(src) or cdn_map.get(Path(src).name)
                if new_src:
                    node["attrs"]["src"] = new_src
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pm)
    return pm


def create_draft(title: str, subtitle: str, pm_doc: dict, author_id: int) -> dict:
    """POST /api/v1/drafts with Prosemirror JSON body. Returns {id, url}."""
    # draft_body must be a JSON string (Prosemirror doc serialized to string)
    prosemirror_str = json.dumps(pm_doc, ensure_ascii=True)

    payload = json.dumps({
        "draft_title": title,
        "draft_subtitle": subtitle,
        # draft_body is a JSON-encoded STRING, not an object
        "draft_body": prosemirror_str,
        "draft_bylines": [{"id": author_id}],
        "type": "newsletter",
        "audience": "everyone",
        "section_chosen": True,
        "should_send_email": False,
    }, ensure_ascii=True)  # ensure_ascii=True → all chars are ASCII, safe for atob() round-trip

    b64_payload = base64.b64encode(payload.encode("ascii")).decode()

    # Use TextDecoder to properly handle the binary string from atob()
    js = (
        "(function(){"
        f"var b64='{b64_payload}';"
        "var raw=atob(b64);"
        "var bytes=new Uint8Array(raw.length);"
        "for(var i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);"
        "var decoded=new TextDecoder('utf-8').decode(bytes);"
        "var x=new XMLHttpRequest();"
        "x.open('POST','/api/v1/drafts',false);"
        "x.setRequestHeader('Content-Type','application/json; charset=utf-8');"
        "x.send(decoded);"
        "if(x.status!==200) return 'ERROR:'+x.status+'|'+x.responseText.substring(0,300);"
        "var d=JSON.parse(x.responseText);"
        "return JSON.stringify({id:d.id,url:d.canonical_url});"
        "})()"
    )
    result = arc_js(js, timeout=30)
    if result.startswith("ERROR"):
        raise RuntimeError(f"Draft creation failed: {result}")
    return json.loads(result)


# ── Editor context setup ──────────────────────────────────────────────────────

def ensure_editor_context(page_load_wait: int = 12, poll_timeout: int = 20) -> bool:
    """Open the editor URL, wait for the SPA to initialize, then verify API access."""
    arc_open_url(EDITOR_URL)
    print(f"[publish] Waiting {page_load_wait}s for editor page to load...", flush=True)
    time.sleep(page_load_wait)

    deadline = time.time() + poll_timeout
    while time.time() < deadline:
        try:
            status = arc_js(
                "(function(){var x=new XMLHttpRequest();"
                "x.open('GET','/api/v1/drafts?limit=1',false);"
                "x.send();return String(x.status);})()",
                timeout=10,
            )
            if status.strip() == "200":
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preprocessed", required=True, help="JSON from preprocess.py")
    args = parser.parse_args()

    data = json.loads(Path(args.preprocessed).read_text())
    title      = data.get("title", "Untitled")
    subtitle   = data.get("subtitle", "") or ""
    pm_doc     = data.get("prosemirror")
    images     = data.get("images", [])
    source_dir = Path(data.get("source_dir", ".")).resolve()

    if not pm_doc:
        print("ERROR: preprocessed JSON missing 'prosemirror' field. "
              "Re-run preprocess.py to regenerate.", file=sys.stderr)
        sys.exit(1)

    # Substack renders title and subtitle separately above the body via draft_title/draft_subtitle.
    # Strip the leading h1 (title) and any immediately following h3 (subtitle) from the body.
    body = pm_doc.get("content", [])
    if body and body[0].get("type") == "heading" and body[0].get("attrs", {}).get("level") == 1:
        body = body[1:]
    if body and body[0].get("type") == "heading" and body[0].get("attrs", {}).get("level") == 3:
        body = body[1:]
    pm_doc["content"] = body

    print(f"[publish] Source: {title[:60]}")
    print(f"[publish] Opening publication context in Arc: {EDITOR_URL}")

    if not ensure_editor_context():
        print(f"ERROR: Could not reach Substack API at {PUBLICATION_HOST}. "
              "Are you logged in?", file=sys.stderr)
        sys.exit(1)

    print("[publish] API context ready. Fetching author id...")
    author_id = get_author_id()
    print(f"[publish] Author user_id: {author_id}")

    # Upload images and build CDN URL map
    cdn_map: dict[str, str] = {}
    for img_path in images:
        local = Path(img_path)
        if not local.is_absolute():
            local = source_dir / img_path
        if not local.exists():
            print(f"[publish] WARNING: image not found: {local}", file=sys.stderr)
            continue
        print(f"[publish] Uploading {local.name} ({local.stat().st_size // 1024}KB)...")
        try:
            cdn_url = upload_image(str(local))
            cdn_map[str(img_path)] = cdn_url
            cdn_map[local.name] = cdn_url
            print(f"[publish] Uploaded → {cdn_url[:70]}...")
        except RuntimeError as e:
            print(f"[publish] WARNING: upload failed ({e}), image will be missing.",
                  file=sys.stderr)

    # Substitute CDN URLs inside the Prosemirror document tree
    substitute_images_in_prosemirror(pm_doc, cdn_map)

    print("[publish] Creating Substack draft...")
    draft = create_draft(title, subtitle, pm_doc, author_id)
    draft_id = draft.get("id")

    if draft_id:
        dashboard_url = f"https://substack.com/dashboard/post/{draft_id}"
    else:
        dashboard_url = f"https://{PUBLICATION_HOST}/publish/post/new"
        print("[publish] WARNING: no draft id in response", file=sys.stderr)

    output = {
        "draft_id": draft_id,
        "dashboard_url": dashboard_url,
        "cdn_images": cdn_map,
        "title": title,
    }
    print(json.dumps(output, indent=2))
    print(f"\n[publish] Draft created. Review (do NOT publish): {dashboard_url}")

    subprocess.run(["open", dashboard_url])


if __name__ == "__main__":
    main()
