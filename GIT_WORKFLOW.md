# QTR Pairing Process - Git Workflow Scripts

This folder contains three PowerShell scripts to streamline your feature branch workflow.

## Quick Reference

### 1. Start New Feature
```powershell
.\new-feature.ps1
# Or with branch name:
.\new-feature.ps1 -BranchName "add-export-feature"
```

### 2. Push Feature and Create PR
```powershell
.\finish-feature.ps1
```

### 3. Cleanup After PR Merged
```powershell
.\cleanup-feature.ps1
```

## Complete Workflow Example

```powershell
# 1. Start working on a new feature
.\new-feature.ps1
# Enter: "fix-database-bug"

# 2. Make your changes to files
# ... edit code ...

# 3. Commit your work
git add .
git commit -m "Fixed database connection issue"

# 4. Push and prepare PR
.\finish-feature.ps1
# Opens PR URL in browser/clipboard

# 5. Create PR on GitHub (fix-database-bug -> main)
# Wait for review and merge

# 6. Clean up after merge
.\cleanup-feature.ps1
# Deletes feature branch, pulls latest main
```

## Script Details

### new-feature.ps1
- Ensures you're on main
- Pulls latest changes
- Creates new feature branch
- Copies quick commands to clipboard

### finish-feature.ps1
- Pushes current branch to origin
- Generates PR URL
- Copies PR creation link

### cleanup-feature.ps1
- Switches back to main
- Pulls your merged changes
- Deletes feature branch locally
- Deletes feature branch remotely

## Best Practices

✅ Always branch FROM main
✅ Always merge TO main
✅ Delete branches after merge
✅ One feature per branch
✅ Use descriptive branch names

❌ Don't work directly on main
❌ Don't merge main into feature branches
❌ Don't reuse old feature branches

## Branch Naming Convention

Good examples:
- `add-dark-mode`
- `fix-import-crash`
- `update-database-schema`
- `improve-tree-performance`

Avoid:
- `changes` (too vague)
- `my-branch` (not descriptive)
- `Version3` (use features, not versions)
