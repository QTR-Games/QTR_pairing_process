# Tree Tooltip Numbers Guide

This guide explains the numbers shown in the hover pop-up and explainability text for tree nodes.

## What the pop-up is showing

For a selected tree node, the explainability text summarizes:

- Mode: current sorting mode objective.
- C2: enhanced cumulative path value.
- Q2: enhanced confidence value.
- R2: enhanced counter-resistance value.
- Regret/Range context: how wide child outcomes can spread.
- Strategic score: final fused score used for strategic sorting.

## C2 (Cumulative2)

C2 estimates path value with turn-aware aggregation.

- Higher C2 is better for us.
- At our decision levels, best child branches dominate.
- At opponent decision levels, adverse child branches are weighted in.

Interpretation:

- High C2 means strong projected totals over the continuation path.
- Low C2 means weak continuation value or strong opponent counterplay.

## Q2 (Confidence2)

Q2 estimates reliability, not just upside.

- Higher Q2 is better.
- It penalizes volatility and small-sample uncertainty.
- A node with steady outcomes can outrank one with swingy outcomes.

Interpretation:

- High Q2: safer, repeatable performance profile.
- Low Q2: wider downside risk and less predictable outcomes.

## R2 (Resistance2)

R2 estimates resistance to being countered.

- Higher R2 is better.
- It penalizes large exploitability gaps between best and worst child outcomes.
- It rewards nodes that stay robust across responses.

Interpretation:

- High R2: difficult for opponent to punish.
- Low R2: easier for opponent to force weak follow-ups.

## Regret / downside terms

Regret reflects spread between best and worst reachable confidence outcomes.

- Lower regret is better.
- High regret means branch quality can collapse under bad responses.

Downside in strategic mode applies a penalty from this spread.

## Strategic score

Strategic mode fuses normalized C2/Q2/R2 plus smoothing and penalties.

- Scores may be negative. This is normal.
- Relative ordering among siblings is what matters.
- On our choice node: higher strategic score should appear first.
- On enemy choice node: lower strategic score (worse for us) should appear first.

## Reading sibling order correctly

Always read order in context of decision owner:

- Friendly decision node: best-for-us first.
- Enemy decision node: worst-for-us first.

The app handles this automatically by node ownership and depth rules.

## Practical workflow

1. Pick a sort mode based on intent.
2. Hover top candidates and compare C2/Q2/R2.
3. Check if a high-score node is driven by one component only.
4. Prefer balanced nodes unless your round plan requires a specific risk profile.
