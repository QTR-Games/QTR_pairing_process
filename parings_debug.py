import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
from itertools import combinations

class LazyTreeview(ttk.Treeview):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind('<<TreeviewOpen>>', self.on_open)

    def on_open(self, event):
        item = self.focus()
        if not self.get_children(item):
            self.populate_tree(item)

    def populate_tree(self, parent=''):
        for i in range(5):
            node_id = self.insert(parent, 'end', text=f"Node {parent}-{i}")
            self.insert(node_id, 'end')

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         wraplength=300)
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

def get_csv_files(directory):
    files = [f[:-4] for f in os.listdir(directory) if f.endswith('.csv')]
    print(f"CSV files found in {directory}: {files}")
    return files


def select_directory_and_update_combobox(combobox):
    directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
    if directory:
        csv_files = [f[:-4] for f in os.listdir(directory) if f.endswith('.csv')]
        combobox['values'] = csv_files
        if not csv_files:
            combobox.set("No CSV files found")
        else:
            combobox.set(csv_files[0])

def clear_textbox(textbox):
    textbox.config(state=tk.NORMAL)
    textbox.delete(1.0, tk.END)

def update_textbox(grid_entries, textbox):
    has_values = any(entry.get() for row in grid_entries for entry in row)
    textbox.config(state=tk.NORMAL)
    textbox.delete(1.0, tk.END)
    if has_values:
        for row in grid_entries:
            row_values = [entry.get().strip() for entry in row]
            if any(row_values):
                textbox.insert(tk.END, ', '.join(row_values) + '\n')
    textbox.config(state=tk.NORMAL)


def update_combobox_colors(grid_entries):
    color_map = {
        '1': 'lightblue',
        '2': 'lightgreen',
        '3': 'yellow',
        '4': 'orange',
        '5': 'red'
    }

    for row in range(1, 6):
        for col in range(1, 6):
            value = grid_entries[row][col].get()
            if value in color_map:
                grid_widgets[row][col].config(bg=color_map[value])
                
def update_color_on_change(var, index, mode, row, col):
    color_map = {
        '1': 'lightblue',
        '2': 'lightgreen',
        '3': 'yellow',
        '4': 'orange',
        '5': 'red'
    }
    value = var.get()
    if value in color_map:
        grid_widgets[row][col].config(bg=color_map[value])
    else:
        grid_widgets[row][col].config(bg='white')  # Default to white if no matching value

def get_data_from_csv(combobox, textbox):
    try:
        file_name = combobox.get()
        if not file_name:
            raise ValueError("No file selected")

        directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
        file_path = os.path.join(directory, file_name + '.csv')

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist")

        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            content = '\n'.join([','.join(row) for row in reader])

        textbox.delete(1.0, tk.END)
        textbox.insert(tk.END, content)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def save_textbox_content(textbox):
    directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
    file_path = filedialog.asksaveasfilename(initialdir=directory, defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if not file_path:
        return

    content = textbox.get(1.0, tk.END).strip()
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for line in content.split('\n'):
            writer.writerow(line.split(','))

def generate_combinations(fNames, oNames, treeview, sort_alpha, first_team):
    treeview.delete(*treeview.get_children()) # clear anything in the tree from a previous run.
    # if sorting enabled, sort the names.
    fNames_sorted = sorted(fNames, key=lambda x: x) if sort_alpha else fNames #sorting
    oNames_sorted = sorted(oNames, key=lambda x: x) if sort_alpha else oNames #sorting
    generate_nested_combinations(fNames_sorted, oNames_sorted) #loop
    
def generate_nested_combinations(fNames, oNames, parent=""):
    if not fNames:
        return
    
    extract_ratings(direction)

    first_fName = fNames[0]
    remaining_fNames = fNames[1:]
    #first_oName = oNames[0]
    #remaining_oNames = oNames[1:]
    combs = list(combinations(oNames, 2))
    combs_sorted = sorted(combs, key=lambda x: (x[0], x[1]))
    
    extract_ratings_team_b()
    
    #print(f"direction {first_team.get()}")
    print(f"direction is 1? - {direction}")
    #print(f"GOING FIRST")
    
    
    for comb in combs_sorted:
        rating_0 = ratings[first_fName].get(comb[0], 'N/A')
        rating_1 = ratings[first_fName].get(comb[1], 'N/A')
        item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)")
        if remaining_fNames:
            for opponent in comb:
                child_id = treeview.insert(item_id, 'end', text=f"{opponent} rating {ratings[first_fName].get(opponent)}", values=ratings[first_fName].get(opponent))
                nested_oNames = [name for name in oNames if name != opponent]
                generate_nested_combinations(remaining_fNames, oNames, child_id)

def update_grid_from_textbox(textbox, grid_entries):
    # validate_grid_data(grid_entries)
    content = textbox.get(1.0, tk.END).strip()
    rows = content.split('\n')
    for r, row in enumerate(rows):
        values = row.split(',')
        for c, value in enumerate(values):
            if r < 6 and c < 6:
                grid_entries[r][c].set(value)
                
def validate_grid_data(grid_entries):
    for row in range(1, 6):
        for col in range(1, 6):
            value = grid_entries[row][col].get()
            if value not in ['1', '2', '3', '4', '5']:
                messagebox.showerror("Error", f"Invalid rating at row {row+1}, column {col+1}. Ratings should be between 1 and 5.")
                return False
    return True

def validate_textbox_data(textbox):
    content = textbox.get(1.0, tk.END).strip()
    rows = content.split('\n')
    if len(rows) != 6:
        messagebox.showerror("Error", "Invalid number of rows in textbox. Expected 6 rows.")
        return False
    for row in rows:
        if len(row.split(',')) != 6:
            messagebox.showerror("Error", "Invalid number of columns in textbox. Expected 6 columns per row.")
            return False
    return True

def save_grid_state(grid_entries):
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if not file_path:
        return

    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in grid_entries:
            writer.writerow([entry.get() for entry in row])

def load_grid_state(grid_entries):
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if not file_path:
        return

    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for r, row in enumerate(reader):
            for c, value in enumerate(row):
                if r < 6 and c < 6:
                    grid_entries[r][c].set(value)

# Adding tooltips (using a simple function)
def create_tooltip(widget, text):
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

def get_opponent_player_names():
    return [grid_entries[0][col].get() for col in range(1, 6)]

def get_friendly_player_names():
    return [grid_entries[row][0].get() for row in range(1, 6)]

def extract_ratings_team_a():
    ratings_a = {}
    fNames = get_friendly_player_names()
    oNames = get_opponent_player_names()
    for row in range(1, 6):
        player = grid_entries[row][0].get()
        ratings_a[player] = {}
        for col in range(1, 6):
            opponent = grid_entries[0][col].get()
            rating = int(grid_entries[row][col].get())
            ratings_a[player][opponent] = rating
    print(f"{ratings_a}")
    return ratings_a

def extract_ratings_team_b():
    ratings_b = {}
    fNames = get_friendly_player_names()
    oNames = get_opponent_player_names()
    for col in range(1, 6):
        player = grid_entries[0][col].get()
        ratings_b[player] = {}
        for row in range(1, 6):
            opponent = grid_entries[row][0].get()
            rating = int(grid_entries[row][col].get())
            ratings_b[player][opponent] = rating
    print(f"{ratings_b}")
    return ratings_b

def extract_ratings(direction):
    fNames = get_friendly_player_names()
    oNames = get_opponent_player_names()
    ratings_a = {fNames[i]: {oNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
    ratings_b = {oNames[i]: {fNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}


def create_ui():
    global grid_entries, grid_widgets, print_ratings, direction, ratings
    print_ratings = True
    # ratings = {}
    root = tk.Tk()
    root.geometry('+0+0')  # Set the window position to top-left corner
    root.title('Parings Debug')

    # Define frames for layout
    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X)

    left_frame = tk.Frame(top_frame)
    left_frame.pack(side=tk.LEFT, padx=10, pady=10)

    right_frame = tk.Frame(top_frame)
    right_frame.pack(side=tk.LEFT, padx=10, pady=10)

    bottom_frame = tk.Frame(root)
    bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Grid entries (left side)
    #tk.Label(left_frame, text="Friendly Team").grid(row=0, column=1, padx=5, pady=5)
    #tk.Label(left_frame, text="Opponent Team").grid(row=1, column=0, padx=5, pady=5)
    grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
    grid_widgets = [[None for _ in range(6)] for _ in range(6)]
    for r in range(6):
        for c in range(6):
            entry = tk.Entry(left_frame, textvariable=grid_entries[r][c], width=10)
            entry.grid(row=r+2, column=c, padx=5, pady=5)
            grid_widgets[r][c] = entry
            grid_entries[r][c].trace_add('write', lambda name, index, mode, var=grid_entries[r][c], row=r, col=c: update_color_on_change(var, index, mode, row, col))


    # Combobox and buttons (left side)
    tk.Label(left_frame, text='Select File:').grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)
    combobox = ttk.Combobox(left_frame, state='readonly', width=20)
    combobox.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)
    select_directory_and_update_combobox(combobox)
    
    # Adding labels for grid entries
    # tk.Label(left_frame, text="Friendly Team").grid(row=1, column=1, padx=5, pady=5)
    # tk.Label(left_frame, text="Opponent Team").grid(row=2, column=0, padx=5, pady=5)


    tk.Button(left_frame, text='UPDATE COLOR', command=lambda: update_combobox_colors(grid_entries)).grid(row=8, column=2, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="IMPORT", command=lambda: get_data_from_csv(combobox, textbox)).grid(row=8, column=3, padx=5, pady=5, sticky=tk.W)
    # Add buttons to save and load the grid state:
    tk.Button(left_frame, text="Load Grid", command=lambda: load_grid_state(grid_entries)).grid(row=8, column=4, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="Save Grid", command=lambda: save_grid_state(grid_entries)).grid(row=8, column=5, padx=5, pady=5, sticky=tk.W)
    
    # Textbox (right side)
    textbox = tk.Text(right_frame, width=60, height=7)
    textbox.pack(expand=1, fill='both')

    tk.Button(right_frame, text="Update Grid", command=lambda: update_grid_from_textbox(textbox, grid_entries)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Update Text", command=lambda: update_textbox(grid_entries, textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Clear Text", command=lambda: clear_textbox(textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Save", command=lambda: save_textbox_content(textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    
    first_team = tk.IntVar()
    pairingLead = tk.Checkbutton(right_frame, text="First team", variable=first_team)
    pairingLead.pack(side=tk.BOTTOM, padx=5, pady=3)
    pairingLead.select()
    direction = first_team.get()
    print(f"first team direction {direction}")
    
    # Treeview (bottom side)
    treeview = LazyTreeview(bottom_frame)
    treeview.pack(expand=1, fill='both')
    
    sort_alpha = tk.IntVar()
    tk.Checkbutton(bottom_frame, text="Sort Pairings Alphabetically", variable=sort_alpha).pack(pady=5)

    def on_generate_combinations():
        validate_grid_data(grid_entries)
        fNames = [grid_entries[i][0].get() for i in range(1, 6)]
        oNames = [grid_entries[0][i].get() for i in range(1, 6)]
        ratings_a = {fNames[i]: {oNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
        ratings_b = {oNames[i]: {fNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
        # ratings_a = extract_ratings_team_a()
        # ratings_b = extract_ratings_team_b()
        if print_ratings:
            print(f"Ratings A {ratings_a} \n\nRatings B {ratings_b} \n\n")
        generate_combinations(fNames, oNames, treeview, sort_alpha=sort_alpha.get(), first_team=first_team.get())

    tk.Button(bottom_frame, text="Generate Combinations", command=on_generate_combinations).pack(pady=10)

    create_tooltip(combobox, "Select a CSV file to import")
    create_tooltip(textbox, "Enter CSV data here")
    create_tooltip(treeview, "Generated combinations will be displayed here")
    
    get_data_from_csv(combobox, textbox)
    update_grid_from_textbox(textbox, grid_entries)
    update_combobox_colors(grid_entries)
    root.mainloop()

if __name__ == '__main__':
    create_ui()
