# Finish Feature Branch Script
# Usage: .\finish-feature.ps1

Write-Host "=== QTR Pairing Process - Finish Feature Branch ===" -ForegroundColor Cyan
Write-Host ""

# Get current branch
$currentBranch = git branch --show-current

if ($currentBranch -eq "main") {
    Write-Host "ERROR: You are on main branch. Switch to a feature branch first!" -ForegroundColor Red
    exit 1
}

Write-Host "Current branch: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Confirm
$confirm = Read-Host "Push this branch and prepare for PR? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "Step 1: Pushing branch to origin..." -ForegroundColor Yellow
git push origin $currentBranch

Write-Host ""
Write-Host "=== SUCCESS! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Go to: https://github.com/QTR-Games/QTR_pairing_process/pulls"
Write-Host "  2. Click 'New Pull Request'"
Write-Host "  3. Set: $currentBranch -> main"
Write-Host "  4. Add description and create PR"
Write-Host "  5. After PR is merged, run: .\cleanup-feature.ps1"
Write-Host ""

# Copy GitHub PR URL to clipboard
$prUrl = "https://github.com/QTR-Games/QTR_pairing_process/compare/main...$currentBranch"
$prUrl | Set-Clipboard
Write-Host "PR creation URL copied to clipboard!" -ForegroundColor Magenta
