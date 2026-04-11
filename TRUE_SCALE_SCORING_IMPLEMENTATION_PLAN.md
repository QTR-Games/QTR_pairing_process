# True-Scale Scoring Implementation Plan

## Objective

Remove rating bucket conversion from all scoring and sorting paths so each active rating system (`1-3`, `1-5`, `1-10`) uses true native ratings for calculations.

## Decision Summary

- No rating-to-`1-5` bucketing in scoring logic.
- Every sort mode must derive from native scale values.
- Scale granularity should be real, not simulated.

## Current Problem

The current tree scoring flow includes a conversion path that maps active-scale ratings to a `1-5` reference before confidence and resistance scoring. This compresses information for wider scales.

Primary references in code:

- `qtr_pairing_process/tree_generator.py`
  - `_to_reference_rating`
  - `calculate_rating_confidence`
  - `calculate_counter_resistance`
  - `simulate_opponent_counter`
- `qtr_pairing_process/ui_manager_v2.py`
  - `apply_combined_sort` enhanced metric orchestration

## Scope

In scope:

- Cumulative, confidence, resistance, and strategic sorting metric pipelines.
- All enhanced metric paths (`C2`, `Q2`, `R2`, strategic fusion).
- Explainability consistency with updated math.
- Documentation updates for scoring semantics.

Out of scope:

- UI layout redesign.
- Database schema changes.

## Implementation Strategy

### Phase 1 - Remove Bucket Dependency

1. Stop using `_to_reference_rating` in confidence/resistance calculations.
2. Keep active rating bounds from `set_rating_system` as the source of truth.
3. Introduce shared native-scale normalization helper used by score functions:

   - `n = clip((r - min_rating) / (max_rating - min_rating), 0.0, 1.0)`

4. Preserve defensive fallback when `max_rating <= min_rating`.

### Phase 2 - Native-Scale Scoring Functions

Replace discrete bucket maps with continuous functions over normalized value `n`.

1. Confidence score (`0-100`, monotonic increasing):

   - `confidence = round(15 + 80 * n)`

2. Counter-resistance score (`0-100`, peak near midpoint):

   - `resistance = round(50 + 35 * (1 - 4*(n - 0.5)^2))`

3. Opponent counter effectiveness (continuous by extremity):

   - `extremity = abs(n - 0.5) * 2`
   - `counter_effectiveness = 0.1 + 0.2 * extremity`

4. Keep clamping and integer output conventions used by existing tag storage.

### Phase 3 - Enhanced Pipeline Integration

1. Ensure enhanced calculators consume updated confidence/resistance values:

   - `calculate_confidence_scores_enhanced`
   - `calculate_counter_resistance_scores_enhanced`
   - `calculate_strategic3_scores`

2. Keep current strategic fusion architecture and tie-break chain.
3. Confirm no residual bucket conversion path is used during strategic sort.

### Phase 4 - Explainability and Docs Alignment

1. Update tooltip and analysis docs to describe native-scale continuous scoring.
2. Remove references that imply fixed `1..5` confidence/resistance tables as active logic.
3. Document expected behavior by scale:

   - `1-3`: coarse differentiation
   - `1-5`: medium differentiation
   - `1-10`: fine differentiation

## Acceptance Criteria

1. No active scoring path depends on `_to_reference_rating`.
2. Confidence and resistance respond to true rating steps for each active scale.
3. For equivalent datasets, `1-10` produces fewer ties than `1-3` in confidence/resistance-driven ordering.
4. Strategic sort reflects richer `Q2` and `R2` resolution under `1-10`.
5. Explainability text and docs match implemented math.

## Risk and Mitigation

Risk: Existing ranking behavior changes versus prior versions.

Mitigation:

1. Keep formulas explicit and documented.
2. Validate deterministic sibling ordering and tie-break behavior.
3. Note scoring change clearly in release notes.

## Rollout Notes

1. Implement in a single feature branch pass to avoid mixed-math states.
2. Run focused tree sorting regressions after each phase.
3. Verify UI behavior manually in all three rating systems before merge.

## Definition of Done

All scoring and sorting mechanisms in every rating scale use native true ratings for calculations, with no bucket-based conversion in active scoring logic.