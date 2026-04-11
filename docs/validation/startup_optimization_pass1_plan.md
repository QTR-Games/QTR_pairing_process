# Startup Regression Optimization Plan (Pass 1)

Date: 2026-03-20
Owner: Performance validation track
Scope: Startup-path regressions from controlled 5x5 comparison

## Objective

Execute a first targeted optimization pass against the two highest-value startup regressions while preserving behavior and existing Phase 2 lazy-gating logic.

## Execution Status

Current state as of 2026-03-20:
1. Phase A instrumentation is complete in qtr_pairing_process/ui_manager_v2.py.
2. Matchup output panel lifecycle regression is fixed and guarded (startup + generate + extract paths).
3. Strict pass1 comparison artifacts are generated:
- docs/validation/perf_summary_pass1.md
- docs/validation/perf_summary_pass1.csv
- docs/validation/perf_capture_pass1_5x5/
4. Phase A exit criteria are met for startup spans.
5. Phase B/C entry reached.

Active next slice (Phase B/C):
1. Phase B: reduce startup.initialize_ui_vars overhead by targeting eager tree/root setup cost centers.
2. Phase C: continue per-cell grid creation micro-optimizations while preserving all interactions.

## Evidence Summary (Controlled 5x5)

Source artifacts:
- docs/validation/perf_summary.md
- docs/validation/perf_summary.csv
- docs/validation/perf_capture_5x5/

Startup FAIL triage:
1. startup.initialize_ui_vars: likely true regression, high impact (+130%, about +664 ms median).
2. startup.create_ui_grids: mixed but likely real regression (+88% median; one pathological outlier, but non-outlier runs still slower).
3. startup.select_database: likely true regression but low absolute impact (single-digit ms).
4. startup.populate_dropdowns: likely noise/low-value target (sub-millisecond absolute delta).

Pass 1 targets only items 1 and 2.

## Included and Excluded Scope

Included:
- Add finer-grained startup/grid instrumentation to decompose hotspots.
- Optimize startup.initialize_ui_vars and startup.create_ui_grids.
- Re-run controlled 5x5 validation and strict gate summary generation.

Excluded:
- Sort-path algorithm changes.
- Perf threshold policy changes.
- Broad UI redesign.

## Plan

### Phase A: Baseline Decomposition

1. Add PerfTimer sub-spans inside initialize_ui_vars to isolate:
- LazyTreeView construction
- TreeGenerator construction
- setup/theme assignments
- immediate cache/setup work

2. Add PerfTimer sub-spans inside create_ui_grids to isolate:
- rating cell construction
- display cell construction
- binding attachment cost
- initial value population/writes

3. Capture a controlled 5-run set and produce a sub-span decomposition table (median + spread).

Exit criteria:
- Every major startup sub-step has measurable timing.
- Hotspot ranking is based on measured sub-spans, not assumptions.

### Phase B: Target 1 Optimization (startup.initialize_ui_vars)

1. Audit eager constructor side-effects in:
- qtr_pairing_process/lazy_tree_view.py
- qtr_pairing_process/tree_generator.py

2. Defer non-critical eager setup until first use where behavior-safe.

3. Add explicit one-time init guards to prevent duplicate initialization paths.

4. Remove repeated startup allocations where reusable constants/objects are safe.

5. Re-run focused startup tests and controlled capture.

Exit criteria:
- Median for startup.initialize_ui_vars decreases materially.
- No behavior regressions in startup, tree interaction, or extraction path.

### Phase C: Target 2 Optimization (startup.create_ui_grids)

1. Reduce per-cell repeated work in construction loops:
- precompute reused callable references
- avoid redundant writes/state toggles when values are unchanged
- defer non-essential bindings where behavior-safe

2. Preserve all current interactions:
- comment editor access
- tooltip behavior
- editability rules

3. Re-run focused tests and controlled capture; track both median and outlier frequency.

Exit criteria:
- Median for startup.create_ui_grids decreases.
- Outlier behavior does not worsen.

### Phase D: Validation Gate

1. Regenerate strict summary:
- docs/validation/run_controlled_perf_compare.ps1 -LogDir docs/validation/perf_capture_5x5 -BaselineGlob "baseline_*.log" -NewGlob "new_*.log" -MinSamplesStartup 5 -MinSamplesSort 5

2. Compare before/after for targeted spans:
- absolute ms saved
- delta % change
- threshold status change

3. Record residual risks and pass-2 recommendation.

Exit criteria:
- Updated docs/validation/perf_summary.md and docs/validation/perf_summary.csv produced from controlled windows.
- Clear go/no-go recommendation for next pass.

## Implementation Targets

Primary code files:
- qtr_pairing_process/ui_manager_v2.py
- qtr_pairing_process/lazy_tree_view.py
- qtr_pairing_process/tree_generator.py

Validation tooling:
- docs/validation/capture_controlled_5x5.py
- docs/validation/run_controlled_perf_compare.ps1
- docs/validation/generate_perf_summary.py

## Verification Checklist

1. Run startup-focused regression tests covering grid/tree initialization behavior.
2. Execute controlled capture windows (minimum 5 baseline, 5 new).
3. Regenerate strict summary with sample gates at 5/5.
4. Confirm median improvements for:
- startup.initialize_ui_vars
- startup.create_ui_grids
5. Manually smoke-check startup flow:
- DB auto-load
- tree readiness
- grid edit behavior
- comments and extraction path

## Decision Rules

1. Prioritize absolute milliseconds saved over raw percentage on tiny spans.
2. Treat startup.initialize_ui_vars as first optimization gate; it is the dominant startup cost increase.
3. Defer startup.select_database and startup.populate_dropdowns until top-two spans are improved.
4. Keep controlled 5x5 results as the source of truth for claims.

## Risks and Mitigations

Risk: Optimizing the wrong hotspot due to aggregate-only timing.
Mitigation: Require Phase A sub-span instrumentation before major refactors.

Risk: Behavior regressions from deferred initialization.
Mitigation: Add one-time guards plus startup/tree/grid smoke checks.

Risk: Overfitting to a single pathological run.
Mitigation: Evaluate medians plus spread and report outlier frequency separately.

## Pass-2 Candidate (If Needed)

If startup still fails after pass 1:
1. Analyze startup.select_database path (config and preference retrieval timing).
2. Add lightweight stabilization for grid outlier conditions if variance remains high.
