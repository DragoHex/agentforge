# Pi Agent Article Generator

A set of Pi agent skills that ingest source material (PDFs, webpages) and generate polished articles in three formats: Teaching notes, SubStack/Medium long-form, and LinkedIn posts.

---

## Prerequisites

- **Pi CLI** — [pi.dev](https://pi.dev) (requires a real TTY; see note below)
- **Ollama** — running locally on `http://localhost:11434`
- **Python 3.10+** with the `venv/` virtualenv activated for scripts
- **expect** — `brew install expect` (used by `run.sh` to provide a TTY for Pi)

---

## Model Setup: blogger-gemma4

The workflow uses a custom Ollama model named `blogger-gemma4`, defined in `Modelfile`.

### Build the model

```bash
cd /Users/msp/repo/agentforge/blogger
./setup.sh
```

`setup.sh` pulls `gemma4:e4b` (if not already present) then creates the `blogger-gemma4` model. `ollama create` will also auto-pull the base model if missing, but pulling first gives clean progress output.

### Modelfile (reference copy lives in this directory)

```
FROM gemma4:e4b

PARAMETER num_ctx 128000
PARAMETER temperature 1.0
PARAMETER top_p 0.95
PARAMETER top_k 64
PARAMETER repeat_penalty 1.15

SYSTEM """
You are an expert academic research assistant specializing in deep-dive literature reviews.
Analyze the provided research paper thoroughly.
When asked for a summary, provide an expansive, deeply structured comprehensive breakdown.
Include explicit sections for: Core Methodology, Critical Variables, Novel Contributions,
Hidden Limitations, and Future Directives.
Do not truncate or over-simplify complex technical concepts.
"""
```

`num_ctx 128000` gives the full 128k context window. The temperature/top_p/top_k settings follow Google's recommended defaults for Gemma 4. `repeat_penalty 1.15` prevents repetition in long outputs.

### Verify the model

```bash
ollama list | grep blogger-gemma4
```

---

## Quick Start

```bash
cd /Users/msp/repo/agentforge/blogger

# Full pipeline: ingest PDF, generate all 3 formats
./run.sh all SkillOpt.pdf

# Full pipeline from a webpage
./run.sh ingest https://arxiv.org/abs/2310.01848
./run.sh all
```

---

## run.sh Reference

`run.sh` is the recommended entry point. It wraps `pi` with `expect` to satisfy Pi's TTY requirement, and runs diagram validation after each step.

```
Usage: ./run.sh <command> [args]

Commands:
  ingest <file|url>   Extract PDF or webpage to output/extracted-source.md
  teaching            Generate teaching article + Excalidraw architecture diagram
  substack            Generate SubStack article (reads compact-for-substack.md)
  linkedin            Generate LinkedIn post (reads compact-for-linkedin.md)
  validate [files]    Validate mermaid/Excalidraw syntax in output files
  all [file]          Run full pipeline (default source: SkillOpt.pdf)

Examples:
  ./run.sh all SkillOpt.pdf
  ./run.sh ingest https://arxiv.org/abs/2310.01848
  ./run.sh teaching                  # from existing extracted-source.md
  ./run.sh substack                  # from existing teaching article
  ./run.sh linkedin                  # from existing substack article
  ./run.sh validate                  # check all 3 output files
```

### Environment overrides

```bash
PI_MODEL=qwen3.6:27b-mlx ./run.sh all     # use heavier model
PI_THINKING=medium ./run.sh teaching      # more deliberate reasoning
  PI_THINKING=off ./run.sh linkedin         # fastest, prose only
PI_TIMEOUT=1200 ./run.sh teaching         # extend timeout (default: 900s)
```

---

## Thinking Level Guide

The default thinking level is `medium`. This is the right choice for most technical paper workflows.

Pi's valid levels (matched to Ollama): `off`, `low`, `medium`, `high`, `xhigh`.

| Level | When to use |
|-------|-------------|
| `off` | LinkedIn posts, prose-only rewrites. Maximum speed. |
| `low` | Light technical content, simple diagrams. |
| `medium` | **Default.** Science/math paper summarisation, diagram generation. Balanced accuracy and speed for technical papers. |
| `high` | Only if lower levels produce incorrect diagrams or wrong benchmark numbers. Expect 3-5x slower. |

For technical papers (physics, ML, biology, math) always use at least `minimal`. Mermaid and Excalidraw diagrams need the model to self-check coordinate consistency and node-ID uniqueness, which `off` skips.

---

## Direct Pi Invocation (without run.sh)

Pi requires a real TTY. From a proper terminal (not piped), run:

```bash
cd /Users/msp/repo/agentforge/blogger

# Full pipeline prompt
pi --provider ollama \
   --model blogger-gemma4 \
   --thinking minimal \
   --no-extensions \
   "Use /skill:ingest-content on SkillOpt.pdf, then generate teaching, substack, and linkedin articles."

# Single skill: teaching article only
pi --provider ollama \
   --model blogger-gemma4 \
   --thinking minimal \
   --no-extensions \
   "Read output/extracted-source.md in sections and generate a teaching article to output/teaching-article.md with all required sections. Prefer Excalidraw for architecture diagrams. No semicolons or em-dashes."

# Single skill: SubStack from existing teaching notes
pi --provider ollama \
   --model blogger-gemma4 \
   --thinking minimal \
   --no-extensions \
   "Use /skill:generate-substack-article. Input is output/teaching-article.md."

# Single skill: LinkedIn from existing SubStack article
pi --provider ollama \
   --model blogger-gemma4 \
   --thinking off \
   --no-extensions \
   "Use /skill:generate-linkedin-post. Input is output/substack-article.md."
```

### Why --no-extensions?

Pi reads `~/.cursor/mcp.json` at startup and tries to connect to every listed MCP server. On a cold start this adds 2-5 minutes of wait time for network timeouts. `--no-extensions` skips this entirely.

### Why expect in run.sh?

Pi checks whether stdout is a TTY before enabling its tool-use mode. When invoked from a script with pipes or shell redirection, it detects no TTY and behaves differently (buffered output, sometimes no file writes). `run.sh` uses `expect` to spawn Pi inside a pseudo-terminal, making it behave identically to an interactive session.

---

## Standalone Prompts (Interactive Pi Session)

Open a Pi session and paste these prompts directly:

### Full pipeline
```
Run /skill:ingest-content on SkillOpt.pdf, then /skill:generate-teaching-article,
then /skill:generate-substack-article, then /skill:generate-linkedin-post.
```

### Teaching article only (from a PDF)
```
Run /skill:ingest-content on SkillOpt.pdf, then /skill:generate-teaching-article.
```

### Teaching article from an already-extracted source
```
Run /skill:generate-teaching-article — it will read output/extracted-source.md.
```

### SubStack from teaching notes
```
Run /skill:generate-substack-article using output/compact-for-substack.md as input.
```

### LinkedIn from SubStack article
```
Run /skill:generate-linkedin-post using output/compact-for-linkedin.md as input.
```

### LinkedIn directly from a source (skipping other formats)
```
Run /skill:ingest-content on SkillOpt.pdf, then /skill:generate-linkedin-post.
```

**Note:** Skills use `/skill:name` syntax only in interactive Pi sessions. In scripted mode (`-p` flag), embed the skill instructions directly in the prompt, as `run.sh` does.

---

## Diagram Validation

Validation runs automatically as the last step of each skill. To run it manually:

```bash
source venv/bin/activate
python3 .pi/skills/validate-diagrams/validate_diagrams.py output/teaching-article.md
```

The validator checks:
- **Mermaid:** unquoted parentheses, reserved node IDs (`end`, `subgraph`), non-ASCII characters, complex edge labels
- **Excalidraw:** valid JSON, required element fields, valid element types, arrow `points` arrays

---

## Skills

### ingest-content
Extracts text from PDFs, webpages, and text documents. Saves to `output/extracted-source.md`. Does not load the full text into context.

| Source | Script |
|--------|--------|
| PDF | `source venv/bin/activate && python3 .pi/skills/ingest-content/extract_pdf.py <path> --output output/extracted-source.md` |
| Webpage | `source venv/bin/activate && python3 .pi/skills/ingest-content/extract_webpage.py <url> --output output/extracted-source.md` |

**CRITICAL: Never use the `read` tool on a `.pdf` file. PDFs are binary. Always run the extraction script first.**

### generate-teaching-article
Creates educational deep-dives: learning objectives, prerequisites, algorithm walkthrough, benchmark tables, glossary, exercises. Writes `output/teaching-article.md` and `output/compact-for-substack.md`.

### generate-substack-article
Creates narrative long-form content with a scene-setting opener, mechanism explanation, evidence section, and counter-argument. Writes `output/substack-article.md` and `output/compact-for-linkedin.md`.

### generate-linkedin-post
Creates a plain-text LinkedIn post (180-250 words). No markdown headers or bold. Writes `output/linkedin-post.md`.

### create-visualization
Generates visual content, choosing the right tool by content type:

| Content | Tool |
|---------|------|
| Architecture, concept maps | **Excalidraw** (preferred for visual appeal) |
| Numeric benchmark comparison | Plotly/Seaborn via `create-visualization/generate_graph.py` |
| Sequence or state machine | Mermaid `sequenceDiagram` / `stateDiagram-v2` |
| Complex scene or illustration | AI image placeholder |

---

## Writing Constraints (AGENTS.md)

| Rule | Detail |
|------|--------|
| No semicolons or em-dashes | Periods, commas, and colons only |
| No banned words | delve, tapestry, testament, beacon, "in conclusion", "it is important to note", furthermore, moreover, "navigating the complexities", landscape |
| Varied sentence length | Mix 3-6 word punchy sentences with longer ones. No symmetrical paragraphs |
| Active voice | Conversational, direct, impeccable grammar |
| No fluff | Start with content, end when the point is made |

---

## Standalone Scripts (no Pi required)

```bash
source venv/bin/activate

# Extract PDF
python3 .pi/skills/ingest-content/extract_pdf.py SkillOpt.pdf --output output/extracted-source.md

# Extract webpage
python3 .pi/skills/ingest-content/extract_webpage.py "https://arxiv.org/abs/2310.01848" --output output/extracted-source.md

# Generate bar chart
python3 .pi/skills/create-visualization/generate_graph.py --type bar --title "Benchmark Results" \
  --data '[{"label":"SkillOpt","value":82.3},{"label":"Baseline","value":60.1}]' \
  --output output/teaching-visuals/benchmark.png

# Generate grouped bar chart (multi-series)
python3 .pi/skills/create-visualization/generate_graph.py --type grouped_bar --title "Multi-Benchmark" \
  --data-file path/to/data.json --output output/teaching-visuals/multi-benchmark.png

# Validate diagrams
python3 .pi/skills/validate-diagrams/validate_diagrams.py output/teaching-article.md
```

---

## Directory Structure

```
blogger/
├── AGENTS.md                        # Writing constraints + skill list (system prompt)
├── Modelfile                        # blogger-gemma4 Ollama model definition
├── README.md                        # This file
├── setup.sh                         # Pull base model + create blogger-gemma4
├── run.sh                           # Pipeline runner (handles TTY via expect)
├── venv/                            # Python virtualenv
├── .pi/
│   ├── prompts/
│   │   ├── teaching.md
│   │   ├── substack.md
│   │   └── linkedin.md
│   └── skills/
│       ├── ingest-content/
│       │   ├── SKILL.md
│       │   ├── extract_pdf.py
│       │   └── extract_webpage.py
│       ├── generate-teaching-article/SKILL.md
│       ├── generate-substack-article/SKILL.md
│       ├── generate-linkedin-post/SKILL.md
│       ├── create-visualization/
│       │   ├── SKILL.md
│       │   └── generate_graph.py
│       └── validate-diagrams/
│           ├── SKILL.md
│           └── validate_diagrams.py
└── output/
    ├── extracted-source.md
    ├── teaching-article.md
    ├── substack-article.md
    ├── linkedin-post.md
    ├── teaching-visuals/
    ├── substack-visuals/
    └── linkedin-visuals/
```
