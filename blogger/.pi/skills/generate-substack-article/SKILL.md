---
name: generate-substack-article
description: Create a technically grounded long-form article for SubStack or Medium audiences. Informative and precise, with data-backed arguments and clear explanations of mechanism.
---

Create a SubStack/Medium article and save to `output/substack-article.md`.

## Step 1: Resolve Input

Check in order. Use the first that exists:
1. `output/teaching-article.md` — read in sections of 100 lines. Extract and hold in working memory: thesis (1 sentence), core mechanism (3-5 bullets), top 3 benchmark numbers, strongest objection. Do not re-read during writing.
2. `output/extracted-source.md` — read in sections, extracting the same fields. Hold compact version in context.
3. No source found: use `/skill:ingest-content` then `/skill:generate-teaching-article` first.

## Step 2: Write the Article

Target: **1500–2500 words**. Adhere to every writing constraint in the system prompt.

**Hard rules — enforce throughout every sentence:**
- No semicolons. No em-dashes (—). Periods and commas only.
- Vary sentence length drastically: short punchy sentences mixed with longer ones.
- Active voice. No intro filler. End abruptly when the point is made.

### Required Structure

```
# [Headline: names the technical contribution or finding precisely. No hype.]
### [Subtitle: one line expanding on what the reader will learn]

[Opening: Start with a concrete number, a specific failure mode, or a problem statement
 that grounds the reader. Do not start with "I" or with a generic statement about AI.
 2-4 sentences maximum.]

[Thesis paragraph: State the core claim explicitly. What does this work establish or change?
 One paragraph. No hedging, but no overreach either.]

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

## Step 2b: Add References

If the source material contains a references or bibliography section, append a `## References` section at the end of the article. Include only the source paper and any works directly named in the article body. Format each as a markdown link on its own line:

```
[<Brief Title> White Paper](https://arxiv.org/abs/<id>)
```

Use arXiv links where available. Omit author lists, venues, and dates. If no references exist in the source, omit this section entirely.

## Step 3: Generate Visuals

Use `/skill:create-visualization` for:
- 1 AI image placeholder for the feature/header image: `<!-- AI-IMAGE: [detailed prompt] -->`
- 1 data visualization (Python chart) for the evidence section → `output/substack-visuals/`
- 1 mermaid diagram for the mechanism section

**Image rule:** Only reference a `![...](substack-visuals/filename.png)` if you actually ran `generate_graph.py` in this session and the file exists. If you cannot run the script, use `<!-- AI-IMAGE: [prompt] -->` instead. Never invent a PNG path for a file you have not created.

## Step 4: Validate Diagrams

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py output/substack-article.md
```

If issues are reported, fix the flagged mermaid blocks (refer to `/skill:create-visualization` syntax rules) and re-validate.

## Step 5: Chain

If the user asked for all 3 formats, use `/skill:generate-linkedin-post` next.
