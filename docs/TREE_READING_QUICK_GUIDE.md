# Tree Reading Quick Guide

This quick guide explains how to read the matchup tree and sort values.

## Core idea

Each branch is a potential pairing sequence.

- Higher sort values are better when the current node is your choice.
- Lower sort values are better for the opponent when the current node is their choice.
- The app automatically flips sort direction by choice owner at each depth.

## Node text

- Top-level rows: your candidate player into two offered opponents.
- Child rows: the resulting response options after a specific pick.
- Deeper rows: next-round continuation from that decision path.

## Sort modes

- Cumulative: favors strongest overall path value.
- Confidence: favors low-variance, reliable outcomes.
- Counter: favors resilience against opponent counters.
- Strategic Fusion: balances C2/Q2/R2 with downside and guardrail terms.

## My Team First

- Checked: your team controls depth-1 choices.
- Unchecked: opponent controls depth-1 choices.
- Ownership alternates by depth with late-round ownership rules built into the model.

## Strategic values can be negative

This is expected. Relative ordering at the current choice level matters more than absolute sign.

## Explainability panel / tooltip

Use the right-side explainability details to inspect per-node components:

- C2, Q2, R2
- Downside term
- Guardrail contribution
- Final strategic score

## Flip Grid

Flip Grid is display-only perspective inversion.

- It swaps visible headers and flips shown ratings around 3.
- It does not save flipped values to the database.
- Flip back before saving.
