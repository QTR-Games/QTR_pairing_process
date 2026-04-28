# Release Manifest - v2.1.2

## Build Metadata

- Version: v2.1.2
- Build timestamp (UTC): 2026-04-28T13:00:53Z
- Commit: 134f37d
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.2.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.2.md
- USER_GUIDE_v2.1.2.md
- ADVANCED_SORTING_GUIDE.md

## Integrity

SHA256  C62E6D5067CD829681498104E2303A2DD6865BBD427B8085F1F434FC34F10AB1  QTR_Pairing_Process_v2.1.2.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.2
~~~
