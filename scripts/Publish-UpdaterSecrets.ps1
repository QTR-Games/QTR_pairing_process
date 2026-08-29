<#
.SYNOPSIS
    Publishes the local updater signing key to GitHub Actions secrets so CI can
    sign desktop releases.

.DESCRIPTION
    Reads webapp/updater.properties and the private key it points at, then sets
    two repository secrets with `gh secret set`:

        TAURI_SIGNING_PRIVATE_KEY
        TAURI_SIGNING_PRIVATE_KEY_PASSWORD

    The names matter. Tauri v2 reads exactly these; the v1 names
    (TAURI_PRIVATE_KEY, TAURI_KEY_PASSWORD) are silently ignored and produce an
    unsigned artifact no installed app will accept.

    Values are piped to gh over stdin, so no secret is ever placed on a command
    line where it could land in PowerShell history or a process listing.

    Re-run this after rotating the key. Secrets are overwritten in place. The
    rotated public key must be committed in the same breath -- see
    scripts/New-UpdaterKey.ps1, which writes both.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Publish-UpdaterSecrets.ps1

.EXAMPLE
    cd webapp; npm run desktop:updater:secrets
#>
[CmdletBinding()]
param(
    [string]$Repo = 'QTR-Games/QTR_pairing_process',
    [string]$PropertiesPath
)

$ErrorActionPreference = 'Stop'

# scripts/ sits at the repository root; the Tauri project is in webapp/.
$repoRoot = Split-Path -Parent $PSScriptRoot
$webappDir = Join-Path $repoRoot 'webapp'
if (-not $PropertiesPath) { $PropertiesPath = Join-Path $webappDir 'updater.properties' }

if (-not (Test-Path $PropertiesPath)) {
    throw "No updater.properties at $PropertiesPath. Run scripts\New-UpdaterKey.ps1 first."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'The GitHub CLI (gh) is required and was not found on PATH.'
}

$properties = @{}
foreach ($line in Get-Content $PropertiesPath) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
    $separator = $trimmed.IndexOf('=')
    if ($separator -lt 1) { continue }
    $properties[$trimmed.Substring(0, $separator).Trim()] = $trimmed.Substring($separator + 1).Trim()
}

foreach ($required in @('keyFile', 'keyPassword')) {
    if (-not $properties.ContainsKey($required)) {
        throw "updater.properties is missing '$required'."
    }
}

# .NET resolves relative paths against its own working directory rather than
# PowerShell's, so build an absolute path.
$keyFile = $properties['keyFile']
if (-not [System.IO.Path]::IsPathRooted($keyFile)) {
    $keyFile = Join-Path $webappDir $keyFile
}
$keyFile = [System.IO.Path]::GetFullPath($keyFile)

if (-not (Test-Path $keyFile)) { throw "Private key not found at $keyFile." }

# The secret is the file's whole contents -- the base64 blob Tauri wrote, not a
# path to it and not the decoded minisign text.
$secrets = [ordered]@{
    TAURI_SIGNING_PRIVATE_KEY          = (Get-Content $keyFile -Raw).Trim()
    TAURI_SIGNING_PRIVATE_KEY_PASSWORD = $properties['keyPassword']
}

foreach ($name in $secrets.Keys) {
    $secrets[$name] | gh secret set $name --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw "Failed to set secret $name (gh exit $LASTEXITCODE)." }
    Write-Host "  set $name" -ForegroundColor Green
}

Write-Host ''
Write-Host "Published 2 updater signing secrets to $Repo." -ForegroundColor Green
Write-Host 'Run the "Release Desktop" workflow to cut a signed, auto-updating build.'
Write-Host 'It verifies this key against the public key in tauri.conf.json before building.'
