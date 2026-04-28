# Release Manifest - v2.1.1

## Build Metadata

- Version: v2.1.1
- Build timestamp (UTC): 2026-04-28T12:40:55Z
- Commit: cd1413a
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- QTR_Pairing_Process_v2.1.1.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v2.1.1.md
- USER_GUIDE_v2.1.1.md
- ADVANCED_SORTING_GUIDE.md

## Integrity

SHA256  7117B73779A386F7DC108986BEBFCD012F98650AC8ED5AEE2B98F5B32837323D  QTR_Pairing_Process_v2.1.1.exe

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version 2.1.1
~~~
