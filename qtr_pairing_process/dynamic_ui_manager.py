""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import tkinter as tk
from tkinter import ttk
from typing import Tuple, Optional, Dict, Any

class DynamicUIManager:
    """
    Utility class for creating UI components that automatically size themselves
    based on their content. This prevents overflow issues and ensures all
    components are properly visible.
    """
    
    @staticmethod
    def create_dynamic_dialog(parent: tk.Tk, title: str, min_width: int = 400, 
                            min_height: int = 300, max_width: int = 1200, 
                            max_height: int = 800, padding: int = 20) -> tk.Toplevel:
        """
        Create a dialog that dynamically sizes itself based on content.
        
        Args:
            parent: Parent window
            title: Dialog title
            min_width: Minimum dialog width
            min_height: Minimum dialog height
            max_width: Maximum dialog width
            max_height: Maximum dialog height
            padding: Internal padding
            
        Returns:
            Configured Toplevel dialog
        """
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        
        # Safe grab - handle existing grabs
        try:
            dialog.grab_set()
        except tk.TclError as e:
            if "grab failed" in str(e).lower():
                # Release any existing grab and try again
                try:
                    parent.grab_release()
                except:
                    pass
                # Small delay to ensure grab is released
                dialog.after(10, lambda: dialog.grab_set())
            else:
                raise
        
        # Store sizing parameters as attributes
        setattr(dialog, '_min_width', min_width)
        setattr(dialog, '_min_height', min_height)
        setattr(dialog, '_max_width', max_width)
        setattr(dialog, '_max_height', max_height)
        setattr(dialog, '_padding', padding)
        setattr(dialog, '_content_added', False)
        
        # Make dialog resizable initially for content measurement
        dialog.resizable(True, True)
        
        return dialog
    
    @staticmethod
    def finalize_dialog_size(dialog: tk.Toplevel, center: bool = True, 
                           make_resizable: bool = False) -> None:
        """
        Calculate optimal size for dialog based on its content and apply it.
        Call this after all content has been added to the dialog.
        
        Args:
            dialog: The dialog to resize
            center: Whether to center the dialog on parent
            make_resizable: Whether to allow user resizing
        """
        # Force update to ensure all widgets are rendered
        dialog.update_idletasks()
        
        # Get the required size from the dialog's content
        padding = getattr(dialog, '_padding', 20)
        req_width = dialog.winfo_reqwidth() + (padding * 2)
        req_height = dialog.winfo_reqheight() + (padding * 2)
        
        # Apply size constraints
        min_width = getattr(dialog, '_min_width', 400)
        min_height = getattr(dialog, '_min_height', 300)
        max_width = getattr(dialog, '_max_width', 800)
        max_height = getattr(dialog, '_max_height', 600)
        
        final_width = max(min_width, min(req_width, max_width))
        final_height = max(min_height, min(req_height, max_height))
        
        # Set the final size
        dialog.geometry(f"{final_width}x{final_height}")
        
        # Center on parent if requested
        if center and dialog.master:
            DynamicUIManager._center_dialog(dialog, final_width, final_height)
        
        # Set resizable policy
        dialog.resizable(make_resizable, make_resizable)
        
        # Add scrolling if content exceeds max size
        if req_width > max_width or req_height > max_height:
            DynamicUIManager._add_scrolling_to_dialog(dialog)
    
    @staticmethod
    def _center_dialog(dialog: tk.Toplevel, width: int, height: int) -> None:
        """Center dialog on its parent window."""
        try:
            parent = dialog.master
            if parent:
                parent_x = parent.winfo_x()
                parent_y = parent.winfo_y()
                parent_width = parent.winfo_width()
                parent_height = parent.winfo_height()
                
                # Calculate center position
                x = parent_x + (parent_width // 2) - (width // 2)
                y = parent_y + (parent_height // 2) - (height // 2)
                
                # Ensure dialog stays on screen
                x = max(0, x)
                y = max(0, y)
                
                dialog.geometry(f"+{x}+{y}")
        except Exception as e:
            print(f"Warning: Could not center dialog: {e}")
            # Fallback to default positioning
            dialog.geometry(f"+50+50")
    
    @staticmethod
    def _add_scrolling_to_dialog(dialog: tk.Toplevel) -> None:
        """Add scrolling capability to dialog if content is too large."""
        # This would be implemented if needed, but with proper sizing
        # it shouldn't be necessary in most cases
        pass
    
    @staticmethod
    def create_dynamic_frame(parent: tk.Widget, **kwargs) -> tk.Frame:
        """Create a frame that expands with its content."""
        frame = tk.Frame(parent, **kwargs)
        
        # Configure weight so frame expands with content
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        return frame
    
    @staticmethod
    def create_button_bar(parent: tk.Widget, buttons: list, spacing: int = 10,
                         align: str = "right") -> tk.Frame:
        """
        Create a button bar that sizes itself based on button content.
        
        Args:
            parent: Parent widget
            buttons: List of button configurations (text, command, **kwargs)
            spacing: Space between buttons
            align: Button alignment ("left", "right", "center")
            
        Returns:
            Frame containing the buttons
        """
        button_frame = tk.Frame(parent, relief=tk.RAISED, bd=1, bg="lightgray")
        
        # Create buttons
        created_buttons = []
        for i, btn_config in enumerate(buttons):
            if isinstance(btn_config, dict):
                text = btn_config.pop('text', f'Button {i+1}')
                command = btn_config.pop('command', None)
                btn = tk.Button(button_frame, text=text, command=command, **btn_config)
            else:
                # Assume it's a simple (text, command) tuple
                text, command = btn_config[:2]
                btn = tk.Button(button_frame, text=text, command=command)
            
            created_buttons.append(btn)
        
        # Pack buttons based on alignment
        if align == "right":
            for btn in reversed(created_buttons):
                btn.pack(side=tk.RIGHT, padx=spacing, pady=8)
        elif align == "left":
            for btn in created_buttons:
                btn.pack(side=tk.LEFT, padx=spacing, pady=8)
        else:  # center
            # For center alignment, calculate positions
            for btn in created_buttons:
                btn.pack(side=tk.LEFT, padx=spacing//2, pady=8)
            button_frame.pack_configure(anchor=tk.CENTER)
        
        return button_frame
    
    @staticmethod
    def create_scrollable_content(parent: tk.Widget, content_height: Optional[int] = None) -> Tuple[tk.Canvas, tk.Frame]:
        """
        Create a scrollable content area that adapts to content size.
        
        Args:
            parent: Parent widget
            content_height: Maximum height before scrolling (None = auto)
            
        Returns:
            Tuple of (canvas, content_frame)
        """
        # Create canvas and scrollbar
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content_frame = tk.Frame(canvas)
        
        # Configure scrolling
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            # Auto-adjust canvas height if not specified
            if content_height is None:
                req_height = content_frame.winfo_reqheight()
                # Limit to reasonable size
                max_height = min(req_height + 20, 600)
                canvas.configure(height=max_height)
        
        content_frame.bind("<Configure>", configure_scroll_region)
        
        # Create window in canvas
        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return canvas, content_frame
    
    @staticmethod
    def auto_size_window(window: tk.Tk, min_width: int = 800, min_height: int = 600,
                        max_width: int = 1600, max_height: int = 1200) -> None:
        """
        Automatically size a main window based on its content.
        
        Args:
            window: The main window to size
            min_width: Minimum window width
            min_height: Minimum window height
            max_width: Maximum window width
            max_height: Maximum window height
        """
        window.update_idletasks()
        
        req_width = window.winfo_reqwidth()
        req_height = window.winfo_reqheight()
        
        final_width = max(min_width, min(req_width, max_width))
        final_height = max(min_height, min(req_height, max_height))
        
        window.geometry(f"{final_width}x{final_height}")
        
        # Center on screen
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        x = (screen_width // 2) - (final_width // 2)
        y = (screen_height // 2) - (final_height // 2)
        
        window.geometry(f"{final_width}x{final_height}+{x}+{y}")

class DynamicDialog:
    """
    Base class for creating dialogs with automatic sizing and proper layout.
    Inherit from this class to ensure consistent, properly-sized dialogs.
    """
    
    def __init__(self, parent: tk.Tk, title: str, **kwargs):
        self.parent = parent
        self.title = title
        self.result = None
        
        # Extract sizing parameters
        self.min_width = kwargs.get('min_width', 400)
        self.min_height = kwargs.get('min_height', 300)
        self.max_width = kwargs.get('max_width', 1000)
        self.max_height = kwargs.get('max_height', 700)
        
        # Create dialog
        self.dialog = DynamicUIManager.create_dynamic_dialog(
            parent, title, self.min_width, self.min_height,
            self.max_width, self.max_height
        )
        
        # Main content area
        self.main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
    def create_content(self):
        """Override this method to add dialog content."""
        pass
    
    def create_buttons(self, buttons: list) -> tk.Frame:
        """Create standard button bar."""
        return DynamicUIManager.create_button_bar(self.main_frame, buttons)
    
    def show(self):
        """Show the dialog and return result."""
        # Create content
        self.create_content()
        
        # Finalize sizing
        DynamicUIManager.finalize_dialog_size(self.dialog, center=True)
        
        # Wait for dialog
        self.dialog.wait_window()
        return self.result
    
    def close(self, result=None):
        """Close dialog with optional result."""
        self.result = result
        self.dialog.destroy()