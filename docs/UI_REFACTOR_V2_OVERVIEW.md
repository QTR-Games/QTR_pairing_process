# UI Manager V2 Refactor - Architecture Overview

**Date:** January 12, 2026  
**Branch:** matchup-dropdown-picker-fixes  
**Original File:** ui_manager_v1_backup.py (3928 lines)  
**Refactored File:** ui_manager_v2.py

---

## Refactor Objectives

**Primary Goal:** Reduce Team Grid tab switch time from 290ms → <150ms

**Performance Bottlenecks Addressed:**
1. Mixed geometry managers (pack + grid in same hierarchy)
2. 113 trace callbacks firing on every change
3. 75 mouse event bindings (3 events × 25 cells)
4. 6-level deep frame nesting
5. 144 redundant StringVar objects
6. Tab visibility recalculation overhead

---

## Architecture Changes

### 1. **Data Model Centralization**
**Problem:** 144 StringVar objects (72 grid entries + 72 display entries)
**Solution:** Single `GridDataModel` class manages all grid state

```python
class GridDataModel:
    def __init__(self):
        self.ratings = [['' for _ in range(6)] for _ in range(6)]
        self.display = [['' for _ in range(6)] for _ in range(6)]
        self.comments = {}  # (row, col) -> comment_text
        self.disabled_cells = set()  # (row, col) tuples
        
    def get_rating(self, row, col): ...
    def set_rating(self, row, col, value, notify=True): ...
```

**Benefits:**
- Eliminates 144 Tk variable objects
- Single source of truth for grid state
- Batch updates without triggering callbacks
- Easier state serialization/debugging

---

### 2. **Canvas-Based Event Handling**
**Problem:** 75 mouse bindings (Enter/Leave/Button-3 on 25 cells)
**Solution:** Single canvas overlay with coordinate-based hit detection

```python
class CommentOverlay:
    def __init__(self, parent, grid_data):
        self.canvas = tk.Canvas(parent, highlightthickness=0)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<Button-3>', self.on_right_click)
        
    def on_mouse_move(self, event):
        cell = self.get_cell_from_coords(event.x, event.y)
        if cell and self.grid_data.has_comment(*cell):
            self.show_tooltip(cell)
```

**Benefits:**
- 75 bindings → 2 bindings (98% reduction)
- Single event handler with coordinate math
- Lower memory overhead
- Easier tooltip management

---

### 3. **Trace Callback Suppression**
**Problem:** 113 trace callbacks fire during batch updates
**Solution:** Context manager for trace suppression

```python
class TraceSuppressionContext:
    def __init__(self, ui_manager):
        self.ui = ui_manager
        
    def __enter__(self):
        self.ui._suppress_traces = True
        return self
        
    def __exit__(self, *args):
        self.ui._suppress_traces = False
        self.ui._flush_pending_updates()
```

**Usage:**
```python
with self.suppress_traces():
    for row in range(1, 6):
        for col in range(1, 6):
            self.grid_data.set_rating(row, col, new_value, notify=False)
# Callbacks fire once after context exit
```

**Benefits:**
- Prevents callback cascade
- Batch UI updates
- Cleaner load/flip operations

---

### 4. **Flattened Frame Hierarchy**
**Problem:** 6-level deep nesting causes layout cascades
**Solution:** 3-level maximum depth

**Before:**
```
root → notebook → team_grid_frame → top_frame → grid_frame → Entry widgets
```

**After:**
```
root → notebook → team_grid_frame → Entry widgets (direct grid placement)
```

**Benefits:**
- Faster geometry calculations
- Reduced pack/grid conflicts
- Clearer widget hierarchy

---

### 5. **Unified Geometry Manager**
**Problem:** Mixed pack() and grid() in same containers
**Solution:** Use grid() for grid widgets, pack() only for outer containers

**Strategy:**
- Notebook tabs: pack()
- Grid entries: grid()
- Button rows: grid()
- No mixing in same frame

**Benefits:**
- Predictable layout behavior
- Single layout calculation pass
- Faster resize performance

---

### 6. **Tab Visibility Optimization**
**Problem:** 290ms to show cached Team Grid tab (no widgets created)
**Solution:** Keep widgets mapped, control visibility via grid_remove()

```python
def on_tab_switch(self, event):
    current_tab = self.notebook.select()
    
    # Don't unmap widgets, just hide from geometry manager
    for tab_name, frame in self.tab_frames.items():
        if tab_name == current_tab:
            frame.grid()  # Show
        else:
            frame.grid_remove()  # Hide but keep configured
```

**Benefits:**
- Eliminates geometry recalculation
- Widgets stay in memory (cached state)
- Near-instant tab switches

---

## Implementation Phases

### Phase A: Data Model + Trace Suppression
**Files:** grid_data_model.py, trace_suppression.py
**Impact:** Foundational for other changes
**Risk:** Low - isolated new modules

### Phase B: Canvas Event Handling
**Files:** comment_overlay.py, canvas_event_handler.py
**Impact:** Eliminates 73 bindings
**Risk:** Medium - changes event flow

### Phase C: Frame Flattening
**Files:** ui_manager_v2.py (structural)
**Impact:** Reduces layout depth
**Risk:** Medium - requires widget reparenting

### Phase D: Geometry Manager Consolidation
**Files:** ui_manager_v2.py (cleanup)
**Impact:** Final optimization
**Risk:** Low - cosmetic changes

---

## Performance Expectations

**Current (V1):**
- Team Grid tab switch (cached): 290-324ms
- Matchup Tree tab switch: 75-97ms (first: 226ms)
- Window resize: Noticeable lag

**Target (V2):**
- Team Grid tab switch (cached): <150ms
- Matchup Tree tab switch: <50ms
- Window resize: Negligible lag

**Measurement:**
- All timings include `update_idletasks()` for actual rendering
- Debug mode outputs timing to console
- Test across 5-10 tab switches for average

---

## Rollback Strategy

**Fallback to V1:**
```python
# In main.py
from qtr_pairing_process.ui_manager_v1_backup import UiManager
# Instead of: from qtr_pairing_process.ui_manager import UiManager
```

**Version Selection:**
```python
# ui_manager.py acts as wrapper
USE_V2 = True  # Set to False to use V1

if USE_V2:
    from .ui_manager_v2 import UiManager
else:
    from .ui_manager_v1_backup import UiManager
```

---

## Testing Checklist

- [ ] All grid cells editable
- [ ] Comment indicators display correctly
- [ ] Comment tooltips appear on hover
- [ ] Right-click comment editor works
- [ ] Row/column checkboxes disable cells
- [ ] Grid flip preserves data
- [ ] Save/load grid data
- [ ] Dropdown synchronization
- [ ] Tree generation from grid
- [ ] Tab switching <150ms (debug timing)
- [ ] Window resize smooth
- [ ] No trace callback errors
- [ ] Canvas overlay doesn't block input

---

## Known Limitations

**V2 Differences from V1:**
1. Comment tooltips may appear slightly different (canvas-based)
2. Grid cell hover states controlled by canvas
3. Some internal APIs changed (external API unchanged)

**Future Enhancements:**
- Virtual scrolling for large grids
- Async database loading
- Progressive rendering for 60 dropdowns

---

## Documentation

**Learning Documents:**
- `CANVAS_EVENT_HANDLING.md` - Canvas-based mouse events
- `DATA_MODEL_VS_STRINGVAR.md` - Architecture comparison
- `TRACE_SUPPRESSION_PATTERN.md` - Batch update strategy
- `TAB_VISIBILITY_OPTIMIZATION.md` - Grid remove pattern

**Code Comments:**
- All major functions have docstrings
- Complex algorithms explained inline
- Performance-critical sections marked with `# PERF:`

---

## Migration Notes

**For Future Developers:**

The V2 refactor maintains API compatibility with V1 for external callers (main.py, database code, etc.). Internal structure is significantly different:

- Grid data accessed via `self.grid_data` instead of `self.grid_entries[r][c].get()`
- Comment handling moved to `CommentOverlay` class
- Event bindings centralized in canvas handlers
- Trace callbacks use suppression context

When extending functionality, follow V2 patterns:
- Use data model for state
- Add canvas handlers instead of widget bindings
- Wrap batch operations in trace suppression
- Keep frame hierarchy flat
