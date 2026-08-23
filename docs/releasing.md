# Releasing

The current release line is **v2.1.4**. The canonical version is
`qtr_pairing_process/VERSION`; `setup.py` reads that file through
`_read_app_version()` and rejects a version that is not
`major.service.maintenance`.

## Build command

Run the release script from a Windows PowerShell environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

The script accepts these parameters:

| Parameter | Script behavior |
| --- | --- |
| `-Version <x.y.z>` | Must equal the canonical version; omitted uses it. |
| `-SkipInstall` | Skips pip upgrade, `requirements.txt`, and `pyinstaller==6.19.0` installation. |
| `-SkipTests` | Skips the two release-gate test files. |
| `-SkipGitChecks` | Skips git preflight checks and emits an emergency-use warning. |

The script requires `.venv\Scripts\python.exe`, the canonical version file,
and a `setup.py` assignment of `version=_read_app_version()`. It does not
create the virtual environment.

## Preflight and build behavior

Unless `-SkipGitChecks` is supplied, the script fetches `origin` and requires:

1. The current branch to be `main`.
2. A clean working tree.
3. Local `main` to exactly match `origin/main`.
4. No local branch with commits unmerged into `main`.
5. No open pull requests when the `gh` CLI is available and its output can be
   read.

If `gh` is unavailable, the open-PR check is skipped with a warning. The
script does not merge, close, or create pull requests.

By default, it upgrades pip, installs `requirements.txt`, installs
`pyinstaller==6.19.0`, and runs only:

```text
test_database_preferences.py
test_phase11_regression.py
```

It removes prior matching EXEs from `dist`, removes `build`, then runs
PyInstaller as a one-file, windowed build of `main.py`. The build collects the
`qtr_pairing_process` package and bundles `docs` plus
`qtr_pairing_process/db_management/sql`.

## Outputs

For version `vX.Y.Z`, the executable is built as
`dist/QTR_Pairing_Process_vX.Y.Z.exe`, copied to
`release/vX.Y.Z/QTR_Pairing_Process_vX.Y.Z.exe`, and hashed with SHA-256 into
`release/vX.Y.Z/SHA256SUMS.txt`.

The script creates `release/vX.Y.Z` as needed, creates a placeholder
`RELEASE_NOTES_vX.Y.Z.md` only if none exists, copies
`docs/FULL_USER_GUIDE.md` to `USER_GUIDE_vX.Y.Z.md`, creates a publish
checklist only if none exists, and writes `RELEASE_MANIFEST.md`. It then zips
every file in that release directory to
`release/QTR_Pairing_Process_vX.Y.Z_release_bundle.zip`.

The generated manifest lists `ADVANCED_SORTING_GUIDE.md`, but this script does
not create or copy that file. The script also does not code-sign the EXE,
create or push a tag, create a GitHub release, upload artifacts, or publish
the ZIP. Those activities are outside this script and must not be assumed to
have happened after a successful build.

## Release checklist supported by the script

1. Update `qtr_pairing_process/VERSION` before building when a new version is
   intended.
2. Build from a clean, up-to-date `main` with all local branches merged or
   deleted, unless an explicit emergency exception is approved.
3. Ensure `docs/FULL_USER_GUIDE.md` exists.
4. Verify the release EXE and `SHA256SUMS.txt` exist after the build.
5. Review release notes and the generated manifest before performing any
   separate tag or publishing process.

Release approval, signing, GitHub publishing, and post-release deployment are
out of scope for `scripts/build_release.ps1`.
