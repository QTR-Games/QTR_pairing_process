"""
Grid Data Model - Centralized state management for rating grid

Replaces 144 StringVar objects with single data model.
Provides observer pattern for UI updates with batch operation support.

© Daniel P Raven and Matt Russell 2024 All Rights Reserved
"""

from typing import Dict, Tuple, Callable, List, Set, Optional, Any


class GridDataModel:
    """
    Centralized data model for grid state management.
    
    Manages:
    - Rating values (6×6 grid)
    - Display/calculated values (6×6 grid)
    - Cell comments (sparse dict)
    - Disabled cell tracking
    
    Features:
    - Observer pattern for change notifications
    - Batch update mode to suppress notifications
    - Single source of truth for all grid state
    """
    
    def __init__(self):
        # Core data structures - pure Python (no Tkinter dependencies)
        self.ratings: List[List[str]] = [['' for _ in range(6)] for _ in range(6)]
        self.display: List[List[str]] = [['' for _ in range(6)] for _ in range(6)]
        self.comments: Dict[Tuple[int, int], str] = {}
        self.disabled_cells: Set[Tuple[int, int]] = set()
        
        # Observer management
        self._observers: List[Callable] = []
        
        # Batch update support
        self._batch_mode = False
        self._pending_notifications: List[Tuple[str, Any]] = []
    
    def add_observer(self, callback: Callable):
        """
        Register observer for data change notifications.
        
        Callback signature: callback(event_type: str, *args)
        
        Event types:
        - 'rating_changed': (row, col, new_value)
        - 'display_changed': (row, col, new_value)
        - 'comment_changed': (row, col, comment_text or None)
        - 'cell_disabled': (row, col, is_disabled)
        - 'batch_update': (list of changes)
        - 'grid_cleared': ()
        - 'grid_loaded': ()
        """
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable):
        """Unregister observer"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, event_type: str, *args):
        """Send notification to all registered observers"""
        if self._batch_mode:
            # Accumulate notifications during batch mode
            self._pending_notifications.append((event_type, args))
        else:
            # Immediate notification
            for observer in self._observers:
                try:
                    observer(event_type, *args)
                except Exception as e:
                    print(f"Observer error: {e}")
    
    # Batch operation context management
    
    def begin_batch(self):
        """Start batch update mode - notifications suppressed until end_batch()"""
        self._batch_mode = True
        self._pending_notifications = []
    
    def end_batch(self):
        """End batch mode - send accumulated notifications as single batch event"""
        self._batch_mode = False
        
        if self._pending_notifications:
            # Send single batch notification with all accumulated changes
            self._notify_observers('batch_update', self._pending_notifications)
            self._pending_notifications = []
    
    # Rating grid access
    
    def get_rating(self, row: int, col: int) -> str:
        """Get rating value for cell"""
        return self.ratings[row][col]
    
    def set_rating(self, row: int, col: int, value: str, notify: bool = True):
        """
        Set rating value with optional notification.
        
        Args:
            row, col: Cell coordinates (0-5)
            value: New rating value
            notify: If False, skip notification (for batch updates)
        """
        old_value = self.ratings[row][col]
        self.ratings[row][col] = value
        
        if notify and old_value != value:
            self._notify_observers('rating_changed', row, col, value)
    
    def get_all_ratings(self) -> List[List[str]]:
        """Get entire rating grid (returns copy)"""
        return [row[:] for row in self.ratings]
    
    def set_all_ratings(self, data: List[List[str]], notify: bool = True):
        """
        Set entire rating grid.
        
        Args:
            data: 6×6 list of rating values
            notify: If False, skip notification
        """
        self.ratings = [row[:] for row in data]
        
        if notify:
            self._notify_observers('grid_loaded')
    
    # Display grid access
    
    def get_display(self, row: int, col: int) -> str:
        """Get display/calculated value for cell"""
        return self.display[row][col]
    
    def set_display(self, row: int, col: int, value: str, notify: bool = True):
        """Set display/calculated value"""
        old_value = self.display[row][col]
        self.display[row][col] = value
        
        if notify and old_value != value:
            self._notify_observers('display_changed', row, col, value)
    
    def get_all_display(self) -> List[List[str]]:
        """Get entire display grid (returns copy)"""
        return [row[:] for row in self.display]
    
    # Comment management
    
    def has_comment(self, row: int, col: int) -> bool:
        """Check if cell has comment"""
        return (row, col) in self.comments
    
    def get_comment(self, row: int, col: int) -> Optional[str]:
        """Get comment text for cell (None if no comment)"""
        return self.comments.get((row, col))
    
    def set_comment(self, row: int, col: int, text: Optional[str], notify: bool = True):
        """
        Set or clear comment for cell.
        
        Args:
            row, col: Cell coordinates
            text: Comment text (None to clear comment)
            notify: If False, skip notification
        """
        cell_key = (row, col)
        
        if text:
            # Set comment
            old_text = self.comments.get(cell_key)
            self.comments[cell_key] = text
            
            if notify and old_text != text:
                self._notify_observers('comment_changed', row, col, text)
        else:
            # Clear comment
            if cell_key in self.comments:
                del self.comments[cell_key]
                
                if notify:
                    self._notify_observers('comment_changed', row, col, None)
    
    def get_all_comments(self) -> Dict[Tuple[int, int], str]:
        """Get all comments (returns copy)"""
        return self.comments.copy()
    
    def clear_all_comments(self, notify: bool = True):
        """Clear all comments"""
        if self.comments:
            self.comments.clear()
            
            if notify:
                self._notify_observers('grid_cleared')
    
    # Cell disable state
    
    def is_cell_disabled(self, row: int, col: int) -> bool:
        """Check if cell is disabled"""
        return (row, col) in self.disabled_cells
    
    def set_cell_disabled(self, row: int, col: int, disabled: bool, notify: bool = True):
        """Enable or disable cell"""
        cell_key = (row, col)
        was_disabled = cell_key in self.disabled_cells
        
        if disabled:
            self.disabled_cells.add(cell_key)
        else:
            self.disabled_cells.discard(cell_key)
        
        if notify and was_disabled != disabled:
            self._notify_observers('cell_disabled', row, col, disabled)
    
    # Bulk operations
    
    def clear_grid(self, notify: bool = True):
        """Clear all rating and display values"""
        self.ratings = [['' for _ in range(6)] for _ in range(6)]
        self.display = [['' for _ in range(6)] for _ in range(6)]
        
        if notify:
            self._notify_observers('grid_cleared')
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Get complete state snapshot for save/undo.
        
        Returns dict with all grid state.
        """
        return {
            'ratings': self.get_all_ratings(),
            'display': self.get_all_display(),
            'comments': self.get_all_comments(),
            'disabled_cells': self.disabled_cells.copy()
        }
    
    def restore_state_snapshot(self, snapshot: Dict[str, Any], notify: bool = True):
        """
        Restore grid state from snapshot.
        
        Use with begin_batch()/end_batch() for efficient restoration.
        """
        self.ratings = [row[:] for row in snapshot['ratings']]
        self.display = [row[:] for row in snapshot['display']]
        self.comments = snapshot['comments'].copy()
        self.disabled_cells = snapshot['disabled_cells'].copy()
        
        if notify:
            self._notify_observers('grid_loaded')
