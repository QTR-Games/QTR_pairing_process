# Create New Feature Branch Script
# Usage: .\new-feature.ps1

param(
    [string]$BranchName
)

Write-Host "=== QTR Pairing Process - New Feature Branch ===" -ForegroundColor Cyan
Write-Host ""

# Get branch name if not provided
if (-not $BranchName) {
    $BranchName = Read-Host "Enter new feature branch name (e.g., 'add-dark-mode', 'fix-import-bug')"
}

# Validate branch name
if (-not $BranchName) {
    Write-Host "ERROR: Branch name cannot be empty!" -ForegroundColor Red
    exit 1
}

# Navigate to project root
Set-Location C:\Users\Daniel.Raven\QTR_pairing_process

Write-Host "Step 1: Switching to main branch..." -ForegroundColor Yellow
git checkout main

Write-Host ""
Write-Host "Step 2: Pulling latest changes from origin/main..." -ForegroundColor Yellow
git pull origin main

Write-Host ""
Write-Host "Step 3: Creating new feature branch '$BranchName'..." -ForegroundColor Yellow
git checkout -b $BranchName

Write-Host ""
Write-Host "=== SUCCESS! ===" -ForegroundColor Green
Write-Host "You are now on branch: $BranchName" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Make your changes"
Write-Host "  2. git add ."
Write-Host "  3. git commit -m 'Description of changes'"
Write-Host "  4. git push origin $BranchName"
Write-Host "  5. Create Pull Request on GitHub: $BranchName -> main"
Write-Host ""
Write-Host "Quick commands saved to clipboard!" -ForegroundColor Magenta

# Copy quick commands to clipboard
$commands = @"
# After making changes:
git add .
git commit -m "Your commit message here"
git push origin $BranchName
# Then create PR on GitHub: $BranchName -> main
"@

$commands | Set-Clipboard
