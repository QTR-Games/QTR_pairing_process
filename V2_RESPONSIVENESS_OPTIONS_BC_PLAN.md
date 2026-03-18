# V2 Responsiveness Plan (Options B and C)

## Purpose
This document captures implementation-ready plans for improving UI responsiveness during heavy generation and sorting operations using:
1. Option B: Cooperative chunking on the UI thread.
2. Option C: Background compute architecture with UI-thread apply.

Option A (busy indicator/status affordances) is intentionally excluded here and remains in the active session plan.

## Problem Statement
During expensive generation/sort paths, long uninterrupted work can block the Tk event loop. This can cause:
1. Window greying and OS "Not Responding" state.
2. Poor user confidence even when processing is still active.
3. Perception of frozen behavior during strategic and initial sort calculations.

## Success Criteria
1. Window remains interactive enough to repaint and avoid OS freeze prompts in typical heavy workloads.
2. Users receive visible, continuously changing progress feedback while operations run.
3. Sorting/generation semantics and output ordering remain functionally identical to current behavior.
4. Existing regression suites continue to pass.

---

## Option B: Cooperative Chunking (Recommended Next Step)

## Summary
Refactor heavy loops into chunked batches that yield back to the event loop between work slices via `after(...)`.

## Why Option B
1. Much lower risk than full threading/process refactor.
2. Compatible with current Tk widget coupling.
3. Significant responsiveness gain if chunk boundaries are chosen well.

## Scope
1. Generation and sort entrypoints in `ui_manager_v2.py` will become orchestration wrappers.
2. Heavy traversal/scoring loops in `tree_generator.py` will be split into resumable batch units.
3. Status/progress updates will occur at chunk boundaries.

## Architecture Outline
1. Add a `WorkChunkRunner` pattern in `ui_manager_v2.py`:
1.1 Start operation and initialize state.
1.2 Execute N units of work.
1.3 Schedule next chunk with `root.after(delay_ms, ...)`.
1.4 Finalize and restore UI state.
2. Represent long operations as resumable state objects:
2.1 Current queue/stack position.
2.2 Partial metric/cache state.
2.3 Progress counters (processed, total_estimate).
3. Preserve deterministic behavior:
3.1 Stable child ordering.
3.2 No change to metric formulas.
3.3 Identical tie-break chain and strategic memo behavior.

## Candidate Targets
1. `ui_manager_v2.py`
1.1 `on_generate_combinations`
1.2 `sort_by_cumulative`
1.3 `sort_by_confidence`
1.4 `sort_by_counter_resistance`
1.5 `sort_by_strategic`
1.6 `apply_combined_sort`
2. `tree_generator.py`
2.1 Strategic/cumulative/confidence/resistance traversals that currently recurse deeply.
2.2 Any full-tree loops that can be batch-processed.

## Implementation Steps
1. Build a generic busy-operation wrapper with chunk scheduling hooks.
2. Convert one path first (recommended: cumulative sort) to validate pattern.
3. Add progress reporting and ETA approximation using processed node count.
4. Roll pattern into remaining sort modes.
5. Refactor generation path last (usually largest surface).
6. Add fallback timeout watchdog and safe abort/recovery behavior.

## Progress UX for Option B
1. Status text examples:
1.1 `Sorting (Strategic): 3,200 / 12,500 nodes`
1.2 `Generating combinations: phase 2 of 4`
2. Use throttled UI updates (for example every 100-250 ms) to avoid excessive redraw overhead.
3. Keep controls disabled while operation active; restore robustly on all exits.

## Risks
1. State-machine complexity can introduce edge-case ordering bugs.
2. Too-small chunk size may increase total runtime due to scheduling overhead.
3. Too-large chunk size may not solve freeze symptoms.

## Mitigations
1. Start with one operation and tune chunk size empirically.
2. Add operation invariants and deterministic snapshot tests.
3. Keep a feature flag to disable chunking during rollout if needed.

## Validation
1. Functional parity tests for all sort modes and generation outputs.
2. Performance logging comparison before/after with large trees.
3. Manual UI stress checks: resize/move window during operation.
4. Existing suite pass: `test_database_preferences.py` and `test_phase11_regression.py`.

---

## Option C: Background Compute Architecture (Stronger Long-Term)

## Summary
Move heavy computation off the UI thread by computing from a non-Tk snapshot model in a worker, then applying results on the UI thread.

## Why Option C
1. Best path for true responsiveness under very heavy workloads.
2. Enables future cancellation and richer progress signaling.
3. Provides foundation for larger performance evolution.

## Core Constraint
Current compute logic interacts directly with Tk tree widgets in many places. Tk is not thread-safe. Therefore, Option C requires decoupling compute from Tk objects before introducing background workers.

## Required Refactor
1. Create a pure data representation of the tree/grid state (`TreeSnapshotModel`).
2. Port heavy scoring/sort logic to operate on snapshot nodes, not Tk widgets.
3. Add mapping layer to apply computed results back to Treeview on UI thread.

## Worker Strategy
1. Preferred initial worker mode: thread for simpler integration.
2. If GIL limits become material, evaluate process-based workers for CPU-heavy strategic paths.
3. Always marshal UI updates via main thread callbacks.

## Architecture Outline
1. UI thread:
1.1 Build immutable snapshot.
1.2 Dispatch worker job.
1.3 Show live status/progress/cancel affordance.
2. Worker:
2.1 Compute metrics/sort order/progress events.
2.2 Emit incremental progress payloads.
2.3 Return final result package.
3. UI thread apply phase:
3.1 Validate operation token (ignore stale results).
3.2 Apply ordering/values/tags in batches.
3.3 Restore controls and clear busy state.

## Candidate New Components
1. `tree_compute_model.py` (snapshot structures)
2. `tree_compute_engine.py` (pure algorithms)
3. `operation_runner.py` (job lifecycle, progress, cancellation)
4. `ui_apply_adapter.py` (maps results back to Tk Treeview)

## Implementation Steps
1. Extract read-only snapshot builder from current tree state.
2. Port one metric path (cumulative) into pure engine for proof of concept.
3. Integrate background runner and tokenized operation lifecycle.
4. Add progress events and cancellation checkpoints.
5. Port confidence, resistance, then strategic pathways.
6. Replace direct heavy Tk traversal in production paths.

## Progress UX for Option C
1. Determinate progress when total work estimate is available.
2. Operation phases displayed explicitly:
1.1 Snapshot
1.2 Compute
1.3 Apply results
3. Add optional cancel action with safe rollback to prior tree state.

## Risks
1. Significant refactor complexity and larger surface for regressions.
2. Requires careful parity validation against existing algorithms.
3. Apply-phase still runs on UI thread and must be batched to avoid stalls.

## Mitigations
1. Implement behind a feature flag and run side-by-side comparison mode in development.
2. Build deterministic parity test fixtures for each sort mode.
3. Batch apply updates (for example 200-500 nodes per tick).

## Validation
1. Algorithm parity tests between legacy and snapshot engines.
2. Soak tests on large datasets.
3. UI responsiveness checks under active compute.
4. Telemetry verification for progress and cancellation events.

---

## Recommendation
1. Implement Option B first for the 2.0 branch to reduce freeze perception quickly with controlled risk.
2. Plan Option C as a staged performance architecture initiative if Option B does not fully eliminate freeze symptoms at scale.

## Suggested Milestones
1. Milestone B1: Chunked cumulative sort + progress text.
2. Milestone B2: Chunked confidence/resistance.
3. Milestone B3: Chunked strategic + generation.
4. Milestone C1: Snapshot model + cumulative worker POC.
5. Milestone C2: Full workerized compute engine parity.
6. Milestone C3: Cancellation + batched apply polish.

## Rollback Strategy
1. Keep non-chunked/non-worker path behind feature flags.
2. Preserve current direct path for immediate fallback if regressions are detected.
