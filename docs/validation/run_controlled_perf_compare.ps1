param(
    [Parameter(Mandatory = $true)]
    [string]$BaselineGlob,

    [Parameter(Mandatory = $true)]
    [string]$NewGlob,

    [string]$LogDir = "perf_logs",
    [string]$OutMd = "docs/validation/perf_summary.md",
    [string]$OutCsv = "docs/validation/perf_summary.csv",
    [int]$MinSamplesStartup = 5,
    [int]$MinSamplesSort = 5
)

$baselineFiles = Get-ChildItem -Path $LogDir -Filter $BaselineGlob -File | Sort-Object Name
$newFiles = Get-ChildItem -Path $LogDir -Filter $NewGlob -File | Sort-Object Name

Write-Host "Baseline files found: $($baselineFiles.Count)"
Write-Host "New files found: $($newFiles.Count)"

if ($baselineFiles.Count -lt $MinSamplesStartup -or $newFiles.Count -lt $MinSamplesStartup) {
    Write-Error "Not enough files for startup sample gate. Need >= $MinSamplesStartup per window."
    exit 1
}

$pythonExe = Join-Path ".venv\Scripts" "python.exe"

& $pythonExe "docs/validation/generate_perf_summary.py" `
    --log-dir $LogDir `
    --baseline-glob $BaselineGlob `
    --new-glob $NewGlob `
    --out-md $OutMd `
    --out-csv $OutCsv `
    --min-samples-startup $MinSamplesStartup `
    --min-samples-sort $MinSamplesSort

if ($LASTEXITCODE -ne 0) {
    Write-Error "Perf summary generation failed."
    exit $LASTEXITCODE
}

Write-Host "Generated: $OutMd"
Write-Host "Generated: $OutCsv"
