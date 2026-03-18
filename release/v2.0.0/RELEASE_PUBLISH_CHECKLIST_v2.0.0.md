# Release Publish Checklist - v2.0.0

## 1. GitHub Release Setup

- Use tag: v2.0.0
- Release title: QTR Pairing Process v2.0.0
- Use body from: release/v2.0.0/GITHUB_RELEASE_BODY_v2.0.0.md

## 2. Upload Assets

- release/v2.0.0/QTR_Pairing_Process_v2.0.0.exe
- release/v2.0.0/SHA256SUMS.txt
- release/v2.0.0/RELEASE_NOTES_v2.0.0.md
- release/v2.0.0/USER_GUIDE_v2.0.0.md
- release/v2.0.0/RELEASE_MANIFEST.md

## 3. Validate Integrity

- Run SHA256 validation locally and compare with SHA256SUMS.txt.

## 4. Post-Publish Safety

- Confirm fallback tag exists: v2.0.0-fallback
- Keep fallback branch available: release/2.0.0-fallback

## 5. Team Comms

- Share release link and checksum instructions with users.
- Include SmartScreen note for first-run executable environments.
