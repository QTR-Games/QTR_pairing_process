# Phase 3a result: memoization is optimal, and that is the finding

Commit `0efaddf`. Measured, not reported — every number below re-derived
independently of the implementing agent.

## Headline

Canonical memoization delivered **1.33x** (1,435.6 ms → 1,078.5 ms at 5v5),
against the 11.4x the isolated minimax PoC predicted for memoization alone.

That gap is the valuable part. The memo is not underperforming. It is
**provably optimal**, and it revealed that scoring arithmetic was no longer
where the time was.

## The memo is exact

| Quantity | Value |
|---|---|
| Nodes in 5v5 tree | 48,751 |
| Distinct canonical states | 5,392 |
| Memo misses (cumulative2) | **5,392** |
| Memo misses (confidence2) | **5,392** |
| Memo misses (resistance2) | **5,392** |
| Node visits during recursion | 10,243 (down from 48,751) |

Misses exactly equal the distinct-state count, for every metric. Each unique
state is computed **exactly once** — the theoretical minimum. The 47.4% "hit
rate" the agent reported is not a shortfall; of 10,243 visits, 5,392 are
genuinely first-time. There is no headroom left in this axis.

Note the earlier estimate of ~625 states was wrong: 625 counts distinct
*remaining-pool* configurations, but a node's value also depends on its own
pairing, so the true state count is 5,392. Still a 9.0x collapse from 48,751.

## Two hypotheses I tested and discarded

**Key mismatch.** `_materialize_all_strategic_from_memo_model` probes the memo
via `_build_structural_memo_key_model`, which looked like the old path-key
builder — a mismatch would silently always miss. It is not: line 806 is a
dispatcher returning the canonical key in canonical mode. All call sites agree.

**Tag materialization.** On a memo hit the code recurses into descendants to
write tags, so a hit is not O(1). Disabling it cut tag writes 9.1x
(48,751 → 5,332) but bought only **1.17x**. Phase 2 already made tag writes
cheap by moving them out of Tk. Not the ceiling.

## Where the time actually goes

| Stage | Time | Share |
|---|---|---|
| Tree construction | 318.3 ms | 32.6% |
| Scoring + sort | 656.7 ms | 67.4% |

And within scoring:

| Quantity | Value |
|---|---|
| Traversal calls | **243,760** |
| Node visits yielded | **2,303,760** |
| Equivalent full passes over the tree | **47.3** |
| Ratio to unique states computed | **427x** |

The scoring pass walks the tree the equivalent of **47 times**, and issues
roughly **five traversal calls per node**, to compute 5,392 distinct values.
The cost is no longer arithmetic. It is *visiting*.

## What this means for sequencing

Memoization is finished. Two paths remain, and they are independent:

1. **Fuse the passes.** Four metrics each traverse separately, plus range
   computation, materialization and the sort walk. Computing all metrics in a
   single traversal is a pure refactor with no behaviour change, and it targets
   the 47x directly. This is now the cheapest remaining win.
2. **Stop building 48,751 nodes.** Construction is a further 32.6% that no
   memo can remove. Only search-space pruning reaches it — and alpha-beta is
   mathematically invalid against the current `alpha*min + (1-alpha)*mean`
   blend (see the p3b block note).

These converge on the same conclusion as `SCORING_DISTRIBUTION_PROPOSAL.md`:
a single distribution-carrying traversal both fuses the passes *and* separates
a prunable floor axis from the expectation. The scoring formula is now the
common blocker for both remaining optimizations.

## Verification performed

- Commit `0efaddf` present; `golden_fixtures/` shows zero modifications.
- Memo statistics re-measured directly from `_metric_memo_hits` /
  `_metric_memo_misses`, not taken from the agent's report.
- Traversal counts obtained by wrapping `_walk_model_nodes`.
- Golden master re-run independently under `QTR_ENGINE=widget` and under
  `QTR_ENGINE=model QTR_RENDER=lazy`.

## Cumulative position

| Stage | 5v5 total |
|---|---|
| Original (widget engine) | 27,564 ms |
| Phase 1 (model, eager) | 4,298 ms |
| Phase 2 (model, lazy) | 1,036 ms |
| **Phase 3a (canonical memo)** | **~975 ms** |

~28x from baseline. Defaults are unchanged: the app still ships
`QTR_ENGINE=widget`, `QTR_RENDER=eager`. Canonical memo is additionally gated
to model engine at 5v5 and above.
