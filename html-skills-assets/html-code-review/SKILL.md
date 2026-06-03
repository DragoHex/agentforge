# html-code-review — Code Review & Understanding Artifacts

## Description
Trigger this skill when the user asks for any kind of code review or code understanding artifact: reviewing a PR with annotated diffs, writing a PR description for reviewers, or mapping out how a module/package works. Use it whenever the output needs rendered diffs, margin annotations, severity badges, file-by-file tours, risk maps, or module call-graph diagrams.

## Use Cases
| Demo | Prompt Pattern |
|------|---------------|
| Annotated PR review | "Review this PR. Render the diff with inline margin annotations, color-code findings by severity, and add jump links to the files that need attention." |
| PR writeup | "Write the PR description for this change: motivation, before/after, file-by-file tour with the why, and where reviewers should focus." |
| Module map | "Draw me a map of how authentication flows through this codebase — boxes, arrows, the hot path, and where each entry point lives." |

## Constraints
Apply ALL rules from `assets/palette.css`. Additionally:
- Single-file only; all CSS/JS inline
- System fonts only
- Use the shared palette exactly as defined
- Code blocks must use monospace font, with syntax-relevant color classes applied via inline `<span>` elements

## Patterns

### 1. Annotated Diff
Read `templates/pr-review-annotated.html`. Structure:
- **Header**: PR number, title, author, branch → target
- **What this PR does**: 3-4 sentence summary
- **Risk map**: Horizontal bar showing each file, color-coded by risk (clay=needs attention, warning=worth a look, olive=safe)
- **File sections**: One section per changed file, with:
  - File path, risk badge, line-change count
  - Rendered diff using `<pre>` with line-number spans
  - Margin annotations: colored callout boxes alongside specific lines
  - Annotation colors: clay outline = critical finding, olive outline = suggestion, gray outline = note
- **Severity tags**: Small colored pills — `needs attention` (clay bg), `worth a look` (warning bg), `safe` (olive bg)

### 2. PR Writeup
Read `templates/pr-writeup.html`. Structure:
- **TL;DR box**: 2-sentence summary
- **Why**: Rationale with before/after metrics or qualitative comparison
- **File-by-file**: Ordered reading list where each file has:
  - Path, change stats, a "start here" or "skim" label
  - The key code snippet (not the full diff)
  - Why this file matters
- **Where to focus your review**: 2-3 numbered items pointing to the trickiest logic
- **Test plan**: Unit/integration/manual sections
- **Rollout**: Flag name, ramp schedule (internal → 10% → 100%)

### 3. Module / Call-Graph Map
Read `templates/module-map.html`. Structure:
- **Request path**: Horizontal or vertical flow showing how a request travels through layers
- **Callstack walkthrough**: Numbered steps, each with:
  - File path and line range
  - Description of what happens at this step
  - Expandable "show source" button revealing the code snippet
- **Box-and-arrow diagram**: Refer to `html-diagram` skill for SVG generation
  - Boxes = packages/modules/files
  - Arrows = call direction or data flow
  - Hot path in clay, rest in neutral
  - Entry points labeled with small badges

## Diff Rendering Rules
- Lines starting with `+` get a green-tinted background (`background: rgba(120,140,93,0.08)`)
- Lines starting with `-` get a red-tinted background (`background: rgba(176,74,74,0.08)`)
- Line numbers are right-aligned in gray-500, monospace
- Changed lines get a left-border accent matching the +/- color
- Use `<code>` inside `<pre>` for semantic correctness
- Never try to embed real `<diff>` or `<ins>`/`<del>` tags — use CSS classes on `<span>` elements

## Gotchas
- The risk map should visually show which files need attention. Use a simple horizontal flexbox with width proportional to lines changed, not a complex visualization.
- When rendering diffs, the margin annotations must stay aligned with the line they reference. Use a two-column layout: fixed-width annotation gutter on the left, scrolling diff on the right. Avoid absolute positioning.
- For module maps, don't try to auto-discover the call graph from code — the agent is creating a *visualization* of known relationships. Describe the structure clearly.
- When showing "before/after" code in a PR writeup, put them side by side or use clear labels. Don't mix them inline without visual separation.
- The "Where to focus" section is the most valuable part of a PR writeup. It should point to the 2-3 specific lines or decisions that carry the most risk, not generic "review the tests" advice.

## References
- `assets/palette.css` — color tokens, typography, spacing
- `templates/pr-review-annotated.html` — annotated diff with margin notes
- `templates/pr-writeup.html` — PR description for reviewers
- `templates/module-map.html` — call-graph with expandable steps
- Cross-reference: `html-diagram` skill for box-and-arrow SVG diagrams in module maps