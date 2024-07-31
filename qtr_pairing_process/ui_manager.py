""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
import os

# installed libraries
import tkinter as tk
from tkinter import ttk, messagebox

# repo libraries
from qtr_pairing_process.delete_team_dialog import DeleteTeamDialog
from qtr_pairing_process.excel_management.excel_importer import ExcelImporter
from qtr_pairing_process.ui_db_funcs import UIDBFuncs
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP
from qtr_pairing_process.lazy_tree_view import LazyTreeView
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.db_load_ui import DbLoadUi
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.xlsx_load_ui import XlsxLoadUi


class UiManager:
    def __init__(
        self,
        color_map,
        scenario_map,
        directory,
        scenario_ranges,
        scenario_to_csv_map,
        print_output=False,
        import_csv_header_and_ratings=False,
        select_team_names=False
    ):
        self.grid_entries = None
        self.grid_widgets = None
        self.grid_display_entries = None
        self.grid_display_widgets = None
        self.print_output = print_output
        self.directory = directory
        self.color_map = color_map
        self.scenario_map = scenario_map
        self.scenario_ranges = scenario_ranges
        self.scenario_to_csv_map = scenario_to_csv_map
        self.treeview = None
        self.is_sorted = False  # State variable to track if the tree is sorted

        self.select_database()
        self.initialize_ui_vars()

        if print_output:
            print(f"TKINTER VERSION: {tk.TkVersion}")
            

    def select_database(self):
        db_load_ui = DbLoadUi()
        self.db_path, self.db_name = db_load_ui.create_or_load_database()

        if self.db_path is None:
            self.db_manager = DbManager()
        else:
            self.db_manager = DbManager(path=self.db_path, name=self.db_name)
            
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
        

        self.top_frame = tk.Frame(self.team_grid_frame)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        self.left_frame = tk.Frame(self.top_frame)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.right_frame = tk.Frame(self.top_frame)
        self.right_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.button_row_frame = tk.Frame(self.team_grid_frame)
        self.button_row_frame.pack(side=tk.TOP, fill=tk.X)

        # set frames for the matchup tree tab
        self.tree_tab_left_frame = tk.Frame(self.matchup_tree_frame)
        self.tree_tab_left_frame.pack(side=tk.LEFT)
        self.tree_tab_right_frame = tk.Frame(self.matchup_tree_frame)
        self.tree_tab_right_frame.pack(side=tk.LEFT, expand=1, fill=tk.BOTH)

        self.buttons_frame = tk.Frame(self.tree_tab_left_frame)
        self.buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_widgets = [[None for _ in range(6)] for _ in range(6)]
        self.grid_display_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_display_widgets = [[None for _ in range(6)] for _ in range(6)]

        self.team_b = tk.IntVar()
        pairingLead = tk.Checkbutton(self.buttons_frame, text="Our team first", variable=self.team_b)
        pairingLead.pack(side=tk.BOTTOM,pady=5)
        pairingLead.select()

        self.sort_alpha = tk.IntVar()
        alphaBox = tk.Checkbutton(self.buttons_frame, text="Sort Pairings Alphabetically", variable=self.sort_alpha)
        alphaBox.pack(side=tk.BOTTOM,pady=5)
        alphaBox.select()

        # create treeview and tree generator
        self.treeview = LazyTreeView(master=self.tree_tab_right_frame, print_output=self.print_output, columns=("Rating"))
        self.tree_generator = TreeGenerator(treeview=self.treeview, sort_alpha=self.sort_alpha.get())

    def create_ui(self):
        for r in range(6):
            for c in range(6):
                entry = tk.Entry(self.left_frame, textvariable=self.grid_entries[r][c], width=10)
                entry.grid(row=r+2, column=c, padx=5, pady=5)
                self.grid_widgets[r][c] = entry
                self.grid_entries[r][c].trace_add('write', lambda name, index, mode, var=self.grid_entries[r][c], row=r, col=c: self.update_color_on_change(var, index, mode, row, col))

                display_entry = tk.Entry(self.right_frame, textvariable=self.grid_display_entries[r][c], width=10, state='readonly')
                display_entry.grid(row=r+2, column=c, padx=5, pady=5)
                self.grid_display_widgets[r][c] = display_entry

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

        # Add Buttons to a row just above the pairing grid       
        tk.Button(self.button_row_frame, text="Export CSV", command=lambda: self.on_export_csvs()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Load Grid", command=lambda: self.load_grid_data_from_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Import CSV", command=lambda: self.on_import_csvs()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Add Team", command=lambda: self.on_add_team_to_db()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Delete Team", command=lambda: self.delete_team()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="REFRESH", command=lambda: self.update_ui()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Import XSLX", command=lambda: self.import_xlsx()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="GET SCORE", command=lambda: self.on_scenario_calculations()).pack(side=tk.LEFT, padx=5, pady=5)

		# Configure Treeview with style and maximize space
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10))
        self.treeview.tree.heading("#0", text="Pairing")
        self.treeview.tree.heading("Rating", text="Rating")
        self.treeview.tree.tag_configure('1', background="orangered")
        self.treeview.tree.tag_configure('2', background="orange")
        self.treeview.tree.tag_configure('3', background="yellow")
        self.treeview.tree.tag_configure('4', background="greenyellow")
        self.treeview.tree.tag_configure('5', background="lime")
        self.treeview.pack(expand=1, fill='both')
		
        generateButton = tk.Button(self.buttons_frame, text="Generate\nCombinations", command=self.on_generate_combinations)
        generateButton.pack(fill=tk.X, pady=5)

        math_button_0 = tk.Button(self.buttons_frame, text="Maximize\nMatchup Strength!", command=self.traverse_and_sum_values_0)
        math_button_0.pack(fill=tk.X, pady=5)

        math_button_1 = tk.Button(self.buttons_frame, text="Sum\nMatchup Strength!", command=self.traverse_and_sum_values_1)
        math_button_1.pack(fill=tk.X, pady=5)

        math_button_3 = tk.Button(self.buttons_frame, text="MEAN\nMatchup Strength!", command=self.traverse_and_sum_values_3)
        math_button_3.pack(fill=tk.X, pady=5)

        math_button_1 = tk.Button(self.buttons_frame, text="Avoid Poor Matchups!", command=self.traverse_and_sum_values_2)
        math_button_1.pack(fill=tk.X, pady=5)

        self.sort_tree_button = tk.Button(self.buttons_frame, text="Sort Matchups!", command=self.toggle_sorting)
        self.sort_tree_button.pack(fill=tk.X, pady=5)

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here\nNavigate the tree with arrow keys!")

        self.update_combobox_colors()
        self.init_display_headers()

        self.root.mainloop()

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

    def on_add_team_to_db(self):
        UIDBFuncs.add_team_to_db(self)

    def on_export_csvs(self):
        UIDBFuncs.export_csvs(self)

    def on_import_csvs(self):
        UIDBFuncs.import_csvs(self)

    def on_scenario_calculations(self):
        self.set_floor_values() # info_col 0
        self.check_pinned_players() # info_col 1
        self.check_for_pins() # info_col 2
        self.check_protect() # info_col 3
        self.check_margins() # info_col 4 & 5

    # Not sure if this data is actually useful to players?
    def check_margins(self):
        for row in range(1, 6):
            try:
                floor_rating_sum = int(self.grid_display_entries[row][0].get())
                all_margins = []
                for col in range(1, 6):
                    col_margin_sum = sum(int(self.grid_entries[row1][col].get()) for row1 in range(1, 6))
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
                # Sum the ratings for the current row
                row_pinned = self.grid_display_entries[row][1].get() != "---"
                row_pinner = self.grid_display_entries[row][2].get() != "---"
                protect = "Yes" if row_pinned or row_pinner else "No"
                self.update_display_fields(row, 3, protect)
            except (ValueError, IndexError) as e:
                print(f"check_protect has failed for row {row} with error:\n{e}")
        
    def check_for_pins(self):
        for row in range(1, 6):
            try:
                good_matchups = sum(1 for col in range(1, 6) if int(self.grid_entries[row][col].get()) > 3)
                can_pin = "PIN" if good_matchups > 1 else "---"
                self.update_display_fields(row, 2, can_pin)
            except (ValueError, IndexError) as e:
                print(f"check_for_pins has failed for row {row} with error:\n{e}")
        
    def check_pinned_players(self):
        for row in range(1, 6):
            try:
                num_bad_matchups = sum(1 for col in range(1, 6) if int(self.grid_entries[row][col].get()) < 3)
                player_pinned = "PINNED!" if num_bad_matchups > 1 else "---"
                self.update_display_fields(row, 1, player_pinned)
            except (ValueError, IndexError) as e:
                print(f"check_pinned_players has failed for row {row} with error:\n{e}")

    def set_floor_values(self): # Calculate the sum of ratings for each player and update the second grid
        for row in range(1,6):
            try:
                # Sum the ratings for the current row
                floor_rating_sum = sum(int(self.grid_entries[row][col].get()) for col in range(1,6))
                # Update the corresponding entry in the display-only grid
                self.update_display_fields(row, 0, floor_rating_sum)
            except (ValueError, IndexError) as e:
                print(f"set_floor_values has failed with error:\n{e}")

    def switch_tab(self):
        current_tab = self.notebook.index(self.notebook.select())
        total_tabs = self.notebook.index('end')
        next_tab = (current_tab + 1) % total_tabs
        self.notebook.select(next_tab)

    def on_generate_combinations(self):
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
        
    def traverse_and_sum_values_0(self):
        self.tree_generator.traverse_and_sum_values(0)

    def traverse_and_sum_values_1(self):
        self.tree_generator.traverse_and_sum_values(1)

    def traverse_and_sum_values_2(self):
        self.tree_generator.traverse_and_sum_values(2)
                   
    def traverse_and_sum_values_3(self):
        self.tree_generator.traverse_and_sum_values(3)

    def sort_matchup_tree(self):
        self.tree_generator.sort_matchup_value()

    def toggle_sorting(self):
        if self.is_sorted:
            self.tree_generator.unsort_matchup_tree()
            self.sort_tree_button.config(text="Sort Matchups!")
        else:
            self.tree_generator.sort_matchup_value()
            self.sort_tree_button.config(text="Remove Sorting")
        
        self.is_sorted = not self.is_sorted  # Toggle the state

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
            except (ValueError,IndexError) as e:
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

    # def select_team_names(self):
    #     # Using this for testing.
    #     # Possibly remove this later.
    #     sql = 'select team_name from teams'
    #     teams = self.db_manager.query_sql(sql)
    #     team_names = [t[0] for t in teams]
    #     if not team_names:
    #         team_names = ['No teams Found']
    #     return team_names

    def set_team_dropdowns(self):
        team_names = UIDBFuncs.select_team_names(self)
        self.combobox_1['values'] = team_names
        self.combobox_2['values'] = team_names

    def load_grid_data_from_db(self):
        team_1 = self.combobox_1.get()
        team_2 = self.combobox_2.get()
        scenario = self.scenario_box.get()[:1]
        if scenario == '':
            self.scenario_box.set("0 - Neutral")
            scenario = self.scenario_box.get()[:1]
        scenario_id = int(scenario)

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        team_2_id = team_2_row[0][0]

        # Do not assume that the lower team value is the home team
        # if team_1_id > team_2_id:
        #     team_1_id, team_2_id = team_2_id, team_1_id

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {row[0]:{'position':i+1,'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {row[0]:{'position':i+1,'name':row[1]}for i,row in enumerate(team_2_players)}
        # print(team_1_dict)
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
        # print(ratings_rows)
        # update usernames
        for _, row_dict in team_2_dict.items():

            self.grid_entries[0][row_dict['position']].set(row_dict['name'])
        
        for _, row_dict in team_1_dict.items():
            self.grid_entries[row_dict['position']][0].set(row_dict['name'])

        for r, row in enumerate(ratings_rows):
            team_1_pos = team_1_dict[row[0]]['position']
            team_2_pos = team_2_dict[row[1]]['position']
            self.grid_entries[team_1_pos][team_2_pos].set(row[2])
        
    def save_grid_data_to_db(self):
        team_1 = self.combobox_1.get()
        team_2 = self.combobox_2.get()
        scenario_id = int(self.scenario_box.get()[:1])

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        team_2_id = team_2_row[0][0]

        # Do not assume that the lower team value is the home team
        # if team_1_id > team_2_id:
        #     team_1_id, team_2_id = team_2_id, team_1_id

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {i+1:{'id':row[0],'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {i+1:{'id':row[0],'name':row[1]}for i,row in enumerate(team_2_players)}

        for row in range(1,len(self.grid_entries)):
            for col in range(1,len(self.grid_entries[0])):
                rating = int(self.grid_entries[row][col].get())
                team_1_player_id = team_1_dict[row]['id']
                team_2_player_id = team_2_dict[col]['id']
                try:
                    self.db_manager.upsert_rating(
                        player_id_1=team_1_player_id,
                        player_id_2=team_2_player_id,
                        team_id_1=team_1_id,
                        team_id_2=team_2_id,
                        scenario_id=scenario_id,
                        rating=rating
                    )
                except (ValueError, IndexError):
                    return 0 

    # def add_team_to_db(self):
    #     # Create a popup window to enter the team name
    #     popup = tk.Tk()
    #     popup.withdraw()  # Hide the main window
        
    #     team_name = simpledialog.askstring("Input", "Enter the team name:", parent=popup)
    #     if team_name:
    #         self.db_manager.create_team(team_name)
    #     popup.destroy()
    #     self.update_ui()

    def delete_team(self):
        popup = tk.Tk()
        popup.withdraw()  # Hide the main window

        # Fetch existing team names
        team_names = UIDBFuncs.select_team_names(self)

        # Create and display the delete team dialog
        dialog = DeleteTeamDialog(popup, team_names)
        popup.wait_window(dialog.top)

        team_name = dialog.selected_team
        if team_name is None:
            return  # User cancelled the operation

        # Validate the user's input
        if team_name not in team_names:
            messagebox.showerror("Error", f"Invalid team name: {team_name}")
            return

        # Retrieve the team_id of the selected team
        team_id_row = self.db_manager.query_sql(f"SELECT team_id FROM teams WHERE team_name='{team_name}'")
        if not team_id_row:
            messagebox.showerror("Error", f"Team not found: '{team_name}'")
            return

        team_id = team_id_row[0][0]

        # Delete related records
        self.db_manager.execute_sql(f"DELETE FROM ratings WHERE team_1_id={team_id} OR team_2_id={team_id}")
        self.db_manager.execute_sql(f"DELETE FROM players WHERE team_id={team_id}")
        self.db_manager.execute_sql(f"DELETE FROM teams WHERE team_id={team_id}")

        messagebox.showinfo("Success", f"Team '{team_name}' and all related records have been deleted successfully.")
        try:
            self.set_team_dropdowns()
            self.update_ui
        except (ValueError, IndexError) as e:
            print(f"delete_team caused an error trying to update the UI: {e}")

    def import_xlsx(self):
        xslx_load_ui  = XlsxLoadUi()
        file_path, file_name = xslx_load_ui.load_xslx_file()
        excel_importer = ExcelImporter(db_manager=self.db_manager, file_path=file_path, file_name=file_name)
        try:
            excel_importer.execute()
        except (ValueError,IndexError) as e:
            print(f"import_xlsx error: {e}")

    # def export_csvs(self):
    #     print(f"Exporting Matchups to CSV")

    #     # Prompt the user to select a file location to save the CSV
    #     file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    #     if not file_path:
    #         return

    #     # Retrieve data from the database
    #     team1_name, team1_players = self.retrieve_team_data(self.combobox_1.get())
    #     team2_name, team2_players = self.retrieve_team_data(self.combobox_2.get())
    #     ratings = self.retrieve_ratings(team1_players, team2_players)

    #     # Write data to CSV
    #     with open(file_path, mode='w', newline='') as csvfile:
    #         writer = csv.writer(csvfile)

    #         # Write headers
    #         writer.writerow([team1_name] + team1_players)
    #         writer.writerow([team2_name] + team2_players)

    #         # Write ratings
    #         for scenario_id, rating_data in ratings.items():
    #             writer.writerow([scenario_id] + team2_players)
    #             for player, player_ratings in rating_data.items():
    #                 writer.writerow([player] + player_ratings)

    # def retrieve_team_data(self, team_name):
    #     team_id = self.db_manager.query_team_id(team_name)
    #     players = self.db_manager.query_sql(f"SELECT player_name FROM players WHERE team_id = {team_id} ORDER BY player_id")
    #     player_names = [player[0] for player in players]
    #     return team_name, player_names

    # def retrieve_ratings(self, team1_players, team2_players):
    #     ratings = {}
    #     scenario_id = []        
    #     for scenario in range(0,6):
            
    #         scenario_id = scenario
    #         ratings[scenario_id] = {}
    #         for player1 in team1_players:
    #             player1_id = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player1}'")[0][0]
    #             # print(f"player1 - {player1_id}: {player1}")
    #             player_ratings = []
    #             for player2 in team2_players:
    #                 player2_id = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player2}'")[0][0]
    #                 rating = self.db_manager.query_sql(f"""
    #                     SELECT rating FROM ratings
    #                     WHERE team_1_player_id = {player1_id} AND team_2_player_id = {player2_id} AND scenario_id = {scenario_id}
    #                 """)
    #                 player_ratings.append(rating[0][0] if rating else 0)  # Default to 0 if no rating found
    #             ratings[scenario_id][player1] = player_ratings

    #     return ratings


    
    # def import_csvs(self):
    #     file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    #     with open(file_path, newline='') as csvfile:
    #         reader = csv.reader(csvfile)
    #         lines = list(reader)

    #     self.import_csv_header_and_ratings(lines)
    #     # self.import_csv_ratings(lines)
    #     self.update_ui()

    # def import_csv_header_and_ratings(self, lines):
    #     # Only take the first two lines from the file.
    #     # CSV import should be exactly 44 lines if done correctly.
    #     # Let's allow it to be short, in case we don't want to import all 6 scenarios
    #     # print(f"file length={len(lines)}")
    #     if len(lines) < 44:
    #         raise ValueError("Insufficient number of lines")

    #     team_lines = lines[:2]
    #     rating_section = lines[2:]

    #     team_names = []
    #     team_name_1 = ""
    #     team_name_2 = ""
    #     player_names = []
    #     team_players_1 = []
    #     team_players_2 = []

    #     team_2_players_ids = {}

    #     for index, line in enumerate(team_lines):
    #         team_names.append(line[0])
    #         player_names.append(line[1:])

    #         # Try to upsert this team and the players.
    #         try:
    #             team_id = self.db_manager.upsert_team(line[0])
    #             players = self.db_manager.upsert_and_validate_players(team_id, player_names[index])
    #         except ValueError as e:
    #             print(f"import_csv_header_and_ratings ERROR - {e}")

    #         # Set combobox values based on the index
    #         if index == 0:
    #             team_name_1 = team_names[index]
    #             self.combobox_1.set(team_name_1)
    #             team_id_1 = team_id
    #             team_players_1 = player_names[index]
    #         elif index == 1:
    #             team_name_2 = team_names[index]
    #             self.combobox_2.set(team_name_2)
    #             team_id_2 = team_id
    #             team_players_2 = player_names[index]

    #     for line in rating_section:
    #         # if this line DOES NOT CONTAIN a friendly player followed by ratings
    #         # this line must contain scenario number followed by enemy player names
    #         rating_line = all(item.isdigit() for item in line[1:])
    #         if not rating_line:
    #             scenario_id = int(line[0])

    #             # Retrieve player_ids for team_1
    #             team_1_players_ids = {
    #                 player_name: player_id
    #                 for player_name, player_id in self.db_manager.query_sql(
    #                     f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_players_1)}) and team_id={team_id_1} ORDER BY player_id"
    #                 )
    #             }

    #             # Retrieve player_ids for team_2
    #             team_2_players_ids = {
    #                 player_name: player_id
    #                 for player_name, player_id in self.db_manager.query_sql(
    #                     f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_players_2)}) and team_id={team_id_2} ORDER BY player_id"
    #                 )
    #             }

    #         elif len(line) > 1 and not line[0].isdigit():
    #             # if this line DOES contain a friendly player followed by ratings
    #             # this line must contain ratings to upsert

    #             if team_2_players_ids:
    #                 player_1 = line[0]
    #                 ratings = list(map(int, line[1:]))
    #                 # Retrieve player_id and team_id for friendly team (team_1)
    #                 result = self.db_manager.query_sql(f"SELECT player_id, team_id FROM players WHERE player_name='{player_1}' and team_id={team_id_1}")
    #                 # if results are retrieved then we can continue.
    #                 try: 
    #                     if result:
    #                         player_id_1, team_id_1 = result[0]
    #                     else:
    #                         raise ValueError(f'{player_1}')
    #                 except (ValueError) as e:
    #                     print(f"VALUE ERROR ON IMPORT: {e}\nThis name doesn't match any friendly player. Check the import file for mistakes based on this name: {e}")

    #                 for i, rating in enumerate(ratings):
    #                     try:
    #                         player_name_2 = list(team_2_players_ids.keys())[i]
    #                         player_id_2 = team_2_players_ids[player_name_2]
    #                         self.db_manager.upsert_rating(player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
    #                     except (ValueError, IndexError) as e:
    #                         print(f"import_csv_header_and_ratings ERROR - {e}")

    #############################################

    def update_combobox_colors(self):
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                if value in self.color_map:
                    self.grid_widgets[row][col].config(bg=self.color_map[value])
                    
    def update_color_on_change(self, var, index, mode, row, col):
        value = var.get()
        if value in self.color_map:
            self.grid_widgets[row][col].config(bg=self.color_map[value])
        else:
            self.grid_widgets[row][col].config(bg='white')

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

    def validate_grid_data(self):
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                if value not in ['1', '2', '3', '4', '5']:
                    messagebox.showerror("Error", f"Invalid rating at row {row+1}, column {col+1}. Ratings should be between 1 and 5.")
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

if __name__ == '__main__':
    ui_manager = UiManager(color_map=DEFAULT_COLOR_MAP, scenario_map=SCENARIO_MAP, directory=os.getcwd())
    ui_manager.create_ui()
