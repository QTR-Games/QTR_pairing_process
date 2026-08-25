# Decision sensitivity: what real roster data says

Status: analysis complete, validated on real data. Informs p4.

> ## ⚠️ Correction (superseded in part)
>
> **The "flat" conclusion below is a scale artifact and should not be read on
> its own.** It is correct that the spread across openers is roughly 1 point out
> of 17 *when measured in points*. It is misleading as a statement about how
> much the decision matters.
>
> Measured as **win probability**, the same decisions on the same rosters span
> roughly **60 percentage points** — e.g. USA Bison ranges from 7.6% to 70.6%.
> Openers that look nearly identical on a points scale are not remotely
> equivalent in how often they win the round.
>
> The flatness is a property of the *units*, not of the decision. This is
> precisely the argument for reporting probabilities rather than unitless
> scores, and it is developed in `SCORING_MATHEMATICS.md` §7.1.
>
> Everything below is left unedited so the original reasoning and its
> correction are both on the record.

The earlier analysis in `REFACTOR_ANALYSIS.md` used **synthetic** rating
matrices drawn uniformly from 1–5. That was the right tool for asking "does
sensitivity vary at all?", but it is the wrong tool for asking "what will my
users see?" This note re-runs the question against the real rosters committed
in the repo and **corrects a conclusion**.

## Data

Three real 5v5 matchups from a past event: the home team versus three
opponents. Ratings are the app's default 1–5 scale where 3 is even, so the
opponent's view of a pairing is the exact complement `6 - r` and the game is
genuinely zero-sum.

The source workbook is no longer committed. It named real players alongside
this team's private ratings of them, which is scouting material in a public
repository; the measurements below are unaffected, because none of them
depended on who anyone was.

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

---

# ⚠️ Finding 5 — supersedes Recommendation item 1

> **The caveat above has now been discharged.** Re-checked against
> `teamthe home team2024_FinalDB.db`: a complete real WTC event, the home team vs
> **31 opponent teams**, all 5v5, 7 scenarios each = 217 real decision
> problems. The compression mechanism is confirmed and much stronger than the
> three-matchup sample suggested.

## 5.1 — The rating grid really is one colour

5,425 real ratings from the event above:

| rating | count | share |
| --- | --- | --- |
| 1 | 161 | 3.0% |
| 2 | 840 | 15.5% |
| **3** | **4,018** | **74.1%** |
| 4 | 406 | 7.5% |
| 5 | 0 | 0.0% |

`SWINETASTIC.db` is the same shape (3 and 4 together = 83.4%). Three quarters
of every matchup ever rated sits on a single value, and the top of the scale is
never used at all.

**Consequence:** rating *differences* carry almost no information. The observed
"3–4 of 5 openers tie exactly" was never a defect in smart sort — it is a direct
arithmetic consequence of the input distribution. No ranking function can
extract separation from a grid that is 74% one number. Signal must come from
**structure** (who holds leverage, and when), not from magnitude.

## 5.2 — The threshold is the hidden variable, and it was wrong

Win probability is defined against a threshold (`Outcome.win_probability`,
`distribution_scoring.py:194-201`): P(total > threshold). Every previous
measurement fixed that threshold at the naive midline, 15 — five games on a 1–5
scale gives totals in 5..25, so 15 is "dead even".

Against **Opponent 01**, at need > 15, all 50 depth-1 lines return
P = 0.0000. Distinct win-probability values: **1**. The app collapses that to
"all choices identical", which presents to the user as *coin flip, doesn't
matter*.

That reading is wrong. The correct reading is **15 is not reachable against
this opponent**. The bar was set outside the achievable range, so naturally
nothing separated. Sweeping the threshold on the same tree:

| need > | min P | max P | spread | interpretation |
| --- | --- | --- | --- | --- |
| 10 | 1.0000 | 1.0000 | 0.0000 | already won — free choice |
| 11 | 0.7086 | 1.0000 | 0.2914 | decision matters |
| 12 | 0.3417 | 1.0000 | 0.6583 | decision matters |
| **13** | **0.0802** | **1.0000** | **0.9198** | **8% vs certainty** |
| 14 | 0.0000 | 0.2734 | 0.2734 | decision matters |
| 15+ | 0.0000 | 0.0000 | 0.0000 | unreachable |

There was no coin flip. There was a **0.92 probability swing** sitting one
threshold below where the app was looking.

## 5.3 — The reachable band is opponent-specific

Same sweep against **Opponent 04** on the same scenario:

| need > | spread | interpretation |
| --- | --- | --- |
| 10 | 0.0000 | already won |
| 11 | 0.4196 | decision matters |
| 12 | 0.8103 | decision matters |
| 13 | 0.9434 | decision matters |
| 14 | 0.3993 | decision matters |
| 15 | 0.0312 | decision matters (barely) |
| 16+ | 0.0000 | unreachable |

Opponent 04's decision band extends to 15; Opponent 01's stops at 14.
**How much your choice matters, and the target it should be aimed at, are
properties of the opponent — and the app currently exposes neither.**

## 5.4 — What this supersedes

Recommendation item 1 above ("say when a decision does not matter") is
**withdrawn**. It was derived from measurements taken at a single, and usually
unreachable, threshold. Reporting "these are tied" in that situation is not
honesty — it is the tool failing to notice it was asked the wrong question.

The replacement framing:

1. **Find the reachable band first.** Compute the range of thresholds where
   `0 < P < 1` for at least one line. Below it the match is already won; above
   it, already lost. Optimising outside the band is wasted effort.
2. **Report leverage per threshold.** `spread = max P − min P` across the
   available choices *is* the "does this decision matter" number, and it peaks
   somewhere inside the band (0.92 at need > 13 above).
3. **Aim at the target the situation demands.** A team that must win reads the
   top of the band and plays to its outs; a team that must not lose reads the
   bottom. Same tree, different column, genuinely different move.

## 5.5 — Reproduction

Session artifacts (not committed), under the session `files/` directory:

- `inspect_real_dbs.py` — schema plus rating histograms for every supplied `.db`
- `probe_db_shape.py` — scenario/team/pair coverage of the event database
- `probe_real_signal.py` — distinct-value counts per objective, per opponent
- `probe_leverage.py` — the threshold sweeps reproduced in 5.2 and 5.3

Opponent ratings are reconstructed with the app's own convention,
`opponent view = 6 − our rating` (`ui_manager_v2.py:8219-8226`), so the model is
strictly zero-sum. Model-engine runs must pass
`golden_master_environment({"QTR_ENGINE": "model", "QTR_RENDER": "lazy"})`;
the harness otherwise pins `QTR_ENGINE=widget` and `model_root` is `None`.

---

# Finding 6 — the engine's optimism, measured in points

You asked, of separating your choice from their response: *"how do we actually
measure or address this scientifically?"* This is the answer to the first half
of it. It turns a judgement call — "does the engine assume the opponent
cooperates?" — into a number with units.

## 6.1 — The test

The same convention that makes the app work also makes it falsifiable. If your
read of a matchup is a 5, theirs is a 1; across five games the two teams' round
totals must sum to exactly 30. That is arithmetic, not modelling.

So solve the same tournament twice: once from your seat, once from theirs, with
the players swapped, every rating flipped to `6 − r`, and the who-picks-first
flag inverted. Then measure

```
excess = (what we think we score) + (what they think they score) − 30
```

If the scoring rule is fair, that is zero. If it quietly lets each side assume
the other will be helpful, **both** sides come out ahead of reality and the
excess is positive. It is denominated in tournament points, so the size of the
error is directly readable.

Before trusting any of it, the harness checks the mirror is real: under a purely
optimistic rule the two seats must value the game *identically*. They did, on
all six matchups — 15/15, 15/15, 16/16, 16/16, 16/16, 17/17. A construction bug
would almost certainly have broken that symmetry.

## 6.2 — The result

the home team 2024, six opponents, scenario 0. Conserved total 30.

| rule | mean excess | min | max |
|---|---|---|---|
| optimistic — `max()` everywhere (today's `cumulative` metric) | **+1.667** | 0.000 | +4.000 |
| minimax — `min()` at their levels | **−1.833** | −3.000 | 0.000 |
| quantal — what the scoring engine actually ships | **−0.181** | −1.040 | +1.089 |

Two things fall out, and the second one I did not expect.

**The optimism is real and it is large.** Against Opponent 06, both teams
conclude they will take 17 points out of 30. Somebody is wrong by 4 points —
which, on your scale, is most of a game. The rule never underestimates on any
matchup tested, which is the signature of a bias rather than noise.

**But flipping `max` to `min` is not the fix.** This is the part worth sitting
with. Pure minimax — assume they always find your worst line — is wrong by
almost exactly as much, just in the other direction. Both sides brace for their
own worst case, and both cannot be right. It *feels* like the conservative,
safe choice, and it is measurably no more honest than optimism.

Only modelling the opponent as *good but fallible* lands near zero — and it does
so about ten times more accurately than either extreme.

## 6.3 — What this means for you

Your axiom was that you must assume the opponent sees the same numbers you do,
mirrored. That assumption now has a test attached, and the engine that ships
passes it while the two obvious alternatives fail it in opposite directions.

Concretely:

1. **"Assume the worst" is not the safe default it looks like.** If you have
   ever felt the tool was too pessimistic about a line, this is why that instinct
   was worth listening to. Minimax feels conservative and is measurably no more
   honest than optimism.
2. **The bias is a property of the rule, not of your data.** Optimism never
   underestimated on any matchup tested; minimax never overestimated on any.
3. **This does not decide anything on its own.** Changing a propagation rule
   changes displayed scores and will fail the golden master by design. That is a
   re-baseline, and it belongs in the hand-walk you asked to do when you can
   concentrate on it — not in a quiet commit.

## 6.3a — Correction: which code path you actually see

**I got this wrong the first time and told you so out loud, so it is recorded
here too.** I originally reported that the `cumulative` column in the sort UI
carried the +1.667 optimism. It does not.

The v2 UI's `cumulative` sort mode routes to a *different* function:

```
ui_manager_v2.py:5477
    run_metric("cumulative", ..., self.tree_generator.calculate_all_path_values_enhanced)
```

`calculate_all_path_values_enhanced` is the `cumulative2` rule. The pure-`max`
function that measured +1.667 is `calculate_all_path_values`, and it is
reachable from only two places, neither of which is the shipping v2 UI:

- `ui_manager_v1_original.py:1095` — the original UI, your stable fallback
- `golden_master_harness.py:33` — the test harness

So the optimism is real, but it lives in the v1 path and in a test fixture. It
was never the number in your v2 sort column.

## 6.3b — What your sort column *actually* does

`cumulative2` aggregates opponent levels as `α·min + (1−α)·mean`, with `α`
defaulting to `0.80` (`tree_generator.py:736-741`). `α=1.0` is pure minimax;
`α=0.0` is "the opponent picks at random". So it is a dial between the two
failure modes measured above — and the conservation law can locate the honest
setting on it.

Sweeping `α` across the same six real opponents:

| α | mean excess | reading |
|---|---|---|
| 0.00 | +0.554 | opponent picks at random |
| **0.20** | **+0.043** | **least biased on this data** |
| 0.40 | −0.455 | |
| 0.60 | −0.934 | |
| **0.80** | **−1.397** | **shipped default** |
| 1.00 | −1.833 | pure minimax |

So the correction cuts both ways. Your sort column is **not** flattering you by
+1.7 as I said. It is doing the opposite: at the shipped `α=0.80` it is
**pessimistic by −1.40**, which is most of the way to full minimax — the very
rule Finding 6 shows is no more honest than optimism.

Two things follow, and the second is the useful one:

1. **The direction of my earlier claim was backwards.** The column understates,
   it does not overstate.
2. **`α` is not a hand-tuned constant any more.** It is already a user
   preference (`database_preferences.py:149`), and conservation now gives it a
   *measurable* correct value rather than a guessed one. Moving `0.80 → ~0.20`
   takes the metric from −1.40 to +0.04 without touching a single line of
   scoring logic.

That `α≈0.2` also lands near the quantal engine's −0.181 is corroborating: two
independently-derived rules agreeing near zero is more convincing than either
alone.

**Caveat I will not paper over:** conservation is a *necessary* condition, not a
sufficient one. `α=0.20` makes the model stop contradicting itself; it does not
prove it predicts real opponents. It is a far better grounded default than a
value that is provably self-inconsistent by 1.4 points, and that is the whole
claim.

## 6.4 — What it does *not* answer

It measures whether the engine is *biased*. It does not yet separate what you
control from what they do to you. The 0.92 swing in Finding 5 is still measured
across all 50 depth-1 nodes, which bundle your opening pick with their reply.
That decomposition is the other half of your question and is still open.

## 6.5 — Reproduction

- `test_zero_sum_conservation.py` (repo root) — the permanent guard. Hermetic,
  synthetic 4v4, no external database, 4 tests in ~1.6s. Includes the
  mirror-fidelity check as a precondition, so the conservation numbers cannot be
  trusted spuriously.
- `probe_conservation.py` (session `files/`) — the real-data probe that produced
  the table in 6.2.

On the synthetic 4v4 grid the effect is starker than on real data: both seats
claim 16 points out of a possible 24, an excess of **+8.0**. Real rosters are
flat (Finding 1), which compresses the bias — it does not remove it.

The mathematics is written up in `docs/SCORING_MATHEMATICS.md` §3.4, where it
now stands as the fourth and only *external* validation check on the scoring
engine.


---

# Finding 7 — separating what you control from what they do to you

*This is the measurement asked for as "how do we actually address this
scientifically." It settles the caveat that every earlier number in this
document carries: the swing was measured across depth-1 nodes, which bundles
**your opening pick** together with **their reply**, so none of it was
attributable to either side.*

## The method

Both halves are measured in round points on the same board, so they compare
directly:

| Quantity | Definition | Whose decision |
|---|---|---|
| **Choice range** | spread of guaranteed value across *our* legal openings | ours |
| **Response range** | spread of value across *their* replies, once we have committed to our best opening | theirs |

Choice range asks: how much does it cost to open badly, if they answer
perfectly? Response range asks: once we have opened well, how much does their
answer still move the result?

Measured on all 31 real WTC 2024 boards. Harness:
`webapp/src/engine/measure.decompose.test.ts`.

## The result

```
our choice     mean 0.48   median 0.00   max 1.0
their reply    mean 1.26   median 1.00   max 2.0

Their reply outweighs our choice on 20/31 boards.
Our choice is worth literally nothing on 16/31 boards.
```

Three things follow, and the third is the important one.

1. **Their reply is worth about 2.6x your opening choice.** The half of the
   decision you do not own dominates the half you do.

2. **On 16 of 31 boards your opening choice is worth exactly zero.** Not
   "nearly zero" — every legal opener guarantees the identical round total. The
   median board is one of these. This is the honest, quantified version of the
   "everything ties" complaint.

3. **Therefore ranking openers cannot be the product.** On the median board
   there is nothing to rank. An app whose central feature is sorting openings by
   score is, on half its inputs, sorting numbers that are all the same — and
   presenting the arbitrary winner as a recommendation.

## What this justifies

This is an independent argument for the opportunity profile, arrived at from
the opposite direction. If our choice is worth 0 and their reply is worth 2.0,
then the only lever left is **which option gives them the most ways to go
wrong** — how much upside is on the table, and how many of their replies take
it away. That is precisely what `optionProfile` reports, and it is why the
tie-break is not a cosmetic addition: on 16 of 31 boards it is the *only*
information available.

It also reframes "play to your outs" as measurable rather than folkloric. When
every opener guarantees the same floor, the choice between them is entirely a
choice about their error surface. There is no floor left to trade away.

## Caveats, stated plainly

- Measured at the opening only. Later decisions may attribute differently, and
  this does not claim otherwise.
- `response` is taken as the upside of the opening the app would actually
  recommend (the highest-upside option among tied-best openings). Using the
  worst tied option instead lowers the response figure; the direction of the
  result does not change, but the 2.6x ratio would.
- Both quantities are computed against *our* grid, under the bound described in
  `protocol.ts` — the opponent minimises our total. That bound survives not
  knowing their grid (Finding 12, the mirror axiom is false), but it is a bound,
  not a prediction of their preferences.

## Supersedes

The correction block at the top of this document cites a win-probability span
of roughly 7.6%–70.6% on USA Bison. **That figure predates the threshold fix
and the protocol-aware engine and should not be quoted.** The points-versus-
probability argument it was making still stands; the specific numbers do not.
Finding 7 is the current, re-measured statement of how much a decision matters.
