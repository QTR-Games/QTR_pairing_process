# Phase 2 UI Rebuild for Low Latency

Reorient the UI for speed-first usability by reducing redraw churn, making updates lazy and conditional, deferring heavy UI work, and introducing optional background loading where it materially reduces UI thread blocking. This plan treats the UI as a cohesive system and targets the largest sources of redraw and layout cost discovered in Phase 1.

## Steps
1. Audit the full UI update graph to identify every redraw and widget mutation path that can be skipped when data is unchanged; map call sites that trigger update_ui, load_grid_data_from_db, on_scenario_calculations, update_comment_indicators, and tree generation. Capture findings in a dedicated audit report so they can guide later steps.
2. Refactor internal UI update operations based on the audit: reduce redundant widget writes, consolidate repeated redraw paths, and standardize update flow ordering so later optimizations have a stable, minimal baseline.
3. Checkpoint: share the audit report and refactor summary for approval before proceeding beyond conservative changes. Conservative-only refactors are pre-approved; moderate+ changes require explicit approval.
4. Implement a strict no-op policy: only apply UI updates when data has changed, including grid cell values, display cells, checkbox states, and combobox selections; introduce lightweight dirty flags per UI region to prevent redundant updates.
5. Make dropdown updates fully lazy: only update round dropdowns when the Team Grid tab is active and visible; avoid refresh when the selected teams are unchanged; defer dropdown refresh until after first render with a minimal idle callback.
6. Remove automatic tree generation on startup and team changes; generate the tree only on explicit user action (Generate Combinations), and keep the tree intact across tab switches without re-rendering or recomputing when ratings are unchanged.
7. Introduce tree snapshot caching: store the latest tree structure and metadata in memory and reuse it when teams and scenario match; invalidate cache only when ratings or team selections change.
8. Batch grid recoloring: replace per-cell config() calls with a single pass that updates only cells whose color or state changed; skip color updates while resizing.
9. Add resize optimization: throttle redraw work during <Configure> (resize) bursts; skip expensive updates and apply a final refresh when resizing ends; measure before/after to ensure OS-level lag reduces.
10. Optional background work: load DB data and compute derived values in a background thread, then marshal minimal UI changes back to the main thread using after; ensure UI remains responsive while data loads.
11. Tighten redraw costs: minimize update_idletasks() usage; wrap only when needed and measure its impact; reduce widget count or reparenting where possible.
12. Update perf instrumentation to align with new logic: track skipped updates, cache hits, resize throttling effectiveness, and tree cache reuse to validate gains. Treat these as instrumentation-only and remove once the refactor is complete.

## Relevant files
- qtr_pairing_process/ui_manager_v2.py — central UI behavior, update graph, redraw throttling, tree generation control
- qtr_pairing_process/grid_data_model.py — add change tracking to support no-op policy and selective updates
- qtr_pairing_process/lazy_tree_view.py — tree reuse strategy and lightweight refresh hooks
- qtr_pairing_process/tree_generator.py — cacheable outputs and reuse inputs
- qtr_pairing_process/db_management/db_manager.py — background-safe data access for preloading

## Verification
1. Run python main.py --perf and confirm reduced teams.change.redraw, scenario.change.redraw, and fewer event_loop.lag spikes.
2. Switch tabs repeatedly and confirm no tree regeneration unless Generate Combinations is clicked.
3. Drag-resize the window and confirm resize burst logging shows throttled updates and improved OS responsiveness.
4. Change team dropdowns and confirm no-op updates are skipped (new perf markers or counters show cache hits/skips).
5. Validate that ratings calculations and comment indicators remain correct after changes.

## Audit and refactor report
- Create UI_AUDIT_AND_REFACTOR_REPORT.md capturing the update graph, high-frequency redraw triggers, and refactor actions taken.
- Include a short approval checklist that separates conservative changes (auto-approved) from moderate+ changes (needs explicit approval).

## Decisions
- Tree generation becomes explicit only (Generate Combinations); no auto-generation on startup or team changes.
- Lazy updates are preferred even if they delay some UI elements until the tab is visible or user interaction occurs.
- Background threading is allowed for DB read/compute paths, with UI updates marshaled to the main thread.

## Further considerations
1. Tree cache scope: cache by (team1, team2, scenario, rating system) vs by (team1, team2, scenario) only; recommend including rating system.
2. Resize throttle aggressiveness: 100–200 ms debounce; recommend 150 ms to reduce OS-level lag.
3. UI rebuild scope: keep current layout but reduce dynamics, vs a targeted refactor of the Team Grid tab first; recommend Team Grid first as the highest impact path.
