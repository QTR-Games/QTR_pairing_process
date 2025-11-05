""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
from multiprocessing import Value
import os
import csv
from typing import List, Optional, Dict, Any

# installed libraries
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from urllib import error
# repo libraries
# from qtr_pairing_process import ui_db_funcs
from qtr_pairing_process.db_management import db_manager
from qtr_pairing_process.ui_db_funcs import UIDBFuncs
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP, RATING_SYSTEMS, DEFAULT_RATING_SYSTEM
from qtr_pairing_process.settings_manager import SettingsManager
from qtr_pairing_process.rating_system_dialog import RatingSystemDialog
from qtr_pairing_process.data_validator import DataValidator
from qtr_pairing_process.lazy_tree_view import LazyTreeView
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.matchup_tree_sync import MatchupTreeSynchronizer
from qtr_pairing_process.db_load_ui import DbLoadUi
from qtr_pairing_process.xlsx_load_ui import XlsxLoadUi
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.delete_team_dialog import DeleteTeamDialog
from qtr_pairing_process.create_team_dialog import CreateTeamDialog
from qtr_pairing_process.excel_management.excel_importer import ExcelImporter
from qtr_pairing_process.excel_management.simple_excel_importer import SimpleExcelImporter
from qtr_pairing_process.database_preferences import DatabasePreferences
from qtr_pairing_process.welcome_dialog import WelcomeDialog, DatabasePreferencesDialog
from qtr_pairing_process.matchup_data_cache import MatchupDataCache


class UiManager:
    def __init__(
        self,
        color_map: Dict[str, str],
        scenario_map: Dict[int, str],
        directory: str,
        scenario_ranges: Dict[int, tuple],
        scenario_to_csv_map: Dict[int, str],
        print_output: bool = False
    ):
        self.print_output = print_output
        self.directory = directory
        self.scenario_map = scenario_map
        self.scenario_ranges = scenario_ranges
        self.scenario_to_csv_map = scenario_to_csv_map
        self.is_sorted = False  # State variable to track if the tree is sorted
        self.active_sort_mode = None  # Track which sort mode is currently active
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Initialize database preferences
        self.db_preferences = DatabasePreferences(print_output=print_output)
        
        # Initialize rating system (this may override the provided color_map)
        self.current_rating_system = self.settings_manager.get_rating_system()
        self.rating_config = RATING_SYSTEMS[self.current_rating_system]
        self.color_map = self.rating_config['color_map']
        self.rating_range = self.rating_config['range']

        # Initialize other UI components
        self.comment_tooltip: Optional[tk.Toplevel] = None
        self.comment_indicators: Dict[tuple, tk.Label] = {}  # Store comment indicators
        self.row_checkboxes: List[tk.IntVar] = []
        self.column_checkboxes: List[tk.IntVar] = []

        self.select_database()
        self.initialize_ui_vars()

        if print_output:
            print(f"TKINTER VERSION: {tk.TkVersion}")
            

    def select_database(self):
        """Select database with persistence support"""
        if self.print_output:
            print("Starting database selection process...")
        
        # Try to load previously selected database
        saved_path, saved_name = self.db_preferences.get_last_database()
        
        if self.print_output:
            print(f"Retrieved saved database: path='{saved_path}', name='{saved_name}'")
        
        if saved_path and saved_name:
            # Validate that the saved database still exists
            if self.print_output:
                print(f"Validating database existence...")
            
            if self.db_preferences.validate_database_exists(saved_path, saved_name):
                # Use saved database
                self.db_path = saved_path
                self.db_name = saved_name
                self.db_manager = DbManager(path=self.db_path, name=self.db_name)
                
                if self.print_output:
                    print(f"✅ Successfully loaded saved database: {saved_name} from {saved_path}")
                
                # Don't return here - continue to cache initialization
                skip_dialog = True
            else:
                # Database file not found, show user-friendly error and continue to selection
                full_path = f"{saved_path}/{saved_name}" if saved_path and saved_name else "Unknown"
                if self.print_output:
                    print(f"❌ Database validation failed for: {full_path}")
                
                messagebox.showwarning("Database Not Found", 
                    f"Previous database '{saved_name}' could not be found at:\n{full_path}\n\n"
                    "Please select a database to continue.")
        
        # No saved database or saved database not found - show selection dialog
        if not locals().get('skip_dialog', False):
            if self.print_output:
                print("Showing database selection dialog...")
            
            db_load_ui = DbLoadUi()
            self.db_path, self.db_name = db_load_ui.create_or_load_database()

            if self.print_output:
                print(f"User selected: path='{self.db_path}', name='{self.db_name}'")

        if self.db_path is None:
            self.db_manager = DbManager()
            if self.print_output:
                print("Using default database manager")
        else:
            # Only create db_manager if we don't already have one (from saved database path)
            if not hasattr(self, 'db_manager') or self.db_manager is None:
                self.db_manager = DbManager(path=self.db_path, name=self.db_name)
            
            # Save the selected database for future use
            if self.db_name is not None:
                success = self.db_preferences.save_database_preference(self.db_path, self.db_name)
                if self.print_output:
                    print(f"Database preference saved: {success}")
            else:
                if self.print_output:
                    print("Cannot save database preference: db_name is None")
        
        # Initialize high-performance cache system after database is ready
        self.cache_error_reason = None  # Track why cache failed
        try:
            print(f"🔄 Attempting to initialize cache with database: {self.db_manager}")
            if self.db_manager is None:
                raise Exception("Database manager is None - database connection failed")
            
            self.data_cache = MatchupDataCache(self.db_manager, print_output=self.print_output)
            print("✅ Data cache initialized successfully")
            print(f"📊 Cache status: {self.data_cache is not None}")
            self.cache_error_reason = None  # Clear any previous error
        except Exception as e:
            error_msg = f"Failed to initialize data cache: {e}"
            print(f"❌ {error_msg}")
            if self.print_output:
                print(f"📊 Database manager status: {self.db_manager}")
                print(f"📊 Database path: {getattr(self, 'db_path', 'Not set')}")
                print(f"📊 Database name: {getattr(self, 'db_name', 'Not set')}")
            
            self.data_cache = None
            self.cache_error_reason = error_msg
            print(f"⚠️ Application will run in FALLBACK MODE due to cache failure")
            print(f"⚠️ Error reason: {self.cache_error_reason}")
            
    def initialize_ui_vars(self):
        # set root
        self.root = tk.Tk()
        self.root.geometry('+0+0')
        self.root.title(f"QTR'S KLIK KLAKER")

        # set key bindings
        self.root.bind('<Escape>', lambda event: self.root.quit())
        self.root.bind('<Return>', lambda event: self.on_generate_combinations())
        self.root.bind('<Control-Tab>', lambda event: self.switch_tab())

        # Create the top team name and scenario display
        self.drop_down_frame = tk.Frame(self.root)
        self.drop_down_frame.pack(side=tk.TOP)

        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.root)

        # Create the frames for the tabs
        self.team_grid_frame = tk.Frame(self.notebook)
        self.matchup_tree_frame = tk.Frame(self.notebook)

        # Add tabs to the notebook
        self.notebook.add(self.team_grid_frame, text='Team Grid')
        self.notebook.add(self.matchup_tree_frame, text='Matchup Tree')

        # Pack the notebook to fill the main window
        self.notebook.pack(expand=1, fill='both')

        # set frames for the team grid tab
        #commenting some changes.

        self.top_frame = tk.Frame(self.team_grid_frame)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        # Single unified grid frame
        self.grid_frame = tk.Frame(self.top_frame, relief=tk.RIDGE, borderwidth=2)
        self.grid_frame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.button_row_frame = tk.Frame(self.team_grid_frame)
        self.button_row_frame.pack(side=tk.TOP, fill=tk.X)

        # set frames for the matchup tree tab - tree now takes full width
        self.tree_tab_frame = tk.Frame(self.matchup_tree_frame)
        self.tree_tab_frame.pack(side=tk.TOP, expand=1, fill=tk.BOTH, padx=5, pady=5)
        
        # Create bottom frame for buttons and output panel side by side
        self.bottom_frame = tk.Frame(self.matchup_tree_frame)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.buttons_frame = tk.Frame(self.bottom_frame)
        self.buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        self.grid_display_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_display_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        
        # Track grid flip state and store original data
        self.grid_is_flipped = False
        self.original_grid_data = None

        self.team_b = tk.IntVar()
        pairingLead = tk.Checkbutton(self.buttons_frame, text="Our team first", variable=self.team_b)
        pairingLead.pack(side=tk.BOTTOM,pady=5)
        pairingLead.select()

        self.sort_alpha = tk.IntVar()
        alphaBox = tk.Checkbutton(self.buttons_frame, text="Sort Pairings Alphabetically", variable=self.sort_alpha)
        alphaBox.pack(side=tk.BOTTOM,pady=5)
        alphaBox.select()

        # create treeview and tree generator with all three score columns
        self.treeview = LazyTreeView(master=self.tree_tab_frame, print_output=self.print_output, columns=("Rating", "Cumulative Score", "Confidence Score", "Resistance Score"))
        self.tree_generator = TreeGenerator(treeview=self.treeview, sort_alpha=self.sort_alpha.get())
        
        # Track current sorting mode for column display
        self.current_sort_mode = "none"

    
    def create_ui(self):
        self.create_ui_grids()

        tk.Label(self.drop_down_frame, text='Select Team 1:').pack(side=tk.LEFT, padx=5, pady=5)
        # Use a StringVar to hold the value of the Combobox
        self.team1_var = tk.StringVar()
        # create combobox
        self.combobox_1 = ttk.Combobox(self.drop_down_frame, state='readonly', width=20, textvariable=self.team1_var)
        self.combobox_1.pack(side=tk.LEFT, padx=5, pady=5)
        # Set an instance variable to keep track of the previous value
        self.previous_team1 = self.team1_var.get()
        # Attach a trace to the StringVar
        self.team1_var.trace_add('write', self.on_team_box_change)
		
        tk.Label(self.drop_down_frame, text='Select Team 2:').pack(side=tk.LEFT, padx=5, pady=5)
        # Use a StringVar to hold the value of the Combobox
        self.team2_var = tk.StringVar()
        # create combobox
        self.combobox_2 = ttk.Combobox(self.drop_down_frame, state='readonly', width=20, textvariable=self.team2_var)
        self.combobox_2.pack(side=tk.LEFT, padx=5, pady=5)
        # Set an instance variable to keep track of the previous value
        self.previous_team2 = self.team2_var.get()
        # Attach a trace to the StringVar
        self.team2_var.trace_add('write', self.on_team_box_change)

        # create combobox for scenario selection
        # create the label
        tk.Label(self.drop_down_frame, text='Choose Scenario:').pack(side=tk.LEFT, padx=5, pady=5)
        # create scenarios drop down box
        # Use a StringVar to hold the value of the Combobox
        self.scenario_var = tk.StringVar()
        self.scenario_box = ttk.Combobox(self.drop_down_frame, state='readonly', width=20, textvariable=self.scenario_var)
        # self.scenario_box.bind('<<ComboboxSelected>>', self.on_combobox_select)
        self.scenario_box.pack(side=tk.LEFT, padx=5, pady=5)
        # Set an instance variable to keep track of the previous value
        self.previous_value = self.scenario_var.get()
        # Attach a trace to the StringVar
        self.scenario_var.trace_add('write', self.on_scenario_box_change)
        self.set_team_dropdowns()
        self.update_scenario_box()

        # Add essential buttons to a row just above the pairing grid       
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Flip Grid", command=lambda: self.flip_grid_perspective()).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Data Management menu button
        data_mgmt_button = tk.Button(self.button_row_frame, text="Data Management", 
                                   command=lambda: self.show_data_management_menu(),
                                   bg="lightcyan", fg="darkgreen", font=("Arial", 9, "bold"),
                                   relief=tk.RAISED, borderwidth=2)
        data_mgmt_button.pack(side=tk.LEFT, padx=10, pady=5)

        # Initialize round tracking variables first
        self.round_dropdowns = []
        self.round_vars = []
        self.enemy_round_dropdowns = []
        self.enemy_round_vars = []
        self.selected_players_per_round = {}
        
        # Create Round Selection section for Team Grid tab only
        self.create_team_grid_round_selection()

		# Configure Treeview with style and maximize space
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10))
        self.treeview.tree.heading("#0", text="Pairing")
        # Configure tree column headings
        self.treeview.tree.heading("Rating", text="Rating")
        self.treeview.tree.heading("Cumulative Score", text="Cumulative Score")
        self.treeview.tree.heading("Confidence Score", text="Confidence Score") 
        self.treeview.tree.heading("Resistance Score", text="Resistance Score")
        
        # Configure column widths - will be dynamically updated
        self.configure_tree_column_widths()
        
        # Bind resize event to update column widths
        self.treeview.tree.bind('<Configure>', self.on_tree_configure)
        
        # Schedule initial column configuration after UI is fully loaded
        self.root.after(100, self.configure_tree_column_widths)
        self.treeview.tree.tag_configure('1', background="orangered")
        self.treeview.tree.tag_configure('2', background="orange")
        self.treeview.tree.tag_configure('3', background="yellow")
        self.treeview.tree.tag_configure('4', background="greenyellow")
        self.treeview.tree.tag_configure('5', background="lime")
        self.treeview.pack(expand=1, fill='both')
		
        generateButton = tk.Button(self.buttons_frame, text="Generate\nCombinations", command=self.on_generate_combinations)
        generateButton.pack(fill=tk.X, pady=5)

        # Initialize sorting state tracking
        self.active_sort_mode = None  # Track which sort is currently active
        
        # Create sorting buttons with active/inactive states
        self.cumulative_button = tk.Button(self.buttons_frame, text="⚫ Cumulative\nSort", command=self.toggle_cumulative_sort)
        self.cumulative_button.pack(fill=tk.X, pady=5)

        self.confidence_button = tk.Button(self.buttons_frame, text="⚫ Highest\nConfidence", command=self.toggle_confidence_sort)
        self.confidence_button.pack(fill=tk.X, pady=5)

        self.counter_button = tk.Button(self.buttons_frame, text="⚫ Counter\nPick", command=self.toggle_counter_sort)
        self.counter_button.pack(fill=tk.X, pady=5)
        
        # Add the new Strategic Optimal button
        self.strategic_button = tk.Button(self.buttons_frame, text="⚫ Strategic\nOptimal", command=self.toggle_strategic_optimal_sort)
        self.strategic_button.pack(fill=tk.X, pady=5)
        
        # Set initial button states (all inactive)
        self.update_sort_button_states()
        


        # Create Matchup Output Panel next to buttons in bottom frame
        self.create_matchup_output_panel()

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here\nNavigate the tree with arrow keys!")
        self.create_tooltip(self.strategic_button, "Strategic Optimal Expected Value sorting\nOptimizes for 3/5 wins while preventing catastrophic failures\nAccounts for opponent counter-strategies and team strength")

        self.update_combobox_colors()
        self.init_display_headers()
        
        # Create status bar
        self.create_status_bar()
        
        # Initialize matchup tree synchronizer after all UI components are created
        self.tree_synchronizer = None
        try:
            self.tree_synchronizer = MatchupTreeSynchronizer(self)
            print("Matchup tree synchronizer initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize tree synchronizer: {e}")

        # Show welcome message if this is first run or user preference
        self.show_welcome_message_if_needed()

        self.root.mainloop()

    def show_welcome_message_if_needed(self):
        """Show welcome message on first run or if preference is enabled"""
        if self.db_preferences.should_show_welcome_message():
            welcome_dialog = WelcomeDialog(self.root)
            show_again = welcome_dialog.show_welcome_message()
            
            # Save the preference
            self.db_preferences.set_welcome_message_preference(show_again)
            
            # If user clicked "Open Data Management", show preferences
            if hasattr(welcome_dialog, 'result') and welcome_dialog.result == "open_settings":
                self.show_preferences_dialog()

    def configure_tree_column_widths(self):
        """Configure tree column widths according to specification: 80% pairing, 5% each for scores"""
        try:
            # Get current tree width (default to reasonable size if not available)
            tree_width = self.treeview.tree.winfo_width() if self.treeview.tree.winfo_width() > 1 else 1000
            
            # If tree width is still 1 (not yet rendered), use the frame width or window width
            if tree_width <= 1:
                try:
                    tree_width = self.tree_tab_frame.winfo_width() if self.tree_tab_frame.winfo_width() > 1 else 1000
                except:
                    tree_width = 1000
            
            # Calculate widths: 80% for pairing, 5% each for the 4 score columns
            pairing_width = int(tree_width * 0.75)  # Slightly less to account for scrollbars
            score_width = int(tree_width * 0.06)    # Slightly more to balance
            
            # Set minimum widths to ensure readability
            min_pairing_width = 400
            min_score_width = 60
            
            pairing_width = max(pairing_width, min_pairing_width)
            score_width = max(score_width, min_score_width)
            
            # Apply widths
            self.treeview.tree.column("#0", width=pairing_width, minwidth=min_pairing_width)
            self.treeview.tree.column("Rating", width=score_width, minwidth=min_score_width)
            self.treeview.tree.column("Cumulative Score", width=score_width, minwidth=min_score_width)
            self.treeview.tree.column("Confidence Score", width=score_width, minwidth=min_score_width)
            self.treeview.tree.column("Resistance Score", width=score_width, minwidth=min_score_width)
            
            if self.print_output:
                print(f"Configured tree columns: Pairing={pairing_width}px, Scores={score_width}px each (total width: {tree_width}px)")
            
        except Exception as e:
            if self.print_output:
                print(f"Error configuring tree column widths: {e}")

    def on_tree_configure(self, event):
        """Handle tree widget resize to maintain column proportions"""
        try:
            # Only reconfigure if the event is for the treeview widget itself
            if event.widget == self.treeview.tree:
                self.root.after_idle(self.configure_tree_column_widths)
        except Exception as e:
            if self.print_output:
                print(f"Error in tree configure event: {e}")

    def show_preferences_dialog(self):
        """Show database and UI preferences dialog"""
        preferences_dialog = DatabasePreferencesDialog(self.root, self.db_preferences)
        preferences_dialog.show_preferences_dialog()

    def create_ui_grids(self):
        self.row_checkboxes = []
        self.column_checkboxes = []

        # Single unified grid title
        grid_label = tk.Label(self.grid_frame, text="Team Matchup Analysis Grid", font=("Arial", 14, "bold"), bg="lightcyan")
        grid_label.grid(row=0, column=0, columnspan=13, pady=(0, 5), sticky="ew")

        # Section headers
        rating_header = tk.Label(self.grid_frame, text="Rating Matrix", font=("Arial", 11, "bold"), bg="lightblue")
        rating_header.grid(row=1, column=0, columnspan=6, pady=(0, 2), sticky="ew")
        
        # Visual separator
        separator = tk.Frame(self.grid_frame, width=3, bg="darkgray")
        separator.grid(row=1, column=6, rowspan=7, sticky="ns", padx=5)
        
        calc_header = tk.Label(self.grid_frame, text="Calculations", font=("Arial", 11, "bold"), bg="lightgreen")
        calc_header.grid(row=1, column=7, columnspan=6, pady=(0, 2), sticky="ew")

        # Create the 6x6 rating grid (left side of unified grid)
        for r in range(6):
            for c in range(6):
                # Rating grid entries (columns 0-5)
                entry = tk.Entry(self.grid_frame, textvariable=self.grid_entries[r][c], width=8, 
                               font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
                entry.grid(row=r + 2, column=c, padx=1, pady=1, sticky="nsew", ipadx=2, ipady=2)
                self.grid_widgets[r][c] = entry
                self.grid_entries[r][c].trace_add('write', lambda name, index, mode, var=self.grid_entries[r][c], row=r, col=c: self.update_color_on_change(var, index, mode, row, col))
                
                # Add comment functionality to matchup cells (not header cells)
                if r > 0 and c > 0:
                    # Bind mouse events for comment tooltips and editing
                    entry.bind("<Enter>", lambda event, row=r, col=c: self.show_comment_tooltip(event, row, col))
                    entry.bind("<Leave>", self.hide_comment_tooltip)
                    entry.bind("<Button-3>", lambda event, row=r, col=c: self.open_comment_editor(event, row, col))

        # Create the display grid (right side of unified grid, columns 7-12)
        for r in range(6):
            for c in range(6):
                # Display grid entries (columns 7-12)
                display_entry = tk.Entry(self.grid_frame, textvariable=self.grid_display_entries[r][c], width=8, 
                                       state='readonly', font=("Arial", 10), relief=tk.SOLID, borderwidth=1,
                                       readonlybackground="lightgray")
                display_entry.grid(row=r + 2, column=c + 7, padx=1, pady=1, sticky="nsew", ipadx=2, ipady=2)
                self.grid_display_widgets[r][c] = display_entry

        # Configure grid weights for the unified grid
        for i in range(2, 8):  # rows 2-7 for grid data
            self.grid_frame.grid_rowconfigure(i, weight=1)
        for i in range(13):  # columns 0-12 (6 rating + separator + 6 display)
            if i != 6:  # Don't expand separator column
                self.grid_frame.grid_columnconfigure(i, weight=1)

        # Add row checkboxes (column 13)
        checkbox_label = tk.Label(self.grid_frame, text="Row\nSelect", font=("Arial", 9, "bold"))
        checkbox_label.grid(row=1, column=13, pady=(0, 2))
        
        for r in range(1, 6):
            var = tk.IntVar()
            entry = tk.Checkbutton(self.grid_frame, variable=var, text=f"R{r}")
            entry.grid(row=r + 2, column=13, padx=2, pady=1, sticky="w")
            var.trace_add('write', lambda name, index, mode, row=r, var=var: self.on_row_checkbox_change(row, var))
            self.row_checkboxes.append(var)

        # Add column checkboxes (row 8, columns 1-5)
        col_label = tk.Label(self.grid_frame, text="Column Select", font=("Arial", 9, "bold"))
        col_label.grid(row=8, column=1, columnspan=5, pady=(5, 0))
        
        for c in range(1, 6):
            var = tk.IntVar()
            entry = tk.Checkbutton(self.grid_frame, variable=var, text=f"C{c}")
            entry.grid(row=9, column=c, padx=1, pady=2, sticky="n")
            var.trace_add('write', lambda name, index, mode, col=c, var=var: self.on_column_checkbox_change(col, var))
            self.column_checkboxes.append(var)

        # Configure weights for checkbox and header areas
        self.grid_frame.grid_rowconfigure(8, weight=0)  # Don't expand label row
        self.grid_frame.grid_rowconfigure(9, weight=0)  # Don't expand checkbox row
        self.grid_frame.grid_columnconfigure(6, weight=0)  # Don't expand separator
        self.grid_frame.grid_columnconfigure(13, weight=0)  # Don't expand checkbox column

        # for r in range(6):
        #     for c in range(6):
        #         display_entry = tk.Entry(self.right_frame, textvariable=self.grid_display_entries[r][c], width=10, state='readonly')
        #         display_entry.grid(row=r, column=c, padx=5, pady=5, sticky="nw")
        #         self.grid_display_widgets[r][c] = display_entry

    def create_team_grid_round_selection(self):
        """Create the Round Selection section for Team Grid tab with 75%/25% split"""
        # Create main container for Round Selection with 75%/25% split
        main_container = tk.Frame(self.team_grid_frame)
        main_container.pack(fill=tk.BOTH, padx=10, pady=5)
        main_container.grid_rowconfigure(0, weight=1)  # Allow vertical expansion
        
        # Configure main container for proper 75%/25% split
        main_container.grid_columnconfigure(0, weight=3)  # 75% for Round Selection
        main_container.grid_columnconfigure(1, weight=1)  # 25% for Matchup Output
        
        # Create 75% width frame for Round Selection
        self.round_selection_frame = tk.Frame(main_container, relief=tk.RIDGE, borderwidth=1)
        self.round_selection_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        
        # Create 25% width frame for future Matchup Output
        self.matchup_output_frame = tk.Frame(main_container, bg='#f0f0f0', relief=tk.RIDGE, borderwidth=1)
        self.matchup_output_frame.grid(row=0, column=1, sticky='nsew', padx=(2, 0))
        
        # Create "Our Team First" checkbox at the top center of Round Selection frame
        self.team_b_duplicate = tk.IntVar()
        # Sync with the original checkbox
        self.team_b_duplicate.set(self.team_b.get())
        # Add trace to keep them in sync
        self.team_b_duplicate.trace_add("write", lambda *args: self.team_b.set(self.team_b_duplicate.get()))
        self.team_b.trace_add("write", lambda *args: self.team_b_duplicate.set(self.team_b.get()))
        
        team_first_checkbox = tk.Checkbutton(self.round_selection_frame, text="Our Team First", variable=self.team_b_duplicate, font=("Arial", 10))
        team_first_checkbox.pack(pady=(5, 10))  # Centered horizontally with padding
        
        # Create header frame for Round Selection title
        header_frame = tk.Frame(self.round_selection_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Centered "Round Selection" label
        round_label = tk.Label(header_frame, text="Round Selection", font=("Arial", 10, "bold"))
        round_label.pack()
        
        # Add placeholder label in matchup output area
        placeholder_label = tk.Label(self.matchup_output_frame, text="Matchup Output\n(Future Feature)", 
                                   bg='#f0f0f0', fg='gray', font=("Arial", 9))
        placeholder_label.pack(expand=True)
        
        # Create round selection dropdowns in the main round selection frame
        self.create_round_selection_dropdowns()

    def on_row_checkbox_change(self, row, var):
        print(f"Row {row} checkbox changed to {var.get()}")
        for col in range(1,6):
            widget = self.grid_widgets[row][col]
            if var.get() == 1:  # Checkbox is checked
                widget.config(state='disabled', bg='grey')
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.column_checkboxes[col-1].get() == 0:  # Column checkbox is also unchecked
                    widget.config(state='normal')
                    self.update_color_on_change(self.grid_entries[row][col], None, None, row, col)
        self.on_scenario_calculations()

    def on_column_checkbox_change(self, col, var):
        print(f"Column {col} checkbox changed to {var.get()}")
        for row in range(1,6):
            widget = self.grid_widgets[row][col]
            if var.get() == 1:  # Checkbox is checked
                widget.config(state='disabled', bg='grey')
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.row_checkboxes[row-1].get() == 0:  # Row checkbox is also unchecked
                    widget.config(state='normal')
                    self.update_color_on_change(self.grid_entries[row][col], None, None, row, col)
        self.on_scenario_calculations()

    def update_combobox_colors(self):
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                widget = self.grid_widgets[row][col]
                if widget and value in self.color_map:
                    widget.config(bg=self.color_map[value])

    def update_color_on_change(self, var, index, mode, row, col):
        if self.row_checkboxes and row-1 < len(self.row_checkboxes) and self.row_checkboxes[row-1].get() == 1:
            return  # Skip updating color if row checkbox is checked
        if self.column_checkboxes and col-1 < len(self.column_checkboxes) and self.column_checkboxes[col-1].get() == 1:
            return  # Skip updating color if column checkbox is checked
        value = var.get()
        widget = self.grid_widgets[row][col]
        if widget and value in self.color_map:
            widget.config(bg=self.color_map[value])
        elif widget:
            widget.config(bg='white')
    
    def update_grid_colors(self):
        """Update all grid cell colors based on current rating system"""
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                widget = self.grid_widgets[row][col]
                if widget and value in self.color_map:
                    widget.config(bg=self.color_map[value])
                elif widget:
                    widget.config(bg='white')
    
    def create_status_bar(self):
        """Create status bar showing current rating system"""
        self.status_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Database info
        db_name = getattr(self, 'db_name', 'Unknown')
        self.db_status = tk.Label(self.status_frame, text=f"Database: {db_name}", anchor=tk.W)
        self.db_status.pack(side=tk.LEFT, padx=5)
        
        # Cache mode indicator with error details
        has_cache_attr = hasattr(self, 'data_cache') 
        cache_not_none = getattr(self, 'data_cache', None) is not None
        
        if self.print_output:
            print(f"📊 Status bar debug: has_cache_attr={has_cache_attr}, cache_not_none={cache_not_none}")
            print(f"📊 data_cache value: {getattr(self, 'data_cache', 'NOT_SET')}")
        
        if has_cache_attr and cache_not_none:
            cache_mode = "Normal Mode"
            cache_color = "#228B22"  # Green for normal
            show_reconnect = False
        else:
            cache_mode = "Fallback Mode"
            cache_color = "#FF6B35"  # Orange for fallback
            show_reconnect = True
            if hasattr(self, 'cache_error_reason') and self.cache_error_reason:
                cache_mode += " (ERROR)"
                cache_color = "#DC143C"  # Red for error

        self.cache_status = tk.Label(self.status_frame, text=f"• {cache_mode}", 
                                   anchor=tk.W, fg=cache_color, font=("Arial", 8, "bold"))
        self.cache_status.pack(side=tk.LEFT, padx=(10, 5))
        
        # Add reconnect button if in fallback mode
        if show_reconnect:
            if self.print_output:
                print("📊 Adding reconnect button (cache failed)")
            self.reconnect_btn = tk.Button(self.status_frame, text="🔄 Reconnect Database", 
                                         command=self.reconnect_database,
                                         bg="#FFA500", fg="white", font=("Arial", 8, "bold"),
                                         relief=tk.RAISED, bd=2)
            self.reconnect_btn.pack(side=tk.LEFT, padx=(5, 10))
        else:
            if self.print_output:
                print("📊 Not adding reconnect button (cache working)")
        
        # Add tooltip for cache status
        self.create_cache_status_tooltip()
        
        # Rating system info
        system_info = f"Rating System: {self.rating_config['name']} ({self.rating_range[0]}-{self.rating_range[1]})"
        self.rating_status = tk.Label(self.status_frame, text=system_info, anchor=tk.CENTER)
        self.rating_status.pack(side=tk.LEFT, expand=True, padx=20)
        
        # Add color preview
        color_frame = tk.Frame(self.status_frame)
        color_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Label(color_frame, text="Colors:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(0, 3))
        
        for rating in sorted(self.color_map.keys()):
            color_box = tk.Label(color_frame, text=rating, bg=self.color_map[rating], 
                               width=2, relief=tk.RAISED, borderwidth=1, font=("Arial", 7, "bold"))
            color_box.pack(side=tk.LEFT, padx=1)
    
    def create_cache_status_tooltip(self):
        """Create tooltip for cache status indicator"""
        # Store reference to current tooltip window
        current_tooltip = None
        
        def show_tooltip(event):
            nonlocal current_tooltip
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                tooltip_text = ("Normal Mode: High-performance caching enabled\n"
                              "• Faster data loading and saving\n"
                              "• Reduced database queries (80-90% fewer)\n"
                              "• Optimal performance")
            else:
                tooltip_text = ("Fallback Mode: Direct database access\n"
                              "• Cache system unavailable\n"
                              "• All operations use direct database queries\n"
                              "• Reduced performance")
                
                if hasattr(self, 'cache_error_reason') and self.cache_error_reason:
                    tooltip_text += f"\n\n❌ Error Details:\n{self.cache_error_reason}\n\nUse 'Reconnect Database' to attempt recovery"
            
            # Create tooltip window
            current_tooltip = tk.Toplevel()
            current_tooltip.wm_overrideredirect(True)
            current_tooltip.configure(bg='lightyellow', relief='solid', bd=1)
            
            # Position tooltip near mouse
            x, y = event.widget.winfo_rootx() + 20, event.widget.winfo_rooty() + 20
            current_tooltip.geometry(f"+{x}+{y}")
            
            # Add tooltip text
            label = tk.Label(current_tooltip, text=tooltip_text, 
                           bg='lightyellow', font=("Arial", 8),
                           justify=tk.LEFT, padx=5, pady=3)
            label.pack()
        
        def hide_tooltip(event):
            nonlocal current_tooltip
            if current_tooltip:
                current_tooltip.destroy()
                current_tooltip = None
        
        # Bind events to cache status label
        if hasattr(self, 'cache_status'):
            self.cache_status.bind('<Enter>', show_tooltip)
            self.cache_status.bind('<Leave>', hide_tooltip)

    
    # Add this method to update display-only fields
    def update_display_fields(self, row, col, value):
        try:
            self.grid_display_entries[row][col].set(value)
        except (ValueError, IndexError) as e:
            print(f"update_display_fields has failed with error:\n{e}")

    def init_display_headers(self):
        try:
            self.update_display_fields(0,0,"FLOOR")
            self.update_display_fields(0,1,"PINNED?")
            self.update_display_fields(0,2,"CAN-PIN?")
            self.update_display_fields(0,3,"PROTECT")
            self.update_display_fields(0,4,"MAX/MIN")
            self.update_display_fields(0,5,"SUM MARG")
        except (ValueError, IndexError) as e:
            print(f"update_display_fields has failed with error:\n{e}")

    def on_scenario_calculations(self):
        """Run all calculations only if we have valid team data."""
        print("🔧 DEBUG: on_scenario_calculations() called")
        
        # Only run calculations if both teams are selected
        if not self._are_both_teams_selected():
            print("🔧 DEBUG: Skipping calculations - teams not properly selected")
            if self.print_output:
                print("Skipping calculations - teams not properly selected")
            return
        
        print("🔧 DEBUG: Teams are properly selected, checking for data in grid")
        
        # Check if we have any actual data in the grid
        has_data = False
        for row in range(1, 6):
            for col in range(1, 6):
                grid_value = self._safe_get_int_from_grid(row, col, default=None)
                if grid_value is not None:
                    print(f"🔧 DEBUG: Found data at [{row}][{col}]: {grid_value}")
                    has_data = True
                    break
            if has_data:
                break
        
        if not has_data:
            print("🔧 DEBUG: No rating data found in grid - clearing calculations but keeping headers")
            if self.print_output:
                print("No rating data in grid - clearing calculations but keeping headers")
            # Clear calculations but keep headers visible
            for row in range(1, 6):
                for col in range(6):
                    if col == 0:  # FLOOR column
                        self.update_display_fields(row, col, "")
                    elif col == 1:  # PINNED? column  
                        self.update_display_fields(row, col, "---")
                    elif col == 2:  # CAN-PIN? column
                        self.update_display_fields(row, col, "---")
                    elif col == 3:  # PROTECT column
                        self.update_display_fields(row, col, "---")
                    elif col == 4:  # MAX/MIN column
                        self.update_display_fields(row, col, "")
                    elif col == 5:  # SUM MARG column
                        self.update_display_fields(row, col, "")
            return
        
        print("🔧 DEBUG: Data found in grid, proceeding with calculations")
        
        # Run all calculation methods
        self.set_floor_values()  # info_col 0
        self.check_pinned_players()  # info_col 1
        self.check_for_pins()  # info_col 2
        self.check_protect()  # info_col 3
        self.check_margins()  # info_col 4 & 5
        
        # Update comment indicators only if we have valid data
        if hasattr(self, 'update_comment_indicators'):
            try:
                self.update_comment_indicators()
            except Exception as e:
                if self.print_output:
                    print(f"Error updating comment indicators: {e}")

    def check_margins(self):
        """Check margins with safe integer conversion."""
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    for col in range(4, 6):
                        self.update_display_fields(row, col, "---")
                    continue
                
                # Get floor rating sum safely
                floor_value = self.grid_display_entries[row][0].get()
                if not floor_value or floor_value == "":
                    self.update_display_fields(row, 4, "")
                    self.update_display_fields(row, 5, "")
                    continue
                
                try:
                    floor_rating_sum = int(floor_value)
                except ValueError:
                    self.update_display_fields(row, 4, "")
                    self.update_display_fields(row, 5, "")
                    continue
                
                all_margins = []
                for col in range(1, 6):
                    col_margin_sum = 0
                    valid_col_ratings = 0
                    
                    for row1 in range(1, 6):
                        widget = self.grid_widgets[row1][col]
                        if widget is not None and widget.cget('state') != 'disabled':
                            rating = self._safe_get_int_from_grid(row1, col, default=None)
                            if rating is not None:
                                col_margin_sum += rating
                                valid_col_ratings += 1
                    
                    if valid_col_ratings > 0:
                        diff = floor_rating_sum - col_margin_sum
                        all_margins.append(diff)
                
                if all_margins:
                    max_margin = max(all_margins)
                    min_margin = min(all_margins)
                    margin_text = f"{max_margin} | {min_margin}"
                    self.update_display_fields(row, 4, margin_text)
                    
                    sum_margins = sum(all_margins)
                    self.update_display_fields(row, 5, sum_margins)
                else:
                    self.update_display_fields(row, 4, "")
                    self.update_display_fields(row, 5, "")
                    
            except Exception as e:
                if self.print_output:
                    print(f"check_margins has failed for row {row} with error: {e}")
                self.update_display_fields(row, 4, "")
                self.update_display_fields(row, 5, "")

    def check_protect(self):
        """Check protection values with safe integer conversion."""
        for row in range(1, 6):
            try:
                if (self.row_checkboxes and 
                    row - 1 < len(self.row_checkboxes) and 
                    self.row_checkboxes[row - 1].get() == 1):
                    self.update_display_fields(row, 3, "---")
                    continue
                
                # Safely check if player is pinned or can pin
                pinned_value = self.grid_display_entries[row][1].get() if hasattr(self, 'grid_display_entries') else ""
                pinner_value = self.grid_display_entries[row][2].get() if hasattr(self, 'grid_display_entries') else ""
                
                row_pinned = pinned_value and pinned_value != "---" and pinned_value != ""
                row_pinner = pinner_value and pinner_value != "---" and pinner_value != ""
                
                protect = "Yes" if row_pinned or row_pinner else "No"
                self.update_display_fields(row, 3, protect)
                
            except Exception as e:
                if self.print_output:
                    print(f"check_protect has failed for row {row} with error: {e}")
                self.update_display_fields(row, 3, "")

    def check_for_pins(self):
        """Check if player can pin opponents with safe integer conversion."""
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 2, "---")
                    continue
                
                good_matchups = 0
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        rating = self._safe_get_int_from_grid(row, col, default=3)  # Default to 3 (neutral)
                        if rating is not None and rating > 3:
                            good_matchups += 1
                
                can_pin = "PIN" if good_matchups > 1 else "---"
                self.update_display_fields(row, 2, can_pin)
                
            except Exception as e:
                if self.print_output:
                    print(f"check_for_pins has failed for row {row} with error: {e}")
                self.update_display_fields(row, 2, "")

    def check_pinned_players(self):
        """Check for pinned players with safe integer conversion."""
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 1, "---")
                    continue
                
                num_bad_matchups = 0
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        rating = self._safe_get_int_from_grid(row, col, default=3)  # Default to 3 (neutral)
                        if rating is not None and rating < 3:
                            num_bad_matchups += 1
                
                player_pinned = "PINNED!" if num_bad_matchups > 1 else "---"
                self.update_display_fields(row, 1, player_pinned)
                
            except Exception as e:
                if self.print_output:
                    print(f"check_pinned_players has failed for row {row} with error: {e}")
                self.update_display_fields(row, 1, "")

    def set_floor_values(self):
        """Set floor values with safe integer conversion."""
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row-1 < len(self.row_checkboxes) and self.row_checkboxes[row-1].get() == 1:
                    self.update_display_fields(row, 0, "---")
                    continue
                
                floor_rating_sum = 0
                valid_ratings = 0
                
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        rating = self._safe_get_int_from_grid(row, col, default=None)
                        if rating is not None:
                            floor_rating_sum += rating
                            valid_ratings += 1
                
                # Only display sum if we have valid ratings
                if valid_ratings > 0:
                    self.update_display_fields(row, 0, floor_rating_sum)
                else:
                    self.update_display_fields(row, 0, "")
                    
            except Exception as e:
                if self.print_output:
                    print(f"set_floor_values has failed for row {row} with error: {e}")
                self.update_display_fields(row, 0, "")

    def switch_tab(self):
        current_tab = self.notebook.index(self.notebook.select())
        total_tabs = self.notebook.index('end')
        next_tab = (current_tab + 1) % total_tabs
        self.notebook.select(next_tab)

    def on_create_team(self):
        self.create_team()
        
    def on_delete_team(self):
        self.delete_team()
        self.update_ui()
    
    def on_change_database(self):
        """Allow user to select a different database or create a new one."""
        from tkinter import messagebox
        
        try:
            # Show confirmation dialog
            result = messagebox.askyesno("Change Database", 
                                       "This will close the current database and allow you to select a new one.\n\n"
                                       "Any unsaved changes will be lost.\n\n"
                                       "Do you want to continue?")
            
            if result:
                # Clear current tree data
                if hasattr(self, 'treeview') and self.treeview:
                    self.treeview.tree.delete(*self.treeview.tree.get_children())
                
                # Reset sorting states
                self.active_sort_mode = None
                self.is_sorted = False
                self.current_sort_mode = "none"
                if hasattr(self, 'update_sort_button_states'):
                    self.update_sort_button_states()
                
                # Clear grid data
                for r in range(6):
                    for c in range(6):
                        self.grid_entries[r][c].set("")
                        self.grid_display_entries[r][c].set("")
                
                # Trigger database selection
                self.select_database()
                
                # Update UI with new database
                self.update_ui()
                
                # Show success message
                db_name = self.db_name if hasattr(self, 'db_name') and self.db_name else "Selected Database"
                messagebox.showinfo("Database Changed", f"Successfully switched to: {db_name}")
                
        except Exception as e:
            print(f"Error changing database: {e}")
            messagebox.showerror("Error", f"Failed to change database: {e}")
    
    def on_configure_rating_system(self):
        """Show dialog to configure rating system preference."""
        try:
            dialog = RatingSystemDialog(self.root, self.current_rating_system, self.db_manager)
            new_system = dialog.show()
            
            if new_system and new_system != self.current_rating_system:
                # Update current system
                self.current_rating_system = new_system
                self.rating_config = RATING_SYSTEMS[new_system]
                self.color_map = self.rating_config['color_map']
                self.rating_range = self.rating_config['range']
                
                # Save preference
                self.settings_manager.set_rating_system(new_system)
                
                # Update grid colors immediately
                self.update_grid_colors()
                
                # Update status bar
                self.update_status_bar()
                
                # Show success message
                messagebox.showinfo("Rating System Updated", 
                                  f"Rating system changed to: {self.rating_config['name']}\n\n"
                                  f"Range: {self.rating_range[0]}-{self.rating_range[1]}\n"
                                  f"Colors updated throughout the application.")
                
        except Exception as e:
            print(f"Error configuring rating system: {e}")
            messagebox.showerror("Error", f"Failed to configure rating system: {e}")
    
    def show_data_management_menu(self):
        """Show a popup menu with data management options."""
        import tkinter as tk
        from tkinter import messagebox
        
        try:
            # Create popup menu window with wider layout for 2x2 grid
            menu_window = tk.Toplevel(self.root)
            menu_window.title("Data Management")
            menu_window.geometry("650x550")
            menu_window.resizable(False, False)
            
            # Center the window
            menu_window.transient(self.root)
            menu_window.grab_set()
            
            # Position relative to main window
            x = self.root.winfo_x() + 50
            y = self.root.winfo_y() + 50
            menu_window.geometry(f"+{x}+{y}")
            
            # Title label
            title_label = tk.Label(menu_window, text="Data Management", 
                                 font=("Arial", 16, "bold"), bg="lightcyan", pady=10)
            title_label.pack(fill=tk.X, padx=10, pady=(10, 15))
            
            # Create main frame for 2x2 grid layout
            main_frame = tk.Frame(menu_window, bg="white")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
            
            # Configure grid weights for equal distribution
            main_frame.grid_columnconfigure(0, weight=1)
            main_frame.grid_columnconfigure(1, weight=1)
            main_frame.grid_rowconfigure(0, weight=1)
            main_frame.grid_rowconfigure(1, weight=1)
            
            # TOP LEFT: Import & Export section
            import_export_frame = tk.Frame(main_frame, bg="lightblue", relief=tk.RAISED, borderwidth=2)
            import_export_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            
            import_export_label = tk.Label(import_export_frame, text="Import & Export", 
                                         font=("Arial", 12, "bold"), fg="darkblue", bg="lightblue")
            import_export_label.pack(pady=(10, 5))
            
            tk.Button(import_export_frame, text="Import CSV", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.import_csvs),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(import_export_frame, text="Export CSV", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.export_csvs),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(import_export_frame, text="Import XLSX", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.import_xlsx),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(import_export_frame, text="Export XLSX", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.export_xlsx),
                     relief=tk.RAISED, borderwidth=1).pack(pady=(3, 10))
            
            # TOP RIGHT: Data Management section
            data_mgmt_frame = tk.Frame(main_frame, bg="lightgreen", relief=tk.RAISED, borderwidth=2)
            data_mgmt_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
            
            data_mgmt_label = tk.Label(data_mgmt_frame, text="Data Management", 
                                     font=("Arial", 12, "bold"), fg="darkgreen", bg="lightgreen")
            data_mgmt_label.pack(pady=(10, 5))
            
            tk.Button(data_mgmt_frame, text="Load Grid", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.load_grid_data_from_db),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(data_mgmt_frame, text="Get Score", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.on_scenario_calculations),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(data_mgmt_frame, text="Refresh UI", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.update_ui),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(data_mgmt_frame, text="Preferences", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.show_preferences_dialog),
                     relief=tk.RAISED, borderwidth=1).pack(pady=(3, 10))
            
            # BOTTOM LEFT: Team Management section
            team_mgmt_frame = tk.Frame(main_frame, bg="lightyellow", relief=tk.RAISED, borderwidth=2)
            team_mgmt_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            
            team_mgmt_label = tk.Label(team_mgmt_frame, text="Team Management", 
                                     font=("Arial", 12, "bold"), fg="darkorange", bg="lightyellow")
            team_mgmt_label.pack(pady=(10, 5))
            
            tk.Button(team_mgmt_frame, text="Create Team", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.on_create_team),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(team_mgmt_frame, text="Delete Team", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.on_delete_team),
                     relief=tk.RAISED, borderwidth=1).pack(pady=(3, 10))
            
            # BOTTOM RIGHT: Database section
            database_frame = tk.Frame(main_frame, bg="mistyrose", relief=tk.RAISED, borderwidth=2)
            database_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
            
            print("Adding Database section to menu...")  # Debug output
            db_label = tk.Label(database_frame, text="Database & Settings", 
                              font=("Arial", 12, "bold"), fg="darkred", bg="mistyrose")
            db_label.pack(pady=(10, 5))
            
            change_db_button = tk.Button(database_frame, text="Change Database", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.on_change_database),
                     relief=tk.RAISED, borderwidth=1)
            change_db_button.pack(pady=3)
            
            rating_system_button = tk.Button(database_frame, text="Rating System", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.on_configure_rating_system),
                     relief=tk.RAISED, borderwidth=1, bg="lightpink")
            rating_system_button.pack(pady=3)
            
            cache_stats_button = tk.Button(database_frame, text="Cache Statistics", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.show_cache_statistics),
                     relief=tk.RAISED, borderwidth=1, bg="lightsteelblue")
            cache_stats_button.pack(pady=(3, 10))
            print("Database section added successfully!")  # Debug output
            
            # Close button frame at the bottom
            close_frame = tk.Frame(menu_window)
            close_frame.pack(pady=10)
            
            close_button = tk.Button(close_frame, text="Close", width=30, height=2,
                                   command=menu_window.destroy,
                                   bg="lightcoral", fg="white", font=("Arial", 10, "bold"),
                                   relief=tk.RAISED, borderwidth=2)
            close_button.pack()
            
            print("Data Management menu created successfully with all sections!")  # Debug output
            
        except Exception as e:
            print(f"Error showing data management menu: {e}")
            messagebox.showerror("Error", f"Failed to show data management menu: {e}")
    
    def _menu_action(self, menu_window, action_func):
        """Execute menu action and close menu window."""
        try:
            menu_window.destroy()  # Close menu first
            action_func()  # Then execute the action
        except Exception as e:
            print(f"Error executing menu action: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to execute action: {e}")
    
    def export_xlsx(self):
        """Export data to XLSX format - placeholder implementation."""
        from tkinter import messagebox
        try:
            # TODO: Implement XLSX export functionality
            messagebox.showinfo("Export XLSX", "XLSX export functionality will be implemented in a future update.")
        except Exception as e:
            print(f"Error exporting XLSX: {e}")
            messagebox.showerror("Error", f"Failed to export XLSX: {e}")
    
    def on_generate_combinations(self):
        fNames, oNames = self.prep_names()
        fRatings, oRatings = self.prep_ratings(fNames,oNames)
        if self.print_output:
            print(f"fRatings: {fRatings}\n")
            print(f"oRatings: {oRatings}\n")
        
        # TEMPORARILY DISABLED - Validate that all 25 ratings are present before generating combinations
        # if not self.validate_complete_ratings(fRatings, oRatings, fNames, oNames):
        #     return  # Validation failed, don't generate combinations
            
        self.validate_grid_data()
        if self.team_b.get():
            self.tree_generator.generate_combinations(fNames, oNames, fRatings, oRatings, our_team_first=True)
        else:
            self.tree_generator.generate_combinations(oNames, fNames, oRatings, fRatings, our_team_first=False)
        
        # Reset all sorting states when generating new combinations
        self.active_sort_mode = None
        self.is_sorted = False
        self.current_sort_mode = "none"
        self.treeview.tree.heading("Rating", text="Rating")
        self.update_sort_value_column()
        self.update_sort_button_states()
        
    def sort_by_confidence(self):
        """Sort tree by risk-adjusted confidence scores"""
        self.tree_generator.sort_by_risk_adjusted_confidence()
        self.current_sort_mode = "confidence"
        self.active_sort_mode = "confidence"
        self.treeview.tree.heading("Rating", text="Confidence Score")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()

    def sort_by_counter_resistance(self):
        """Sort tree by counter-resistance against opponent strategies"""
        self.tree_generator.sort_by_opponent_response_simulation()
        self.current_sort_mode = "resistance"
        self.active_sort_mode = "resistance"
        self.treeview.tree.heading("Rating", text="Resistance Score")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()

    def sort_by_strategic_optimal(self):
        """Sort tree by strategic optimal expected value"""
        self.tree_generator.sort_by_strategic_optimal()
        self.current_sort_mode = "strategic"
        self.active_sort_mode = "strategic"
        self.treeview.tree.heading("Rating", text="Strategic EV")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()

    def sort_by_cumulative(self):
        """Sort tree by cumulative value"""
        self.tree_generator.sort_by_cumulative_value()
        self.current_sort_mode = "cumulative"
        self.active_sort_mode = "cumulative"
        self.treeview.tree.heading("Rating", text="Cumulative Value")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()
    
    def unsort_tree(self):
        """Remove all sorting and return to default order"""
        self.tree_generator.unsort_tree()
        self.current_sort_mode = "none"
        self.active_sort_mode = None
        self.treeview.tree.heading("Rating", text="Rating")
        self.update_sort_value_column()
        self.is_sorted = False
        self.update_sort_button_states()
    
    def toggle_cumulative_sort(self):
        """Toggle cumulative sorting on/off"""
        if self.active_sort_mode == "cumulative":
            self.unsort_tree()
        else:
            self.sort_by_cumulative()
    
    def toggle_confidence_sort(self):
        """Toggle confidence sorting on/off"""
        if self.active_sort_mode == "confidence":
            self.unsort_tree()
        else:
            self.sort_by_confidence()
    
    def toggle_counter_sort(self):
        """Toggle counter-resistance sorting on/off"""
        if self.active_sort_mode == "resistance":
            self.unsort_tree()
        else:
            self.sort_by_counter_resistance()

    def toggle_strategic_optimal_sort(self):
        """Toggle strategic optimal sorting on/off"""
        if self.active_sort_mode == "strategic":
            self.unsort_tree()
        else:
            self.sort_by_strategic_optimal()
    
    def update_sort_button_states(self):
        """Update button appearance to show active/inactive states"""
        try:
            # Reset all buttons to inactive state with gray background and dim circle
            self.cumulative_button.config(text="⚫ Cumulative\nSort", relief=tk.RAISED, bg='lightgray', fg='black')
            self.confidence_button.config(text="⚫ Highest\nConfidence", relief=tk.RAISED, bg='lightgray', fg='black')
            self.counter_button.config(text="⚫ Counter\nPick", relief=tk.RAISED, bg='lightgray', fg='black')
            self.strategic_button.config(text="⚫ Strategic\nOptimal", relief=tk.RAISED, bg='lightgray', fg='black')
            
            # Set active button to bright green with pressed appearance
            if self.active_sort_mode == "cumulative":
                self.cumulative_button.config(text="� ACTIVE\nCumulative", relief=tk.SUNKEN, bg='lightgreen', fg='darkgreen')
            elif self.active_sort_mode == "confidence":
                self.confidence_button.config(text="� ACTIVE\nConfidence", relief=tk.SUNKEN, bg='lightgreen', fg='darkgreen')
            elif self.active_sort_mode == "resistance":
                self.counter_button.config(text="� ACTIVE\nCounter Pick", relief=tk.SUNKEN, bg='lightgreen', fg='darkgreen')
            elif self.active_sort_mode == "strategic":
                self.strategic_button.config(text="� ACTIVE\nStrategic", relief=tk.SUNKEN, bg='lightgreen', fg='darkgreen')
                
        except Exception as e:
            print(f"ERROR updating sort button states: {e}")
            # Fallback to very basic text-only updates
            try:
                if self.active_sort_mode == "cumulative":
                    self.cumulative_button.config(text="[ACTIVE]\nCumulative")
                elif self.active_sort_mode == "confidence":
                    self.confidence_button.config(text="[ACTIVE]\nConfidence")
                elif self.active_sort_mode == "resistance":
                    self.counter_button.config(text="[ACTIVE]\nCounter Pick")
                elif self.active_sort_mode == "strategic":
                    self.strategic_button.config(text="[ACTIVE]\nStrategic")
                else:
                    # All inactive
                    self.cumulative_button.config(text="Cumulative\nSort")
                    self.confidence_button.config(text="Highest\nConfidence")
                    self.counter_button.config(text="Counter\nPick")
                    self.strategic_button.config(text="Strategic\nOptimal")
            except Exception as e2:
                print(f"ERROR: Fallback button update also failed: {e2}")

    def update_scenario_box(self):
        scenarios = []
        if self.scenario_map:
            for scenario in self.scenario_map.values():
                # if self.print_output:print(scenario)
                scenarios.append(scenario)
            self.scenario_box['values'] = scenarios
        else:
            self.scenario_box['values'] = ("1 - Recon","2 - Battle Lines","3 - Wolves At Our Heels","4 - Payload","5 - Two Fronts","6 - Invasion")

    def on_scenario_box_change(self, *args):
        # Get the new value
        new_value = self.scenario_var.get()
        # Compare with the previous value
        if new_value != self.previous_value:
            print(f"🔧 DEBUG: Scenario changed from '{self.previous_value}' to '{new_value}'")
            self.previous_value = new_value
            try:
                print(f"🔧 DEBUG: About to call update_ui() for scenario change")
                self.update_ui()
                print(f"🔧 DEBUG: update_ui() completed, now calling on_scenario_calculations()")
                # Trigger scenario calculations to populate the right grid
                self.on_scenario_calculations()
                print(f"🔧 DEBUG: on_scenario_calculations() completed for scenario change")
            except (ValueError, IndexError) as e:
                print(f"scenario_box_change error: {e}")

    def _is_valid_team_selection(self, team_name):
        """Check if team name is valid for database operations."""
        if not team_name:
            return False
        if team_name.strip() == '':
            return False
        if team_name == 'No teams Found':
            return False
        return True

    def _are_both_teams_selected(self):
        """Check if both teams are selected and valid."""
        team1 = self.team1_var.get() if hasattr(self, 'team1_var') else ""
        team2 = self.team2_var.get() if hasattr(self, 'team2_var') else ""
        
        return (self._is_valid_team_selection(team1) and 
                self._is_valid_team_selection(team2) and 
                team1 != team2)

    def _teams_changed_meaningfully(self, new_team1, new_team2):
        """Check if team change warrants a database reload."""
        old_team1 = getattr(self, 'previous_team1', '')
        old_team2 = getattr(self, 'previous_team2', '')
        
        print(f"🔧 DEBUG: _teams_changed_meaningfully check:")
        print(f"🔧 DEBUG:   New teams: '{new_team1}' vs '{new_team2}'")
        print(f"🔧 DEBUG:   Old teams: '{old_team1}' vs '{old_team2}'")
        print(f"🔧 DEBUG:   Team1 valid: {self._is_valid_team_selection(new_team1)}")
        print(f"🔧 DEBUG:   Team2 valid: {self._is_valid_team_selection(new_team2)}")
        print(f"🔧 DEBUG:   Teams different: {new_team1 != new_team2}")
        
        # If both teams are valid now and at least one changed
        if (self._is_valid_team_selection(new_team1) and 
            self._is_valid_team_selection(new_team2) and 
            new_team1 != new_team2):
            
            team_changed = (new_team1 != old_team1 or new_team2 != old_team2)
            print(f"🔧 DEBUG:   At least one team changed: {team_changed}")
            
            if team_changed:
                print(f"🔧 DEBUG:   Meaningful change detected - returning True")
                return True
        
        print(f"🔧 DEBUG:   No meaningful change - returning False")
        return False

    def _safe_get_int_from_grid(self, row: int, col: int, default: Optional[int] = 0) -> Optional[int]:
        """Safely extract integer value from grid, handling empty strings."""
        try:
            value = self.grid_entries[row][col].get()
            if not value or value.strip() == '':
                return default
            return int(value)
        except (ValueError, IndexError):
            return default

    def _clear_grid_calculations(self):
        """Clear all calculated display fields when teams are invalid."""
        try:
            for row in range(1, 6):
                for col in range(1, 6):
                    # Clear the display grid calculations
                    if hasattr(self, 'grid_display_entries'):
                        self.grid_display_entries[row][col].set('')
        except Exception as e:
            if self.print_output:
                print(f"Error clearing grid calculations: {e}")

    def on_team_box_change(self, *args):
        """Handle team dropdown changes with proper validation."""
        print(f"🔧 DEBUG: on_team_box_change() called with args: {args}")
        
        # Get the new values
        new_team1_value = self.team1_var.get()
        new_team2_value = self.team2_var.get()
        
        print(f"🔧 DEBUG: Team values - Team1: '{new_team1_value}', Team2: '{new_team2_value}'")
        
        # Track if either value changed
        team1_changed = new_team1_value != getattr(self, 'previous_team1', '')
        team2_changed = new_team2_value != getattr(self, 'previous_team2', '')
        
        print(f"🔧 DEBUG: Previous values - Team1: '{getattr(self, 'previous_team1', '')}', Team2: '{getattr(self, 'previous_team2', '')}'")
        print(f"🔧 DEBUG: Changes detected - Team1: {team1_changed}, Team2: {team2_changed}")
        
        # Only proceed if something actually changed
        if not (team1_changed or team2_changed):
            print(f"🔧 DEBUG: No meaningful changes detected, returning early")
            return
        
        # If we don't have both teams selected validly, clear calculations and return
        if not self._are_both_teams_selected():
            print(f"🔧 DEBUG: Teams not ready for database operations: '{new_team1_value}' vs '{new_team2_value}'")
            
            # Update tracking variables after clearing
            self.previous_team1 = new_team1_value
            self.previous_team2 = new_team2_value
            
            # Clear any existing grid calculations
            self._clear_grid_calculations()
            
            # Clear comment indicators
            if hasattr(self, 'clear_comment_indicators'):
                self.clear_comment_indicators()
            
            return
        
        # Check if this change actually warrants a database reload (BEFORE updating previous values)
        if not self._teams_changed_meaningfully(new_team1_value, new_team2_value):
            print(f"🔧 DEBUG: Team change not meaningful enough for database reload")
            # Update tracking variables even if not meaningful
            self.previous_team1 = new_team1_value
            self.previous_team2 = new_team2_value
            return
        
        # Update tracking variables after meaningful change detected
        self.previous_team1 = new_team1_value
        self.previous_team2 = new_team2_value
        
        # Now we know both teams are valid and different - safe to proceed
        try:
            print(f"🔧 DEBUG: Both teams selected: '{new_team1_value}' vs '{new_team2_value}'")
            
            # Update round dropdowns when team changes (do this first)
            print(f"🔧 DEBUG: About to call update_round_dropdown_options()")
            self.update_round_dropdown_options()
            print(f"🔧 DEBUG: update_round_dropdown_options() completed")
            
            # Automatically set scenario to 0 when both teams are selected
            # This will trigger on_scenario_box_change which will handle the rest of the flow
            if hasattr(self, 'scenario_var') and hasattr(self, 'scenario_box'):
                current_scenario = self.scenario_var.get()
                print(f"🔧 DEBUG: Current scenario value: '{current_scenario}'")
                
                # Always ensure the dropdown shows '0 - Neutral' visually
                target_scenario = '0 - Neutral'
                
                # First ensure the dropdown values are populated
                self.update_scenario_box()
                
                # Force the combobox to update its display
                if hasattr(self.scenario_box, 'current'):
                    try:
                        # Find the index of '0 - Neutral' in the values
                        values = self.scenario_box['values']
                        print(f"🔧 DEBUG: Available scenario values: {values}")
                        if target_scenario in values:
                            index = list(values).index(target_scenario)
                            self.scenario_box.current(index)
                            print(f"🔧 DEBUG: Set dropdown display to show '{target_scenario}' at index {index}")
                        else:
                            print(f"🔧 DEBUG: Target scenario '{target_scenario}' not found in values: {values}")
                    except Exception as e:
                        print(f"🔧 DEBUG: Error setting dropdown display: {e}")
                
                if current_scenario != target_scenario:
                    print(f"🔧 DEBUG: Setting scenario from '{current_scenario}' to '{target_scenario}' - this will trigger scenario change handler")
                    self.scenario_var.set(target_scenario)
                    print(f"🔧 DEBUG: Scenario set - scenario change handler should now be triggered automatically")
                else:
                    print(f"🔧 DEBUG: Scenario already set to '{target_scenario}', manually triggering scenario calculations")
                    # If scenario is already set to neutral, we need to manually trigger the calculations
                    # since changing to the same value won't trigger the trace
                    self.on_scenario_calculations()
            else:
                print(f"🔧 DEBUG: WARNING - scenario_var or scenario_box not available")
            
        except Exception as e:
            if self.print_output:
                print(f'team_box_change ERROR: {e}')
            # Clear grid on error to prevent partial/invalid state
            self._clear_grid_calculations()
            
    

    ####################
    # DB Fill/Save Funcs
    ####################

    def update_ui(self):
        # Update the team dropdowns and grid values
        self.set_team_dropdowns()
        # Ensure display headers are always visible
        self.init_display_headers()
        self.load_grid_data_from_db()
        # print(self.extract_ratings())

    def select_team_names(self):
        """Get team names using cache (eliminates database query)"""
        # Check if data_cache is initialized
        if not hasattr(self, 'data_cache') or self.data_cache is None:
            if self.print_output:
                print("⚠️ Data cache not initialized, falling back to direct database query")
            # Fallback to direct database query
            if hasattr(self, 'db_manager') and self.db_manager is not None:
                try:
                    result = self.db_manager.query_sql("SELECT team_name FROM teams ORDER BY team_name")
                    team_names = [row[0] for row in result] if result else []
                    if self.print_output:
                        print(f"📋 Retrieved {len(team_names)} team names from database (fallback)")
                    return team_names
                except Exception as e:
                    if self.print_output:
                        print(f"❌ Error getting team names from database: {e}")
                    return []
            else:
                if self.print_output:
                    print("❌ No database manager available")
                return []
        
        team_names = self.data_cache.get_team_names()
        if self.print_output:
            print(f"📋 Retrieved {len(team_names)} team names from cache")
        return team_names

    def set_team_dropdowns(self):
        team_names = self.select_team_names()
        self.combobox_1['values'] = team_names
        self.combobox_2['values'] = team_names

    def load_grid_data_from_db(self):
        """Load grid data using high-performance cache (eliminates 15-20 database queries)"""
        team_1 = self.combobox_1.get()
        team_2 = self.combobox_2.get()
        scenario = self.scenario_box.get()[:1]
        if scenario == '':
            self.scenario_box.set("0 - Neutral")
            scenario = self.scenario_box.get()[:1]
        scenario_id = int(scenario)

        if self.print_output:
            print(f"🚀 Loading grid data for {team_1} vs {team_2}, scenario {scenario_id}")

        # Get all data from cache in one call (replaces 15-20 database queries)
        if hasattr(self, 'data_cache') and self.data_cache is not None:
            try:
                cached_data = self.data_cache.get_cached_grid_data(team_1, team_2, scenario_id)
                if not cached_data:
                    if self.print_output:
                        print("⚠️ Cache miss, falling back to direct database queries")
                    cached_data = self._load_grid_data_direct(team_1, team_2, scenario_id)
            except Exception as cache_error:
                if self.print_output:
                    print(f"❌ Cache error: {cache_error}, falling back to direct database queries")
                cached_data = self._load_grid_data_direct(team_1, team_2, scenario_id)
        else:
            if self.print_output:
                print("⚠️ Data cache not available, using direct database queries")
            # Fallback to direct database queries
            cached_data = self._load_grid_data_direct(team_1, team_2, scenario_id)
            if not cached_data:
                if self.print_output:
                    print("❌ Direct database query also failed")
                return
        
        if not cached_data:
            if self.print_output:
                print(f"❌ Unable to load data for teams '{team_1}' and '{team_2}'")
            return

        team_1_id = cached_data['team1_id']
        team_2_id = cached_data['team2_id']
        team_1_players = cached_data['team1_players']
        team_2_players = cached_data['team2_players']
        ratings = cached_data['ratings']

        # Convert to dictionaries for position mapping (same logic as before)
        team_1_dict = {row[0]:{'position':i+1,'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {row[0]:{'position':i+1,'name':row[1]} for i,row in enumerate(team_2_players)}

        # Update usernames in grid
        for _, row_dict in team_2_dict.items():
            pos = row_dict['position']
            if 0 <= pos < len(self.grid_entries[0]):
                self.grid_entries[0][pos].set(row_dict['name'])
        
        for _, row_dict in team_1_dict.items():
            pos = row_dict['position']
            if 0 <= pos < len(self.grid_entries):
                self.grid_entries[pos][0].set(row_dict['name'])

        # Update ratings in grid using cached data
        for (player1_id, player2_id), rating in ratings.items():
            if player1_id in team_1_dict and player2_id in team_2_dict:
                team_1_pos = team_1_dict[player1_id]['position']
                team_2_pos = team_2_dict[player2_id]['position']
                if (0 <= team_1_pos < len(self.grid_entries) and 
                    0 <= team_2_pos < len(self.grid_entries[0])):
                    self.grid_entries[team_1_pos][team_2_pos].set(rating)
        
        if self.print_output:
            total_ratings = len(ratings)
            print(f"✅ Loaded {len(team_1_players)} vs {len(team_2_players)} players with {total_ratings} ratings from cache")
        
        # Update comment indicators after loading grid data
        self.update_comment_indicators()
        
        # Always trigger scenario calculations to populate the right grid
        print(f"🔧 DEBUG: About to call on_scenario_calculations() from load_grid_data_from_db()")
        self.on_scenario_calculations()
        print(f"🔧 DEBUG: on_scenario_calculations() completed from load_grid_data_from_db()")
        
        # Auto-generate combinations if grid is properly populated
        if self.should_auto_generate_combinations():
            try:
                self.on_generate_combinations()
                if self.print_output:
                    print("Auto-generated combinations after loading grid data")
            except Exception as e:
                if self.print_output:
                    print(f"Auto-generation failed: {e}")
        
    def should_auto_generate_combinations(self):
        """Check if conditions are met for auto-generating combinations"""
        # Check if both teams are selected and different
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()
        
        if not team_1 or not team_2 or team_1 == team_2:
            return False
            
        if team_1 == 'No teams Found' or team_2 == 'No teams Found':
            return False
        
        # Check if we have player names in the grid
        friendly_names = self.get_friendly_player_names()
        opponent_names = self.get_opponent_player_names()
        
        # Need at least some player names
        if not any(name.strip() for name in friendly_names) or not any(name.strip() for name in opponent_names):
            return False
        
        # Check if we have at least some ratings data (not requiring all cells to be filled)
        has_ratings = False
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get().strip()
                if value and value != '0':  # Consider non-zero ratings as valid data
                    has_ratings = True
                    break
            if has_ratings:
                break
        
        return has_ratings
    
    def _load_grid_data_direct(self, team_1, team_2, scenario_id):
        """Direct database fallback when cache is not available"""
        print(f"🔄 FALLBACK MODE: Attempting direct database queries for {team_1} vs {team_2}, scenario {scenario_id}")
        try:
            if not hasattr(self, 'db_manager') or self.db_manager is None:
                error_msg = "No database manager available for direct queries"
                print(f"❌ FALLBACK FAILED: {error_msg}")
                return None
            
            # Get team IDs
            print(f"🔍 FALLBACK: Looking up team IDs for '{team_1}' and '{team_2}'")
            team_sql_template = "select team_id from teams where team_name='{team_name}'"
            
            team_1_sql = team_sql_template.format(team_name=team_1)
            print(f"🔍 FALLBACK: Executing query: {team_1_sql}")
            team_1_row = self.db_manager.query_sql(team_1_sql)
            if not team_1_row:
                error_msg = f"Team '{team_1}' not found in database"
                print(f"❌ FALLBACK FAILED: {error_msg}")
                return None
            team_1_id = team_1_row[0][0]
            print(f"✅ FALLBACK: Found {team_1} with ID {team_1_id}")

            team_2_sql = team_sql_template.format(team_name=team_2)
            print(f"🔍 FALLBACK: Executing query: {team_2_sql}")
            team_2_row = self.db_manager.query_sql(team_2_sql)
            if not team_2_row:
                error_msg = f"Team '{team_2}' not found in database"
                print(f"❌ FALLBACK FAILED: {error_msg}")
                return None
            team_2_id = team_2_row[0][0]
            print(f"✅ FALLBACK: Found {team_2} with ID {team_2_id}")

            # Get players
            print(f"🔍 FALLBACK: Looking up players for teams {team_1_id} and {team_2_id}")
            player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
            
            team_1_player_sql = player_sql_template.format(team_id=team_1_id)
            print(f"🔍 FALLBACK: Executing query: {team_1_player_sql}")
            team_1_players = self.db_manager.query_sql(team_1_player_sql)
            print(f"✅ FALLBACK: Found {len(team_1_players) if team_1_players else 0} players for {team_1}")
            
            team_2_player_sql = player_sql_template.format(team_id=team_2_id)
            print(f"🔍 FALLBACK: Executing query: {team_2_player_sql}")
            team_2_players = self.db_manager.query_sql(team_2_player_sql)
            print(f"✅ FALLBACK: Found {len(team_2_players) if team_2_players else 0} players for {team_2}")

            # Get ratings
            ratings_sql = f"""
                SELECT p1.player_id, p2.player_id, r.rating 
                FROM ratings r
                JOIN players p1 ON r.team_1_player_id = p1.player_id
                JOIN players p2 ON r.team_2_player_id = p2.player_id
                WHERE p1.team_id = {team_1_id} AND p2.team_id = {team_2_id} AND r.scenario_id = {scenario_id}
            """
            print(f"🔍 FALLBACK: Executing ratings query: {ratings_sql}")
            ratings_rows = self.db_manager.query_sql(ratings_sql)
            print(f"✅ FALLBACK: Found {len(ratings_rows) if ratings_rows else 0} ratings for scenario {scenario_id}")
            
            # Convert ratings to dictionary format
            ratings = {}
            if ratings_rows:
                for row in ratings_rows:
                    ratings[(row[0], row[1])] = row[2]

            result = {
                'team1_id': team_1_id,
                'team2_id': team_2_id,
                'team1_players': team_1_players,
                'team2_players': team_2_players,
                'ratings': ratings
            }
            
            print(f"✅ FALLBACK SUCCESS: Returning data with {len(ratings)} ratings")
            return result
            
        except Exception as e:
            error_msg = f"Error in direct database query: {e}"
            print(f"❌ FALLBACK FAILED: {error_msg}")
            print(f"📊 Exception type: {type(e).__name__}")
            import traceback
            print(f"📊 Full traceback: {traceback.format_exc()}")
            return None
    
    def _get_team_ids_direct(self, team_1, team_2):
        """Get team IDs directly from database"""
        try:
            if not hasattr(self, 'db_manager') or self.db_manager is None:
                return None
            
            team_sql_template = "select team_id from teams where team_name='{team_name}'"
            
            team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
            if not team_1_row:
                return None
            team_1_id = team_1_row[0][0]

            team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
            if not team_2_row:
                return None
            team_2_id = team_2_row[0][0]
            
            return (team_1_id, team_2_id)
            
        except Exception as e:
            if self.print_output:
                print(f"❌ Error getting team IDs: {e}")
            return None
    
    def _get_team_players_direct(self, team_id):
        """Get team players directly from database"""
        try:
            if not hasattr(self, 'db_manager') or self.db_manager is None:
                return []
            
            player_sql = f"SELECT player_id, player_name FROM players WHERE team_id={team_id} ORDER BY player_id"
            players = self.db_manager.query_sql(player_sql)
            return players if players else []
            
        except Exception as e:
            if self.print_output:
                print(f"❌ Error getting team players: {e}")
            return []
        
    def save_grid_data_to_db(self):
        """Save grid data to database using cache for team lookups and keeping cache synchronized"""
        # Prevent saving when grid is flipped to opponent's perspective
        if self.grid_is_flipped:
            messagebox.showwarning("Cannot Save", 
                "Cannot save data while grid is flipped to opponent's perspective.\n"
                "Please click 'Flip Grid' again to restore friendly perspective before saving.")
            return
            
        team_1 = self.combobox_1.get()
        team_2 = self.combobox_2.get()
        scenario_id = int(self.scenario_box.get()[:1])

        if self.print_output:
            print(f"💾 Saving grid data for {team_1} vs {team_2}, scenario {scenario_id}")

        # Get team IDs from cache (eliminates 2 database queries)
        if hasattr(self, 'data_cache') and self.data_cache is not None:
            team_1_id = self.data_cache.get_team_id(team_1)
            team_2_id = self.data_cache.get_team_id(team_2)
        else:
            if self.print_output:
                print("⚠️ Data cache not available, using direct database queries for save")
            # Fallback to direct database queries
            team_ids = self._get_team_ids_direct(team_1, team_2)
            if not team_ids:
                if self.print_output:
                    print("❌ Could not get team IDs from database")
                return
            team_1_id, team_2_id = team_ids

        if team_1_id is None:
            print(f"Team '{team_1}' not found in cache")
            return
        if team_2_id is None:
            print(f"Team '{team_2}' not found in cache")
            return

        # Get players from cache (eliminates 2 more database queries)
        if hasattr(self, 'data_cache') and self.data_cache is not None:
            team_1_players = self.data_cache.get_team_players(team_1_id)
            team_2_players = self.data_cache.get_team_players(team_2_id)
        else:
            # Fallback to direct database queries
            team_1_players = self._get_team_players_direct(team_1_id)
            team_2_players = self._get_team_players_direct(team_2_id)

        team_1_dict = {i+1:{'id':row[0],'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {i+1:{'id':row[0],'name':row[1]} for i,row in enumerate(team_2_players)}

        saved_count = 0
        for row in range(1, len(self.grid_entries)):
            for col in range(1, len(self.grid_entries[0])):
                try:
                    rating = int(self.grid_entries[row][col].get())
                    team_1_player_id = team_1_dict[row]['id']
                    team_2_player_id = team_2_dict[col]['id']
                    
                    # Save to database
                    self.db_manager.upsert_rating(
                        player_id_1=team_1_player_id,
                        player_id_2=team_2_player_id,
                        team_id_1=team_1_id,
                        team_id_2=team_2_id,
                        scenario_id=scenario_id,
                        rating=rating
                    )
                    
                    # Update cache to keep it synchronized (if available)
                    if hasattr(self, 'data_cache') and self.data_cache is not None:
                        self.data_cache.update_cached_rating(
                            team_1_id, team_2_id, scenario_id,
                            team_1_player_id, team_2_player_id, rating
                        )
                    
                    saved_count += 1
                    
                except (ValueError, IndexError) as e:
                    if self.print_output:
                        print(f"Error saving rating at [{row}, {col}]: {e}")
                    continue

        if self.print_output:
            print(f"✅ Saved {saved_count} ratings and updated cache")

    def add_team_to_db(self):
        # Use the main window as parent for the dialog
        team_name = simpledialog.askstring("Input", "Enter the team name:", parent=self.root)
        if team_name:
            self.db_manager.create_team(team_name)
            # Refresh cache after adding team
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                self.data_cache.refresh_base_data()
        self.update_ui()

    def create_team(self):
        """Create a new team using the Create Team Wizard dialog"""
        # Fetch existing team names to check for duplicates
        existing_team_names = self.select_team_names()

        # Create and display the create team dialog using existing root
        dialog = CreateTeamDialog(self.root, existing_team_names)
        result = dialog.show()

        if result is None:
            return  # User cancelled the operation

        team_name = result["team_name"]
        player_names = result["player_names"]

        try:
            # Check if team already exists
            team_exists = team_name in existing_team_names
            
            if team_exists:
                # Update existing team's players
                team_id = self.db_manager.query_team_id(team_name)
                
                if team_id is None:
                    raise RuntimeError(f"Could not find team ID for existing team '{team_name}'")
                
                # Delete existing players for this team using secure method
                secure_db = self.db_manager.get_secure_interface()
                secure_db.delete_players_for_team_secure(team_id)
                
                # Insert new players
                for player_name in player_names:
                    self.db_manager.create_player(player_name, team_id)
                    
                messagebox.showinfo("Success", 
                                  f"Team '{team_name}' has been updated successfully!\n\n"
                                  f"Players updated:\n" + "\n".join([f"• {name}" for name in player_names]))
            else:
                # Create new team
                team_id = self.db_manager.upsert_team(team_name)
                
                # Create players
                for player_name in player_names:
                    self.db_manager.create_player(player_name, team_id)
                    
                messagebox.showinfo("Success", 
                                  f"Team '{team_name}' has been created successfully!\n\n"
                                  f"Players added:\n" + "\n".join([f"• {name}" for name in player_names]))

            # Refresh cache after team/player changes
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                self.data_cache.refresh_base_data()

            # Update UI like successful CSV import
            self.set_team_dropdowns()
            self.update_ui()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create/update team: {str(e)}")
            print(f"create_team error: {e}")

    def delete_team(self):
        # Fetch existing team names
        team_names = self.select_team_names()

        # Create and display the delete team dialog using existing root
        dialog = DeleteTeamDialog(self.root, team_names)
        self.root.wait_window(dialog.top)

        team_name = dialog.selected_team
        if team_name is None:
            return  # User cancelled the operation

        # Validate the user's input
        if team_name not in team_names:
            messagebox.showerror("Error", f"Invalid team name: {team_name}")
            return

        # Use secure delete method
        try:
            secure_db = self.db_manager.get_secure_interface()
            success = secure_db.delete_team_secure(team_name)
            
            if not success:
                messagebox.showerror("Error", f"Team not found: '{team_name}'")
                return
        except (ValueError, RuntimeError) as e:
            messagebox.showerror("Error", f"Failed to delete team: {e}")
            return

        messagebox.showinfo("Success", f"Team '{team_name}' and all related records have been deleted successfully.")
        
        # Refresh cache after team deletion
        if hasattr(self, 'data_cache') and self.data_cache is not None:
            self.data_cache.refresh_base_data()
        
        try:
            self.set_team_dropdowns()
            self.update_ui
        except (ValueError, IndexError) as e:
            print(f"delete_team caused an error trying to update the UI: {e}")

    def import_xlsx(self):
        """Import Excel file using the new simple format"""
        # Let user select the Excel file
        file_path = filedialog.askopenfilename(
            title="Select Excel File for Import",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # Extract filename without extension for team name
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Create and execute the simple importer
            simple_importer = SimpleExcelImporter(
                db_manager=self.db_manager, 
                file_path=file_path, 
                scenario_id=0  # Default to neutral scenario
            )
            
            teams_imported = simple_importer.execute()
            
            # Show success message
            messagebox.showinfo(
                "Import Successful", 
                f"Successfully imported {teams_imported} teams from {file_name}"
            )
            
            # Refresh the UI to show the new data
            self.update_ui()
            
        except Exception as e:
            messagebox.showerror(
                "Import Error", 
                f"Failed to import Excel file:\n{str(e)}"
            )
            print(f"Excel import error: {e}")

    def export_csvs(self):
        print(f"Exporting Matchups to CSV")

        # Prompt the user to select a file location to save the CSV
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        # Retrieve data from the database
        team1_name, team1_players = self.retrieve_team_data(self.combobox_1.get())
        team2_name, team2_players = self.retrieve_team_data(self.combobox_2.get())
        ratings = self.retrieve_ratings(team1_players, team2_players)

        # Write data to CSV
        with open(file_path, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write headers
            writer.writerow([team1_name] + team1_players)
            writer.writerow([team2_name] + team2_players)

            # Write ratings
            for scenario_id, rating_data in ratings.items():
                writer.writerow([scenario_id] + team2_players)
                for player, player_ratings in rating_data.items():
                    writer.writerow([player] + player_ratings)

    def retrieve_team_data(self, team_name):
        team_id = self.db_manager.query_team_id(team_name)
        players = self.db_manager.query_sql(f"SELECT player_name FROM players WHERE team_id = {team_id} ORDER BY player_id")
        player_names = [player[0] for player in players]
        return team_name, player_names

    def retrieve_ratings(self, team1_players, team2_players):
        ratings = {}
        scenario_id = []        
        for scenario in range(0,6):
            
            scenario_id = scenario
            ratings[scenario_id] = {}
            for player1 in team1_players:
                player1_result = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player1}'")
                if not player1_result:
                    print(f"Player '{player1}' not found in database")
                    continue
                player1_id = player1_result[0][0]
                # print(f"player1 - {player1_id}: {player1}")
                player_ratings = []
                for player2 in team2_players:
                    player2_result = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player2}'")
                    if not player2_result:
                        print(f"Player '{player2}' not found in database")
                        player_ratings.append(0)
                        continue
                    player2_id = player2_result[0][0]
                    rating = self.db_manager.query_sql(f"""
                        SELECT rating FROM ratings
                        WHERE team_1_player_id = {player1_id} AND team_2_player_id = {player2_id} AND scenario_id = {scenario_id}
                    """)
                    player_ratings.append(rating[0][0] if rating else 0)  # Default to 0 if no rating found
                ratings[scenario_id][player1] = player_ratings

        return ratings


    
    def import_csvs(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            lines = list(reader)

        self.import_csv_header_and_ratings(lines)
        # self.import_csv_ratings(lines)
        self.update_ui()

    def import_csv_header_and_ratings(self, lines):
        # Only take the first two lines from the file.
        # CSV import should be exactly 44 lines if done correctly.
        # Let's allow it to be short, in case we don't want to import all 6 scenarios
        # print(f"file length={len(lines)}")
        if len(lines) < 44:
            raise ValueError("Insufficient number of lines")

        team_lines = lines[:2]
        rating_section = lines[2:]

        team_names = []
        team_name_1 = ""
        team_name_2 = ""
        player_names = []
        team_players_1 = []
        team_players_2 = []
        team_id_1 = 0
        team_id_2 = 0

        team_2_players_ids = {}

        for index, line in enumerate(team_lines):
            team_names.append(line[0])
            player_names.append(line[1:])

            # Try to upsert this team and the players.
            try:
                team_id = self.db_manager.upsert_team(line[0])
                players = self.db_manager.upsert_and_validate_players(team_id, player_names[index])
                
                # Set combobox values based on the index
                if index == 0:
                    team_name_1 = team_names[index]
                    self.combobox_1.set(team_name_1)
                    team_id_1 = team_id
                    team_players_1 = player_names[index]
                elif index == 1:
                    team_name_2 = team_names[index]
                    self.combobox_2.set(team_name_2)
                    team_id_2 = team_id
                    team_players_2 = player_names[index]
            except ValueError as e:
                print(f"import_csv_header_and_ratings ERROR - {e}")
                continue

        scenario_id = 0  # Initialize scenario_id
        team_2_players_ids = {}

        for line in rating_section:
            # if this line DOES NOT CONTAIN a friendly player followed by ratings
            # this line must contain scenario number followed by enemy player names
            rating_line = all(item.isdigit() for item in line[1:])
            if not rating_line:
                scenario_id = int(line[0])

                # Retrieve player_ids for team_1
                team_1_players_ids = {
                    player_name: player_id
                    for player_name, player_id in self.db_manager.query_sql(
                        f"""SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'"{name}"' for name in team_players_1)}) and team_id={team_id_1} ORDER BY player_id"""
                    )
                }

                # Retrieve player_ids for team_2
                team_2_players_ids = {
                    player_name: player_id
                    for player_name, player_id in self.db_manager.query_sql(
                        f"""SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'"{name}"' for name in team_players_2)}) and team_id={team_id_2} ORDER BY player_id"""
                    )
                }

            elif len(line) > 1 and not line[0].isdigit():
                # if this line DOES contain a friendly player followed by ratings
                # this line must contain ratings to upsert

                if team_2_players_ids and 'scenario_id' in locals():
                    player_1 = line[0]
                    ratings = list(map(int, line[1:]))
                    # Retrieve player_id and team_id for friendly team (team_1)
                    result = self.db_manager.query_sql(f"SELECT player_id, team_id FROM players WHERE player_name='{player_1}' and team_id={team_id_1}")
                    # if results are retrieved then we can continue.
                    player_id_1 = 0
                    try: 
                        if result:
                            player_id_1, team_id_1 = result[0]
                        else:
                            raise ValueError(f'{player_1}')
                    except (ValueError) as e:
                        print(f"VALUE ERROR ON IMPORT: {e}\nThis name doesn't match any friendly player. Check the import file for mistakes based on this name: {e}")
                        continue

                    for i, rating in enumerate(ratings):
                        try:
                            player_name_2 = list(team_2_players_ids.keys())[i]
                            player_id_2 = team_2_players_ids[player_name_2]
                            self.db_manager.upsert_rating(player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
                        except (ValueError, IndexError) as e:
                            print(f"import_csv_header_and_ratings ERROR - {e}")

    #############################################

    def prep_names(self):
        fNames = [self.grid_entries[i][0].get() for i in range(1, 6)]
        oNames = [self.grid_entries[0][i].get() for i in range(1, 6)]
        return fNames, oNames

    def prep_ratings(self,fNames,oNames):
        fRatings = {fNames[i]: {oNames[j]: self.grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
        oRatings = {oNames[i]: {fNames[j]: self.grid_entries[j+1][i+1].get() for j in range(5)} for i in range(5)}
        return fRatings, oRatings
    
    def prep_scenario(self):
        scenario = self.get_scenario_num()
        return scenario

    def sort_names(self, fNames, oNames, check_alpha):
        if check_alpha.get():
            # print("Sorting...")
            fNames_sorted = sorted(fNames, key=lambda x: x)
            oNames_sorted = sorted(oNames, key=lambda x: x)
        else:
            fNames_sorted = fNames
            oNames_sorted = oNames
        return fNames_sorted, oNames_sorted
    
    # def get_row_range(self):
    #     current_scenario = self.get_scenario_num()
    #     row_lo, row_hi = self.scenario_ranges.get(current_scenario, (1, 6))  # Default to (1, 6) if scenario is not found
    #     if current_scenario < 1:
    #         print("Scenario Agnostic Pairing...")
    #     return row_lo, row_hi

    def get_scenario_num(self):
        num_string = self.scenario_box.get()[:1]
        num = 0
        if num_string:
            num = int(num_string)
            if self.print_output: print(type(num))
        return num

    def validate_complete_ratings(self, fRatings, oRatings, fNames, oNames):
        """
        Validate that all 25 matchup ratings are present before generating combinations.
        
        Args:
            fRatings: Ratings matrix for first team
            oRatings: Ratings matrix for second team (should match fRatings)
            fNames: Names of first team players
            oNames: Names of second team players
            
        Returns:
            bool: True if all 25 ratings are present, False otherwise
        """
        # Check that we have 5 players per team
        if len(fNames) != 5 or len(oNames) != 5:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Incomplete Team Data", 
                f"Each team must have exactly 5 players.\n\n"
                f"Current: Team 1 has {len(fNames)} players, Team 2 has {len(oNames)} players.\n\n"
                "Please ensure both teams are properly loaded before generating combinations.")
            return False
        
        # Check that ratings matrix is 5x5
        if len(fRatings) != 5 or any(len(row) != 5 for row in fRatings):
            import tkinter.messagebox as messagebox
            messagebox.showerror("Incomplete Ratings Matrix", 
                f"Ratings matrix must be 5x5.\n\n"
                f"Current matrix dimensions: {len(fRatings)}x{len(fRatings[0]) if fRatings else 0}\n\n"
                "Please ensure all player matchup ratings are loaded.")
            return False
        
        # Count missing ratings (empty cells or invalid values)
        missing_ratings = []
        min_rating, max_rating = self.rating_range
        
        for i in range(5):
            for j in range(5):
                try:
                    rating = fRatings[i][j]
                    # Check if rating is empty, None, or outside valid range
                    if (rating is None or rating == "" or 
                        (isinstance(rating, str) and rating.strip() == "") or
                        (isinstance(rating, (int, float)) and (rating < min_rating or rating > max_rating))):
                        missing_ratings.append((i+1, j+1, fNames[i] if i < len(fNames) else f"Player {i+1}", 
                                              oNames[j] if j < len(oNames) else f"Player {j+1}"))
                except (IndexError, TypeError, ValueError):
                    missing_ratings.append((i+1, j+1, fNames[i] if i < len(fNames) else f"Player {i+1}", 
                                          oNames[j] if j < len(oNames) else f"Player {j+1}"))
        
        # If there are missing ratings, show detailed error
        if missing_ratings:
            import tkinter.messagebox as messagebox
            
            missing_count = len(missing_ratings)
            total_ratings = 25
            
            # Create detailed message showing first few missing ratings
            missing_details = []
            for i, (row, col, fname, oname) in enumerate(missing_ratings[:10]):  # Show up to 10 missing
                missing_details.append(f"• Row {row}, Col {col}: {fname} vs {oname}")
            
            error_message = (
                f"Missing Ratings Detected!\n\n"
                f"Found {missing_count} missing or invalid ratings out of {total_ratings} total.\n\n"
                f"Missing ratings:\n" + "\n".join(missing_details)
            )
            
            if missing_count > 10:
                error_message += f"\n... and {missing_count - 10} more missing ratings."
            
            error_message += (
                f"\n\nAll {total_ratings} player matchup ratings must be present and within the range "
                f"{min_rating}-{max_rating} before generating combinations.\n\n"
                f"Please complete all ratings and try again."
            )
            
            messagebox.showerror("Incomplete Ratings Data", error_message)
            return False
        
        # All validations passed
        print(f"✅ Validation passed: All 25 ratings are present and valid ({min_rating}-{max_rating})")
        return True

    def validate_grid_data(self):
        """Validate grid data based on current rating system"""
        min_rating, max_rating = self.rating_range
        valid_ratings = [str(i) for i in range(min_rating, max_rating + 1)]
        
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                if value and value not in valid_ratings:
                    system_name = self.rating_config['name']
                    messagebox.showerror("Error", 
                                       f"Invalid rating at row {row+1}, column {col+1}.\n\n"
                                       f"Current system: {system_name}\n"
                                       f"Valid ratings: {min_rating}-{max_rating}")
                    return False
        return True

    def create_tooltip(self, widget, text):
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{widget.winfo_rootx() + 20}+{widget.winfo_rooty() + 20}")
        label = tk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1, padx=2, pady=2)
        label.pack()
        tooltip.withdraw()

        def show_tooltip(event):
            tooltip.deiconify()

        def hide_tooltip(event):
            tooltip.withdraw()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def get_opponent_player_names(self):
        return [self.grid_entries[0][col].get() for col in range(1, 6)]

    def get_friendly_player_names(self):
        return [self.grid_entries[row][0].get() for row in range(1, 6)]
    
    def extract_ratings(self):
        ratings = {}
        fNames = self.get_friendly_player_names()
        oNames = self.get_opponent_player_names()
        for row in range(1, 6):
            player = self.grid_entries[row][0].get()
            ratings[player] = {}
            for col in range(1, 6):
                opponent = self.grid_entries[0][col].get()
                rating = int(self.grid_entries[row][col].get())
                ratings[player][opponent] = rating
        return ratings

    # Comment functionality methods
    def check_comment_exists(self, row, col):
        """Check if a comment exists for a specific cell without showing tooltip"""
        try:
            # Get current team and scenario information
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()
            
            # Get player names from grid
            friendly_player = self.grid_entries[row][0].get()
            opponent_player = self.grid_entries[0][col].get()
            
            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                return False
            
            # Query comment from database
            comment = self.db_manager.query_comment_by_name(
                team1_name, team2_name, scenario_name, 
                friendly_player, opponent_player
            )
            
            return comment is not None and comment.strip() != ""
        except Exception:
            return False

    def clear_comment_indicators(self):
        """Clear all existing comment indicators"""
        if hasattr(self, 'comment_indicators'):
            for indicator in self.comment_indicators.values():
                indicator.destroy()
            self.comment_indicators.clear()
        else:
            self.comment_indicators = {}

    def update_comment_indicators(self):
        """Update corner indicators for cells that have comments"""
        # Clear existing indicators first
        self.clear_comment_indicators()
        
        for row in range(1, 6):
            for col in range(1, 6):
                if self.check_comment_exists(row, col):
                    self.add_comment_indicator(row, col)

    def add_comment_indicator(self, row, col):
        """Add a small corner indicator for comments"""
        try:
            # Create a small triangle indicator
            indicator = tk.Label(
                self.grid_frame,
                text="▲",  # Small triangle
                font=("Arial", 6),
                fg="#FF6B35",  # Orange-red color for visibility
                bg=self.grid_frame.cget('bg'),
                relief=tk.FLAT,
                borderwidth=0
            )
            
            # Store the indicator for cleanup later
            self.comment_indicators[(row, col)] = indicator
            
            # Schedule positioning after the widget is drawn
            self.root.after_idle(lambda: self.position_comment_indicator(indicator, row, col))
            
        except Exception as e:
            print(f"Error adding comment indicator at ({row}, {col}): {e}")

    def position_comment_indicator(self, indicator, row, col):
        """Position the comment indicator in the top-right corner of the cell"""
        try:
            widget = self.grid_widgets[row][col]
            if widget is not None and widget.winfo_exists():
                # Ensure the indicator hasn't been destroyed
                if not indicator.winfo_exists():
                    return
                    
                # Position the indicator in the top-right corner
                indicator.place(
                    in_=widget,
                    anchor="ne",
                    relx=1.0,  # Right edge
                    rely=0.0,  # Top edge
                    x=-2,      # Slight offset from edge
                    y=2        # Slight offset from edge
                )
            else:
                # Widget doesn't exist, safely destroy indicator
                if indicator.winfo_exists():
                    indicator.destroy()
        except Exception as e:
            print(f"Error positioning comment indicator at ({row}, {col}): {e}")
            # If positioning fails, safely destroy the indicator
            try:
                if indicator.winfo_exists():
                    indicator.destroy()
            except:
                pass  # Ignore any destruction errors

    def show_comment_tooltip(self, event, row, col):
        """Show tooltip with comment text when hovering over a matchup cell"""
        try:
            # Get current team and scenario information
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()
            
            # Get player names from grid
            friendly_player = self.grid_entries[row][0].get()
            opponent_player = self.grid_entries[0][col].get()
            
            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                return
            
            # Query comment from database
            comment = self.db_manager.query_comment_by_name(
                team1_name, team2_name, scenario_name, 
                friendly_player, opponent_player
            )
            
            if comment:
                # Create tooltip window
                self.comment_tooltip = tk.Toplevel(self.root)
                self.comment_tooltip.wm_overrideredirect(True)
                
                # Position tooltip near cursor
                x = event.widget.winfo_rootx() + 20
                y = event.widget.winfo_rooty() + event.widget.winfo_height() + 5
                self.comment_tooltip.wm_geometry(f"+{x}+{y}")
                
                # Create label with comment text
                label = tk.Label(
                    self.comment_tooltip, 
                    text=comment, 
                    justify=tk.LEFT,
                    background="#ffffe0", 
                    relief=tk.SOLID, 
                    borderwidth=1,
                    wraplength=300,
                    padx=5,
                    pady=5
                )
                label.pack()
                
        except Exception as e:
            print(f"Error showing comment tooltip: {e}")

    def hide_comment_tooltip(self, event=None):
        """Hide the comment tooltip"""
        if hasattr(self, 'comment_tooltip') and self.comment_tooltip:
            self.comment_tooltip.destroy()
            self.comment_tooltip = None

    def open_comment_editor(self, event, row, col):
        """Open a dialog to edit/add comments for a specific matchup"""
        try:
            # Get current team and scenario information
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()
            
            # Get player names from grid
            friendly_player = self.grid_entries[row][0].get()
            opponent_player = self.grid_entries[0][col].get()
            
            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                messagebox.showwarning("Missing Information", 
                                     "Please select teams, scenario, and ensure player names are filled in.")
                return
            
            # Get existing comment
            existing_comment = self.db_manager.query_comment_by_name(
                team1_name, team2_name, scenario_name, 
                friendly_player, opponent_player
            ) or ""
            
            # Create comment editor dialog
            self.create_comment_dialog(
                team1_name, team2_name, scenario_name, 
                friendly_player, opponent_player, existing_comment
            )
            
        except Exception as e:
            print(f"Error opening comment editor: {e}")
            messagebox.showerror("Error", f"Failed to open comment editor: {e}")

    def create_comment_dialog(self, team1_name, team2_name, scenario_name, 
                            friendly_player, opponent_player, existing_comment):
        """Create a dialog window for editing comments"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Matchup Comment")
        dialog.geometry("500x400")
        dialog.resizable(True, True)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title label
        title_text = f"Comment for {friendly_player} vs {opponent_player}\nScenario: {scenario_name}"
        title_label = tk.Label(dialog, text=title_text, font=("Arial", 12, "bold"))
        title_label.pack(pady=10)
        
        # Character count frame
        count_frame = tk.Frame(dialog)
        count_frame.pack(fill=tk.X, padx=10)
        
        char_count_label = tk.Label(count_frame, text="Characters: 0/2000", anchor="e")
        char_count_label.pack(side=tk.RIGHT)
        
        # Text area for comment
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        comment_text = tk.Text(
            text_frame, 
            height=15, 
            width=60, 
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        
        # Scrollbar for text area
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=comment_text.yview)
        comment_text.configure(yscrollcommand=scrollbar.set)
        
        comment_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert existing comment
        if existing_comment:
            comment_text.insert(tk.END, existing_comment)
            
        # Update character count
        def update_char_count(event=None):
            content = comment_text.get("1.0", tk.END).strip()
            char_count = len(content)
            char_count_label.config(text=f"Characters: {char_count}/2000")
            
            # Change color if approaching or exceeding limit
            if char_count > 2000:
                char_count_label.config(fg="red")
            elif char_count > 1800:
                char_count_label.config(fg="orange")
            else:
                char_count_label.config(fg="black")
        
        # Bind character count update
        comment_text.bind('<KeyRelease>', update_char_count)
        comment_text.bind('<ButtonRelease>', update_char_count)
        update_char_count()  # Initial count
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_comment():
            try:
                comment_content = comment_text.get("1.0", tk.END).strip()
                
                # Validate length
                if len(comment_content) > 2000:
                    messagebox.showerror("Comment Too Long", 
                                       "Comment must be 2000 characters or less.")
                    return
                
                # Save to database
                if comment_content:
                    self.db_manager.upsert_comment_by_name(
                        team1_name, team2_name, scenario_name,
                        friendly_player, opponent_player, comment_content
                    )
                    messagebox.showinfo("Success", "Comment saved successfully!")
                else:
                    # Delete comment if empty
                    self.db_manager.delete_comment_by_name(
                        team1_name, team2_name, scenario_name,
                        friendly_player, opponent_player
                    )
                    messagebox.showinfo("Success", "Comment deleted successfully!")
                
                dialog.destroy()
                
            except Exception as e:
                print(f"Error saving comment: {e}")
                messagebox.showerror("Error", f"Failed to save comment: {e}")
        
        def delete_comment():
            if messagebox.askyesno("Delete Comment", "Are you sure you want to delete this comment?"):
                try:
                    self.db_manager.delete_comment_by_name(
                        team1_name, team2_name, scenario_name,
                        friendly_player, opponent_player
                    )
                    messagebox.showinfo("Success", "Comment deleted successfully!")
                    dialog.destroy()
                except Exception as e:
                    print(f"Error deleting comment: {e}")
                    messagebox.showerror("Error", f"Failed to delete comment: {e}")
        
        # Buttons
        tk.Button(button_frame, text="Save", command=save_comment, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Delete", command=delete_comment, bg="lightcoral").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Focus on text area
        comment_text.focus_set()

    def update_sort_value_column(self):
        """Update the Sort Value column based on current sorting mode"""
        self.update_sort_value_recursive("")

    def update_sort_value_recursive(self, node):
        """Recursively update sort values for all nodes in tree"""
        children = self.treeview.tree.get_children(node)
        
        for child in children:
            # Get the appropriate sort value based on current mode
            sort_value = str(self.get_sort_value_for_node(child))
            
            # Update the Rating column (first column, index 0)
            current_values = list(self.treeview.tree.item(child, 'values'))
            if len(current_values) < 1:
                current_values.append(sort_value)
            else:
                current_values[0] = sort_value
            
            self.treeview.tree.item(child, values=current_values)
            
            # Recursively update children
            self.update_sort_value_recursive(child)

    def get_sort_value_for_node(self, node):
        """Extract the appropriate sort value from node tags based on current sort mode"""
        if self.current_sort_mode == "none":
            return ""
        elif self.current_sort_mode == "confidence":
            return self.tree_generator.get_confidence_from_tags(node)
        elif self.current_sort_mode == "resistance":
            return self.tree_generator.get_resistance_from_tags(node)
        elif self.current_sort_mode == "cumulative":
            return self.tree_generator.get_cumulative_from_tags(node)
        else:
            return ""

    def flip_grid_perspective(self):
        """Flip the grid to show opponent's perspective of matchup ratings."""
        try:
            if not self.grid_is_flipped:
                # Store original data before flipping (use grid_entries, not grid_display_entries)
                self.original_grid_data = {}
                for row in range(6):
                    for col in range(6):
                        self.original_grid_data[(row, col)] = self.grid_entries[row][col].get()
                
                # 1. Swap team player names
                # Store friendly team names (column 0, rows 1-5)
                friendly_names = []
                for row in range(1, 6):
                    friendly_names.append(self.grid_entries[row][0].get())
                
                # Store enemy team names (row 0, columns 1-5)  
                enemy_names = []
                for col in range(1, 6):
                    enemy_names.append(self.grid_entries[0][col].get())
                
                # Swap the names - put enemy names where friendly names were
                for row in range(1, 6):
                    if row - 1 < len(enemy_names):
                        self.grid_entries[row][0].set(enemy_names[row - 1])
                
                # Put friendly names where enemy names were
                for col in range(1, 6):
                    if col - 1 < len(friendly_names):
                        self.grid_entries[0][col].set(friendly_names[col - 1])
                
                # 2. Flip ratings around 3 (1↔5, 2↔4, 3 stays 3)
                for row in range(1, 6):
                    for col in range(1, 6):
                        current_value = self.grid_entries[row][col].get()
                        if current_value.isdigit():
                            rating = int(current_value)
                            # Flip around 3: new_rating = 6 - old_rating
                            flipped_rating = 6 - rating
                            self.grid_entries[row][col].set(str(flipped_rating))
                
                self.grid_is_flipped = True
                print("Grid flipped to opponent's perspective")
                
            else:
                # Restore original data
                if self.original_grid_data:
                    for row in range(6):
                        for col in range(6):
                            original_value = self.original_grid_data.get((row, col), "")
                            self.grid_entries[row][col].set(original_value)
                
                self.grid_is_flipped = False
                self.original_grid_data = None
                print("Grid restored to friendly perspective")
                
        except Exception as e:
            print(f"Error flipping grid perspective: {e}")
            messagebox.showerror("Error", f"Failed to flip grid perspective: {e}")

    def create_round_selection_dropdowns(self):
        """Create dropdowns for tracking player selections across tournament rounds."""
        try:
            # Clear existing content (but skip the header frame that was created in parent method)
            for widget in self.round_selection_frame.winfo_children():
                if widget.winfo_class() != 'Frame' or len(widget.winfo_children()) == 0:
                    continue  # Skip the header frame
                widget.destroy()
            
            self.round_dropdowns.clear()
            self.round_vars.clear()
            self.enemy_round_dropdowns = []
            self.enemy_round_vars = []
            
            # Create grid container for the dropdowns directly in round_selection_frame
            grid_container = tk.Frame(self.round_selection_frame)
            grid_container.pack(fill=tk.X, padx=10, pady=5)
            
            # Column headers
            header_frame = tk.Frame(grid_container)
            header_frame.pack(fill=tk.X, pady=(0, 8))
            
            # Configure header column layout to match round frames
            header_frame.grid_columnconfigure(0, weight=0, minsize=80)
            header_frame.grid_columnconfigure(1, weight=1, minsize=150)
            header_frame.grid_columnconfigure(2, weight=1, minsize=150)
            
            tk.Label(header_frame, text="Round", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, sticky='w')
            tk.Label(header_frame, text="Friendly", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, sticky='w')
            tk.Label(header_frame, text="Enemy", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, sticky='w')
            
            # Create 5 rounds of dropdowns (ante system: 1 ante + 2 responses per round)
            for round_num in range(1, 6):
                round_frame = tk.Frame(grid_container)
                round_frame.pack(fill=tk.X, pady=2)
                
                # Configure consistent column layout
                round_frame.grid_columnconfigure(0, weight=0, minsize=80)  # Round label
                round_frame.grid_columnconfigure(1, weight=1, minsize=150)  # Friendly column
                round_frame.grid_columnconfigure(2, weight=1, minsize=150)  # Enemy column
                
                # Round number label
                tk.Label(round_frame, text=f"Round {round_num}:", font=("Arial", 9), width=8).grid(row=0, column=0, padx=5, sticky='w')
                
                # Determine who antes this round (alternating: friendly odd rounds, enemy even rounds)
                friendly_antes = (round_num % 2 == 1)
                
                if friendly_antes:
                    # Friendly team antes (1 dropdown), Enemy responds (2 dropdowns)
                    friendly_var = tk.StringVar()
                    friendly_dropdown = ttk.Combobox(round_frame, state='readonly', width=18, textvariable=friendly_var)
                    friendly_dropdown.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
                    
                    # Create a sub-frame for enemy responses to maintain alignment
                    enemy_response_frame = tk.Frame(round_frame)
                    enemy_response_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=2, sticky='nsew')
                    
                    # Enemy response dropdowns - vertically stacked
                    enemy_var1 = tk.StringVar()
                    enemy_dropdown1 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var1)
                    enemy_dropdown1.pack(fill=tk.X, pady=(0, 2))
                    
                    enemy_var2 = tk.StringVar()
                    enemy_dropdown2 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var2)
                    enemy_dropdown2.pack(fill=tk.X, pady=(0, 0))
                    
                    # Bind events
                    friendly_var.trace_add('write', lambda *args, r=round_num, v=friendly_var: self.on_ante_selection_change_direct(r, v))
                    enemy_var1.trace_add('write', lambda *args, r=round_num, p=1, v=enemy_var1: self.on_response_selection_change_direct(r, p, v))
                    enemy_var2.trace_add('write', lambda *args, r=round_num, p=2, v=enemy_var2: self.on_response_selection_change_direct(r, p, v))
                    
                    # Store references
                    self.round_vars.append(friendly_var)
                    self.round_dropdowns.append(friendly_dropdown)
                    self.enemy_round_vars.extend([enemy_var1, enemy_var2])
                    self.enemy_round_dropdowns.extend([enemy_dropdown1, enemy_dropdown2])
                    self.selected_players_per_round[round_num] = {
                        'ante': None, 'ante_team': 'friendly',
                        'response1': None, 'response2': None, 'response_team': 'enemy'
                    }
                    
                else:
                    # Enemy team antes (1 dropdown), Friendly responds (2 dropdowns)
                    enemy_var = tk.StringVar()
                    enemy_dropdown = ttk.Combobox(round_frame, state='readonly', width=18, textvariable=enemy_var)
                    enemy_dropdown.grid(row=0, column=2, padx=5, pady=2, sticky='ew')
                    
                    # Create a sub-frame for friendly responses to maintain alignment
                    friendly_response_frame = tk.Frame(round_frame)
                    friendly_response_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=2, sticky='nsew')
                    
                    # Friendly response dropdowns - vertically stacked
                    friendly_var1 = tk.StringVar()
                    friendly_dropdown1 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var1)
                    friendly_dropdown1.pack(fill=tk.X, pady=(0, 2))
                    
                    friendly_var2 = tk.StringVar()
                    friendly_dropdown2 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var2)
                    friendly_dropdown2.pack(fill=tk.X, pady=(0, 0))
                    
                    # Bind events
                    enemy_var.trace_add('write', lambda *args, r=round_num, v=enemy_var: self.on_ante_selection_change_direct(r, v))
                    friendly_var1.trace_add('write', lambda *args, r=round_num, p=1, v=friendly_var1: self.on_response_selection_change_direct(r, p, v))
                    friendly_var2.trace_add('write', lambda *args, r=round_num, p=2, v=friendly_var2: self.on_response_selection_change_direct(r, p, v))
                    
                    # Store references
                    self.enemy_round_vars.append(enemy_var)
                    self.enemy_round_dropdowns.append(enemy_dropdown)
                    self.round_vars.extend([friendly_var1, friendly_var2])
                    self.round_dropdowns.extend([friendly_dropdown1, friendly_dropdown2])
                    self.selected_players_per_round[round_num] = {
                        'ante': None, 'ante_team': 'enemy',
                        'response1': None, 'response2': None, 'response_team': 'friendly'
                    }
            
            # Update dropdown options
            self.update_round_dropdown_options()
            
        except Exception as e:
            print(f"Error creating round selection dropdowns: {e}")
            messagebox.showerror("Error", f"Failed to create round selection dropdowns: {e}")

    def update_round_dropdown_options(self):
        """Update the options in round dropdowns based on current team selection."""
        try:
            # Get current friendly team players from database
            friendly_players = []
            if self.team1_var.get():
                team_name = self.team1_var.get()
                # Get team ID
                team_id_query = f"SELECT team_id FROM teams WHERE team_name = '{team_name}'"
                team_result = self.db_manager.query_sql(team_id_query)
                
                if team_result:
                    team_id = team_result[0][0]
                    # Get player names for this team
                    player_query = f"SELECT player_name FROM players WHERE team_id = {team_id} ORDER BY player_id"
                    player_results = self.db_manager.query_sql(player_query)
                    friendly_players = [row[0] for row in player_results]
            
            # Get current enemy team players from database
            enemy_players = []
            if self.team2_var.get():
                team_name = self.team2_var.get()
                # Get team ID
                team_id_query = f"SELECT team_id FROM teams WHERE team_name = '{team_name}'"
                team_result = self.db_manager.query_sql(team_id_query)
                
                if team_result:
                    team_id = team_result[0][0]
                    # Get player names for this team
                    player_query = f"SELECT player_name FROM players WHERE team_id = {team_id} ORDER BY player_id"
                    player_results = self.db_manager.query_sql(player_query)
                    enemy_players = [row[0] for row in player_results]
            
            # Update all dropdowns with ante/response system and matchup logic
            if hasattr(self, 'round_dropdowns') and hasattr(self, 'enemy_round_dropdowns'):
                self._update_ante_response_dropdowns(friendly_players, enemy_players)
                    
        except Exception as e:
            print(f"Error updating round dropdown options: {e}")

    def on_ante_selection_change(self, round_num):
        """Handle ante selection changes."""
        try:
            # The lambda captures the round_num correctly, but we need to find the right variable
            # by examining which dropdown triggered this event
            round_data = self.selected_players_per_round.get(round_num, {})
            ante_team = round_data.get('ante_team')
            selected_player = None
            
            # Get the actual selected value from the dropdown that triggered this
            if ante_team == 'friendly':
                # For friendly ante rounds (1, 3, 5), find the friendly dropdown for this round
                for i, var in enumerate(self.round_vars):
                    if var.get():  # If this dropdown has a value, it might be the one that changed
                        # Map dropdown index to round number based on our layout
                        if self._is_ante_dropdown_for_round(i, round_num, 'friendly'):
                            selected_player = var.get()
                            break
            else:
                # For enemy ante rounds (2, 4), find the enemy dropdown for this round
                for i, var in enumerate(self.enemy_round_vars):
                    if var.get():  # If this dropdown has a value, it might be the one that changed
                        if self._is_ante_dropdown_for_round(i, round_num, 'enemy'):
                            selected_player = var.get()
                            break
            
            self.selected_players_per_round[round_num]['ante'] = selected_player if selected_player else None
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            print(f"Round {round_num} ante selection ({ante_team}): {selected_player}")
            
        except Exception as e:
            print(f"Error handling ante selection change: {e}")

    def on_response_selection_change(self, round_num, position):
        """Handle response selection changes."""
        try:
            round_data = self.selected_players_per_round.get(round_num, {})
            response_team = round_data.get('response_team')
            selected_player = None
            
            # Find the correct dropdown that corresponds to this round and position
            if response_team == 'friendly':
                # Find the friendly response dropdown for this round and position
                for i, var in enumerate(self.round_vars):
                    if self._is_response_dropdown_for_round_position(i, round_num, position, 'friendly'):
                        selected_player = var.get()
                        break
            else:
                # Find the enemy response dropdown for this round and position
                for i, var in enumerate(self.enemy_round_vars):
                    if self._is_response_dropdown_for_round_position(i, round_num, position, 'enemy'):
                        selected_player = var.get()
                        break
            
            # Update tracking
            response_key = f'response{position}'
            self.selected_players_per_round[round_num][response_key] = selected_player if selected_player else None
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            print(f"Round {round_num} response {position} ({response_team}): {selected_player}")
            
        except Exception as e:
            print(f"Error handling response selection change: {e}")

    def _is_ante_dropdown_for_round(self, dropdown_index, round_num, team):
        """Check if dropdown index corresponds to ante dropdown for specific round and team."""
        # This is a simplified check - you may need to adjust based on actual dropdown ordering
        if team == 'friendly' and round_num % 2 == 1:  # Friendly antes on odd rounds
            expected_index = (round_num - 1) // 2
            return dropdown_index == expected_index
        elif team == 'enemy' and round_num % 2 == 0:  # Enemy antes on even rounds
            expected_index = (round_num - 2) // 2
            return dropdown_index == expected_index
        return False

    def _is_response_dropdown_for_round_position(self, dropdown_index, round_num, position, team):
        """Check if dropdown index corresponds to response dropdown for specific round, position and team."""
        # This is a simplified check - you may need to adjust based on actual dropdown ordering
        # The logic here depends on how dropdowns are stored in the arrays
        return False  # Placeholder - needs proper implementation based on dropdown layout

    def on_ante_selection_change_direct(self, round_num, var):
        """Handle ante selection changes with direct variable access."""
        try:
            selected_player = var.get()
            self.selected_players_per_round[round_num]['ante'] = selected_player if selected_player else None
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            round_data = self.selected_players_per_round.get(round_num, {})
            ante_team = round_data.get('ante_team', 'unknown')
            print(f"Round {round_num} ante selection ({ante_team}): {selected_player}")
            
            # Sync with matchup tree if synchronizer is available
            if hasattr(self, 'tree_synchronizer') and self.tree_synchronizer:
                self.tree_synchronizer.sync_round_to_tree(round_num)
            
        except Exception as e:
            print(f"Error handling ante selection change: {e}")

    def on_response_selection_change_direct(self, round_num, position, var):
        """Handle response selection changes with direct variable access."""
        try:
            selected_player = var.get()
            response_key = f'response{position}'
            self.selected_players_per_round[round_num][response_key] = selected_player if selected_player else None
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            round_data = self.selected_players_per_round.get(round_num, {})
            response_team = round_data.get('response_team', 'unknown')
            print(f"Round {round_num} response {position} ({response_team}): {selected_player}")
            
            # Sync with matchup tree if synchronizer is available
            if hasattr(self, 'tree_synchronizer') and self.tree_synchronizer:
                self.tree_synchronizer.sync_round_to_tree(round_num)
            
        except Exception as e:
            print(f"Error handling response selection change: {e}")

    def _get_ante_dropdown_index(self, round_num, team):
        """Get the dropdown index for the ante selection of a specific round and team."""
        # This is a simplified index calculation - you may need to adjust based on actual storage
        return round_num - 1

    def _get_response_dropdown_index(self, round_num, team, position):
        """Get the dropdown index for the response selection of a specific round, team, and position."""
        # This is a simplified index calculation - you may need to adjust based on actual storage
        base_index = (round_num - 1) * 2
        return base_index + (position - 1)

    def _update_ante_response_dropdowns(self, friendly_players, enemy_players):
        """Update dropdowns with proper ante/response logic and matchup correlation."""
        try:
            dropdown_index = 0
            enemy_dropdown_index = 0
            
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                friendly_antes = (round_num % 2 == 1)
                
                if friendly_antes:
                    # Round 1, 3, 5: Friendly antes, Enemy responds
                    # Update friendly ante dropdown with special logic for matchup correlation
                    if dropdown_index < len(self.round_dropdowns):
                        if round_num == 1:
                            # Round 1: Normal available players
                            available_friendly = self._get_available_friendly_players(round_num, friendly_players)
                        else:
                            # Round 3, 5: Only players who responded in previous round
                            available_friendly = self._get_friendly_ante_options(round_num)
                        
                        self.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly
                        dropdown_index += 1
                    
                    # Update enemy response dropdowns
                    available_enemy = self._get_available_enemy_players(round_num, enemy_players)
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + available_enemy
                        enemy_dropdown_index += 1
                    
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + available_enemy
                        enemy_dropdown_index += 1
                        
                else:
                    # Round 2, 4: Enemy antes, Friendly responds
                    # Enemy ante dropdown - special logic for matchup correlation
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        ante_options = self._get_enemy_ante_options(round_num)
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + ante_options
                        enemy_dropdown_index += 1
                    
                    # Update friendly response dropdowns
                    available_friendly = self._get_available_friendly_players(round_num, friendly_players)
                    if dropdown_index < len(self.round_dropdowns):
                        self.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly
                        dropdown_index += 1
                    
                    if dropdown_index < len(self.round_dropdowns):
                        self.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly
                        dropdown_index += 1
                        
        except Exception as e:
            print(f"Error updating ante/response dropdowns: {e}")

    def _get_enemy_ante_options(self, round_num):
        """Get valid ante options for enemy based on previous round's responses."""
        if round_num <= 1:
            return []
        
        # For round 2, 4, etc., the ante options are the enemy players who responded in the previous round
        previous_round = round_num - 1
        previous_round_data = self.selected_players_per_round.get(previous_round, {})
        
        # The ante options are the enemy players from the previous round's responses
        ante_options = []
        if previous_round_data.get('response_team') == 'enemy':
            if previous_round_data.get('response1'):
                ante_options.append(previous_round_data['response1'])
            if previous_round_data.get('response2'):
                ante_options.append(previous_round_data['response2'])
        
        return ante_options

    def _get_friendly_ante_options(self, round_num):
        """Get valid ante options for friendly based on previous round's responses."""
        if round_num <= 1:
            return []
        
        # For round 3, 5, etc., the ante options are the friendly players who responded in the previous round
        previous_round = round_num - 1
        previous_round_data = self.selected_players_per_round.get(previous_round, {})
        
        # The ante options are the friendly players from the previous round's responses
        ante_options = []
        if previous_round_data.get('response_team') == 'friendly':
            if previous_round_data.get('response1'):
                ante_options.append(previous_round_data['response1'])
            if previous_round_data.get('response2'):
                ante_options.append(previous_round_data['response2'])
        
        return ante_options

    def _get_available_friendly_players(self, round_num, all_friendly_players):
        """Get available friendly players for the current round."""
        used_players = set()
        
        # Collect all used friendly players from previous rounds
        for r in range(1, round_num):
            round_data = self.selected_players_per_round.get(r, {})
            if round_data.get('ante_team') == 'friendly' and round_data.get('ante'):
                used_players.add(round_data['ante'])
            if round_data.get('response_team') == 'friendly':
                if round_data.get('response1'):
                    used_players.add(round_data['response1'])
                if round_data.get('response2'):
                    used_players.add(round_data['response2'])
        
        return [player for player in all_friendly_players if player not in used_players]

    def _get_available_enemy_players(self, round_num, all_enemy_players):
        """Get available enemy players for the current round."""
        used_players = set()
        
        # Collect all used enemy players from previous rounds
        for r in range(1, round_num):
            round_data = self.selected_players_per_round.get(r, {})
            if round_data.get('ante_team') == 'enemy' and round_data.get('ante'):
                used_players.add(round_data['ante'])
            if round_data.get('response_team') == 'enemy':
                if round_data.get('response1'):
                    used_players.add(round_data['response1'])
                if round_data.get('response2'):
                    used_players.add(round_data['response2'])
        
        return [player for player in all_enemy_players if player not in used_players]

    def create_matchup_output_panel(self):
        """Create a panel to display the final 5 matchups in a simple format."""
        try:
            # Create output panel frame next to buttons in bottom frame
            self.output_panel_frame = tk.Frame(self.bottom_frame, relief=tk.RIDGE, borderwidth=2, bg="lightyellow")
            self.output_panel_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Panel title
            title_label = tk.Label(self.output_panel_frame, text="Final Matchups Output", 
                                 font=("Arial", 12, "bold"), bg="lightyellow")
            title_label.pack(pady=(5, 0))
            
            # Instructions
            instructions = tk.Label(self.output_panel_frame, 
                                  text="Select a pairing from the tree above, then click 'Extract Matchups' to display the 5 final matchups:",
                                  font=("Arial", 9), bg="lightyellow", fg="darkblue")
            instructions.pack(pady=(0, 5))
            
            # Extract button
            extract_button = tk.Button(self.output_panel_frame, text="Extract Matchups", 
                                     command=self.extract_final_matchups, font=("Arial", 10, "bold"),
                                     bg="lightgreen", relief=tk.RAISED)
            extract_button.pack(pady=5)
            
            # Text area for matchups display
            self.matchups_text = tk.Text(self.output_panel_frame, height=8, width=80, 
                                       font=("Consolas", 10), bg="white", relief=tk.SUNKEN,
                                       borderwidth=2, wrap=tk.WORD)
            self.matchups_text.pack(padx=10, pady=(0, 10), fill=tk.BOTH, expand=True)
            
            # Add scrollbar
            scrollbar = tk.Scrollbar(self.matchups_text)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.matchups_text.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=self.matchups_text.yview)
            
            # Copy button
            copy_button = tk.Button(self.output_panel_frame, text="Copy to Clipboard", 
                                  command=self.copy_matchups_to_clipboard, font=("Arial", 9),
                                  bg="lightblue", relief=tk.RAISED)
            copy_button.pack(pady=(0, 5))
            
        except Exception as e:
            print(f"Error creating matchup output panel: {e}")
            messagebox.showerror("Error", f"Failed to create matchup output panel: {e}")

    def extract_final_matchups(self):
        """Extract the final 5 matchups from the currently selected tree item."""
        try:
            # Get selected item from tree
            selected_item = self.treeview.tree.selection()
            
            if not selected_item:
                messagebox.showwarning("No Selection", "Please select a pairing from the tree above.")
                return
            
            # Get the selected item's data
            item = selected_item[0]
            item_text = self.treeview.tree.item(item, 'text')
            item_values = self.treeview.tree.item(item, 'values')
            
            print(f"Selected item text: {item_text}")
            print(f"Selected item values: {item_values}")
            
            # Parse the matchup information
            matchups = self.parse_matchups_from_tree_item(item)
            
            print(f"Parsed matchups: {matchups}")
            
            if not matchups:
                # Provide more detailed debugging information
                children_count = len(self.treeview.tree.get_children(item))
                debug_info = f"Debug Info:\n"
                debug_info += f"- Selected item: {item_text}\n"
                debug_info += f"- Item values: {item_values}\n"
                debug_info += f"- Children count: {children_count}\n"
                debug_info += f"- Tree structure analysis required\n"
                
                messagebox.showwarning("No Matchups", f"No matchup data found for the selected item.\n\n{debug_info}")
                return
            
            # Format matchups for display in the requested format
            output_text = f"Complete Decision Path - {item_text}\n"
            output_text += "=" * 70 + "\n\n"
            
            for matchup in matchups:
                round_num = matchup.get('round', '?')
                choice = matchup.get('choice', 'Unknown choice')
                decision = matchup.get('decision', 'Unknown decision')
                rating = matchup.get('rating', 'N/A')
                
                output_text += f"Matchup {round_num}: {choice}\n"
                output_text += f"\tDecision: {decision} (Rating: {rating})\n\n"
            
            output_text += "=" * 70 + "\n"
            output_text += f"Total Decision Points: {len(matchups)}\n"
            output_text += f"Generated at: {self.get_current_timestamp()}\n"
            output_text += "\nThis shows the complete path of decisions made to reach the selected tree position."
            
            # Display in text widget
            self.matchups_text.delete(1.0, tk.END)
            self.matchups_text.insert(1.0, output_text)
            
            print(f"Successfully extracted {len(matchups)} matchups from selected tree item")
            
        except Exception as e:
            print(f"Error extracting final matchups: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to extract matchups: {e}")

    def parse_matchups_from_tree_item(self, item):
        """Parse the complete decision path leading to the selected tree item."""
        try:
            # Build the complete path from root to selected item
            decision_path = self.build_decision_path(item)
            
            if not decision_path:
                return []
                
            # Convert path items to matchup decisions
            matchups = self.convert_path_to_matchups(decision_path)
            
            return matchups
            
        except Exception as e:
            print(f"Error parsing matchups from tree item: {e}")
            return []
    
    def build_decision_path(self, target_item):
        """Build the complete path from root to the target item."""
        try:
            path = []
            current_item = target_item
            
            # Traverse up the tree to build the complete path
            while current_item:
                item_text = self.treeview.tree.item(current_item, 'text')
                item_values = self.treeview.tree.item(current_item, 'values')
                
                path.insert(0, {
                    'item_id': current_item,
                    'text': item_text,
                    'values': item_values,
                    'level': len(path)
                })
                
                # Get parent item
                parent = self.treeview.tree.parent(current_item)
                current_item = parent if parent else None
            
            print(f"Built decision path with {len(path)} levels:")
            for i, step in enumerate(path):
                print(f"  Level {i}: {step['text']}")
            
            return path
            
        except Exception as e:
            print(f"Error building decision path: {e}")
            return []
    
    def convert_path_to_matchups(self, decision_path):
        """Convert the decision path into individual matchup decisions."""
        try:
            matchups = []
            
            # Skip the root "Pairings" node and focus on actual decision nodes
            decision_nodes = [node for node in decision_path if 'vs' in node['text'] or 'rating' in node['text']]
            
            print(f"Processing {len(decision_nodes)} decision nodes:")
            
            for i, node in enumerate(decision_nodes):
                text = node['text']
                values = node['values']
                rating = values[0] if values else 'N/A'
                
                print(f"  Processing node {i+1}: {text}")
                
                if ' vs ' in text and ' OR ' in text:
                    # This is a choice node like "HABIBI vs Pete (3/5) OR Bokur (3/5)"
                    matchup_info = self.parse_choice_node(text, decision_nodes, i)
                    if matchup_info:
                        matchup_info['rating'] = rating
                        matchup_info['round'] = i + 1
                        matchups.append(matchup_info)
                        
                elif ' rating ' in text:
                    # This is a decision node like "Pete rating 3"
                    # The decision was made in the parent choice node
                    continue
                    
                elif ' vs ' in text and ' OR ' not in text:
                    # This is a final decision like "Kyle vs STEVE (3/5)"
                    parts = text.split(' vs ')
                    if len(parts) == 2:
                        friendly = parts[0].strip()
                        opponent_with_rating = parts[1].strip()
                        # Extract opponent name (remove rating in parentheses)
                        opponent = opponent_with_rating.split('(')[0].strip()
                        
                        matchups.append({
                            'round': i + 1,
                            'friendly': friendly,
                            'opponent': opponent,
                            'rating': rating,
                            'choice': text,
                            'decision': text
                        })
            
            # Now identify the actual decisions made by looking at the tree structure
            return self.identify_actual_decisions(decision_path, matchups)
            
        except Exception as e:
            print(f"Error converting path to matchups: {e}")
            return []
    
    def parse_choice_node(self, text, all_nodes, current_index):
        """Parse a choice node to extract the options and determine the decision made."""
        try:
            # Extract the base matchup and options
            # Format: "Player1 vs Player2 (X/Y) OR Player3 (X/Y)"
            if ' vs ' not in text or ' OR ' not in text:
                return None
                
            parts = text.split(' vs ', 1)
            friendly = parts[0].strip()
            
            options_part = parts[1]
            options = [opt.strip() for opt in options_part.split(' OR ')]
            
            # Look at the next node in the path to determine which option was chosen
            decision_made = None
            if current_index + 1 < len(all_nodes):
                next_node = all_nodes[current_index + 1]
                next_text = next_node['text']
                
                # Determine which option was selected
                for option in options:
                    option_name = option.split('(')[0].strip()
                    if option_name in next_text or next_text.startswith(option_name):
                        decision_made = f"{friendly} vs {option}"
                        break
            
            return {
                'friendly': friendly,
                'options': options,
                'choice': text,
                'decision': decision_made or f"{friendly} vs {options[0]}"  # Default to first option
            }
            
        except Exception as e:
            print(f"Error parsing choice node: {e}")
            return None
    
    def identify_actual_decisions(self, decision_path, preliminary_matchups):
        """Identify the actual decisions made by analyzing the tree traversal path."""
        try:
            final_matchups = []
            
            # Group nodes by their position in the decision tree
            choice_nodes = []
            decision_nodes = []
            
            for node in decision_path:
                text = node['text']
                if ' vs ' in text and ' OR ' in text:
                    choice_nodes.append(node)
                elif ' rating ' in text:
                    decision_nodes.append(node)
            
            print(f"Found {len(choice_nodes)} choice nodes and {len(decision_nodes)} decision nodes")
            
            # Match each choice with its corresponding decision
            for i, choice_node in enumerate(choice_nodes):
                choice_text = choice_node['text']
                rating = choice_node['values'][0] if choice_node['values'] else 'N/A'
                
                # Find the corresponding decision node
                decision_text = None
                if i < len(decision_nodes):
                    decision_text = decision_nodes[i]['text']
                
                # Parse the choice and decision
                matchup = self.create_matchup_from_choice_and_decision(choice_text, decision_text, rating, i + 1)
                if matchup:
                    final_matchups.append(matchup)
            
            return final_matchups
            
        except Exception as e:
            print(f"Error identifying actual decisions: {e}")
            return preliminary_matchups  # Return preliminary results as fallback
    
    def create_matchup_from_choice_and_decision(self, choice_text, decision_text, rating, round_num):
        """Create a matchup entry from choice and decision texts."""
        try:
            if not choice_text or ' vs ' not in choice_text:
                return None
                
            # Parse choice: "Player1 vs Player2 (X/Y) OR Player3 (X/Y)"
            parts = choice_text.split(' vs ', 1)
            friendly = parts[0].strip()
            
            options_part = parts[1]
            options = [opt.strip() for opt in options_part.split(' OR ')]
            
            # Determine which option was chosen based on decision_text
            chosen_option = options[0]  # Default
            if decision_text:
                for option in options:
                    option_name = option.split('(')[0].strip()
                    if option_name in decision_text:
                        chosen_option = option
                        break
            
            # Clean up the chosen option (remove rating info)
            opponent = chosen_option.split('(')[0].strip()
            
            return {
                'round': round_num,
                'friendly': friendly,
                'opponent': opponent,
                'rating': rating,
                'choice': f"{friendly} vs {' or '.join([opt.split('(')[0].strip() for opt in options])}",
                'decision': f"{friendly} vs {opponent}"
            }
            
        except Exception as e:
            print(f"Error creating matchup from choice and decision: {e}")
            return None
    
    def extract_opponent_from_context(self, context_text, player):
        """Extract opponent name from context text."""
        try:
            # Handle formats like "Player1 vs Player2 (X/Y) OR Player3 (X/Y)"
            if ' vs ' in context_text and ' OR ' in context_text:
                vs_part = context_text.split(' vs ')[1]  # Get everything after " vs "
                or_parts = vs_part.split(' OR ')  # Split on " OR "
                
                for part in or_parts:
                    # Extract player name (remove rating info in parentheses)
                    clean_name = part.split('(')[0].strip()
                    if clean_name != player:
                        return clean_name
            
            return "Unknown"
            
        except Exception as e:
            print(f"Error extracting opponent from context: {e}")
            return "Unknown"
    
    def extract_matchups_from_tree_structure(self, item):
        """Alternative method to extract matchups by analyzing tree structure."""
        try:
            matchups = []
            
            # Get the item text and try to understand the matchup structure
            item_text = self.treeview.tree.item(item, 'text')
            item_values = self.treeview.tree.item(item, 'values')
            
            print(f"Analyzing tree item: {item_text}")
            print(f"Item values: {item_values}")
            
            # For now, create a basic structure based on what we can extract
            if item_text and item_values:
                rating = item_values[0] if item_values else 'N/A'
                
                # Try to extract player names from the text
                if ' vs ' in item_text:
                    parts = item_text.split(' vs ')
                    friendly = parts[0].strip()
                    opponent_part = parts[1].strip()
                    
                    # Clean up opponent name (remove rating info)
                    opponent = opponent_part.split('(')[0].strip()
                    
                    matchups.append({
                        'friendly': friendly,
                        'opponent': opponent,
                        'rating': rating,
                        'path': item_text
                    })
            
            return matchups
            
        except Exception as e:
            print(f"Error in alternative matchup extraction: {e}")
            return []

    def copy_matchups_to_clipboard(self):
        """Copy the matchups text to clipboard."""
        try:
            text_content = self.matchups_text.get(1.0, tk.END).strip()
            if text_content:
                self.root.clipboard_clear()
                self.root.clipboard_append(text_content)
                messagebox.showinfo("Copied", "Matchups copied to clipboard!")
            else:
                messagebox.showwarning("No Content", "No matchup data to copy.")
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")

    def get_current_timestamp(self):
        """Get current timestamp as a formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def show_cache_statistics(self):
        """Show comprehensive cache performance statistics."""
        try:
            # Create statistics window
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Cache Performance Statistics")
            stats_window.geometry("500x400")
            stats_window.resizable(True, True)
            
            # Center the window
            stats_window.transient(self.root)
            stats_window.grab_set()
            
            # Position relative to main window
            x = self.root.winfo_x() + 100
            y = self.root.winfo_y() + 100
            stats_window.geometry(f"+{x}+{y}")
            
            # Create scrollable text area
            text_frame = tk.Frame(stats_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Text widget with scrollbar
            stats_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=stats_text.yview)
            stats_text.configure(yscrollcommand=scrollbar.set)
            
            # Pack text and scrollbar
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Get cache statistics
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                stats = self.data_cache.get_cache_stats()
            else:
                stats = {"cache_hit_rate": 0, "total_queries": 0, "cache_hits": 0}
            
            # Format statistics display
            stats_content = f"""📊 CACHE PERFORMANCE STATISTICS
{'=' * 50}

💾 DATA CACHED:
• Teams cached: {stats['teams_cached']}
• Players cached: {stats['players_cached']}
• Rating matchups cached: {stats['ratings_cached']}
• Total rating entries: {stats['total_rating_entries']}
• Comments cached: {stats['comments_cached']}

🎯 PERFORMANCE METRICS:
• Cache hits: {stats['cache_hits']:,}
• Cache misses: {stats['cache_misses']:,}
• Hit rate: {stats['hit_rate_percent']:.1f}%
• Last refresh: {stats['last_refresh']}

📈 PERFORMANCE ASSESSMENT:
"""
            
            # Add performance assessment
            hit_rate = stats['hit_rate_percent']
            if hit_rate > 80:
                stats_content += "🟢 EXCELLENT: Cache is performing optimally!\n"
                stats_content += "   Database queries reduced by 80-90%\n"
            elif hit_rate > 60:
                stats_content += "🟡 GOOD: Cache is performing well\n"
                stats_content += "   Consider preloading more common matchups\n"
            else:
                stats_content += "🔴 NEEDS IMPROVEMENT: Low cache hit rate\n"
                stats_content += "   Recommend preloading frequently used data\n"
            
            # Add query reduction estimate
            total_requests = stats['cache_hits'] + stats['cache_misses']
            if total_requests > 0:
                saved_queries = stats['cache_hits']
                stats_content += f"\n⚡ DATABASE OPTIMIZATION:\n"
                stats_content += f"   Estimated queries saved: {saved_queries:,}\n"
                stats_content += f"   Without cache: ~{total_requests * 15:,} queries\n"
                stats_content += f"   With cache: ~{stats['cache_misses'] * 15:,} queries\n"
                reduction = ((saved_queries * 15) / (total_requests * 15)) * 100 if total_requests > 0 else 0
                stats_content += f"   Query reduction: {reduction:.1f}%\n"
            
            stats_content += f"\n🔧 CACHE OPERATIONS:\n"
            stats_content += f"   • Refresh cache when teams/players change\n"
            stats_content += f"   • Cache invalidates automatically on data changes\n"
            stats_content += f"   • Preload common matchups for best performance\n"
            
            # Insert content into text widget
            stats_text.insert(tk.END, stats_content)
            stats_text.config(state=tk.DISABLED)  # Make read-only
            
            # Add buttons frame
            buttons_frame = tk.Frame(stats_window)
            buttons_frame.pack(pady=10)
            
            # Refresh cache button
            refresh_button = tk.Button(buttons_frame, text="Refresh Cache", 
                                     command=lambda: self._refresh_cache_and_update_stats(stats_window),
                                     bg="lightblue", width=15)
            refresh_button.pack(side=tk.LEFT, padx=5)
            
            # Close button
            close_button = tk.Button(buttons_frame, text="Close", 
                                   command=stats_window.destroy,
                                   bg="lightcoral", width=15)
            close_button.pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show cache statistics: {e}")
            print(f"Cache statistics error: {e}")
    
    def _refresh_cache_and_update_stats(self, stats_window):
        """Helper method to refresh cache and update statistics display"""
        try:
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                self.data_cache.refresh_base_data()
                messagebox.showinfo("Cache Refreshed", "Cache has been refreshed successfully!")
                stats_window.destroy()
                # Reopen the statistics window with updated data
                self.show_cache_statistics()
            else:
                messagebox.showerror("Error", "Data cache not available")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh cache: {e}")
            print(f"Cache refresh error: {e}")
    
    def reconnect_database(self):
        """Reconnect to database and reinitialize cache system."""
        try:
            print("🔄 User requested database reconnection...")
            
            # Attempt to reinitialize the database connection
            if hasattr(self, 'db_manager') and self.db_manager:
                print(f"📊 Current database manager: {self.db_manager}")
                
                # Test database connection with a simple query
                try:
                    test_result = self.db_manager.query_sql("SELECT COUNT(*) FROM teams")
                    print(f"✅ Database connection test successful: {test_result}")
                except Exception as db_error:
                    print(f"❌ Database connection test failed: {db_error}")
                    raise Exception(f"Database connection failed: {db_error}")
                
                # Reinitialize the cache system
                print("🔄 Reinitializing cache system...")
                self.data_cache = MatchupDataCache(self.db_manager, print_output=self.print_output)
                self.cache_error_reason = None
                print("✅ Cache system reinitialized successfully!")
                
                # Update the status bar to reflect normal mode
                self.update_status_bar()
                
                # Show success message to user
                import tkinter.messagebox as messagebox
                messagebox.showinfo("Success", 
                    "Database reconnection successful!\n\n"
                    "The application is now running in Normal Mode with full caching enabled.")
                
            else:
                raise Exception("Database manager not available")
                
        except Exception as e:
            error_msg = f"Failed to reconnect database: {e}"
            print(f"❌ {error_msg}")
            self.cache_error_reason = error_msg
            
            # Show error message to user
            import tkinter.messagebox as messagebox
            messagebox.showerror("Reconnection Failed", 
                f"Could not reconnect to database:\n\n{error_msg}\n\n"
                "The application will continue in Fallback Mode.")

    def update_status_bar(self):
        """Update the status bar to reflect current system state."""
        if hasattr(self, 'status_frame'):
            # Clear existing status bar
            for widget in self.status_frame.winfo_children():
                widget.destroy()
            
            # Recreate status bar with updated information
            # Database info
            db_name = getattr(self, 'db_name', 'Unknown')
            self.db_status = tk.Label(self.status_frame, text=f"Database: {db_name}", anchor=tk.W)
            self.db_status.pack(side=tk.LEFT, padx=5)
            
            # Cache mode indicator with error details
            if hasattr(self, 'data_cache') and self.data_cache is not None:
                cache_mode = "Normal Mode"
                cache_color = "#228B22"  # Green for normal
            else:
                cache_mode = "Fallback Mode"
                cache_color = "#FF6B35"  # Orange for fallback
                if hasattr(self, 'cache_error_reason') and self.cache_error_reason:
                    cache_mode += " (ERROR)"
                    cache_color = "#DC143C"  # Red for error
            
            self.cache_status = tk.Label(self.status_frame, text=f"• {cache_mode}", 
                                       anchor=tk.W, fg=cache_color, font=("Arial", 8, "bold"))
            self.cache_status.pack(side=tk.LEFT, padx=(10, 5))
            
            # Add reconnect button if in fallback mode
            if hasattr(self, 'data_cache') and self.data_cache is None:
                self.reconnect_btn = tk.Button(self.status_frame, text="🔄 Reconnect Database", 
                                             command=self.reconnect_database,
                                             bg="#FFA500", fg="white", font=("Arial", 8, "bold"),
                                             relief=tk.RAISED, bd=2)
                self.reconnect_btn.pack(side=tk.LEFT, padx=(5, 10))
            
            # Add tooltip for cache status
            self.create_cache_status_tooltip()
            
            # Rating system info
            system_info = f"Rating System: {self.rating_config['name']} ({self.rating_range[0]}-{self.rating_range[1]})"
            self.rating_status = tk.Label(self.status_frame, text=system_info, anchor=tk.CENTER)
            self.rating_status.pack(side=tk.LEFT, expand=True, padx=20)
            
            # Add color preview
            color_frame = tk.Frame(self.status_frame)
            color_frame.pack(side=tk.RIGHT, padx=5)
            
            tk.Label(color_frame, text="Colors:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(0, 3))
            
            for rating in sorted(self.color_map.keys()):
                color = self.color_map[rating]
                label = tk.Label(color_frame, text=f"{rating}", bg=color, width=3, font=("Arial", 7, "bold"))
                label.pack(side=tk.LEFT, padx=1)

    def force_tree_sync(self):
        """Manually trigger tree synchronization - useful for debugging."""
        if hasattr(self, 'tree_synchronizer') and self.tree_synchronizer:
            print("Manually triggering tree synchronization...")
            self.tree_synchronizer.force_full_sync()
        else:
            print("Tree synchronizer not available")
    
    def get_tree_sync_status(self):
        """Get tree synchronization status for debugging."""
        if hasattr(self, 'tree_synchronizer') and self.tree_synchronizer:
            return self.tree_synchronizer.get_sync_status()
        else:
            return {"error": "Tree synchronizer not initialized"}

if __name__ == '__main__':
    ui_manager = UiManager(
        color_map=DEFAULT_COLOR_MAP, 
        scenario_map=SCENARIO_MAP, 
        directory=os.getcwd(),
        scenario_ranges=SCENARIO_RANGES,
        scenario_to_csv_map=SCENARIO_TO_CSV_MAP
    )
    ui_manager.create_ui()
