# html-diagram — SVG Illustrations & Diagrams

## Description
Trigger this skill when the user asks for any kind of SVG-based visual: diagrams, flowcharts, architecture maps, figure sheets for blog posts, spot illustrations, or annotated process flows. Use it whenever the output needs boxes-and-arrows, geometric art, or clickable pipeline diagrams — anything where inline SVG is the right medium. Also cross-referenced by `html-document` (data-flow diagrams, explainer diagrams), `html-code-review` (module maps), and `html-design` (spot illustrations).

## Use Cases
| Demo | Prompt Pattern |
|------|---------------|
| SVG figure sheet | "Draw the header illustrations for my blog post about background jobs — queue, retry, fan-out" |
| Annotated flowchart | "Draw our deploy pipeline as a flowchart. Click any step to see what runs, timings, and failure paths." |
| Architecture diagram | "Map out how authentication flows through this codebase as boxes and arrows." |
| Data-flow diagram | "Show the optimistic-write path and realtime fan-out for the comment threads feature." |
| Spot illustrations | "Create a small geometric illustration of a task queue with workers pulling jobs." |

## Constraints
Apply ALL rules from `assets/palette.css`. Also apply these SVG-specific rules:
- Strokes: `1.5px` for neutral boxes, `2px` for emphasised containers
- All rectangles use `rx="10"`; no drop shadows or gradients in SVG
- Labels inside boxes: `11px mono` font-family
- Annotations outside boxes: `12px sans-serif`, fill `#87867F` (gray-500)
- Clay (`#D97757`) marks "the thing in focus" — the active element, the current step, the hot path
- Olive (`#788C5D`) marks "success / done" — completed steps, passed checks, healthy state
- Each standalone SVG carries its own `<style>` block so it can be downloaded independently
- For figure sheets, add a "Download SVG" button per figure that copies the SVG markup to clipboard or triggers a download

## Patterns

### 1. Box-and-Arrow Flowchart
Read `templates/annotated-flowchart.html` for the full template. Key elements:
- **Process step**: `<rect rx="10" fill="#FAF9F5" stroke="#D1CFC5" stroke-width="1.5">` with centered label
- **Decision diamond**: A rotated rect or polygon, fill `#F0EEE6`, stroke `#87867F`
- **Terminal (start/end)**: `<rect rx="20">` with rounded ends, fill `#788C5D` (olive)
- **Success path**: Green stroke `#788C5D`, dashed
- **Failure path**: Red stroke `#B04A4A`, dashed
- **Arrows**: `<path marker-end="url(#arrow)">` with a `<marker id="arrow">` defined in `<defs>`
- **Annotations**: `<text fill="#87867F" font-size="12" font-family="sans-serif">` positioned near steps
- **Interactivity**: Wrap each step in an `<a>` or use onclick to expand a detail panel below the diagram
- **Legend**: Small box in bottom-right showing process/decision/terminal/success/failure symbols

### 2. SVG Figure Sheet
Read `templates/svg-figure-sheet.html` for the full template. Key elements:
- Grid layout: 1-3 columns of figure cards
- Each card: figure title, the SVG, a caption describing where to use it, a "Download SVG" button
- Each SVG is self-contained with its own `<style>` block
- Use the geometric illustration patterns: queues (stacked rounded rects), retries (ascending steps with backoff labels), fan-out (one node branching to N, then merging back)
- Keep illustrations simple: 3-6 elements max per figure, clear labels, distinct colors

### 3. Architecture / Module Map
Read `templates/annotated-flowchart.html` (reuse the box-and-arrow pattern with different labels). Key elements:
- Boxes represent packages, services, or modules
- Arrows show data flow, call direction, or dependency
- Hot path: highlight the primary request path with clay-colored boxes and thicker strokes (2px)
- Entry points: label with small "entry" badges
- Group related boxes with a larger dashed container rect

## Gotchas
- When generating SVG, Claude often forgets the `xmlns="http://www.w3.org/2000/svg"` attribute on the `<svg>` tag — this breaks rendering in some browsers.
- Text elements in SVG don't wrap. For multi-line labels, use multiple `<tspan>` elements or position separate `<text>` elements.
- For clickable flowcharts, the onclick handler must reference an element ID that exists. Define the detail divs *after* the SVG in the HTML.
- When creating a "Download SVG" button, don't try to use blob URLs — use `navigator.clipboard.writeText()` to copy the SVG source so the user can paste it, OR use a data URI download link: `<a href="data:image/svg+xml;charset=utf-8,..." download="figure.svg">`.
- Avoid `foreignObject` in SVG — it has inconsistent support and breaks the "standalone SVG" guarantee.
- For diagrams that need to be responsive, set `viewBox` on the `<svg>` and use percentage widths rather than fixed pixel sizes.

## References
- `assets/palette.css` — color tokens, typography, spacing
- `templates/annotated-flowchart.html` — full flowchart template
- `templates/svg-figure-sheet.html` — full figure sheet template
- Cross-reference: `html-document` skill uses diagram patterns for data-flow and explainer diagrams
- Cross-reference: `html-code-review` skill uses diagram patterns for module maps