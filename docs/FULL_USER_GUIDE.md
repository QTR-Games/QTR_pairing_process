# QTR Pairing Process Full User Guide

This guide covers the main workflow and key controls in the app.

## 1. Basic workflow

1. Select Team 1 and Team 2.
2. Select Scenario.
3. Review or edit grid values.
4. Click Generate Combinations.
5. Use sort modes to evaluate paths.
6. Select a tree path and extract final matchups.
7. Save Grid if you changed ratings.

## 2. Main interface sections

- Rating Matrix (left): 5x5 matchup ratings and names.
- Calculations panel (right of matrix): floor/pin/protect/bus guidance.
- Tree panel (bottom): decision tree and sort values.
- Final Matchups Output (upper right): extracted lineup summary and notes.

## 3. Rating matrix behavior

- Ratings are usually on a 1 to 5 scale.
- Header cells hold player names.
- Matchup cells hold numeric ratings.
- Row/column lock checkboxes affect calc guidance and round context.

## 4. Flip Grid

Flip Grid changes display perspective only.

- Names swap sides visually.
- Ratings invert around 3 for opponent perspective.
- Do not save while flipped.
- Flip back to friendly view before Save Grid.

## 5. Tree generation and cache

Generate Combinations builds the current matchup tree.

- Cached snapshots may restore quickly for repeated selections.
- Data Management includes options to clear active or all tree caches.

## 6. Sort modes

- Cumulative Sort: path-value oriented.
- Highest Confidence: low-variance reliability.
- Counter Pick: robustness against counters.
- Strategic Fusion: balanced C2/Q2/R2 with downside and guardrail.

Node ordering is decision-owner aware:

- Friendly choice nodes: best options for us first.
- Enemy choice nodes: worst options for us first.

## 7. Explainability

Hover/select nodes to inspect component details.

- C2, Q2, R2
- Regret/downside context
- Strategic score and exploitability context

For deeper metric interpretation, open Tooltip Numbers Guide in Data Management.

## 8. Data Management menu

Use Data Management for:

- Import/Export CSV/XLSX
- Load/Refresh/Get Score
- Team creation/deletion
- Rating system changes
- Database switching
- Tree cache clear actions
- Opening both guides

## 9. Keyboard shortcuts

Core workflow:

- Ctrl+S: Save Grid to database.
- Ctrl+Z: Undo last shortcut-tracked calculation/data-management action (with confirmation).
- Ctrl+Y: Redo last undone shortcut action.
- Ctrl+R: Recalculate scenario values immediately.
- Ctrl+Enter: Generate Combinations.
- Ctrl+F: Flip Grid perspective.
- Ctrl+G: Focus first rating cell (top-left matchup cell) for rapid data entry.

Sort modes:

- Ctrl+1: Strategic Fusion.
- Ctrl+2: Counter Pick.
- Ctrl+3: Highest Confidence.
- Ctrl+4: Cumulative Sort.

Clipboard/grid actions:

- Ctrl+C: Copy current 5x5 grid values to clipboard.
- Ctrl+V: Paste 5x5 grid values from clipboard.

Data management and utilities:

- Ctrl+D: Open comment editor for currently focused matchup cell.
- Ctrl+Shift+R: Clear all tree cache.
- Ctrl+Shift+T: Open Import Templates popup.
- Ctrl+Shift+L: Open import logs folder.
- Ctrl+Shift+S: Export CSV.
- Ctrl+Shift+X: Export XLSX.

Team and help:

- Ctrl+N: New Team.
- Ctrl+H: Open Full User Guide.

## 10. Saving and persistence

- Save Grid writes current friendly-view ratings to DB.
- Team/scenario selections and preferences are persisted.
- Generated tree cache persists for faster reloads.

## 11. Troubleshooting

If ordering looks incorrect:

1. Confirm My Team First state.
2. Regenerate tree after major changes.
3. Reapply desired sort mode.
4. Clear active tree cache and regenerate.

If calc guidance seems stale:

1. Toggle a lock checkbox once.
2. Refresh UI from Data Management.
3. Regenerate combinations.

## 12. Recommended match-day routine

1. Pre-load team/scenario and generate trees.
2. Validate sort mode aligns with round objective.
3. Use explainability to avoid one-metric traps.
4. Extract final matchups and copy to clipboard for quick reference.
