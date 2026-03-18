# QTR Pairing Process 2.0.0 Release Notes

Release date: 2026-03-18
Release type: Stable
Tag: v2.0.0
Fallback tag: v2.0.0-fallback

## Highlights

- Strategic sorting reliability improvements for the Matchup Tree.
- UI layout polish and better control organization for faster workflow.
- Responsiveness updates during heavy operations with visible loading state.
- Status and sorting telemetry refinements for debugging and performance analysis.
- Continued stability work across tree generation, memoization, and preferences.

## What Is New In 2.0.0

- Strategic score display hardening:
  - Fixed scenarios where strategic values could appear as zeros in the tree.
  - Improved memoized strategic path materialization so descendant nodes display correctly.
- Matchup Tree UX upgrades:
  - Expanded analysis grid options.
  - Show/hide checkbox controls with active visual state feedback.
  - Sort controls moved into a more central workflow location.
  - Column header sorting aligned with loading-state behavior.
- Visual consistency:
  - Comment indicators no longer override the rating color mapping of grid cells.
- Responsiveness Option A implementation:
  - Loading text shown in status bar during generation and sorting.
  - Busy indicator/progress behavior for long operations.
  - Temporary disabling of heavy-action controls while operations run.

## Compatibility

- OS: Windows 10/11 (64-bit)
- Python runtime: bundled in executable build artifact behavior (no local Python required to run exe)
- Data and configuration: existing local config and database files are retained

## Known Notes

- First launch can be slower than subsequent launches due to one-file extraction behavior.
- If SmartScreen appears, choose More info then Run anyway for trusted internal distribution.

## Upgrade Guidance

- Backup your `KLIK_KLAK_KONFIG.json` and database files before broad team rollout.
- Validate one representative matchup dataset before tournament day.
- Keep fallback marker `v2.0.0-fallback` available for quick rollback.

## Verification

- Regression test subset used during release prep:
  - `test_database_preferences.py`
  - `test_phase11_regression.py`
- Result: passing in release-prep environment.

## Release Assets

- `QTR_Pairing_Process_v2.0.0.exe`
- `SHA256SUMS.txt`
- `RELEASE_NOTES_v2.0.0.md`
- `USER_GUIDE_v2.0.0.md`
