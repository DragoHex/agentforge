# html-editor — Interactive Editing Interfaces

## Description
Trigger this skill when the user asks for a throwaway editing interface: drag-and-drop kanban boards, form-based config editors with validation, or live preview template editors. Use it whenever the output needs two-way interaction — the user manipulates the UI and exports the result back into text. Always include an export/copy button.

## Use Cases
| Demo | Prompt Pattern |
|------|---------------|
| Ticket triage board | "I have 24 tickets. Make me a drag-and-drop board with Now/Next/Later/Cut columns so I can triage them. Add a 'Copy as markdown' button at the end." |
| Feature flag editor | "Build an editor for our feature-flag JSON. Group toggles by area, warn when a prerequisite flag is off, and show a 'Copy diff' button for only the changed keys." |
| Prompt tuner | "I'm iterating on a support-reply prompt. Make me a split-pane editor where I type the template on the left and see 3 sample tickets rendered live on the right." |

## Constraints
Apply ALL rules from `assets/palette.css`. Additionally:
- Single-file only; all CSS/JS inline
- System fonts only
- No external drag-and-drop libraries — use the native HTML5 Drag and Drop API
- Every editor MUST end with an export/copy button that puts the result on the clipboard
- Every editor MUST have a Reset button to restore initial state
- State is DOM-only (no localStorage, no server) — refreshing the page resets everything

## Patterns

### 1. Drag-and-Drop Kanban Board
Read `templates/triage-board.html`. Key elements:
- **Columns**: 3-5 columns (e.g., Now / Next / Later / Cut) using CSS flexbox
- **Cards**: Each card is a `<div draggable="true">` with title, tags (clickable to filter), and metadata
- **Drag events**: `dragstart` (set data + add dragging class), `dragover` (allow drop + show indicator), `drop` (move card to new column)
- **Drop indicator**: A thin colored line that appears between cards during `dragover`, showing exactly where the card will land
- **Tag filter**: Clicking a tag at the top highlights cards with that tag and dims others
- **Copy as markdown**: Button that reads the current board state and formats as a markdown list grouped by column
- **Reset**: Restores the initial card ordering

### 2. Feature Flag / Config Editor
Read `templates/feature-flag-editor.html`. Key elements:
- **Toggle groups**: Sections organized by area (e.g., "Experiments", "Performance", "Access Control")
- **Each toggle**: Label, description, on/off switch (styled checkbox or button toggle)
- **Dependency warnings**: When a flag depends on another, show a yellow warning banner if the prerequisite is off
- **Pending changes counter**: Small badge showing "N changed" — only counts toggles that differ from initial state
- **Copy diff**: Button that serializes only the changed keys into a JSON diff format and copies to clipboard
- **Copy full JSON**: Copies the entire current config state
- **Reset**: Restores all toggles to initial state

### 3. Prompt Tuner (Split-Pane)
Read `templates/prompt-tuner.html`. Key elements:
- **Left pane**: Editable `<textarea>` showing the prompt template with `{{variable_slots}}` highlighted
- **Right pane**: 3 sample inputs rendered through the template, updating live as the user types (debounced ~300ms)
- **Slot highlighting**: `{{slots}}` in the textarea are visually distinguished with a colored background
- **Available slots panel**: Shows the variable names the user can use
- **Sample selector**: Dropdown or tabs to switch between different sample inputs
- **Character/token counter**: Shows approximate character count and token estimate
- **Copy prompt**: Copies the current template text
- **Reset**: Restores to the original template

## Gotchas
- The native HTML5 Drag and Drop API requires `event.preventDefault()` in `dragover` to allow dropping. Forgetting this is the #1 bug.
- On mobile, native drag-and-drop doesn't work. Add touch event fallbacks or note that the board requires desktop.
- For the prompt tuner, debounce the rendering (use `setTimeout` with 300ms and clear on each keystroke). Without debounce, rendering 3 samples on every keystroke will lag.
- The "Copy diff" in the feature flag editor needs to track initial state. Store the initial toggle values in a JS object at page load and compare against current state when generating the diff.
- For the triage board, the "Copy as markdown" output should be well-formatted: H2 for column names, bullet lists for tickets, with tags in brackets.
- Export buttons should show visual feedback ("Copied!") for 1-2 seconds after clicking, using `navigator.clipboard.writeText()`.

## References
- `assets/palette.css` — color tokens, typography, spacing
- `templates/triage-board.html` — drag-and-drop kanban with markdown export
- `templates/feature-flag-editor.html` — form-based toggle editor with diff export
- `templates/prompt-tuner.html` — split-pane live template editor