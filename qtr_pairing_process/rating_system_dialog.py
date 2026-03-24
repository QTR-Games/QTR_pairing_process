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
        self.ui_theme = {
            "font_title": ("Arial", 16, "bold"),
            "font_group_title": ("Arial", 12, "bold"),
            "font_body": ("Arial", 10),
            "font_body_bold": ("Arial", 11, "bold"),
            "font_small": ("Arial", 9),
            "font_small_bold": ("Arial", 8, "bold"),
            "pad_sm": 6,
            "pad_md": 10,
            "pad_lg": 15,
            "bg_surface": "#f7fbff",
            "bg_surface_alt": "#eef4f8",
            "bg_primary": "#d8efe5",
            "bg_danger": "#f7d9db",
            "fg_primary": "#103d2b",
            "fg_body": "#2f3b4a",
            "fg_subtle": "#5b6675",
            "fg_warning": "#8b1a1a",
            "wrap_main": 450,
            "wrap_warning": 400,
        }
        
        # These will be initialized in create_content()
        self.system_var = None  # type: tk.StringVar | None
        self.warning_frame = None  # type: tk.Frame | None
        
        # Initialize with dynamic sizing - min 500x400, max 800x700
        super().__init__(parent, "Rating System Configuration", 
                        min_width=500, min_height=400, 
                        max_width=800, max_height=700)

    def _apply_theme_to_dialog(self):
        """Apply consistent dialog-level theme values."""
        theme = self.ui_theme
        self.dialog.configure(bg=theme["bg_surface"])
        self.main_frame.configure(bg=theme["bg_surface"])
    
    def create_content(self):
        """Create dialog content using dynamic sizing"""
        self._apply_theme_to_dialog()
        theme = self.ui_theme

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="Select Rating System",
            font=theme["font_title"],
            bg=theme["bg_surface"],
            fg=theme["fg_primary"],
        )
        title_label.pack(pady=(0, theme["pad_lg"]))
        
        # Description
        desc_text = ("Choose your preferred rating system. This affects how you enter matchup ratings "
                    "and the color coding throughout the application.")
        desc_label = tk.Label(
            self.main_frame,
            text=desc_text,
            wraplength=theme["wrap_main"],
            justify=tk.LEFT,
            bg=theme["bg_surface"],
            fg=theme["fg_body"],
            font=theme["font_body"],
        )
        desc_label.pack(pady=(0, theme["pad_lg"]))
        
        # Rating system selection frame
        selection_frame = tk.LabelFrame(
            self.main_frame,
            text="Available Rating Systems",
            font=theme["font_group_title"],
            padx=theme["pad_lg"],
            pady=theme["pad_md"],
            bg=theme["bg_surface_alt"],
            fg=theme["fg_primary"],
        )
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, theme["pad_lg"]))
        
        self.system_var = tk.StringVar(value=self.current_system)
        
        # Create radio buttons for each system
        for system_key, system_info in RATING_SYSTEMS.items():
            system_frame = tk.Frame(selection_frame, bg=theme["bg_surface_alt"])
            system_frame.pack(fill=tk.X, pady=theme["pad_sm"])
            
            # Radio button
            radio = tk.Radiobutton(system_frame, text=system_info['name'], 
                                 variable=self.system_var, value=system_key,
                                 font=theme["font_body_bold"],
                                 command=self._on_system_change,
                                 bg=theme["bg_surface_alt"],
                                 fg=theme["fg_primary"],
                                 activebackground=theme["bg_surface_alt"],
                                 activeforeground=theme["fg_primary"],
                                 selectcolor=theme["bg_surface"],
                                 anchor=tk.W,
                                 relief=tk.FLAT)
            radio.pack(anchor=tk.W)
            
            # Description
            desc_label = tk.Label(system_frame, text=system_info['description'], 
                                font=theme["font_body"], fg=theme["fg_subtle"], bg=theme["bg_surface_alt"])
            desc_label.pack(anchor=tk.W, padx=(25, 0))
            
            # Color preview
            color_frame = tk.Frame(system_frame, bg=theme["bg_surface_alt"])
            color_frame.pack(anchor=tk.W, padx=(25, 0), pady=(3, 0))
            
            tk.Label(
                color_frame,
                text="Colors:",
                font=theme["font_small"],
                bg=theme["bg_surface_alt"],
                fg=theme["fg_body"],
            ).pack(side=tk.LEFT)
            
            for rating, color in system_info['color_map'].items():
                color_box = tk.Label(color_frame, text=rating, bg=color, width=3, 
                                   relief=tk.RAISED, borderwidth=1, font=theme["font_small_bold"])
                color_box.pack(side=tk.LEFT, padx=(2, 0))
        
        # Warning frame (initially hidden)
        self.warning_frame = tk.Frame(self.main_frame, bg=theme["bg_danger"], relief=tk.SOLID, borderwidth=1)
        
        warning_icon = tk.Label(
            self.warning_frame,
            text="⚠",
            font=("Arial", 14, "bold"),
            bg=theme["bg_danger"],
            fg=theme["fg_warning"],
        )
        warning_icon.pack(side=tk.LEFT, padx=(theme["pad_sm"], theme["pad_sm"]), pady=theme["pad_sm"])
        
        warning_text = tk.Label(self.warning_frame, 
                               text="Warning: Existing rating data detected! Changing the rating system "
                                    "may cause data inconsistencies. This should only be done with a blank database.",
                               wraplength=theme["wrap_warning"], justify=tk.LEFT, fg=theme["fg_warning"],
                               font=theme["font_body_bold"], bg=theme["bg_danger"])
        warning_text.pack(side=tk.LEFT, padx=(0, theme["pad_sm"]), pady=theme["pad_sm"])
        
        # Initially hide warning
        self.warning_frame.pack_forget()
        
        # Create buttons using the dynamic button manager
        buttons = [
            {
                'text': 'Apply Changes',
                'command': self._on_apply,
                'bg': theme['bg_primary'],
                'fg': theme['fg_primary'],
                'font': theme['font_body_bold'],
                'width': 15,
                'height': 2,
                'relief': tk.RAISED,
                'bd': 2
            },
            {
                'text': 'Cancel',
                'command': self._on_cancel,
                'bg': theme['bg_surface_alt'],
                'fg': theme['fg_body'],
                'font': theme['font_body_bold'],
                'width': 12,
                'height': 2,
                'relief': tk.RAISED,
                'bd': 2
            }
        ]
        
        button_frame = self.create_buttons(buttons)
        button_frame.configure(bg=theme["bg_surface_alt"], bd=1, relief=tk.GROOVE)
        button_frame.pack(fill=tk.X, pady=(theme["pad_lg"], theme["pad_sm"]))
        
        # Check initial state
        self._check_database_state()
    
    def _on_system_change(self):
        """Handle rating system selection change"""
        self._check_database_state()

    def _refresh_dialog_size(self):
        """Recalculate dialog size after dynamic content changes."""
        self.dialog.update_idletasks()
        req_width = self.dialog.winfo_reqwidth() + 20
        req_height = self.dialog.winfo_reqheight() + 20
        final_width = max(self.min_width, min(req_width, self.max_width))
        final_height = max(self.min_height, min(req_height, self.max_height))
        self.dialog.geometry(f"{final_width}x{final_height}")
    
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

        self._refresh_dialog_size()
    
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
        self.result = new_system
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancel dialog without changes"""
        self.selected_system = None
        self.result = None
        self.dialog.destroy()