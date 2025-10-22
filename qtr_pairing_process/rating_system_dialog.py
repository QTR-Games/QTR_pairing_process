""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import tkinter as tk
from tkinter import ttk, messagebox
from .constants import RATING_SYSTEMS
from .dynamic_ui_manager import DynamicDialog, DynamicUIManager

class RatingSystemDialog(DynamicDialog):
    """Dialog for selecting rating system preference"""
    
    def __init__(self, parent, current_system, db_manager):
        self.current_system = current_system
        self.db_manager = db_manager
        self.selected_system = None
        
        # These will be initialized in create_content()
        self.system_var = None  # type: tk.StringVar | None
        self.warning_frame = None  # type: tk.Frame | None
        
        # Initialize with dynamic sizing - min 500x400, max 800x700
        super().__init__(parent, "Rating System Configuration", 
                        min_width=500, min_height=400, 
                        max_width=800, max_height=700)
    
    def create_content(self):
        """Create dialog content using dynamic sizing"""
        # Title
        title_label = tk.Label(self.main_frame, text="Select Rating System", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Description
        desc_text = ("Choose your preferred rating system. This affects how you enter matchup ratings "
                    "and the color coding throughout the application.")
        desc_label = tk.Label(self.main_frame, text=desc_text, wraplength=450, justify=tk.LEFT)
        desc_label.pack(pady=(0, 15))
        
        # Rating system selection frame
        selection_frame = tk.LabelFrame(self.main_frame, text="Available Rating Systems", 
                                       font=("Arial", 12, "bold"), padx=15, pady=10)
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.system_var = tk.StringVar(value=self.current_system)
        
        # Create radio buttons for each system
        for system_key, system_info in RATING_SYSTEMS.items():
            system_frame = tk.Frame(selection_frame)
            system_frame.pack(fill=tk.X, pady=8)
            
            # Radio button
            radio = tk.Radiobutton(system_frame, text=system_info['name'], 
                                 variable=self.system_var, value=system_key,
                                 font=("Arial", 11, "bold"),
                                 command=self._on_system_change)
            radio.pack(anchor=tk.W)
            
            # Description
            desc_label = tk.Label(system_frame, text=system_info['description'], 
                                font=("Arial", 10), fg="gray")
            desc_label.pack(anchor=tk.W, padx=(25, 0))
            
            # Color preview
            color_frame = tk.Frame(system_frame)
            color_frame.pack(anchor=tk.W, padx=(25, 0), pady=(3, 0))
            
            tk.Label(color_frame, text="Colors:", font=("Arial", 9)).pack(side=tk.LEFT)
            
            for rating, color in system_info['color_map'].items():
                color_box = tk.Label(color_frame, text=rating, bg=color, width=3, 
                                   relief=tk.RAISED, borderwidth=1, font=("Arial", 8, "bold"))
                color_box.pack(side=tk.LEFT, padx=(2, 0))
        
        # Warning frame (initially hidden)
        self.warning_frame = tk.Frame(self.main_frame)
        
        warning_icon = tk.Label(self.warning_frame, text="⚠️", font=("Arial", 14))
        warning_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        warning_text = tk.Label(self.warning_frame, 
                               text="Warning: Existing rating data detected! Changing the rating system "
                                    "may cause data inconsistencies. This should only be done with a blank database.",
                               wraplength=400, justify=tk.LEFT, fg="red", font=("Arial", 10, "bold"))
        warning_text.pack(side=tk.LEFT)
        
        # Initially hide warning
        self.warning_frame.pack_forget()
        
        # Create buttons using the dynamic button manager
        buttons = [
            {
                'text': 'Apply Changes',
                'command': self._on_apply,
                'bg': 'lightgreen',
                'fg': 'white',
                'font': ('Arial', 11, 'bold'),
                'width': 15,
                'height': 2,
                'relief': tk.RAISED,
                'bd': 2
            },
            {
                'text': 'Cancel',
                'command': self._on_cancel,
                'bg': 'lightcoral',
                'fg': 'white',
                'font': ('Arial', 11, 'bold'),
                'width': 12,
                'height': 2,
                'relief': tk.RAISED,
                'bd': 2
            }
        ]
        
        button_frame = self.create_buttons(buttons)
        button_frame.pack(fill=tk.X, pady=(15, 5))
        
        # Check initial state
        self._check_database_state()
    
    def _on_system_change(self):
        """Handle rating system selection change"""
        self._check_database_state()
    
    def _check_database_state(self):
        """Check if database has existing data and show warning if needed"""
        if self.system_var is None or self.warning_frame is None:
            return
            
        if self.system_var.get() != self.current_system:
            try:
                ratings_count = self.db_manager.get_ratings_count()
                if ratings_count > 0:
                    self.warning_frame.pack(fill=tk.X, pady=(0, 10))
                else:
                    self.warning_frame.pack_forget()
            except Exception as e:
                print(f"Error checking database state: {e}")
                self.warning_frame.pack_forget()
        else:
            self.warning_frame.pack_forget()
    
    def _on_apply(self):
        """Apply the selected rating system"""
        if self.system_var is None:
            return
            
        new_system = self.system_var.get()
        
        if new_system == self.current_system:
            self.dialog.destroy()
            return
        
        # Check for existing data and confirm
        try:
            ratings_count = self.db_manager.get_ratings_count()
            if ratings_count > 0:
                confirm = messagebox.askyesno(
                    "Confirm Rating System Change",
                    f"Your database contains {ratings_count} rating entries. "
                    f"Changing from {RATING_SYSTEMS[self.current_system]['name']} to "
                    f"{RATING_SYSTEMS[new_system]['name']} may cause data inconsistencies.\n\n"
                    f"Existing ratings may be interpreted incorrectly with the new scale.\n\n"
                    f"Are you sure you want to proceed?",
                    icon="warning"
                )
                if not confirm:
                    return
        except Exception as e:
            print(f"Error checking database: {e}")
        
        self.selected_system = new_system
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancel dialog without changes"""
        self.selected_system = None
        self.dialog.destroy()