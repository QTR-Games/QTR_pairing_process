# Release Notes - QTR Pairing Process v2.1.1

## What's New

### True-Scale Scoring (replaces bucketed scoring)

The scoring engine now uses a continuous 1-to-max scale instead of discrete buckets. This produces more accurate floor/ceiling calculations and better differentiation between similar matchup paths. The old bucketed system remains available as an opt-in setting but is no longer the default.

### Advanced Strategic Sorting

Three sorting modes are now available on the matchup tree:

- **Cumulative Sort** (default): Ranks paths by summed rating value — highest theoretical score first.
- **Confidence Sort**: Ranks paths by reliability. Penalizes high-variance paths; promotes consistent, predictable outcomes. Best for high-stakes rounds where avoiding losses matters more than chasing maximum upside.
- **Counter-Resistance Sort**: Ranks paths by how well they hold up against optimal opponent counter-play. Midpoint ratings score highest because they are hardest to exploit. Best against adaptive, experienced opponents.

Sort mode is decision-owner aware: friendly-choice nodes place your best options first; enemy-choice nodes place the opponent's worst options (for you) first.

### Sort UI Improvements

Sort controls are cleaner and faster to use. "Remove Sorting" returns the tree to its original unsorted order in one click.

### Matchup Heuristic Improvements

Extract MU Heuristics improvements give better guidance on which matchups to protect, pin, or leave open based on scenario context.

### Data Management Bug Fixes

Multiple fixes to team creation, deletion, and player import/export workflows. Excel (.xlsx) import is now supported in addition to CSV.

### General Stability

Post-v2 touchups including UI polish, performance tuning, and minor regressions fixed from the v2.0 launch.

---

## Known Limitations

- True-scale scoring is Windows-only in this release.
- The bucketed scoring system will be removed in a future release.

---

## Installation

1. Download `QTR_Pairing_Process_v2.1.1_release_bundle.zip` from the GitHub releases page.
2. Unzip anywhere on your PC.
3. Open the unzipped folder and double-click `QTR_Pairing_Process_v2.1.1.exe`.
4. No installer required.

---

## Full Changelog

https://github.com/QTR-Games/QTR_pairing_process/compare/v2.0.0...v2.1.1
