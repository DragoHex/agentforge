---
name: generate-linkedin-post
description: Create a concise, scannable LinkedIn post from source content. Optimized for feed engagement with hook line, short paragraphs, one visual, and a call-to-action.
---

Create a LinkedIn post and save to `output/linkedin-post.md`.

## Step 1: Resolve Input

Check in order. Use the first that exists:
1. `output/substack-article.md` — read it fully. Extract: hook stat, 2-sentence context, 1 takeaway.
2. `output/teaching-article.md` — read Key Takeaways and Benchmark Results sections only.
3. `output/extracted-source.md` — read abstract/introduction only.
4. No source found: use `/skill:ingest-content` then return here.

## Step 2: Write the Post

Target: **150–250 words**. Save to `output/linkedin-post.md`.

### Format Rules

LinkedIn renders plain text, not markdown. Follow these rules exactly:
- No `#` headers, no `**bold**`, no `- bullet` dashes
- One idea per line
- Blank line between every paragraph
- Hashtags on the last line only

### Required Structure

```
[Hook: 1-2 lines. The single most surprising number, claim, or reversal.
 Concrete and specific. Not "AI is changing everything." Example:
 "A 27B model with a self-editing skill file just beat GPT-5.5 on 6 benchmarks."]

[Blank line]

[Paragraph 1 — context: Why does this matter? Who cares and why should they?
 2-3 lines maximum.]

[Blank line]

[Paragraph 2 — the mechanism or evidence: One data point or one crisp explanation.
 Not a list. Flowing sentences. 2-3 lines.]

[Blank line]

[Paragraph 3 — practical takeaway: What should the reader do or think differently?
 Keep it grounded. 1-2 lines.]

[Blank line]

[Visual reference — one chart, diagram, or image]

[Blank line]

[Closing question or CTA: Invite a reaction. One line. Ends with a question mark.]

[Blank line]

#[Hashtag1] #[Hashtag2] #[Hashtag3]
```

Use 3–5 hashtags. Mix one broad tag (#AI or #MachineLearning) with specific ones (#AgentSystems, #LLM, topic-specific).

## Step 3: Generate Visual

Use `/skill:create-visualization` for one strong visual:
- Prefer a clean bar chart comparing the key metric across methods
- Or a mermaid diagram if numeric data is absent
- Save to `output/linkedin-visuals/`

Reference with relative path from `output/`:
```markdown
![Caption](linkedin-visuals/filename.png)
```

## Step 4: Validate Diagrams

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py output/linkedin-post.md
```

If issues are reported, fix the flagged mermaid blocks (refer to `/skill:create-visualization` syntax rules) and re-validate.
