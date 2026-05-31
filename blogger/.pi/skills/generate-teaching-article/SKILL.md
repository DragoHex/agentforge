---
name: generate-teaching-article
description: Create a detailed educational deep-dive from source content. Includes explanations, mermaid diagrams, data visualizations, benchmark tables, glossary, and practice exercises for classroom or self-study use.
---

Create a teaching article and save to `output/teaching-article.md`.

## Step 1: Resolve Input

**NEVER read a `.pdf` file directly — PDF files are binary. Use `output/extracted-source.md` (already extracted text).**

Check in order. Use the first that exists:
1. `output/extracted-source.md` — read it section by section using the read tool (read in chunks of ~100 lines at a time to avoid context overflow)
2. A `.md` or `.txt` file the user specified directly
3. No text source found: use `/skill:ingest-content` first to extract to `output/extracted-source.md`

## Step 2: Write the Article

Save to `output/teaching-article.md`. Adhere to every writing constraint in the system prompt.

### Required Structure

```
# [Topic]: A Complete Teaching Guide

## Learning Objectives
2-4 specific, measurable objectives.

## Prerequisites
What the reader must know first.

## Core Concept
Define it from first principles. State why it matters with one concrete real-world consequence.

## Algorithm / Mechanism Walkthrough
Step-by-step breakdown of every named component in the source. No component omitted.
Include a mermaid flowchart of the full process.

## Technical Deep Dive  (3-5 subsections)
Layer complexity progressively. Each subsection: explain the idea, show a concrete example,
note edge cases or failure modes. Cover every technique mentioned in the source.

## Benchmark Results
Reproduce every quantitative result from the source as a markdown table.
Format: | Method | Metric | Value | Notes |
Do not paraphrase numbers. Copy exact figures.

## Practical Example
One worked example from start to finish, tracing through the full mechanism.

## Visual Walkthrough
Embed all diagrams here. Reference Python-generated charts by their saved path.
Visual paths must be relative to output/: e.g. teaching-visuals/chart.png

## Ablations & Analysis
Cover every ablation or sensitivity study in the source. What breaks when each component is removed?

## Glossary
One-line definition for every technical term introduced. Alphabetical order.

## Key Takeaways
5-7 bullet points. Each one a complete, precise sentence.

## Practice Exercises
3-5 exercises ranging from recall to application to design.
```

## Step 3: Generate Visuals

Use `/skill:create-visualization` for:
- 1 mermaid architecture or process diagram (embed in Algorithm section)
- 1 mermaid flowchart or sequence diagram (embed in Deep Dive)
- 1 Python chart (Plotly/Seaborn) for any numeric benchmark data → save to `output/teaching-visuals/`
- AI image placeholder for any complex conceptual illustration: `<!-- AI-IMAGE: [detailed prompt] -->`

Reference all saved visuals with relative paths from `output/`:
```markdown
![Chart Title](teaching-visuals/filename.png)
```

## Step 4: Validate Diagrams

```bash
source venv/bin/activate && python3 .pi/skills/validate-diagrams/validate_diagrams.py output/teaching-article.md
```

If issues are reported, fix the flagged mermaid blocks (refer to `/skill:create-visualization` syntax rules) and re-validate.

## Step 5: Chain

If the user asked for all 3 formats, use `/skill:generate-substack-article` next.
