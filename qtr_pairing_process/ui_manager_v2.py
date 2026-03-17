""" ┬⌐ Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
from multiprocessing import Value
import os
import sys
import csv
import json
import sqlite3
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
import tkinter.font as tkfont

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
from qtr_pairing_process.perf_timer import PerfTimer


class UiManager:
    def __init__(
        self,
        color_map: Dict[str, str],
        scenario_map: Dict[int, str],
        directory: str,
        scenario_ranges: Dict[int, tuple],
        scenario_to_csv_map: Dict[int, str],
        print_output: bool = False,
        perf_enabled: Optional[bool] = None
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
        self.strategic_preferences = self.db_preferences.get_strategic_preferences()
        self.tie_break_order = self.strategic_preferences.get('strategic3', {}).get(
            'tie_break_order',
            'confidence_then_cumulative'
        )
        strategic3_prefs = self.strategic_preferences.get('strategic3', {})
        self.auto_sort_after_generate = bool(strategic3_prefs.get('auto_sort_after_generate', True))
        self.auto_sort_toggle_enabled = bool(strategic3_prefs.get('auto_sort_toggle_enabled', True))
        config_rating_system = ui_prefs.get('rating_system')

        self.tree_autogen_enabled = self.db_preferences.get_tree_autogen_enabled()
        self.lazy_sort_on_expand = bool(ui_prefs.get("lazy_sort_on_expand", False))
        self.lazy_sort_mode = str(
            ui_prefs.get(
                "lazy_sort_mode",
                "fast_expand_first" if self.lazy_sort_on_expand else "strict",
            )
        )
        if self.lazy_sort_mode == "fast_expand_first":
            self.lazy_sort_on_expand = True
        
        self.current_rating_system = config_rating_system or self.settings_manager.get_rating_system()
        self.rating_config = RATING_SYSTEMS[self.current_rating_system]
        self.color_map = self.rating_config['color_map']
        self.rating_range = self.rating_config['range']

        pref_perf = ui_prefs.get("perf_logging_enabled")
        if perf_enabled is None:
            perf_is_enabled = pref_perf if pref_perf is not None else self.is_debugging
        else:
            perf_is_enabled = perf_enabled

        self.perf_logging_enabled = perf_is_enabled
        self.perf = PerfTimer(
            enabled=perf_is_enabled,
            log_dir=Path(__file__).parent.parent / "perf_logs",
            buffered=True,
            buffer_size=25,
            max_daily_files=5,
        )

        # Initialize other UI components
        self.comment_tooltip: Optional[tk.Toplevel] = None
        self.comment_indicators: Dict[tuple, tk.Widget] = {}  # Store comment indicators
        self.comment_indicator_callbacks: Dict[tuple, str] = {}  # Store after_idle callback IDs
        self.row_checkboxes: List[tk.IntVar] = []
        self.column_checkboxes: List[tk.IntVar] = []
        self._current_hover_cell = None
        self._team_dropdowns_initialized = False
        self._auto_populated_teams = False
        self._team_change_in_progress = False
        self._scenario_calc_job = None
        self._scenario_calc_delay_ms = 120
        self._team_cache: Dict[str, Dict[str, Any]] = {}
        self._comment_cache: Dict[tuple, Dict[tuple, str]] = {}
        self._scenario_change_auto = False
        self._event_loop_lag_threshold_ms = 16.0
        self._resize_job = None
        self._resize_active = False
        self._resize_start_time = 0.0
        self._resize_last_time = 0.0
        self._resize_event_count = 0
        self._resize_start_size = (0, 0)
        self._resize_end_size = (0, 0)
        self._last_root_size = (0, 0)
        self._tree_autogen_job = None
        self._grid_color_dirty = False
        self._background_load_enabled = True
        self._grid_load_generation = 0
        self._grid_load_in_flight = False
        self._tree_cache_enabled = True
        self._tree_cache = {}
        self._tree_cache_key = None
        self._tree_generation_id = 0
        self._calc_grid_cache = {}
        self._primary_metrics_dirty = True
        self._last_primary_metrics_signature = None
        self._metric_signatures = {}
        self._sorted_children_cache = {}
        self._available_explainability_metrics = set()
        
        
        # Initialize logger
        self.logger = get_logger(__name__)
        self.logger.info("UiManager initializing...")
        
        with self.perf.span("startup.select_database"):
            self.select_database()
        with self.perf.span("startup.initialize_ui_vars"):
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
                self._ensure_generated_tree_cache_table()
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
            self._ensure_generated_tree_cache_table()
            # Save this database as the preferred one
            if self.db_path and self.db_name:
                self.db_preferences.save_database_preference(self.db_path, self.db_name)
                self.logger.info(f"Saved database preference: {self.db_name} at {self.db_path}")
            
    def initialize_ui_vars(self):
        # set root
        self.root = tk.Tk()
        self.root.geometry('1600x1000')
        self.root.minsize(1400, 900)
        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.attributes('-zoomed', True)
        self.root.title(f"QTR'S KLIK KLAKER")

        # set key bindings
        self.root.bind('<Escape>', lambda event: self.root.quit())
        self.root.bind('<Return>', lambda event: self.on_generate_combinations())
        self.root.bind('<FocusIn>', lambda event: self._on_root_focus_in())
        self.root.bind('<FocusOut>', lambda event: self._hide_all_popups(), add='+')
        self.root.bind('<Button-1>', self._on_root_click_for_popups, add='+')
        self.root.bind('<Configure>', self._on_root_configure, add='+')
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)

        self._last_root_size = (self.root.winfo_width(), self.root.winfo_height())

        # Create the top team name and scenario display
        self.drop_down_frame = tk.Frame(self.root)
        self.drop_down_frame.pack(side=tk.TOP)

        # Single main container (no tabs)
        self.team_grid_frame = tk.Frame(self.root)
        self.team_grid_frame.pack(expand=1, fill='both')

        self.top_frame = tk.Frame(self.team_grid_frame)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=0)
        self.top_frame.grid_columnconfigure(2, weight=1)
        self.top_frame.grid_rowconfigure(0, weight=1)

        # Single unified grid frame (left)
        self.grid_frame = tk.Frame(self.top_frame, relief=tk.RIDGE, borderwidth=2)
        self.grid_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Vertical sort controls strip between grid and matchup extract.
        self.sort_controls_frame = tk.Frame(self.top_frame, relief=tk.GROOVE, borderwidth=1)
        self.sort_controls_frame.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ns")

        # Matchup output section (right of grid, above tree)
        self.matchup_output_container = tk.Frame(self.top_frame)
        self.matchup_output_container.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="nsew")

        self.tree_autogen_var = tk.IntVar(value=1 if self.tree_autogen_enabled else 0)
        self.lazy_sort_on_expand_var = tk.IntVar(value=1 if self.lazy_sort_on_expand else 0)
        self.create_matchup_output_panel()
        self.matchup_output_panel_created = True

        self.button_row_frame = tk.Frame(self.team_grid_frame)
        self.button_row_frame.pack(side=tk.TOP, fill=tk.X)

        # Tree controls bar sits directly above the tree and keeps options right aligned.
        self.tree_options_bar = tk.Frame(self.team_grid_frame)
        self.tree_options_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 2))

        # Tree section (below grid)
        self.tree_container_frame = tk.Frame(self.team_grid_frame)
        self.tree_container_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        self.tree_view_frame = tk.Frame(self.tree_container_frame)
        self.tree_view_frame.pack(side=tk.LEFT, expand=1, fill=tk.BOTH)

        # V2: Replace 144 StringVars with single GridDataModel
        self.grid_data_model = GridDataModel()
        self.grid_data_model.add_observer(self._on_grid_data_changed)
        
        # Widget references (Entry widgets only, no StringVars)
        self.grid_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        self.grid_display_widgets: List[List[Optional[tk.Entry]]] = [[None for _ in range(6)] for _ in range(6)]
        
        # Comment overlay intentionally unused; per-cell bindings handle comments.
        self.comment_overlay = None
        
        # Track grid flip state and store original data
        self.grid_is_flipped = False
        self.original_grid_data = None

        # Grid dirty tracking and status message rotation
        self._grid_dirty = False
        self._status_messages = []
        self._status_message_index = 0
        self._status_message_phase = 0
        self._status_message_job = None
        self._status_font_normal = ("Arial", 8)
        self._status_font_emphasis = ("Arial", 8, "bold")
        self._status_fg_normal = "#666666"
        self._status_fg_emphasis = "#000000"

        # Clipboard paste helpers
        self._paste_5x5_button = None
        self._top_left_rating_entry = None

        # Header name tooltip state
        self._name_tooltip_window = None
        self._name_tooltip_label = None
        self._name_tooltip_cell = None

        # Comment tooltip state
        self._comment_tooltip_window = None
        self._comment_tooltip_label = None
        self._comment_tooltip_cell = None
        self._comment_editor_open = False
        self._popup_pending = False
        self.notes_text: Optional[tk.Text] = None
        self._tree_explain_tooltip: Optional[tk.Toplevel] = None
        self._tree_explain_tooltip_label: Optional[tk.Label] = None
        self._tree_explain_last_node: Optional[str] = None


        self.team_b = tk.IntVar()
        pairingLead = tk.Checkbutton(self.tree_options_bar, text="Our team first", variable=self.team_b)
        pairingLead.pack(side=tk.RIGHT, padx=(8, 0), pady=5)

        # create treeview and tree generator
        self.treeview = LazyTreeView(master=self.tree_view_frame, print_output=self.print_output, columns=("Rating", "Sort Value"))
        self.tree_generator = TreeGenerator(
            treeview=self.treeview,
            strategic_preferences=self.strategic_preferences,
        )
        self.tree_generator.set_generation_id(self._tree_generation_id)
        
        # Track current sorting mode for column display
        self.current_sort_mode = "none"

        # Column sorting state
        self.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
        self.active_column_sort = None
        
        # Matchup output panel is created as part of right-column setup
        self.matchup_output_panel_created = True
        

    
    def _populate_dropdowns(self):
        """Populate dropdowns after UI is visible (deferred for performance)"""
        with self.perf.span("startup.populate_dropdowns"):
            self.set_team_dropdowns()
            self.update_scenario_box()
    

    
    def create_ui(self):
        with self.perf.span("startup.create_ui_grids"):
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
        self.team1_var.trace_add('write', self._on_team_box_change_traced)
		
        tk.Label(self.drop_down_frame, text='Select Team 2:').pack(side=tk.LEFT, padx=5, pady=5)
        # Use a StringVar to hold the value of the Combobox
        self.team2_var = tk.StringVar()
        # create combobox
        self.combobox_2 = ttk.Combobox(self.drop_down_frame, state='readonly', width=20, textvariable=self.team2_var)
        self.combobox_2.pack(side=tk.LEFT, padx=5, pady=5)
        # Set an instance variable to keep track of the previous value
        self.previous_team2 = self.team2_var.get()
        # Attach a trace to the StringVar
        self.team2_var.trace_add('write', self._on_team_box_change_traced)

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
        self.scenario_var.trace_add('write', self._on_scenario_box_change_traced)
        
        # Defer team dropdowns and scenario box population to after UI is shown
        self.root.after(10, self._populate_dropdowns)

        # Add essential buttons to a row just above the pairing grid       
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        self.flip_grid_button = tk.Button(self.button_row_frame, text="Flip Grid", command=lambda: self.flip_grid_perspective())
        self.flip_grid_button.pack(side=tk.LEFT, padx=5, pady=5)

        self._paste_5x5_button = tk.Button(
            self.button_row_frame,
            text="Paste 5x5",
            command=self._on_paste_5x5_button,
            state=tk.DISABLED
        )
        self._paste_5x5_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Data Management menu button
        data_mgmt_button = tk.Button(self.button_row_frame, text="Data Management", 
                                   command=lambda: self.show_data_management_menu(),
                                   bg="lightcyan", fg="darkgreen", font=("Arial", 9, "bold"),
                                   relief=tk.RAISED, borderwidth=2)
        data_mgmt_button.pack(side=tk.LEFT, padx=10, pady=5)
        

        
        # Configure Treeview with style
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10))
        self.treeview.tree.heading("#0", text="Pairing", command=lambda: self.on_column_click("#0"))
        self.treeview.tree.heading("Rating", text="Rating", command=lambda: self.on_column_click("Rating"))
        self.treeview.tree.heading("Sort Value", text="Sort Value", command=lambda: self.on_column_click("Sort Value"))
        
        # Configure column widths
        self.treeview.tree.column("Rating", width=80, minwidth=50)
        self.treeview.tree.column("Sort Value", width=100, minwidth=80)
        self.treeview.tree.tag_configure('1', background="orangered")
        self.treeview.tree.tag_configure('2', background="orange")
        self.treeview.tree.tag_configure('3', background="yellow")
        self.treeview.tree.tag_configure('4', background="greenyellow")
        self.treeview.tree.tag_configure('5', background="lime")
        self.treeview.tree.bind("<<TreeviewSelect>>", self._on_tree_selection_changed, add='+')
        self.treeview.tree.bind("<<TreeviewOpen>>", self._on_tree_node_opened, add='+')
        self.treeview.tree.bind("<Motion>", self._on_tree_hover_explain, add='+')
        self.treeview.tree.bind("<Leave>", self._hide_tree_explain_tooltip, add='+')
        self.treeview.pack(expand=1, fill='both')
        
        # Create centered vertical sort strip between grid and matchup extract
        generateButton = tk.Button(self.sort_controls_frame, text="Generate\nCombinations", command=self.on_generate_combinations, width=16)
        generateButton.pack(fill=tk.X, padx=8, pady=(8, 5))

        # Initialize sorting state tracking
        self.active_sort_mode = None
        
        # Create sorting buttons with active/inactive states
        self.cumulative_button = tk.Button(self.sort_controls_frame, text="Cumulative\nSort", command=self.toggle_cumulative_sort, width=16)
        self.cumulative_button.pack(fill=tk.X, padx=8, pady=5)

        self.confidence_button = tk.Button(self.sort_controls_frame, text="Highest\nConfidence", command=self.toggle_confidence_sort, width=16)
        self.confidence_button.pack(fill=tk.X, padx=8, pady=5)

        self.counter_button = tk.Button(self.sort_controls_frame, text="Counter\nPick", command=self.toggle_counter_sort, width=16)
        self.counter_button.pack(fill=tk.X, padx=8, pady=5)

        self.strategic_button = tk.Button(self.sort_controls_frame, text="Strategic\nFusion", command=self.toggle_strategic_sort, width=16)
        self.strategic_button.pack(fill=tk.X, padx=8, pady=5)

        self.sort_guidance_label = tk.Label(
            self.sort_controls_frame,
            text="Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            font=("Arial", 8),
            fg="#333333",
            justify=tk.LEFT,
            anchor=tk.W
        )
        self.sort_guidance_label.pack(fill=tk.X, padx=8, pady=(6, 8))
        
        # Set initial button states (all inactive)
        self.update_sort_button_states()
        
        # Add tooltip
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here\nNavigate the tree with arrow keys!")
        
        # Matchup output panel is created on startup
        
        # Load grid once widgets exist
        self.root.after(1, self.load_grid_data_from_db)

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")

        self.update_combobox_colors()
        self.init_display_headers()
        
        # Create status bar
        self.create_status_bar()
        self._refresh_paste_button_state()
        
        # Show welcome dialog if this is first time or user hasn't disabled it
        if self.db_preferences.should_show_welcome_message():
            self.root.after(500, self.show_welcome_dialog)  # Delay to ensure UI is ready

        self.root.mainloop()
        if hasattr(self, 'perf') and self.perf:
            self.perf.close()

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
        calc_header.grid(row=1, column=7, columnspan=5, pady=(0, 2), sticky="ew")

        # V2: Create the 6x6 rating grid WITHOUT StringVars or bindings
        # All state managed by GridDataModel; comments handled per cell.
        with self.perf.span("grid.create_rating_cells"):
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

                    if (r == 0 and c > 0) or (c == 0 and r > 0):
                        entry.bind(
                            "<Button-1>",
                            lambda event, row=r, col=c: self._toggle_name_tooltip(event, row, col),
                            add='+'
                        )

                    if r == 1 and c == 1:
                        self._top_left_rating_entry = entry
                        entry.bind("<Control-v>", self._on_top_left_paste_event, add='+')
                        entry.bind("<<Paste>>", self._on_top_left_paste_event, add='+')
                        entry.bind("<FocusIn>", lambda event: self._refresh_paste_button_state(), add='+')

                    # Right-click per-cell comment editor for matchup cells
                    if r > 0 and c > 0:
                        entry.bind(
                            "<Button-1>",
                            lambda event, row=r, col=c: self._toggle_comment_tooltip(event, row, col),
                            add='+'
                        )
                        entry.bind("<Button-3>", lambda event, row=r, col=c: self.open_comment_editor(event, row, col), add='+')
                
                    # Set initial value from model (Phase 1: handle None ΓåÆ '')
                    initial_value = self.grid_data_model.get_rating(r, c)
                    if initial_value is None:
                        entry.insert(0, '')
                    else:
                        entry.insert(0, str(initial_value))

        # Create the display grid (right side of unified grid, columns 7-11)
        with self.perf.span("grid.create_display_cells"):
            for r in range(6):
                for c in range(5):
                    # Display grid entries (columns 7-11) - no textvariable
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
        for i in range(12):  # columns 0-11
            self.grid_frame.grid_columnconfigure(i, weight=0)  # Fixed width

        # Add row checkboxes (column 12)
        checkbox_label = tk.Label(self.grid_frame, text="Row\nSelect", font=("Arial", 9, "bold"))
        checkbox_label.grid(row=1, column=12, pady=(0, 2))
        
        for r in range(1, 6):
            var = tk.IntVar()
            entry = tk.Checkbutton(self.grid_frame, variable=var, text=f"R{r}")
            entry.grid(row=r + 2, column=12, padx=2, pady=1, sticky="w")
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
        self.grid_frame.grid_columnconfigure(12, weight=0)
        
        # Per-cell bindings handle comment editing and click-to-show popups.

    def on_row_checkbox_change(self, row, var):
        for col in range(1,6):
            widget = self.grid_widgets[row][col]
            if var.get() == 1:  # Checkbox is checked
                if self.grid_data_model.is_cell_disabled(row, col):
                    continue
                widget.config(state='disabled', bg='grey')
                # V2: Update data model and display
                self.grid_data_model.set_cell_disabled(row, col, True)
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.column_checkboxes[col-1].get() == 0:  # Column checkbox is also unchecked
                    if not self.grid_data_model.is_cell_disabled(row, col):
                        continue
                    widget.config(state='normal')
                    self.grid_data_model.set_cell_disabled(row, col, False)
                    # V2: No need to call update_color_on_change explicitly - observer handles it

        # Row/column lock-ins drive calc-grid advisory fields only.
        # Keep tree caches/scores intact to preserve UI responsiveness.
        self._schedule_scenario_calculations(immediate=True)

    def on_column_checkbox_change(self, col, var):
        for row in range(1,6):
            widget = self.grid_widgets[row][col]
            if var.get() == 1:  # Checkbox is checked
                if self.grid_data_model.is_cell_disabled(row, col):
                    continue
                widget.config(state='disabled', bg='grey')
                # V2: Update data model and display
                self.grid_data_model.set_cell_disabled(row, col, True)
                self.update_display_fields(row, col, "---")
            else:  # Checkbox is unchecked
                if self.row_checkboxes[row-1].get() == 0:  # Row checkbox is also unchecked
                    if not self.grid_data_model.is_cell_disabled(row, col):
                        continue
                    widget.config(state='normal')
                    self.grid_data_model.set_cell_disabled(row, col, False)
                    # V2: Observer handles color update

        # Row/column lock-ins drive calc-grid advisory fields only.
        # Keep tree caches/scores intact to preserve UI responsiveness.
        self._schedule_scenario_calculations(immediate=True)

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
        if self._resize_active:
            self._mark_grid_color_dirty()
            return
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
        if not widget:
            return

        if self._has_comment_cached(row, col):
            new_color = '#ffffcc'
        elif value_str in self.color_map:
            new_color = self.color_map[value_str]
        else:
            new_color = 'white'

        if widget.cget('bg') != new_color:
            widget.config(bg=new_color)
    
    def update_grid_colors(self):
        """Update all grid cell colors based on current rating system"""
        if self._resize_active:
            self._mark_grid_color_dirty()
            return
        self._grid_color_dirty = False
        comment_map = self._get_comment_map_for_current_selection()
        for row in range(1, 6):
            for col in range(1, 6):
                # V2: Get value from GridDataModel (may be int or str)
                value = self.grid_data_model.get_rating(row, col)
                value_str = str(value) if value != '' else ''
                widget = self.grid_widgets[row][col]
                
                # Check for comment indicator first
                if not widget:
                    continue

                if self._has_comment_cached(row, col, comment_map=comment_map):
                    new_color = '#ffffcc'
                elif value_str in self.color_map:
                    new_color = self.color_map[value_str]
                else:
                    new_color = 'white'

                if widget.cget('bg') != new_color:
                    widget.config(bg=new_color)
    
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

        # Dynamic status messages (e.g., unsaved changes)
        self.dynamic_status_frame = tk.Frame(self.status_frame, width=240, height=22)
        self.dynamic_status_frame.pack(side=tk.RIGHT, padx=10, pady=2)
        self.dynamic_status_frame.pack_propagate(False)

        self.dynamic_status_label = tk.Label(
            self.dynamic_status_frame,
            text="",
            anchor=tk.W,
            font=self._status_font_normal,
            fg=self._status_fg_normal
        )
        self.dynamic_status_label.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2, pady=1)
        
        # Add color preview
        color_frame = tk.Frame(self.status_frame)
        color_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Label(color_frame, text="Colors:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(0, 3))
        
        for rating in sorted(self.color_map.keys()):
            color_box = tk.Label(color_frame, text=rating, bg=self.color_map[rating], 
                               width=2, relief=tk.RAISED, borderwidth=1, font=("Arial", 7, "bold"))
            color_box.pack(side=tk.LEFT, padx=1)

        self._refresh_status_messages()
    
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

        self._refresh_status_messages()

    def _set_perf_logging(self, enabled: bool):
        self.perf_logging_enabled = enabled
        self.perf.set_enabled(enabled)
        self.db_preferences.update_ui_preferences({"perf_logging_enabled": enabled})

    def _on_perf_logging_toggle(self):
        enabled = bool(self.perf_logging_var.get())
        self._set_perf_logging(enabled)

    def _notify_restart_required(self, setting_name: str, enabled: bool):
        state_label = "enabled" if enabled else "disabled"
        messagebox.showwarning(
            "Restart Required",
            f"{setting_name} has been {state_label}.\n\n"
            "Please restart the application for this change to take effect."
        )

    def _on_tree_autogen_toggle(self):
        enabled = bool(self.tree_autogen_var.get())
        self.db_preferences.set_tree_autogen_enabled(enabled)
        self._notify_restart_required("Tree auto-generation", enabled)

    def _on_lazy_sort_toggle(self):
        enabled = bool(self.lazy_sort_on_expand_var.get())
        self.lazy_sort_on_expand = enabled
        self.lazy_sort_mode = "fast_expand_first" if enabled else "strict"
        self.db_preferences.update_ui_preferences(
            {
                "lazy_sort_on_expand": enabled,
                "lazy_sort_mode": self.lazy_sort_mode,
            }
        )

    def _on_tree_node_opened(self, _event=None):
        if not getattr(self, "lazy_sort_on_expand", False):
            return
        if not self.active_sort_mode and not self.active_column_sort:
            return

        node = ""
        try:
            node = self.treeview.tree.focus() or ""
        except Exception:
            node = ""
        if not node:
            return

        self._sort_children_combined(
            node,
            self.active_sort_mode,
            self.active_column_sort,
            recurse_mode="expanded",
        )

    def _set_grid_dirty(self, is_dirty: bool):
        if self._grid_dirty != is_dirty:
            self._grid_dirty = is_dirty
            self._refresh_status_messages()

    def _refresh_status_messages(self):
        messages = []
        if self._grid_dirty:
            messages.append("Unsaved grid data")
        self._set_status_messages(messages)

    def _set_status_messages(self, messages: List[str]):
        if not hasattr(self, 'dynamic_status_label'):
            return

        self._status_messages = [msg for msg in messages if msg]
        self._status_message_index = 0
        self._status_message_phase = 0

        self._cancel_status_rotation()

        if not self._status_messages:
            self.dynamic_status_label.config(text="")
            return

        self._rotate_status_message()

    def _cancel_status_rotation(self):
        if self._status_message_job is not None:
            try:
                self.root.after_cancel(self._status_message_job)
            except Exception:
                pass
            self._status_message_job = None

    def _rotate_status_message(self):
        if not self._status_messages or not hasattr(self, 'dynamic_status_label'):
            return

        message = self._status_messages[self._status_message_index]

        if self._status_message_phase == 0:
            self.dynamic_status_label.config(
                text=message,
                font=self._status_font_normal,
                fg=self._status_fg_normal
            )
            delay_ms = 300
        elif self._status_message_phase == 1:
            self.dynamic_status_label.config(
                text=message,
                font=self._status_font_emphasis,
                fg=self._status_fg_emphasis
            )
            delay_ms = 800
        elif self._status_message_phase == 2:
            self.dynamic_status_label.config(
                text=message,
                font=self._status_font_normal,
                fg=self._status_fg_normal
            )
            delay_ms = 300
        else:
            self._status_message_phase = 0
            self._status_message_index = (self._status_message_index + 1) % len(self._status_messages)
            delay_ms = 200
            self._status_message_job = self.root.after(delay_ms, self._rotate_status_message)
            return

        self._status_message_phase += 1
        self._status_message_job = self.root.after(delay_ms, self._rotate_status_message)

    def _on_root_focus_in(self):
        self._refresh_paste_button_state()

    def _on_app_close(self):
        try:
            if hasattr(self, 'perf') and self.perf:
                self.perf.close()
        finally:
            self.root.destroy()

    def _mark_grid_color_dirty(self):
        self._grid_color_dirty = True

    def _invalidate_calc_grid_cache(self):
        self._calc_grid_cache.clear()

    def _current_lock_masks(self):
        row_mask = tuple(int(v.get()) for v in self.row_checkboxes) if self.row_checkboxes else (0, 0, 0, 0, 0)
        col_mask = tuple(int(v.get()) for v in self.column_checkboxes) if self.column_checkboxes else (0, 0, 0, 0, 0)
        return row_mask, col_mask

    def _get_grid_ratings_signature(self):
        matrix = []
        for row in range(1, 6):
            row_values = []
            for col in range(1, 6):
                value = self.grid_data_model.get_rating(row, col)
                if isinstance(value, int):
                    row_values.append(value)
                else:
                    row_values.append(None)
            matrix.append(tuple(row_values))
        return tuple(matrix)

    def _build_calc_grid_cache_key(self):
        team_1 = self.combobox_1.get().strip() if hasattr(self, 'combobox_1') else ""
        team_2 = self.combobox_2.get().strip() if hasattr(self, 'combobox_2') else ""
        scenario_id = self.get_scenario_num() if hasattr(self, 'scenario_box') else 0
        row_mask, col_mask = self._current_lock_masks()
        return (team_1, team_2, scenario_id, row_mask, col_mask, self._get_grid_ratings_signature())

    def _compute_calc_grid_rows_for_current_state(self):
        row_mask, _ = self._current_lock_masks()
        floor_values = {}
        pinned_values = {}
        can_pin_values = {}
        protect_values = {}
        bus_values = {}

        for row in range(1, 6):
            if row_mask[row - 1] == 1:
                floor_values[row] = "---"
                continue
            floor_rating_sum = 0
            for col in range(1, 6):
                widget = self.grid_widgets[row][col]
                if widget is not None and widget.cget('state') != 'disabled':
                    cell_value = self.grid_data_model.get_rating(row, col)
                    if isinstance(cell_value, int):
                        floor_rating_sum += cell_value
            floor_values[row] = floor_rating_sum

        for row in range(1, 6):
            if row_mask[row - 1] == 1:
                pinned_values[row] = "---"
                can_pin_values[row] = "---"
                protect_values[row] = "---"
                bus_values[row] = "---"
                continue

            num_bad_matchups = 0
            good_matchups = 0
            for col in range(1, 6):
                widget = self.grid_widgets[row][col]
                if widget is not None and widget.cget('state') != 'disabled':
                    cell_value = self.grid_data_model.get_rating(row, col)
                    if isinstance(cell_value, int):
                        if cell_value < 3:
                            num_bad_matchups += 1
                        if cell_value > 3:
                            good_matchups += 1

            pinned_values[row] = "PINNED!" if num_bad_matchups > 1 else "---"
            can_pin_values[row] = "PIN" if good_matchups > 1 else "---"
            protect_values[row] = "Yes" if (pinned_values[row] != "---" or can_pin_values[row] != "---") else "No"

            floor_value = floor_values[row]
            if floor_value == "---":
                bus_values[row] = "---"
                continue

            all_margins = []
            for col in range(1, 6):
                col_margin_sum = 0
                for row1 in range(1, 6):
                    widget = self.grid_widgets[row1][col]
                    if widget is not None and widget.cget('state') != 'disabled':
                        cell_value = self.grid_data_model.get_rating(row1, col)
                        if isinstance(cell_value, int):
                            col_margin_sum += cell_value
                all_margins.append(int(floor_value) - col_margin_sum)

            max_margin = max(all_margins)
            min_margin = min(all_margins)
            bus_values[row] = self._get_bus_advisory_label(max_margin=max_margin, min_margin=min_margin)

        return {
            "floor": floor_values,
            "pinned": pinned_values,
            "can_pin": can_pin_values,
            "protect": protect_values,
            "bus": bus_values,
        }

    def _apply_calc_grid_rows(self, rows):
        for row in range(1, 6):
            self.update_display_fields(row, 0, rows["floor"].get(row, "---"))
            self.update_display_fields(row, 1, rows["pinned"].get(row, "---"))
            self.update_display_fields(row, 2, rows["can_pin"].get(row, "---"))
            self.update_display_fields(row, 3, rows["protect"].get(row, "---"))
            self.update_display_fields(row, 4, rows["bus"].get(row, "---"))

    def _invalidate_tree_cache(self, reason: str = ""):
        if self._tree_cache:
            self._tree_cache.clear()
        self._tree_cache_key = None
        self._invalidate_calc_grid_cache()
        self._sorted_children_cache.clear()
        self._primary_metrics_dirty = True
        self._last_primary_metrics_signature = None
        self._metric_signatures.clear()
        if hasattr(self, 'tree_generator') and self.tree_generator:
            self.tree_generator.clear_memoization(reason=reason)
        if reason and self.perf.enabled:
            self._log_perf_entry("tree.cache.invalidate", 0.0, reason=reason)

    def _tree_has_nodes(self) -> bool:
        if not hasattr(self, 'treeview'):
            return False
        return bool(self.treeview.tree.get_children())

    def _build_tree_cache_key(self) -> Optional[tuple]:
        if not hasattr(self, 'team1_var') or not hasattr(self, 'team2_var'):
            return None
        team_1 = self.team1_var.get().strip()
        team_2 = self.team2_var.get().strip()
        if not team_1 or not team_2:
            return None
        scenario_id = self.get_scenario_num() if hasattr(self, 'scenario_box') else 0
        rating_system = self.current_rating_system
        team_first = bool(self.team_b.get()) if hasattr(self, 'team_b') else True
        ratings_signature = json.dumps(self._get_grid_ratings_signature(), ensure_ascii=False)
        return (team_1, team_2, scenario_id, rating_system, team_first, ratings_signature)

    def _next_tree_generation_id(self) -> int:
        self._tree_generation_id += 1
        return self._tree_generation_id

    def _set_tree_generation_id(self, generation_id: int):
        try:
            normalized = int(generation_id)
        except (TypeError, ValueError):
            normalized = 0
        if normalized <= 0:
            normalized = self._next_tree_generation_id()
        self._tree_generation_id = normalized
        if hasattr(self, 'tree_generator') and self.tree_generator:
            self.tree_generator.set_generation_id(normalized)

    def _set_tree_memo_state_token(self, cache_key=None):
        if not hasattr(self, 'tree_generator') or not self.tree_generator:
            return

        token_source = cache_key if cache_key is not None else self._build_tree_cache_key()
        if token_source is None:
            token_source = ("uncached", self._tree_generation_id)

        token = json.dumps(token_source, ensure_ascii=False, default=str)
        self.tree_generator.set_memo_state_token(token)

    def _ensure_generated_tree_cache_table(self):
        if not getattr(self, 'db_path', None) or not getattr(self, 'db_name', None):
            return
        sql = """
            CREATE TABLE IF NOT EXISTS generated_tree_cache (
                team_1_name TEXT NOT NULL,
                team_2_name TEXT NOT NULL,
                scenario_id INTEGER NOT NULL,
                rating_system TEXT NOT NULL,
                team_first INTEGER NOT NULL,
                ratings_signature TEXT NOT NULL,
                generation_id INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_1_name, team_2_name, scenario_id, rating_system, team_first, ratings_signature)
            )
        """
        try:
            self.db_manager.execute_sql(sql)
            with self.db_manager.connect_db(self.db_path, self.db_name) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(generated_tree_cache)")
                existing_columns = {row[1] for row in cur.fetchall()}
                if "ratings_signature" not in existing_columns:
                    # Cache table is versioned by schema; recreate to guarantee exact-input keys.
                    cur.execute("DROP TABLE IF EXISTS generated_tree_cache")
                    cur.execute(sql)
                    conn.commit()
        except Exception as exc:
            self.logger.warning(f"Could not ensure generated_tree_cache table: {exc}")

    def _load_persistent_tree_snapshot(self, cache_key: tuple):
        if not cache_key or not getattr(self, 'db_path', None) or not getattr(self, 'db_name', None):
            return None
        self._ensure_generated_tree_cache_table()
        team_1, team_2, scenario_id, rating_system, team_first, ratings_signature = cache_key
        try:
            with self.db_manager.connect_db(self.db_path, self.db_name) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT snapshot_json, generation_id
                    FROM generated_tree_cache
                    WHERE team_1_name = ?
                      AND team_2_name = ?
                      AND scenario_id = ?
                      AND rating_system = ?
                      AND team_first = ?
                                            AND ratings_signature = ?
                    """,
                                        (
                                                team_1,
                                                team_2,
                                                int(scenario_id),
                                                str(rating_system),
                                                int(bool(team_first)),
                                                str(ratings_signature),
                                        ),
                )
                row = cur.fetchone()
            if not row:
                return None
            snapshot_json, generation_id = row
            return {
                "snapshot": json.loads(snapshot_json),
                "generation_id": int(generation_id),
            }
        except Exception as exc:
            self.logger.warning(f"Failed to load persistent tree cache: {exc}")
            return None

    def _save_persistent_tree_snapshot(self, cache_key: tuple, payload: Dict[str, Any]):
        if not cache_key or not payload or not getattr(self, 'db_path', None) or not getattr(self, 'db_name', None):
            return
        self._ensure_generated_tree_cache_table()
        team_1, team_2, scenario_id, rating_system, team_first, ratings_signature = cache_key
        try:
            snapshot_json = json.dumps(payload.get("snapshot", []), ensure_ascii=False)
            generation_id = int(payload.get("generation_id", self._tree_generation_id or 1))
            with self.db_manager.connect_db(self.db_path, self.db_name) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO generated_tree_cache
                    (team_1_name, team_2_name, scenario_id, rating_system, team_first, ratings_signature, generation_id, snapshot_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(team_1_name, team_2_name, scenario_id, rating_system, team_first, ratings_signature)
                    DO UPDATE SET
                        generation_id = excluded.generation_id,
                        snapshot_json = excluded.snapshot_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        team_1,
                        team_2,
                        int(scenario_id),
                        str(rating_system),
                        int(bool(team_first)),
                        str(ratings_signature),
                        generation_id,
                        snapshot_json,
                    ),
                )
                conn.commit()
        except (sqlite3.Error, TypeError, ValueError) as exc:
            self.logger.warning(f"Failed to persist tree cache snapshot: {exc}")

    def _capture_tree_snapshot(self):
        def walk(node_id):
            item = self.treeview.tree.item(node_id)
            children = self.treeview.tree.get_children(node_id)
            return {
                "text": item.get("text", ""),
                "values": item.get("values", ()),
                "tags": item.get("tags", ()),
                "open": bool(item.get("open", False)),
                "children": [walk(child) for child in children]
            }

        roots = self.treeview.tree.get_children()
        return [walk(node_id) for node_id in roots]

    def _restore_tree_snapshot(self, snapshot):
        self.treeview.tree.delete(*self.treeview.tree.get_children())

        def insert_node(parent, node):
            new_id = self.treeview.tree.insert(
                parent,
                'end',
                text=node.get("text", ""),
                values=node.get("values", ()),
                tags=node.get("tags", ())
            )
            if node.get("open"):
                self.treeview.tree.item(new_id, open=True)
            for child in node.get("children", []):
                insert_node(new_id, child)
            return new_id

        for root in snapshot or []:
            insert_node("", root)

    def _reset_tree_sort_state(self):
        self.active_sort_mode = None
        self.is_sorted = False
        self.current_sort_mode = "none"
        self.column_sort_states = {"#0": "none", "Rating": "none", "Sort Value": "none"}
        self.active_column_sort = None
        self._sorted_children_cache.clear()
        self._primary_metrics_dirty = True
        self._last_primary_metrics_signature = None
        self._metric_signatures.clear()
        self._available_explainability_metrics.clear()
        self.update_column_headers()
        self.update_sort_value_column()
        self.update_sort_button_states()
        self._update_sort_hint()

    def _mark_explainability_metrics_available(self, primary_mode):
        if primary_mode == "cumulative":
            self._available_explainability_metrics.add("cumulative")
        elif primary_mode == "confidence":
            self._available_explainability_metrics.add("confidence")
            self._available_explainability_metrics.add("regret")
            self._available_explainability_metrics.add("downside")
            self._available_explainability_metrics.add("guardrail")
        elif primary_mode == "resistance":
            self._available_explainability_metrics.add("resistance")
        elif primary_mode == "strategic3":
            self._available_explainability_metrics.add("strategic")
            self._available_explainability_metrics.add("exploit")

    def _format_explainability_metric(self, metric_key, value):
        if metric_key in self._available_explainability_metrics:
            return str(value)
        return "--"

    def _build_primary_metrics_signature(self, primary_mode):
        if not primary_mode:
            return None

        metric_signature = self._build_metric_signature(primary_mode)
        return (primary_mode, metric_signature)

    def _base_cache_signature(self):
        cache_key = self._build_tree_cache_key()
        if cache_key is None:
            scenario_id = self.get_scenario_num() if hasattr(self, 'scenario_box') else 0
            team_first = bool(self.team_b.get()) if hasattr(self, 'team_b') else True
            ratings_signature = self._get_grid_ratings_signature() if hasattr(self, 'grid_data_model') else None
            cache_key = (
                self.team1_var.get().strip() if hasattr(self, 'team1_var') else "",
                self.team2_var.get().strip() if hasattr(self, 'team2_var') else "",
                scenario_id,
                getattr(self, 'current_rating_system', ''),
                team_first,
                ratings_signature,
            )
        return cache_key

    def _build_metric_signature(self, metric_key):
        cache_key = self._base_cache_signature()
        if not hasattr(self, 'tree_generator') or not self.tree_generator:
            return (metric_key, cache_key)

        tree_gen = self.tree_generator

        def numeric(value, default=0.0):
            try:
                return round(float(value), 6)
            except (TypeError, ValueError):
                return round(float(default), 6)

        if metric_key == "cumulative":
            return (metric_key, cache_key, numeric(tree_gen.cumulative2_alpha, 0.8))
        if metric_key == "confidence":
            return (
                metric_key,
                cache_key,
                numeric(tree_gen.confidence2_k, 0.85),
                numeric(tree_gen.confidence2_u, 12.0),
            )
        if metric_key == "resistance":
            return (
                metric_key,
                cache_key,
                numeric(tree_gen.resistance2_beta, 1.0),
                numeric(tree_gen.resistance2_gamma, 2.0),
            )
        if metric_key == "strategic3":
            return (
                metric_key,
                cache_key,
                tree_gen._compute_parameter_signature(),
                self._build_metric_signature("cumulative"),
                self._build_metric_signature("confidence"),
                self._build_metric_signature("resistance"),
            )

        return (metric_key, cache_key)

    def _is_metric_stale(self, metric_key):
        if self._primary_metrics_dirty:
            return True
        return self._metric_signatures.get(metric_key) != self._build_metric_signature(metric_key)

    def _mark_metric_fresh(self, metric_key):
        self._metric_signatures[metric_key] = self._build_metric_signature(metric_key)

    def _should_recompute_primary_on_column_click(self):
        if not self.active_sort_mode:
            return False

        if self._primary_metrics_dirty:
            return True

        current_signature = self._build_primary_metrics_signature(self.active_sort_mode)
        return current_signature != self._last_primary_metrics_signature

    def _log_perf_entry(self, label: str, elapsed_ms: float, **meta: Any):
        if not self.perf.enabled:
            return
        try:
            self.perf._write_log(label, elapsed_ms, meta)
        except Exception:
            pass

    def _record_event_loop_lag(self, source: str, start_time: float):
        if not hasattr(self, 'root') or not self.perf.enabled:
            return

        def log_lag():
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            if elapsed_ms >= self._event_loop_lag_threshold_ms:
                self._log_perf_entry("event_loop.lag", elapsed_ms, source=source)

        self.root.after_idle(log_lag)

    def _measure_update_idletasks(self, label: str):
        if not hasattr(self, 'root') or not self.perf.enabled:
            return

        start = time.perf_counter()
        self.root.update_idletasks()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._log_perf_entry(label, elapsed_ms)

    def _on_root_configure(self, event):
        if event.widget is not self.root:
            return

        width = int(event.width)
        height = int(event.height)
        if (width, height) == self._last_root_size:
            return

        now = time.perf_counter()
        self._last_root_size = (width, height)

        if not self._resize_active:
            self._resize_active = True
            self._resize_start_time = now
            self._resize_event_count = 0
            self._resize_start_size = (width, height)
            self._record_event_loop_lag("resize.burst", now)

        self._resize_end_size = (width, height)
        self._resize_last_time = now
        self._resize_event_count += 1
        self._mark_grid_color_dirty()

        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass

        self._resize_job = self.root.after(150, self._finalize_resize_burst)

    def _finalize_resize_burst(self):
        if not self._resize_active:
            return

        duration_ms = (self._resize_last_time - self._resize_start_time) * 1000.0
        delta_w = self._resize_end_size[0] - self._resize_start_size[0]
        delta_h = self._resize_end_size[1] - self._resize_start_size[1]
        resize_kind = self._classify_resize_burst(duration_ms, self._resize_event_count)

        self._log_perf_entry(
            "resize.burst",
            duration_ms,
            start_w=self._resize_start_size[0],
            start_h=self._resize_start_size[1],
            end_w=self._resize_end_size[0],
            end_h=self._resize_end_size[1],
            delta_w=delta_w,
            delta_h=delta_h,
            events=self._resize_event_count,
            kind=resize_kind
        )

        self._resize_active = False
        self._resize_job = None

        if self._grid_color_dirty:
            self._grid_color_dirty = False
            self.update_grid_colors()

    def _classify_resize_burst(self, duration_ms: float, event_count: int) -> str:
        if duration_ms >= 200.0 and event_count > 2:
            return "drag"
        return "one_off"

    def _schedule_tree_autogenerate(self):
        if not hasattr(self, 'root'):
            return
        if not self.tree_autogen_enabled:
            return
        if self._tree_autogen_job is not None:
            try:
                self.root.after_cancel(self._tree_autogen_job)
            except Exception:
                pass

        self._tree_autogen_job = self.root.after(75, self.auto_generate_tree_after_teams_loaded)

    def _read_clipboard_text(self) -> Optional[str]:
        try:
            return self.root.clipboard_get()
        except tk.TclError:
            return None

    def _parse_clipboard_grid(self, text: str):
        if not text:
            return None, "Clipboard is empty."

        lines = [line.strip() for line in text.strip().splitlines() if line.strip() != ""]
        if len(lines) != 5:
            return None, "Expected 5 rows of data."

        grid = []
        for line in lines:
            if "\t" in line:
                parts = line.split("\t")
            elif "," in line:
                parts = line.split(",")
            else:
                return None, "Expected tab- or comma-separated values."

            parts = [part.strip() for part in parts]
            if len(parts) != 5:
                return None, "Expected 5 columns per row."

            row_values = []
            for part in parts:
                if part == "" or not part.isdigit():
                    return None, "All values must be whole numbers."
                row_values.append(int(part))
            grid.append(row_values)

        return grid, None

    def _refresh_paste_button_state(self):
        if not self._paste_5x5_button:
            return

        clipboard_text = self._read_clipboard_text()
        grid, _ = self._parse_clipboard_grid(clipboard_text or "")
        if grid:
            self._paste_5x5_button.config(state=tk.NORMAL)
        else:
            self._paste_5x5_button.config(state=tk.DISABLED)

    def _apply_5x5_grid(self, grid: List[List[int]]):
        self.grid_data_model.begin_batch()
        for r in range(1, 6):
            for c in range(1, 6):
                self.grid_data_model.set_rating(r, c, grid[r - 1][c - 1])
        self.grid_data_model.end_batch()
        self._schedule_scenario_calculations()
        self._set_grid_dirty(True)

    def _on_paste_5x5_button(self):
        clipboard_text = self._read_clipboard_text() or ""
        grid, error = self._parse_clipboard_grid(clipboard_text)
        if not grid:
            messagebox.showerror(
                "Paste Failed",
                "Could not paste clipboard data into the grid.\n"
                "Expected a 5x5 grid of numbers separated by tabs or commas."
            )
            return

        self._apply_5x5_grid(grid)
        messagebox.showinfo(
            "Paste Complete",
            "Pasted 25 values into the ratings grid.\nRemember to Save Grid to keep changes."
        )
        self._refresh_paste_button_state()

    def _on_top_left_paste_event(self, event):
        clipboard_text = self._read_clipboard_text() or ""
        grid, _ = self._parse_clipboard_grid(clipboard_text)
        if not grid:
            return None

        self._apply_5x5_grid(grid)
        messagebox.showinfo(
            "Paste Complete",
            "Pasted 25 values into the ratings grid.\nRemember to Save Grid to keep changes."
        )
        self._refresh_paste_button_state()
        return "break"

    def _ensure_name_tooltip_window(self):
        if self._name_tooltip_window:
            return

        self._name_tooltip_window = tk.Toplevel(self.root)
        self._name_tooltip_window.wm_overrideredirect(True)
        self._name_tooltip_window.wm_attributes("-topmost", True)
        self._name_tooltip_window.withdraw()

        self._name_tooltip_label = tk.Label(
            self._name_tooltip_window,
            text="",
            justify=tk.LEFT,
            anchor=tk.W,
            bg="#1f2430",
            fg="#f0f3f6",
            font=("Arial", 10),
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6
        )
        self._name_tooltip_label.pack(fill=tk.BOTH, expand=True)

    def _hide_name_tooltip(self):
        if self._name_tooltip_window:
            self._name_tooltip_window.withdraw()
        self._name_tooltip_cell = None

    def _toggle_name_tooltip(self, event, row: int, col: int):
        if self._comment_editor_open:
            return
        self._ensure_name_tooltip_window()

        widget = self.grid_widgets[row][col]
        if not widget:
            return

        if self._name_tooltip_cell == (row, col):
            self._hide_name_tooltip()
            return

        self._popup_pending = True
        self._hide_comment_tooltip_popup()

        text = widget.get().strip()
        if not text:
            self._hide_name_tooltip()
            return

        if not self._is_text_truncated(widget, text):
            self._hide_name_tooltip()
            return

        wrap_width = self._get_left_grid_width()
        if self._name_tooltip_label is None:
            return
        if self._name_tooltip_window is None:
            return
        self._name_tooltip_label.config(text=text, wraplength=wrap_width)
        self._name_tooltip_window.update_idletasks()

        x = widget.winfo_rootx()
        tooltip_height = self._name_tooltip_window.winfo_height()
        y = widget.winfo_rooty() - tooltip_height - 4
        if y < 0:
            y = 0
        self._name_tooltip_window.geometry(f"+{x}+{y}")
        def show_popup():
            if self._name_tooltip_window is None:
                return
            self._name_tooltip_window.deiconify()
            self._name_tooltip_window.lift()
            self._name_tooltip_cell = (row, col)
            self._popup_pending = False

        self.root.after_idle(show_popup)

    def _ensure_comment_tooltip_window(self):
        if self._comment_tooltip_window:
            return

        self._comment_tooltip_window = tk.Toplevel(self.root)
        self._comment_tooltip_window.wm_overrideredirect(True)
        self._comment_tooltip_window.wm_attributes("-topmost", True)
        self._comment_tooltip_window.withdraw()

        self._comment_tooltip_label = tk.Label(
            self._comment_tooltip_window,
            text="",
            justify=tk.LEFT,
            anchor=tk.W,
            bg="#1f2430",
            fg="#f0f3f6",
            font=("Arial", 10),
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6
        )
        self._comment_tooltip_label.pack(fill=tk.BOTH, expand=True)

    def _hide_comment_tooltip_popup(self):
        if self._comment_tooltip_window:
            self._comment_tooltip_window.withdraw()
        self._comment_tooltip_cell = None

    def _toggle_comment_tooltip(self, event, row: int, col: int):
        if self._comment_editor_open:
            return
        self._ensure_comment_tooltip_window()

        if self._comment_tooltip_cell == (row, col):
            self._hide_comment_tooltip_popup()
            return

        comment = self._get_comment_for_cell(row, col)
        if comment is None or comment == "":
            self._hide_comment_tooltip_popup()
            return

        self._popup_pending = True
        self._hide_name_tooltip()

        wrap_length = self._get_comment_wraplength(comment)
        if self._comment_tooltip_label is None:
            return
        if self._comment_tooltip_window is None:
            return
        self._comment_tooltip_label.config(text=comment, wraplength=wrap_length)
        self._comment_tooltip_window.update_idletasks()

        widget = self.grid_widgets[row][col]
        if not widget:
            return

        x = widget.winfo_rootx()
        tooltip_height = self._comment_tooltip_window.winfo_height()
        y = widget.winfo_rooty() - tooltip_height - 4
        if y < 0:
            y = 0
        self._comment_tooltip_window.geometry(f"+{x}+{y}")
        def show_popup():
            if self._comment_tooltip_window is None:
                return
            self._comment_tooltip_window.deiconify()
            self._comment_tooltip_window.lift()
            self._comment_tooltip_cell = (row, col)
            self._popup_pending = False

        self.root.after_idle(show_popup)

    def _get_comment_for_cell(self, row: int, col: int) -> Optional[str]:
        team1_name = self.team1_var.get()
        team2_name = self.team2_var.get()
        scenario_name = self.scenario_var.get()

        friendly_player = self.grid_data_model.get_rating(row, 0)
        opponent_player = self.grid_data_model.get_rating(0, col)

        if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
            return None

        comment_map = self._get_comment_map_for_current_selection()
        return comment_map.get((friendly_player, opponent_player))

    def _get_comment_wraplength(self, text: str) -> int:
        max_width = 6 * self._get_default_column_width()
        if self._comment_tooltip_label is None:
            return max_width
        font = tkfont.Font(font=self._comment_tooltip_label.cget("font"))
        lines = text.splitlines() or [text]
        max_line_width = max(font.measure(line) for line in lines) if lines else 0
        if max_line_width > max_width:
            return max_width
        return 0

    def _get_default_column_width(self) -> int:
        widget = self.grid_widgets[1][1] if self.grid_widgets[1][1] else None
        if widget:
            width = widget.winfo_width()
            if width <= 1:
                width = widget.winfo_reqwidth()
            if width > 0:
                return width
        return 64

    def _on_root_click_for_popups(self, event):
        if self._comment_editor_open:
            self._hide_all_popups()
            return

        if self._popup_pending:
            return

        widget = event.widget
        for r in range(6):
            for c in range(6):
                if self.grid_widgets[r][c] is widget:
                    return

        self._hide_all_popups()

    def _hide_all_popups(self):
        self._hide_name_tooltip()
        self._hide_comment_tooltip_popup()

    def _is_text_truncated(self, widget: tk.Entry, text: str) -> bool:
        widget_width = widget.winfo_width()
        if widget_width <= 1:
            return len(text) > 8

        font = tkfont.Font(font=widget.cget("font"))
        text_width = font.measure(text)
        padding = 8
        return text_width > max(widget_width - padding, 1)

    def _get_left_grid_width(self) -> int:
        width = 0
        for c in range(6):
            widget = self.grid_widgets[0][c]
            if widget:
                width += widget.winfo_width()
        if width <= 0:
            return 360
        return width
    
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
            self.update_display_fields(0,4,"BUS RIDE")
            # SUM MARG removed
        except (ValueError, IndexError) as e:
            print(f"update_display_fields has failed with error:\n{e}")

    def on_scenario_calculations(self):
        self._schedule_scenario_calculations()

    def _schedule_scenario_calculations(self, immediate: bool = False):
        if not hasattr(self, 'root'):
            return

        if self._scenario_calc_job is not None:
            try:
                self.root.after_cancel(self._scenario_calc_job)
            except Exception:
                pass
            self._scenario_calc_job = None

        if immediate:
            self._run_scenario_calculations()
            return

        self._scenario_calc_job = self.root.after(
            self._scenario_calc_delay_ms,
            self._run_scenario_calculations
        )

    def _run_scenario_calculations(self):
        self._scenario_calc_job = None
        self._on_scenario_calculations()

    def _on_scenario_calculations(self):
        # Guard: Don't run calculations if teams are not selected
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()
        
        if not team_1 or not team_2:
            # Clear display fields when no teams are selected
            for row in range(1, 6):
                for col in range(0, 6):
                    self.update_display_fields(row, col, "---")
            return

        cache_key = self._build_calc_grid_cache_key()
        cached_rows = self._calc_grid_cache.get(cache_key)
        if cached_rows is None:
            cached_rows = self._compute_calc_grid_rows_for_current_state()
            self._calc_grid_cache[cache_key] = cached_rows

        self._apply_calc_grid_rows(cached_rows)

    def check_margins(self):
        for row in range(1, 6):
            try:
                if self.row_checkboxes and row - 1 < len(self.row_checkboxes) and self.row_checkboxes[row - 1].get() == 1:
                    self.update_display_fields(row, 4, "---")
                    continue
                
                # V2: Get floor value from GridDataModel
                floor_value = self.grid_data_model.get_display(row, 0)
                if not floor_value or floor_value == "---" or floor_value.strip() == "":
                    self.update_display_fields(row, 4, "---")
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
                bus_text = self._get_bus_advisory_label(max_margin=max_margin, min_margin=min_margin)
                self.update_display_fields(row, 4, bus_text)
                # SUM MARG removed
            except (ValueError, IndexError) as e:
                print(f"check_margins has failed for row {row} with error:\n{e}")

    def _get_current_round_depth(self):
        """Approximate current round depth from lock-in checkboxes (1..5)."""
        row_locked = sum(1 for v in self.row_checkboxes if v.get() == 1)
        col_locked = sum(1 for v in self.column_checkboxes if v.get() == 1)
        return max(1, min(5, max(row_locked, col_locked) + 1))

    def _get_current_scenario_number(self):
        scenario_text = ""
        if hasattr(self, "scenario_var"):
            scenario_text = (self.scenario_var.get() or "").strip()
        if not scenario_text:
            return None
        try:
            return int(scenario_text.split("-")[0].strip())
        except (ValueError, IndexError):
            return None

    def _get_bus_threshold(self):
        bus_cfg = self.strategic_preferences.get("bus", {})
        threshold_policy = bus_cfg.get("threshold_policy", "scenario_dependent")
        global_threshold = int(bus_cfg.get("global_threshold", 60))

        scenario_number = self._get_current_scenario_number()
        scenario_thresholds = bus_cfg.get("scenario_thresholds", {})
        depth_thresholds = bus_cfg.get("depth_thresholds", {})
        depth_key = str(self._get_current_round_depth())
        depth_threshold = depth_thresholds.get(depth_key)

        threshold = global_threshold
        if threshold_policy == "scenario_dependent" and scenario_number is not None:
            threshold = scenario_thresholds.get(str(scenario_number), global_threshold)

        if depth_threshold is not None:
            try:
                threshold = int((int(threshold) + int(depth_threshold)) / 2)
            except (TypeError, ValueError):
                pass

        return max(0, min(100, int(threshold)))

    def _get_bus_advisory_label(self, max_margin, min_margin):
        """Display-only BUS advisory from spread opportunity and downside risk."""
        spread = max_margin - min_margin
        downside_risk = max(0, -min_margin)
        bus_score = max(0, int((spread * 4) + (downside_risk * 2)))
        threshold = self._get_bus_threshold()
        bus_yes = bus_score >= threshold
        return f"YES ({bus_score})" if bus_yes else f"NO ({bus_score})"

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
                self._invalidate_tree_cache("database_change")
                
                # Reset sorting states
                self.active_sort_mode = None
                self.is_sorted = False
                self.current_sort_mode = "none"
                if hasattr(self, 'update_sort_button_states'):
                    self.update_sort_button_states()
                
                # Clear grid data
                self.grid_data_model.clear_grid(notify=True)
                
                # Trigger database selection
                self.select_database()
                self._invalidate_team_cache()
                self._invalidate_comment_cache()
                
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
                self._invalidate_tree_cache("rating_system_change")
                
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

    def clear_generated_tree_cache_active_matchup(self):
        """Clear persisted tree snapshots for the active matchup selection only."""
        team_1 = self.combobox_1.get().strip() if hasattr(self, 'combobox_1') else ""
        team_2 = self.combobox_2.get().strip() if hasattr(self, 'combobox_2') else ""
        if not team_1 or not team_2:
            messagebox.showwarning(
                "Tree Cache",
                "Select both teams before clearing cache for the active matchup.",
            )
            return

        scenario_id = self.get_scenario_num() if hasattr(self, 'scenario_box') else 0
        rating_system = self.current_rating_system
        team_first = int(bool(self.team_b.get())) if hasattr(self, 'team_b') else 1

        try:
            self._ensure_generated_tree_cache_table()
            with self.db_manager.connect_db(self.db_path, self.db_name) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    DELETE FROM generated_tree_cache
                    WHERE team_1_name = ?
                      AND team_2_name = ?
                      AND scenario_id = ?
                      AND rating_system = ?
                      AND team_first = ?
                    """,
                    (team_1, team_2, int(scenario_id), str(rating_system), team_first),
                )
                removed = cur.rowcount if cur.rowcount is not None else 0
                conn.commit()

            active_prefix = (team_1, team_2, int(scenario_id), str(rating_system), bool(team_first))
            self._tree_cache = {
                key: value for key, value in self._tree_cache.items() if tuple(key[:5]) != active_prefix
            }
            if self._tree_cache_key and tuple(self._tree_cache_key[:5]) == active_prefix:
                self._tree_cache_key = None
            if hasattr(self, 'tree_generator') and self.tree_generator:
                self.tree_generator.clear_memoization(reason="clear_active_generated_tree_cache")

            messagebox.showinfo(
                "Tree Cache",
                f"Removed {removed} cached tree snapshot(s) for the active matchup.",
            )
        except Exception as exc:
            messagebox.showerror("Tree Cache", f"Failed to clear active matchup cache: {exc}")

    def clear_generated_tree_cache_all_matchups(self):
        """Clear all persisted tree snapshots across all matchups."""
        try:
            self._ensure_generated_tree_cache_table()
            with self.db_manager.connect_db(self.db_path, self.db_name) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM generated_tree_cache")
                removed = cur.rowcount if cur.rowcount is not None else 0
                conn.commit()

            self._tree_cache.clear()
            self._tree_cache_key = None
            if hasattr(self, 'tree_generator') and self.tree_generator:
                self.tree_generator.clear_memoization(reason="clear_all_generated_tree_cache")

            messagebox.showinfo(
                "Tree Cache",
                f"Removed {removed} cached tree snapshot(s) across all matchups.",
            )
        except Exception as exc:
            messagebox.showerror("Tree Cache", f"Failed to clear all tree cache entries: {exc}")

    def _open_markdown_guide(self, title: str, relative_path: str):
        """Open a markdown guide in a simple in-app reader window."""
        try:
            guide_path = Path(__file__).parent.parent / relative_path
            if not guide_path.exists():
                messagebox.showerror("Guide", f"Guide file not found:\n{guide_path}")
                return

            content = guide_path.read_text(encoding="utf-8")

            guide_window = tk.Toplevel(self.root)
            guide_window.title(title)
            guide_window.geometry("900x700")
            guide_window.transient(self.root)

            header = tk.Label(
                guide_window,
                text=title,
                font=("Arial", 13, "bold"),
                bg="lightcyan",
                anchor="w",
                padx=10,
                pady=8,
            )
            header.pack(fill=tk.X)

            frame = tk.Frame(guide_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text_widget = tk.Text(
                frame,
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
                font=("Consolas", 10),
            )
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)

            text_widget.insert("1.0", content)
            text_widget.config(state=tk.DISABLED)

            footer = tk.Frame(guide_window)
            footer.pack(fill=tk.X, padx=8, pady=(0, 8))

            tk.Button(
                footer,
                text="Close",
                width=14,
                command=guide_window.destroy,
            ).pack(side=tk.RIGHT)
        except Exception as exc:
            messagebox.showerror("Guide", f"Failed to open guide: {exc}")

    def open_tooltip_numbers_guide(self):
        self._open_markdown_guide(
            title="Tree Tooltip Numbers Guide",
            relative_path="docs/NODE_TOOLTIP_NUMBERS_GUIDE.md",
        )

    def open_full_user_guide(self):
        self._open_markdown_guide(
            title="QTR Pairing Process User Guide",
            relative_path="docs/FULL_USER_GUIDE.md",
        )
    
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
            tk.Button(data_mgmt_frame, text="Clear Active Tree Cache", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.clear_generated_tree_cache_active_matchup),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(data_mgmt_frame, text="Clear All Tree Cache", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.clear_generated_tree_cache_all_matchups),
                     relief=tk.RAISED, borderwidth=1).pack(pady=(3, 10))
            tk.Button(data_mgmt_frame, text="Tooltip Numbers Guide", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.open_tooltip_numbers_guide),
                     relief=tk.RAISED, borderwidth=1).pack(pady=3)
            tk.Button(data_mgmt_frame, text="Full User Guide", width=20, height=1,
                     command=lambda: self._menu_action(menu_window, self.open_full_user_guide),
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

            self.perf_logging_var = tk.IntVar(value=1 if self.perf_logging_enabled else 0)
            perf_toggle = tk.Checkbutton(
                database_frame,
                text="Perf Logging",
                variable=self.perf_logging_var,
                command=self._on_perf_logging_toggle,
                bg="mistyrose"
            )
            perf_toggle.pack(pady=(0, 10))
            
            tree_autogen_toggle = tk.Checkbutton(
                database_frame,
                text="Tree Auto-Generate (restart)",
                variable=self.tree_autogen_var,
                command=self._on_tree_autogen_toggle,
                bg="mistyrose"
            )
            tree_autogen_toggle.pack(pady=(0, 10))

            lazy_sort_toggle = tk.Checkbutton(
                database_frame,
                text="Enable Fast Lazy Sorting",
                variable=self.lazy_sort_on_expand_var,
                command=self._on_lazy_sort_toggle,
                bg="mistyrose"
            )
            lazy_sort_toggle.pack(pady=(0, 6))

            tk.Label(
                database_frame,
                text="Sorts expanded branches first; deeper branches sort on expand.",
                bg="mistyrose",
                fg="#5b2c2c",
                font=("Arial", 8),
                wraplength=220,
                justify=tk.LEFT,
            ).pack(pady=(0, 10))
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

        cache_key = self._build_tree_cache_key()
        our_team_first = bool(self.team_b.get()) if hasattr(self, 'team_b') else True
        if self._tree_cache_enabled and cache_key:
            if cache_key == self._tree_cache_key and self._tree_has_nodes():
                self.tree_generator.our_team_first = our_team_first
                self._set_tree_generation_id(self._tree_generation_id)
                self._set_tree_memo_state_token(cache_key)
                self._log_perf_entry("tree.cache.hit", 0.0, reason="active")
                self._reset_tree_sort_state()
                return
            cached_payload = self._tree_cache.get(cache_key)
            if not cached_payload:
                cached_payload = self._load_persistent_tree_snapshot(cache_key)
                if cached_payload:
                    self._tree_cache[cache_key] = cached_payload
            if cached_payload:
                if isinstance(cached_payload, dict):
                    snapshot = cached_payload.get("snapshot", [])
                    generation_id = cached_payload.get("generation_id", self._next_tree_generation_id())
                else:
                    snapshot = cached_payload
                    generation_id = self._next_tree_generation_id()
                self._restore_tree_snapshot(snapshot)
                self._tree_cache_key = cache_key
                self.tree_generator.our_team_first = our_team_first
                self._set_tree_generation_id(generation_id)
                self._set_tree_memo_state_token(cache_key)
                self._log_perf_entry("tree.cache.hit", 0.0, reason="restore")
                self._reset_tree_sort_state()
                return
            self._log_perf_entry("tree.cache.miss", 0.0)
        
        fNames, oNames = self.prep_names()
        fRatings, oRatings = self.prep_ratings(fNames,oNames)
        if self.print_output:
            print(f"fRatings: {fRatings}\n")
            print(f"oRatings: {oRatings}\n")
        self.validate_grid_data()
        if our_team_first:
            self.tree_generator.generate_combinations(
                fNames,
                oNames,
                fRatings,
                oRatings,
                our_team_first=True,
            )
        else:
            self.tree_generator.generate_combinations(
                oNames,
                fNames,
                oRatings,
                fRatings,
                our_team_first=False,
            )
        self._set_tree_generation_id(self._next_tree_generation_id())
        self._set_tree_memo_state_token(cache_key)
        
        # Automatically expand the root "Pairings" node
        root_nodes = self.treeview.tree.get_children()
        if root_nodes:
            self.treeview.tree.item(root_nodes[0], open=True)

        if self._tree_cache_enabled and cache_key:
            cache_payload = {
                "snapshot": self._capture_tree_snapshot(),
                "generation_id": self._tree_generation_id,
            }
            self._tree_cache[cache_key] = cache_payload
            self._save_persistent_tree_snapshot(cache_key, cache_payload)
            self._tree_cache_key = cache_key
            self._log_perf_entry("tree.cache.store", 0.0)

        # Reset all sorting states when generating new combinations
        self._reset_tree_sort_state()
        if self.auto_sort_toggle_enabled and self.auto_sort_after_generate:
            # Run first-pass strategic sort through the same path as manual button clicks.
            self.sort_by_strategic()
        self._update_matchup_summary([])
        
    def sort_by_confidence(self):
        """Sort tree by risk-adjusted confidence scores"""
        self.current_sort_mode = "confidence"
        self.active_sort_mode = "confidence"
        self.apply_combined_sort(compute_primary_tags=True)
        self.update_sort_value_column()
        self.update_column_headers()
        self.is_sorted = True
        self.update_sort_button_states()
        self._update_sort_hint()

    def sort_by_counter_resistance(self):
        """Sort tree by counter-resistance against opponent strategies"""
        self.current_sort_mode = "resistance"
        self.active_sort_mode = "resistance"
        self.apply_combined_sort(compute_primary_tags=True)
        self.update_sort_value_column()
        self.update_column_headers()
        self.is_sorted = True
        self.update_sort_button_states()
        self._update_sort_hint()

    def sort_by_cumulative(self):
        """Sort tree by cumulative value"""
        self.current_sort_mode = "cumulative"
        self.active_sort_mode = "cumulative"
        self.apply_combined_sort(compute_primary_tags=True)
        self.update_sort_value_column()
        self.update_column_headers()
        self.is_sorted = True
        self.update_sort_button_states()
        self._update_sort_hint()

    def sort_by_strategic(self):
        """Sort tree by unified strategic score using enhanced metric foundations."""
        with self.perf.span("strategic.sort.end_to_end"):
            self.current_sort_mode = "strategic3"
            self.active_sort_mode = "strategic3"

            with self.perf.span("strategic.sort.apply_combined"):
                self.apply_combined_sort(compute_primary_tags=True)

            memo_stats = self.tree_generator.get_memoization_stats()
            if self.perf.enabled:
                self._log_perf_entry(
                    "strategic.memo.stats",
                    0.0,
                    hits=memo_stats["hits"],
                    misses=memo_stats["misses"],
                    hit_rate=f"{memo_stats['hit_rate']:.2%}",
                    entries=memo_stats["entries"],
                )

            with self.perf.span("strategic.sort.update_sort_value_column"):
                self.update_sort_value_column()
            with self.perf.span("strategic.sort.update_column_headers"):
                self.update_column_headers()

            self.is_sorted = True
            with self.perf.span("strategic.sort.update_sort_button_states"):
                self.update_sort_button_states()
            with self.perf.span("strategic.sort.update_sort_hint"):
                self._update_sort_hint()
    
    def unsort_tree(self):
        """Remove all sorting and return to default order"""
        self.current_sort_mode = "none"
        self.active_sort_mode = None
        self.update_sort_value_column()
        self.update_column_headers()
        self.apply_combined_sort(compute_primary_tags=False)
        self.is_sorted = self.active_column_sort is not None
        self.update_sort_button_states()
        self._update_sort_hint()
    
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

    def toggle_strategic_sort(self):
        """Toggle unified strategic sorting on/off"""
        if self.active_sort_mode == "strategic3":
            self.unsort_tree()
        else:
            self.sort_by_strategic()
    
    def update_sort_button_states(self):
        """Update button appearance to show active/inactive states"""
        # Reset all buttons to inactive state (dim red circle)
        self.cumulative_button.config(text="Cumulative\nSort", relief=tk.RAISED, bg='SystemButtonFace')
        self.confidence_button.config(text="Highest\nConfidence", relief=tk.RAISED, bg='SystemButtonFace')
        self.counter_button.config(text="Counter\nPick", relief=tk.RAISED, bg='SystemButtonFace')
        self.strategic_button.config(text="Strategic\nFusion", relief=tk.RAISED, bg='SystemButtonFace')
        
        # Set active button to bright red circle and pressed appearance
        if self.active_sort_mode == "cumulative":
            self.cumulative_button.config(text="Cumulative\nSort", relief=tk.SUNKEN, bg='lightcoral')
        elif self.active_sort_mode == "confidence":
            self.confidence_button.config(text="Highest\nConfidence", relief=tk.SUNKEN, bg='lightcoral')
        elif self.active_sort_mode == "resistance":
            self.counter_button.config(text="Counter\nPick", relief=tk.SUNKEN, bg='lightcoral')
        elif self.active_sort_mode == "strategic3":
            self.strategic_button.config(text="Strategic\nFusion", relief=tk.SUNKEN, bg='lightcoral')

    def on_column_click(self, column_id):
        """Cycle sort state for a column and apply combined sorting."""
        current_state = self.column_sort_states.get(column_id, "none")

        if current_state == "none":
            new_state = "desc"
        elif current_state == "desc":
            new_state = "asc"
        else:
            new_state = "none"

        for col in self.column_sort_states:
            self.column_sort_states[col] = "none"

        self.column_sort_states[column_id] = new_state
        self.active_column_sort = column_id if new_state != "none" else None

        recompute_primary = self._should_recompute_primary_on_column_click()
        self.apply_combined_sort(compute_primary_tags=recompute_primary)
        self.update_sort_value_column()
        self.update_column_headers()

    def _get_sort_value_header_base(self):
        if self.current_sort_mode == "confidence":
            return "Confidence Score"
        if self.current_sort_mode == "resistance":
            return "Resistance Score"
        if self.current_sort_mode == "cumulative":
            return "Cumulative Value"
        if self.current_sort_mode == "strategic3":
            return "Strategic Score"
        return "Sort Value"

    def update_column_headers(self):
        base_names = {
            "#0": "Pairing",
            "Rating": "Rating",
            "Sort Value": self._get_sort_value_header_base(),
        }

        for column_id in ["#0", "Rating", "Sort Value"]:
            state = self.column_sort_states.get(column_id, "none")
            suffix = ""
            if state == "asc":
                suffix = " ^"
            elif state == "desc":
                suffix = " v"
            self.treeview.tree.heading(column_id, text=f"{base_names[column_id]}{suffix}")

    def apply_combined_sort(self, compute_primary_tags=True):
        """Apply advanced sort as primary and column sort as secondary per sibling set."""
        primary_mode = self.active_sort_mode
        secondary_column = self.active_column_sort

        with self.perf.span(
            "sort.apply_combined.total",
            primary=(primary_mode or "none"),
            secondary=(secondary_column or "none"),
            compute_primary=int(bool(compute_primary_tags)),
        ):
            if not primary_mode and not secondary_column:
                with self.perf.span("sort.apply_combined.unsort_tree"):
                    self.tree_generator.unsort_tree()
                return

            if compute_primary_tags and primary_mode:
                self._set_tree_memo_state_token()
                recomputed_any = False

                def run_metric(metric_key, span_label, compute_func):
                    nonlocal recomputed_any
                    if not self._is_metric_stale(metric_key):
                        return False
                    with self.perf.span(span_label):
                        compute_func("")
                    self._mark_metric_fresh(metric_key)
                    recomputed_any = True
                    return True

                if primary_mode == "cumulative":
                    run_metric("cumulative", "sort.compute.cumulative2", self.tree_generator.calculate_all_path_values_enhanced)
                elif primary_mode == "confidence":
                    run_metric("confidence", "sort.compute.confidence2", self.tree_generator.calculate_confidence_scores_enhanced)
                elif primary_mode == "resistance":
                    run_metric("resistance", "sort.compute.resistance2", self.tree_generator.calculate_counter_resistance_scores_enhanced)
                elif primary_mode == "strategic3":
                    recomputed_c2 = run_metric(
                        "cumulative",
                        "sort.compute.strategic3.cumulative2",
                        self.tree_generator.calculate_all_path_values_enhanced,
                    )
                    recomputed_q2 = run_metric(
                        "confidence",
                        "sort.compute.strategic3.confidence2",
                        self.tree_generator.calculate_confidence_scores_enhanced,
                    )
                    recomputed_r2 = run_metric(
                        "resistance",
                        "sort.compute.strategic3.resistance2",
                        self.tree_generator.calculate_counter_resistance_scores_enhanced,
                    )

                    if self._is_metric_stale("strategic3") or recomputed_c2 or recomputed_q2 or recomputed_r2:
                        with self.perf.span("sort.compute.strategic3.final"):
                            self.tree_generator.calculate_strategic3_scores("")
                        self._mark_metric_fresh("strategic3")
                        recomputed_any = True

                self._last_primary_metrics_signature = self._build_primary_metrics_signature(primary_mode)
                self._primary_metrics_dirty = False
                self._mark_explainability_metrics_available(primary_mode)

            recurse_mode = "expanded" if getattr(self, "lazy_sort_on_expand", False) else "all"
            self._sort_children_combined("", primary_mode, secondary_column, recurse_mode=recurse_mode)

    def _sort_children_combined(self, node, primary_mode, secondary_column, _profile=None, _depth=0, recurse_mode="all"):
        profile_owner = _profile is None
        perf_enabled = bool(getattr(getattr(self, 'perf', None), 'enabled', False))
        if profile_owner and perf_enabled and primary_mode:
            _profile = {
                "mode": primary_mode,
                "nodes": 0,
                "sibling_total": 0,
                "max_siblings": 0,
                "max_depth": 0,
                "leaf_calls": 0,
                "text_sort_ms": 0.0,
                "tie_break_ms": 0.0,
                "secondary_ms": 0.0,
                "primary_ms": 0.0,
                "reorder_ms": 0.0,
                "recurse_ms": 0.0,
                "cache_hit_nodes": 0,
                "cache_miss_nodes": 0,
                "start": time.perf_counter(),
            }

        children = self.treeview.tree.get_children(node)
        if not children:
            if _profile is not None:
                _profile["leaf_calls"] += 1
            return

        if _profile is not None:
            _profile["nodes"] += 1
            _profile["sibling_total"] += len(children)
            _profile["max_siblings"] = max(_profile["max_siblings"], len(children))
            _profile["max_depth"] = max(_profile["max_depth"], _depth)

        secondary_state = "none"
        if secondary_column:
            secondary_state = self.column_sort_states.get(secondary_column, "none")
        secondary_reverse = secondary_state == "desc"

        primary_reverse = False
        if primary_mode:
            # Choice ownership for sibling ordering belongs to the current decision node.
            # For root sorting and the synthetic "Pairings" node, depth-1 children
            # represent the first real decision owner.
            decision_node = node
            if not decision_node:
                decision_node = children[0]
            else:
                node_text = (self.treeview.tree.item(decision_node, 'text') or "").strip().lower()
                if node_text == "pairings":
                    decision_node = children[0]
            primary_reverse = not self.tree_generator._is_opponent_choice_level(decision_node)

        def primary_key(child_id):
            if primary_mode == "cumulative":
                return self.tree_generator.get_cumulative2_from_tags(child_id)
            if primary_mode == "confidence":
                return self.tree_generator.get_confidence2_from_tags(child_id)
            if primary_mode == "resistance":
                return self.tree_generator.get_resistance2_from_tags(child_id)
            if primary_mode == "strategic3":
                return self.tree_generator.get_strategic3_from_tags(child_id)
            return 0

        def secondary_key(child_id):
            if not secondary_column:
                return 0
            if secondary_column == "#0":
                return (self.treeview.tree.item(child_id, 'text') or "").lower()
            values = self.treeview.tree.item(child_id, 'values') or []
            idx = 0 if secondary_column == "Rating" else 1
            try:
                return int(values[idx])
            except (ValueError, IndexError, TypeError):
                return 0

        def metric_value(child_id, metric):
            if metric == "cumulative":
                return self.tree_generator.get_cumulative2_from_tags(child_id)
            if metric == "confidence":
                return self.tree_generator.get_confidence2_from_tags(child_id)
            if metric == "resistance":
                return self.tree_generator.get_resistance2_from_tags(child_id)
            if metric == "regret":
                # Lower regret is better; invert so higher key value remains better.
                return -self.tree_generator.get_regret2_from_tags(child_id)
            if metric == "strategic3":
                return self.tree_generator.get_strategic3_from_tags(child_id)
            if metric == "strategic_exploit":
                # Lower exploitability is better; invert so higher key value remains better.
                return -self.tree_generator.get_strategic3_exploitability_from_tags(child_id)
            if metric == "rating":
                values = self.treeview.tree.item(child_id, 'values') or []
                try:
                    return int(values[0])
                except (ValueError, IndexError, TypeError):
                    return 0
            return 0

        def resolve_tie_break_chain():
            mode_defaults = {
                "confidence": ["regret", "cumulative", "resistance"],
                "cumulative": ["confidence", "resistance"],
                "resistance": ["confidence", "cumulative"],
                "strategic3": ["strategic_exploit", "confidence", "cumulative"],
            }

            if primary_mode in mode_defaults:
                configured = mode_defaults[primary_mode]
            else:
                configured = {
                    "confidence_then_cumulative": ["confidence", "cumulative", "resistance"],
                    "cumulative_then_confidence": ["cumulative", "confidence", "resistance"],
                    "resistance_then_confidence": ["resistance", "confidence", "cumulative"],
                }.get(self.tie_break_order, ["confidence", "cumulative", "resistance"])

            # Prevent duplicate sort dimensions when primary/secondary are already active.
            excluded = set()
            if primary_mode:
                excluded.add(primary_mode)
            if secondary_column == "Rating":
                excluded.add("rating")

            return [metric for metric in configured if metric not in excluded]

        child_set_key = tuple(sorted(children))
        tie_break_order = getattr(self, 'tie_break_order', 'confidence_then_cumulative')
        current_sort_mode = getattr(self, 'current_sort_mode', 'none')
        primary_signature = getattr(self, '_last_primary_metrics_signature', None)
        sort_context_key = (
            primary_mode or "none",
            secondary_column or "none",
            secondary_state,
            bool(primary_reverse),
            tie_break_order,
            primary_signature,
        )
        cache_key = (node, child_set_key, sort_context_key)
        sort_cache = getattr(self, '_sorted_children_cache', None)
        if sort_cache is None:
            sort_cache = {}
            setattr(self, '_sorted_children_cache', sort_cache)
        cached_order = sort_cache.get(cache_key)

        if cached_order is not None:
            children_sorted = list(cached_order)
            if _profile is not None:
                _profile["cache_hit_nodes"] += 1
        else:
            if _profile is not None:
                _profile["cache_miss_nodes"] += 1
            children_sorted = list(children)

            # Final deterministic fallback for equal numeric metrics.
            section_start = time.perf_counter()
            children_sorted.sort(key=lambda child_id: (self.treeview.tree.item(child_id, 'text') or "").lower())
            if _profile is not None:
                _profile["text_sort_ms"] += (time.perf_counter() - section_start) * 1000.0

            # Deterministic tie-break chain obeys same decision-owner direction as primary mode.
            if primary_mode:
                section_start = time.perf_counter()
                for tie_metric in reversed(resolve_tie_break_chain()):
                    children_sorted.sort(key=lambda child_id, m=tie_metric: metric_value(child_id, m), reverse=primary_reverse)
                if _profile is not None:
                    _profile["tie_break_ms"] += (time.perf_counter() - section_start) * 1000.0

            if secondary_column and secondary_state != "none":
                section_start = time.perf_counter()
                children_sorted.sort(key=secondary_key, reverse=secondary_reverse)
                if _profile is not None:
                    _profile["secondary_ms"] += (time.perf_counter() - section_start) * 1000.0

            if primary_mode:
                section_start = time.perf_counter()
                children_sorted.sort(key=primary_key, reverse=primary_reverse)
                if _profile is not None:
                    _profile["primary_ms"] += (time.perf_counter() - section_start) * 1000.0

            sort_cache[cache_key] = tuple(children_sorted)

        section_start = time.perf_counter()
        for child in children_sorted:
            self.treeview.tree.detach(child)
        for child in children_sorted:
            self.treeview.tree.move(child, node, 'end')
        if _profile is not None:
            _profile["reorder_ms"] += (time.perf_counter() - section_start) * 1000.0

        section_start = time.perf_counter()
        for child in children_sorted:
            should_recurse = recurse_mode == "all"
            if recurse_mode == "expanded":
                try:
                    should_recurse = bool(self.treeview.tree.item(child, "open"))
                except Exception:
                    should_recurse = False
            if not should_recurse:
                continue
            self._sort_children_combined(
                child,
                primary_mode,
                secondary_column,
                _profile=_profile,
                _depth=_depth + 1,
                recurse_mode=recurse_mode,
            )
        if _profile is not None:
            _profile["recurse_ms"] += (time.perf_counter() - section_start) * 1000.0

        if profile_owner and _profile is not None:
            total_ms = (time.perf_counter() - _profile["start"]) * 1000.0
            nodes = int(_profile["nodes"]) if _profile["nodes"] else 0
            avg_siblings = (_profile["sibling_total"] / nodes) if nodes else 0.0
            self._log_perf_entry(
                "sort.children.profile",
                total_ms,
                mode=_profile["mode"],
                nodes=nodes,
                cache_hits=int(_profile["cache_hit_nodes"]),
                cache_misses=int(_profile["cache_miss_nodes"]),
                leaf_calls=int(_profile["leaf_calls"]),
                max_depth=int(_profile["max_depth"]),
                avg_siblings=f"{avg_siblings:.2f}",
                max_siblings=int(_profile["max_siblings"]),
                text_ms=f"{_profile['text_sort_ms']:.2f}",
                tie_ms=f"{_profile['tie_break_ms']:.2f}",
                secondary_ms=f"{_profile['secondary_ms']:.2f}",
                primary_ms=f"{_profile['primary_ms']:.2f}",
                reorder_ms=f"{_profile['reorder_ms']:.2f}",
                recurse_ms=f"{_profile['recurse_ms']:.2f}",
            )

    def update_scenario_box(self):
        scenarios = []
        if self.scenario_map:
            for scenario in self.scenario_map.values():
                # if self.print_output:print(scenario)
                scenarios.append(scenario)
            self.scenario_box['values'] = scenarios
        else:
            self.scenario_box['values'] = ("1 - Recon","2 - Battle Lines","3 - Wolves At Our Heels","4 - Payload","5 - Two Fronts","6 - Invasion")

    def _on_team_box_change_traced(self, *args):
        start_time = time.perf_counter()
        with self.perf.span("team_dropdown.trace"):
            self.on_team_box_change(*args)
        self._record_event_loop_lag("team_dropdown.trace", start_time)

    def _on_scenario_box_change_traced(self, *args):
        start_time = time.perf_counter()
        with self.perf.span("scenario_dropdown.trace"):
            self.on_scenario_box_change(*args)
        self._record_event_loop_lag("scenario_dropdown.trace", start_time)

    def on_scenario_box_change(self, *args):
        # Get the new value
        new_value = self.scenario_var.get()
        # Compare with the previous value
        if new_value != self.previous_value:
            # print(f"Scenario changed from {self.previous_value} to {new_value}\nLOADING NEW SCENARIO DATA\n")
            self.previous_value = new_value
            try:
                span_label = "scenario.change.auto" if self._scenario_change_auto else "scenario.change.end_to_end"
                with self.perf.span(span_label):
                    self._invalidate_comment_cache()
                    self._apply_scenario_change_updates()
                    self._measure_update_idletasks("scenario.change.redraw")
            except (ValueError, IndexError) as e:
                print(f"scenario_box_change error: {e}")
            finally:
                self._scenario_change_auto = False

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
                with self.perf.span("teams.change.end_to_end"):
                    self._invalidate_comment_cache()
                    if not new_team1_value.strip() or not new_team2_value.strip():
                        self._schedule_scenario_calculations(immediate=True)
                        self._measure_update_idletasks("teams.change.redraw")
                        return
                    self._apply_team_change_updates()
                    self._measure_update_idletasks("teams.change.redraw")
            except (ValueError,IndexError) as e:
                print(f"team_box_change error: {e}")
            
    

    ####################
    # DB Fill/Save Funcs
    ####################

    def update_ui(self):
        # Update the team dropdowns and grid values
        with self.perf.span("ui.update_ui.set_team_dropdowns"):
            self.set_team_dropdowns()
        with self.perf.span("ui.update_ui.load_grid"):
            self.load_grid_data_from_db()
        # print(self.extract_ratings())

    def _apply_team_change_updates(self):
        if self._team_change_in_progress:
            return

        self._team_change_in_progress = True
        try:
            self._invalidate_tree_cache("team_change")
            with self.perf.span("teams.change.load_grid"):
                self.load_grid_data_from_db(refresh_ui=True)
        finally:
            self._team_change_in_progress = False

    def _apply_scenario_change_updates(self):
        self._invalidate_tree_cache("scenario_change")
        with self.perf.span("scenario.change.load_grid"):
            self.load_grid_data_from_db(refresh_ui=True)

    def _post_grid_load_refresh(self):
        self._invalidate_comment_cache()
        self.update_comment_indicators()
        self._schedule_scenario_calculations(immediate=True)
        self._set_grid_dirty(False)
        if self.tree_autogen_enabled:
            self._schedule_tree_autogenerate()

    def _invalidate_team_cache(self, team_name: Optional[str] = None):
        if team_name:
            self._team_cache.pop(team_name, None)
            return
        self._team_cache.clear()

    def _invalidate_comment_cache(self):
        self._comment_cache.clear()

    def _get_team_data(self, team_name: str) -> Optional[Dict[str, Any]]:
        if not team_name:
            return None

        cached = self._team_cache.get(team_name)
        if cached:
            return cached

        team_id_result = self.db_manager.query_sql(
            f"SELECT team_id FROM teams WHERE team_name = '{team_name}'"
        )
        if not team_id_result:
            print(f"Team '{team_name}' not found in database")
            return None

        team_id = team_id_result[0][0]
        player_results = self.db_manager.query_sql(
            f"SELECT player_id, player_name FROM players WHERE team_id = {team_id} ORDER BY player_id"
        )

        players = [{'id': row[0], 'name': row[1]} for row in player_results]
        data = {'team_id': team_id, 'players': players}
        self._team_cache[team_name] = data
        return data

    def _get_comment_map_for_current_selection(self) -> Dict[tuple, str]:
        team1_name = self.team1_var.get().strip() if hasattr(self, 'team1_var') else ''
        team2_name = self.team2_var.get().strip() if hasattr(self, 'team2_var') else ''
        scenario_id = self.get_scenario_num() if hasattr(self, 'scenario_box') else 0

        if not team1_name or not team2_name:
            return {}

        cache_key = (team1_name, team2_name, scenario_id)
        cached = self._comment_cache.get(cache_key)
        if cached is not None:
            return cached

        team1_data = self._get_team_data(team1_name)
        team2_data = self._get_team_data(team2_name)
        if not team1_data or not team2_data:
            return {}

        comments = self.db_manager.query_all_comments(
            team1_data['team_id'],
            team2_data['team_id'],
            scenario_id
        )
        self._comment_cache[cache_key] = comments or {}
        return self._comment_cache[cache_key]

    def _has_comment_cached(self, row: int, col: int, comment_map: Optional[Dict[tuple, str]] = None) -> bool:
        friendly_player = self.grid_data_model.get_rating(row, 0)
        opponent_player = self.grid_data_model.get_rating(0, col)
        if not friendly_player or not opponent_player:
            return False

        if comment_map is None:
            comment_map = self._get_comment_map_for_current_selection()
        return (friendly_player, opponent_player) in comment_map

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

        if not self._team_dropdowns_initialized:
            self._team_dropdowns_initialized = True
        
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
        
        if is_debugging and not self._auto_populated_teams:
            print("DEBUG: Debugger detected - auto-populating teams")
            if len(team_names) >= 2 and not self.combobox_1.get() and not self.combobox_2.get():
                self.combobox_1.set(team_names[0])
                self.combobox_2.set(team_names[1])
                print(f"DEBUG: Set Team 1: {team_names[0]}, Team 2: {team_names[1]}")
                # Trigger data load after setting teams (100ms delay ensures UI is ready)
                self.root.after(100, self.load_grid_data_from_db)
                self._auto_populated_teams = True
            else:
                print("DEBUG: Not enough teams in database to auto-populate")
        else:
            print("DEBUG: No debugger detected - skipping auto-population")

    def load_grid_data_from_db(self, refresh_ui: bool = True):
        self._start_grid_load(refresh_ui=refresh_ui)

    def _start_grid_load(self, refresh_ui: bool = True):
        team_1 = self.combobox_1.get().strip()
        team_2 = self.combobox_2.get().strip()

        # Guard: Don't try to load data if teams are not selected
        if not team_1 or not team_2:
            return

        scenario = self.scenario_box.get()[:1]
        if scenario == '':
            self._scenario_change_auto = True
            self.scenario_box.set("0 - Neutral")
            scenario = self.scenario_box.get()[:1]
        scenario_id = int(scenario)

        if self._background_load_enabled and hasattr(self, 'root'):
            self._grid_load_generation += 1
            generation = self._grid_load_generation
            self._grid_load_in_flight = True
            worker = threading.Thread(
                target=self._background_grid_load_worker,
                args=(generation, team_1, team_2, scenario_id, refresh_ui),
                daemon=True
            )
            worker.start()
            return

        snapshot = self._fetch_grid_snapshot(team_1, team_2, scenario_id)
        if snapshot is None:
            return
        self._apply_grid_snapshot(snapshot, refresh_ui)

    def _background_grid_load_worker(self, generation: int, team_1: str, team_2: str, scenario_id: int, refresh_ui: bool):
        snapshot = self._fetch_grid_snapshot(team_1, team_2, scenario_id)

        def apply_snapshot():
            if generation != self._grid_load_generation:
                return
            self._grid_load_in_flight = False
            if snapshot is None:
                return
            self._apply_grid_snapshot(snapshot, refresh_ui)

        if hasattr(self, 'root'):
            self.root.after(0, apply_snapshot)

    def _fetch_grid_snapshot(self, team_1: str, team_2: str, scenario_id: int) -> Optional[Dict[str, Any]]:
        team_1_data = self._fetch_team_data_for_load(team_1)
        team_2_data = self._fetch_team_data_for_load(team_2)
        if not team_1_data or not team_2_data:
            return None

        team_1_id = team_1_data['team_id']
        team_2_id = team_2_data['team_id']
        team_1_dict = {row['id']: {'position': i + 1, 'name': row['name']} for i, row in enumerate(team_1_data['players'])}
        team_2_dict = {row['id']: {'position': i + 1, 'name': row['name']} for i, row in enumerate(team_2_data['players'])}

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
        return {
            'team_1_dict': team_1_dict,
            'team_2_dict': team_2_dict,
            'ratings_rows': ratings_rows
        }

    def _fetch_team_data_for_load(self, team_name: str) -> Optional[Dict[str, Any]]:
        if not team_name:
            return None

        team_id_result = self.db_manager.query_sql(
            f"SELECT team_id FROM teams WHERE team_name = '{team_name}'"
        )
        if not team_id_result:
            print(f"Team '{team_name}' not found in database")
            return None

        team_id = team_id_result[0][0]
        player_results = self.db_manager.query_sql(
            f"SELECT player_id, player_name FROM players WHERE team_id = {team_id} ORDER BY player_id"
        )

        players = [{'id': row[0], 'name': row[1]} for row in player_results]
        return {'team_id': team_id, 'players': players}

    def _apply_grid_snapshot(self, snapshot: Dict[str, Any], refresh_ui: bool = True):
        team_1_dict = snapshot['team_1_dict']
        team_2_dict = snapshot['team_2_dict']
        ratings_rows = snapshot['ratings_rows']

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
        for row in ratings_rows:
            team_1_pos = team_1_dict[row[0]]['position']
            team_2_pos = team_2_dict[row[1]]['position']
            if 0 <= team_1_pos < 6 and 0 <= team_2_pos < 6:
                # Store as integer for efficient calculations
                self.grid_data_model.set_rating(team_1_pos, team_2_pos, int(row[2]), notify=False)

        # End batch mode - this triggers single batch notification
        self.grid_data_model.end_batch()

        # Refresh UI from model after batch load
        self.grid_data_model._notify_observers('grid_loaded')

        if refresh_ui:
            self._post_grid_load_refresh()
        
    def auto_generate_tree_after_teams_loaded(self):
        """
        Automatically generate the matchup tree after both teams are loaded.
        This prevents first-interaction lag by pre-generating the tree structure.
        Only generates if tree doesn't already exist.
        """
        try:
            if not self.tree_autogen_enabled:
                return
            self._tree_autogen_job = None
            # Check if tree already exists
            root_nodes = self.treeview.tree.get_children()
            if root_nodes and len(root_nodes) > 0:
                # Tree already exists, don't regenerate
                return
            
            # Generate the tree silently in the background
            with self.perf.span("tree.auto_generate"):
                self.on_generate_combinations()
            print("Auto-generated matchup tree after teams loaded")
            
        except Exception as e:
            # Don't block UI if generation fails
            print(f"Warning: Auto-generation of tree failed: {e}")
        
    def save_grid_data_to_db(self):
        with self.perf.span("grid.save_to_db"):
            self._save_grid_data_to_db()

    def _save_grid_data_to_db(self):
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

            self._set_grid_dirty(False)

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
                                  f"Players updated:\n" + "\n".join([f"ΓÇó {name}" for name in player_names]))
            else:
                # Create new team
                team_id = self.db_manager.upsert_team(team_name)
                
                # Create players
                for player_name in player_names:
                    self.db_manager.create_player(player_name, team_id)
                    
                messagebox.showinfo("Success", 
                                  f"Team '{team_name}' has been created successfully!\n\n"
                                  f"Players added:\n" + "\n".join([f"ΓÇó {name}" for name in player_names]))

            # Update UI like successful CSV import
            self._invalidate_team_cache()
            self._invalidate_comment_cache()
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
            self._invalidate_team_cache()
            self._invalidate_comment_cache()
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
            self._invalidate_team_cache()
            self._invalidate_comment_cache()
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
        self._invalidate_team_cache()
        self._invalidate_comment_cache()
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
            comment_map = self._get_comment_map_for_current_selection()
            friendly_player = self.grid_data_model.get_rating(row, 0)
            opponent_player = self.grid_data_model.get_rating(0, col)
            if not all([friendly_player, opponent_player]):
                return False
            return (friendly_player, opponent_player) in comment_map
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

        comment_map = self._get_comment_map_for_current_selection()
        if not comment_map:
            return

        for row in range(1, 6):
            friendly_player = self.grid_data_model.get_rating(row, 0)
            if not friendly_player:
                continue
            for col in range(1, 6):
                opponent_player = self.grid_data_model.get_rating(0, col)
                if not opponent_player:
                    continue
                if (friendly_player, opponent_player) in comment_map:
                    self.add_comment_indicator(row, col)

    def add_comment_indicator(self, row, col):
        """Add a small corner indicator for comments"""
        try:
            # Create a small red arrowhead (downward triangle) for visibility.
            indicator = tk.Canvas(
                self.grid_frame,
                width=9,
                height=9,
                highlightthickness=0,
                borderwidth=0,
                relief=tk.FLAT
            )
            indicator.create_polygon(
                1, 1,
                8, 1,
                4, 8,
                fill="#D32F2F",
                outline="white"
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
                # Match the cell background to reduce visual seams.
                try:
                    indicator.configure(bg=widget.cget('bg'))
                except Exception:
                    pass
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
        """Show tooltip with comment text when hovering over a matchup cell."""
        try:
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()

            friendly_player = self.grid_data_model.get_rating(row, 0)
            opponent_player = self.grid_data_model.get_rating(0, col)

            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                return

            comment = self.db_manager.query_comment_by_name(
                team1_name, team2_name, scenario_name,
                friendly_player, opponent_player
            )

            if comment:
                self.comment_tooltip = tk.Toplevel(self.root)
                self.comment_tooltip.wm_overrideredirect(True)

                x = event.x_root + 10
                y = event.y_root + 10
                self.comment_tooltip.wm_geometry(f"+{x}+{y}")

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

    def _find_grid_cell_at_cursor(self, event):
        """Return (row, col) for matchup cell under cursor, or None."""
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if not widget:
            return None

        for r in range(1, 6):
            for c in range(1, 6):
                if self.grid_widgets[r][c] == widget:
                    return (r, c)

        return None

    def _on_grid_motion(self, event):
        """Handle hover movement to show/hide comment tooltips."""
        cell = self._find_grid_cell_at_cursor(event)
        if cell != self._current_hover_cell:
            self.hide_comment_tooltip()
            self._current_hover_cell = cell
            if cell:
                row, col = cell
                self.show_comment_tooltip(event, row, col)

    def _on_grid_leave(self, event):
        """Hide comment tooltip when leaving the grid area."""
        self.hide_comment_tooltip()
        self._current_hover_cell = None

    def hide_comment_tooltip(self, event=None):
        """Hide the comment tooltip."""
        if hasattr(self, 'comment_tooltip') and self.comment_tooltip:
            self.comment_tooltip.destroy()
            self.comment_tooltip = None

    def open_comment_editor(self, event, row, col):
        """Open a dialog to edit/add comments for a specific matchup."""
        try:
            if self._comment_editor_open:
                return

            self._hide_all_popups()
            team1_name = self.team1_var.get()
            team2_name = self.team2_var.get()
            scenario_name = self.scenario_var.get()

            friendly_player = self.grid_data_model.get_rating(row, 0)
            opponent_player = self.grid_data_model.get_rating(0, col)

            if not all([team1_name, team2_name, scenario_name, friendly_player, opponent_player]):
                messagebox.showwarning(
                    "Missing Information",
                    "Please select teams, scenario, and ensure player names are filled in."
                )
                return

            existing_comment = self.db_manager.query_comment_by_name(
                team1_name, team2_name, scenario_name,
                friendly_player, opponent_player
            ) or ""

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
        self._comment_editor_open = True
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

        def close_dialog():
            self._comment_editor_open = False
            dialog.destroy()
        
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
                    self._invalidate_comment_cache()
                    self.update_comment_indicators()
                    self.update_grid_colors()
                else:
                    # Delete comment if empty
                    self.db_manager.delete_comment_by_name(
                        team1_name, team2_name, scenario_name,
                        friendly_player, opponent_player
                    )
                    messagebox.showinfo("Success", "Comment deleted successfully!")
                    self._invalidate_comment_cache()
                    self.update_comment_indicators()
                    self.update_grid_colors()

                close_dialog()
                
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
                    self._invalidate_comment_cache()
                    self.update_comment_indicators()
                    self.update_grid_colors()
                    close_dialog()
                except Exception as e:
                    print(f"Error deleting comment: {e}")
                    messagebox.showerror("Error", f"Failed to delete comment: {e}")
        
        # Buttons
        tk.Button(button_frame, text="Save", command=save_comment, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Delete", command=delete_comment, bg="lightcoral").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=close_dialog).pack(side=tk.RIGHT, padx=5)
        
        # Focus on text area
        comment_text.focus_set()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

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
            return self.tree_generator.get_confidence2_from_tags(node)
        elif self.current_sort_mode == "resistance":
            return self.tree_generator.get_resistance2_from_tags(node)
        elif self.current_sort_mode == "cumulative":
            return self.tree_generator.get_cumulative2_from_tags(node)
        elif self.current_sort_mode == "strategic3":
            return self.tree_generator.get_strategic3_from_tags(node)
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
                
                # 2. Flip ratings around 3 (1Γåö5, 2Γåö4, 3 stays 3)
                for row in range(1, 6):
                    for col in range(1, 6):
                        current_value = self.grid_data_model.get_rating(row, col)
                        if isinstance(current_value, int):
                            # Flip around 3: new_rating = 6 - old_rating
                            flipped_rating = 6 - current_value
                            self.grid_data_model.set_rating(row, col, flipped_rating, notify=False)
                
                self.grid_data_model.end_batch()
                # Batch mutation used notify=False for performance; emit one refresh event.
                self.grid_data_model._notify_observers('grid_loaded')
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

    def _update_sort_hint(self):
        if not hasattr(self, 'sort_guidance_label'):
            return
        hint_map = {
            None: "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            "none": "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            "cumulative": "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            "confidence": "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            "resistance": "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax",
            "strategic3": "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax"
        }
        hint = hint_map.get(self.active_sort_mode, "Sort guidance:\nCumulative: steady paths\nConfidence: low-variance wins\nCounter: resilient picks\nStrategic: balanced minimax")
        self.sort_guidance_label.config(text=hint)

    def _load_pairing_notes(self):
        if self.notes_text is None:
            return
        self.notes_text.delete("1.0", tk.END)
        if self.pairing_plan_notes:
            self.notes_text.insert("1.0", self.pairing_plan_notes)

    def _save_pairing_notes(self):
        if self.notes_text is None:
            return
        notes = self.notes_text.get("1.0", tk.END).rstrip()
        max_chars = 4096
        if len(notes) > max_chars:
            notes = notes[:max_chars]
            self.notes_text.delete("1.0", tk.END)
            self.notes_text.insert("1.0", notes)
        self.pairing_plan_notes = notes
        self.db_preferences.set_pairing_plan_notes(notes)

    def _clear_pairing_notes(self):
        if self.notes_text is None:
            return
        self.notes_text.delete("1.0", tk.END)
        self.pairing_plan_notes = ""
        self.db_preferences.set_pairing_plan_notes("")

    def create_matchup_output_panel(self, parent: Optional[tk.Frame] = None):
        """Create a panel to display the final 5 matchups in a simple format."""
        try:
            target_parent = parent if parent is not None else self.matchup_output_container
            # Create output panel frame below the tree section
            self.output_panel_frame = tk.Frame(target_parent, relief=tk.RIDGE, borderwidth=2, bg="lightyellow")
            self.output_panel_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=5, pady=5, expand=True)
            
            # Panel title
            title_label = tk.Label(self.output_panel_frame, text="Final Matchups Output", 
                                 font=("Arial", 12, "bold"), bg="lightyellow")
            title_label.pack(pady=(5, 0))

            summary_frame = tk.Frame(self.output_panel_frame, bg="lightyellow")
            summary_frame.pack(fill=tk.X, padx=10, pady=(2, 6))

            self.summary_matchups_label = tk.Label(
                summary_frame,
                text="Final matchups: Not extracted yet",
                font=("Arial", 9),
                bg="lightyellow",
                fg="#333333",
                justify=tk.LEFT,
                anchor=tk.W,
                wraplength=360
            )
            self.summary_matchups_label.pack(fill=tk.X)

            self.summary_spread_label = tk.Label(
                summary_frame,
                text="Best/Worst spread: --",
                font=("Arial", 9),
                bg="lightyellow",
                fg="#333333",
                justify=tk.LEFT,
                anchor=tk.W
            )
            self.summary_spread_label.pack(fill=tk.X)

            self.summary_explain_label = tk.Label(
                summary_frame,
                text="Explainability: select a tree node to view C2/Q2/R2 and strategic factors.",
                font=("Arial", 8),
                bg="lightyellow",
                fg="#333333",
                justify=tk.LEFT,
                anchor=tk.W,
                wraplength=360
            )
            self.summary_explain_label.pack(fill=tk.X, pady=(2, 0))

            self.summary_histogram = tk.Canvas(
                summary_frame,
                height=60,
                bg="white",
                relief=tk.SUNKEN,
                borderwidth=1
            )
            self.summary_histogram.pack(fill=tk.X, pady=(4, 0))
            
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

    def _update_matchup_summary(self, matchups: List[Dict[str, Any]]):
        if not hasattr(self, 'summary_matchups_label'):
            return

        if not matchups:
            self.summary_matchups_label.config(text="Final matchups: Not extracted yet")
            self.summary_spread_label.config(text="Best/Worst spread: --")
            self._render_confidence_histogram([])
            return

        matchup_lines = []
        ratings = []
        for matchup in matchups:
            decision = matchup.get('decision') or matchup.get('choice') or ""
            if decision:
                matchup_lines.append(decision)
            rating_value = self._parse_rating_value(matchup.get('rating'))
            if rating_value is not None:
                ratings.append(rating_value)

        summary_text = "Final matchups: " + ("; ".join(matchup_lines) if matchup_lines else "(unavailable)")
        self.summary_matchups_label.config(text=summary_text)

        if ratings:
            best = max(ratings)
            worst = min(ratings)
            avg = sum(ratings) / len(ratings)
            self.summary_spread_label.config(
                text=f"Best/Worst spread: {best:.2f} / {worst:.2f} (avg {avg:.2f})"
            )
        else:
            self.summary_spread_label.config(text="Best/Worst spread: --")

        self._render_confidence_histogram(ratings)

        selected_item = self.treeview.tree.selection() if hasattr(self, 'treeview') else []
        self._update_explainability_card(selected_item[0] if selected_item else None)

    def _get_tag_value(self, node_id: Optional[str], prefix: str, default: int = 0) -> int:
        if not node_id:
            return default
        try:
            tags = self.treeview.tree.item(node_id, 'tags') or []
            for tag in tags:
                tag_str = str(tag)
                if tag_str.startswith(prefix):
                    return int(tag_str.replace(prefix, ''))
        except (ValueError, TypeError):
            return default
        return default

    def _get_mode_profile_text(self) -> str:
        profile = {
            "cumulative": "Mode: Cumulative (aggressive opponent-aware accumulation)",
            "confidence": "Mode: Confidence (low-variance 3/5 reliability)",
            "resistance": "Mode: Counter (exploitability resistance)",
            "strategic3": "Mode: Strategic Fusion (balanced C2/Q2/R2 + bounded guardrail)",
        }
        active_mode = self.active_sort_mode or "none"
        return profile.get(active_mode, "Mode: Unsorted (raw tree order)")

    def _format_explainability_text(self, node_id: Optional[str]) -> str:
        if not node_id:
            return "Explainability: select a tree node to view C2/Q2/R2 and strategic factors."

        c2 = self.tree_generator.get_cumulative2_from_tags(node_id)
        q2 = self.tree_generator.get_confidence2_from_tags(node_id)
        r2 = self.tree_generator.get_resistance2_from_tags(node_id)
        regret = self.tree_generator.get_regret2_from_tags(node_id)
        floor2 = self._get_tag_value(node_id, 'floor2_', default=q2)
        ceiling2 = self._get_tag_value(node_id, 'ceiling2_', default=q2)
        downside = max(0, ceiling2 - floor2)
        strategic = self.tree_generator.get_strategic3_from_tags(node_id)
        exploit = self.tree_generator.get_strategic3_exploitability_from_tags(node_id)
        children = self.treeview.tree.get_children(node_id)
        sibling_count = len(self.treeview.tree.get_children(self.treeview.tree.parent(node_id) or ""))

        lines = [
            self._get_mode_profile_text(),
            (
                "C2/Q2/R2: "
                f"{self._format_explainability_metric('cumulative', c2)} / "
                f"{self._format_explainability_metric('confidence', q2)} / "
                f"{self._format_explainability_metric('resistance', r2)}"
            ),
            (
                "Regret/Downside: "
                f"{self._format_explainability_metric('regret', regret)} / "
                f"{self._format_explainability_metric('downside', downside)}"
            ),
            (
                "Strategic/Exploitability: "
                f"{self._format_explainability_metric('strategic', strategic)} / "
                f"{self._format_explainability_metric('exploit', exploit)}"
            ),
            (
                "Round-win guardrail signal: "
                f"{self._format_explainability_metric('guardrail', f'{q2 - 50:+d}')}"
            ),
            f"Context: siblings={sibling_count}, remaining children={len(children)}",
            "Bus context: advisory only (YES/NO from calc-grid thresholds)",
        ]
        return "\n".join(lines)

    def _update_explainability_card(self, node_id: Optional[str]):
        if not hasattr(self, 'summary_explain_label'):
            return
        self.summary_explain_label.config(text=self._format_explainability_text(node_id))

    def _on_tree_selection_changed(self, _event=None):
        selected = self.treeview.tree.selection()
        self._update_explainability_card(selected[0] if selected else None)

    def _ensure_tree_explain_tooltip(self):
        if self._tree_explain_tooltip:
            return
        self._tree_explain_tooltip = tk.Toplevel(self.root)
        self._tree_explain_tooltip.wm_overrideredirect(True)
        self._tree_explain_tooltip.wm_attributes("-topmost", True)
        self._tree_explain_tooltip.withdraw()
        self._tree_explain_tooltip_label = tk.Label(
            self._tree_explain_tooltip,
            text="",
            justify=tk.LEFT,
            background="#fff9d8",
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=4,
            font=("Consolas", 8)
        )
        self._tree_explain_tooltip_label.pack(fill=tk.BOTH, expand=True)

    def _hide_tree_explain_tooltip(self, _event=None):
        if self._tree_explain_tooltip:
            self._tree_explain_tooltip.withdraw()
        self._tree_explain_last_node = None

    def _on_tree_hover_explain(self, event):
        node_id = self.treeview.tree.identify_row(event.y)
        if not node_id:
            self._hide_tree_explain_tooltip()
            return
        if node_id == self._tree_explain_last_node:
            return

        self._ensure_tree_explain_tooltip()
        if self._tree_explain_tooltip is None or self._tree_explain_tooltip_label is None:
            return

        text = self._format_explainability_text(node_id)
        self._tree_explain_tooltip_label.config(text=text)
        self._tree_explain_tooltip.update_idletasks()

        x = self.treeview.tree.winfo_rootx() + event.x + 18
        y = self.treeview.tree.winfo_rooty() + event.y + 18
        self._tree_explain_tooltip.geometry(f"+{x}+{y}")
        self._tree_explain_tooltip.deiconify()
        self._tree_explain_tooltip.lift()
        self._tree_explain_last_node = node_id

    def _parse_rating_value(self, rating: Any) -> Optional[float]:
        if rating is None:
            return None
        if isinstance(rating, (int, float)):
            return float(rating)
        rating_text = str(rating).strip()
        if not rating_text:
            return None
        if '/' in rating_text:
            rating_text = rating_text.split('/', 1)[0].strip()
        try:
            return float(rating_text)
        except ValueError:
            return None

    def _render_confidence_histogram(self, ratings: List[float]):
        if not hasattr(self, 'summary_histogram'):
            return
        canvas = self.summary_histogram
        canvas.delete("all")

        if not ratings:
            canvas.create_text(4, 30, anchor=tk.W, text="No confidence data", fill="#777777", font=("Arial", 8))
            return

        min_rating = self.rating_range[0] if hasattr(self, 'rating_range') else 1
        max_rating = self.rating_range[1] if hasattr(self, 'rating_range') else 5
        bin_count = 5
        bin_width = (max_rating - min_rating) / bin_count
        bins = [0] * bin_count

        for rating in ratings:
            if rating < min_rating:
                idx = 0
            elif rating >= max_rating:
                idx = bin_count - 1
            else:
                idx = int((rating - min_rating) / bin_width)
                idx = min(idx, bin_count - 1)
            bins[idx] += 1

        width = int(canvas.winfo_width() or 240)
        height = int(canvas.winfo_height() or 60)
        padding = 4
        available_width = max(width - padding * 2, 1)
        bar_width = available_width / bin_count
        max_count = max(bins) if bins else 1

        for i, count in enumerate(bins):
            bar_height = int((count / max_count) * (height - padding * 2)) if max_count else 0
            x0 = padding + i * bar_width + 1
            x1 = padding + (i + 1) * bar_width - 1
            y0 = height - padding - bar_height
            y1 = height - padding
            canvas.create_rectangle(x0, y0, x1, y1, fill="#7fbf7f", outline="#4f7f4f")
            label = f"{min_rating + i * bin_width:.0f}"
            canvas.create_text(x0 + 2, height - 2, anchor=tk.SW, text=label, fill="#555555", font=("Arial", 7))
    
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

            self._update_matchup_summary(matchups)
            
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
            self._invalidate_calc_grid_cache()
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
            self._invalidate_calc_grid_cache()
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
            self._invalidate_tree_cache("grid_cleared")
            self._invalidate_calc_grid_cache()
            # Refresh entire grid
            for r in range(6):
                for c in range(6):
                    self._update_entry_from_model(r, c)
                    self._update_display_entry_from_model(r, c)
        
        elif event_type == 'grid_loaded':
            self._invalidate_calc_grid_cache()
            # Refresh entire grid after load
            for r in range(6):
                for c in range(6):
                    self._update_entry_from_model(r, c)
                    self._update_display_entry_from_model(r, c)
                    if self.grid_data_model.has_comment(r, c):
                        self._update_comment_indicator(r, c, True)
            self.update_grid_colors()
    
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
                new_value = None  # Empty string ΓåÆ None
            else:
                new_value = current_value  # Keep invalid strings for validation error
        else:
            # Header cell - keep as string (player name)
            new_value = current_value if current_value else None
        
        if new_value != model_value:
            self.grid_data_model.set_rating(row, col, new_value)
            # Trigger color update and scenario calculations
            self.update_color_on_change(None, None, None, row, col)
            self._schedule_scenario_calculations()
            if row > 0 and col > 0:
                self._invalidate_tree_cache("rating_change")
                self._set_grid_dirty(True)
    
    def _update_entry_from_model(self, row: int, col: int):
        """
        Update Entry widget from GridDataModel value.
        Phase 1: Convert int/None ΓåÆ string for Entry widget display.
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
            new_value = self.grid_data_model.get_display(row, col)
            current_text = widget.get()
            if current_text == new_value:
                return

            widget.config(state='normal')
            widget.delete(0, tk.END)
            widget.insert(0, new_value)
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
            return
    
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
