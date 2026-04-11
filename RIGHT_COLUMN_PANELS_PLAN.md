# Right Column Panels Plan

## Overview
Add three panels in the right column (Matchup Summary, Notes/Plan, What-if) and allow the user to select which single panel is shown using a Data Management menu dropdown. Reuse the existing right-column container and matchup output panel styling. Wire toggles to existing actions and persist new preferences via DatabasePreferences. Default panel is Notes/Plan.

## Steps
1. Extend the right-column layout to host multiple panels: create a vertical stack inside `matchup_output_container` with three child frames for Matchup Summary, Notes/Plan, and What-if. Show only the selected panel (e.g., `pack_forget`/`grid_remove`). Use the same frame styling and padding pattern as `create_matchup_output_panel()`.
2. Implement Matchup Summary panel:
   - Add a summary frame with title and a compact content area (labels + optional canvas for histogram bars).
   - Data sources:
     - Final matchups: reuse `matchup_output_text` contents or the internal matchups list from `on_generate_combinations()`.
     - Best/worst spread: compute from tree path values or ratings (use TreeGenerator tag values if available) and show min/max/avg.
     - Confidence histogram: derive confidence scores and render 5-7 bins.
   - Update logic: refresh summary when combinations are generated and when sort mode changes (hook into `on_generate_combinations`, `toggle_*_sort`).
3. Implement Notes/Plan panel:
   - Create a small `tk.Text` control with Save/Clear buttons.
   - Persist notes to preferences (new key like `pairing_plan_notes`) with a size cap (4-8 KB).
   - Load notes on startup and update the text widget.
4. Implement What-if panel:
   - Provide toggles for: swap team order, sort mode hints, tree auto-generate, plus a compact legend.
   - Swap team order: reuse `flip_grid_perspective()` and refresh summary/labels as needed.
   - Sort mode hints: display current `active_sort_mode` and a short hint.
   - Tree auto-generate: bind to existing `tree_autogen_var` and `_on_tree_autogen_toggle()`.
   - Compact legend: reuse `color_map` and status bar legend logic.
5. Add Data Management menu dropdown for panel selection:
   - Add a dropdown in the Data Management menu to choose `Matchup Summary`, `Notes/Plan`, or `What-if`.
   - Persist the selection to KONFIG (e.g., `ui_preferences.right_column_panel`) via `DatabasePreferences.update_ui_preferences()`.
   - Default to `Notes/Plan` when no preference exists.
   - When the dropdown changes, immediately switch the visible panel in the right column.
6. Wire refresh flows:
   - On `on_generate_combinations`: update summary panel + histogram + sort hint.
   - On sort toggles: update summary/hints without regenerating the tree.
   - On rating system change: refresh legend colors.
7. Add guardrails:
   - If no tree exists or no matchups computed, show placeholder states.
   - If histogram data missing, render empty bars or hide the histogram area.

## Relevant Files
- qtr_pairing_process/ui_manager_v2.py
- qtr_pairing_process/tree_generator.py
- qtr_pairing_process/database_preferences.py
- KLIK_KLAK_KONFIG.json

## Verification
1. Launch app: right column defaults to Notes/Plan panel.
2. Data Management menu dropdown changes the visible panel immediately.
3. Selection persists after restart (KONFIG updated).
4. Generate combinations: summary updates with final matchups, best/worst spread, and histogram.
5. Toggle sort modes: sort hint text updates; summary remains consistent.
6. Toggle tree auto-generate from What-if panel: setting persists and triggers restart warning.
7. Enter notes, save, restart app: notes persist.

## Decisions
- Single-panel display is controlled from Data Management menu to reduce on-screen clutter.
- Notes/Plan is the default when no preference exists.
- Matchup Summary draws from existing matchup output and tree values to avoid recomputing pairing logic.
- Notes persist as plain text with a size cap.
- What-if panel reuses existing actions (flip grid, sort buttons, tree auto-generate) rather than introducing new logic.

## Further Considerations
1. Data source for summary metrics: use TreeGenerator path values (accurate) vs parsing `matchup_output_text` (simpler).
2. Histogram design: 5 bins (compact) vs 7 bins (detail).
3. Notes persistence: explicit Save button vs auto-save on focus-out.
