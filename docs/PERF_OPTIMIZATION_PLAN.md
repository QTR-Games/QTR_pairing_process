# Performance Optimization Plan

Consolidate team-change work into a single update cycle, cache team/player data, and batch UI recalculations so grid.load_from_db, grid.scenario_calculations, and comments.update_indicators run once per user action. Add short throttling for scenario recalcs and skip no-op updates to minimize redundant work.

## Steps
1. Audit trigger chains to confirm when update_ui(), load_grid_data_from_db(), on_scenario_calculations(), and update_comment_indicators() fire on team and scenario changes. Document the call graph and current duplicate call sites in UiManager.
2. Implement a team-change transaction in UiManager: on team dropdown change, set a guard flag (for example, _team_change_in_progress), perform all data loads once, then clear the guard. Ensure nested calls short-circuit when the guard is active.
3. Cache and reuse team/player data: introduce a small in-memory cache keyed by team name to player list and team id. Use it in update_round_dropdown_options() and the grid load path to avoid repeated DB queries on the same selection. Provide a cache invalidation path when teams are added, deleted, or imported.
4. Batch UI updates after data load: create a method (for example, _apply_team_change_updates) that calls load_grid_data_from_db(), then a single on_scenario_calculations() and a single update_comment_indicators() after all grid data is set. Ensure GridDataModel.begin_batch()/end_batch() spans the entire load and post-load UI refresh.
5. Avoid full-grid comment refresh: replace per-cell check_comment_exists() loops with a single DB query for all comments for the active team and scenario. Update only indicators whose state changes. Cache the comment map for the current team and scenario and invalidate on comment edits or team or scenario changes.
6. Add throttling for scenario recalculation: schedule on_scenario_calculations() via a single after callback (for example, 100 to 150 ms). On repeated triggers, cancel the prior callback and reschedule to coalesce changes.
7. Short-circuit no-change updates: in dropdown and checkbox handlers, compare new selections with prior state and skip work when unchanged. Extend the existing _updating_dropdowns guard to cover checkbox syncs and update_round_dropdown_options() calls.
8. Add perf spans or counters (optional) around new guard paths to validate reduction in grid.load_from_db, comments.update_indicators, and grid.scenario_calculations calls per user action.

## Relevant Files
- qtr_pairing_process/ui_manager_v2.py
- qtr_pairing_process/grid_data_model.py
- qtr_pairing_process/db_management/db_manager.py

## Verification
1. Run the app with perf logging on. Change teams and scenario and confirm grid.load_from_db, comments.update_indicators, and grid.scenario_calculations appear once per action in perf_log.txt.
2. Validate dropdowns and checkboxes still update correctly when changing teams or selecting rounds.
3. Edit a comment, ensure indicators update correctly without full-grid refresh, and verify cache invalidation.
4. Manually exercise rapid row and column toggles and confirm scenario calculation is throttled and the final state is correct.

## Decisions
- Batch data load and UI refresh into a single team-change transaction and throttle scenario recalculations by about 100 to 150 ms.
- Cache team/player data and comment maps to reduce DB calls; invalidate on team or comment mutations.

## Further Considerations
1. Throttle duration: 100 ms vs 150 ms. Recommendation: start at 120 ms and adjust based on UX.
2. Comment cache scope: per (team1, team2, scenario) vs per scenario only. Recommendation: include team1, team2, and scenario to avoid cross-team leakage.
3. Guard scope: team-change-only vs all dropdown changes. Recommendation: apply to team and scenario changes first, then expand if needed.
