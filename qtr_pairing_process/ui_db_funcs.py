""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
import csv

# installed libraries
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
# repo libraries
from qtr_pairing_process.xlsx_load_ui import XlsxLoadUi
from qtr_pairing_process.delete_team_dialog import DeleteTeamDialog
from qtr_pairing_process.excel_management.excel_importer import ExcelImporter

class UIDBFuncs:
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
        self.is_sorted = False  # State variable to track if the tree is sorted
        self.set_team_dropdowns = None

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

        team_2_players_ids = {}

        for index, line in enumerate(team_lines):
            team_names.append(line[0])
            player_names.append(line[1:])

            # Try to upsert this team and the players.
            try:
                team_id = self.db_manager.upsert_team(line[0])
                players = self.db_manager.upsert_and_validate_players(team_id, player_names[index])
            except ValueError as e:
                print(f"import_csv_header_and_ratings ERROR - {e}")

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
                        f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_players_1)}) and team_id={team_id_1} ORDER BY player_id"
                    )
                }

                # Retrieve player_ids for team_2
                team_2_players_ids = {
                    player_name: player_id
                    for player_name, player_id in self.db_manager.query_sql(
                        f"SELECT player_name, player_id FROM players WHERE player_name IN ({', '.join(f'\"{name}\"' for name in team_players_2)}) and team_id={team_id_2} ORDER BY player_id"
                    )
                }

            elif len(line) > 1 and not line[0].isdigit():
                # if this line DOES contain a friendly player followed by ratings
                # this line must contain ratings to upsert

                if team_2_players_ids:
                    player_1 = line[0]
                    ratings = list(map(int, line[1:]))
                    # Retrieve player_id and team_id for friendly team (team_1)
                    result = self.db_manager.query_sql(f"SELECT player_id, team_id FROM players WHERE player_name='{player_1}' and team_id={team_id_1}")
                    # if results are retrieved then we can continue.
                    try: 
                        if result:
                            player_id_1, team_id_1 = result[0]
                        else:
                            raise ValueError(f'{player_1}')
                    except (ValueError) as e:
                        print(f"VALUE ERROR ON IMPORT: {e}\nThis name doesn't match any friendly player. Check the import file for mistakes based on this name: {e}")

                    for i, rating in enumerate(ratings):
                        try:
                            player_name_2 = list(team_2_players_ids.keys())[i]
                            player_id_2 = team_2_players_ids[player_name_2]
                            self.db_manager.upsert_rating(player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
                        except (ValueError, IndexError) as e:
                            print(f"import_csv_header_and_ratings ERROR - {e}")
