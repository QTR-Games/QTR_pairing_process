# QTR Pairing Process v2.0.0

Stable 2.0 release focused on strategic-sort reliability, UI workflow polish, and responsiveness during heavy operations.

## Highlights

- Fixed strategic score display cases where tree values could appear as zero.
- Improved strategic memoized descendant materialization for reliable tree display.
- Upgraded Matchup Tree workflow:
  - expanded analysis grid behavior
  - show/hide checkbox controls with clear active-state feedback
  - sort controls moved to a more central workflow area
  - column-header sorting aligned with busy/loading behavior
- Preserved rating-color semantics when comments are present.
- Added visible loading state for generation/sorting plus temporary heavy-control lockout.

## Included Assets

- QTR_Pairing_Process_v2.0.0.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.0.0.md
- USER_GUIDE_v2.0.0.md
- RELEASE_MANIFEST.md

## Compatibility

- Windows 10/11 (64-bit)
- No separate Python install required for end-users running the executable

## Verification

Regression subset run during release prep:

- test_database_preferences.py
- test_phase11_regression.py

Status: passing

## Checksums

Use SHA256SUMS.txt to validate binary integrity before distribution.

PowerShell example:

~~~powershell
Get-FileHash .\QTR_Pairing_Process_v2.0.0.exe -Algorithm SHA256
~~~

## Rollback References

- v2.0.0-fallback
- v2.0-fallback-2026-03-18
- release/2.0.0-fallback
- release/2.0-fallback-2026-03-18
