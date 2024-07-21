""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
import os
import csv

# installed libraries
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
# repo libraries
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP
from qtr_pairing_process.lazy_tree_view import LazyTreeView
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.db_load_ui import DbLoadUi
from qtr_pairing_process.xlsx_load_ui import XlsxLoadUi
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.delete_team_dialog import DeleteTeamDialog
from qtr_pairing_process.excel_management.excel_importer import ExcelImporter

class UiManager:
    def __init__(
        self,
        color_map,
        scenario_map,
        directory,
        scenario_ranges,
        scenario_to_csv_map,
        print_output=False
    ):
        self.grid_entries = None
        self.grid_widgets = None
        self.print_output = print_output
        self.directory = directory
        self.color_map = color_map
        self.scenario_map = scenario_map
        self.scenario_ranges = scenario_ranges
        self.scenario_to_csv_map = scenario_to_csv_map
        self.treeview = None


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

        self.grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_widgets = [[None for _ in range(6)] for _ in range(6)]

        self.team_b = tk.IntVar()
        # pairingLead = tk.Checkbutton(self.tree_tab_left_frame, text="Our team first", variable=self.team_b)
        # pairingLead.pack(fill=tk.X, pady=5)
        # pairingLead.select()

        self.sort_alpha = tk.IntVar()
        # alphaBox = tk.Checkbutton(self.tree_tab_left_frame, text="Sort Pairings Alphabetically", variable=self.sort_alpha)
        # alphaBox.pack(fill=tk.X, pady=5)
        # alphaBox.select()

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

		# create combobox for file selection
        # create the label
        tk.Label(self.drop_down_frame, text='Select Team 1:').pack(side=tk.LEFT, padx=5, pady=5)
        # create combobox
        self.combobox_1 = ttk.Combobox(self.drop_down_frame, state='readonly', width=20)
        self.combobox_1.pack(side=tk.LEFT, padx=5, pady=5)
		
        tk.Label(self.drop_down_frame, text='Select Team 2:').pack(side=tk.LEFT, padx=5, pady=5)
        # create combobox
        self.combobox_2 = ttk.Combobox(self.drop_down_frame, state='readonly', width=20)
        self.combobox_2.pack(side=tk.LEFT, padx=5, pady=5)

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
        tk.Button(self.button_row_frame, text="Export CSV", command=lambda: self.export_csvs()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Load Grid", command=lambda: self.load_grid_data_from_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Import CSV", command=lambda: self.import_csvs()).pack(side=tk.LEFT, padx=5, pady=3)
		# tk.Button(self.button_row_frame, text="Add Team", command=lambda: self.add_team_to_db()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Delete Team", command=lambda: self.delete_team()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="REFRESH", command=lambda: self.update_ui()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Import XSLX", command=lambda: self.import_xlsx()).pack(side=tk.LEFT, padx=5, pady=3)

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
		
        # Configure the bottom_frame for Matchup Tree tab
        buttons_frame = tk.Frame(self.tree_tab_left_frame)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        generateButton = tk.Button(buttons_frame, text="Generate\nCombinations", command=self.on_generate_combinations)
        generateButton.pack(fill=tk.X, pady=5)

        math_button_0 = tk.Button(buttons_frame, text="Maximize\nMatchup Strength!", command=self.traverse_and_sum_values_0)
        math_button_0.pack(fill=tk.X, pady=5)

        math_button_1 = tk.Button(buttons_frame, text="Sum\nMatchup Strength!", command=self.traverse_and_sum_values_1)
        math_button_1.pack(fill=tk.X, pady=5)

        optimize_button = tk.Button(buttons_frame, text="Optimize!", command=self.optimize_matchups)
        optimize_button.pack(fill=tk.X, pady=5)

        # self.team_b = tk.IntVar()
        pairingLead = tk.Checkbutton(buttons_frame, text="Our team first", variable=self.team_b)
        pairingLead.pack(side=tk.BOTTOM,pady=5)
        pairingLead.select()

        # self.sort_alpha = tk.IntVar()
        alphaBox = tk.Checkbutton(buttons_frame, text="Sort Pairings Alphabetically", variable=self.sort_alpha)
        alphaBox.pack(pady=5)
        alphaBox.select()

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here")

        self.update_combobox_colors()

        self.root.mainloop()

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
                   
    def traverse_and_sum_values(self):
        self.tree_generator.traverse_and_sum_values()

    def optimize_matchups(self):
        self.tree_generator.optimize_matchups()

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

            self.update_ui()
            
    ####################
    # DB Fill/Save Funcs
    ####################

    def update_ui(self):
        # Update the team dropdowns and grid values
        self.set_team_dropdowns()
        self.load_grid_data_from_db()

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
        if team_1_id > team_2_id:
            team_1_id, team_2_id = team_2_id, team_1_id

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
        if team_1_id > team_2_id:
            team_1_id, team_2_id = team_2_id, team_1_id

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

    def add_team_to_db(self):
        # Create a popup window to enter the team name
        popup = tk.Tk()
        popup.withdraw()  # Hide the main window
        
        team_name = simpledialog.askstring("Input", "Enter the team name:", parent=popup)
        if team_name:
            self.db_manager.create_team(team_name)
        popup.destroy()
        self.update_ui()

    def delete_team(self):
        popup = tk.Tk()
        popup.withdraw()  # Hide the main window

        # Fetch existing team names
        team_names = self.select_team_names()

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
        self.set_team_dropdowns()

    def import_xlsx(self):
        xslx_load_ui  = XlsxLoadUi()
        file_path, file_name = xslx_load_ui.load_xslx_file()
        excel_importer = ExcelImporter(db_manager=self.db_manager, file_path=file_path, file_name=file_name)
        excel_importer.execute()

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
                player1_id = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player1}'")[0][0]
                # print(f"player1 - {player1_id}: {player1}")
                player_ratings = []
                for player2 in team2_players:
                    player2_id = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player2}'")[0][0]
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
        print(f"file length={len(lines)}")
        if len(lines) < 44:
            raise ValueError("Insufficient number of lines")

        team_lines = lines[:2]
        rating_section = lines[2:]
        scenario_id = 0
        team_id = 0
        team_id_1 = 0
        team_id_2 = 0
        team_name = ""
        team_2_player_ids = {}

        for index, line in enumerate(team_lines):
            team_name = line[0]
            player_names = line[1:]

            # Try to upsert this team and the players.
            try:
                team_id = self.db_manager.upsert_team(team_name)
                players = self.db_manager.upsert_and_validate_players(team_id, player_names)
            except ValueError as e:
                print(f"import_csv_header_and_ratings ERROR - {e}")

            # Set combobox values based on the index
            if index == 0:
                self.combobox_1.set(team_name)
                team_id_1 = team_id
            elif index == 1:
                self.combobox_2.set(team_name)
                team_id_2 = team_id
        
        for line in rating_section:
            # print(line)
            rating_line = all(item.isdigit() for item in line[1:])
            # if this line DOES NOT CONTAIN a friendly player followed by ratings
            # this line must contain scenario number followed by enemy player names
            if not rating_line:
                scenario_id = int(line[0])
                team_2_players = line[1:]
                team_1_players = self.db_manager.query_sql(f"SELECT player_name FROM players WHERE team_id = {team_id_1}")

                # Retrieve player_ids for enemy team (team_2)
                team_2_player_ids = {
                    player_name: player_id 
                    for player_name, player_id in self.db_manager.query_sql(
                        f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_2_players)}) and team_id={team_id_2}"
                    )
                }
                print(team_2_player_ids)

            # if this line DOES contain a friendly player followed by ratings
            # this line must contain ratings to upsert
            elif len(line) > 1 and not line[0].isdigit():
                player_name = line[0]
                ratings = list(map(int, line[1:]))

                
                if team_1_player_ids:
                    player_id_1 = team_1_player_ids[1]
                    self.db_manager.upsert_rating(player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)


    # def import_csv_ratings(self, lines):
    #     # Skip the first two header lines
    #     lines = lines[2:]
    #     team_2_players = []
    #     team_2_player_ids = {}
    #     team_2_id = 0

    #     for line in lines:
    #         # print(line)
    #         rating_line = all(item.isdigit() for item in line[1:])
    #         if not rating_line:
    #             scenario_id = int(line[0])
    #             team_2_players = line[1:]

    #             # Retrieve player_ids for enemy team (team_2)
    #             team_2_player_ids = {
    #                 player_name: player_id 
    #                 for player_name, player_id in self.db_manager.query_sql(
    #                     f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_2_players)}) "
    #                 )
    #             }
    #             print(team_2_id)
    #             # Retrieve team_id of the enemy team (team_2) once
    #             if team_2_players:
    #                 team_2_id = self.db_manager.query_sql(f"SELECT team_id FROM players WHERE player_name='{team_2_players[0]}'")[0][0]

    #         elif len(line) > 1 and not line[0].isdigit():
    #             player_name = line[0]
    #             ratings = list(map(int, line[1:]))
                
    #             # Retrieve player_id and team_id for friendly team (team_1)
    #             result = self.db_manager.query_sql(f"SELECT player_id, team_id FROM players WHERE player_name='{player_name}'")
    #             if result:
                    
    #                 player_id_1, team_id_1 = result[0]
    #                 try:
    #                     for i, rating in enumerate(ratings):
    #                         player_name_2 = team_2_players[i]
    #                         player_id_2 = team_2_player_ids[player_name_2]
    #                         rows_affected = self.db_manager.upsert_rating(
    #                             player_id_1,
    #                             player_id_2,
    #                             team_id_1,
    #                             team_2_id,
    #                             scenario_id,
    #                             rating
    #                         )
    #                         if rows_affected == 0:
    #                             raise ValueError(f'insert_scenarios operation failed for table {table}. No rows were affected.')
    #                 except (ValueError,IndexError):
    #                     return 0

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
    
    def get_row_range(self):
        current_scenario = self.get_scenario_num()
        row_lo, row_hi = self.scenario_ranges.get(current_scenario, (1, 6))  # Default to (1, 6) if scenario is not found
        if current_scenario < 1:
            print("Scenario Agnostic Pairing...")
        return row_lo, row_hi

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
