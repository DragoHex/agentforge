# HTML Effectiveness Agent Skills — Implementation Plan

## Overview

Based on Thariq Shihipar's "The Unreasonable Effectiveness of HTML" article and all 20 demo pages from https://thariqs.github.io/html-effectiveness/, this plan organizes **20 distinct use cases across 9 categories** into **5 minimal skills**. Each skill is a folder containing a `SKILL.md` instruction file, reusable CSS/JS template snippets, and reference assets.

---

## Color Palette & Design Tokens

Extracted from the [SVG Illustrations page](https://thariqs.github.io/html-effectiveness/10-svg-illustrations.html) and the [Design System page](https://thariqs.github.io/html-effectiveness/05-design-system.html). **All 5 skills share this identical palette.**

```
┌──────────────┬──────────┬──────────────────────────────────────┐
│ Token        │ Hex      │ Role                                 │
├──────────────┼──────────┼──────────────────────────────────────┤
│ --ivory      │ #FAF9F5  │ Page background                      │
│ --slate      │ #141413  │ Primary text, headings               │
│ --clay       │ #D97757  │ Focus/emphasis, primary accent       │
│ --olive      │ #788C5D  │ Success/done, positive indicators    │
│ --oat        │ #E3DACC  │ Card/container backgrounds           │
│ --gray-150   │ #F0EEE6  │ Subtle surface, hover states         │
│ --gray-300   │ #D1CFC5  │ Borders, dividers                    │
│ --gray-500   │ #87867F  │ Secondary text, annotations          │
│ --gray-700   │ #3D3D3A  │ Strong secondary text                │
│ --white      │ #FFFFFF  │ Cards on ivory bg                    │
│ --warning    │ #C78E3F  │ Warning states                       │
│ --danger     │ #B04A4A  │ Error/danger states                  │
│ --info       │ #5C7CA3  │ Informational highlights             │
└──────────────┴──────────┴──────────────────────────────────────┘
```

### Typography Scale (shared)
| Role | Size | Line-height | Weight |
|------|------|-------------|--------|
| Display | 48px | 1.1 | 500 |
| Heading 1 | 32px | 1.2 | 500 |
| Heading 2 | 24px | 1.3 | 500 |
| Body | 16px | 1.55 | 430 |
| Small | 14px | 1.5 | 430 |
| Caption | 12px | 1.4 | 500 |
| Mono (code) | 13px | 1.5 | 430 |

### Spacing Scale (shared)
`4, 8, 12, 16, 24, 32, 48, 64` (in px)

### SVG Rules (shared)
- Strokes: `1.5px` neutral boxes, `2px` emphasised containers
- Rectangles: `rx="10"`, no drop shadows or gradients
- Labels inside boxes: `11px mono`; annotations outside: `12px sans`, `gray-500`
- Clay = in-focus element; Olive = success/done
- Each SVG carries its own `<style>` block for standalone portability

### Global Constraints (shared across all skills)
1. **Single-file only** — zero external dependencies (no CDN, no Google Fonts)
2. **Inline CSS** in `<style>` block in `<head>`
3. **Inline JS** in `<script>` block at end of `<body>`
4. **System fonts** only: `system-ui, -apple-system, sans-serif` and `monospace`
5. **No network calls** — works offline/air-gapped
6. **All SVG inline** — never remote image URLs

---

## The 5 Skills

### Skill 1: `html-document`
**Covers 8 demos across 4 categories**

| Category | Demos Covered |
|----------|--------------|
| Exploration & Planning | #01 Three code approaches, #02 Visual design directions, #16 Implementation plan |
| Decks | #09 Arrow-key slide deck |
| Research & Learning | #14 Feature explainer, #15 Concept explainer |
| Reports | #11 Weekly status, #12 Incident timeline |

**Structural patterns mastered by this skill:**
- **Multi-section layout**: Tabbed panels, collapsible accordion sections, sticky table of contents
- **Comparison grids**: Side-by-side columns (2-4 panels) with pros/cons, trade-off labels
- **Timelines**: Horizontal milestone track, vertical minute-by-minute incident log, Gantt-like planning views
- **Data display**: Metric cards, simple bar/line charts (CSS-drawn, no library), status tables with severity badges
- **Slide navigation**: `<section>` tags with arrow-key JS for presentation mode, slide counter, progress indicator
- **Interactive explainers**: TL;DR summary boxes, collapsible step-by-step walkthroughs, tabbed code/config snippets, FAQ accordions, hover-linked glossary terms, live interactive diagrams (e.g., consistent hashing ring with add/remove node buttons)
- **Implementation plans**: Milestone timeline, data-flow diagrams (ASCII-to-SVG), inline mockups, risk matrix table, open-questions section

### Skill 2: `html-code-review`
**Covers 3 demos across 1 category**

| Category | Demos Covered |
|----------|--------------|
| Code Review | #03 Annotated PR review, #17 PR writeup, #04 Module map |

**Structural patterns mastered by this skill:**
- **Diff rendering**: Side-by-side or unified diff with syntax highlighting via CSS classes, line numbers, +/- indicators
- **Margin annotations**: Callout notes alongside specific diff lines, color-coded by severity (clay=critical, olive=suggestion, gray-500=note)
- **Severity tags**: Badge components (needs attention / worth a look / safe) with distinct styling
- **File-by-file tours**: Ordered file list with why each file matters, collapsible code blocks
- **Risk maps**: Visual grid showing files plotted by risk level
- **Module/call-graph maps**: Box-and-arrow diagrams of packages/modules, hot-path highlighting, entry-point labels
- **PR writeup structure**: TL;DR box, Why section, Before/After comparison, File-by-file walkthrough, Where to focus review, Test plan, Rollout plan

### Skill 3: `html-design`
**Covers 4 demos across 2 categories**

| Category | Demos Covered |
|----------|--------------|
| Design | #05 Living design system, #06 Component variants |
| Prototyping | #07 Animation sandbox, #08 Clickable flow |

**Structural patterns mastered by this skill:**
- **Design token display**: Color swatch grids (with hex labels, copy-on-click), typography scale with live preview text, spacing scale visualizer, border-radius samples, shadow elevation cards
- **Component variant matrix**: Every size × state × variant combination laid out in a grid; hover to see props/JSX; "best for:" labels
- **Animation sandbox**: Keyframe timeline visualization, duration/easing sliders, play/pause toggle, copy-paste CSS output block
- **Clickable prototype**: Multiple screens linked via click handlers, state transitions, form interactions
- **Visual design exploration**: Light/dark mode toggle, multiple layout directions in a grid, palette variations

### Skill 4: `html-diagram`
**Covers 2 demos across 1 category (plus cross-referenced by others)**

| Category | Demos Covered |
|----------|--------------|
| Illustrations & Diagrams | #10 SVG figure sheet, #13 Annotated flowchart |

**Structural patterns mastered by this skill:**
- **Inline SVG generation**: Box-and-arrow diagrams, flowcharts, architecture diagrams, sequence diagrams, data hierarchies — all as pure inline SVG
- **SVG figure sheets**: Multiple standalone SVGs in a grid, each with its own `<style>` block, "Download SVG" button per figure
- **Annotated flowcharts**: Process steps with click-to-expand details (what runs, timings, failure paths), color-coded nodes (process/decision/terminal/success/failure), legend
- **Diagram interactivity**: Click steps to reveal annotations, hover for tooltips, zoom/pan for large diagrams
- **Geometric spot illustrations**: Simple geometric SVGs (queue/retry/fan-out patterns)

### Skill 5: `html-editor`
**Covers 3 demos across 1 category**

| Category | Demos Covered |
|----------|--------------|
| Custom Editing Interfaces | #18 Ticket triage board, #19 Feature flag editor, #20 Prompt tuner |

**Structural patterns mastered by this skill:**
- **Drag-and-drop boards**: Kanban-style columns, draggable cards using native HTML5 Drag and Drop API, filter by tag, reset button
- **Form-based config editors**: Toggle switches grouped by area, dependency validation, pending-changes counter
- **Export/copy pattern**: "Copy as markdown", "Copy diff", "Copy full JSON", "Copy prompt" — all using `navigator.clipboard.writeText()`
- **Live preview split-pane**: Editable template on left, sample inputs rendered on right, re-renders on every keystroke (debounced), variable slot highlighting
- **Editor reset**: Always include a Reset button

---

## Coverage Matrix: 20 Demos → 5 Skills

```
Demo  │ Category                  │ html-document │ html-code-review │ html-design │ html-diagram │ html-editor
──────┼───────────────────────────┼───────────────┼──────────────────┼─────────────┼──────────────┼────────────
  #01 │ Code approaches compare   │      ✓        │                  │             │              │
  #02 │ Visual design directions  │      ✓        │                  │      ✓      │              │
  #03 │ Annotated PR review       │               │        ✓         │             │              │
  #04 │ Module map                │               │        ✓         │             │      ✓       │
  #05 │ Living design system      │               │                  │      ✓      │              │
  #06 │ Component variants        │               │                  │      ✓      │              │
  #07 │ Animation sandbox         │               │                  │      ✓      │              │
  #08 │ Clickable flow            │               │                  │      ✓      │              │
  #09 │ Arrow-key slide deck      │      ✓        │                  │             │              │
  #10 │ SVG figure sheet          │               │                  │             │      ✓       │
  #11 │ Weekly status report      │      ✓        │                  │             │              │
  #12 │ Incident timeline         │      ✓        │                  │             │              │
  #13 │ Annotated flowchart       │               │                  │             │      ✓       │
  #14 │ Feature explainer         │      ✓        │                  │             │      ✓       │
  #15 │ Concept explainer         │      ✓        │                  │             │      ✓       │
  #16 │ Implementation plan       │      ✓        │                  │             │      ✓       │
  #17 │ PR writeup                │               │        ✓         │             │              │
  #18 │ Ticket triage board       │               │                  │             │              │      ✓
  #19 │ Feature flag editor       │               │                  │             │              │      ✓
  #20 │ Prompt tuner              │               │                  │             │              │      ✓
```

**Summary**: 12 demos use `html-document`, 3 use `html-code-review`, 4 use `html-design`, 5 reference `html-diagram` (3 standalone + 2 cross-referenced), 3 use `html-editor`.

---

## Implementation Order

1. `assets/palette.css` — shared foundation for all 5 skills
2. `html-diagram/` — SVG patterns referenced by document, code-review, and design skills
3. `html-document/` — covers most demos (8) and establishes core layout patterns
4. `html-code-review/` — builds on diff rendering patterns, references diagram for module maps
5. `html-design/` — design system patterns, references diagram for spot illustrations
6. `html-editor/` — most specialized, self-contained

---

## What Each SKILL.md Contains

1. **Description** — When to trigger this skill (written for the model)
2. **Use Cases** — Which demos/categories this covers, with example prompts
3. **Constraints** — The single-file rules + palette reference
4. **Patterns** — Each structural pattern with template reference and example prompt
5. **Gotchas** — Common failure modes
6. **References** — Pointers to template files, palette.css, and cross-skill dependencies