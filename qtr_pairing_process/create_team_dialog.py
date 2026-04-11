""" © Daniel P Raven 2024 All Rights Reserved """
import tkinter as tk
from tkinter import ttk, messagebox
from .dynamic_ui_manager import DynamicDialog
from .data_validator import DataValidator


class CreateTeamDialog(DynamicDialog):
    def __init__(
        self,
        parent,
        existing_team_names,
        dialog_title="Create Team Wizard",
        confirm_button_text="Create Team",
        initial_team_name=None,
        initial_player_names=None,
        team_exists_behavior="prompt_update",
    ):
        self.existing_team_names = existing_team_names
        self.dialog_title = dialog_title
        self.confirm_button_text = confirm_button_text
        self.initial_team_name = initial_team_name or ""
        self.initial_player_names = list(initial_player_names or [])
        self.team_exists_behavior = team_exists_behavior
        self.result = None
        self.player_entries = []
        self.team_name_entry = None  # type: tk.Entry | None
        self.ui_theme = {
            "font_title": ("Arial", 16, "bold"),
            "font_group_title": ("Arial", 12, "bold"),
            "font_body": ("Arial", 10),
            "font_body_bold": ("Arial", 10, "bold"),
            "font_small": ("Arial", 9),
            "pad_sm": 6,
            "pad_md": 10,
            "pad_lg": 15,
            "bg_surface": "#f7fbff",
            "bg_surface_alt": "#eef4f8",
            "bg_primary": "#d8efe5",
            "bg_secondary": "#e8eef5",
            "bg_tooltip": "#f8f4d8",
            "fg_primary": "#103d2b",
            "fg_body": "#2f3b4a",
            "fg_subtle": "#5b6675",
        }
        
        # Initialize with dynamic sizing - min 500x450, max 650x650
        super().__init__(parent, self.dialog_title, 
                        min_width=500, min_height=450, 
                        max_width=650, max_height=650)

    def _apply_theme_to_dialog(self):
        theme = self.ui_theme
        self.dialog.configure(bg=theme["bg_surface"])
        self.main_frame.configure(bg=theme["bg_surface"])
        
    def create_content(self):
        """Create dialog content using dynamic sizing"""
        self._apply_theme_to_dialog()
        theme = self.ui_theme

        # Main title
        title_label = tk.Label(
            self.main_frame,
            text=self.dialog_title,
            font=theme["font_title"],
            fg=theme["fg_primary"],
            bg=theme["bg_surface"],
        )
        title_label.pack(pady=(0, theme["pad_lg"]))
        
        # Section 1: Team Name
        team_frame = tk.LabelFrame(
            self.main_frame,
            text="Team Information",
            font=theme["font_group_title"],
            padx=theme["pad_lg"],
            pady=theme["pad_md"],
            bg=theme["bg_surface_alt"],
            fg=theme["fg_primary"],
        )
        team_frame.pack(fill="x", pady=(0, theme["pad_lg"]))
        
        tk.Label(
            team_frame,
            text="Team Name:",
            font=theme["font_body_bold"],
            bg=theme["bg_surface_alt"],
            fg=theme["fg_body"],
        ).pack(anchor="w")
        self.team_name_entry = tk.Entry(team_frame, font=theme["font_body"], width=40)
        self.team_name_entry.pack(fill="x", pady=(theme["pad_sm"], 0))
        if self.initial_team_name:
            self.team_name_entry.insert(0, self.initial_team_name)
        
        # Add tooltip for team name
        self.create_tooltip(self.team_name_entry, 
                          "Enter the name of the team you want to create")
        
        # Section 2: Player Names
        players_frame = tk.LabelFrame(
            self.main_frame,
            text="Player Roster",
            font=theme["font_group_title"],
            padx=theme["pad_lg"],
            pady=theme["pad_md"],
            bg=theme["bg_surface_alt"],
            fg=theme["fg_primary"],
        )
        players_frame.pack(fill="x", pady=(0, theme["pad_lg"]))
        
        for i in range(5):
            player_label = tk.Label(
                players_frame,
                text=f"Player {i+1}:",
                font=theme["font_body_bold"],
                bg=theme["bg_surface_alt"],
                fg=theme["fg_body"],
            )
            player_label.pack(anchor="w", pady=(theme["pad_md"] if i > 0 else 0, 0))
            
            player_entry = tk.Entry(players_frame, font=theme["font_body"], width=40)
            player_entry.pack(fill="x", pady=(theme["pad_sm"] - 2, 0))
            if i < len(self.initial_player_names):
                player_entry.insert(0, str(self.initial_player_names[i]))
            self.player_entries.append(player_entry)
            
            # Add tooltips for player entries
            if i == 0:
                tooltip_text = "Enter the name of the first player / team captain"
            else:
                tooltip_text = f"Enter the name of the {self.ordinal(i+1)} player on the team"
            
            self.create_tooltip(player_entry, tooltip_text)
        
        # Create buttons using the dynamic button manager
        buttons = [
            {
                'text': self.confirm_button_text,
                'command': self.create_team,
                'bg': theme['bg_primary'],
                'fg': theme['fg_primary'],
                'font': theme['font_body_bold'],
                'width': 12,
                'height': 1,
                'relief': tk.RAISED,
                'bd': 2
            },
            {
                'text': 'Cancel',
                'command': self.cancel,
                'bg': theme['bg_secondary'],
                'fg': theme['fg_body'],
                'font': theme['font_body'],
                'width': 12,
                'height': 1,
                'relief': tk.RAISED,
                'bd': 2
            }
        ]
        
        button_frame = self.create_buttons(buttons)
        button_frame.configure(bg=theme["bg_surface_alt"], relief=tk.GROOVE, bd=1)
        button_frame.pack(fill=tk.X, pady=(theme["pad_lg"], theme["pad_sm"]))
        
        # Focus on team name entry
        self.team_name_entry.focus_set()
        
        # Bind Enter key to create team
        self.dialog.bind('<Return>', lambda event: self.create_team())
        self.dialog.bind('<Escape>', lambda event: self.cancel())
        
    def ordinal(self, n):
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return f"{n}{suffix}"
        
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        theme = self.ui_theme

        def show_tooltip(event):
            tooltip = tk.Toplevel(self.dialog)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            label = tk.Label(
                tooltip,
                text=text,
                background=theme["bg_tooltip"],
                foreground=theme["fg_body"],
                relief="solid",
                borderwidth=1,
                font=theme["font_small"],
                padx=6,
                pady=4,
            )
            label.pack()
            
            # Store tooltip reference
            widget.tooltip = tooltip
            
            # Auto-hide tooltip after 3 seconds
            tooltip.after(3000, lambda: tooltip.destroy() if tooltip.winfo_exists() else None)
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                try:
                    if widget.tooltip.winfo_exists():
                        widget.tooltip.destroy()
                except tk.TclError:
                    pass
                
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        
    def validate_input(self):
        """Validate all input fields using secure data validation"""
        if self.team_name_entry is None:
            return None
            
        try:
            # Get and validate team name
            team_name_raw = self.team_name_entry.get().strip()
            team_name = DataValidator.validate_team_name(team_name_raw)
            
            # Get and validate player names
            player_names_raw = []
            for i, entry in enumerate(self.player_entries):
                player_name_raw = entry.get().strip()
                if not player_name_raw:
                    messagebox.showerror("Validation Error", 
                                       f"Player {i+1} name cannot be empty.")
                    entry.focus_set()
                    return None
                player_names_raw.append(player_name_raw)
            
            # Validate all player names using batch validation
            player_names = DataValidator.validate_batch_names(player_names_raw, DataValidator.validate_player_name)
            
            return {"team_name": team_name, "player_names": player_names}
            
        except ValueError as e:
            error_msg = str(e)
            
            # Try to identify which field caused the error and focus it
            if "team name" in error_msg.lower():
                messagebox.showerror("Validation Error", f"Team name error: {error_msg}")
                if self.team_name_entry is not None:
                    self.team_name_entry.focus_set()
            else:
                messagebox.showerror("Validation Error", f"Input validation error: {error_msg}")
                
            return None
        
    def create_team(self):
        """Validate input and create team"""
        data = self.validate_input()
        if not data:
            return
            
        team_name = data["team_name"]
        player_names = data["player_names"]
        
        # Check if team already exists
        if team_name in self.existing_team_names:
            if self.team_exists_behavior == "error":
                messagebox.showerror(
                    "Team Exists",
                    f"Team '{team_name}' already exists. Choose a unique team name.",
                )
                return

            response = messagebox.askyesno(
                "Team Exists", 
                f"Team '{team_name}' already exists.\n\n"
                f"Would you like to update the player names for this existing team?\n\n"
                f"Click 'Yes' to update players, or 'No' to cancel."
            )
            if not response:
                return
                
        self.result = data
        self.close(data)
        
    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.close(None)