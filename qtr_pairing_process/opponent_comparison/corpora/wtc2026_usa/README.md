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
`guarantees.csv` was transcribed from those images by eye.

**Per-file transcription grades live in `manifest.json` under `reliability`,
not here.** The manifest is what a consumer actually loads; a warning sitting
in prose beside the data is a warning nobody sees at the point of use.
`load_corpus()` refuses to load a corpus whose declared files are not all
graded, with a reason, so a future corpus cannot quietly skip this.

| File | Grade | Why |
|---|---|---|
| `round_values.csv` | `RECONCILED` | Counts must reproduce the value the tool **printed**. All five rounds at zero residual; rounds 1 and 5 out-of-sample. |
| `opponent_decisions.csv` | `RECONCILED` | Slip counts cross-check against `round_values.opponent_slips`, transcribed from a different part of each log. |
| `guarantees.csv` | `RECONCILED` | 80 integrity checks across 40 rows, all passing. See below. |
| `as_supplied/*.csv` | `AS_SUPPLIED` | Arrived as data files; not transcribed by us. |

### Which artefact wins, and why it matters

**The screenshots are the primary artefact and they are directly readable** —
clean monospace text, no ambiguity between `S` and `5`, `1` and `I`, or `0`
and `O`. Read them.

**Machine-OCR `.txt` dumps of these same screenshots exist in some session
folders. They are lossy and they corrupt the count position:**

```
"OG SN 0S OH"   <- a lossy OCR dump of what the image renders as   0G 5N 0S 0H
"IG 3N IS OH"   <- ... 1G 3N 1S 0H
```

Those strings are artefacts of the OCR pass, **not** of the source. An earlier
revision of this corpus graded `guarantees.csv` `UNRELIABLE_OCR` and named the
images as the reason, on the strength of exactly those two strings. That was
wrong in the direction that destroys data: it would have retired 40 usable
rows because a derivative was noisy. If you are extending this corpus and you
find both forms, **the image wins and the `.txt` is not evidence of anything.**

### Why `guarantees.csv` is nonetheless checked

A hand transcription of a legible image can still slip. That — not a noisy
source — is the residual risk, and it is what the three checks guard: every
vector totals exactly 5, each step's `after` chains to the next step's
`before`, and each round's final vector equals its outcome in
`round_values.csv`. Any single misread digit breaks at least one. The totals
check alone is 80 independent assertions over 40 rows, all passing, which is
more integrity evidence than any other file in this corpus carries.

One caution learned the hard way: the earlier form of the total check was
`sum(after) >= sum(before)`, which is **vacuous** here because every vector
totals 5 on both sides. It compared `5 >= 5` and guarded nothing. The equality
form is the one that actually trips.

### What the guarantee vectors do *not* unlock

They do not improve identification of the utility weights. It is tempting to
think 40 transcribed vectors must constrain `GOOD`/`EVEN`/`SOFT` more tightly
than five round values do — but **the logs print a value only for the final
outcome of a round.** Intermediate guarantee states are printed as bare label
vectors with no number attached, so they yield no equations. They constrain
the transcription, not the weights. The recovery still rests on five printed
values, exactly as `manifest.json` says.

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

- **`HARD DODGE` is unidentified.** It occurs zero times across every
  observation in the corpus: zero in all five round outcomes, and zero in all
  80 intermediate guarantee counts (40 steps × before/after). Any weight at
  all reconciles the data. `RivalLabelUtility.value_of` raises
  `UnidentifiedLabel` rather than silently scoring it as 0. Note the two
  facts are different in strength: "we never saw one in an outcome" is n=5,
  while "the tool never once guaranteed one at any intermediate step" is
  n=80 and much harder to dismiss as a small-sample accident.
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
names its files, counts, per-file `reliability` grades and caveats. No code
changes. The loader will refuse it until every declared file carries a grade
and a reason.

## What a second event of this format would and would not fix

Worth stating plainly for whoever collects the next one, because it is a
corpus-design constraint rather than a sample-size problem:

- More events **would** sharpen the adversarial-line rate, currently 9/20.
- More events **would not** make either opponent model scoreable. The mirrors
  need a rating matrix, which these logs never contain; the rival utility
  needs a label on the branch *not* taken, and the tool labels only *locked*
  pairings. Both gaps are structural. A hundred events of this format leave
  the model backtest at n=0.

To race the models you need a log format that records either the numbers
behind a recommendation or the labels on every candidate, not just the chosen
one.
