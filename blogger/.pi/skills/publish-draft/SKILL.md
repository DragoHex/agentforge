# Skill: publish-draft

Create a DRAFT post on Substack from a local markdown article.
**Never publish.** The word "publish" must not appear in any API call body.

## When to Use
When the user asks to draft a Substack post, create a draft, or publish-as-draft
from an article file.

## Requirements
- `pi-mcp-adapter` loaded and `@playwright/mcp` available (configured in `.pi/mcp.json`)
- Python venv active (`source venv/bin/activate`)
- `mmdc` available (`npm install -g @mermaid-js/mermaid-cli`)

---

## Step 1: Pre-process the article

```bash
source venv/bin/activate && python3 .pi/skills/publish-draft/preprocess.py \
  --input <input_file> \
  --output output/draft-preprocessed.json
```

Read `output/draft-preprocessed.json`. Confirm:
- `title` is set
- `images` list is populated
- Any mermaid blocks were rendered to PNG

---

## Step 2: Open browser and verify Substack login

```
browser_navigate(url="https://substack.com")
```

Take a snapshot. If the page shows a sign-in form or login wall, tell the user to log in
via the visible browser, then wait and take another snapshot to confirm they are logged in.

---

## Step 3: Upload images and create the draft in one call

Use `browser_run_code_unsafe` with this script. Replace the working directory path
with the actual absolute path of the blogger project directory:

```javascript
const fs = require('fs');
const path = require('path');

async (page) => {
  const dataPath = path.resolve('output/draft-preprocessed.json');
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

  // Upload each image to Substack CDN
  const cdnMap = {};
  for (const imgPath of (data.images || [])) {
    try {
      const absPath = path.resolve(imgPath);
      const imgBytes = fs.readFileSync(absPath);
      const b64 = imgBytes.toString('base64');
      const cdnUrl = await page.evaluate(async (b64) => {
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: 'image/png' });
        const fd = new FormData();
        fd.append('file', blob, 'upload.png');
        const r = await fetch('/api/v1/image', {
          method: 'POST',
          credentials: 'include',
          body: fd
        });
        if (!r.ok) throw new Error(`Image upload failed: ${r.status}`);
        const j = await r.json();
        return j.url || j.imageUrl || '';
      }, b64);
      cdnMap[imgPath] = cdnUrl;
    } catch (e) {
      cdnMap[imgPath] = `ERROR:${e.message}`;
    }
  }

  // Substitute CDN URLs in the HTML
  let html = data.html;
  for (const [local, cdn] of Object.entries(cdnMap)) {
    if (!cdn.startsWith('ERROR:')) {
      html = html.split(local).join(cdn);
    }
  }

  // Create draft — do NOT set published: true
  const post = await page.evaluate(async (payload) => {
    const r = await fetch('/api/v1/post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`Draft creation failed: ${r.status} ${txt}`);
    }
    return await r.json();
  }, {
    draft_title: data.title,
    draft_subtitle: data.subtitle || '',
    draft_body: html,
    audience: 'everyone',
    type: 'newsletter',
    section_chosen: true
  });

  const draftId = post.id;
  const draftUrl = post.canonical_url || `https://substack.com/dashboard/post/${draftId}`;
  return JSON.stringify({ id: draftId, draft_url: draftUrl, images_uploaded: cdnMap });
}
```

Parse the returned JSON for `id` and `draft_url`.

---

## Step 4: Navigate to the draft

```
browser_navigate(url="https://substack.com/dashboard/post/<id>")
```

Take a snapshot to confirm:
- The post title matches
- The status is **Draft**, not Published

Report the dashboard URL to the user.

---

## Error Handling

- If `/api/v1/post` returns 401/403: Substack session has expired. Go back to Step 2 and ask
  the user to log in again.
- If `/api/v1/image` fails for an image: Log the error, skip that image, continue with
  the draft. Report which images failed at the end.
- If `browser_run_code_unsafe` is not available: Tell the user to ensure
  `--caps=browser_run_code_unsafe` is in `.pi/mcp.json`.
