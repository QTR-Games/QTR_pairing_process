# Sun-Tzu Strategy Analysis (Deferred)

## Status
- Decision date: 2026-04-03
- Release decision: Deferred (not implementing in current cycle)
- Reason: Keep current scope focused on existing BUS advisory improvements and avoid introducing a second strategic model without full validation.

## Source Context
This note captures analysis from community discussion screenshots about a "Sun-Tzu" ("Art of War") pairing method.

### Best-Effort Transcript Summary
- Core concept: Assume opponent top player can beat your top player regardless.
- Tactical response:
  - Feed your worst player into their best player ("take the bus").
  - Then aim for pair-downs across remaining players:
    - your #1 into their #2,
    - your #2 into their #3,
    - etc.
- Community caveats:
  - Not always preferred.
  - Often driven by confidence/feel in team quality and uncertainty in opponent read.
  - Suggested extension: add a "star power modifier" to emulate this approach mathematically.

## Analytical Interpretation
The Sun-Tzu method is a structured sacrificial sequence plan (not generic one-off bussing):
1. Neutralize one opponent outlier by spending your lowest-value piece.
2. Convert resulting board state into controlled pair-downs.
3. Prioritize sequence feasibility over local matchup greed.

## Comparison to Current Implementation
Current BUS system (advisory-only) uses per-row score mechanics:
- spread and downside from margin states,
- threshold gating,
- optional degree/abort/outlier/leverage context.

Sun-Tzu introduces additional structure not currently explicit:
- roster ladder assumptions (best/second-best ordering),
- explicit star-neutralization objective,
- sequence-level feasibility across later pairing steps.

## Gaps Identified (If Revisited)
1. No explicit team power ladder model in current advisor.
2. No explicit star-neutralization term (targeting opponent outlier as primary objective).
3. No rankability-confidence parameter (how trustworthy player ordering is).
4. No table-control sensitivity term tied to Sun-Tzu viability.
5. No sequence validator for whether pair-down chain remains feasible after each lock-in.

## Deferred Implementation Sketch (Future Cycle)
If this is resumed, keep it advisory-first:
1. Add config-gated `sun_tzu` block under strategic preferences.
2. Build Team Power Index per player (or optional manual captain ranking).
3. Add Opponent Star Detection threshold.
4. Compute Sun-Tzu Feasibility Score:
   - expected gain across remaining pairings after sacrificial assignment,
   - adjusted by confidence and table-control context.
5. Add stop/abort rules when chain feasibility collapses.
6. Surface compact explainability in right-grid popup (similar style to BUS).
7. Ship behind feature toggle and validate with scenario regressions before default-on.

## Proposed Config Seeds (Draft)
```json
"sun_tzu": {
  "enabled": false,
  "star_gap_trigger": 0.8,
  "rankability_confidence": 0.6,
  "table_control_modifier": 0.25,
  "min_projected_gain": 4,
  "abort_on_low_confidence": true
}
```

## Validation Plan (When Resumed)
- Unit tests:
  - star/outlier detection,
  - rankability confidence impact,
  - sequence feasibility and abort behavior.
- Integration tests:
  - round-depth transitions,
  - lock-in interactions,
  - compatibility with existing BUS advisor and popup explainability.
- Manual checks:
  - captain readability of rationale,
  - no hidden coercion in sort ranking (advisory-first remains intact).

## Revisit Criteria
Consider re-opening this item when at least one is true:
1. Multiple tournament reports show repeatable Sun-Tzu success patterns.
2. Team captains request explicit "star neutralization" advisory in production.
3. Enough historical matchup logs exist to tune confidence and chain-feasibility thresholds.
