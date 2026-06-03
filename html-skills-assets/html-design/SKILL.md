# html-design — Design Artifacts & Prototyping

## Description
Trigger this skill when the user asks for design artifacts: living design systems, component variant matrices, animation sandboxes, clickable prototypes, or visual design explorations. Use it whenever the output needs to communicate visual design decisions — color tokens, typography scales, component states, motion tuning, or multi-screen interaction flows.

## Use Cases
| Demo | Prompt Pattern |
|------|---------------|
| Living design system | "Generate a design system reference page from our tokens: colors, type scale, spacing, radii, shadows, and core components." |
| Component variants | "Show every size, state, and intent variant of the Card component on a single sheet so I can review them." |
| Animation sandbox | "I want to tune the task-complete micro-interaction. Give me a sandbox with sliders for duration and easing." |
| Clickable flow | "Wire up these four screens so I can click through the onboarding flow and feel the interaction." |

## Constraints
Apply ALL rules from `assets/palette.css`. Additionally:
- Single-file only; all CSS/JS inline
- System fonts only
- Use the shared palette exactly as defined
- For prototypes: prioritize feel over pixel-perfection — the goal is to judge interaction, not visual polish

## Patterns

### 1. Design System Reference
Read `templates/design-system.html`. Structure:
- **Color section**: Swatch grid — each swatch shows the color, token name (CSS variable), and hex value. Group by Primary, Neutral, Semantic. Swatches should be clickable to copy the hex value.
- **Typography section**: Each type role shown at its actual size with a sample sentence. Display, H1, H2, Body, Small, Caption. Show font-weight, size/line-height, and weight in a small label next to each.
- **Spacing section**: Visual bars showing each spacing token width with the token name below.
- **Radius & Elevation**: Rounded-corner samples at each radius; shadow cards showing sm/md/lg elevation.
- **Core components**: Small live-rendered examples of buttons, inputs, toggles, and badges using the design tokens.

### 2. Component Variant Matrix
Read `templates/component-variants.html`. Structure:
- **Controls**: Checkboxes/toggles at the top for variant axes (padding, border style, shadow on/off, layout direction)
- **Grid**: Every combination rendered as a live card in a grid
- **Hover inspector**: When you hover a card, show its props below the grid (JSX snippet or prop list)
- **"Best for" labels**: Each variant row/column gets a small caption describing its ideal use case
- Use CSS to actually render the component in each state — this is NOT a screenshot, it's a live rendering

### 3. Animation Sandbox
Read `templates/animation-sandbox.html`. Structure:
- **Preview area**: The animated element (e.g., a task row with checkbox, label) that plays the animation
- **Controls**: Range sliders for duration, delay, easing curve; a play/pause button
- **Keyframe timeline**: Visual representation of the keyframe sequence showing what changes at each offset
- **Copy-paste CSS block**: A `<pre>` that updates live as sliders change, showing the exact CSS the user can copy into their codebase
- Easing curve selector: buttons for common easing values (ease, ease-in, ease-out, cubic-bezier presets)

### 4. Clickable Prototype
Read `templates/clickable-prototype.html`. Structure:
- **Screen container**: Phone-frame or desktop-panel sized container
- **Screen switching**: Each "screen" is a `<div>`; only one visible at a time. Click handlers on buttons/links switch screens.
- **Transition**: Simple CSS fade or slide between screens (200ms)
- **State memory**: Simple JS object holding the current state (form values, selections) so navigating back preserves data
- **Breadcrumb/back**: A simple back button or breadcrumb showing the flow position
- **Design decisions panel**: Below the prototype, a section listing what's being tested and open questions

## Gotchas
- For the design system, don't use CSS custom properties to *define* colors within the swatches — show the raw hex value in a monospace label so users can copy it. The swatches' backgrounds should use the actual hex color directly.
- Component variant matrices can get very large (combinations multiply). For components with many axes, show the most important 2-3 axes and note that others exist but are omitted.
- Animation sandboxes: use `requestAnimationFrame` for the play button, not `setInterval`. Reset the animation state when sliders change. The copy-paste CSS block should include only the keyframe and transition properties, not the sandbox's own UI CSS.
- Clickable prototypes: don't use `window.location` or URL hashes for screen switching — use JavaScript to toggle `display` or a CSS class. This keeps the entire flow in one file without navigation side effects.
- For the "design decisions" panel in prototypes, list concrete, testable assertions ("Drop indicator snaps to nearest gap" not "Drag feels good").

## References
- `assets/palette.css` — color tokens, typography, spacing
- `templates/design-system.html` — full design token reference page
- `templates/component-variants.html` — variant matrix with hover inspector
- `templates/animation-sandbox.html` — keyframe tuner with live CSS output
- `templates/clickable-prototype.html` — multi-screen interactive flow