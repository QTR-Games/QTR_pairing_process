# Proposal: propagate distributions instead of scalars

Status: analysis complete, measured. Not implemented. Supersedes part of p4.

You asked whether there is a better way to score, especially a more efficient
one. There is, and unusually it is both — but it changes results, so it must be
opt-in and shown side by side rather than swapped in.

## What the code already tells us

`_calculate_confidence_scores_enhanced_model` computes:

```python
mu           = sum(child_scores) / len(child_scores)
variance     = sum((s - mu) ** 2 for s in child_scores) / len(child_scores)
sigma        = math.sqrt(variance)
conservative = mu - (k * sigma) - (u / math.sqrt(n))
regret2      = max(0, ceiling2 - floor2)
```

Mean, variance, a lower confidence bound, a regret range. **These are moments
of a distribution.** The app is already reaching for a distribution and
reconstructing it from summary statistics via a Gaussian approximation, with
three hand-tuned constants: `cumulative2_alpha = 0.80`, `confidence2_k = 0.85`,
`confidence2_u = 12.0`.

Carrying the distribution itself replaces the approximation with the exact
quantity, and removes all three knobs.

## Why points hide your real decisions

Points and win probability are different objectives. A WTC round is won by
crossing a threshold, not by accumulating points: with 1–5 ratings and
complementary opponent values the two totals sum to 30, so we win above 15.

Measured on the three real matchups in `DapperBadgersImport1.xlsx`
(`points_vs_winprob.py`, opponent modelled as boundedly rational, λ=1.0):

| Matchup | Point spread across openers | Win-probability spread |
|---|---|---|
| vs USA Condor | 0.87 | 61.0% → 100% |
| vs USA Jackrabbits | 1.52 | 64.7% → 100% |
| vs USA Bison | **0.39** | **38.7% → 66.1%** |

The Bison row is the important one. In points, best and worst openers differ by
**0.39** — invisible, indistinguishable from noise. In win probability the same
two choices differ by **27 points**.

**This corrects an earlier finding of mine.** `DECISION_SENSITIVITY_FINDINGS.md`
concluded real rosters are "flat" because openers differ by ~1 point out of ~17.
That flatness is an artifact of the scoring scale, not a property of the game.
Points compress near a threshold; win probability expands. The decisions do
matter — the current score cannot see it.

Note also that both objectives selected the *same* top opener in all three
matchups. The value is not in changing the pick; it is in showing how much the
pick is worth, which points systematically understates.

## Cost

Measured at 5v5 scale, memoised on canonical state (`bench_distribution_cost.py`):

| Pass | Median | Memo states |
|---|---|---|
| scalar, one metric | 5.12 ms | 630 |
| **scalar ×4 (as today)** | **20.49 ms** | 630 |
| **distribution (all metrics)** | **9.66 ms** | 630 |

A distribution pass costs 1.89x a single scalar pass but **0.47x the four
passes the app runs today** — less than half — while producing strictly more.
From one traversal you can read floor, expected value, win probability,
variance, regret range and any quantile.

## What this fixes

- **Removes the alpha blend that blocks pruning.** `alpha*min + (1-alpha)*mean`
  produces a number no opponent behaviour actually yields, and its `mean` term
  makes alpha-beta mathematically invalid (see the p3b block note). A
  distribution keeps min and mean as separate readable quantities, so the pure
  floor axis is prunable while the expectation is not — each gets the treatment
  it deserves.
- **Replaces three unprincipled constants with one meaningful one.** `alpha`,
  `k` and `u` become a single opponent-rationality parameter λ, where λ→∞ is a
  perfect opponent and λ=0 is a coin flip. Unlike the current constants, λ is
  calibratable: record real opponent choices and fit it.
- **Makes confidence exact rather than Gaussian-approximated.**
  `mu - k*sigma - u/sqrt(n)` is a normal-approximation stand-in for a low
  quantile. With the real distribution, take the quantile.

## Risks and honest caveats

- **This changes results.** Golden master will fail by design. It needs the same
  deliberate re-baseline treatment as p3c, with a reviewed diff — never a
  fixture regeneration to make tests green.
- The cost benchmark is a synthetic 5v5 with the same branching structure, not
  the app's four real passes. The 0.47x is representative, not a promise.
- `resistance` and `strategic3` were not analysed in the same depth as
  `confidence2`. The claim that a distribution subsumes *confidence2* is well
  supported; that it subsumes all four is not yet established.
- Distributions must stay small. Totals span a bounded integer range, so support
  is naturally tens of buckets. If a future change makes values continuous, this
  approach needs bucketing.
- λ=1.0 was chosen for illustration and is not fitted to real results.

## Suggested sequencing

Land p3a (canonical memo) first — it is exact and benefits any scoring scheme.
Then build the distribution pass **alongside** the existing scores, not
replacing them, so both can be displayed and compared on real scenarios. Only
after it has been trusted on real data should it become the default, and that
should be an explicit decision.
