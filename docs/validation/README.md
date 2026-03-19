# Validation Artifacts

This directory contains phase-level UI modernization validation outputs.

## Scope

- Visual baseline matrix and capture checklist
- Performance before/after protocol and summary tables
- Decision log for deferred work and acceptance thresholds

## Current Decisions

1. Baseline capture matrix:
- 1920x1080 @ 100% scaling
- 2560x1440 @ 125% scaling

2. Performance regression thresholds:
- Startup median regression <= 5%
- Generate/sort median regression <= 10%
- No critical span regression > 15% without written rationale

3. Accessibility implementation:
- Deferred to backlog until user demand cites accessibility concerns.

## Required Screens

1. Main workspace default state
2. Main workspace after generate + active sort mode
3. Data Management menu (collapsed advanced sections)
4. Data Management menu (expanded advanced sections)
5. Welcome dialog
6. Rating system dialog
7. Create/Modify team dialog

## Outputs

- screenshot_matrix.md
- perf_protocol.md
- perf_summary.md
- decision_log.md
