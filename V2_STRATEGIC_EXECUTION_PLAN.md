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
1. cumulative2 parameters
1. confidence2 parameters
1. resistance2 parameters
1. strategic fusion parameters
1. bus recommendation parameters
1. Add robust load/save/validation in [qtr_pairing_process/database_preferences.py](qtr_pairing_process/database_preferences.py):
1. schema defaults
1. range clamps
1. missing-key fallback
1. version-safe migration path
1. Wire startup parameter hydration in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py), and pass effective parameters into [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Acceptance criteria:
1. all parameters load with defaults on clean config
1. invalid values clamp safely
1. no runtime errors if config keys are absent

**Phase 2: Deterministic Sorting Engine and Turn Integrity**
1. Enforce sibling ordering invariants in sort recursion in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
1. our-choice levels sort descending
1. opponent-choice levels sort ascending
1. Add deterministic tie-break chain for equal scores.
1. Validate opponent rebound integrity against current depth ownership rules in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Acceptance criteria:
1. repeated runs with same state yield identical ordering
1. opponent layers never sort as if they are our choice

**Phase 3: First-Pass Auto Strategic and Click Consistency**
1. After Generate completes, auto-run Strategic Fusion once through the same pipeline used by manual clicks.
1. Ensure first-pass and click-pass produce identical outputs for identical state.
1. Guard against stale score reads by preserving compute-before-display ordering.
1. Acceptance criteria:
1. strategic values present and non-zero on first pass
1. no ordering differences between auto and manual triggers with unchanged inputs

**Phase 4: Dynamic Lock-In State Model**
1. Treat checkbox states as availability masks in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py).
1. On every checkbox change, recompute from remaining options:
1. calc-grid metrics
1. pin and can-pin states
1. bus yes/no
1. score cache invalidation
1. Ensure recalc paths are incremental and fast enough for in-round use.
1. Acceptance criteria:
1. every checkbox toggle updates visible metrics immediately
1. removed players never appear in remaining-option analytics

**Phase 5: Calc Grid Enhancement as Display-Only Guidance**
1. Expand per-player calc-grid outputs in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
1. floor quality under availability masks
1. pinned and can-pin dynamic values
1. opening quality signal
1. danger exposure signal
1. bus yes/no recommendation
1. Keep these as transparent decision aids and not silent strategic sort terms unless explicitly configured.
1. Acceptance criteria:
1. values are per-player and availability-aware
1. values update across rounds as lock-ins accumulate

**Phase 6: Bussing Engine as Advisory Signal**
1. Implement bus scoring in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py):
1. immediate sacrifice cost
1. downstream positional gain
1. phase sensitivity by round depth
1. Convert bus score to BUS YES/NO using selected threshold policy.
1. Keep bus result outside forced strategic ranking behavior.
1. Expose bus rationale in explainability surfaces.
1. Acceptance criteria:
1. BUS toggles contextually over pairing rounds
1. user can ignore BUS without hidden rank coercion

**Phase 7: Mode-Objective Separation (Critical Behavioral Contract)**
1. Confidence mode objective profile:
1. primary: low-variance 3-of-5 success
1. secondary: expected value preservation
1. tie-break: regret
1. Cumulative mode objective profile:
1. primary: aggressive opponent-aware value accumulation
1. Counter mode objective profile:
1. primary: exploitability resistance and adversarial robustness
1. Strategic Fusion objective profile:
1. balanced C2/Q2/R2 fusion
1. round-win feasibility as bounded guardrail term
1. exploitability as tie-break
1. Acceptance criteria:
1. confidence is visibly more conservative
1. strategic remains balanced and not dominated by one objective

**Phase 8: Explainability in Tooltip and Right Panel**
1. Tooltip content in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
1. C2/Q2/R2/downside/final score
1. mode label and objective profile
1. pin and bus context snippets
1. Right panel card content:
1. component contribution breakdown
1. round-win guardrail impact
1. bus yes/no reasoning
1. remaining-option context
1. Acceptance criteria:
1. displayed factors match active mode and current node
1. users can trace why a node ranked where it did

**Phase 9: Remove Obsolete Controls and Defaults**
1. Remove alphabetic sorting logic and UI traces in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py) and [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py).
1. Set My Team First default unchecked in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py).
1. Acceptance criteria:
1. no alpha-sort paths executed
1. startup default reflects unchecked My Team First

**Phase 10: Performance Memoization and Safety**
1. Add strategic recursion memoization in [qtr_pairing_process/tree_generator.py](qtr_pairing_process/tree_generator.py) keyed by:
1. tree state
1. availability mask
1. active mode
1. parameter hash
1. Add invalidation triggers for team, scenario, grid changes, lock-in changes, and parameter changes.
1. Add perf counters to confirm hit rate and latency improvements.
1. Acceptance criteria:
1. repeated sorts are faster
1. no stale ranking after state changes

**Phase 11: Regression and Behavioral Test Matrix**
1. Determinism tests:
1. same inputs produce same ordering
1. First-click tests:
1. non-zero and stable values on first strategic compute
1. Turn-integrity tests:
1. opponent rebound ordering preserved by depth
1. Lock-in dynamic tests:
1. pinned/can-pin/bus update with checkbox changes
1. Mode-separation tests:
1. confidence conservative bias present
1. strategic balanced behavior retained
1. Performance tests:
1. memoization correctness and hit-rate checks
1. Acceptance criteria:
1. all targeted tests pass in CI/local test run

**Delivery Sequence and Dependencies**
1. Phase 1 must complete before all others.
2. Phases 2 and 3 are next and block user-visible trust.
3. Phases 4 through 8 can be parallelized by surface area once state contracts are fixed.
4. Phase 9 can run parallel with late testing.
5. Phases 10 and 11 finalize release readiness.

**Risks and Mitigations**
1. Risk: objective leakage between modes.
1. Mitigation: explicit mode profile tests and explainability labels.
1. Risk: stale caches after lock-in changes.
1. Mitigation: strict invalidation keys and tests.
1. Risk: user confusion around bus behavior.
1. Mitigation: BUS stays advisory with clear reason text.

**Verification Checklist**
1. Manual smoke:
1. generate tree and confirm auto strategic sort
1. toggle lock-ins and confirm dynamic recalc
1. switch modes and observe expected behavioral differences
1. verify opponent rebound logic visually in deeper levels
1. Automated:
1. deterministic ordering tests
1. first-pass strategic tests
1. lock-in recalc tests
1. mode objective separation tests
1. memoization and invalidation tests

**Finalized decisions**
1. Round-win guardrail strength in Strategic Fusion:
1. medium penalty
2. BUS YES threshold policy:
1. scenario-dependent threshold
3. Strategic auto-sort trigger scope:
1. config-toggle default on
4. Deterministic tie-break order when primary scores are equal:
1. user-selectable toggle in Data Management menu
1. persist selection in KONFIG/preferences
1. first-time default: confidence2 then cumulative2
