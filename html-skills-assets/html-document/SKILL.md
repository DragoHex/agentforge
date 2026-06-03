# html-document — Structured Informational Documents

## Description
Trigger this skill when the user asks for any kind of structured informational HTML document: side-by-side comparisons, visual design explorations, implementation plans, slide decks, feature/concept explainers, research documents, weekly status reports, or incident post-mortems. This skill covers the broadest set of use cases — any output where structured layout, navigation, and data presentation matter more than code review or interactive editing.

## Use Cases
| Demo | Prompt Pattern |
|------|---------------|
| Code approaches compare | "Compare three approaches to debounced search: useEffect, custom hook, and a library. Show them side by side with pros/cons." |
| Visual design directions | "I haven't decided on the empty-state design. Generate 4 markedly different directions in a grid so I can compare." |
| Implementation plan | "Build an implementation plan for the comment-threads feature with milestones, a data-flow diagram, mockups, and a risk table." |
| Arrow-key slide deck | "Turn this Slack thread into a short presentation deck I can arrow-key through in a meeting." |
| Feature explainer | "Explain how rate limiting works in this repo — TL;DR box, collapsible request-path steps, tabbed config snippets, FAQ." |
| Concept explainer | "Teach me consistent hashing with a live interactive ring diagram, comparison table, and glossary." |
| Weekly status report | "Generate a weekly engineering status with shipped items, metrics cards, a small chart, and carryover items." |
| Incident timeline | "Write up the post-mortem for the 502 incident: TL;DR, minute-by-minute timeline, root cause with code snippet, action items." |

## Constraints
Apply ALL rules from `assets/palette.css`. Additionally:
- Single-file only; all CSS/JS inline
- System fonts only
- No network calls; all SVG inline
- Use the shared palette exactly as defined
- Mobile-responsive: use max-width container, stack columns on narrow screens

## Patterns

### 1. Side-by-Side Comparison Grid
Read `templates/comparison-grid.html`. For comparing 2-4 approaches/options:
- Each column = one approach, with a header label
- Show the code/solution, then pros/cons in labeled lists
- Add a "verdict bar" at the bottom of each column: bundle impact, testability, reuse, SSR safety
- Use `border: 1px solid var(--gray-300)` column dividers
- Clay highlight the recommended or "in focus" column with a subtle left-border accent

### 2. Visual Design Exploration
Read `templates/design-exploration.html`. For presenting multiple visual directions:
- 2×2 or 3×2 grid of design mockup cards
- Each card: variant label (A, B, C, D), a title, body copy, and a CTA button rendered in the variant's style
- Light/dark mode toggle in the corner
- Below each card: a 1-2 sentence label explaining the trade-off
- These are NOT pixel-perfect mockups — they are "vibe boards" rendered with CSS, enough to react to

### 3. Timeline Layout
Read `templates/timeline.html`. Two variants:
- **Horizontal milestone track**: 4-6 circles on a line, each with a date range and description below. Good for implementation plans.
- **Vertical incident log**: Left-aligned timestamps (`14:02`), right-aligned events, with severity bars (green/yellow/red). Good for post-mortems.

### 4. Status Report / Metrics
Read `templates/status-report.html`. Key sections:
- **Header**: Team name, week, summary stats in a 3-4 column metric row (PRs merged, Deploys, Incidents, etc.)
- **Highlights**: Bulleted narrative of key accomplishments
- **Shipped table**: PR #, Title, Author, Risk badge — a clean table
- **Velocity chart**: CSS-drawn mini bar chart (no library needed — use flexbox bars with percentage widths)
- **Carryover**: In-review / Blocked / Slipped items with owner

### 5. Slide Deck
Read `templates/slide-deck.html`. Structure:
- Each slide is a `<section>` tag
- Only the current slide is visible; others are `display: none`
- Arrow keys navigate left/right; click dots at bottom
- Slide counter: "1 / 6" in bottom-right
- Keep slides short: one main heading, 3-5 bullet points or a single diagram per slide
- CSS transitions for slide changes (fade or slide)

### 6. Explainer (Feature or Concept)
Read `templates/explainer.html`. Structure:
- **TL;DR box** at the top: clay-bordered card with 2-3 sentence summary
- **Step-by-step walkthrough**: Collapsible `<details>` elements, each revealing annotated code blocks
- **Tabbed code/config**: CSS-only tabs (radio buttons + labels) showing different file contexts
- **FAQ accordion**: `<details>` elements with question as `<summary>` and answer in body
- **Glossary**: Definition list with hover-linked terms throughout the document
- **Interactive diagram** (if relevant): e.g., consistent hashing ring with add/remove node buttons — cross-reference `html-diagram` skill

### 7. Implementation Plan
Read `templates/implementation-plan.html`. Structure:
- **Header**: Feature name, effort estimate, surfaces touched, new tables, feature flag name
- **Milestones**: 4-5 horizontal blocks with week labels and checkpoints
- **Data-flow diagram**: Refer to `html-diagram` skill for box-and-arrow SVG
- **Mockups**: Simple HTML/CSS wireframes of key screens with annotations
- **Key code**: The 2-3 most important code blocks that are easy to get wrong (migrations, hooks)
- **Risk table**: Risk, Severity (HIGH/MED/LOW), Mitigation — styled as a table with severity badges
- **Open questions**: Pending decisions with stakeholders

### 8. Incident Post-Mortem
Read `templates/incident-report.html`. Structure:
- **TL;DR box**: What happened, impact, mitigation — clay-bordered summary
- **Timeline**: Vertical log with timestamps, using the incident timeline pattern
- **Root cause**: Explanation with the offending code diff inline
- **Impact table**: Requests failed, peak error rate, users affected, data loss, SLA breach
- **Action items**: Table with owner initials, description, due date — checkmark for done

## Gotchas
- Long comparison grids: When comparing 3+ complex code blocks, the page can get very long. Use a sticky table of contents or tabs to let readers jump between sections.
- Slide decks: The arrow-key JS must handle edge cases — don't wrap past the first/last slide unless the user asked for looping. Always show a "slide X / N" counter.
- Timelines: Don't use CSS `position: absolute` for timeline positioning — it breaks on mobile. Use flexbox with pseudo-elements for the connecting line.
- Explainer diagrams: If the explainer includes an interactive diagram (like the consistent hashing ring), the interactive JS must NOT reload the page. Use event listeners, not form submits.
- Charts in reports: Don't try to use Chart.js or any library. CSS bars (flexbox divs with percentage widths) or simple SVG line charts are sufficient and keep the single-file guarantee.
- Status reports: The velocity chart is the part most likely to look wrong. Use simple `<div>` bars with inline `width: X%` styles based on actual data — the agent generates the bars, not a generic template.

## References
- `assets/palette.css` — color tokens, typography, spacing
- `templates/comparison-grid.html` — side-by-side approach comparison
- `templates/design-exploration.html` — visual design direction grid
- `templates/timeline.html` — horizontal milestone + vertical incident timeline
- `templates/status-report.html` — weekly status with metrics and chart
- `templates/slide-deck.html` — keyboard-navigable presentation
- `templates/explainer.html` — feature/concept explainer with collapsibles
- `templates/implementation-plan.html` — full implementation plan
- `templates/incident-report.html` — post-mortem report
- Cross-reference: `html-diagram` skill for SVG data-flow diagrams, flowcharts, and spot illustrations within documents