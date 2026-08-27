<#
.SYNOPSIS
    Installs the phone app onto a device over Wi-Fi, without a cable and without
    routing the APK through cloud storage.

.DESCRIPTION
    The manual loop this replaces is: run the workflow, download the artifact,
    unzip it, upload it somewhere, open that on the phone, download it again,
    tap it. This script collapses that to one command by driving `adb` over
    Android's wireless debugging.

    By default it takes the APK from the most recent successful `Release APK`
    workflow run, which is the release-signed build -- the same identity already
    on the phone, so it upgrades in place. Use -Local to build from the working
    tree instead when you are iterating on unpushed changes.

    Nothing here needs the Android SDK on PATH. `adb` is discovered from
    ANDROID_HOME, ANDROID_SDK_ROOT, the standard per-user SDK location, and
    finally PATH, because a stock Android Studio install sets none of them.

.PARAMETER PairAddress
    host:port from the phone's "Pair device with pairing code" dialog. Only
    needed once per phone. Note this is a DIFFERENT port from the one used to
    connect -- the pairing dialog and the main wireless debugging screen show
    two different ports, and using the wrong one fails with a bare
    "failed to authenticate".

.PARAMETER PairCode
    The six-digit code shown alongside PairAddress. Expires in a few minutes.

.PARAMETER Device
    host:port from the main "Wireless debugging" screen. Remembered after the
    first successful connect, so later runs need no arguments at all. Android
    issues a new port every time wireless debugging is toggled off and on, so
    pass this again when a remembered address stops connecting.

.PARAMETER Usb
    Skip wireless entirely and use whatever device is already attached.

.PARAMETER ApkPath
    Install a specific APK instead of fetching one.

.PARAMETER Local
    Build from the working tree instead of downloading from CI. Requires the
    local toolchain described in docs/android-build.md.

.PARAMETER DebugVariant
    With -Local, build the debug variant. Off by default and deliberately so: a
    debug APK is signed with a throwaway key, so Android refuses to install it
    over the release build already on the phone and the failure reads as a
    signature error with no hint about the cause.

.EXAMPLE
    # One time, with the phone showing its pairing dialog:
    .\scripts\Install-ToPhone.ps1 -PairAddress 192.168.1.50:37021 -PairCode 123456 -Device 192.168.1.50:41234

.EXAMPLE
    # Every time after that:
    .\scripts\Install-ToPhone.ps1
#>
[CmdletBinding()]
param(
    [string]$PairAddress,
    [string]$PairCode,
    [string]$Device,
    [switch]$Usb,
    [string]$ApkPath,
    [switch]$Local,
    [switch]$DebugVariant
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$appId = 'com.gronksoft.klikklak'
$repoSlug = 'QTR-Games/QTR_pairing_process'

# The remembered device address lives outside the repository rather than in it.
# A repo-local state file would need a .gitignore entry to stay uncommitted, and
# a developer's LAN address is exactly the kind of thing that should not be one
# `git add -A` away from a public history.
$stateDir = Join-Path $env:LOCALAPPDATA 'KlikKlak'
$statePath = Join-Path $stateDir 'phone-device.json'

function Find-Adb {
    foreach ($root in @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT, (Join-Path $env:LOCALAPPDATA 'Android\Sdk'))) {
        if (-not $root) { continue }
        $probe = Join-Path $root 'platform-tools\adb.exe'
        if (Test-Path $probe) { return $probe }
    }
    $onPath = Get-Command adb -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    throw @'
adb was not found.

It ships with the Android SDK "platform-tools" package. Install it through
Android Studio (SDK Manager -> SDK Tools -> Android SDK Platform-Tools), or set
ANDROID_HOME to an existing SDK.
'@
}

# adb reports many failures on stdout while still exiting 0, so the exit code
# alone is not a reliable success signal and callers inspect the text instead.
# Arguments are passed as an explicit array: a `-s` in a remaining-arguments
# parameter would be parsed by PowerShell as a parameter name, not passed on.
function Invoke-Adb {
    param([string[]]$Arguments)
    # Native tools write progress and diagnostics to stderr even when they
    # succeed, and under `$ErrorActionPreference = 'Stop'` a redirected stderr
    # line is promoted to a terminating error. adb's own text is what callers
    # check, so stderr is captured rather than thrown -- otherwise a purely
    # cosmetic message (`monkey` announcing its arguments) aborts a run that
    # has already installed successfully.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $script:adb @Arguments 2>&1 | Out-String
    }
    finally {
        $ErrorActionPreference = $previous
    }
    return $output.Trim()
}

$script:adb = Find-Adb
Write-Host "adb: $script:adb" -ForegroundColor DarkGray

# ---------------------------------------------------------------- connect ----

$target = $null

if (-not $Usb) {
    if ($PairAddress) {
        if (-not $PairCode) {
            throw 'A -PairCode is required with -PairAddress. Both are shown in the phone''s pairing dialog.'
        }
        Write-Host "Pairing with $PairAddress..." -ForegroundColor Cyan
        $pairResult = Invoke-Adb @('pair', $PairAddress, $PairCode)
        Write-Host $pairResult
        if ($pairResult -notmatch 'Successfully paired') {
            throw @"
Pairing failed.

The usual causes, in order of likelihood:
  * the code expired -- it is only valid for a few minutes, so reopen the
    dialog and rerun with the new code and port;
  * -PairAddress used the port from the main wireless debugging screen rather
    than the one in the pairing dialog. They are different;
  * the laptop and phone are on different networks, or the network blocks
    client-to-client traffic (common on guest and venue wifi).
"@
        }
    }

    if (-not $Device -and (Test-Path $statePath)) {
        $Device = (Get-Content $statePath -Raw | ConvertFrom-Json).device
        if ($Device) { Write-Host "Using remembered device $Device" -ForegroundColor DarkGray }
    }

    if (-not $Device) {
        throw @'
No device address.

Pass -Device host:port, using the address shown on the phone under
Developer options -> Wireless debugging. If this phone has never been paired
with this laptop, tap "Pair device with pairing code" and pass -PairAddress and
-PairCode as well; those use a different, one-time port.
'@
    }

    Write-Host "Connecting to $Device..." -ForegroundColor Cyan
    $connectResult = Invoke-Adb @('connect', $Device)
    Write-Host $connectResult
    if ($connectResult -match 'cannot connect|failed to connect|unable to connect') {
        throw @"
Could not connect to $Device.

Android issues a NEW port every time wireless debugging is toggled off and on,
and after most reboots, so a remembered address goes stale routinely. Check the
current host:port on the phone and pass it with -Device.

If the port is right and it still fails, the pairing was lost -- pair again.
"@
    }

    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    @{ device = $Device } | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    $target = $Device
}

# With several devices attached, adb refuses to guess. Resolve to exactly one.
$deviceLines = @((Invoke-Adb @('devices')) -split "`r?`n" |
        Select-Object -Skip 1 |
        Where-Object { $_ -match '\S' -and $_ -notmatch 'offline|unauthorized' })

if ($deviceLines.Count -eq 0) {
    throw 'No usable device is connected. If the phone shows an "Allow debugging?" prompt, accept it and rerun.'
}
if (-not $target) {
    if ($deviceLines.Count -gt 1) {
        throw "More than one device is attached:`n$($deviceLines -join "`n")`nPass -Device to choose one."
    }
    $target = ($deviceLines[0] -split '\s+')[0]
}
Write-Host "Target: $target" -ForegroundColor DarkGray

# -------------------------------------------------------------------- apk ----

if ($ApkPath) {
    if (-not (Test-Path $ApkPath)) { throw "No APK at $ApkPath." }
    $resolvedApk = (Resolve-Path $ApkPath).Path
}
elseif ($Local) {
    $webapp = Join-Path $repoRoot 'webapp'
    $npmScript = if ($DebugVariant) { 'android:build:debug' } else { 'android:build:release' }
    Write-Host "Building locally (npm run $npmScript)..." -ForegroundColor Cyan
    Push-Location $webapp
    try {
        & npm run $npmScript
        if ($LASTEXITCODE -ne 0) { throw "npm run $npmScript failed with exit code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
    $variantDir = if ($DebugVariant) { 'debug' } else { 'release' }
    $built = Join-Path $webapp "android\app\build\outputs\apk\$variantDir"
    $resolvedApk = (Get-ChildItem $built -Filter *.apk -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
    if (-not $resolvedApk) { throw "The build reported success but no APK was found under $built." }
}
else {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'The GitHub CLI (gh) is required to fetch a CI build. Install it, or pass -ApkPath, or use -Local.'
    }

    Write-Host 'Finding the latest successful Release APK run...' -ForegroundColor Cyan
    # The --json list must be a single argument: PowerShell would otherwise split
    # `databaseId, createdAt` on the space and pass `createdAt` to gh as a bare
    # command, which fails with `unknown command "createdAt"`.
    $runJson = & gh run list --repo $repoSlug --workflow=release-apk.yml --status=success --limit 1 --json 'databaseId,createdAt' 2>&1
    if ($LASTEXITCODE -ne 0) { throw "gh run list failed: $runJson" }

    $runs = @($runJson | ConvertFrom-Json)
    if ($runs.Count -eq 0) {
        throw 'No successful Release APK run was found. Trigger the "Release APK" workflow from the Actions tab first, or use -Local.'
    }
    $run = $runs[0]
    Write-Host "  run $($run.databaseId) from $($run.createdAt)" -ForegroundColor DarkGray

    # Cached per run id, so repeated installs of the same build cost nothing and
    # a new build is still picked up automatically.
    $downloadDir = Join-Path ([System.IO.Path]::GetTempPath()) "klikklak-apk-$($run.databaseId)"
    $cached = @(Get-ChildItem $downloadDir -Recurse -Filter *.apk -ErrorAction SilentlyContinue)
    if ($cached.Count -eq 0) {
        Remove-Item $downloadDir -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
        Write-Host 'Downloading the artifact...' -ForegroundColor Cyan
        $downloadResult = & gh run download $run.databaseId --repo $repoSlug --dir $downloadDir 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw @"
gh run download failed: $downloadResult

Artifacts are kept for 90 days. If the run is older than that its artifact is
gone and a new run is needed.
"@
        }
    }
    else {
        Write-Host 'Reusing the already-downloaded artifact.' -ForegroundColor DarkGray
    }

    $resolvedApk = (Get-ChildItem $downloadDir -Recurse -Filter *.apk | Select-Object -First 1).FullName
    if (-not $resolvedApk) { throw "The artifact contained no APK. Looked under $downloadDir." }
}

$apkItem = Get-Item $resolvedApk
Write-Host ("APK: {0} ({1:N1} MB)" -f $apkItem.Name, ($apkItem.Length / 1MB)) -ForegroundColor DarkGray

# ---------------------------------------------------------------- install ----

Write-Host 'Installing...' -ForegroundColor Cyan
$installResult = Invoke-Adb @('-s', $target, 'install', '-r', $resolvedApk)
Write-Host $installResult

if ($installResult -match 'INSTALL_FAILED_VERSION_DOWNGRADE') {
    $installed = Invoke-Adb @('-s', $target, 'shell', 'dumpsys', 'package', $appId)
    $current = ([regex]::Match($installed, 'versionCode=(\d+)')).Groups[1].Value
    throw @"
The phone already has a build with a versionCode at or above this one$(if ($current) { " (installed: $current)" }).

Android will not install over a newer build, and reports it as this error or as
a bare "App not installed". Rerun the Release APK workflow with a HIGHER version
code, or uninstall first -- note that uninstalling erases the saved boards,
which live in the app's local storage and are not backed up anywhere.
"@
}

if ($installResult -match 'INSTALL_FAILED_UPDATE_INCOMPATIBLE|signatures do not match') {
    throw @"
The installed app is signed with a different key than this APK.

The usual cause is mixing a debug build with a release build: they use different
signing identities and Android treats them as different apps that happen to
share an ID. Install the release APK (the default for this script), or uninstall
the existing app first -- which erases its saved boards.
"@
}

if ($installResult -notmatch 'Success') {
    throw "The install did not report success. adb said:`n$installResult"
}

Write-Host ''
Write-Host 'Installed. Launching...' -ForegroundColor Green
Invoke-Adb @('-s', $target, 'shell', 'monkey', '-p', $appId, '-c', 'android.intent.category.LAUNCHER', '1') | Out-Null
