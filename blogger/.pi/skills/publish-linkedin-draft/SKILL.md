---
name: publish-linkedin-draft
description: Prepare a LinkedIn post draft from a markdown file. Copies the text to the clipboard and opens Arc on the LinkedIn feed with step-by-step instructions to paste and save as draft. Runs `./run.sh draft-linkedin [file]`. Never publishes.
---

# Skill: publish-linkedin-draft

Prepare a LinkedIn draft post from a local markdown file.
**Never publishes.** The user must explicitly click "Post" to publish; the script
only opens the feed and provides clipboard content.

## Why not fully automated?

LinkedIn migrated its post-creation system to Next.js RSC server actions in 2025.
The previous Voyager API endpoints (`/voyager/api/shares`, `/ugcPosts`, `normShares`)
no longer exist. The "Start a post" modal also requires a real user click
(`isTrusted=true`); programmatic JS events are ignored.

The script gets you 90% of the way there in seconds. The user completes the last
3 steps manually.

## When to Use

When the user asks to draft a LinkedIn post or push a post file to LinkedIn for review.

## Requirements

- Arc browser running and logged into `linkedin.com`
- Python venv active (`source venv/bin/activate`)

---

## Step 1: Run the draft helper

```bash
source venv/bin/activate && python3 -u .pi/skills/publish-linkedin-draft/publish_linkedin.py \
  --input output/linkedin-post.md
```

Pass a different file with `--input <path>` if needed.

---

## Step 2: Tell the user what to do in Arc

The script prints numbered instructions. Relay them to the user:

1. In the Arc tab that just opened (LinkedIn feed), click **"Start a post"**
2. Press **Cmd+V** to paste the copied text
3. If there are images: click the **image icon** and select the listed file(s)
4. Click **X** to close the dialog — LinkedIn will ask "Save as draft?" — click **Save**

**Do NOT click "Post".**

---

## Error Handling

- `ERROR: Input file not found`: Verify the path passed to `--input`.
- `WARNING: pbcopy failed`: Ask the user to manually copy the text from `output/linkedin-post.md`.
- `WARNING: image not found`: The image path in the markdown doesn't point to an existing file.
  Check that the generate-linkedin-post skill ran and created the visual.
