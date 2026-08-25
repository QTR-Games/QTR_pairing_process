<#
.SYNOPSIS
    Publishes the local release signing material to GitHub Actions secrets so
    CI can produce signed APKs.

.DESCRIPTION
    Reads webapp/android/keystore.properties and the keystore it points at, then
    sets four repository secrets with `gh secret set`:

        ANDROID_KEYSTORE_BASE64
        ANDROID_KEYSTORE_PASSWORD
        ANDROID_KEY_ALIAS
        ANDROID_KEY_PASSWORD

    Values are piped to gh over stdin, so no secret is ever placed on a command
    line where it could land in PowerShell history or a process listing.

    Re-run this after rotating the keystore. Secrets are overwritten in place.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Publish-SigningSecrets.ps1

.EXAMPLE
    cd webapp; npm run android:signing:secrets
#>
[CmdletBinding()]
param(
    [string]$Repo = 'QTR-Games/QTR_pairing_process',
    [string]$PropertiesPath
)

$ErrorActionPreference = 'Stop'

# scripts/ sits at the repository root; the Capacitor project is in webapp/.
$repoRoot = Split-Path -Parent $PSScriptRoot
$androidDir = Join-Path $repoRoot 'webapp\android'
if (-not $PropertiesPath) { $PropertiesPath = Join-Path $androidDir 'keystore.properties' }

if (-not (Test-Path $PropertiesPath)) {
    throw "No keystore.properties at $PropertiesPath. Run scripts\New-ReleaseKeystore.ps1 first."
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

foreach ($required in @('storeFile', 'storePassword', 'keyAlias', 'keyPassword')) {
    if (-not $properties.ContainsKey($required)) {
        throw "keystore.properties is missing '$required'."
    }
}

# storeFile is stored relative to webapp/android/. .NET resolves relative paths
# against its own working directory rather than PowerShell's, so build an
# absolute path.
$storeFile = $properties['storeFile']
if (-not [System.IO.Path]::IsPathRooted($storeFile)) {
    $storeFile = Join-Path $androidDir $storeFile
}
$storeFile = [System.IO.Path]::GetFullPath($storeFile)

if (-not (Test-Path $storeFile)) { throw "Keystore not found at $storeFile." }

$base64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($storeFile))

$secrets = [ordered]@{
    ANDROID_KEYSTORE_BASE64   = $base64
    ANDROID_KEYSTORE_PASSWORD = $properties['storePassword']
    ANDROID_KEY_ALIAS         = $properties['keyAlias']
    ANDROID_KEY_PASSWORD      = $properties['keyPassword']
}

foreach ($name in $secrets.Keys) {
    $secrets[$name] | gh secret set $name --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw "Failed to set secret $name (gh exit $LASTEXITCODE)." }
    Write-Host "  set $name" -ForegroundColor Green
}

Write-Host ''
Write-Host "Published 4 signing secrets to $Repo." -ForegroundColor Green
Write-Host 'Run the "Release APK" workflow to produce a signed, installable build.'
