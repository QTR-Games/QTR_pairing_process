# WTC 2026 — USA — Pear Master logs

## What this is

One team's complete pairing record from WTC 2026: five rounds, 25 locked
matchups, and every opponent decision point with the rival tool's own verdict
on it.

The rival tool is **Pear Master**, used *by USA*. So "the rival model" here
means the model Pear Master optimises, not a model belonging to USA's
opponents. Getting this backwards leads to picking the wrong population — the
10 cells flagged `nominated_selected_by_them` were made by five *different*
opposing teams and were never a coherent sample of anything.

## Provenance

Primary artefact: five screenshots of the Pear Master session log,
`WTC_2026_USA_PEAR_MASTER_1.jpg` … `_5.jpg`. These are **outside the
repository** and are not committed; they are personal captures.

Everything in `opponent_decisions.csv`, `round_values.csv` and
`guarantees.csv` was transcribed from those images by eye. Treat them as
OCR-grade: the reconciliation tests in `test_opponent_corpus.py` exist
precisely because a hand transcription needs an independent check. They verify
that each round's final guarantee vector equals its final outcome, and that the
outcome's value under `GOOD=+1 / EVEN=0 / SOFT=-10` equals the value the tool
*printed*. All five rounds reconcile at zero residual.

`as_supplied/` holds the two CSVs exactly as they arrived from the sibling
session, unmodified, for audit.

## The supplied CSVs are a lossy projection

`as_supplied/wtc2026_usa_pairing_cells.csv` and `..._decisions.csv` are useful
but incomplete. Relative to the logs they drop six things:

| Dropped | Why it matters |
|---|---|
| The printed round value | Without it the utility recovery is under-determined up to an additive constant — `(+2, +1, −9)` fits the labels equally well. The printed values pin it. |
| The 4th label `H` (HARD DODGE) | Its absence from the CSVs hides that the alphabet has four symbols, not three. |
| Opponent choice sets | No choice set, no counterfactual, no prediction to score. |
| Opponent verdicts | `They slipped` / `They played their strongest line` is the only adversarial signal in the corpus. |
| Per-step guarantee vectors | The only way to check a transcription against itself. |
| `[forced]` markers on decisions | A forced move is not a choice and must leave the denominator. |

They are committed unchanged under `as_supplied/` rather than treated as the
corpus, so that the loss is visible instead of baked in.

## Known limits

- **`HARD DODGE` is unidentified.** It occurs zero times in all five rounds, so
  any weight at all reconciles the data. `RivalLabelUtility.value_of` raises
  `UnidentifiedLabel` rather than silently scoring it as 0.
- **n = 1 team, 1 event, 1 tool.** No generalisation claim is supported. The
  whitepaper names "reading a strategy off five rounds of one team" as its own
  signature failure mode.
- **No rating matrix exists.** The logs carry labels and names, never numbers.
  That is why rating-space models report `NotEvaluable` here rather than a bad
  score — the gap is named, not absorbed into the denominator.
- **Verdicts are Pear Master's judgement, not an outcome.** "They slipped"
  means the tool thought a better line existed, not that the game was lost.

## Adding another event

Drop a sibling directory next to this one containing a `manifest.json` that
names its files, counts and caveats. No code changes.
