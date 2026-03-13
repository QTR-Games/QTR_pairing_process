# UI Audit and Refactor Report

## Purpose
Document the UI update graph, high-frequency redraw triggers, and the refactor work that reduces redundant updates. This report feeds Phase 2 planning and the checkpoint approval step.

## Scope
- UI update graph coverage
- Redraw and mutation hot spots
- Refactor actions taken
- Approval checklist

## Update graph (map of triggers to UI work)
- update_ui
	- Called from create_team, on_delete_team, on_change_database, import_xlsx, import_csvs
	- Menu action: Data Management -> Refresh UI
- load_grid_data_from_db
	- Called from update_ui, _apply_team_change_updates, _apply_scenario_change_updates
	- Called at Team Grid init (after widgets created) and debug auto-populate (after setting teams)
	- Menu action: Data Management -> Load Grid
- on_scenario_calculations
	- Menu action: Data Management -> Get Score
	- Scheduled by _schedule_scenario_calculations (row/column checkbox changes, paste 5x5, _post_grid_load_refresh)
- update_comment_indicators
	- Called from _post_grid_load_refresh after grid loads
	- Called after comment add/delete in create_comment_dialog
- Tree generation
	- on_generate_combinations (Generate Combinations button)
	- auto_generate_tree_after_teams_loaded via _schedule_tree_autogenerate
	- sync_tree_with_round_1_ante triggers generation if tree absent

## High-frequency redraw triggers
- Instrumentation-only: team_dropdown.trace and scenario_dropdown.trace (trace handlers wrapped around load grid + refresh)
- Instrumentation-only: teams.change.redraw and scenario.change.redraw (update_idletasks measurement spans)
- Instrumentation-only: resize.burst (Configure-driven resize sequences)
- Underlying triggers that remain after removing instrumentation: team dropdown changes, scenario dropdown changes, and root resize events

## Refactor actions taken
- Avoid redundant writes to display grid entries by skipping no-op updates in _update_display_entry_from_model

## Risk and regression notes
- Display fields should still refresh when values change; verify scenario calculations update display grid.

## Approval checklist
### Conservative changes (auto-approved)
- No-op skip for display widget updates in _update_display_entry_from_model

### Moderate+ changes (requires explicit approval)
- None in this checkpoint

## Open questions
- TODO: list questions or decision points needing input
