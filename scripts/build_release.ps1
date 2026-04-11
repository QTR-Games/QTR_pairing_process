param(
    [string]$Version = "2.1.1",
    [switch]$SkipInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    throw "Python executable not found at $python. Create and configure the venv first."
}

$baseExeName = "QTR_Pairing_Process"
$exeName = "${baseExeName}_v$Version"
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

# Use .spec file for proper dependency bundling
$specFile = Join-Path $repoRoot "QTR_Pairing_Process.spec"
if (Test-Path $specFile) {
    Write-Host "Building with .spec file for enhanced dependency handling..."
    & $python -m PyInstaller --noconfirm --clean $specFile

    # Normalize spec output name to the versioned release artifact name.
    if ((-not (Test-Path $exeSource)) -and (Test-Path $specExeSource)) {
        Move-Item -Path $specExeSource -Destination $exeSource -Force
    }
} else {
    Write-Host "Building with command-line options (no .spec file found)..."
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name $exeName main.py
}

if (-not (Test-Path $exeSource)) {
    throw "Build finished without expected artifact: $exeSource"
}

Copy-Item $exeSource $exeRelease -Force

$hash = (Get-FileHash $exeRelease -Algorithm SHA256).Hash
"SHA256  $hash  $exeName.exe" | Set-Content $checksumFile

$releaseNotes = Join-Path $releaseDir "RELEASE_NOTES_v$Version.md"
$userGuide = Join-Path $releaseDir "USER_GUIDE_v$Version.md"
$manifest = Join-Path $releaseDir "RELEASE_MANIFEST.md"

if (-not (Test-Path $releaseNotes)) {
    "# Release Notes`n`nAdd release notes for v$Version." | Set-Content $releaseNotes
}
if (-not (Test-Path $userGuide)) {
    "# User Guide`n`nAdd end-user documentation for v$Version." | Set-Content $userGuide
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
- USER_GUIDE_v$Version.md

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
