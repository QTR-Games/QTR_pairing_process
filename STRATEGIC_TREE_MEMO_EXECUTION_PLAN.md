# Strategic Tree and Memo Execution Plan

Goal: fix the visible tree corruption bug first (synthetic placeholder children like Node 14498-*), then continue with memoization performance work and optional persistence.

Latest perf evidence from the two newest executions indicates strategic performance regressed and memoization remained ineffective:

- perf_logs/perf_20260317_112529_703716.log vs perf_logs/perf_20260317_112146_304991.log
- strategic end-to-end: 22.37s vs 17.56s (+27%)
- strategic final compute: 10.35s vs 7.10s (+46%)
- recurse_ms: 34.32s vs 27.86s (+23%)
- memo hit-rate: 0% (hits=0, misses=48751 first run)

## Steps

1. Patch blocker bug first: disable synthetic placeholder node generation (highest priority, unblocker).

- Remove or guard demo auto-population in LazyTreeView open handler so expanding leaf nodes cannot inject fake children.
- Keep only real TreeGenerator data in production tree.
- Add or adjust a focused regression check so expanding leaves does not create synthetic Node rows.

1. UI cleanup for Final Matchups Output spacing (depends on step 1).

- Remove summary explainability label creation and pack block from create_matchup_output_panel in qtr_pairing_process/ui_manager_v2.py.
- Keep summary matchups label, summary spread label, and histogram canvas intact.
- Preserve explainability helper methods and guard in update explainability card.

1. Add regression-driven perf triage using newest two runs (depends on steps 1 and 2).

- Treat strategic final compute and recursion overhead as P0 hotspots.
- Add targeted perf markers separating final-score compute from traversal and reordering costs.
- Confirm whether strategic final increase is input-size related or path inefficiency.

1. Baseline and observability hardening (depends on step 3).

- Capture baseline from strategic.memo.stats, sort.apply_combined.total, and strategic.sort.end_to_end.
- Add diagnostics fields: memo_context_hash, memo_key_mode, memo_clear_reason, memo_cleared_entries, strategic_invocation_id.

1. In-memory memo key redesign from transient widget IDs (depends on step 4).

- Replace node-ID memo keys in strategic compute with stable structural keys derived from tree path identity.
- Candidate shape: (depth, sibling_index_chain, normalized_node_text, role_signature).
- Keep keys deterministic across restore and regenerate for unchanged matchup state.

1. Memo context and clear-rule separation (depends on steps 4 and 5).

- Keep strict context tuple for score-sensitive invalidation (strategic parameters plus memo state token).
- Separate clear causes into explicit buckets: state_change, param_change, tree_cache_reset, manual_clear, context_mismatch.
- Clear only on score-relevant state shifts; avoid clears from non-impacting UI operations.

1. UI token stability review (parallel with steps 5 and 6).

- Audit where memo token is set and reset in generation and restore paths.
- Ensure identical tree state yields identical memo token.
- Prevent unnecessary token churn during mode-only sort switching.

1. Correctness and deterministic guardrails (depends on steps 5, 6, and 7).

- Preserve strategic math exactly.
- Validate no ordering drift in opponent-choice nodes and tie-break behavior.
- Validate strategic range normalization remains correct when memo hits are used.

1. Verification gate A: in-memory memo acceptance (depends on steps 4 through 8).

- Warm reruns show meaningful memo hit-rate increase.
- Warm strategic latency drops.
- No regression in ranking correctness.

1. Optional phase: cross-session persistent memoization (depends on gate A pass).

- Add persisted memo artifacts only if in-memory gains plateau and correctness remains stable.
- Persist by strict signature key (state plus strategic params plus version), not runtime widget IDs.
- Add schema versioning and safe fallback when version or signature mismatch.
- Gate behind feature flag or toggle initially for controlled rollout.

1. Verification gate B: persistent memo acceptance (depends on step 10).

- Confirm true warm-up benefit after app restart on unchanged state.
- Confirm strict invalidation on any state or parameter changes.
- Confirm no stale-score incidents; fallback to recompute on uncertainty.

## Relevant Files

- qtr_pairing_process/lazy_tree_view.py
- qtr_pairing_process/ui_manager_v2.py
- qtr_pairing_process/tree_generator.py
- qtr_pairing_process/database_preferences.py
- test_phase11_regression.py
- test_database_preferences.py
- perf_logs/perf_20260317_112529_703716.log
- perf_logs/perf_20260317_112146_304991.log

## Verification

1. Expand previously affected leaf paths and confirm no synthetic Node children appear.
1. Confirm summary explainability block no longer renders in Final Matchups Output.
1. Confirm histogram and Extract Matchups controls shift up without overlap or clipping after resize.
1. Re-run perf and verify whether strategic final and recurse spans remain dominant after instrumentation split.
1. Run strategic sort twice with unchanged state; second run should show non-trivial memo hits.
1. Trigger tree cache restore and rerun strategic; memo reuse should survive restore when state unchanged.
1. Change score-relevant parameter and confirm memo clears with correct reason.
1. Re-run phase11 strategic and chooser regression subset.
1. Optional phase: restart app with unchanged state and confirm measurable warm-up benefit from persisted memo.

## Decisions

Included:

- Tree placeholder-node bugfix before performance changes.
- Strategic final compute and recursion as explicit P0 optimization targets.
- In-memory memo stabilization as first performance priority.
- Persistent memoization as optional second phase with strict safety gates.

Excluded for now:

- Immediate DB schema expansion for memo before in-memory approach is validated.
- Full tree virtualization or lazy node generation changes outside this memo workstream.

## Further Considerations

1. _grid_dirty should remain a performance hint, not the authoritative recalculation gate.
1. Use short-circuiting only when _grid_dirty is false and signatures plus tokens match.
1. Persistence improves cold-to-warm startup behavior, but increases stale-risk and migration complexity.
1. Keep cache design conservative: deterministic keys, strict invalidation, schema versioning, and observable telemetry.
1. Config backup retention recommendation: reduce max_config_backups default from 5 to 3 after short soak period if no rollback need emerges.
