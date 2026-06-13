# Publish Draft: Plan

## Goal

Convert a generated markdown article into a Substack draft using the existing Pi MCP
infrastructure. No posting. Only drafts.

---

## Approach: pi-mcp-adapter + @playwright/mcp

`pi-mcp-adapter` is already installed globally. Adding `@playwright/mcp` via `.pi/mcp.json`
gives the Pi agent a set of browser automation tools without any custom TypeScript code.

Authentication reuses the Playwright MCP persistent browser profile. The user logs in once
via the visible browser window. The session is preserved across runs.

Image upload and draft creation happen via `browser_run_code_unsafe`, which runs a
Playwright Node.js script inside the already-authenticated browser context. No cookie
extraction, no Keychain access, no Arc dependency.

---

## Why Not a Python Script with API calls?

Arc encrypts its cookies with a macOS Keychain key. `browser-cookie3` does not support Arc
natively. Extracting those cookies reliably requires either profile-level hacking or
launching Arc with remote debugging enabled — both are fragile. The MCP approach solves
authentication by letting the user log in once in a visible browser and reusing the session.

---

## Architecture

```
run.sh draft substack output/substack-article.md
    │
    ├─ Python pre-processing (no LLM, no browser)
    │   preprocess.py:
    │     - renders mermaid code blocks → PNG via mmdc
    │     - converts markdown → HTML
    │     - writes output/draft-preprocessed.json
    │
    └─ Pi agent with @playwright/mcp (pi-mcp-adapter)
         │
         ├─ browser_navigate → substack.com → verify login
         │
         ├─ browser_run_code_unsafe
         │     reads draft-preprocessed.json via Node.js fs
         │     uploads each PNG via fetch() in page context
         │     creates draft via POST /api/v1/post
         │     returns { id, draft_url, dashboard_url }
         │
         └─ browser_navigate → dashboard URL → verify draft (not published)
```

---

## Files

| File | Purpose |
|---|---|
| `.pi/mcp.json` | Project MCP config: adds @playwright/mcp |
| `.pi/skills/publish-draft/SKILL.md` | Pi skill: guides agent through all steps |
| `.pi/skills/publish-draft/preprocess.py` | Mermaid→PNG, markdown→HTML, writes JSON |
| `run.sh draft` | Calls preprocess.py then run_pi with the skill |
| `run.sh draft-auth` | One-time Substack login via visible browser |

---

## Pre-processing: What preprocess.py Does

Input: a markdown file (e.g. `output/substack-article.md`)

1. Finds all ` ```mermaid ``` ` blocks, calls `mmdc` to render each to PNG.
   Replaces the block with `![Diagram](path/to/mermaid-HASH.png)`.
2. Replaces `<!-- AI-IMAGE: [...] -->` placeholders with italic captions (skipped).
3. Replaces `.excalidraw` image references with a placeholder note (not yet auto-converted).
4. Converts the processed markdown to HTML.
5. Writes `output/draft-preprocessed.json`:
   ```json
   {
     "title": "...",
     "subtitle": "...",
     "html": "<p>...</p>",
     "images": ["output/substack-visuals/main-benchmarks.png", ...]
   }
   ```

---

## Substack Draft Creation

The Pi agent navigates to `substack.com` and executes a single `browser_run_code_unsafe`
call that:

1. Reads `output/draft-preprocessed.json` via Node.js `fs`
2. For each image path, reads the file, converts to base64, uploads via
   `fetch('/api/v1/image', ...)` from within the authenticated page context
3. Substitutes CDN URLs in the HTML
4. POSTs to `/api/v1/post` with `draft_title`, `draft_body`, etc.
5. Returns `{ id, canonical_url }` — the draft URL

The agent then navigates to the dashboard URL to verify the draft is saved and not published.

---

## Diagram Conversion Status

| Type | Handled |
|---|---|
| Mermaid code blocks | Yes — mmdc renders to PNG |
| Existing PNG files | Yes — uploaded directly |
| Excalidraw `.excalidraw` files | Stub — logs warning, inserts text placeholder |
| `<!-- AI-IMAGE: ... -->` | Stripped — becomes italic caption |

Excalidraw auto-conversion is deferred. The files exist in `teaching-visuals/` and are not
referenced in the substack or linkedin articles.

---

## Validation

Run:
```bash
./run.sh draft substack output/substack-article.md
```

Expected:
1. `preprocess.py` renders the mermaid flowchart to `output/draft-assets/mermaid-*.png`
2. Browser opens, shows Substack (logged in)
3. Image uploaded to Substack CDN
4. Draft created — `dashboard_url` returned
5. Browser navigates to draft — confirms status is "Draft", not "Published"

**Never run `./run.sh draft` with `--publish` flag or equivalent. That flag does not exist
intentionally.**
