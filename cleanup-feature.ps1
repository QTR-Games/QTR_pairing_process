# Cleanup After Feature Merged Script
# Usage: .\cleanup-feature.ps1
# Run this after your feature branch PR has been merged

Write-Host "=== QTR Pairing Process - Cleanup After Merge ===" -ForegroundColor Cyan
Write-Host ""

# Get current branch
$currentBranch = git branch --show-current

if ($currentBranch -eq "main") {
    Write-Host "You are already on main branch." -ForegroundColor Green
    $branchToDelete = Read-Host "Enter the feature branch name to delete"
} else {
    $branchToDelete = $currentBranch
    Write-Host "Current feature branch: $branchToDelete" -ForegroundColor Yellow
}

Write-Host ""
$confirm = Read-Host "Delete branch '$branchToDelete' locally and remotely? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "Step 1: Switching to main..." -ForegroundColor Yellow
git checkout main

Write-Host ""
Write-Host "Step 2: Pulling latest changes (includes your merged work)..." -ForegroundColor Yellow
git pull origin main

Write-Host ""
Write-Host "Step 3: Deleting local branch '$branchToDelete'..." -ForegroundColor Yellow
git branch -d $branchToDelete

Write-Host ""
Write-Host "Step 4: Deleting remote branch '$branchToDelete'..." -ForegroundColor Yellow
git push origin --delete $branchToDelete

Write-Host ""
Write-Host "=== CLEANUP COMPLETE! ===" -ForegroundColor Green
Write-Host "You are now on main with your merged changes." -ForegroundColor Green
Write-Host "Ready to create a new feature branch!" -ForegroundColor Cyan
