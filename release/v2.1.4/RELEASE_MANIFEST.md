# Release Manifest - v2.1.4

## Build Metadata

- Version: v2.1.4
- Build timestamp (UTC): 2026-04-28T16:02:05Z
- Commit: fcda317
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.4.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.4.md
- USER_GUIDE_v2.1.4.md  (copied from docs/FULL_USER_GUIDE.md)
- ADVANCED_SORTING_GUIDE.md

## Integrity

SHA256  D390470C18274AAF87A83C7F1B945B0412314CAA8BF1BC081F7A8023329F8DAD  QTR_Pairing_Process_v2.1.4.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.4
~~~
