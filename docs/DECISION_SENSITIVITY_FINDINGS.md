# Decision sensitivity: what real roster data says

Status: analysis complete, validated on real data. Informs p4.

The earlier analysis in `REFACTOR_ANALYSIS.md` used **synthetic** rating
matrices drawn uniformly from 1–5. That was the right tool for asking "does
sensitivity vary at all?", but it is the wrong tool for asking "what will my
users see?" This note re-runs the question against the real rosters committed
in the repo and **corrects a conclusion**.

## Data

`DapperBadgersImport1.xlsx` contains three real 5v5 matchups: Dapper Badgers
vs USA Condor, USA Jackrabbits, and USA Bison. Ratings are the app's default
1–5 scale where 3 is even, so the opponent's view of a pairing is the exact
complement `6 - r` and the game is genuinely zero-sum.

Scripts (session artifacts, not committed): `real_data_sensitivity.py`,
`leverage_by_depth.py`, `upside_among_ties.py`.

## Finding 1 — real rosters are far flatter than synthetic ones

| Matchup | Guaranteed value by opener | Spread | Openers tied optimal |
|---|---|---|---|
| vs USA Condor | 17, 17, 17, 17, 16 | **1.0** | 4 of 5 |
| vs USA Jackrabbits | 18, 18, 18, 18, 17 | **1.0** | 4 of 5 |
| vs USA Bison | 17, 17, 17, 16, 16 | **1.0** | 3 of 5 |

A spread of 1 point on a ~17 point total is about **6%**. The synthetic
uniform case suggested 32% of rosters would have a materially consequential
opener. Real rosters do not look like that, because real ratings cluster in
2–4 — players on comparable teams are comparable. The synthetic "tiered
ladder" case (0% sensitivity) is much closer to reality than the uniform case.

**This matters because the current "smart sort" presents a single best opener.
On real data, 3–4 of the 5 openers are exactly tied.** The UI implies a
precision the underlying data does not support, and invites the user to agonise
over a choice that is provably a coin flip.

## Finding 2 — a hypothesis I got wrong

If the opening barely matters, the obvious guess is that leverage lives later,
in the responses. Measured across all three matchups:

| Depth | Decisions | Avg spread | Max | Exact ties |
|---|---|---|---|---|
| 0 | 15 | 1.40 | 3 | 7% |
| 1 | 300 | 1.07 | 3 | 12% |
| 2 | 1,800 | 0.81 | 3 | **36%** |

Leverage **decreases** with depth and ties become more common. The guess was
wrong. The tree is not back-loaded; it is flat throughout, and the largest
single swing available anywhere is 3 points.

## Finding 3 — the axis the app is missing

Ranking by guaranteed floor cannot separate tied choices. Adding a second
axis — expected value against an opponent who does not play perfectly —
does:

| Matchup | Opener | Floor | vs random | Upside |
|---|---|---|---|---|
| vs USA Jackrabbits | Pete | **17.0** | 17.71 | 0.71 |
| | Bokur | 16.0 | 17.71 | **1.71** |
| | Dan | 16.0 | 17.58 | 1.58 |
| | Kyle | 16.0 | 17.58 | 1.58 |
| | Jack | 16.0 | 17.50 | 1.50 |

Pete is the safest opener and Bokur is the most opportunistic, and **the app
currently has no way to say that.** It collapses both into one number and
reports a winner. Among choices genuinely tied on floor, the expected-value
tie-break is real but modest (0.21–0.25 points) — worth surfacing, not worth
overselling.

## What this means for p4

The valuable feature is not a better single ranking. It is:

1. **Say when a decision does not matter.** "Any of these four openers
   guarantees 17" is more useful, and more honest, than silently ranking them.
   36% of deeper decisions are exact ties.
2. **Report two axes, not one.** Floor is the guarantee against a good
   opponent; expected value is the payoff if they slip. A team that must win
   should read a different column than a team that must not lose. This is
   tournament-situation-dependent and the app should not decide it for them.
3. **Scale the confidence to the evidence.** With a maximum swing of 3 points
   anywhere in the tree, presenting a decisive-looking recommendation is
   miscalibrated.

Caveat worth stating: this is three matchups from one team's data. The pattern
is consistent across all three and has a plausible mechanism (real ratings
compress toward the middle), but it should be re-checked against more saved
scenarios before any of it is hard-coded into the UI.

## Dependency note

The two-axis calculation needs expected value alongside minimax. Both come
from the same traversal, so p4 should land **after** p3b (alpha-beta), and
the expected-value pass must not be pruned — pruning is only valid for the
minimax axis. That is an easy and quiet way to get wrong numbers.
