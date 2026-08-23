param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "test", "test-fast", "lint", "format", "typecheck", "run", "check", "help")]
    [string]$Task = "help"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Assert-LastExitCode {
    param([string]$Operation)

    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Get-VenvPython {
    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment not found. Run '.\dev.ps1 setup' first."
    }

    return $venvPython
}

function Invoke-Tests {
    param([switch]$Fast)

    $python = Get-VenvPython
    $baseTemp = Join-Path ([System.IO.Path]::GetTempPath()) "qtr-pytest-$([guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $baseTemp | Out-Null

    try {
        $arguments = @("-m", "pytest", "-q", "--basetemp=$baseTemp")
        if ($Fast) {
            $arguments += @("-x", "-m", "not requires_tk")
        }

        & $python @arguments
        Assert-LastExitCode "pytest"
    }
    finally {
        if (Test-Path $baseTemp) {
            Remove-Item -Recurse -Force $baseTemp
        }
    }
}

function Invoke-Lint {
    $python = Get-VenvPython
    & $python -m ruff check .
    Assert-LastExitCode "ruff check"
}

function Invoke-Format {
    $python = Get-VenvPython
    & $python -m ruff check --select I --fix .
    Assert-LastExitCode "ruff import sorting"
    & $python -m ruff format .
    Assert-LastExitCode "ruff format"
}

function Invoke-Typecheck {
    $python = Get-VenvPython
    & $python -m mypy qtr_pairing_process
    Assert-LastExitCode "mypy"
}

function Invoke-Setup {
    $bootstrapPython = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $bootstrapPython) {
        & py -3 -m venv .venv
    }
    else {
        & python -m venv .venv
    }
    Assert-LastExitCode "virtual environment creation"

    $python = Get-VenvPython
    & $python -m pip install --upgrade pip
    Assert-LastExitCode "pip upgrade"
    & $python -m pip install -r requirements.txt
    Assert-LastExitCode "application dependency installation"
    & $python -m pip install pytest ruff mypy
    Assert-LastExitCode "development tool installation"
}

function Show-Help {
    @"
Usage: .\dev.ps1 <task>

Tasks:
  setup       Create .venv and install application and development dependencies.
  test        Run the complete pytest suite with an isolated temporary directory.
  test-fast   Stop on first failure and skip tests marked requires_tk.
  lint        Run ruff checks.
  format      Fix import sorting, then format with ruff.
  typecheck   Type-check qtr_pairing_process with mypy.
  run         Start the Tkinter application through main.py.
  check       Run lint, typecheck, and the complete test suite.
  help        Show this message.
"@ | Write-Host
}

Push-Location $repoRoot
try {
    switch ($Task) {
        "setup" { Invoke-Setup }
        "test" { Invoke-Tests }
        "test-fast" { Invoke-Tests -Fast }
        "lint" { Invoke-Lint }
        "format" { Invoke-Format }
        "typecheck" { Invoke-Typecheck }
        "run" {
            $python = Get-VenvPython
            & $python main.py
            Assert-LastExitCode "application"
        }
        "check" {
            Invoke-Lint
            Invoke-Typecheck
            Invoke-Tests
        }
        "help" { Show-Help }
    }
}
finally {
    Pop-Location
}
