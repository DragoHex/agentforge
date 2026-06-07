---
name: generate-linkedin-post
description: Create a concise, informative LinkedIn post from source content. Grounded in the technical substance, written for practitioners who value precision over hype.
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

**Hard rules — enforce throughout every sentence:**
- No semicolons. No em-dashes (—). Periods and commas only.
- Vary sentence length drastically: short punchy sentences mixed with longer ones.
- Active voice. No intro filler. End abruptly when the point is made.

### Format Rules

LinkedIn renders plain text, not markdown. Follow these rules exactly:
- No `#` headers, no `**bold**`, no `- bullet` dashes
- One idea per line
- Blank line between every paragraph
- Hashtags on the last line only

### Required Structure

```
[Hook: 1-2 lines. The core technical insight or the most counterintuitive finding.
 Lead with a specific claim, not a vague declaration. A stat can support it but should not stand alone.
 Concrete and specific. Not "AI is changing everything." Example:
 "You have been improving your agent by hand. That is gradient descent without a learning rate."]

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

[Substack reference — ONLY if a Substack URL was provided in the prompt:
 "For a deeper dive, the full breakdown is on Substack: <url>"
 Omit this line entirely if no URL was given.]

[Blank line]

#[Hashtag1] #[Hashtag2] #[Hashtag3]
```

Use 3–5 hashtags. Mix one broad tag (#AI or #MachineLearning) with specific ones (#AgentSystems, #LLM, topic-specific).

## Step 3: Generate Visual

Use `/skill:create-visualization` for one strong visual:
- Prefer a clean bar chart comparing the key metric across methods
- Or a mermaid diagram if numeric data is absent
- Save to `output/linkedin-visuals/`

**Image rule:** Only reference a `![...](linkedin-visuals/filename.png)` if you actually ran the chart script in this session and the file exists. If you cannot run the script, use `<!-- AI-IMAGE: [prompt] -->` instead. Never invent a PNG path for a file you have not created.

## Step 4: Validate Diagrams

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py output/linkedin-post.md
```

If issues are reported, fix the flagged mermaid blocks (refer to `/skill:create-visualization` syntax rules) and re-validate.
