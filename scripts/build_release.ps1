param(
    [string]$Version = "",
    [switch]$SkipInstall,
    [switch]$SkipTests,
    # Pass -SkipGitChecks only in an emergency (e.g. offline build).
    # All normal releases MUST pass every git pre-flight check.
    [switch]$SkipGitChecks
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# ─── Git pre-flight checks ───────────────────────────────────────────────────
if ($SkipGitChecks) {
    Write-Warning "Git pre-flight checks are SKIPPED (-SkipGitChecks). Use only in an emergency."
} else {
    Write-Host ""
    Write-Host "=== Git Pre-Flight Checks ==="

    # Fetch so local tracking refs reflect current remote state.
    Write-Host "  Fetching latest state from origin..."
    git fetch origin 2>&1 | Out-Null

    # 1. Must be on main.
    $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($currentBranch -ne "main") {
        throw "Pre-flight failed: You are on branch '$currentBranch'. All releases must be built from 'main'. Switch to main and retry."
    }
    Write-Host "  [OK] Current branch: main"

    # 2. Working directory must be clean.
    $dirtyFiles = git status --porcelain
    if ($dirtyFiles) {
        Write-Host ""
        Write-Host "Pre-flight failed: Working directory has uncommitted changes:"
        $dirtyFiles | ForEach-Object { Write-Host "  $_" }
        throw "Commit or stash all changes before building a release."
    }
    Write-Host "  [OK] Working directory is clean"

    # 3. Local main must be in sync with origin/main (no unpushed commits, no unpulled commits).
    $localCommit  = (git rev-parse main).Trim()
    $remoteCommit = (git rev-parse origin/main).Trim()
    if ($localCommit -ne $remoteCommit) {
        $ahead  = [int](git rev-list --count "origin/main..main")
        $behind = [int](git rev-list --count "main..origin/main")
        Write-Host ""
        if ($ahead -gt 0) {
            Write-Host "  Local main is $ahead commit(s) AHEAD of origin/main (unpushed):"
            git log --oneline "origin/main..main" | ForEach-Object { Write-Host "    $_" }
        }
        if ($behind -gt 0) {
            Write-Host "  Local main is $behind commit(s) BEHIND origin/main (unpulled):"
            git log --oneline "main..origin/main" | ForEach-Object { Write-Host "    $_" }
        }
        throw "Pre-flight failed: Local main and origin/main are out of sync. Push or pull before releasing."
    }
    Write-Host "  [OK] Local main is in sync with origin/main"

    # 4. Check for local branches that have commits not yet merged into main.
    $rawUnmerged = git branch --no-merged main 2>&1
    $unmergedBranches = $rawUnmerged |
        Where-Object { $_ -match '\S' } |
        ForEach-Object { $_.Trim().TrimStart('* ') } |
        Where-Object { $_ -ne '' }
    if ($unmergedBranches) {
        Write-Host ""
        Write-Host "  Pre-flight failed: The following local branches have commits NOT merged into main:"
        foreach ($b in $unmergedBranches) {
            $unmergedCount = [int](git rev-list --count "main..$b" 2>$null)
            Write-Host "    - $b  ($unmergedCount unmerged commit(s))"
            git log --oneline "main..$b" | ForEach-Object { Write-Host "        $_" }
        }
        Write-Host ""
        Write-Host "  Review the commits above and decide whether they should be merged into main before this release."
        Write-Host "  To skip this check in an emergency: -SkipGitChecks"
        throw "Pre-flight failed: Unmerged local branches exist. Merge or delete them before releasing."
    }
    Write-Host "  [OK] No local branches with unmerged commits"

    # 5. Check for open pull requests (requires gh CLI; skipped gracefully if unavailable).
    $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghCmd) {
        Write-Host "  Checking for open pull requests..."
        $prJson = gh pr list --state open --json number,title,headRefName 2>$null
        if ($prJson) {
            try {
                $openPRs = $prJson | ConvertFrom-Json
                if ($openPRs -and $openPRs.Count -gt 0) {
                    Write-Host ""
                    Write-Host "  Pre-flight failed: $($openPRs.Count) open pull request(s) exist:"
                    foreach ($pr in $openPRs) {
                        Write-Host "    - PR #$($pr.number): '$($pr.title)'  [branch: $($pr.headRefName)]"
                    }
                    Write-Host ""
                    Write-Host "  Merge, close, or confirm each PR is intentionally excluded before releasing."
                    Write-Host "  To skip this check in an emergency: -SkipGitChecks"
                    throw "Pre-flight failed: Open pull requests exist. Resolve them before releasing."
                }
                Write-Host "  [OK] No open pull requests"
            } catch [System.Management.Automation.RuntimeException] {
                # Rethrow our own throw; swallow JSON parse errors from gh output.
                throw
            } catch {
                Write-Warning "  Could not parse PR list from gh CLI; skipping PR check."
            }
        }
    } else {
        Write-Warning "  gh CLI not found; skipping open-PR check. Install GitHub CLI for full pre-flight coverage."
    }

    Write-Host ""
    Write-Host "All pre-flight checks passed."
    Write-Host ""
}
# ─────────────────────────────────────────────────────────────────────────────

$python = Join-Path $repoRoot ".venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    throw "Python executable not found at $python. Create and configure the venv first."
}

$canonicalVersionFile = Join-Path $repoRoot "qtr_pairing_process/VERSION"
if (-not (Test-Path $canonicalVersionFile)) {
    throw "Canonical version file not found: $canonicalVersionFile"
}

$canonicalVersion = (& $python "scripts/version_tools.py" --show).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read canonical version from scripts/version_tools.py"
}
if ($canonicalVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Canonical version '$canonicalVersion' is invalid. Expected major.service.maintenance (for example 2.1.1)."
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = $canonicalVersion
}
elseif ($Version -ne $canonicalVersion) {
    throw "Version mismatch: requested '$Version' but canonical version is '$canonicalVersion'. Update qtr_pairing_process/VERSION or omit -Version."
}

$setupContent = Get-Content (Join-Path $repoRoot "setup.py") -Raw
if ($setupContent -notmatch 'version\s*=\s*_read_app_version\(\)') {
    throw "Preflight failed: setup.py must source version from canonical VERSION file via _read_app_version()."
}

$exeName = "QTR_Pairing_Process_v$Version"
$baseExeName = "QTR_Pairing_Process"
$distDir = Join-Path $repoRoot "dist"
$releaseRoot = Join-Path $repoRoot "release"
$releaseDir = Join-Path $releaseRoot "v$Version"
$exeSource = Join-Path $distDir "$exeName.exe"
$specExeSource = Join-Path $distDir "$baseExeName.exe"
$exeRelease = Join-Path $releaseDir "$exeName.exe"
$checksumFile = Join-Path $releaseDir "SHA256SUMS.txt"
$zipPath = Join-Path $releaseRoot "${exeName}_release_bundle.zip"

Write-Host "=== QTR Release Build ==="
Write-Host "Version: v$Version"
Write-Host "Repo: $repoRoot"
Write-Host "Python: $python"

if (-not (Test-Path $releaseRoot)) {
    New-Item -ItemType Directory -Path $releaseRoot | Out-Null
}
if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

if (-not $SkipInstall) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
    & $python -m pip install pyinstaller==6.19.0
}

if (-not $SkipTests) {
    & $python -m pytest -q test_database_preferences.py test_phase11_regression.py
}

if (Test-Path $exeSource) {
    Remove-Item $exeSource -Force
}
if (Test-Path $specExeSource) {
    Remove-Item $specExeSource -Force
}
if (Test-Path (Join-Path $repoRoot "build")) {
    Remove-Item (Join-Path $repoRoot "build") -Recurse -Force
}

# Always build a self-contained single-file exe using explicit flags.
# Required data bundles (prevents runtime errors in the frozen exe):
#   --collect-all qtr_pairing_process  — bundles every sub-package so no ModuleNotFoundError at launch
#   --add-data docs;docs               — bundles FULL_USER_GUIDE.md so Help > User Guide works
#   --add-data sql;sql                 — bundles SQL schema files for database bootstrap
Write-Host "Building self-contained exe..."
$sqlDataArg  = "qtr_pairing_process/db_management/sql;qtr_pairing_process/db_management/sql"
$docsDataArg = "docs;docs"
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name $exeName `
    --add-data $sqlDataArg `
    --add-data $docsDataArg `
    --collect-all qtr_pairing_process `
    main.py

if (-not (Test-Path $exeSource)) {
    throw "Build finished without expected artifact: $exeSource"
}

Copy-Item $exeSource $exeRelease -Force

$hash = (Get-FileHash $exeRelease -Algorithm SHA256).Hash
"SHA256  $hash  $exeName.exe" | Set-Content $checksumFile

$releaseNotes = Join-Path $releaseDir "RELEASE_NOTES_v$Version.md"
$userGuide = Join-Path $releaseDir "USER_GUIDE_v$Version.md"
$manifest = Join-Path $releaseDir "RELEASE_MANIFEST.md"
$publishChecklist = Join-Path $releaseDir "RELEASE_PUBLISH_CHECKLIST_v$Version.md"

if (-not (Test-Path $releaseNotes)) {
    "# Release Notes`n`nAdd release notes for v$Version." | Set-Content $releaseNotes
}

# Always copy the canonical user guide from docs/ into the release folder.
$canonicalGuide = Join-Path $repoRoot "docs\FULL_USER_GUIDE.md"
if (-not (Test-Path $canonicalGuide)) {
    throw "Preflight failed: docs/FULL_USER_GUIDE.md not found. Update the user guide before building a release."
}
Copy-Item $canonicalGuide $userGuide -Force
Write-Host "User guide copied: $userGuide"
if (-not (Test-Path $publishChecklist)) {
    @"
# Release Publish Checklist - v$Version

- [ ] Create or verify release tag: v$Version
- [ ] Verify artifacts exist in release/v$Version
- [ ] Validate SHA256SUMS.txt against release executable
- [ ] Review RELEASE_NOTES_v$Version.md for Known Performance Debt disclosure
- [ ] Attach EXE and documentation assets to the GitHub release
"@ | Set-Content $publishChecklist
}

$commit = (git rev-parse --short HEAD).Trim()
$timestampUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$manifestContent = @"
# Release Manifest - v$Version

## Build Metadata

- Version: v$Version
- Build timestamp (UTC): $timestampUtc
- Commit: $commit
- Build host OS: Windows
- Build script: scripts/build_release.ps1

## Artifacts

- $exeName.exe
- SHA256SUMS.txt
- RELEASE_NOTES_v$Version.md
- USER_GUIDE_v$Version.md  (copied from docs/FULL_USER_GUIDE.md)
- ADVANCED_SORTING_GUIDE.md

## Integrity

$((Get-Content $checksumFile) -join "`n")

## Reproducible Build Command

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1 -Version $Version
~~~
"@

$manifestContent | Set-Content $manifest

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath

Write-Host ""
Write-Host "Build complete."
Write-Host "EXE: $exeRelease"
Write-Host "SHA256: $checksumFile"
Write-Host "Manifest: $manifest"
Write-Host "Bundle: $zipPath"
