"""
Comment Overlay - Canvas-based event handling for grid comments

Replaces 75 widget-level bindings with 2 canvas-level bindings.
Uses coordinate-based hit detection for hover and click events.

© Daniel P Raven and Matt Russell 2024 All Rights Reserved
"""

import tkinter as tk
from typing import Optional, Callable, Tuple


class CommentOverlay:
    """
    Canvas-based event overlay for grid cell interactions.
    
    Handles:
    - Mouse hover detection with coordinate-based hit testing
    - Comment indicator tooltips
    - Right-click context menu for comments
    - Event pass-through for left-clicks (editing)
    
    Advantages:
    - 75 widget bindings → 2 canvas bindings
    - Single event handler for all cells
    - Cleaner coordinate-based logic
    - No per-widget state tracking
    """
    
    def __init__(
        self,
        parent_frame: tk.Frame,
        grid_data_model,
        comment_editor_callback: Callable[[int, int], None]
    ):
        """
        Initialize comment overlay.
        
        Args:
            parent_frame: Frame containing the grid (canvas placed over this)
            grid_data_model: GridDataModel instance for comment state
            comment_editor_callback: Function to call on right-click: callback(row, col)
        """
        self.parent_frame = parent_frame
        self.data_model = grid_data_model
        self.comment_editor_callback = comment_editor_callback
        
        # Canvas overlay - placed over grid using place geometry
        self.canvas = tk.Canvas(
            parent_frame,
            highlightthickness=0,
            cursor='arrow'
        )
        
        # Grid geometry tracking (set by update_grid_geometry())
        self.cell_positions = {}  # {(row, col): (x, y, width, height)}
        self.grid_bbox = None  # Overall grid bounding box
        
        # Tooltip management
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.current_hover_cell: Optional[Tuple[int, int]] = None
        
        # Event bindings - only 2 bindings for entire grid
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<Button-3>', self._on_right_click)  # Right-click
        
        # Left-click pass-through handled by canvas transparency
    
    def show(self):
        """Make canvas visible"""
        if self.grid_bbox:
            x, y, width, height = self.grid_bbox
            self.canvas.place(x=x, y=y, width=width, height=height)
    
    def hide(self):
        """Hide canvas overlay"""
        self.canvas.place_forget()
        self._hide_tooltip()
    
    def update_grid_geometry(self, cell_positions: dict, grid_bbox: Tuple[int, int, int, int]):
        """
        Update grid cell positions for hit detection.
        
        Called after grid layout or resize to update coordinate mapping.
        
        Args:
            cell_positions: {(row, col): (x, y, width, height)} relative to parent
            grid_bbox: (x, y, width, height) of entire grid area
        """
        self.cell_positions = cell_positions
        self.grid_bbox = grid_bbox
        
        # Update canvas placement
        if grid_bbox:
            x, y, width, height = grid_bbox
            self.canvas.place(x=x, y=y, width=width, height=height)
    
    def _get_cell_from_coords(self, canvas_x: int, canvas_y: int) -> Optional[Tuple[int, int]]:
        """
        Convert canvas coordinates to cell (row, col).
        
        Uses bounding box hit testing against stored cell positions.
        
        Args:
            canvas_x, canvas_y: Coordinates relative to canvas origin
        
        Returns:
            (row, col) tuple or None if not over any cell
        """
        if not self.grid_bbox:
            return None
        
        # Convert canvas coords to parent frame coords
        bbox_x, bbox_y, _, _ = self.grid_bbox
        frame_x = canvas_x + bbox_x
        frame_y = canvas_y + bbox_y
        
        # Check each cell for hit
        for (row, col), (x, y, width, height) in self.cell_positions.items():
            if (x <= frame_x < x + width) and (y <= frame_y < y + height):
                return (row, col)
        
        return None
    
    def _on_mouse_move(self, event):
        """
        Handle mouse movement over canvas.
        
        Shows tooltip when hovering over cell with comment.
        Hides tooltip when leaving cell.
        """
        cell = self._get_cell_from_coords(event.x, event.y)
        
        # Check if we've moved to a different cell
        if cell != self.current_hover_cell:
            self._hide_tooltip()
            self.current_hover_cell = cell
            
            # Show tooltip if new cell has comment
            if cell and self.data_model.has_comment(*cell):
                self._show_tooltip(cell, event.x_root, event.y_root)
    
    def _on_right_click(self, event):
        """
        Handle right-click on canvas.
        
        Opens comment editor for the clicked cell.
        """
        cell = self._get_cell_from_coords(event.x, event.y)
        
        if cell:
            row, col = cell
            # Hide tooltip before showing editor
            self._hide_tooltip()
            # Invoke comment editor callback
            self.comment_editor_callback(row, col)
    
    def _show_tooltip(self, cell: Tuple[int, int], x: int, y: int):
        """
        Display tooltip showing comment text.
        
        Args:
            cell: (row, col) of cell with comment
            x, y: Screen coordinates for tooltip placement
        """
        row, col = cell
        comment_text = self.data_model.get_comment(row, col)
        
        if not comment_text:
            return
        
        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.canvas)
        self.tooltip_window.wm_overrideredirect(True)  # No window decorations
        
        # Position slightly offset from mouse
        self.tooltip_window.wm_geometry(f"+{x + 10}+{y + 10}")
        
        # Tooltip content
        label = tk.Label(
            self.tooltip_window,
            text=comment_text,
            background='#ffffe0',  # Light yellow
            foreground='#000000',
            borderwidth=1,
            relief='solid',
            font=('Arial', 9),
            padx=5,
            pady=3,
            justify='left'
        )
        label.pack()
    
    def _hide_tooltip(self):
        """Destroy tooltip window if visible"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
    def refresh_comment_indicators(self, entry_widgets: dict):
        """
        Update visual comment indicators on grid cells.
        
        Args:
            entry_widgets: {(row, col): Entry widget} for indicator placement
        """
        # Clear existing indicators
        for (row, col), entry in entry_widgets.items():
            entry.configure(bg='white')
        
        # Add indicators for cells with comments
        for (row, col) in self.data_model.get_all_comments().keys():
            if (row, col) in entry_widgets:
                entry_widgets[(row, col)].configure(bg='#ffffcc')  # Light yellow background
    
    def on_grid_visibility_changed(self, visible: bool):
        """
        Handle grid visibility changes.
        
        Args:
            visible: True if grid becoming visible, False if hiding
        """
        if visible:
            self.show()
        else:
            self.hide()
            self._hide_tooltip()
    
    def destroy(self):
        """Clean up overlay resources"""
        self._hide_tooltip()
        self.canvas.destroy()
