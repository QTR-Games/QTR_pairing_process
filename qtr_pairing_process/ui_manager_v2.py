""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
from multiprocessing import Value
import os
import sys
import csv
import time
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
from qtr_pairing_process.db_load_ui import DbLoadUi
from qtr_pairing_process.database_preferences import DatabasePreferences
from qtr_pairing_process.welcome_dialog import WelcomeDialog
from qtr_pairing_process.app_logger import get_logger
from qtr_pairing_process.xlsx_load_ui import XlsxLoadUi
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.delete_team_dialog import DeleteTeamDialog
from qtr_pairing_process.create_team_dialog import CreateTeamDialog
from qtr_pairing_process.excel_management.excel_importer import ExcelImporter
from qtr_pairing_process.excel_management.simple_excel_importer import SimpleExcelImporter
from qtr_pairing_process.grid_data_model import GridDataModel
from qtr_pairing_process.comment_overlay import CommentOverlay


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
        
        # Check if running in debug mode early for FILL button visibility
        self.is_debugging = 'debugpy' in sys.modules or sys.gettrace() is not None
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Initialize database preferences manager FIRST (before rating system)
        self.db_preferences = DatabasePreferences(print_output=print_output)
        
        # Initialize rating system from unified config (KLIK_KLAK_KONFIG.json)
        # Check db_preferences first, fallback to old settings manager if not found
        config_rating_system = None
        ui_prefs = self.db_preferences.get_ui_preferences()
        config_rating_system = ui_prefs.get('rating_system')
        
        self.current_rating_system = config_rating_system or self.settings_manager.get_rating_system()
        self.rating_config = RATING_SYSTEMS[self.current_rating_system]
        self.color_map = self.rating_config['color_map']
        self.rating_range = self.rating_config['range']

        # Initialize other UI components
        self.comment_tooltip: Optional[tk.Toplevel] = None
        self.comment_indicators: Dict[tuple, tk.Label] = {}  # Store comment indicators
        self.comment_indicator_callbacks: Dict[tuple, str] = {}  # Store after_idle callback IDs
        self.row_checkboxes: List[tk.IntVar] = []
        self.column_checkboxes: List[tk.IntVar] = []
        self._updating_dropdowns = False  # Flag to prevent recursive updates
        
        # Tree synchronization state tracking
        self._tree_sync_in_progress = False  # Lock to prevent Phase 1 when triggered by Phase 2
        self._current_tree_top_player = None  # Track which player is currently at top of tree
        
        # Initialize logger
        self.logger = get_logger(__name__)
        self.logger.info("UiManager initializing...")
        
        self.select_database()
        self.initialize_ui_vars()

        if print_output:
            print(f"TKINTER VERSION: {tk.TkVersion}")
            

    def select_database(self):
        """Select database - automatically loads last used database if available"""
        # Try to load the last used database from config
        last_path, last_name = self.db_preferences.get_last_database()
        
        if last_path and last_name:
            # Validate that the saved database still exists
            if self.db_preferences.validate_database_exists(last_path, last_name):
                # Use the saved database
                self.db_path = last_path
                self.db_name = last_name
                self.db_manager = DbManager(path=self.db_path, name=self.db_name)
                self.logger.info(f"Auto-loaded last database: {self.db_name} from {self.db_path}")
                return
            else:
                self.logger.warning(f"Last used database not found: {last_name} at {last_path}")
                self.logger.info("Showing database selector...")
        
        # No saved database or it doesn't exist - show the selector
        db_load_ui = DbLoadUi()
        self.db_path, self.db_name = db_load_ui.create_or_load_database()

        if self.db_path is None:
            self.db_manager = DbManager()
        else:
            self.db_manager = DbManager(path=self.db_path, name=self.db_name)
            # Save this database as the preferred one
            if self.db_path and self.db_name:
                self.db_preferences.save_database_preference(self.db_path, self.db_name)
                self.logger.info(f"Saved database preference: {self.db_name} at {self.db_path}")
            
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

        # set frames for the matchup tree tab
        self.tree_tab_left_frame = tk.Frame(self.matchup_tree_frame)
        self.tree_tab_left_frame.pack(side=tk.LEFT)
        self.tree_tab_right_frame = tk.Frame(self.matchup_tree_frame)
        self.tree_tab_right_frame.pack(side=tk.LEFT, expand=1, fill=tk.BOTH)

        self.buttons_frame = tk.Frame(self.tree_tab_left_frame)
        self.buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # V2: Replace 144 StringVars with single GridDataModel
        self.grid_data_model = GridDataModel()
        self.grid_data_model.add_observer(self._on_grid_data_changed)
        
        # Widget references (Entry widgets only, no StringVars)
        self.grid_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        self.grid_display_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        
        # Comment overlay will be initialized after grid creation
        self.comment_overlay: Optional[CommentOverlay] = None
        
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

        # create treeview and tree generator
        self.treeview = LazyTreeView(master=self.tree_tab_right_frame, print_output=self.print_output, columns=("Rating", "Sort Value"))
        self.tree_generator = TreeGenerator(treeview=self.treeview, sort_alpha=self.sort_alpha.get())
        
        # Track current sorting mode for column display
        self.current_sort_mode = "none"
        
        # Matchup output panel will be created lazily when generating combinations
        self.matchup_output_panel_created = False
        
        # Track Team Grid initialization (lazy load only the heavy Team Grid tab)
        self.team_grid_initialized = False

    
    def _populate_dropdowns(self):
        """Populate dropdowns after UI is visible (deferred for performance)"""
        self.set_team_dropdowns()
        self.update_scenario_box()
    
    def on_tab_switch(self, event):
        """Initialize Team Grid tab on first access with timing"""
        start_time = None
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            
            # Start timing in debug mode
            if self.is_debugging:
                start_time = time.perf_counter()
                print(f"\n[TAB SWITCH] Switching to '{current_tab}' tab...")
            
            if current_tab == "Team Grid":
                self.init_team_grid_if_needed()
            
            # Force all UI updates to complete before measuring time
            if self.is_debugging and start_time is not None:
                self.root.update_idletasks()  # Process all pending UI events
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                print(f"[TAB SWITCH] '{current_tab}' tab fully rendered in {elapsed_ms:.2f}ms\n")
                
        except Exception as e:
            print(f"Error in tab switch: {e}")
    
    def init_team_grid_if_needed(self):
        """Initialize Team Grid tab content only once, on first access"""
        if self.team_grid_initialized:
            if self.is_debugging:
                print("[TAB SWITCH] Team Grid already initialized (cached)")
            return
        
        init_start = None
        if self.is_debugging:
            init_start = time.perf_counter()
            print("[TAB SWITCH] Initializing Team Grid content (60 dropdowns)...")
        
        # Create Round Selection section (60 dropdowns)
        self.create_team_grid_round_selection()
        self.team_grid_initialized = True
        
        if self.is_debugging and init_start is not None:
            # Force rendering to complete before measuring
            self.root.update_idletasks()
            init_elapsed_ms = (time.perf_counter() - init_start) * 1000
            print(f"[TAB SWITCH] Team Grid initialization fully rendered in {init_elapsed_ms:.2f}ms")
    
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
        
        # Defer team dropdowns and scenario box population to after UI is shown
        self.root.after(10, self._populate_dropdowns)

        # Add essential buttons to a row just above the pairing grid       
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Flip Grid", command=lambda: self.flip_grid_perspective()).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Data Management menu button
        data_mgmt_button = tk.Button(self.button_row_frame, text="Data Management", 
                                   command=lambda: self.show_data_management_menu(),
                                   bg="lightcyan", fg="darkgreen", font=("Arial", 9, "bold"),
                                   relief=tk.RAISED, borderwidth=2)
        data_mgmt_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Clear button for round dropdowns
        clear_button = tk.Button(self.button_row_frame, text="Clear",
                               command=lambda: self.clear_round_dropdowns(),
                               bg="lightyellow", fg="darkred", font=("Arial", 9, "bold"),
                               relief=tk.RAISED, borderwidth=2)
        clear_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # FILL button (only visible in debug mode) - for testing convenience
        self.fill_button = tk.Button(self.button_row_frame, text="FILL",
                               command=lambda: self.fill_round_dropdowns(),
                               bg="lightgreen", fg="darkblue", font=("Arial", 9, "bold"),
                               relief=tk.RAISED, borderwidth=2)
        # Only pack if in debug mode (will be checked after is_debugging is set)
        if hasattr(self, 'is_debugging') and self.is_debugging:
            self.fill_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Initialize round tracking variables
        self.round_dropdowns = []
        self.round_vars = []
        self.enemy_round_dropdowns = []
        self.enemy_round_vars = []
        self.selected_players_per_round = {}
        
        # Configure Treeview with style
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10))
        self.treeview.tree.heading("#0", text="Pairing")
        self.treeview.tree.heading("Rating", text="Rating")
        self.treeview.tree.heading("Sort Value", text="Sort Value")
        
        # Configure column widths
        self.treeview.tree.column("Rating", width=80, minwidth=50)
        self.treeview.tree.column("Sort Value", width=100, minwidth=80)
        self.treeview.tree.tag_configure('1', background="orangered")
        self.treeview.tree.tag_configure('2', background="orange")
        self.treeview.tree.tag_configure('3', background="yellow")
        self.treeview.tree.tag_configure('4', background="greenyellow")
        self.treeview.tree.tag_configure('5', background="lime")
        self.treeview.pack(expand=1, fill='both')
        
        # Create Generate Combinations button
        generateButton = tk.Button(self.buttons_frame, text="Generate\nCombinations", command=self.on_generate_combinations)
        generateButton.pack(fill=tk.X, pady=5)

        # Initialize sorting state tracking
        self.active_sort_mode = None
        
        # Create sorting buttons with active/inactive states
        self.cumulative_button = tk.Button(self.buttons_frame, text="🔴 Cumulative\nSort", command=self.toggle_cumulative_sort)
        self.cumulative_button.pack(fill=tk.X, pady=5)

        self.confidence_button = tk.Button(self.buttons_frame, text="🔴 Highest\nConfidence", command=self.toggle_confidence_sort)
        self.confidence_button.pack(fill=tk.X, pady=5)

        self.counter_button = tk.Button(self.buttons_frame, text="🔴 Counter\nPick", command=self.toggle_counter_sort)
        self.counter_button.pack(fill=tk.X, pady=5)
        
        # Set initial button states (all inactive)
        self.update_sort_button_states()
        
        # Add tooltip
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here\nNavigate the tree with arrow keys!")
        
        # Matchup output panel will be created on first combination generation
        
        # Bind tab switch for lazy Team Grid initialization
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_switch)
        
        # Initialize Team Grid tab content on first access (default tab)
        self.root.after(1, self.init_team_grid_if_needed)

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")

        self.update_combobox_colors()
        self.init_display_headers()
        
        # Create status bar
        self.create_status_bar()
        
        # Show welcome dialog if this is first time or user hasn't disabled it
        if self.db_preferences.should_show_welcome_message():
            self.root.after(500, self.show_welcome_dialog)  # Delay to ensure UI is ready

        self.root.mainloop()

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

        # V2: Create the 6x6 rating grid WITHOUT StringVars or bindings
        # All state managed by GridDataModel, events by CommentOverlay
        for r in range(6):
            for c in range(6):
                # Rating grid entries (columns 0-5) - no textvariable, no bindings
                entry = tk.Entry(self.grid_frame, width=8, 
                               font=("Arial", 10), relief=tk.SOLID, borderwidth=1)
                entry.grid(row=r + 2, column=c, padx=1, pady=1, sticky="nsew", ipadx=2, ipady=2)
                self.grid_widgets[r][c] = entry
                
                # V2: Manual synchronization with GridDataModel (no trace callbacks)
                # We'll use FocusOut event for manual synchronization
                entry.bind("<FocusOut>", lambda event, row=r, col=c: self._sync_entry_to_model(row, col, event.widget))
                entry.bind("<Return>", lambda event, row=r, col=c: self._sync_entry_to_model(row, col, event.widget))
                
                # Set initial value from model (Phase 1: handle None → '')
                initial_value = self.grid_data_model.get_rating(r, c)
                if initial_value is None:
                    entry.insert(0, '')
                else:
                    entry.insert(0, str(initial_value))

        # Create the display grid (right side of unified grid, columns 7-12)
        for r in range(6):
            for c in range(6):
                # Display grid entries (columns 7-12) - no textvariable
                display_entry = tk.Entry(self.grid_frame, width=8, 
                                       state='readonly', font=("Arial", 10), relief=tk.SOLID, borderwidth=1,
                                       readonlybackground="lightgray")
                display_entry.grid(row=r + 2, column=c + 7, padx=1, pady=1, sticky="nsew", ipadx=2, ipady=2)
                self.grid_display_widgets[r][c] = display_entry
                
                # Set initial value from model
                display_entry.config(state='normal')
                display_entry.delete(0, tk.END)
                display_entry.insert(0, self.grid_data_model.get_display(r, c))
                display_entry.config(state='readonly')

        # Use minimal grid weights to reduce resize lag
        for i in range(2, 8):  # rows 2-7 for grid data
            self.grid_frame.grid_rowconfigure(i, weight=0)  # Fixed height
        for i in range(13):  # columns 0-12
            self.grid_frame.grid_columnconfigure(i, weight=0)  # Fixed width

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
        self.grid_frame.grid_rowconfigure(8, weight=0)
        self.grid_frame.grid_rowconfigure(9, weight=0)
        self.grid_frame.grid_columnconfigure(6, weight=0)
        self.grid_frame.grid_columnconfigure(13, weight=0)
        
        # V2: Initialize CommentOverlay after grid creation (replaces 75 mouse bindings)
        self.comment_overlay = CommentOverlay(
            parent_frame=self.grid_frame,
            grid_data_model=self.grid_data_model,
            comment_editor_callback=self._open_comment_editor_for_cell
        )
        
        # Calculate and set grid geometry for overlay
        self.root.after(100, self._update_comment_overlay_geometry)

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
                # V2: Update data model and display
                self.grid_data_model.set_cell_disabled(row, col, True)
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.column_checkboxes[col-1].get() == 0:  # Column checkbox is also unchecked
                    widget.config(state='normal')
                    self.grid_data_model.set_cell_disabled(row, col, False)
                    # V2: No need to call update_color_on_change explicitly - observer handles it
        self.on_scenario_calculations()

    def on_column_checkbox_change(self, col, var):
        print(f"Column {col} checkbox changed to {var.get()}")
        for row in range(1,6):
            widget = self.grid_widgets[row][col]
            if var.get() == 1:  # Checkbox is checked
                widget.config(state='disabled', bg='grey')
                # V2: Update data model and display
                self.grid_data_model.set_cell_disabled(row, col, True)
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.row_checkboxes[row-1].get() == 0:  # Row checkbox is also unchecked
                    widget.config(state='normal')
                    self.grid_data_model.set_cell_disabled(row, col, False)
                    # V2: Observer handles color update
        self.on_scenario_calculations()

    def update_combobox_colors(self):
        for row in range(1, 6):
            for col in range(1, 6):
                # V2: Read from GridDataModel
                value = self.grid_data_model.get_rating(row, col)
                widget = self.grid_widgets[row][col]
                if widget and value in self.color_map:
                    widget.config(bg=self.color_map[value])

    def update_color_on_change(self, var, index, mode, row, col):
        # V2: var parameter no longer used (kept for compatibility with existing callers)
        if self.row_checkboxes and row-1 < len(self.row_checkboxes) and self.row_checkboxes[row-1].get() == 1:
            return  # Skip updating color if row checkbox is checked
        if self.column_checkboxes and col-1 < len(self.column_checkboxes) and self.column_checkboxes[col-1].get() == 1:
            return  # Skip updating color if column checkbox is checked
        
        # V2: Get value from GridDataModel (may be int or str)
        value = self.grid_data_model.get_rating(row, col)
        # Convert to string for color map lookup
        value_str = str(value) if value != '' else ''
        widget = self.grid_widgets[row][col]
        
        # Check if cell has comment (comment indicator takes precedence)
        if self.grid_data_model.has_comment(row, col):
            widget.config(bg='#ffffcc')  # Light yellow for comments
        elif widget and value_str in self.color_map:
            widget.config(bg=self.color_map[value_str])
        elif widget:
            widget.config(bg='white')
    
    def update_grid_colors(self):
        """Update all grid cell colors based on current rating system"""
        for row in range(1, 6):
            for col in range(1, 6):
                # V2: Get value from GridDataModel (may be int or str)
                value = self.grid_data_model.get_rating(row, col)
                value_str = str(value) if value != '' else ''
                widget = self.grid_widgets[row][col]
                
                # Check for comment indicator first
                if self.grid_data_model.has_comment(row, col):
                    widget.config(bg='#ffffcc')
                elif widget and value_str in self.color_map:
                    widget.config(bg=self.color_map[value_str])
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
    
    def update_status_bar(self):
        """Update status bar information"""
        if hasattr(self, 'rating_status'):
            system_info = f"Rating System: {self.rating_config['name']} ({self.rating_range[0]}-{self.rating_range[1]})"
            self.rating_status.config(text=system_info)
        
        if hasattr(self, 'db_status'):
            db_name = getattr(self, 'db_name', 'Unknown')
            self.db_status.config(text=f"Database: {db_name}")
        
        # Recreate color preview with new colors
        if hasattr(self, 'status_frame'):
            # Remove old color frame
            for widget in self.status_frame.winfo_children():
                if isinstance(widget, tk.Frame) and widget.winfo_children():
                    # Check if this frame contains color boxes
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and child.cget('text') in self.color_map:
                            widget.destroy()
                            break
            
            # Add new color frame
            color_frame = tk.Frame(self.status_frame)
            color_frame.pack(side=tk.RIGHT, padx=5)
            
            tk.Label(color_frame, text="Colors:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(0, 3))
            
            for rating in sorted(self.color_map.keys()):
                color_box = tk.Label(color_frame, text=rating, bg=self.color_map[rating], 
                                   width=2, relief=tk.RAISED, borderwidth=1, font=("Arial", 7, "bold"))
                color_box.pack(side=tk.LEFT, padx=1)
    
    # Add this method to update display-only fields
    def update_display_fields(self, row, col, value):
        try:
            # V2: Update GridDataModel display value
            self.grid_data_model.set_display(row, col, str(value), notify=True)
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
        # Guard: Don't run calculations if teams are not selected
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()
        
        if not team_1 or not team_2:
            # Clear display fields when no teams are selected
            for row in range(1, 6):
                for col in range(0, 6):
                    self.update_display_fields(row, col, "---")
            return
        
        self.set_floor_values()  # info_col 0
        self.check_pinned_players()  # info_col 1
        self.check_for_pins()  # info_col 2
        self.check_protect()  # info_col 3
        self.check_margins()  # info_col 4 & 5
        self.update_comment_indicators()  # Update comment visual indicators

    def check_margins(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    for col in range(4, 6):
                        self.update_display_fields(row, col, "---")
                    continue
                
                # V2: Get floor value from GridDataModel
                floor_value = self.grid_data_model.get_display(row, 0)
                if not floor_value or floor_value == "---" or floor_value.strip() == "":
                    for col in range(4, 6):
                        self.update_display_fields(row, col, "---")
                    continue
                floor_rating_sum = int(floor_value)
                
                all_margins = []
                for col in range(1, 6):
                    col_margin_sum = 0
                    for row1 in range(1, 6):
                        widget = self.grid_widgets[row1][col]
                        if widget is not None and widget.cget('state') != 'disabled':
                            # V2: Get integer value directly from GridDataModel
                            cell_value = self.grid_data_model.get_rating(row1, col)
                            if isinstance(cell_value, int):
                                col_margin_sum += cell_value
                    diff = floor_rating_sum - col_margin_sum
                    all_margins.append(diff)
                
                max_margin = max(all_margins)
                min_margin = min(all_margins)
                margin_text = f"{max_margin} | {min_margin}"
                self.update_display_fields(row, 4, margin_text)
                sum_margins = sum(all_margins)
                self.update_display_fields(row, 5, sum_margins)
            except (ValueError, IndexError) as e:
                print(f"check_margins has failed for row {row} with error:\n{e}")

    def check_protect(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 3, "---")
                    continue
                # V2: Read from GridDataModel
                row_pinned = self.grid_data_model.get_display(row, 1) != "---"
                row_pinner = self.grid_data_model.get_display(row, 2) != "---"
                protect = "Yes" if row_pinned or row_pinner else "No"
                self.update_display_fields(row, 3, protect)
            except (ValueError, IndexError) as e:
                print(f"check_protect has failed for row {row} with error:\n{e}")

    def check_for_pins(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 2, "---")
                    continue
                good_matchups = 0
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        # V2: Get integer value directly from GridDataModel
                        cell_value = self.grid_data_model.get_rating(row, col)
                        if isinstance(cell_value, int) and cell_value > 3:
                            good_matchups += 1
                can_pin = "PIN" if good_matchups > 1 else "---"
                self.update_display_fields(row, 2, can_pin)
            except (ValueError, IndexError) as e:
                print(f"check_for_pins has failed for row {row} with error:\n{e}")

    def check_pinned_players(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 1, "---")
                    continue
                num_bad_matchups = 0
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        # V2: Get integer value directly from GridDataModel
                        cell_value = self.grid_data_model.get_rating(row, col)
                        if isinstance(cell_value, int) and cell_value < 3:
                            num_bad_matchups += 1
                player_pinned = "PINNED!" if num_bad_matchups > 1 else "---"
                self.update_display_fields(row, 1, player_pinned)
            except (ValueError, IndexError) as e:
                print(f"check_pinned_players has failed for row {row} with error:\n{e}")

    def set_floor_values(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row-1 < len(self.row_checkboxes) and self.row_checkboxes[row-1].get() == 1:
                    self.update_display_fields(row, 0, "---")
                    continue
                floor_rating_sum = 0
                for col in range(1, 6):
                    widget = self.grid_widgets[row][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        # V2: Get integer value directly from GridDataModel
                        cell_value = self.grid_data_model.get_rating(row, col)
                        if isinstance(cell_value, int):
                            floor_rating_sum += cell_value
                self.update_display_fields(row, 0, floor_rating_sum)
            except (ValueError, IndexError) as e:
                print(f"set_floor_values has failed with error:\n{e}")

    def show_welcome_dialog(self):
        """Show welcome dialog on first startup"""
        try:
            welcome = WelcomeDialog(self.root)
            show_again = welcome.show_welcome_message()
            
            # Save preference
            self.db_preferences.set_welcome_message_preference(show_again)
            
            # If user chose to open settings, show data management menu
            if hasattr(welcome, 'result') and welcome.result == "open_settings":
                self.show_data_management_menu()
        except Exception as e:
            self.logger.error(f"Error showing welcome dialog: {e}", exc_info=True)
    
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
                messagebox.showinfo("Database Changed", f"Successfully switched to: {db_name}\n\nThis database will be loaded automatically on next startup.")
                
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
                
                # Save to unified config (KLIK_KLAK_KONFIG.json)
                self.db_preferences.update_ui_preferences({'rating_system': new_system})
                
                # Also save to old settings for backward compatibility
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
            rating_system_button.pack(pady=(3, 10))
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
        # Create matchup output panel on first use
        if not self.matchup_output_panel_created:
            self.create_matchup_output_panel()
            self.matchup_output_panel_created = True
        
        fNames, oNames = self.prep_names()
        fRatings, oRatings = self.prep_ratings(fNames,oNames)
        if self.print_output:
            print(f"fRatings: {fRatings}\n")
            print(f"oRatings: {oRatings}\n")
        self.validate_grid_data()
        if self.team_b.get():
            self.tree_generator.generate_combinations(fNames, oNames, fRatings, oRatings)
        else:
            self.tree_generator.generate_combinations(oNames, fNames, oRatings, fRatings)
        
        # Automatically expand the root "Pairings" node
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            self.treeview.tree.item(root_nodes[0], open=True)
        
        # Reset all sorting states when generating new combinations
        self.active_sort_mode = None
        self.is_sorted = False
        self.current_sort_mode = "none"
        self.treeview.tree.heading("Sort Value", text="Sort Value")
        self.update_sort_value_column()
        self.update_sort_button_states()
        
    def sort_by_confidence(self):
        """Sort tree by risk-adjusted confidence scores"""
        self.tree_generator.sort_by_risk_adjusted_confidence()
        self.current_sort_mode = "confidence"
        self.active_sort_mode = "confidence"
        self.treeview.tree.heading("Sort Value", text="Confidence Score")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()

    def sort_by_counter_resistance(self):
        """Sort tree by counter-resistance against opponent strategies"""
        self.tree_generator.sort_by_opponent_response_simulation()
        self.current_sort_mode = "resistance"
        self.active_sort_mode = "resistance"
        self.treeview.tree.heading("Sort Value", text="Resistance Score")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()

    def sort_by_cumulative(self):
        """Sort tree by cumulative value"""
        self.tree_generator.sort_by_cumulative_value()
        self.current_sort_mode = "cumulative"
        self.active_sort_mode = "cumulative"
        self.treeview.tree.heading("Sort Value", text="Cumulative Value")
        self.update_sort_value_column()
        self.is_sorted = True
        self.update_sort_button_states()
    
    def unsort_tree(self):
        """Remove all sorting and return to default order"""
        self.tree_generator.unsort_tree()
        self.current_sort_mode = "none"
        self.active_sort_mode = None
        self.treeview.tree.heading("Sort Value", text="Sort Value")
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
    
    def update_sort_button_states(self):
        """Update button appearance to show active/inactive states"""
        # Reset all buttons to inactive state (dim red circle)
        self.cumulative_button.config(text="⭕ Cumulative\nSort", relief=tk.RAISED, bg='SystemButtonFace')
        self.confidence_button.config(text="⭕ Highest\nConfidence", relief=tk.RAISED, bg='SystemButtonFace')
        self.counter_button.config(text="⭕ Counter\nPick", relief=tk.RAISED, bg='SystemButtonFace')
        
        # Set active button to bright red circle and pressed appearance
        if self.active_sort_mode == "cumulative":
            self.cumulative_button.config(text="🔴 Cumulative\nSort", relief=tk.SUNKEN, bg='lightcoral')
        elif self.active_sort_mode == "confidence":
            self.confidence_button.config(text="🔴 Highest\nConfidence", relief=tk.SUNKEN, bg='lightcoral')
        elif self.active_sort_mode == "resistance":
            self.counter_button.config(text="🔴 Counter\nPick", relief=tk.SUNKEN, bg='lightcoral')

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
            # print(f"Scenario changed from {self.previous_value} to {new_value}\nLOADING NEW SCENARIO DATA\n")
            self.previous_value = new_value
            try:
                self.update_ui()
            except (ValueError, IndexError) as e:
                print(f"scenario_box_change error: {e}")

    def on_team_box_change(self, *args):
        # Get the new value
        new_team1_value = self.team1_var.get()
        new_team2_value = self.team2_var.get()
        perform_update = False
        # Compare with the previous value
        if new_team1_value != self.previous_team1:
            self.previous_team1 = new_team1_value
            perform_update = True
        if new_team2_value != self.previous_team2:
            self.previous_team2 = new_team2_value
            perform_update = True
        if perform_update:
            try:
                self.update_ui()
                # Update round dropdowns when team changes
                self.update_round_dropdown_options()
                # Trigger scenario calculations to populate the grid on the right
                self.on_scenario_calculations()
            except (ValueError,IndexError) as e:
                print(f"team_box_change error: {e}")
            
    

    ####################
    # DB Fill/Save Funcs
    ####################

    def update_ui(self):
        # Update the team dropdowns and grid values
        self.set_team_dropdowns()
        self.load_grid_data_from_db()
        # print(self.extract_ratings())

    def select_team_names(self):
        # Using this for testing.
        # Possibly remove this later.
        sql = 'select team_name from teams'
        teams = self.db_manager.query_sql(sql)
        team_names = [t[0] for t in teams]
        if not team_names:
            team_names = ['No teams Found']
        return team_names

    def set_team_dropdowns(self):
        team_names = self.select_team_names()
        self.combobox_1['values'] = team_names
        self.combobox_2['values'] = team_names
        
        # DEBUG MODE AUTO-POPULATION:
        # When running under a debugger, automatically load the first two teams to reduce
        # manual clicking during development testing.
        # 
        # Detection Method: sys.gettrace() returns a trace function when Python's trace/debug
        # mechanism is active. This works with most Python debuggers including:
        # - VS Code's debugpy (current development environment)
        # - PyCharm debugger
        # - pdb (Python's built-in debugger)
        # - Most IDE debuggers that use Python's trace mechanism
        #
        # Known Limitations:
        # - May also trigger when code coverage tools or profilers are running
        # - Some custom debuggers might not use Python's trace mechanism
        # - Not 100% universal across all debugging environments
        #
        # Alternative Implementation (if needed):
        # If more explicit control is needed, could use environment variable:
        #   if os.getenv('DEBUG_MODE') == 'true':
        # Then set in launch.json: "env": {"DEBUG_MODE": "true"}
        #
        # Decision: Current approach sufficient for single-developer workflow.
        import sys
        
        # Check if debugpy (VS Code debugger) is loaded
        # This is more reliable than sys.gettrace() for VS Code debugging
        # since gettrace() may not be active during early initialization
        is_debugging = 'debugpy' in sys.modules or sys.gettrace() is not None
        
        # Update debug mode flag (already set in __init__ but recheck here for auto-population)
        self.is_debugging = is_debugging
        
        print(f"DEBUG: debugpy in sys.modules = {'debugpy' in sys.modules}")
        print(f"DEBUG: sys.gettrace() = {sys.gettrace()}")
        print(f"DEBUG: is_debugging = {is_debugging}")
        print(f"DEBUG: Number of teams available: {len(team_names)}")
        print(f"DEBUG: Teams: {team_names[:5] if len(team_names) > 5 else team_names}")
        
        if is_debugging:
            print("DEBUG: Debugger detected - auto-populating teams")
            if len(team_names) >= 2:
                self.combobox_1.set(team_names[0])
                self.combobox_2.set(team_names[1])
                print(f"DEBUG: Set Team 1: {team_names[0]}, Team 2: {team_names[1]}")
                # Trigger data load after setting teams (100ms delay ensures UI is ready)
                self.root.after(100, self.load_grid_data_from_db)
            else:
                print("DEBUG: Not enough teams in database to auto-populate")
        else:
            print("DEBUG: No debugger detected - skipping auto-population")

    def load_grid_data_from_db(self):
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()
        
        # Guard: Don't try to load data if teams are not selected
        if not team_1 or not team_2:
            return
        
        scenario = self.scenario_box.get()[:1]
        if scenario == '':
            self.scenario_box.set("0 - Neutral")
            scenario = self.scenario_box.get()[:1]
        scenario_id = int(scenario)

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        if not team_1_row:
            print(f"Team '{team_1}' not found in database")
            return
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        if not team_2_row:
            print(f"Team '{team_2}' not found in database")
            return
        team_2_id = team_2_row[0][0]

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {row[0]:{'position':i+1,'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {row[0]:{'position':i+1,'name':row[1]}for i,row in enumerate(team_2_players)}
        
        ratings_sql = f"""
            SELECT
                team_1_player_id,
                team_2_player_id,
                rating,
                team_1_id,
                team_2_id
            FROM
                ratings
            WHERE
                team_1_player_id IN ({','.join([str(x) for x in team_1_dict.keys()])})
              AND
                team_2_player_id IN ({','.join([str(x) for x in team_2_dict.keys()])})
              AND
                team_1_id = {team_1_id}
              AND
                team_2_id = {team_2_id}
              AND
                scenario_id = {scenario_id}
            ORDER BY
                team_1_player_id, team_2_player_id
        """

        ratings_rows = self.db_manager.query_sql(ratings_sql)
        
        # V2: Use batch mode for efficient GridDataModel updates
        self.grid_data_model.begin_batch()
        
        # Update usernames (header row and column)
        for _, row_dict in team_2_dict.items():
            pos = row_dict['position']
            if 0 <= pos < 6:
                self.grid_data_model.set_rating(0, pos, row_dict['name'], notify=False)
        
        for _, row_dict in team_1_dict.items():
            pos = row_dict['position']
            if 0 <= pos < 6:
                self.grid_data_model.set_rating(pos, 0, row_dict['name'], notify=False)

        # Update ratings
        for r, row in enumerate(ratings_rows):
            team_1_pos = team_1_dict[row[0]]['position']
            team_2_pos = team_2_dict[row[1]]['position']
            if 0 <= team_1_pos < 6 and 0 <= team_2_pos < 6:
                # Store as integer for efficient calculations
                self.grid_data_model.set_rating(team_1_pos, team_2_pos, int(row[2]), notify=False)
        
        # End batch mode
        self.grid_data_model.end_batch()
        
        # Manually notify observers that grid has been loaded (notify=False above means no events queued)
        self.grid_data_model._notify_observers('grid_loaded')
        
        # Update comment indicators after loading grid data
        self.update_comment_indicators()
        
        # Auto-generate tree after both teams are loaded
        self.auto_generate_tree_after_teams_loaded()
        
    def auto_generate_tree_after_teams_loaded(self):
        """
        Automatically generate the matchup tree after both teams are loaded.
        This prevents first-interaction lag by pre-generating the tree structure.
        Only generates if tree doesn't already exist.
        """
        try:
            # Check if tree already exists
            root_nodes = self.treeview.tree.get_children()
            if root_nodes and len(root_nodes) > 0:
                # Tree already exists, don't regenerate
                return
            
            # Generate the tree silently in the background
            self.on_generate_combinations()
            print("Auto-generated matchup tree after teams loaded")
            
        except Exception as e:
            # Don't block UI if generation fails
            print(f"Warning: Auto-generation of tree failed: {e}")
        
    def save_grid_data_to_db(self):
        # Prevent saving when grid is flipped to opponent's perspective
        if self.grid_is_flipped:
            messagebox.showwarning("Cannot Save", 
                "Cannot save data while grid is flipped to opponent's perspective.\n"
                "Please click 'Flip Grid' again to restore friendly perspective before saving.")
            return
        
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()
        
        # Guard: Don't try to save data if teams are not selected
        if not team_1 or not team_2:
            messagebox.showwarning("Cannot Save", 
                "Please select both teams before saving.")
            return
        
        scenario_id = int(self.scenario_box.get()[:1])

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        if not team_1_row:
            print(f"Team '{team_1}' not found in database")
            return
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        if not team_2_row:
            print(f"Team '{team_2}' not found in database")
            return
        team_2_id = team_2_row[0][0]

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {i+1:{'id':row[0],'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {i+1:{'id':row[0],'name':row[1]}for i,row in enumerate(team_2_players)}

        # V2: Read from GridDataModel instead of StringVars
        for row in range(1, 6):
            for col in range(1, 6):
                rating_value = self.grid_data_model.get_rating(row, col)
                if not rating_value:
                    continue
                try:
                    # Convert to int if needed
                    if isinstance(rating_value, str):
                        rating = int(rating_value)
                    else:
                        rating = rating_value
                    
                    team_1_player_id = team_1_dict[row]['id']
                    team_2_player_id = team_2_dict[col]['id']
                    self.db_manager.upsert_rating(
                        player_id_1=team_1_player_id,
                        player_id_2=team_2_player_id,
                        team_id_1=team_1_id,
                        team_id_2=team_2_id,
                        scenario_id=scenario_id,
                        rating=rating
                    )
                except (ValueError, IndexError) as e:
                    print(f"Error saving rating at ({row}, {col}): {e}")
                    continue 

    def add_team_to_db(self):
        # Use the main window as parent for the dialog
        team_name = simpledialog.askstring("Input", "Enter the team name:", parent=self.root)
        if team_name:
            self.db_manager.create_team(team_name)
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
        # V2: Read from GridDataModel
        fNames = [self.grid_data_model.get_rating(i, 0) for i in range(1, 6)]
        oNames = [self.grid_data_model.get_rating(0, i) for i in range(1, 6)]
        return fNames, oNames

    def prep_ratings(self,fNames,oNames):
        # V2: Read from GridDataModel
        fRatings = {fNames[i]: {oNames[j]: self.grid_data_model.get_rating(i+1, j+1) for j in range(5)} for i in range(5)}
        oRatings = {oNames[i]: {fNames[j]: self.grid_data_model.get_rating(j+1, i+1) for j in range(5)} for i in range(5)}
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

    def validate_grid_data(self):
        """Validate grid data based on current rating system"""
        min_rating, max_rating = self.rating_range
        valid_ratings = list(range(min_rating, max_rating + 1))
        
        for row in range(1, 6):
            for col in range(1, 6):
                # V2: Read from GridDataModel (may be int or str)
                value = self.grid_data_model.get_rating(row, col)
                # Convert to int for validation if it's a string digit
                if isinstance(value, str) and value.strip().isdigit():
                    value = int(value)
                
                if isinstance(value, int) and value not in valid_ratings:
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
        # V2: Read from GridDataModel
        return [self.grid_data_model.get_rating(0, col) for col in range(1, 6)]

    def get_friendly_player_names(self):
        # V2: Read from GridDataModel
        return [self.grid_data_model.get_rating(row, 0) for row in range(1, 6)]
    
    def get_enemy_player_names(self):
        """Get enemy/opponent player names from grid."""
        return self.get_opponent_player_names()
    
    def extract_ratings(self):
        ratings = {}
        fNames = self.get_friendly_player_names()
        oNames = self.get_opponent_player_names()
        for row in range(1, 6):
            # V2: Read from GridDataModel
            player = self.grid_data_model.get_rating(row, 0)
            ratings[player] = {}
            for col in range(1, 6):
                opponent = self.grid_data_model.get_rating(0, col)
                rating_value = self.grid_data_model.get_rating(row, col)
                # Store integer directly
                if isinstance(rating_value, int):
                    ratings[player][opponent] = rating_value
        return ratings

    # Comment functionality methods
    def check_comment_exists(self, row, col):
        """Check if a comment exists for a specific cell without showing tooltip"""
        try:
            # Get current team and scenario information
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()
            
            # V2: Get player names from GridDataModel
            friendly_player = self.grid_data_model.get_rating(row, 0)
            opponent_player = self.grid_data_model.get_rating(0, col)
            
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
        # Cancel all pending callbacks first
        if hasattr(self, 'comment_indicator_callbacks'):
            for callback_id in self.comment_indicator_callbacks.values():
                try:
                    self.root.after_cancel(callback_id)
                except:
                    pass  # Callback may have already executed
            self.comment_indicator_callbacks.clear()
        else:
            self.comment_indicator_callbacks = {}
        
        # Now destroy the indicator widgets
        if hasattr(self, 'comment_indicators'):
            for indicator in self.comment_indicators.values():
                try:
                    if indicator.winfo_exists():
                        indicator.destroy()
                except:
                    pass  # Widget may already be destroyed
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
            
            # Schedule positioning after the widget is drawn and store callback ID
            callback_id = self.root.after_idle(lambda: self.position_comment_indicator(indicator, row, col))
            self.comment_indicator_callbacks[(row, col)] = callback_id
            
        except Exception as e:
            print(f"Error adding comment indicator at ({row}, {col}): {e}")

    def position_comment_indicator(self, indicator, row, col):
        """Position the comment indicator in the top-right corner of the cell"""
        try:
            # First check if indicator still exists (might have been cleared)
            if not indicator.winfo_exists():
                return
            
            widget = self.grid_widgets[row][col]
            if widget is not None and widget.winfo_exists():
                # Position the indicator in the top-right corner
                indicator.place(
                    in_=widget,
                    anchor="ne",
                    relx=1.0,  # Right edge
                    rely=0.0,  # Top edge
                    x=-2,      # Slight offset from edge
                    y=2        # Slight offset from edge
                )
        except Exception as e:
            # Silently handle errors - widget may have been destroyed
            try:
                if indicator.winfo_exists():
                    indicator.destroy()
            except:
                pass  # Widget already destroyed

    def show_comment_tooltip(self, event, row, col):
        """[DEPRECATED V2] CommentOverlay handles tooltips now. Kept for compatibility."""
        # V2: CommentOverlay handles tooltip display via canvas events
        # This method kept for compatibility but not used
        pass

    def hide_comment_tooltip(self, event=None):
        """[DEPRECATED V2] CommentOverlay handles tooltips. Kept for compatibility."""
        # V2: CommentOverlay handles tooltip hiding
        pass

    def open_comment_editor(self, event, row, col):
        """[DEPRECATED V2] Use _open_comment_editor_for_cell. Kept for compatibility."""
        # V2: CommentOverlay calls _open_comment_editor_for_cell directly
        # Redirect to new method
        self._open_comment_editor_for_cell(row, col)

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
            
            # Update the Sort Value column (second column, index 1)
            current_values = list(self.treeview.tree.item(child, 'values'))
            if len(current_values) < 2:
                current_values.append(sort_value)
            else:
                current_values[1] = sort_value
            
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
                # Phase 1: Use snapshot API for cleaner state management
                self.flip_snapshot = self.grid_data_model.get_state_snapshot()
                
                self.grid_data_model.begin_batch()
                
                # 1. Swap team player names
                friendly_names = [self.grid_data_model.get_rating(row, 0) for row in range(1, 6)]
                enemy_names = [self.grid_data_model.get_rating(0, col) for col in range(1, 6)]
                
                # Swap the names
                for row in range(1, 6):
                    if row - 1 < len(enemy_names):
                        self.grid_data_model.set_rating(row, 0, enemy_names[row - 1], notify=False)
                
                for col in range(1, 6):
                    if col - 1 < len(friendly_names):
                        self.grid_data_model.set_rating(0, col, friendly_names[col - 1], notify=False)
                
                # 2. Flip ratings around 3 (1↔5, 2↔4, 3 stays 3)
                for row in range(1, 6):
                    for col in range(1, 6):
                        current_value = self.grid_data_model.get_rating(row, col)
                        if isinstance(current_value, int):
                            # Flip around 3: new_rating = 6 - old_rating
                            flipped_rating = 6 - current_value
                            self.grid_data_model.set_rating(row, col, flipped_rating, notify=False)
                
                self.grid_data_model.end_batch()
                self.grid_is_flipped = True
                print("Grid flipped to opponent's perspective")
                
            else:
                # Phase 1: Restore using snapshot API
                if hasattr(self, 'flip_snapshot') and self.flip_snapshot:
                    self.grid_data_model.restore_state_snapshot(self.flip_snapshot, notify=True)
                    self.flip_snapshot = None
                
                self.grid_is_flipped = False
                print("Grid restored to friendly perspective")
                
        except Exception as e:
            print(f"Error flipping grid perspective: {e}")
            messagebox.showerror("Error", f"Failed to flip grid perspective: {e}")

    def create_round_selection_dropdowns(self):
        """Create dropdowns for tracking player selections across tournament rounds."""
        try:
            # Get team size from config to determine dropdown structure
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)  # Default to 5 if not set
            print(f"Creating dropdowns for {team_size}-player teams")
            
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
            tk.Label(header_frame, text="Team B", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, sticky='w')
            tk.Label(header_frame, text="Team A", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, sticky='w')
            
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
                    
                    # Enemy response dropdown 1
                    enemy_var1 = tk.StringVar()
                    enemy_dropdown1 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var1)
                    enemy_dropdown1.pack(fill=tk.X, pady=(0, 2))
                    
                    # Enemy response dropdown 2 - only create if not the last round
                    if round_num < team_size:
                        enemy_var2 = tk.StringVar()
                        enemy_dropdown2 = ttk.Combobox(enemy_response_frame, state='readonly', width=18, textvariable=enemy_var2)
                        enemy_dropdown2.pack(fill=tk.X, pady=(0, 0))
                        enemy_var2.trace_add('write', lambda *args, r=round_num, p=2, v=enemy_var2: self.on_response_selection_change_direct(r, p, v))
                        self.enemy_round_vars.extend([enemy_var1, enemy_var2])
                        self.enemy_round_dropdowns.extend([enemy_dropdown1, enemy_dropdown2])
                    else:
                        self.enemy_round_vars.append(enemy_var1)
                        self.enemy_round_dropdowns.append(enemy_dropdown1)
                    
                    # Bind events
                    friendly_var.trace_add('write', lambda *args, r=round_num, v=friendly_var: self.on_ante_selection_change_direct(r, v))
                    enemy_var1.trace_add('write', lambda *args, r=round_num, p=1, v=enemy_var1: self.on_response_selection_change_direct(r, p, v))
                    
                    # Store references
                    self.round_vars.append(friendly_var)
                    self.round_dropdowns.append(friendly_dropdown)
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
                    
                    # Friendly response dropdown 1
                    friendly_var1 = tk.StringVar()
                    friendly_dropdown1 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var1)
                    friendly_dropdown1.pack(fill=tk.X, pady=(0, 2))
                    
                    # Friendly response dropdown 2 - only create if not the last round
                    if round_num < team_size:
                        friendly_var2 = tk.StringVar()
                        friendly_dropdown2 = ttk.Combobox(friendly_response_frame, state='readonly', width=18, textvariable=friendly_var2)
                        friendly_dropdown2.pack(fill=tk.X, pady=(0, 0))
                        friendly_var2.trace_add('write', lambda *args, r=round_num, p=2, v=friendly_var2: self.on_response_selection_change_direct(r, p, v))
                        self.round_vars.extend([friendly_var1, friendly_var2])
                        self.round_dropdowns.extend([friendly_dropdown1, friendly_dropdown2])
                    else:
                        self.round_vars.append(friendly_var1)
                        self.round_dropdowns.append(friendly_dropdown1)
                    
                    # Bind events
                    enemy_var.trace_add('write', lambda *args, r=round_num, v=enemy_var: self.on_ante_selection_change_direct(r, v))
                    friendly_var1.trace_add('write', lambda *args, r=round_num, p=1, v=friendly_var1: self.on_response_selection_change_direct(r, p, v))
                    
                    # Store references
                    self.enemy_round_vars.append(enemy_var)
                    self.enemy_round_dropdowns.append(enemy_dropdown)
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
            # Skip if we're updating dropdowns programmatically
            if self._updating_dropdowns:
                return
            
            selected_player = var.get()
            old_ante = self.selected_players_per_round[round_num].get('ante')
            self.selected_players_per_round[round_num]['ante'] = selected_player if selected_player else None
            
            # If the ante changed (including being cleared), clear all subsequent rounds
            if old_ante != (selected_player if selected_player else None):
                self.clear_subsequent_rounds(round_num)
            
            round_data = self.selected_players_per_round.get(round_num, {})
            ante_team = round_data.get('ante_team', 'unknown')
            
            # Check if this is round 2, 4 (enemy antes, so check previous round's friendly responses)
            # or round 3, 5 (friendly antes, so check previous round's enemy responses)
            if round_num in [2, 3, 4, 5] and selected_player:
                previous_round = round_num - 1
                previous_round_data = self.selected_players_per_round.get(previous_round, {})
                
                # Get the two responses from the previous round
                response1 = previous_round_data.get('response1')
                response2 = previous_round_data.get('response2')
                response_team = previous_round_data.get('response_team')
                
                # The response that was NOT selected as ante is the one that "played"
                # So we need to mark it as implicitly selected
                if response1 and response2:
                    if selected_player == response1:
                        # Response2 was the one that played - mark it in tracking
                        previous_round_data['implicit_selection'] = response2
                    elif selected_player == response2:
                        # Response1 was the one that played - mark it in tracking
                        previous_round_data['implicit_selection'] = response1
            else:
                # Clear any implicit selection if ante is cleared
                if round_num >= 2:
                    previous_round = round_num - 1
                    previous_round_data = self.selected_players_per_round.get(previous_round, {})
                    if 'implicit_selection' in previous_round_data:
                        previous_round_data['implicit_selection'] = None
            
            # Recalculate ALL checkboxes from scratch based on current selections
            self.update_all_checkboxes_from_selections()
            self.update_all_column_checkboxes_from_selections()
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            # NEW: Trigger tree synchronization for Round 1 ante changes
            if round_num == 1 and ante_team == 'friendly':
                self.sync_tree_with_round_1_ante(selected_player)
            
            print(f"Round {round_num} ante selection ({ante_team}): {selected_player}")
            
        except Exception as e:
            print(f"Error handling ante selection change: {e}")

    def sync_tree_with_round_1_ante(self, selected_player):
        """
        Synchronize tree when Round 1 ante (friendly) is selected.
        - Generate tree if not generated or stale
        - Sort tree with worst matchups first (enemy's best picks)
        - Expand only Round 1 nodes containing selected player
        - Select the first Round 1 node (worst matchup)
        - If player is empty/cleared, collapse entire tree
        
        Smart reordering: Only reorders tree when player changes, preventing
        nodes from jumping when user interacts with already-sorted tree.
        """
        try:
            # Check if sync is triggered by Phase 2 (tree → dropdown)
            # If so, skip to prevent infinite loop
            if self._tree_sync_in_progress:
                return
            
            # If selection is cleared, collapse the tree
            if not selected_player:
                self.collapse_entire_tree()
                self._current_tree_top_player = None
                return
            
            # Check if this player is already at the top
            # If so, skip reordering (prevents jumping when clicking nodes)
            if self._current_tree_top_player == selected_player:
                return
            
            # Check if we need to generate the tree
            root_nodes = self.treeview.tree.get_children()
            if not root_nodes or len(root_nodes) == 0:
                # No tree exists, generate it
                self.on_generate_combinations()
            
            # Sort tree with worst matchups first (enemy's best picks)
            # Use cumulative sort in reverse (lowest values first = worst for friendly team)
            self.sort_tree_worst_first()
            
            # Collapse entire tree first
            self.collapse_entire_tree()
            
            # Expand only Round 1 nodes with selected player and select first one
            self.expand_and_select_round1_nodes(selected_player)
            
            # Update state: this player is now at the top
            self._current_tree_top_player = selected_player
            
        except Exception as e:
            print(f"Error synchronizing tree with Round 1 ante: {e}")
            import traceback
            traceback.print_exc()
    
    def collapse_entire_tree(self):
        """Collapse all tree nodes recursively."""
        try:
            def collapse_recursive(node_id):
                # Collapse this node
                self.treeview.tree.item(node_id, open=False)
                # Recursively collapse all children
                children = self.treeview.tree.get_children(node_id)
                for child in children:
                    collapse_recursive(child)
            
            # Start from root nodes
            root_nodes = self.treeview.tree.get_children()
            for root in root_nodes:
                collapse_recursive(root)
                
        except Exception as e:
            print(f"Error collapsing tree: {e}")
    
    def expand_and_select_round1_nodes(self, player_name):
        """
        Physically reorder Round 1 nodes to move selected player's matchups to the top.
        Select the first node (which will be worst matchup after sorting).
        Keep all children collapsed.
        """
        try:
            root_nodes = self.treeview.tree.get_children()
            if not root_nodes:
                return
            
            # The first root node should be "Pairings"
            pairings_root = root_nodes[0]
            
            # Expand the Pairings root
            self.treeview.tree.item(pairings_root, open=True)
            
            # Get all first-level children (these are Round 1 matchups)
            round1_nodes = self.treeview.tree.get_children(pairings_root)
            
            # Separate nodes into two groups: player matchups and others
            player_nodes = []
            other_nodes = []
            
            for node_id in round1_nodes:
                node_text = self.treeview.tree.item(node_id, 'text')
                
                # Check if this node contains the selected player
                if player_name in node_text:
                    player_nodes.append((node_id, node_text))
                else:
                    other_nodes.append((node_id, node_text))
            
            # Sort other nodes alphabetically by text
            other_nodes.sort(key=lambda x: x[1])
            
            # Detach all Round 1 nodes
            for node_id in round1_nodes:
                self.treeview.tree.detach(node_id)
            
            # Re-insert player matchups first (at the top, directly under parent)
            for node_id, _ in player_nodes:
                self.treeview.tree.move(node_id, pairings_root, 'end')
                # Keep children collapsed
                self.treeview.tree.item(node_id, open=False)
            
            # Then re-insert other nodes in alphabetical order
            for node_id, _ in other_nodes:
                self.treeview.tree.move(node_id, pairings_root, 'end')
                # Keep children collapsed
                self.treeview.tree.item(node_id, open=False)
            
            # Select the first player node (worst matchup for selected player)
            if player_nodes:
                first_matching_node = player_nodes[0][0]
                # Clear any existing selection
                self.treeview.tree.selection_remove(self.treeview.tree.selection())
                # Select the first node
                self.treeview.tree.selection_set(first_matching_node)
                # Ensure it's visible
                self.treeview.tree.see(first_matching_node)
                
        except Exception as e:
            print(f"Error expanding Round 1 nodes: {e}")
            import traceback
            traceback.print_exc()
    
    def sort_tree_worst_first(self):
        """
        Sort tree with worst matchups first (lowest ratings = enemy's best picks).
        This is the inverse of normal cumulative sorting.
        """
        try:
            # Save original order if not already saved
            if not hasattr(self.tree_generator, 'original_order_saved') or not self.tree_generator.original_order_saved:
                self.tree_generator.save_original_order()
                self.tree_generator.original_order_saved = True
            
            # Calculate cumulative values
            self.tree_generator.calculate_all_path_values("")
            
            # Sort recursively, but with LOWEST values first (worst for friendly team)
            root_nodes = self.treeview.tree.get_children()
            for root in root_nodes:
                self.sort_children_by_cumulative_reverse(root)
            
            # Update UI state
            self.current_sort_mode = "worst_first"
            self.active_sort_mode = "worst_first"
            self.treeview.tree.heading("Sort Value", text="Worst First")
            self.update_sort_value_column()
            self.is_sorted = True
            
        except Exception as e:
            print(f"Error sorting tree worst first: {e}")
            import traceback
            traceback.print_exc()
    
    def sort_children_by_cumulative_reverse(self, node):
        """Recursively sort children by cumulative values in REVERSE (worst first)."""
        try:
            children = self.treeview.tree.get_children(node)
            if not children:
                return
            
            # Get cumulative values for all children
            children_with_scores = []
            for child in children:
                cumulative_value = self.tree_generator.get_cumulative_value_from_tags(child)
                children_with_scores.append((child, cumulative_value))
            
            # Sort by cumulative value (LOWEST first - worst outcomes at top)
            children_with_scores.sort(key=lambda x: x[1], reverse=False)
            
            # Reorder children in the tree
            for child, _ in children_with_scores:
                self.treeview.tree.detach(child)
            for child, _ in children_with_scores:
                self.treeview.tree.move(child, node, 'end')
            
            # Recursively sort grandchildren
            for child, _ in children_with_scores:
                self.sort_children_by_cumulative_reverse(child)
                
        except Exception as e:
            print(f"Error sorting children reverse: {e}")

    def on_response_selection_change_direct(self, round_num, position, var):
        """Handle response selection changes with direct variable access."""
        try:
            # Skip if we're updating dropdowns programmatically
            if self._updating_dropdowns:
                return
            
            selected_player = var.get()
            response_key = f'response{position}'
            old_response = self.selected_players_per_round[round_num].get(response_key)
            self.selected_players_per_round[round_num][response_key] = selected_player if selected_player else None
            
            # If this response was cleared, also clear the other response in the same round
            # AND clear any implicit selection that may have been set by a future round
            if not selected_player and old_response:
                # Clear the other response in this round
                other_position = 2 if position == 1 else 1
                other_key = f'response{other_position}'
                self.selected_players_per_round[round_num][other_key] = None
                
                # Clear implicit selection from this round (set by future rounds)
                if 'implicit_selection' in self.selected_players_per_round[round_num]:
                    self.selected_players_per_round[round_num]['implicit_selection'] = None
                    print(f"DEBUG: Cleared implicit selection from Round {round_num}")
            
            # If the response changed (including being cleared), clear all subsequent rounds
            if old_response != (selected_player if selected_player else None):
                self.clear_subsequent_rounds(round_num)
                # Refresh UI to show all cleared responses
                self.refresh_dropdown_ui_from_tracking()
            
            # Update all dropdown options to reflect new availability
            self.update_round_dropdown_options()
            
            # Recalculate checkboxes AFTER all clearing and UI updates are done
            self.update_all_checkboxes_from_selections()
            self.update_all_column_checkboxes_from_selections()
            
            # Get team size from config to check if this is the last round
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            
            # In the last round (round N for N-player teams), treat the first response like an ante
            # since it's the only remaining player and should check the box
            if round_num == team_size and position == 1:
                round_data = self.selected_players_per_round.get(round_num, {})
                response_team = round_data.get('response_team')
            
            round_data = self.selected_players_per_round.get(round_num, {})
            response_team = round_data.get('response_team', 'unknown')
            print(f"Round {round_num} response {position} ({response_team}): {selected_player}")
            
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
    
    def clear_subsequent_rounds(self, from_round):
        """Clear all dropdown selections in rounds after the specified round."""
        try:
            # Clear all rounds after from_round
            for round_num in range(from_round + 1, 6):
                if round_num in self.selected_players_per_round:
                    round_data = self.selected_players_per_round[round_num]
                    
                    # Clear the tracking data
                    round_data['ante'] = None
                    round_data['response1'] = None
                    round_data['response2'] = None
                    if 'implicit_selection' in round_data:
                        round_data['implicit_selection'] = None
            
            # After clearing tracking data, refresh ALL dropdowns to reflect the cleared state
            # This will properly clear only the dropdowns for rounds > from_round
            # while preserving the current round's selection
            self.refresh_dropdown_ui_from_tracking()
            
            print(f"Cleared all rounds after round {from_round}")
            
        except Exception as e:
            print(f"Error clearing subsequent rounds: {e}")
    
    def refresh_dropdown_ui_from_tracking(self):
        """Refresh all dropdown UI elements to match the tracking dictionary."""
        try:
            # Set flag to prevent recursive calls
            self._updating_dropdowns = True
            
            # Update friendly dropdowns
            friendly_dropdown_idx = 0
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                response_team = round_data.get('response_team')
                
                if ante_team == 'friendly':
                    # Set friendly ante dropdown
                    if friendly_dropdown_idx < len(self.round_vars):
                        ante_value = round_data.get('ante', '')
                        self.round_vars[friendly_dropdown_idx].set(ante_value if ante_value else "")
                        friendly_dropdown_idx += 1
                
                if response_team == 'friendly':
                    # Set friendly response dropdowns
                    if friendly_dropdown_idx < len(self.round_vars):
                        response1_value = round_data.get('response1', '')
                        self.round_vars[friendly_dropdown_idx].set(response1_value if response1_value else "")
                        friendly_dropdown_idx += 1
                    
                    if friendly_dropdown_idx < len(self.round_vars):
                        response2_value = round_data.get('response2', '')
                        self.round_vars[friendly_dropdown_idx].set(response2_value if response2_value else "")
                        friendly_dropdown_idx += 1
            
            # Update enemy dropdowns
            enemy_dropdown_idx = 0
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                response_team = round_data.get('response_team')
                
                if ante_team == 'enemy':
                    # Set enemy ante dropdown
                    if enemy_dropdown_idx < len(self.enemy_round_vars):
                        ante_value = round_data.get('ante', '')
                        self.enemy_round_vars[enemy_dropdown_idx].set(ante_value if ante_value else "")
                        enemy_dropdown_idx += 1
                
                if response_team == 'enemy':
                    # Set enemy response dropdowns
                    if enemy_dropdown_idx < len(self.enemy_round_vars):
                        response1_value = round_data.get('response1', '')
                        self.enemy_round_vars[enemy_dropdown_idx].set(response1_value if response1_value else "")
                        enemy_dropdown_idx += 1
                    
                    # Check if second response dropdown exists (not in last round)
                    ui_prefs = self.db_preferences.get_ui_preferences()
                    team_size = ui_prefs.get('team_size', 5)
                    if round_num < team_size and enemy_dropdown_idx < len(self.enemy_round_vars):
                        response2_value = round_data.get('response2', '')
                        self.enemy_round_vars[enemy_dropdown_idx].set(response2_value if response2_value else "")
                        enemy_dropdown_idx += 1
            
            # Clear flag after update
            self._updating_dropdowns = False
            
        except Exception as e:
            self._updating_dropdowns = False
            print(f"Error refreshing dropdown UI: {e}")
    
    def clear_round_dropdowns(self):
        """Clear all values from round selection dropdowns."""
        try:
            # Set flag to prevent callbacks during bulk clear
            self._updating_dropdowns = True
            
            # Clear all friendly dropdown values
            for var in self.round_vars:
                var.set("")
            
            # Clear all enemy dropdown values
            for var in self.enemy_round_vars:
                var.set("")
            
            # Clear tracking dictionary
            for round_num in self.selected_players_per_round:
                self.selected_players_per_round[round_num]['ante'] = None
                self.selected_players_per_round[round_num]['response1'] = None
                self.selected_players_per_round[round_num]['response2'] = None
                if 'implicit_selection' in self.selected_players_per_round[round_num]:
                    self.selected_players_per_round[round_num]['implicit_selection'] = None
            
            # Uncheck all row checkboxes
            for checkbox_var in self.row_checkboxes:
                checkbox_var.set(0)
            
            # Uncheck all column checkboxes
            for checkbox_var in self.column_checkboxes:
                checkbox_var.set(0)
            
            # Clear flag
            self._updating_dropdowns = False
            
            print("All round dropdowns cleared")
            
        except Exception as e:
            self._updating_dropdowns = False
            print(f"Error clearing round dropdowns: {e}")
    
    def fill_round_dropdowns(self):
        """Fill all dropdowns with the first available option (for testing purposes)."""
        try:
            print("Starting to fill all round dropdowns with first available options...")
            
            # First clear everything to start fresh
            self.clear_round_dropdowns()
            
            # Get team size from config
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            
            # Get current team player lists
            friendly_players = self.get_friendly_player_names()
            enemy_players = self.get_enemy_player_names()
            
            if not friendly_players or not enemy_players:
                print("Cannot fill dropdowns: teams not selected")
                messagebox.showwarning("Teams Required", "Please select both teams before using FILL.")
                return
            
            # Process each round sequentially
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                friendly_antes = (round_num % 2 == 1)
                
                # Update dropdown options first to get current available players
                self.update_round_dropdown_options()
                
                if friendly_antes:
                    # Friendly antes, Enemy responds
                    # Get friendly ante dropdown and select first available
                    dropdown_idx = self._get_friendly_ante_dropdown_index(round_num)
                    if dropdown_idx is not None and dropdown_idx < len(self.round_dropdowns):
                        dropdown = self.round_dropdowns[dropdown_idx]
                        values = dropdown['values']
                        if len(values) > 1:  # First item is empty string
                            first_option = values[1]
                            self.round_vars[dropdown_idx].set(first_option)
                            print(f"Round {round_num}: Set friendly ante to {first_option}")
                            # Small delay to allow callbacks to process
                            self.root.update_idletasks()
                    
                    # Update options again after ante selection
                    self.update_round_dropdown_options()
                    
                    # Get enemy response dropdowns and select first available
                    enemy_dropdown_indices = self._get_enemy_response_dropdown_indices(round_num)
                    for idx, enemy_idx in enumerate(enemy_dropdown_indices):
                        if enemy_idx < len(self.enemy_round_dropdowns):
                            dropdown = self.enemy_round_dropdowns[enemy_idx]
                            values = dropdown['values']
                            if len(values) > 1:
                                first_option = values[1]
                                self.enemy_round_vars[enemy_idx].set(first_option)
                                print(f"Round {round_num}: Set enemy response {idx+1} to {first_option}")
                                self.root.update_idletasks()
                                # Update options after first response before second
                                if idx == 0:
                                    self.update_round_dropdown_options()
                else:
                    # Enemy antes, Friendly responds
                    # Get enemy ante dropdown and select first available
                    dropdown_idx = self._get_enemy_ante_dropdown_index(round_num)
                    if dropdown_idx is not None and dropdown_idx < len(self.enemy_round_dropdowns):
                        dropdown = self.enemy_round_dropdowns[dropdown_idx]
                        values = dropdown['values']
                        if len(values) > 1:
                            first_option = values[1]
                            self.enemy_round_vars[dropdown_idx].set(first_option)
                            print(f"Round {round_num}: Set enemy ante to {first_option}")
                            self.root.update_idletasks()
                    
                    # Update options again after ante selection
                    self.update_round_dropdown_options()
                    
                    # Get friendly response dropdowns and select first available
                    friendly_dropdown_indices = self._get_friendly_response_dropdown_indices(round_num)
                    for idx, friendly_idx in enumerate(friendly_dropdown_indices):
                        if friendly_idx < len(self.round_dropdowns):
                            dropdown = self.round_dropdowns[friendly_idx]
                            values = dropdown['values']
                            if len(values) > 1:
                                first_option = values[1]
                                self.round_vars[friendly_idx].set(first_option)
                                print(f"Round {round_num}: Set friendly response {idx+1} to {first_option}")
                                self.root.update_idletasks()
                                # Update options after first response before second
                                if idx == 0:
                                    self.update_round_dropdown_options()
            
            print("Finished filling all round dropdowns")
            
        except Exception as e:
            print(f"Error filling round dropdowns: {e}")
            messagebox.showerror("Fill Error", f"Failed to fill dropdowns: {e}")
    
    def _get_friendly_ante_dropdown_index(self, round_num):
        """Get the dropdown index for friendly ante in the specified round."""
        # Friendly antes in rounds 1, 3, 5
        # Dropdown order: [R1-ante, R2-resp1, R2-resp2, R3-ante, R4-resp1, R4-resp2, R5-ante]
        if round_num == 1:
            return 0
        elif round_num == 3:
            return 3
        elif round_num == 5:
            return 6
        return None
    
    def _get_enemy_ante_dropdown_index(self, round_num):
        """Get the dropdown index for enemy ante in the specified round."""
        # Enemy antes in rounds 2, 4
        # Dropdown order: [R1-resp1, R1-resp2, R2-ante, R3-resp1, R3-resp2, R4-ante, R5-resp1]
        if round_num == 2:
            return 2
        elif round_num == 4:
            return 5
        return None
    
    def _get_enemy_response_dropdown_indices(self, round_num):
        """Get the dropdown indices for enemy responses in the specified round."""
        # Enemy responds in rounds 1, 3, 5
        # Dropdown order: [R1-resp1, R1-resp2, R2-ante, R3-resp1, R3-resp2, R4-ante, R5-resp1]
        if round_num == 1:
            return [0, 1]
        elif round_num == 3:
            return [3, 4]
        elif round_num == 5:
            return [6]  # Only one response in last round
        return []
    
    def _get_friendly_response_dropdown_indices(self, round_num):
        """Get the dropdown indices for friendly responses in the specified round."""
        # Friendly responds in rounds 2, 4
        # Dropdown order: [R1-ante, R2-resp1, R2-resp2, R3-ante, R4-resp1, R4-resp2, R5-ante]
        if round_num == 2:
            return [1, 2]
        elif round_num == 4:
            return [4, 5]
        return []
    
    def sync_checkbox_with_player_selection(self, player_name):
        """Check or uncheck the row checkbox corresponding to the selected player."""
        try:
            if not player_name:
                # If player name is empty, we need to check if this player is used anywhere else
                # If not, uncheck their box
                self.update_all_checkboxes_from_selections()
                return
            
            # Get friendly player names from grid
            friendly_players = self.get_friendly_player_names()
            
            # Find which row this player is in (1-5)
            for row_idx, friendly_player in enumerate(friendly_players):
                if friendly_player == player_name:
                    # Check the checkbox for this row (row_idx is 0-based, checkbox is 1-based)
                    if row_idx < len(self.row_checkboxes):
                        self.row_checkboxes[row_idx].set(1)
                        print(f"Checked box for {player_name} at row {row_idx + 1}")
                    break
            
        except Exception as e:
            print(f"Error syncing checkbox with player selection: {e}")
    
    def sync_column_checkbox_with_player_selection(self, player_name):
        """Check or uncheck the column checkbox corresponding to the selected enemy player."""
        try:
            if not player_name:
                # If player name is empty, recalculate all column checkboxes
                self.update_all_column_checkboxes_from_selections()
                return
            
            # Get enemy player names from grid
            enemy_players = self.get_opponent_player_names()
            
            # Find which column this player is in (1-5)
            for col_idx, enemy_player in enumerate(enemy_players):
                if enemy_player == player_name:
                    # Check the checkbox for this column (col_idx is 0-based, checkbox is 1-based)
                    if col_idx < len(self.column_checkboxes):
                        self.column_checkboxes[col_idx].set(1)
                        print(f"Checked column box for {player_name} at column {col_idx + 1}")
                    break
            
        except Exception as e:
            print(f"Error syncing column checkbox with player selection: {e}")
    
    def update_all_column_checkboxes_from_selections(self):
        """Update all column checkboxes based on current dropdown selections."""
        try:
            # Get team size to identify the last round
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            
            # Get all selected enemy players from ante selections and implicit selections
            selected_players = set()
            
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                
                # Only add ante if it's from enemy team
                if ante_team == 'enemy' and round_data.get('ante'):
                    selected_players.add(round_data['ante'])
                
                # Add implicit selections if they're enemy players
                if round_data.get('implicit_selection'):
                    # Check if this implicit selection is an enemy player
                    enemy_players = self.get_opponent_player_names()
                    if round_data['implicit_selection'] in enemy_players:
                        selected_players.add(round_data['implicit_selection'])
                
                # In the last round, if enemy is responding, include the first response
                if round_num == team_size:
                    response_team = round_data.get('response_team')
                    if response_team == 'enemy' and round_data.get('response1'):
                        selected_players.add(round_data['response1'])
            
            # Get enemy player names
            enemy_players = self.get_opponent_player_names()
            
            # Update each checkbox based on whether that player is selected
            for col_idx, enemy_player in enumerate(enemy_players):
                if col_idx < len(self.column_checkboxes):
                    if enemy_player in selected_players:
                        self.column_checkboxes[col_idx].set(1)
                    else:
                        self.column_checkboxes[col_idx].set(0)
            
        except Exception as e:
            print(f"Error updating all column checkboxes from selections: {e}")
    
    def update_all_checkboxes_from_selections(self):
        """Update all row checkboxes based on current dropdown selections."""
        try:
            # Get team size to identify the last round
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)
            
            # Get all selected friendly players from ante selections and implicit selections
            selected_players = set()
            
            print("DEBUG: Calculating row checkboxes...")
            for round_num in range(1, 6):
                round_data = self.selected_players_per_round.get(round_num, {})
                ante_team = round_data.get('ante_team')
                
                # Only add ante if it's from friendly team
                if ante_team == 'friendly' and round_data.get('ante'):
                    selected_players.add(round_data['ante'])
                    print(f"  Round {round_num}: Friendly ante = {round_data['ante']}")
                
                # Add implicit selections if they're friendly players
                if round_data.get('implicit_selection'):
                    # Check if this implicit selection is a friendly player
                    friendly_players = self.get_friendly_player_names()
                    if round_data['implicit_selection'] in friendly_players:
                        selected_players.add(round_data['implicit_selection'])
                        print(f"  Round {round_num}: Implicit selection = {round_data['implicit_selection']}")
                
                # In the last round, if friendly is responding, include the first response
                if round_num == team_size:
                    response_team = round_data.get('response_team')
                    if response_team == 'friendly' and round_data.get('response1'):
                        selected_players.add(round_data['response1'])
                        print(f"  Round {round_num}: Last round response = {round_data['response1']}")
            
            print(f"DEBUG: Total selected friendly players: {selected_players}")
            
            # Get friendly player names
            friendly_players = self.get_friendly_player_names()
            
            # Update each checkbox based on whether that player is selected
            for row_idx, friendly_player in enumerate(friendly_players):
                if row_idx < len(self.row_checkboxes):
                    should_check = friendly_player in selected_players
                    current_state = self.row_checkboxes[row_idx].get()
                    if should_check != current_state:
                        print(f"DEBUG: Setting {friendly_player} checkbox to {1 if should_check else 0} (was {current_state})")
                        self.row_checkboxes[row_idx].set(1 if should_check else 0)
            
        except Exception as e:
            print(f"Error updating all checkboxes from selections: {e}")

    def _update_ante_response_dropdowns(self, friendly_players, enemy_players):
        """Update dropdowns with proper ante/response logic and matchup correlation."""
        try:
            # Get team size from config once at the start
            ui_prefs = self.db_preferences.get_ui_preferences()
            team_size = ui_prefs.get('team_size', 5)  # Default to 5 if not set
            print(f"DEBUG: team_size from config = {team_size}")
            
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
                    # First response dropdown: exclude previous rounds + current round ante
                    available_enemy = self._get_available_enemy_players(round_num, enemy_players)
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + available_enemy
                        enemy_dropdown_index += 1
                    
                    # Second response dropdown: also exclude current round response1
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        available_enemy_2 = self._get_available_enemy_players(round_num, enemy_players, exclude_current_response1=True)
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + available_enemy_2
                        enemy_dropdown_index += 1
                        
                else:
                    # Round 2, 4: Enemy antes, Friendly responds
                    # Enemy ante dropdown - special logic for matchup correlation
                    if enemy_dropdown_index < len(self.enemy_round_dropdowns):
                        ante_options = self._get_enemy_ante_options(round_num)
                        self.enemy_round_dropdowns[enemy_dropdown_index]['values'] = [""] + ante_options
                        enemy_dropdown_index += 1
                    
                    # Update friendly response dropdowns
                    # First response dropdown: exclude previous rounds + current round ante
                    available_friendly = self._get_available_friendly_players(round_num, friendly_players)
                    if dropdown_index < len(self.round_dropdowns):
                        self.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly
                        dropdown_index += 1
                    
                    # Second response dropdown: also exclude current round response1
                    if dropdown_index < len(self.round_dropdowns):
                        available_friendly_2 = self._get_available_friendly_players(round_num, friendly_players, exclude_current_response1=True)
                        self.round_dropdowns[dropdown_index]['values'] = [""] + available_friendly_2
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

    def _get_available_friendly_players(self, round_num, all_friendly_players, exclude_current_response1=False):
        """Get available friendly players for the current round.
        
        Args:
            round_num: The round number to get available players for
            all_friendly_players: List of all friendly player names
            exclude_current_response1: If True, also exclude response1 from the current round
                                      (used for the second response dropdown)
        """
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
        
        # Also check current round for ante (if friendly antes this round)
        current_round_data = self.selected_players_per_round.get(round_num, {})
        if current_round_data.get('ante_team') == 'friendly' and current_round_data.get('ante'):
            used_players.add(current_round_data['ante'])
        
        # If this is for the second response dropdown, also exclude response1 from current round
        if exclude_current_response1 and current_round_data.get('response_team') == 'friendly':
            if current_round_data.get('response1'):
                used_players.add(current_round_data['response1'])
        
        return [player for player in all_friendly_players if player not in used_players]

    def _get_available_enemy_players(self, round_num, all_enemy_players, exclude_current_response1=False):
        """Get available enemy players for the current round.
        
        Args:
            round_num: The round number to get available players for
            all_enemy_players: List of all enemy player names
            exclude_current_response1: If True, also exclude response1 from the current round
                                      (used for the second response dropdown)
        """
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
        
        # Also check current round for ante (if enemy antes this round)
        current_round_data = self.selected_players_per_round.get(round_num, {})
        if current_round_data.get('ante_team') == 'enemy' and current_round_data.get('ante'):
            used_players.add(current_round_data['ante'])
        
        # If this is for the second response dropdown, also exclude response1 from current round
        if exclude_current_response1 and current_round_data.get('response_team') == 'enemy':
            if current_round_data.get('response1'):
                used_players.add(current_round_data['response1'])
        
        return [player for player in all_enemy_players if player not in used_players]

    def create_matchup_output_panel(self):
        """Create a panel to display the final 5 matchups in a simple format."""
        try:
            # Create output panel frame at the bottom of the tree tab right frame
            self.output_panel_frame = tk.Frame(self.tree_tab_right_frame, relief=tk.RIDGE, borderwidth=2, bg="lightyellow")
            self.output_panel_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
            
            # Panel title
            title_label = tk.Label(self.output_panel_frame, text="Final Matchups Output", 
                                 font=("Arial", 12, "bold"), bg="lightyellow")
            title_label.pack(pady=(5, 0))
            
            # Instructions
            instructions = tk.Label(self.output_panel_frame, 
                                  text="Select a pairing from the tree above, then click 'Extract Matchups' to display the 5 final matchups:",
                                  font=("Arial", 9), bg="lightyellow", fg="darkblue")
            instructions.pack(pady=(0, 5))
            
            # Button and checkbox frame
            button_frame = tk.Frame(self.output_panel_frame, bg="lightyellow")
            button_frame.pack(pady=5)
            
            # Extract button
            extract_button = tk.Button(button_frame, text="Extract Matchups", 
                                     command=self.extract_final_matchups, font=("Arial", 10, "bold"),
                                     bg="lightgreen", relief=tk.RAISED)
            extract_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Verbose mode checkbox
            self.verbose_matchup_var = tk.BooleanVar()
            # Initialize from config: verbose=True if format is "verbose", else False
            current_format = self.db_preferences.get_matchup_output_format()
            self.verbose_matchup_var.set(current_format == "verbose")
            
            verbose_checkbox = tk.Checkbutton(button_frame, text="Verbose Output",
                                            variable=self.verbose_matchup_var,
                                            command=self.on_verbose_mode_changed,
                                            font=("Arial", 9), bg="lightyellow")
            verbose_checkbox.pack(side=tk.LEFT)
            
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

    def on_verbose_mode_changed(self):
        """Handle verbose mode checkbox changes and save to config."""
        try:
            is_verbose = self.verbose_matchup_var.get()
            format_type = "verbose" if is_verbose else "standard"
            
            # Save to config
            success = self.db_preferences.set_matchup_output_format(format_type)
            
            if success:
                print(f"Matchup output format updated to: {format_type}")
            else:
                print(f"Warning: Failed to save matchup output format preference")
                
        except Exception as e:
            print(f"Error updating verbose mode preference: {e}")
    
    def format_matchups_verbose(self, matchups, item_text):
        """Format matchups in verbose mode with complete decision path details."""
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
        
        return output_text
    
    def format_matchups_concise(self, matchups, item_text):
        """Format matchups in concise mode with brief summary."""
        output_text = ""
        
        for i, matchup in enumerate(matchups, 1):
            decision = matchup.get('decision', 'Unknown decision')
            rating = matchup.get('rating', 'N/A')
            output_text += f"{i}. {decision} ({rating})\n"
        
        output_text += f"\nGenerated: {self.get_current_timestamp()}"
        
        return output_text
    
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
            
            # Format matchups based on config preference
            output_format = self.db_preferences.get_matchup_output_format()
            
            if output_format == "verbose":
                output_text = self.format_matchups_verbose(matchups, item_text)
            else:  # Default to standard
                output_text = self.format_matchups_concise(matchups, item_text)
            
            # Always log the verbose version to file, regardless of UI display format
            verbose_output = self.format_matchups_verbose(matchups, item_text)
            self.logger.info(f"Matchup Extraction:\n{verbose_output}")
            
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
    
    # ========================================================================
    # V2: GridDataModel Integration Methods
    # ========================================================================
    
    def _on_grid_data_changed(self, event_type: str, *args):
        """
        Observer callback for GridDataModel changes.
        
        Updates UI widgets in response to data model changes.
        """
        if event_type == 'rating_changed':
            row, col, value = args
            self._update_entry_from_model(row, col)
            self.update_color_on_change(None, None, None, row, col)
        
        elif event_type == 'display_changed':
            row, col, value = args
            self._update_display_entry_from_model(row, col)
        
        elif event_type == 'comment_changed':
            row, col, comment_text = args
            # Update comment indicator
            self._update_comment_indicator(row, col, comment_text is not None)
        
        elif event_type == 'cell_disabled':
            row, col, is_disabled = args
            widget = self.grid_widgets[row][col]
            if widget:
                if is_disabled:
                    widget.config(state='disabled', bg='grey')
                else:
                    widget.config(state='normal')
                    self.update_color_on_change(None, None, None, row, col)
        
        elif event_type == 'batch_update':
            # Efficiently handle batch updates (e.g., from load_grid_data_from_db)
            notifications = args[0]
            for evt_type, evt_args in notifications:
                self._on_grid_data_changed(evt_type, *evt_args)
        
        elif event_type == 'grid_cleared':
            # Refresh entire grid
            for r in range(6):
                for c in range(6):
                    self._update_entry_from_model(r, c)
                    self._update_display_entry_from_model(r, c)
        
        elif event_type == 'grid_loaded':
            # Refresh entire grid after load
            for r in range(6):
                for c in range(6):
                    self._update_entry_from_model(r, c)
                    self._update_display_entry_from_model(r, c)
                    if self.grid_data_model.has_comment(r, c):
                        self._update_comment_indicator(r, c, True)
    
    def _sync_entry_to_model(self, row: int, col: int, widget: tk.Entry):
        """
        Sync Entry widget value to GridDataModel.
        
        Called on FocusOut and Return key to update model with manual entry.
        Phase 1: Converts rating cells (row > 0, col > 0) to integers.
        """
        current_value = widget.get().strip()
        model_value = self.grid_data_model.get_rating(row, col)
        
        # For rating cells, convert to integer or None
        if row > 0 and col > 0:
            # Rating cell - convert to int if valid, None if empty
            if current_value and current_value.isdigit():
                new_value = int(current_value)
            elif not current_value:
                new_value = None  # Empty string → None
            else:
                new_value = current_value  # Keep invalid strings for validation error
        else:
            # Header cell - keep as string (player name)
            new_value = current_value if current_value else None
        
        if new_value != model_value:
            self.grid_data_model.set_rating(row, col, new_value)
            # Trigger color update and scenario calculations
            self.update_color_on_change(None, None, None, row, col)
            self.on_scenario_calculations()
    
    def _update_entry_from_model(self, row: int, col: int):
        """
        Update Entry widget from GridDataModel value.
        Phase 1: Convert int/None → string for Entry widget display.
        """
        widget = self.grid_widgets[row][col]
        if widget:
            current_text = widget.get()
            model_value = self.grid_data_model.get_rating(row, col)
            
            # Convert model value to string for Entry widget
            if model_value is None:
                model_str = ''
            elif isinstance(model_value, int):
                model_str = str(model_value)
            else:
                model_str = str(model_value)  # Handle string (player names)
            
            if current_text != model_str:
                widget.delete(0, tk.END)
                widget.insert(0, model_str)
    
    def _update_display_entry_from_model(self, row: int, col: int):
        """Update display Entry widget from GridDataModel value"""
        widget = self.grid_display_widgets[row][col]
        if widget:
            widget.config(state='normal')
            widget.delete(0, tk.END)
            widget.insert(0, self.grid_data_model.get_display(row, col))
            widget.config(state='readonly')
    
    def _update_comment_indicator(self, row: int, col: int, has_comment: bool):
        """Update visual comment indicator for cell"""
        widget = self.grid_widgets[row][col]
        if widget and row > 0 and col > 0:  # Only matchup cells
            if has_comment:
                widget.config(bg='#ffffcc')  # Light yellow for comments
            else:
                # Restore color based on rating
                self.update_color_on_change(None, None, None, row, col)
    
    def _update_comment_overlay_geometry(self):
        """Calculate and update CommentOverlay geometry after grid layout"""
        if not self.comment_overlay:
            return
        
        # Calculate cell positions and grid bounding box
        cell_positions = {}
        min_x = min_y = float('inf')
        max_x = max_y = 0
        
        for r in range(1, 6):  # Only matchup cells (skip headers)
            for c in range(1, 6):
                widget = self.grid_widgets[r][c]
                if widget:
                    x = widget.winfo_x()
                    y = widget.winfo_y()
                    width = widget.winfo_width()
                    height = widget.winfo_height()
                    
                    cell_positions[(r, c)] = (x, y, width, height)
                    
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x + width)
                    max_y = max(max_y, y + height)
        
        # Grid bounding box
        grid_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)
        
        # Update overlay
        self.comment_overlay.update_grid_geometry(cell_positions, grid_bbox)
        self.comment_overlay.show()
    
    def _open_comment_editor_for_cell(self, row: int, col: int):
        """
        Open comment editor for specific cell (callback for CommentOverlay).
        
        Simplified version that works with GridDataModel.
        """
        try:
            # Get current team and scenario information
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()
            
            # Get player names from grid
            friendly_player = self.grid_data_model.get_rating(row, 0)
            opponent_player = self.grid_data_model.get_rating(0, col)
            
            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                messagebox.showwarning("Missing Information", 
                                     "Please select teams, scenario, and ensure player names are filled in.")
                return
            
            # Get existing comment from database
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

if __name__ == '__main__':
    ui_manager = UiManager(
        color_map=DEFAULT_COLOR_MAP, 
        scenario_map=SCENARIO_MAP, 
        directory=os.getcwd(),
        scenario_ranges=SCENARIO_RANGES,
        scenario_to_csv_map=SCENARIO_TO_CSV_MAP
    )
    ui_manager.create_ui()
