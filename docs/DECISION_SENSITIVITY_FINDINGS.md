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

---

# ⚠️ Finding 5 — supersedes Recommendation item 1

> **The caveat above has now been discharged.** Re-checked against
> `teamIrving2024_FinalDB.db`: a complete real WTC event, Team Irving vs
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

Against **Australia Spangled**, at need > 15, all 50 depth-1 lines return
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

Same sweep against **Canada Goose** on the same scenario:

| need > | spread | interpretation |
| --- | --- | --- |
| 10 | 0.0000 | already won |
| 11 | 0.4196 | decision matters |
| 12 | 0.8103 | decision matters |
| 13 | 0.9434 | decision matters |
| 14 | 0.3993 | decision matters |
| 15 | 0.0312 | decision matters (barely) |
| 16+ | 0.0000 | unreachable |

Canada Goose's decision band extends to 15; Australia Spangled's stops at 14.
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

