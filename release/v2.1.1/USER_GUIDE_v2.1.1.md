# QTR Pairing Process - User Guide v2.1.1

## 1. Basic workflow

1. Select Team 1 and Team 2.
2. Select Scenario.
3. Review or edit grid values.
4. Click Generate Combinations.
5. Use sort modes to evaluate paths.
6. Select a tree path and extract final matchups.
7. Save Grid if you changed ratings.

## 2. Main interface sections

- **Rating Matrix** (left): 5×5 matchup ratings and player names.
- **Calculations panel** (right of matrix): floor/pin/protect/bus guidance.
- **Tree panel** (bottom): decision tree and sort values.
- **Final Matchups Output** (upper right): extracted lineup summary and notes.

## 3. Rating matrix behavior

- Ratings are on a 1-to-5 scale by default (configurable).
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

- Cached snapshots restore quickly for repeated selections.
- Data Management includes options to clear active or all tree caches.

## 6. Sort modes

Four modes are available in v2.1.1:

| Mode | Purpose | Best For |
|---|---|---|
| Cumulative Sort | Maximize total path value | Confident in ratings, want max upside |
| Confidence Sort | Prioritize reliable outcomes | Elimination rounds, conservative play |
| Counter-Resistance Sort | Survive opponent counter-play | Adaptive/skilled opponents |
| Strategic Fusion | Balanced C/Q/R with downside guardrail | General-purpose advanced use |

Node ordering is decision-owner aware:
- **Friendly choice nodes**: your best options first.
- **Enemy choice nodes**: opponent's worst options (for you) first.

### Using Sort Modes

1. Generate Combinations to build the tree.
2. Click a sort button to apply.
3. Top branches show the best strategies for your chosen method.
4. Use "Remove Sorting" to return to original order.
5. Compare multiple modes to understand different strategic angles.

## 7. Explainability

Select or hover over nodes to inspect component details:

- **C2, Q2, R2**: component scores (cumulative, confidence, resistance).
- **Regret/downside context**: how much worse than the best outcome this path is.
- **Strategic score**: combined score used for ranking.

For metric interpretation, open the **Tooltip Numbers Guide** from Data Management.

## 8. Data Management menu

Use Data Management for:

- Import/Export CSV or XLSX
- Load / Refresh / Get Score
- Team creation and deletion
- Rating system changes (1–3, 1–5, 1–10)
- Database switching
- Tree cache clear actions
- Opening user and tooltip guides

## 9. Excel / CSV Import

In v2.1.1, team rosters and player ratings can be imported from `.xlsx` files in addition to `.csv`.

Supported import formats are documented in `DapperBadgersImport_Example.csv` (included in the app folder on development builds).

## 10. Saving and persistence

- **Save Grid** writes current friendly-view ratings to the database.
- Team/scenario selections and preferences are persisted across sessions.
- Generated tree cache persists for faster reloads.

## 11. Troubleshooting

**If sort ordering looks incorrect:**

1. Confirm "My Team First" state is correct.
2. Regenerate tree after major rating changes.
3. Reapply the desired sort mode.
4. Clear active tree cache and regenerate.

**If calc guidance seems stale:**

1. Toggle a lock checkbox once to force a refresh.
2. Use Refresh UI from Data Management.
3. Regenerate combinations.

## 12. Recommended match-day routine

1. Pre-load team/scenario and generate trees before the round.
2. Validate the sort mode matches your round objective.
3. Use explainability to avoid over-relying on a single metric.
4. Extract final matchups and copy to clipboard for quick reference.
