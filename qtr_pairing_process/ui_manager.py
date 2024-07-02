""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
# native libraries
import os
import csv

# installed libraries
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
# repo libraries
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP
from qtr_pairing_process.lazy_tree_view import LazyTreeView
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.db_load_ui import DbLoadUi
from qtr_pairing_process.db_management.db_manager import DbManager
class UiManager:
    def __init__(
        self,
        color_map,
        scenario_map,
        directory,
        scenario_ranges,
        scenario_to_csv_map,
        print_output=True
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
        self.root.title('Pairings Debug')

        # set key bindings
        self.root.bind('<Escape>', lambda event: self.root.quit())
        self.root.bind('<Return>', lambda event: self.on_generate_combinations())
    
        # set frames
        self.drop_down_frame = tk.Frame(self.root)
        self.drop_down_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        self.left_frame = tk.Frame(self.top_frame)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.right_frame = tk.Frame(self.top_frame)
        self.right_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.button_row_frame = tk.Frame(self.root)
        self.button_row_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
        self.grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
        self.grid_widgets = [[None for _ in range(6)] for _ in range(6)]
    
        # create textbox
        self.textbox = tk.Text(self.right_frame, width=60, height=7)
        self.textbox.pack(expand=1, fill='both')

        # set team_b button
        self.team_b = tk.IntVar()
        pairingLead = tk.Checkbutton(self.right_frame, text="Our team first", variable=self.team_b)
        pairingLead.pack(side=tk.RIGHT, padx=5, pady=3)
        pairingLead.select()

        # set alpha checkbox
        self.sort_alpha = tk.IntVar()
        alphaBox = tk.Checkbutton(self.right_frame, text="Sort Pairings Alphabetically", variable=self.sort_alpha)
        alphaBox.pack(side=tk.RIGHT,pady=3,padx=5)
        alphaBox.select()

        # create treeview and tree generator
        self.treeview = LazyTreeView(master=self.bottom_frame, print_output=self.print_output,columns=("Rating"))
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
        self.select_team_names()
        self.update_scenario_box()

        # Add Buttons to a row just above the pairing grid       
        tk.Button(self.button_row_frame, text="IMPORT CSV", command=lambda: self.get_data_from_csv()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Load Grid", command=lambda: self.load_grid_data_from_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Save Grid", command=lambda: self.save_grid_data_to_db()).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.button_row_frame, text="Update Grid", command=lambda: self.update_grid_from_textbox()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Update Text", command=lambda: self.update_textbox()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Clear Text", command=lambda: self.clear_textbox()).pack(side=tk.LEFT, padx=5, pady=3)
        tk.Button(self.button_row_frame, text="Save", command=lambda: self.save_textbox_content()).pack(side=tk.LEFT, padx=5, pady=3)
        
        # Configure Treeview ... with style!
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 12))
        self.treeview.tree.heading("#0", text="Pairing")
        self.treeview.tree.heading("Rating", text="Rating")
        self.treeview.tree.tag_configure('1', background="orangered")
        self.treeview.tree.tag_configure('2', background="orange")
        self.treeview.tree.tag_configure('3', background="yellow")
        self.treeview.tree.tag_configure('4', background="yellowgreen")
        self.treeview.tree.tag_configure('5', background="deepskyblue")
        self.treeview.pack(expand=1, fill='both')

    
        generateButton = tk.Button(self.bottom_frame, text="Generate Combinations", command=self.on_generate_combinations)
        generateButton.pack(pady=10)
        show_info_button = tk.Button(text="Show Info", command=self.treeview.item_details)
        show_info_button.pack()
        show_selection_button = tk.Button(text="Show Selection", command=self.treeview.show_selection)
        show_selection_button.pack(side=tk.LEFT, padx=5, pady=3)
        get_node_data = tk.Button(text="Get Rating", command=self.treeview.get_selected_value)
        get_node_data.pack(side=tk.LEFT, padx=5, pady=3)

        self.create_tooltip(self.combobox_1, "Select a CSV file to import")
        self.create_tooltip(self.scenario_box, "Choose 0 for Scenario Agnostic Ratings\nChoose a Steamroller Scenario for specific ratings")
        self.create_tooltip(self.textbox, "You may copy and paste valus from a CSV file in this box.")
        self.create_tooltip(self.treeview, "Generated combinations will be displayed here")
        
        # self.get_data_from_csv()
        self.update_grid_from_textbox()
        self.update_combobox_colors()
        self.root.mainloop()


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
            print(f"Scenario changed from {self.previous_value} to {new_value}\nLOADING NEW SCENARIO DATA\n")
            self.previous_value = new_value
            self.update_grid_from_textbox()


    def get_csv_files(self):
        files = [f[:-4] for f in os.listdir(self.directory) if f.endswith('.csv')]
        print(f"CSV files found in {self.directory}: {files}")
        return files

    ####################
    # DB Fill/Save Funcs
    ####################

    def select_team_names(self):
        sql = 'select team_name from teams'
        teams = self.db_manager.query_sql(sql)
        team_names = [t[0] for t in teams]
        if not team_names:
            team_names = ['No teams Found']
        self.combobox_1['values'] = team_names
        self.combobox_2['values'] = team_names

    def load_grid_data_from_db(self):
        team_1 = self.combobox_1.get()
        team_2 = self.combobox_2.get()
        scenario_id = int(self.scenario_box.get()[:1])

        team_sql_template = "select team_id from teams where team_name='{team_name}'"
        team_1_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_1))
        team_1_id = team_1_row[0][0]

        team_2_row = self.db_manager.query_sql(team_sql_template.format(team_name=team_2))
        team_2_id = team_2_row[0][0]

        if team_1_id > team_2_id:
            team_1_id, team_2_id = team_2_id, team_1_id

        player_sql_template = "select player_id, player_name from players where team_id={team_id} order by player_id"
        team_1_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_1_id))
        team_2_players = self.db_manager.query_sql(player_sql_template.format(team_id=team_2_id))

        team_1_dict = {row[0]:{'position':i+1,'name':row[1]} for i,row in enumerate(team_1_players)}
        team_2_dict = {row[0]:{'position':i+1,'name':row[1]}for i,row in enumerate(team_2_players)}
        print(team_1_dict)
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
        print(ratings_rows)
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

                self.db_manager.upsert_rating(
                    player_id_1=team_1_player_id,
                    player_id_2=team_2_player_id,
                    team_id_1=team_1_id,
                    team_id_2=team_2_id,
                    scenario_id=scenario_id,
                    rating=rating
                )


    #############################################


    def clear_textbox(self):
        self.textbox.config(state=tk.NORMAL)
        self.textbox.delete(1.0, tk.END)

    def update_textbox(self): # THIS NEEDS TO BE UPDATED TO ACCOMODATE SCENARIO STUFF.
        has_values = any(entry.get() for row in self.grid_entries for entry in row)
        self.textbox.config(state=tk.NORMAL)
        self.textbox.delete(1.0, tk.END)
        if has_values:
            for row in self.grid_entries:
                row_values = [entry.get().strip() for entry in row]
                if any(row_values):
                    self.textbox.insert(tk.END, ', '.join(row_values) + '\n')
        self.textbox.config(state=tk.NORMAL)


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

    def get_data_from_csv(self):
        try:
            file_name = self.combobox_1.get()
            if not file_name:
                raise ValueError("No file selected")

            file_path = os.path.join(self.directory, file_name + '.csv')

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} does not exist")

            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                content = '\n'.join([','.join(row) for row in reader])
            # if self.print_output:print(content)
            self.textbox.delete(1.0, tk.END)
            self.textbox.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_textbox_content(self):
        file_path = filedialog.asksaveasfilename(initialdir=self.directory, defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        content = self.textbox.get(1.0, tk.END).strip()
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            for line in content.split('\n'):
                writer.writerow(line.split(','))
        self.get_csv_files()

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
            print("Sorting...")
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

    def update_grid(self,rows,row_lo,row_hi,row_correction):
        for r, row in enumerate(rows):
            values = row.split(',')
            for c, value in enumerate(values):
                if c < 6:
                    if r < 6:
                        self.grid_entries[r][c].set(value)
                    if row_lo <= r < row_hi:
                        corrected_r = r - row_correction
                        if corrected_r < 6:
                            self.grid_entries[corrected_r][c].set(value)
                            # if self.print_output: print(f"r: {r}; row_correction: {row_correction}; sum: {corrected_r}; c is: {c}; value: {value}")

    def update_grid_from_textbox(self): 
        content = self.textbox.get(1.0, tk.END).strip()
        rows = content.split('\n')
        current_scenario = self.get_scenario_num()
        row_lo, row_hi = self.get_row_range()
        row_correction = current_scenario * 6
        self.update_grid(rows,row_lo,row_hi,row_correction)

    def validate_grid_data(self):
        for row in range(1, 6):
            for col in range(1, 6):
                value = self.grid_entries[row][col].get()
                if value not in ['1', '2', '3', '4', '5']:
                    messagebox.showerror("Error", f"Invalid rating at row {row+1}, column {col+1}. Ratings should be between 1 and 5.")
                    return False
        return True

    def validate_textbox_data(self):
        content = self.textbox.get(1.0, tk.END).strip()
        rows = content.split('\n')
        if len(rows) != 6:
            messagebox.showerror("Error", "Invalid number of rows in textbox. Expected 6 rows.")
            return False
        for row in rows:
            if len(row.split(',') != 6):
                messagebox.showerror("Error", "Invalid number of columns in textbox. Expected 6 columns per row.")
                return False
        return True

    def save_grid_state(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            for row in self.grid_entries:
                writer.writerow([entry.get() for entry in row])

    def load_grid_state(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            for r, row in enumerate(reader):
                for c, value in enumerate(row):
                    if r < 6 and c < 6:
                        self.grid_entries[r][c].set(value)

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
