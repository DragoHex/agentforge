---
name: generate-substack-article
description: Create a narrative long-form article for SubStack or Medium audiences. Story-driven, data-backed, with visual storytelling and pull quotes.
---

Create a SubStack/Medium article and save to `output/substack-article.md`.

## Step 1: Resolve Input

Check in order. Use the first that exists:
1. `output/teaching-article.md` — read in sections of 100 lines. Extract and hold in working memory: thesis (1 sentence), core mechanism (3-5 bullets), top 3 benchmark numbers, strongest objection. Do not re-read during writing.
2. `output/extracted-source.md` — read in sections, extracting the same fields. Hold compact version in context.
3. No source found: use `/skill:ingest-content` then `/skill:generate-teaching-article` first.

## Step 2: Write the Article

Target: **1500–2500 words**. Adhere to every writing constraint in the system prompt.

### Required Structure

```
# [Compelling headline that promises a specific, surprising insight]
### [Subtitle: one line expanding on what the reader will learn]

[Opening: Start with a scene, a specific moment, or a concrete number that creates tension.
 Do not start with "I" or with a generic statement about AI. 2-4 sentences maximum.]

[Thesis paragraph: State the big idea explicitly. What does this work prove or break?
 One paragraph. No hedging.]

## [Section 1 title — establish the problem]
[What was the accepted approach before? Why was it insufficient? Include a chart or
 trend visualization if numeric data supports it.]

## [Section 2 title — the mechanism]
[Walk through how the solution works. Name every component. Use a diagram.
 Embed a pull quote from the source material or a sharp paraphrase of the core insight.]

> "Pull quote capturing the single sharpest idea from this section."

## [Section 3 title — the evidence]
[Present results. Exact numbers. Comparisons to competing approaches.
 What does beating X by Y points on Z benchmark actually mean in practice?]

## [Section 4 title — implications or counter-argument]
[What does this change? Address the most obvious objection honestly.
 Do not dismiss it. Show both what holds and what remains uncertain.]

[Closing: Circle back to the opening scene or number. End on something the reader can
 act on or remember. No summary recap. No moral lesson. Abrupt is fine.]
```

## Step 3: Generate Visuals

Use `/skill:create-visualization` for:
- 1 AI image placeholder for the feature/header image: `<!-- AI-IMAGE: [detailed prompt] -->`
- 1 data visualization (Python chart) for the evidence section → `output/substack-visuals/`
- 1 mermaid diagram for the mechanism section

Reference saved visuals with relative paths from `output/`:
```markdown
![Caption](substack-visuals/filename.png)
```

## Step 4: Validate Diagrams

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py output/substack-article.md
```

If issues are reported, fix the flagged mermaid blocks (refer to `/skill:create-visualization` syntax rules) and re-validate.

## Step 5: Chain

If the user asked for all 3 formats, use `/skill:generate-linkedin-post` next.
