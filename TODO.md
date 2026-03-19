# Project To Do

All items from the previous backlog are now implemented.

## Completed

- [x] Parameterization via config in KLIK_KLAK_KONFIG.json is wired.
- [x] Automated regression tests for v2 and strategic3 are added.
- [x] Performance memoization for strategic3 recursion is implemented.
- [x] v2 tuning parameters load from config with safe defaults and validation.
- [x] Deterministic ordering and first-pass strategic behavior are covered by targeted tests.
- [x] Explainability includes strategic breakdown details (C2/Q2/R2/downside/final score surfaces).
- [x] Best-node sorting is applied at each tree decision level for first pass and manual sort actions.
- [x] Calc grid optimization and lock-in-aware caching are implemented.
- [x] BUS advisory logic is implemented as display guidance.
- [x] Basic strategy heuristics are incorporated into ratings/sorting logic.
- [x] Alphabetic sorting default path is removed from normal advanced sorting workflow.
- [x] Default for "My Team First" is unchecked.
- [x] Integration test module for generated_tree_cache persistence and generation-id propagation is added.
- [x] Data Management actions to clear generated_tree_cache for active matchup or all matchups are added.
- [x] Targeted chooser-direction regression tests are added:
  - [x] My Team First unchecked: friendly-choice sibling sort is descending by strategic value.
  - [x] My Team First checked: chooser-direction flips correctly by depth owner.
- [x] Flip Grid display bug fixed (model updates now trigger UI refresh while remaining display-only).
- [x] Quick guide added for reading tree choices and sort behavior.
- [x] Tooltip numbers guide added to explain C2/Q2/R2 and pop-up explainability values, with Data Management access.
- [x] Full user guide added for main app workflows, with separate Data Management access.

## New Backlog

- [ ] Harden `_normalize_database_reference` for Windows path edge cases:
  - [ ] UNC paths and mixed separators
  - [ ] Relative paths resolved against config location
  - [ ] Symlink/realpath normalization policy
- [ ] Add a compatibility unit test for `TreeGenerator._read_pref` parity:
  - [ ] Assert raw-path behavior matches `_read_raw_pref`
  - [ ] Assert bounded numeric-path behavior matches `_read_numeric_pref`
- [ ] Add a Modify Team button to data management. This button will allow you to pick a team, and modify the name of the team and/or the names of the players similar to the pop up for creating a team.