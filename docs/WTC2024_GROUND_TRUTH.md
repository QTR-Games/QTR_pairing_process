# WTC 2024 ground truth — withdrawn from this repository

This document recorded the reconstruction of the home team's WTC 2024 results:
the pre-round grids, the boards that were actually played, and Findings 1–22
derived from them.

**It is no longer published here, and that is deliberate.**

The findings themselves are not sensitive. What was sensitive is the *join*
between them: real player names on both teams, paired with this team's private
assessment of each opponent. Either half alone is harmless — the rosters are
public tournament record — but together they are scouting material, in a public
repository.

The document still exists and is still maintained. It is kept outside version
control, on the maintainer's machine.

## What remains here

Everything that does not depend on knowing who anyone is:

- `docs/DECISION_SENSITIVITY_FINDINGS.md` — the measured findings
- `docs/SCORING_MATHEMATICS.md` — the scoring model
- `webapp/src/engine/__fixtures__/wtc2024Boards.json` — all 31 boards, with
  every rating matrix bit-for-bit unchanged and the labels anonymised

The fixture is the important one. Because only the labels were remapped, every
test and every measured number that referenced these boards is still exactly
as valid as it was before. Nothing in the analysis rested on the names.

## Citations elsewhere

Source and docs that cite "Finding N" against this file still refer to real,
recorded findings. The numbering is unchanged.
