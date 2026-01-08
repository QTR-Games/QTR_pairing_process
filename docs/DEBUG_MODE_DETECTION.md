# Debug Mode Detection Implementation

## Overview
The application automatically populates team dropdowns when running under a debugger to streamline development testing workflow.

## Implementation Details

### Detection Method
Uses `sys.gettrace()` to detect if Python's trace/debug mechanism is active.

**Location**: `qtr_pairing_process/ui_manager.py` in `set_team_dropdowns()` method

### Behavior
When debugger is detected:
1. First team in database → Left dropdown
2. Second team in database → Right dropdown  
3. Grid data auto-loads after 100ms delay

### Compatibility

**Works With**:
- VS Code debugpy (primary development environment)
- PyCharm debugger
- pdb (Python's built-in debugger)
- Most IDE debuggers using Python's trace mechanism

**Known Limitations**:
- May trigger with code coverage tools or profilers
- Some custom debuggers may not use Python's trace mechanism
- Not 100% universal across all debugging environments

## Alternative Implementation

If more explicit control needed in future:

```python
import os
if os.getenv('DEBUG_MODE') == 'true':
    # Auto-populate teams
```

With `launch.json` configuration:
```json
{
  "env": {"DEBUG_MODE": "true"}
}
```

## Decision Rationale

**Current approach chosen because**:
- Single-developer workflow - no need for complex configuration
- Works reliably with VS Code debugging (primary tool)
- Simple implementation without external configuration
- Easy to understand and maintain

**When to revisit**:
- Multiple developers with different debugging setups
- False positives from profiling/coverage tools become problematic
- Need for more explicit control over debug behavior

## Last Updated
January 8, 2026
