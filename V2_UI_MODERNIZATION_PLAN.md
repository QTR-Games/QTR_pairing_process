# V2 UI Modernization Plan

## Purpose
This document defines a practical roadmap to modernize the QTR desktop experience for a 2.0 release while preserving the existing workflow strength and minimizing regression risk.

## Goals for 2.0
1. Deliver a visibly more modern and polished UI without disrupting established user flows.
2. Improve readability and hierarchy across dense screens.
3. Increase discoverability of actions and reduce visual clutter.
4. Improve accessibility and keyboard friendliness.
5. Preserve or improve performance in grid and tree-heavy workflows.

## Design Principles
1. Clarity first: strong hierarchy, spacing, and grouping.
2. Familiarity preserved: modernize styling before changing behavior.
3. Progressive disclosure: keep advanced controls visible but not overwhelming.
4. Indicator over decoration: keep comments and status cues informative and subtle.
5. Phase-based delivery: ship incremental wins with continuous validation.

## Current UI Inventory (High Level)
1. Main workspace with team/scenario selectors, matchup analysis grid, matchup output panel, and pairing tree.
2. Action/control surfaces split across top area and middle rows.
3. Multi-step workflows supported by dialogs (team creation, rating system, welcome/preferences, database load, import).
4. Status bar includes DB, rating system, and dynamic state messaging.
5. Heavy interaction zones:
   1. Rating grid editing and visual color mapping.
   2. Tree generation/sorting/explainability.
   3. Data management menu and dialogs.

## Major Modernization Opportunities

### A) Visual Language and Styling
1. Introduce a single UI token set for spacing, type sizes, and semantic colors.
2. Standardize button hierarchy:
   1. Primary actions (Generate, Extract, Save) with stronger emphasis.
   2. Secondary actions (Flip, Paste, Expand/Show controls) with softer style.
   3. Utility actions (open settings, backup) with tertiary style.
3. Normalize panel surfaces:
   1. Consistent border radius style equivalent for Tk contexts (frame relief and border discipline).
   2. Consistent section title bars and section spacing.
4. Harmonize label typography and reduce all-caps where not needed.

### B) Layout and Information Architecture
1. Enforce predictable vertical rhythm between:
   1. Header controls (team/scenario).
   2. Analysis area (grid + summary).
   3. Action strip (generate/sort utilities).
   4. Results area (tree/output).
2. Keep high-frequency actions in one contiguous action lane.
3. Reduce visual competition between grid, output card, and action controls.
4. Improve responsive behavior at minimum and maximized sizes.

### C) Grid and Data Readability
1. Preserve rating color fidelity regardless of comment presence.
2. Keep comment indicator arrow as the only comment marker.
3. Improve row/column scanning through subtle alignment and spacing consistency.
4. Ensure expanded-grid mode cleanly reclaims checkbox space with clear state feedback.

### D) Tree and Analysis Presentation
1. Improve tree readability with refined header styling and spacing.
2. Clarify active sort state consistently across button state, header labels, and guidance text.
3. Improve empty states for output and tree areas so users know the next action.

### E) Dialog and Utility UX
1. Standardize dialog shell behavior:
   1. Consistent sizing and centering.
   2. Consistent button placement.
   3. Consistent helper text blocks.
2. Upgrade welcome/preferences dialog messaging for 2.0 framing.
3. Improve import/database dialogs with clearer guidance and safer default actions.

### F) Accessibility and Input Efficiency
1. Add strong focus-visible styles for keyboard users.
2. Add high-contrast UI option (in addition to current rating color systems).
3. Strengthen tab order and shortcut discoverability.
4. Verify color contrast for all text on colored backgrounds.

## Suggested Phased Rollout

## Phase 1: Immediate 2.0 Polish (Low Risk, High Impact)
1. Establish tokenized visual system and apply to main workspace.
2. Standardize control row spacing, typography, and button hierarchy.
3. Harmonize status bar and helper text appearance.
4. Unify tooltip presentation style.
5. Deliver improved empty states in output and tree sections.

Exit criteria:
1. Main workspace has consistent modern look and action hierarchy.
2. Core workflows unchanged and stable.

## Phase 2: Structural Layout Refinement (Medium Risk, High Impact)
1. Refine frame composition to reduce layout coupling and improve resize behavior.
2. Group actions by intent with clearer sections.
3. Tighten spacing and alignment across top analysis region.
4. Modernize dialogs to shared composition patterns.

Exit criteria:
1. Layout remains stable across min/max sizes.
2. Dialogs and top-level surfaces feel visually cohesive.

## Phase 3: Advanced UX Enhancements (Medium Risk, Medium-High Impact)
1. Add optional modern theme variants (light-first default, optional dark/high-contrast).
2. Add keyboard-first affordances and hinting.
3. Add subtle transition cues for important state changes.
4. Improve onboarding text and 2.0 identity messaging.

Exit criteria:
1. Theme and accessibility options are production-safe.
2. New users can understand core flow more quickly.

## Implementation Priorities
1. Priority 1: Main workspace visual consistency and action hierarchy.
2. Priority 2: Dialog polish and consistency.
3. Priority 3: Accessibility and keyboard flow.
4. Priority 4: Theme options and enhanced transitions.

## Validation Plan
1. Functional regression:
   1. Team selection, scenario changes, grid edits, generate combinations, all sort modes, extraction.
   2. Comments, indicators, persistence behavior, and cache interactions.
2. Visual regression:
   1. Capture standard screenshot baselines for main screen states and key dialogs.
   2. Verify spacing, clipping, and alignment at min/max sizes.
3. Performance regression:
   1. Compare startup, generation, and sort timings with perf logs before/after each phase.
4. Accessibility checks:
   1. Keyboard-only navigation across major controls.
   2. Focus visibility and contrast checks.

## Risks and Mitigations
1. Risk: Visual updates introduce accidental behavior regressions.
   1. Mitigation: Keep Phase 1 style-only where possible; run regression suite each step.
2. Risk: Layout refactors break resize or clipping behavior.
   1. Mitigation: Add screenshot checkpoints at standard viewport sizes.
3. Risk: Theme options create inconsistent widget styling in mixed Tk/ttk contexts.
   1. Mitigation: Pilot theme set on a narrow UI surface first, then scale.

## Candidate Focus Areas by File
1. qtr_pairing_process/ui_manager_v2.py
   1. Primary workspace layout, controls, grid/tree panels, status bar.
2. qtr_pairing_process/dynamic_ui_manager.py
   1. Shared dialog scaffolding and reusable composition helpers.
3. qtr_pairing_process/welcome_dialog.py
   1. 2.0 framing and first-run polish.
4. qtr_pairing_process/create_team_dialog.py
   1. Form readability, input hierarchy, and button consistency.
5. qtr_pairing_process/rating_system_dialog.py
   1. Settings clarity and control consistency.
6. qtr_pairing_process/db_load_ui.py and qtr_pairing_process/xlsx_load_ui.py
   1. Utility flow polish and guidance.
7. qtr_pairing_process/constants.py
   1. Candidate location for shared UI tokens and palette definitions.

## Suggested 2.0 Showcase Enhancements
1. Distinct 2.0 welcome surface with concise "what is new" highlights.
2. Consistent active-state signaling for sort and workspace mode controls.
3. Clean empty-state messaging in tree/output panels.
4. More intentional spacing and alignment that looks deliberate on demos/screenshots.

## Execution Notes
1. Do not attempt full framework migration in 2.0 scope.
2. Favor iterative polish merged in small PRs with before/after screenshots.
3. Track each milestone with a short acceptance checklist and known tradeoffs.

## Success Metrics
1. Reduced visual clutter in user feedback.
2. Improved perceived modernness in internal/demo reviews.
3. No regression in core workflow pass rate.
4. Equal or better performance for startup and sort operations.
5. Better first-run comprehension from the welcome and settings surfaces.
