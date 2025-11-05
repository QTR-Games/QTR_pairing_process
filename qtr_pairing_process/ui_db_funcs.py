""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
import csv
from typing import Optional, Callable, List, Any

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
        db_manager=None,
        print_output=False
    ):
        # Initialize basic attributes
        self.print_output = print_output
        self.directory = directory
        self.color_map = color_map
        self.scenario_map = scenario_map
        self.scenario_ranges = scenario_ranges
        self.scenario_to_csv_map = scenario_to_csv_map
        self.is_sorted = False  # State variable to track if the tree is sorted
        
        # UI component references (to be set by UI manager)
        self.db_manager = db_manager  # type: ignore # Will be set by UI manager
        self.grid_entries: Optional[List[List[Any]]] = None
        self.grid_widgets: Optional[List[List[Any]]] = None
        self.combobox_1: Optional[Any] = None  # tkinter.ttk.Combobox
        self.combobox_2: Optional[Any] = None  # tkinter.ttk.Combobox
        self.scenario_box: Optional[Any] = None  # tkinter.ttk.Combobox
        self.treeview: Optional[Any] = None
        
        # Method references (to be set by UI manager)
        self.update_ui: Optional[Callable[[], None]] = None
        # set_team_dropdowns is implemented as a method below

    def set_ui_components(self, ui_manager):
        """Set references to UI manager components"""
        self.db_manager = ui_manager.db_manager
        self.grid_entries = ui_manager.grid_entries
        self.grid_widgets = ui_manager.grid_widgets
        self.combobox_1 = ui_manager.combobox_1
        self.combobox_2 = ui_manager.combobox_2
        self.scenario_box = ui_manager.scenario_box
        self.treeview = ui_manager.treeview
        self.update_ui = ui_manager.update_ui

    def _validate_ui_components(self):
        """Validate that required UI components are available"""
        if self.db_manager is None:
            raise RuntimeError("Database manager not initialized")
        if self.grid_entries is None:
            raise RuntimeError("Grid entries not initialized")
        if self.combobox_1 is None or self.combobox_2 is None:
            raise RuntimeError("Team comboboxes not initialized")
        if self.scenario_box is None:
            raise RuntimeError("Scenario box not initialized")
    
    def _safe_get_combobox_value(self, combobox) -> str:
        """Safely get combobox value"""
        if combobox is None:
            return ""
        return combobox.get()
    
    def _safe_set_combobox_value(self, combobox, value: str):
        """Safely set combobox value"""
        if combobox is not None:
            combobox.set(value)
    
    def _safe_get_scenario_value(self) -> str:
        """Safely get scenario box value"""
        if self.scenario_box is None:
            return "0"
        return self.scenario_box.get()[:1] if self.scenario_box.get() else "0"

    def select_team_names(self):
        """Get team names from database"""
        if self.db_manager is None:
            return ['No teams Found']
        
        try:
            sql = 'select team_name from teams'
            teams = self.db_manager.query_sql(sql)
            team_names = [t[0] for t in teams]
            if not team_names:
                team_names = ['No teams Found']
            return team_names
        except Exception as e:
            if self.print_output:
                print(f"Error loading team names: {e}")
            return ['No teams Found']

    def set_team_dropdowns(self):
        """Set team dropdown values"""
        try:
            team_names = self.select_team_names()
            if self.combobox_1 is not None:
                self.combobox_1['values'] = team_names
            if self.combobox_2 is not None:
                self.combobox_2['values'] = team_names
        except Exception as e:
            if self.print_output:
                print(f"Error setting team dropdowns: {e}")

    def load_grid_data_from_db(self):
        """Load grid data from database"""
        try:
            self._validate_ui_components()
        except RuntimeError as e:
            if self.print_output:
                print(f"Cannot load grid data: {e}")
            return
        
        if self.db_manager is None:
            if self.print_output:
                print("Database manager not initialized")
            return
        
        team_1 = self._safe_get_combobox_value(self.combobox_1)
        team_2 = self._safe_get_combobox_value(self.combobox_2)
        scenario = self._safe_get_scenario_value()
        if scenario == '':
            self._safe_set_combobox_value(self.scenario_box, "0 - Neutral")
            scenario = self._safe_get_scenario_value()
        
        try:
            scenario_id = int(scenario)
        except (ValueError, TypeError):
            if self.print_output:
                print(f"Invalid scenario value: {scenario}")
            return

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        if not team_1_row:
            if self.print_output:
                print(f"Team '{team_1}' not found in database")
            return
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        if not team_2_row:
            if self.print_output:
                print(f"Team '{team_2}' not found in database")
            return
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
        # Update usernames with bounds checking
        if self.grid_entries is not None:
            for _, row_dict in team_2_dict.items():
                pos = row_dict['position']
                if 0 <= pos < len(self.grid_entries[0]):
                    self.grid_entries[0][pos].set(row_dict['name'])
            
            for _, row_dict in team_1_dict.items():
                pos = row_dict['position']
                if 0 <= pos < len(self.grid_entries):
                    self.grid_entries[pos][0].set(row_dict['name'])

            for r, row in enumerate(ratings_rows):
                team_1_pos = team_1_dict[row[0]]['position']
                team_2_pos = team_2_dict[row[1]]['position']
                if (0 <= team_1_pos < len(self.grid_entries) and 
                    0 <= team_2_pos < len(self.grid_entries[0])):
                    self.grid_entries[team_1_pos][team_2_pos].set(row[2])
        
    def save_grid_data_to_db(self):
        """Save grid data to database"""
        try:
            self._validate_ui_components()
        except RuntimeError as e:
            if self.print_output:
                print(f"Cannot save grid data: {e}")
            return
        
        if self.db_manager is None:
            if self.print_output:
                print("Database manager not initialized")
            return
        
        team_1 = self._safe_get_combobox_value(self.combobox_1)
        team_2 = self._safe_get_combobox_value(self.combobox_2)
        
        try:
            scenario_id = int(self._safe_get_scenario_value())
        except (ValueError, TypeError):
            if self.print_output:
                print("Invalid scenario for saving")
            return

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        if not team_1_row:
            if self.print_output:
                print(f"Team '{team_1}' not found in database")
            return
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        if not team_2_row:
            if self.print_output:
                print(f"Team '{team_2}' not found in database")
            return
        team_2_id = team_2_row[0][0]

        # Do not assume that the lower team value is the home team
        # if team_1_id > team_2_id:
        #     team_1_id, team_2_id = team_2_id, team_1_id

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {i+1:{'id':row[0],'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {i+1:{'id':row[0],'name':row[1]}for i,row in enumerate(team_2_players)}

        if self.grid_entries is not None:
            for row in range(1, len(self.grid_entries)):
                for col in range(1, len(self.grid_entries[0])):
                    try:
                        rating = int(self.grid_entries[row][col].get())
                        if row in team_1_dict and col in team_2_dict:
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
                    except (ValueError, IndexError, KeyError) as e:
                        if self.print_output:
                            print(f"Error saving rating at [{row}, {col}]: {e}")
                        continue

    def add_team_to_db(self):
        """Add a new team to the database"""
        if self.db_manager is None:
            if self.print_output:
                print("Database manager not available")
            return
            
        # Create a popup window to enter the team name
        popup = tk.Tk()
        popup.withdraw()  # Hide the main window
        
        team_name = simpledialog.askstring("Input", "Enter the team name:", parent=popup)
        if team_name:
            self.db_manager.create_team(team_name)
        popup.destroy()
        
        if self.update_ui is not None:
            self.update_ui()

    def delete_team(self):
        if self.db_manager is None:
            messagebox.showerror("Error", "Database manager not initialized")
            return
            
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

        if not team_id_row:
            messagebox.showerror("Error", f"Team '{team_name}' not found in database.")
            return
        
        team_id = team_id_row[0][0]

        try:
            # Delete related records
            self.db_manager.execute_sql(f"DELETE FROM ratings WHERE team_1_id={team_id} OR team_2_id={team_id}")
            self.db_manager.execute_sql(f"DELETE FROM players WHERE team_id={team_id}")
            self.db_manager.execute_sql(f"DELETE FROM teams WHERE team_id={team_id}")

            messagebox.showinfo("Success", f"Team '{team_name}' and all related records have been deleted successfully.")
            if self.set_team_dropdowns is not None:
                self.set_team_dropdowns()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete team: {e}")

    def import_xlsx(self):
        """Import Excel file"""
        if self.db_manager is None:
            messagebox.showerror("Error", "Database not available")
            return
            
        try:
            xslx_load_ui = XlsxLoadUi()
            file_path, file_name = xslx_load_ui.load_xslx_file()
            if file_path and file_name:
                excel_importer = ExcelImporter(db_manager=self.db_manager, file_path=file_path, file_name=file_name)
                excel_importer.execute()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import Excel file: {e}")

    def export_csvs(self):
        """Export matchups to CSV"""
        try:
            self._validate_ui_components()
        except RuntimeError as e:
            messagebox.showerror("Error", f"Cannot export CSV: {e}")
            return
            
        if self.print_output:
            print("Exporting Matchups to CSV")

        # Prompt the user to select a file location to save the CSV
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        try:
            # Retrieve data from the database
            team1_name, team1_players = self.retrieve_team_data(self._safe_get_combobox_value(self.combobox_1))
            team2_name, team2_players = self.retrieve_team_data(self._safe_get_combobox_value(self.combobox_2))
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
                        
            if self.print_output:
                print(f"CSV exported successfully to {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {e}")

    def retrieve_team_data(self, team_name):
        """Retrieve team data from database"""
        if self.db_manager is None:
            return team_name, []
            
        try:
            team_id = self.db_manager.query_team_id(team_name)
            if team_id is None:
                return team_name, []
                
            players = self.db_manager.query_sql(f"SELECT player_name FROM players WHERE team_id = {team_id} ORDER BY player_id")
            player_names = [player[0] for player in players]
            return team_name, player_names
        except Exception as e:
            if self.print_output:
                print(f"Error retrieving team data for {team_name}: {e}")
            return team_name, []

    def retrieve_ratings(self, team1_players, team2_players):
        """Retrieve ratings data from database"""
        if self.db_manager is None:
            return {}
            
        ratings = {}
        
        try:
            for scenario in range(0, 6):
                scenario_id = scenario
                ratings[scenario_id] = {}
                
                for player1 in team1_players:
                    player1_result = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player1}'")
                    if not player1_result:
                        continue
                    player1_id = player1_result[0][0]
                    
                    player_ratings = []
                    for player2 in team2_players:
                        try:
                            player2_result = self.db_manager.query_sql(f"SELECT player_id FROM players WHERE player_name = '{player2}'")
                            if not player2_result:
                                player_ratings.append(0)
                                continue
                            player2_id = player2_result[0][0]
                            
                            rating = self.db_manager.query_sql(f"""
                                SELECT rating FROM ratings
                                WHERE team_1_player_id = {player1_id} AND team_2_player_id = {player2_id} AND scenario_id = {scenario_id}
                            """)
                            player_ratings.append(rating[0][0] if rating else 0)  # Default to 0 if no rating found
                        except Exception as e:
                            if self.print_output:
                                print(f"Error getting rating for {player1} vs {player2}: {e}")
                            player_ratings.append(0)
                            
                    ratings[scenario_id][player1] = player_ratings
                    
        except Exception as e:
            if self.print_output:
                print(f"Error retrieving ratings: {e}")
            
        return ratings


    
    def import_csvs(self):
        if self.db_manager is None:
            messagebox.showerror("Error", "Database manager not initialized")
            return
            
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            lines = list(reader)

        self.import_csv_header_and_ratings(lines)
        # self.import_csv_ratings(lines)
        if self.update_ui is not None:
            self.update_ui()

    def import_csv_header_and_ratings(self, lines):
        if self.db_manager is None:
            messagebox.showerror("Error", "Database manager not initialized")
            return
            
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
        team_id_1 = None
        team_id_2 = None

        team_2_players_ids = {}

        for index, line in enumerate(team_lines):
            team_names.append(line[0])
            player_names.append(line[1:])

            # Try to upsert this team and the players.
            team_id = None
            try:
                team_id = self.db_manager.upsert_team(line[0])
                players = self.db_manager.upsert_and_validate_players(team_id, player_names[index])
            except ValueError as e:
                print(f"import_csv_header_and_ratings ERROR - {e}")
                continue  # Skip this team if there's an error

            # Set combobox values based on the index
            if index == 0 and team_id is not None:
                team_name_1 = team_names[index]
                self._safe_set_combobox_value(self.combobox_1, team_name_1)
                team_id_1 = team_id
                team_players_1 = player_names[index]
            elif index == 1 and team_id is not None:
                team_name_2 = team_names[index]
                self._safe_set_combobox_value(self.combobox_2, team_name_2)
                team_id_2 = team_id
                team_players_2 = player_names[index]

        # Initialize scenario_id
        scenario_id = None
        
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

                if team_2_players_ids and scenario_id is not None:
                    player_1 = line[0]
                    ratings = list(map(int, line[1:]))
                    # Retrieve player_id and team_id for friendly team (team_1)
                    result = self.db_manager.query_sql(f"SELECT player_id, team_id FROM players WHERE player_name='{player_1}' and team_id={team_id_1}")
                    # if results are retrieved then we can continue.
                    player_id_1 = None
                    try: 
                        if result:
                            player_id_1, team_id_1 = result[0]
                        else:
                            raise ValueError(f'{player_1}')
                    except (ValueError) as e:
                        print(f"VALUE ERROR ON IMPORT: {e}\nThis name doesn't match any friendly player. Check the import file for mistakes based on this name: {e}")
                        continue

                    if player_id_1 is not None:
                        for i, rating in enumerate(ratings):
                            try:
                                player_name_2 = list(team_2_players_ids.keys())[i]
                                player_id_2 = team_2_players_ids[player_name_2]
                                self.db_manager.upsert_rating(player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
                            except (ValueError, IndexError) as e:
                                print(f"import_csv_header_and_ratings ERROR - {e}")
