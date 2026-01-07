""" © Daniel P Raven 2024 All Rights Reserved """
import tkinter as tk
from tkinter import ttk, messagebox
from .dynamic_ui_manager import DynamicDialog
from .data_validator import DataValidator


class CreateTeamDialog(DynamicDialog):
    def __init__(self, parent, existing_team_names):
        self.existing_team_names = existing_team_names
        self.result = None
        self.player_entries = []
        self.team_name_entry = None  # type: tk.Entry | None
        
        # Initialize with dynamic sizing - min 500x450, max 650x650
        super().__init__(parent, "Create Team Wizard", 
                        min_width=500, min_height=450, 
                        max_width=650, max_height=650)
        
    def create_content(self):
        """Create dialog content using dynamic sizing"""
        # Main title
        title_label = tk.Label(self.main_frame, text="Create Team Wizard", 
                              font=("Arial", 16, "bold"), fg="darkblue")
        title_label.pack(pady=(0, 15))
        
        # Section 1: Team Name
        team_frame = tk.LabelFrame(self.main_frame, text="Team Information", 
                                  font=("Arial", 12, "bold"), padx=15, pady=10)
        team_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(team_frame, text="Team Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.team_name_entry = tk.Entry(team_frame, font=("Arial", 10), width=40)
        self.team_name_entry.pack(fill="x", pady=(5, 0))
        
        # Add tooltip for team name
        self.create_tooltip(self.team_name_entry, 
                          "Enter the name of the team you want to create")
        
        # Section 2: Player Names
        players_frame = tk.LabelFrame(self.main_frame, text="Player Roster", 
                                     font=("Arial", 12, "bold"), padx=15, pady=10)
        players_frame.pack(fill="x", pady=(0, 15))
        
        for i in range(5):
            player_label = tk.Label(players_frame, text=f"Player {i+1}:", 
                                   font=("Arial", 10, "bold"))
            player_label.pack(anchor="w", pady=(8 if i > 0 else 0, 0))
            
            player_entry = tk.Entry(players_frame, font=("Arial", 10), width=40)
            player_entry.pack(fill="x", pady=(3, 0))
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
                'text': 'Create Team',
                'command': self.create_team,
                'bg': 'lightgreen',
                'fg': 'black',
                'font': ('Arial', 10, 'bold'),
                'width': 12,
                'height': 1,
                'relief': tk.RAISED,
                'bd': 2
            },
            {
                'text': 'Cancel',
                'command': self.cancel,
                'bg': 'lightcoral',
                'fg': 'black',
                'font': ('Arial', 10),
                'width': 12,
                'height': 1,
                'relief': tk.RAISED,
                'bd': 2
            }
        ]
        
        button_frame = self.create_buttons(buttons)
        button_frame.pack(fill=tk.X, pady=(15, 5))
        
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
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            label = tk.Label(tooltip, text=text, background="lightyellow", 
                           relief="solid", borderwidth=1, font=("Arial", 9),
                           padx=5, pady=3)
            label.pack()
            
            # Store tooltip reference
            widget.tooltip = tooltip
            
            # Auto-hide tooltip after 3 seconds
            tooltip.after(3000, lambda: tooltip.destroy() if tooltip.winfo_exists() else None)
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip') and widget.tooltip.winfo_exists():
                widget.tooltip.destroy()
                
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