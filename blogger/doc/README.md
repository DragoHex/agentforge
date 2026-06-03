# Pi Agent Article Generator

A set of skills and scripts for the [Pi coding agent](https://pi.dev) that ingest source material (PDFs, webpages, documents) and generate polished articles in three formats: Teaching, SubStack/Medium, and LinkedIn.

## Directory Structure

```
blogger/
├── AGENTS.md                          # Writing system prompt + 4-step workflow
├── SkillOpt.pdf                       # Test PDF for validation
├── venv/                              # Python virtual environment
├── .pi/
│   ├── prompts/
│   │   ├── teaching.md
│   │   ├── substack.md
│   │   └── linkedin.md
│   └── skills/
│       ├── ingest-content/            # PDF + webpage ingestion
│       │   ├── SKILL.md
│       │   ├── extract_pdf.py
│       │   └── extract_webpage.py
│       ├── generate-teaching-article/SKILL.md
│       ├── generate-substack-article/SKILL.md
│       ├── generate-linkedin-post/SKILL.md
│       ├── create-visualization/      # Mermaid/Plotly/Excalidraw
│       │   ├── SKILL.md
│       │   └── generate_graph.py
│       └── validate-diagrams/
│           ├── SKILL.md
│           └── validate_diagrams.py
├── templates/
│   ├── teaching-template.md           # Teaching article structure
│   ├── substack-template.md           # SubStack article structure
│   └── linkedin-template.md           # LinkedIn post structure
├── doc/
│   └── README.md                     # This file
└── output/
    ├── extracted-source.md            # Extracted source content
    ├── teaching-article.md            # Generated teaching article
    ├── substack-article.md            # Generated SubStack/Medium article
    ├── linkedin-post.md               # Generated LinkedIn post
    ├── teaching-visuals/              # Visuals for teaching article
    ├── substack-visuals/              # Visuals for SubStack article
    └── linkedin-visuals/             # Visuals for LinkedIn post
```

## Workflow

The agent follows 4 sequential steps:

1. **Ingest** - Extract content from the source (PDF, webpage, or document) using the `ingest-content` skill
2. **Generate Teaching Article** - Create a detailed educational deep-dive with diagrams and visualizations
3. **Generate SubStack/Medium Article** - Create a narrative long-form article for public audiences
4. **Generate LinkedIn Post** - Create a concise, scannable post optimized for the LinkedIn feed

Each step reads the previous step's full output directly: `extracted-source.md` → `teaching-article.md` → `substack-article.md` → `linkedin-post.md`.

## Skills

### ingest-content
Extracts raw text and structure from PDFs, webpages, and text files.

- **PDF**: `source venv/bin/activate && python3 .pi/skills/ingest-content/extract_pdf.py <path> --output output/extracted-source.md`
- **Webpages**: `source venv/bin/activate && python3 .pi/skills/ingest-content/extract_webpage.py <url> --output output/extracted-source.md`
- **Text**: Use the Pi read tool directly

Uses PyMuPDF (falling back to pdfplumber, then pypdf) for PDFs and readability-lxml (falling back to newspaper3k, then basic HTML parsing) for webpages.

### generate-teaching-article
Creates educational deep-dives with:
- Learning objectives and prerequisites
- Progressive complexity from first principles
- Concrete examples for every abstract idea
- Mermaid diagrams, data visualizations, and concept maps
- Practice exercises

### generate-substack-article
Creates engaging long-form content with:
- Narrative-driven structure (story → insight → implications)
- Data and evidence woven into the story
- Pull quotes, callout boxes, and visual breaks
- Strong opening and closing that circles back

### generate-linkedin-post
Creates professional LinkedIn posts with:
- Hook line with the single most surprising insight
- 3-5 short, scannable paragraphs
- One strong visualization
- Call-to-action or question to drive engagement

### create-visualization
Generates visual content using:
- **Mermaid diagrams** - Flowcharts, sequence diagrams, timelines, mindmaps (embedded in markdown)
- **Plotly/Seaborn (Python)** - Bar, line, scatter, pie, heatmap, histogram, box plots (saved as PNG)
- **Excalidraw** - Hand-drawn style diagrams (JSON files)
- **AI Image Placeholder** - `<!-- AI-IMAGE: prompt -->` for complex illustrations

## Writing Constraints

The system prompt enforces a natural, human voice:
- **No semicolons (;)** or em-dashes (—)
- **No banned words**: delve, tapestry, testament, beacon, "in conclusion", "it is important to note", furthermore, moreover, "navigating the complexities", landscape
- **Varied sentence lengths**: Mix short (3-6 word) and long sentences. Avoid symmetrical paragraph lengths.
- **Active voice, conversational tone, impeccable grammar**
- **No fluff**: No introductory filler or preachy wrap-ups. Start directly, end abruptly.

## Python Dependencies

All dependencies are installed in the `venv/` directory:

```
pypdf pdfplumber PyMuPDF        # PDF extraction
plotly seaborn matplotlib pandas  # Data visualization
kaleido                          # Static image export from Plotly
```

Activate: `source venv/bin/activate`

## Usage

### With Pi Agent

```bash
cd /Users/msp/repo/agentforge/blogger

# Full pipeline via run.sh
./run.sh all SkillOpt.pdf

# Individual steps
./run.sh ingest SkillOpt.pdf
./run.sh teaching
./run.sh substack
./run.sh linkedin
```

### Standalone Scripts

```bash
# Activate venv first
source venv/bin/activate

# Extract PDF
python3 .pi/skills/ingest-content/extract_pdf.py SkillOpt.pdf --output output/extracted-source.md

# Extract webpage
python3 .pi/skills/ingest-content/extract_webpage.py "https://example.com/article" --output output/extracted-source.md

# Generate a chart
python3 .pi/skills/create-visualization/generate_graph.py --type bar --title "Performance Comparison" \
  --data '[{"label":"GPT-5.5","value":82.3},{"label":"GPT-5.4","value":70.1},{"label":"Qwen3.5","value":60.2}]' \
  --output output/chart.png
```

## Verification

- **PDF extraction**: Tested with SkillOpt.pdf (27 pages) - all text extracted with page markers ✓
- **Graph generation**: Bar chart test produced 1400x1000 PNG (52KB) ✓
- **Pi agent integration**: Skills follow the `SKILL.md` format, auto-discovered from `.pi/skills/`

## Article Categories

| Category | Audience | Style | Length | Visuals |
|----------|----------|-------|--------|---------|
| Teaching | Students | Explanatory, first principles | Long | 3+ diagrams, charts, exercises |
| SubStack/Medium | Public readers | Narrative, engaging | Medium-Long | 2+ visuals, pull quotes |
| LinkedIn | Professionals | Concise, scannable | Short | 1 strong visual, hashtags |

## File Formats

- Articles are saved as Markdown (`.md`) files
- Graphs are saved as PNG images
- Mermaid diagrams are embedded as ```mermaid code blocks
- Excalidraw files are saved as `.excalidraw` JSON
- Complex image placeholders use `<!-- AI-IMAGE: prompt -->` comments
