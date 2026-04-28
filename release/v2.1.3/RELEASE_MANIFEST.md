# Release Manifest - v2.1.3

## Build Metadata

- Version: v2.1.3
- Build timestamp (UTC): 2026-04-28T15:32:26Z
- Commit: e9de2c4
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.3.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.3.md
- USER_GUIDE_v2.1.3.md  (copied from docs/FULL_USER_GUIDE.md)
- ADVANCED_SORTING_GUIDE.md

## Integrity

SHA256  F63531EB8F189712A13BE7E820AC7063B6ADFD5D265BC65E2DA4BC5A07B2A3D6  QTR_Pairing_Process_v2.1.3.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.3
~~~
