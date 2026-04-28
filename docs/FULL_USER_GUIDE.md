# QTR Pairing Process — Full User Guide

**Version 2.1.3**

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Main Interface Overview](#2-main-interface-overview)
3. [Rating Matrix](#3-rating-matrix)
4. [Import and Export](#4-import-and-export)
5. [Tree Generation and Sort Modes](#5-tree-generation-and-sort-modes)
6. [Calculations Panel](#6-calculations-panel)
7. [Flip Grid](#7-flip-grid)
8. [Data Management Menu](#8-data-management-menu)
9. [Keyboard Shortcuts](#9-keyboard-shortcuts)
10. [Saving and Persistence](#10-saving-and-persistence)
11. [WTC Pairing Strategy](#11-wtc-pairing-strategy)
12. [Troubleshooting](#12-troubleshooting)
13. [Recommended Match-Day Routine](#13-recommended-match-day-routine)

---

## 1. Getting Started

### First Launch

On first launch a welcome dialog appears. Use it to:

- **Create a new database** — choose a location that is easy to share (Desktop, Documents). Name it descriptively, e.g. `WTC2025_MyTeam.db`.
- **Open an existing database** — browse to a `.db` file you already have.

The welcome dialog can be reopened at any time from Data Management.

### Understanding the Rating System

Ratings express your expected performance in a matchup. The default scale is 1–5. Scales 1–3 and 1–10 are also supported and can be changed in Data Management.

| Rating | Meaning |
|---|---|
| 5 | Near-certain win — prioritize |
| 4 | Favorable — likely win |
| 3 | Even/neutral — could go either way |
| 2 | Unfavorable — likely loss |
| 1 | Near-certain loss — avoid if possible |

Most analysis uses **Scenario 0 (Agnostic)**. Only create scenario-specific ratings if a matchup meaningfully shifts on a particular deployment map.

---

## 2. Main Interface Overview

| Region | Purpose |
|---|---|
| **Top bar** | Team 1 / Team 2 / Scenario dropdowns, Save Grid, Data Management |
| **Rating Matrix (left)** | 5×5 grid of player names and matchup ratings |
| **Calculations panel (right of grid)** | Floor / pin / protect / bus guidance |
| **Tree panel (bottom)** | Decision tree with sort controls and node values |
| **Final Matchups Output (upper right)** | Extracted lineup summary and notes |

---

## 3. Rating Matrix

### Entering Ratings

- Click any matchup cell (row > 0, col > 0) and type a number.
- Press **Tab** to advance to the next cell in the row. **Shift+Tab** moves back.
- Press **Enter** or click away to confirm and sync to the model.
- Cell colors update automatically as you type.

### Header Cells

- Row 0 cells hold your players' names (Team 1 perspective).
- Column 0 cells hold opponent players' names.
- Click a header cell and type to rename. Changes are reflected in the tree and export immediately.

### Lock Checkboxes

Each row and column has a lock checkbox. Locking a player marks them as assigned (already paired this round), which affects the calc panel guidance and excludes them from tree calculations.

### Rating System

- Active scale is shown in Data Management → Rating System.
- Supported: `1-3`, `1-5`, `1-10`.
- Changing the scale normalizes all existing ratings to the new range automatically.
- Import files may contain values matched to whichever scale was active when they were exported.

---

## 4. Import and Export

### Import Formats

Both **CSV** and **XLSX** are supported for importing player names and ratings.

**Individual team import** — one team's ratings against a named opponent:

- Columns: `team_name`, `player_name`, `opponent_team_name`, `opponent_player_name`, `scenario_id`, `rating`

**Multi-team import** — multiple teams in one file; each row identifies both sides.

**Names-only import** — a file containing only player names for a team, with no rating data. Useful for seeding a new opponent's roster before ratings are known.

### Import Templates

Use **Data Management → Import Templates** (or **Ctrl+Shift+T**) to download pre-filled template files:

| Template | Description |
|---|---|
| Single Team Import XLSX | XLSX template for one team's ratings |
| Single Team Import CSV | CSV equivalent |
| Multiple Team Import XLSX | XLSX template for multiple teams |
| Multiple Team Import CSV | CSV equivalent |
| Names Only | Roster template — no rating columns |
| Download All (ZIP) | All of the above bundled |

Templates include editable example data showing the exact expected format.

### Export

- **Export CSV** (Ctrl+Shift+S) — saves current team ratings as a CSV file.
- **Export XLSX** (Ctrl+Shift+X) — saves as an Excel workbook.

Exported files can be shared with team members, imported into another database, or used as backups.

### Import Logs

**Data Management → Open Import Logs** (or **Ctrl+Shift+L**) opens the folder where the app writes a timestamped log of every import operation. Check these logs if an import produces unexpected results.

### Captain / Member Handoff Workflow

When team members prepare ratings on different machines and a captain consolidates them:

1. Captain creates the master database and shares team/player naming conventions before data entry begins.
2. Each member exports their individual rating files using Export CSV or Export XLSX.
3. Members send files to the captain without renaming team or player columns.
4. Captain imports each file, reviewing any mismatch warnings before confirming overwrites.
5. Captain exports a verification snapshot after all imports and shares for final review.

**Safe handoff rules:**
- Keep team and player names identical across all files.
- Prefer app-generated export files over manually edited spreadsheets.
- Resolve lineage mismatch warnings before the tournament roster locks.
- Archive the final `.db` file and import logs together.

---

## 5. Tree Generation and Sort Modes

### Generating the Tree

1. Select Team 1, Team 2, and Scenario.
2. Enter ratings in the grid.
3. Click **Generate Combinations** (or **Ctrl+Enter**).

The tree models all possible WTC pairing sequences. Each branch is one complete pairing path from start to finish.

### Tree Cache

Generated trees are cached per team/scenario combination. Switching back to a previously viewed combination restores the tree instantly. Use **Data Management → Clear Active Tree Cache** or **Clear All Tree Cache** (Ctrl+Shift+R) to force a rebuild.

### Sort Modes

Four sort modes are available. Sort buttons appear above the tree. Click again to toggle off and return to original order.

| Button | Shortcut | Best For |
|---|---|---|
| **Strategic Fusion** | Ctrl+1 | General use — balanced C/Q/R with downside guardrail |
| **Counter Pick** | Ctrl+2 | Adaptive opponents who will counter your strategy |
| **Highest Confidence** | Ctrl+3 | Elimination rounds where consistency beats upside |
| **Cumulative Sort** | Ctrl+4 | Maximum theoretical path value |

**Node ordering is decision-owner aware:**
- Friendly choice nodes (your pick) — best options for you appear first.
- Enemy choice nodes (opponent's pick) — opponent's worst options for you appear first.

### Sort Mode Details

**Cumulative Sort** — sums all ratings in each path. Highest total first. Use when you're confident in your ratings and want the maximum-upside path.

**Highest Confidence** — assigns a reliability score to each rating (rating 5 = 95%, 4 = 80%, 3 = 60%, 2 = 35%, 1 = 15%). Penalizes high-variance paths. Use in high-stakes rounds when avoiding a bad outcome matters more than chasing the ceiling.

**Counter Pick** — scores each rating by how well it resists optimal opponent counter-play. Mid-range ratings (3 on 1–5 scale) score highest because they are the hardest to counter; extreme ratings are easier to exploit. Use against adaptive, experienced opponents.

**Strategic Fusion** — weighted combination of cumulative, confidence, and resistance scores with a downside penalty applied. The most general-purpose sort for most situations.

### Explainability

Select or hover over any tree node to inspect its component values:

- **C2** — cumulative score component
- **Q2** — confidence score component
- **R2** — counter-resistance component
- **Regret / downside** — how much worse this path is than the best-case
- **Strategic score** — the combined ranking value

For a full description of each metric, open **Tooltip Numbers Guide** in Data Management.

---

## 6. Calculations Panel

The calculations panel (to the right of the rating grid) provides per-player guidance based on the current grid values and lock state:

- **Floor** — the worst rating this player has against any remaining opponent.
- **Pin** — players this person can "pin" (force opponent into a bad choice).
- **Protect** — matchups worth protecting (high-value pairings to preserve).
- **Bus** — sacrifice candidates whose loss costs little.

Lock a player's row to mark them as already paired. The panel recalculates automatically.

If guidance looks stale, toggle a lock checkbox once or use **Refresh UI** from Data Management.

---

## 7. Flip Grid

**Flip Grid** switches your view to the opponent's perspective.

- Player names swap sides visually.
- Ratings invert around the midpoint of the active scale (e.g. around 3 on a 1–5 scale), showing how the opponent sees each matchup.
- **Do not Save Grid while flipped.** Saving in flipped mode would write the inverted values to the database.
- Flip back to the friendly-team view before clicking Save Grid.

Shortcut: **Ctrl+F**. Flip state is shown in the window title.

---

## 8. Data Management Menu

Open with the **Data Management** button in the top bar, or **Ctrl+D**.

### Import / Export section

| Action | Description |
|---|---|
| Import CSV | Import a CSV file of ratings or names |
| Import XLSX | Import an Excel file of ratings or names |
| Export CSV | Export current team ratings as CSV |
| Export XLSX | Export current team ratings as XLSX |
| Import Logs | Open the import logs folder |
| Import Templates | Download template files for data entry |

### Team / Grid section

| Action | Description |
|---|---|
| Load Grid | Load saved ratings for the current selection |
| Refresh UI | Reload all dropdowns and recalculate |
| Get Score | Show the cumulative score for the current grid |
| Save Grid | Write current ratings to the database |
| Create Team | Add a new team |
| Delete Team | Remove a team and all associated data |

### Settings section

| Action | Description |
|---|---|
| Rating System | Change the active rating scale (1-3 / 1-5 / 1-10) |
| Switch Database | Open a different `.db` file |
| Clear Active Tree Cache | Rebuild tree for the current matchup on next generate |
| Clear All Tree Cache | Remove all cached trees |

### Help section

| Action | Description |
|---|---|
| Open Full User Guide | Opens this document |
| Tooltip Numbers Guide | Reference for C2/Q2/R2 and other node metrics |

---

## 9. Keyboard Shortcuts

### Core Workflow

| Shortcut | Action |
|---|---|
| Ctrl+Enter | Generate Combinations |
| Ctrl+S | Save Grid to database |
| Ctrl+R | Recalculate scenario values immediately |
| Ctrl+Z | Undo last shortcut-tracked action |
| Ctrl+Y | Redo last undone action |
| Ctrl+F | Flip Grid perspective |
| Ctrl+G | Focus the top-left rating cell for rapid entry |

### Sort Modes

| Shortcut | Sort Mode |
|---|---|
| Ctrl+1 | Strategic Fusion |
| Ctrl+2 | Counter Pick |
| Ctrl+3 | Highest Confidence |
| Ctrl+4 | Cumulative Sort |

### Grid and Clipboard

| Shortcut | Action |
|---|---|
| Ctrl+C | Copy current 5×5 grid values to clipboard |
| Ctrl+V | Paste 5×5 grid values from clipboard |
| Tab | Next rating cell (within the 5×5 area) |
| Shift+Tab | Previous rating cell |
| Ctrl+I | Open comment editor for the focused matchup cell |

### Data Management and Utilities

| Shortcut | Action |
|---|---|
| Ctrl+D | Open Data Management menu |
| Ctrl+Shift+S | Export CSV |
| Ctrl+Shift+X | Export XLSX |
| Ctrl+Shift+T | Open Import Templates popup |
| Ctrl+Shift+L | Open import logs folder |
| Ctrl+Shift+R | Clear all tree cache |

### Team and Help

| Shortcut | Action |
|---|---|
| Ctrl+N | New Team |
| Ctrl+H | Open Full User Guide |

---

## 10. Saving and Persistence

- **Save Grid** (Ctrl+S) writes current friendly-view ratings to the active database. Do not save while the grid is flipped.
- Team selection, scenario selection, and UI preferences (sort mode, rating system, etc.) persist across sessions.
- Generated tree cache persists for faster reloads when revisiting the same team/scenario combination.
- Database files are standalone `.db` files and can be copied, emailed, or backed up at any time.

---

## 11. WTC Pairing Strategy

### How WTC Snake Pairing Works

**Setup:** Captains roll off. The loser becomes **Team B** (presents first); the winner becomes **Team A**.

**Pairing sequence:**

| Round | Who acts | What happens |
|---|---|---|
| 1 | Team B presents 1 player | Team A offers 2 opponents → Team B picks one → Team A picks table |
| 2 | Team B offers 2 players | Team A picks one → Team B picks table |
| 3–5 | Pattern repeats | Roles alternate each round |

**Final result:** Team B controls 2 matchup outcomes and picks 3 tables. Team A controls 3 matchup outcomes and picks 2 tables.

### Core Strategic Concepts

**Pinning** — holding two players who both beat the opponent's remaining options. Forces the opponent to choose between bad and worse.

**Floor play** — choosing the player whose worst rating against any remaining opponent is highest. Minimizes downside risk. Use when ahead or in conservative situations.

**Ceiling play** — prioritizing players with potential exceptional matchups. Use when behind and needing high-value wins.

**Table selection** — the team that doesn't pick the matchup gets to pick the table. In close scenarios, table advantages (terrain, deployment, scenario mechanics) can swing the result.

### Using the Tree for Real Decisions

1. Generate the tree for the current round's opponent.
2. Apply the sort mode that fits your situation (see Section 5).
3. Read the top branch as your recommended pairing sequence.
4. Use explainability values to understand why a path ranked where it did.
5. Cross-check with the calculations panel for floor/pin/protect guidance.

### Choosing the Right Sort Mode by Situation

| Situation | Recommended Mode |
|---|---|
| Most rounds, balanced approach | Strategic Fusion |
| Elimination / can't afford a bad loss | Highest Confidence |
| Opponent is adaptive and experienced | Counter Pick |
| Need maximum points to catch up | Cumulative Sort |

### Common Tactical Patterns

**Sacrificial lamb** — present a player you are willing to lose with. Forces the opponent to "spend" a good player beating you badly, preserving your strong options.

**False floor** — present what looks like your safest player, but who has a hidden vulnerability. Baits an overconfident response.

**Double threat** — hold two players who both counter the opponent's remaining options. Guarantees at least one excellent matchup regardless of their choice.

---

## 12. Troubleshooting

### Tree ordering looks wrong

1. Confirm **My Team First** toggle is set correctly for your perspective.
2. Regenerate the tree after major rating changes.
3. Reapply the desired sort mode (it may have been cleared).
4. Clear the active tree cache and regenerate.

### Calculation guidance looks stale

1. Toggle any lock checkbox once to force a recalculation.
2. Use **Refresh UI** in Data Management.
3. Regenerate Combinations.

### Import did not work as expected

1. Check the import log (Data Management → Open Import Logs or Ctrl+Shift+L) for the exact error.
2. Verify team and player names in the file exactly match names in the database (case-sensitive).
3. Download a fresh template from Import Templates and compare your file's columns to the template's columns.
4. Ensure the file uses the correct rating scale for the active database.

### Empty dropdowns or "No teams found"

1. Click **Refresh UI** in Data Management.
2. Confirm the correct database is loaded (Data Management → Switch Database).
3. If the database was newly created, use Import to load team data.

### Database creation fails on first launch

Ensure the application has write permission to the folder you selected for the database. Try the Desktop or Documents folder. If the error persists, check the app log file in the application folder.

---

## 13. Recommended Match-Day Routine

### Before the Tournament

1. Import all opponent team rosters (use Import Templates → Names Only if you only have player names).
2. Complete ratings for all opponents you expect to face.
3. Generate trees for your highest-priority matchups and review the top paths.
4. Export and share a consolidated database backup with your team.

### Before Each Round

1. Load the correct opponent team and scenario.
2. Lock any players already paired in previous rounds.
3. Apply the sort mode that fits the round objective.
4. Note your top 2–3 paths and the key pin/floor options from the calculations panel.

### During Pairings

1. Use the tree to validate each decision in real time.
2. If opponent behavior is unexpected, switch sort modes to reframe the analysis.
3. Use Ctrl+C to copy the grid for quick reference if needed away from the screen.

### After Each Round

1. Update ratings if you learned something about a matchup.
2. Save Grid.
3. Clear the active tree cache for that matchup so the next generate reflects new ratings.
4. Note which sort mode best predicted the actual outcome.
