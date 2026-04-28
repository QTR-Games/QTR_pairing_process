# Release Manifest - v2.1.1

## Build Metadata

- Version: v2.1.1
- Build timestamp (UTC): 2026-04-28T12:57:43Z
- Commit: 119f8d1
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.1.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.1.md
- USER_GUIDE_v2.1.1.md
- ADVANCED_SORTING_GUIDE.md

## Integrity

SHA256  7E19B60EBD3820D86DF6E38BC2B3A36B06B6AEDB600DED426386245AE2B578B0  QTR_Pairing_Process_v2.1.1.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.1
~~~
