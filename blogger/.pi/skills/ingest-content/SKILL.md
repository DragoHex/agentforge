---
name: ingest-content
description: Extract text from PDF files, webpages, and text documents. Use this skill first when the user provides source material for article generation.
---

Extract raw content from the source and save to disk. Do not load the full extracted text into context.

**CRITICAL: PDF files are binary. NEVER use the `read` tool on a `.pdf` file. ALWAYS run the bash extraction script below.**

## Step 1: Run Extraction

**PDF:**
```bash
source venv/bin/activate && python3 .pi/skills/ingest-content/extract_pdf.py "<path>" --output output/extracted-source.md
```

**Webpage:**
```bash
source venv/bin/activate && python3 .pi/skills/ingest-content/extract_webpage.py "<url>" --output output/extracted-source.md
```

**Text/Markdown file:** Copy or rename to `output/extracted-source.md`.

## Step 2: Verify

Confirm the script printed a success message and the file exists. Read only the `## Metadata` block (first ~15 lines) to verify page count and source. Do not read the full content into context.

## Step 3: Chain

Tell the user the extraction is complete, then proceed to the requested format:

- Full pipeline: use `/skill:generate-teaching-article`
- Teaching only: use `/skill:generate-teaching-article`
- Substack only: use `/skill:generate-substack-article`
- LinkedIn only: use `/skill:generate-linkedin-post`

Each downstream skill reads the source file on-demand using the read tool.
