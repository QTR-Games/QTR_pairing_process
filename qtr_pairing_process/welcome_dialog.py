""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

class WelcomeDialog:
    """Welcome dialog for first-time users with preference saving"""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.result = None
        self.show_again = True
        self.dialog = None
        self.ui_theme = {
            "font_title": ("Arial", 16, "bold"),
            "font_body": ("Arial", 10),
            "font_body_bold": ("Arial", 10, "bold"),
            "font_small": ("Arial", 8),
            "pad_sm": 8,
            "pad_md": 12,
            "pad_lg": 20,
            "bg_surface": "#f7fbff",
            "bg_surface_alt": "#eef4f8",
            "bg_text": "#f3f7fa",
            "bg_primary": "#d8efe5",
            "bg_secondary": "#e8eef5",
            "fg_primary": "#103d2b",
            "fg_body": "#2f3b4a",
            "fg_subtle": "#5b6675",
        }

    def _configure_styles(self):
        """Configure local ttk styles for welcome/preferences dialogs."""
        theme = self.ui_theme
        style = ttk.Style(self.dialog)
        style.configure("Welcome.Root.TFrame", background=theme["bg_surface"])
        style.configure(
            "Welcome.Title.TLabel",
            background=theme["bg_surface"],
            foreground=theme["fg_primary"],
            font=theme["font_title"],
        )
        style.configure(
            "Welcome.Check.TCheckbutton",
            background=theme["bg_surface"],
            foreground=theme["fg_body"],
            font=theme["font_body"],
        )
        style.configure(
            "Welcome.Primary.TButton",
            font=theme["font_body_bold"],
        )
        style.configure(
            "Welcome.Secondary.TButton",
            font=theme["font_body"],
        )
    
    def show_welcome_message(self) -> bool:
        """
        Show welcome message dialog
        Returns: True if user wants to see message again, False otherwise
        """
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Welcome to QTR's Klik Klaker!")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=self.ui_theme["bg_surface"])
        self._configure_styles()
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=str(self.ui_theme["pad_lg"]), style="Welcome.Root.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, 
            text="🎯 Welcome to QTR's Klik Klaker!", 
            style="Welcome.Title.TLabel")
        title_label.pack(pady=(0, self.ui_theme["pad_md"]))
        
        # Welcome message
        welcome_text = """
    What is new in 2.0

    QTR's Klik Klaker now uses a cleaner, more consistent workspace and keeps your setup between sessions.

    Highlights

    1) Database Memory
    Your last selected database is loaded automatically on startup.

    2) Faster Data Management
    Import, export, team actions, and guides are grouped in one command center.

    3) Safer Defaults
    If a saved database path is missing, you will be prompted to select a valid database.

    4) Portable Configuration
    Preferences are stored in KLIK_KLAK_KONFIG.json next to the application.

    Tip
    Use Data Management any time to change database, adjust settings, or open guides.

    Have a great session.
        """
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame, style="Welcome.Root.TFrame")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, self.ui_theme["pad_md"]))
        
        text_widget = tk.Text(text_frame, 
            wrap=tk.WORD, 
            font=self.ui_theme["font_body"],
            bg=self.ui_theme["bg_text"],
            fg=self.ui_theme["fg_body"],
            relief=tk.FLAT,
            padx=10,
            pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert and configure text
        text_widget.insert(tk.END, welcome_text)
        text_widget.config(state=tk.DISABLED)
        
        # Checkbox frame
        checkbox_frame = ttk.Frame(main_frame, style="Welcome.Root.TFrame")
        checkbox_frame.pack(fill=tk.X, pady=(0, self.ui_theme["pad_md"]))
        
        self.show_again_var = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(checkbox_frame,
            text="Don't show this message at startup",
            variable=self.show_again_var,
            style="Welcome.Check.TCheckbutton")
        checkbox.pack(anchor=tk.W)
        
        # Button frame
        button_frame = ttk.Frame(main_frame, style="Welcome.Root.TFrame")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, 
            text="Continue", 
            command=self._on_continue,
            style="Welcome.Primary.TButton").pack(side=tk.RIGHT, padx=(self.ui_theme["pad_sm"], 0))
        
        ttk.Button(button_frame, 
            text="Open Data Management", 
            command=self._on_open_settings,
            style="Welcome.Secondary.TButton").pack(side=tk.RIGHT)
        
        # Wait for dialog to close
        self.dialog.wait_window()
        
        # Return whether to show again (inverted because checkbox says "don't show")
        return not self.show_again_var.get()
    
    def _on_continue(self):
        """Handle continue button click"""
        self.show_again = not self.show_again_var.get()
        if self.dialog:
            self.dialog.destroy()
    
    def _on_open_settings(self):
        """Handle open settings button click"""
        self.show_again = not self.show_again_var.get()
        self.result = "open_settings"
        if self.dialog:
            self.dialog.destroy()


class DatabasePreferencesDialog:
    """Dialog for managing database and UI preferences"""
    
    def __init__(self, parent: tk.Tk, preferences_manager):
        self.parent = parent
        self.preferences_manager = preferences_manager
        self.dialog = None
        self.ui_theme = {
            "font_body": ("Arial", 10),
            "font_body_bold": ("Arial", 10, "bold"),
            "font_small": ("Arial", 8),
            "pad_sm": 8,
            "pad_md": 10,
            "bg_surface": "#f7fbff",
            "fg_body": "#2f3b4a",
            "fg_subtle": "#5b6675",
        }

    def _configure_styles(self):
        theme = self.ui_theme
        style = ttk.Style(self.dialog)
        style.configure("Prefs.Root.TFrame", background=theme["bg_surface"])
        style.configure(
            "Prefs.TLabel",
            background=theme["bg_surface"],
            foreground=theme["fg_body"],
            font=theme["font_body"],
        )
        style.configure(
            "Prefs.Subtle.TLabel",
            background=theme["bg_surface"],
            foreground=theme["fg_subtle"],
            font=theme["font_small"],
        )
        style.configure("Prefs.TButton", font=theme["font_body"])
        style.configure("PrefsBold.TButton", font=theme["font_body_bold"])
        style.configure(
            "Prefs.TLabelframe",
            background=theme["bg_surface"],
            foreground=theme["fg_body"],
        )
        style.configure(
            "Prefs.TLabelframe.Label",
            background=theme["bg_surface"],
            foreground=theme["fg_body"],
            font=theme["font_body_bold"],
        )
        
    def show_preferences_dialog(self):
        """Show preferences management dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Database & UI Preferences")
        self.dialog.geometry("600x450")
        self.dialog.resizable(True, True)
        self.dialog.configure(bg=self.ui_theme["bg_surface"])
        self._configure_styles()
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Main frame with notebook
        main_frame = ttk.Frame(self.dialog, padding=str(self.ui_theme["pad_md"]), style="Prefs.Root.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Database tab
        db_frame = ttk.Frame(notebook, padding="10")
        notebook.add(db_frame, text="Database")
        
        self._create_database_tab(db_frame)
        
        # UI Preferences tab
        ui_frame = ttk.Frame(notebook, padding="10")
        notebook.add(ui_frame, text="UI Preferences")
        
        self._create_ui_preferences_tab(ui_frame)
        
        # Advanced tab
        advanced_frame = ttk.Frame(notebook, padding="10")
        notebook.add(advanced_frame, text="Advanced")
        
        self._create_advanced_tab(advanced_frame)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy, style="Prefs.TButton").pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Backup Config", command=self._backup_config, style="PrefsBold.TButton").pack(side=tk.RIGHT, padx=(0, self.ui_theme["pad_md"]))
    
    def _create_database_tab(self, parent):
        """Create database preferences tab"""
        # Current database info
        db_group = ttk.LabelFrame(parent, text="Current Database", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        db_group.pack(fill=tk.X, pady=(0, 10))
        
        path, name = self.preferences_manager.get_last_database()
        
        ttk.Label(db_group, text="Database Name:", style="Prefs.TLabel").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(db_group, text=name or "None selected", 
             font=self.ui_theme["font_body_bold"], style="Prefs.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(db_group, text="Database Path:", style="Prefs.TLabel").grid(row=1, column=0, sticky=tk.W, pady=2)
        path_label = ttk.Label(db_group, text=path or "None selected", 
                      style="Prefs.Subtle.TLabel")
        path_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Actions
        action_group = ttk.LabelFrame(parent, text="Actions", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        action_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(action_group, text="Clear Database Preference", 
              command=self._clear_database, style="Prefs.TButton").pack(pady=2, fill=tk.X)
        
        ttk.Label(action_group, text="This will prompt for database selection on next startup", 
             style="Prefs.Subtle.TLabel").pack(pady=(0, 5))
    
    def _create_ui_preferences_tab(self, parent):
        """Create UI preferences tab"""
        # Welcome message
        welcome_group = ttk.LabelFrame(parent, text="Startup Behavior", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        welcome_group.pack(fill=tk.X, pady=(0, 10))
        
        prefs = self.preferences_manager.get_ui_preferences()
        
        self.show_welcome_var = tk.BooleanVar(value=prefs.get("show_welcome_message", True))
        ttk.Checkbutton(welcome_group, 
                       text="Show welcome message at startup",
                       variable=self.show_welcome_var,
                       command=self._update_welcome_preference).pack(anchor=tk.W)
        
        # Rating system (if needed in future)
        rating_group = ttk.LabelFrame(parent, text="Default Settings", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        rating_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(rating_group, text="Rating System:", style="Prefs.TLabel").pack(anchor=tk.W, pady=2)
        rating_var = tk.StringVar(value=prefs.get("rating_system", "1-5"))
        ttk.Combobox(rating_group, textvariable=rating_var, 
                    values=["1-3", "1-5", "1-10"], state="readonly").pack(fill=tk.X, pady=2)
    
    def _create_advanced_tab(self, parent):
        """Create advanced preferences tab"""
        # Config file info
        config_group = ttk.LabelFrame(parent, text="Configuration File", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        config_group.pack(fill=tk.X, pady=(0, 10))
        
        config_path = self.preferences_manager.get_config_file_path()
        
        ttk.Label(config_group, text="Config File Location:", style="Prefs.TLabel").pack(anchor=tk.W, pady=2)
        
        path_frame = ttk.Frame(config_group)
        path_frame.pack(fill=tk.X, pady=2)
        
        path_entry = ttk.Entry(path_frame, font=self.ui_theme["font_small"])
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        path_entry.insert(0, config_path)
        path_entry.config(state="readonly")
        
        ttk.Button(path_frame, text="Open Folder", 
              command=lambda: self._open_config_folder(config_path), style="Prefs.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        
        # Logging
        log_group = ttk.LabelFrame(parent, text="Logging", padding=str(self.ui_theme["pad_md"]), style="Prefs.TLabelframe")
        log_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(log_group, text="Verbose logging is enabled by default", style="Prefs.TLabel").pack(anchor=tk.W, pady=2)
        ttk.Label(log_group, text="Logs are stored in: qtr_pairing_process.log", 
             style="Prefs.Subtle.TLabel").pack(anchor=tk.W, pady=2)
    
    def _clear_database(self):
        """Clear database preference"""
        result = messagebox.askyesno("Clear Database Preference", 
            "This will clear the saved database preference.\n"
            "You will be prompted to select a database on next startup.\n\n"
            "Continue?")
        
        if result:
            if self.preferences_manager.clear_database_preference():
                messagebox.showinfo("Success", "Database preference cleared successfully.")
                if self.dialog:
                    self.dialog.destroy()
    
    def _update_welcome_preference(self):
        """Update welcome message preference"""
        self.preferences_manager.set_welcome_message_preference(self.show_welcome_var.get())
    
    def _backup_config(self):
        """Create config backup"""
        backup_path = self.preferences_manager.backup_config()
        if backup_path:
            messagebox.showinfo("Backup Created", 
                f"Configuration backup created:\n{backup_path}")
        else:
            messagebox.showwarning("Backup Failed", 
                "Could not create configuration backup.")
    
    def _open_config_folder(self, config_path):
        """Open config file folder in file explorer"""
        import subprocess
        import os
        
        folder_path = os.path.dirname(config_path)
        
        try:
            # Windows
            if os.name == 'nt':
                subprocess.Popen(['explorer', folder_path])
            # macOS
            elif os.name == 'posix' and os.uname().sysname == 'Darwin':
                subprocess.Popen(['open', folder_path])
            # Linux
            else:
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")