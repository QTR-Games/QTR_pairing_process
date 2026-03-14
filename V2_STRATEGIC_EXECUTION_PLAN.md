## Plan: v2 Completion with Mode-Specific Objectives, Dynamic Recalc, and Balanced Strategic Fusion

Deliver a stable, tournament-ready decision system where ratings stay immutable, lock-in state drives live recalculation, and each sorting mode preserves its intent. Confidence remains conservative for 3-of-5 stability, while Strategic Fusion remains multi-objective with a tunable round-win guardrail.

**Scope Statement**
- In scope: config wiring, deterministic sort behavior, lock-in-aware recalc, pin/bus guidance, explainability, performance memoization, regression tests, and UI cleanup.
- Out of scope: editing or suggesting rating changes to the user; hidden bussing coercion in strategic scoring.

**Guiding Principles**
1. User-entered grid values are authoritative truth.
2. Recommendations are derived from fixed ratings and dynamic availability state only.
3. Opponent-optimal rebound behavior must be preserved at opponent decision layers.
4. Mode intent must remain distinct; avoid objective collapse across modes.

**Phase 1: Parameterization Foundation**
1. Add mode-specific config blocks in [KLIK_KLAK_KONFIG.json](KLIK_KLAK_KONFIG.json):
   - cumulative2 parameters
   - confidence2 parameters
   - resistance2 parameters
   - strategic fusion parameters
   - bus recommendation parameters
1. Add robust load/save/validation in [qtr_pairing_process/database_preferences.py](qtr_pairing_process/database_preferences.py):
   - schema defaults
   - range clamps
   - missing-key fallback
   - version-safe migration path
1. Wire startup parameter hydration in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py), and pass effective parameters into [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Acceptance criteria:
   - all parameters load with defaults on clean config
   - invalid values clamp safely
   - no runtime errors if config keys are absent

**Phase 2: Deterministic Sorting Engine and Turn Integrity**
1. Enforce sibling ordering invariants in sort recursion in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
   - our-choice levels sort descending
   - opponent-choice levels sort ascending
1. Add deterministic tie-break chain for equal scores.
1. Validate opponent rebound integrity against current depth ownership rules in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Acceptance criteria:
   - repeated runs with same state yield identical ordering
   - opponent layers never sort as if they are our choice

**Phase 3: First-Pass Auto Strategic and Click Consistency**
1. After Generate completes, auto-run Strategic Fusion once through the same pipeline used by manual clicks.
1. Ensure first-pass and click-pass produce identical outputs for identical state.
1. Guard against stale score reads by preserving compute-before-display ordering.
1. Acceptance criteria:
   - strategic values present and non-zero on first pass
   - no ordering differences between auto and manual triggers with unchanged inputs

**Phase 4: Dynamic Lock-In State Model**
1. Treat checkbox states as availability masks in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py).
1. On every checkbox change, recompute from remaining options:
   - calc-grid metrics
   - pin and can-pin states
   - bus yes/no
   - score cache invalidation
1. Ensure recalc paths are incremental and fast enough for in-round use.
1. Acceptance criteria:
   - every checkbox toggle updates visible metrics immediately
   - removed players never appear in remaining-option analytics

**Phase 5: Calc Grid Enhancement as Display-Only Guidance**
1. Expand per-player calc-grid outputs in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
   - floor quality under availability masks
   - pinned and can-pin dynamic values
   - opening quality signal
   - danger exposure signal
   - bus yes/no recommendation
1. Keep these as transparent decision aids and not silent strategic sort terms unless explicitly configured.
1. Acceptance criteria:
   - values are per-player and availability-aware
   - values update across rounds as lock-ins accumulate

**Phase 6: Bussing Engine as Advisory Signal**
1. Implement bus scoring in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py):
   - immediate sacrifice cost
   - downstream positional gain
   - phase sensitivity by round depth
1. Convert bus score to BUS YES/NO using selected threshold policy.
1. Keep bus result outside forced strategic ranking behavior.
1. Expose bus rationale in explainability surfaces.
1. Acceptance criteria:
   - BUS toggles contextually over pairing rounds
   - user can ignore BUS without hidden rank coercion

**Phase 7: Mode-Objective Separation (Critical Behavioral Contract)**
1. Confidence mode objective profile:
   - primary: low-variance 3-of-5 success
   - secondary: expected value preservation
   - tie-break: regret
1. Cumulative mode objective profile:
   - primary: aggressive opponent-aware value accumulation
1. Counter mode objective profile:
   - primary: exploitability resistance and adversarial robustness
1. Strategic Fusion objective profile:
   - balanced C2/Q2/R2 fusion
   - round-win feasibility as bounded guardrail term
   - exploitability as tie-break
1. Acceptance criteria:
   - confidence is visibly more conservative
   - strategic remains balanced and not dominated by one objective

**Phase 8: Explainability in Tooltip and Right Panel**
1. Tooltip content in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
   - C2/Q2/R2/downside/final score
   - mode label and objective profile
   - pin and bus context snippets
1. Right panel card content:
   - component contribution breakdown
   - round-win guardrail impact
   - bus yes/no reasoning
   - remaining-option context
1. Acceptance criteria:
   - displayed factors match active mode and current node
   - users can trace why a node ranked where it did

**Phase 9: Remove Obsolete Controls and Defaults**
1. Remove alphabetic sorting logic and UI traces in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py) and [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Set My Team First default unchecked in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py).
1. Acceptance criteria:
   - no alpha-sort paths executed
   - startup default reflects unchecked My Team First

**Phase 10: Performance Memoization and Safety**
1. Add strategic recursion memoization in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py) keyed by:
   - tree state
   - availability mask
   - active mode
   - parameter hash
1. Add invalidation triggers for team, scenario, grid changes, lock-in changes, and parameter changes.
1. Add perf counters to confirm hit rate and latency improvements.
1. Acceptance criteria:
   - repeated sorts are faster
   - no stale ranking after state changes

**Phase 11: Regression and Behavioral Test Matrix**
1. Determinism tests:
   - same inputs produce same ordering
1. First-click tests:
   - non-zero and stable values on first strategic compute
1. Turn-integrity tests:
   - opponent rebound ordering preserved by depth
1. Lock-in dynamic tests:
   - pinned/can-pin/bus update with checkbox changes
1. Mode-separation tests:
   - confidence conservative bias present
   - strategic balanced behavior retained
1. Performance tests:
   - memoization correctness and hit-rate checks
1. Acceptance criteria:
   - all targeted tests pass in CI/local test run

**Delivery Sequence and Dependencies**
1. Phase 1 must complete before all others.
2. Phases 2 and 3 are next and block user-visible trust.
3. Phases 4 through 8 can be parallelized by surface area once state contracts are fixed.
4. Phase 9 can run parallel with late testing.
5. Phases 10 and 11 finalize release readiness.

**Risks and Mitigations**
1. Risk: objective leakage between modes.
   - Mitigation: explicit mode profile tests and explainability labels.
1. Risk: stale caches after lock-in changes.
   - Mitigation: strict invalidation keys and tests.
1. Risk: user confusion around bus behavior.
   - Mitigation: BUS stays advisory with clear reason text.

**Verification Checklist**
1. Manual smoke:
   - generate tree and confirm auto strategic sort
   - toggle lock-ins and confirm dynamic recalc
   - switch modes and observe expected behavioral differences
   - verify opponent rebound logic visually in deeper levels
1. Automated:
   - deterministic ordering tests
   - first-pass strategic tests
   - lock-in recalc tests
   - mode objective separation tests
   - memoization and invalidation tests

**Finalized decisions**
1. Round-win guardrail strength in Strategic Fusion:
   - medium penalty
2. BUS YES threshold policy:
   - scenario-dependent threshold
3. Strategic auto-sort trigger scope:
   - config-toggle default on
4. Deterministic tie-break order when primary scores are equal:
   - user-selectable toggle in Data Management menu
   - persist selection in KONFIG/preferences
   - first-time default: confidence2 then cumulative2

