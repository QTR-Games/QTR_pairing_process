# Release Manifest - v2.1.1

## Build Metadata

- Version: v2.1.1
- Build timestamp (UTC): 2026-04-11T18:51:34Z
- Commit: 1882d5f
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.1.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.1.md
- USER_GUIDE_v2.1.1.md

## Integrity

SHA256  1CCE04B74F7E024C58B4A7F3767B0AC72599CFA9E34CB40B4D09E280D462C91A  QTR_Pairing_Process_v2.1.1.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.1
~~~
