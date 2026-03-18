# Release Manifest - v2.0.0

## Build Metadata

- Product: QTR Pairing Process
- Version: v2.0.0
- Release date: 2026-03-18
- Build timestamp (UTC): 2026-03-18T19:36:31Z
- Branch: main
- Commit: db342d2
- Release tag: v2.0.0
- Fallback tag: v2.0.0-fallback
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.0.0.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.0.0.md
- USER_GUIDE_v2.0.0.md
- RELEASE_MANIFEST.md

## Integrity

SHA256  E7549C0CA77C626C483F810E492C824A546981CF418245A6FE7DF45CD25398FE  QTR_Pairing_Process_v2.0.0.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.0.0
~~~

## Rollback Guidance

- v2.0.0-fallback
- v2.0-fallback-2026-03-18
- release/2.0.0-fallback
- release/2.0-fallback-2026-03-18

