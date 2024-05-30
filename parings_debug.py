import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
from itertools import combinations

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
    # Get the list of all .csv files in the specified directory
    files = [f[:-4] for f in os.listdir(directory) if f.endswith('.csv')]
    print(f"CSV files found in {directory}: {files}")  # Debug statement
    return files

def select_directory_and_update_combobox(combobox):
    # Open a directory selection dialog
    directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
    if directory:
        # Update the combobox with .csv file names from the selected directory
        csv_files = get_csv_files(directory)
        combobox['values'] = csv_files
        if not csv_files:
            combobox.set("No CSV files found")
        else:
            combobox.set(csv_files[0])
            
def get_data_from_csv(combobox,textbox):
    # Open a directory selection dialog
    directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
    if directory:
        # Update the combobox with .csv file names from the selected directory
        csv_files = get_csv_files(directory)
    # messagebox.showinfo(title="csv files", message=f"{csv_files}")
    
    # Get the selected CSV file name from the combobox
    file_name = combobox.get()
    file_path = directory+'/'+file_name+'.csv'
    
    # Clear the existing text in the textbox
    textbox.config(state=tk.NORMAL)
    textbox.delete(1.0, tk.END)
    
    try:
        with open(file_path, newline='') as csvfile:
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                textbox.insert(tk.END, ','.join(row) + '\n')
    except FileNotFoundError:
        messagebox.showerror("File Not Found", f"The file named '{file_name}' does not exist in directory: {directory}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    
    messagebox.showinfo(title="Import Successful!", message=f"Matchup Data imported from {file_name}")
    textbox.config(state=tk.NORMAL)

def load_csv_to_grid(combobox, grid_entries):
    # Get the selected file name from the combobox
    selected_file = combobox.get()
    if not selected_file:
        messagebox.showerror("Error", "No file selected")
        return

    # Assuming the directory was set during the combobox population
    directory = filedialog.askdirectory()
    if not directory:
        
        messagebox.showerror("Error", "No directory selected")
        return

    file_path = os.path.join(directory, selected_file + '.csv')
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"{file_path} does not exist")
        return

    # Load the CSV file and populate the grid
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for r, row in enumerate(reader):
            for c, value in enumerate(row):
                if r < len(grid_entries) and c < len(grid_entries[r]):
                    grid_entries[r][c].set(value)

def clear_textbox(textbox):
    textbox.config(state=tk.NORMAL)
    textbox.delete(1.0, tk.END)  # Clear the textbox

def update_textbox(grid_entries, textbox):
    # Check if the grid has any values
    has_values = any(entry.get() for row in grid_entries for entry in row)
    textbox.config(state=tk.NORMAL)
    textbox.delete(1.0, tk.END)  # Clear the textbox
    if has_values:
        for row in grid_entries:
            row_values = [entry.get().strip() for entry in row]
            if any(row_values):
                textbox.insert(tk.END, ', '.join(row_values) + '\n')
    textbox.config(state=tk.NORMAL)

def update_grid(textbox, grid_entries):
    # Get the text from the textbox
    text = textbox.get("1.0", tk.END).strip()
    
    # Split the text into lines
    lines = text.split('\n')
    
    # Loop through the lines and split each line by comma
    for r, line in enumerate(lines):
        values = line.split(',')
        # Ensure we have exactly 6 values per line for the grid
        values = [v.strip() for v in values[:6]]
        for c, value in enumerate(values):
            # Update the grid_entries with the values
            grid_entries[r][c].set(value)

def update_combobox_colors(grid_entries):
    color_map = {
        '1': 'light blue',
        '2': 'green',
        '3': 'yellow',
        '4': 'orange',
        '5': 'red'
    }
    for row in range(6):
        for col in range(6):
            if row == 0 or col == 0:
                continue
            value = grid_entries[row][col].get()
            if value in color_map:
                widget = grid_entries[row][col].trace_info()[0][2]
                widget.config(background=color_map[value])

# Function to get opponent player names
def get_opponent_player_names():
    oNames = [grid_entries[0][col].get() for col in range(1, 6)]
    # messagebox.showinfo(title="Opponent's Names", message=f"{oNames}")
    return oNames

# Function to get friendly player names
def get_friendly_player_names():
    fNames = [grid_entries[row][0].get() for row in range(1, 6)]
    # messagebox.showinfo(title="Friendly Team Names", message=f"{fNames}")
    return fNames
    
# Function to generate combinations and populate Treeview
def generate_combinations(fNames, oNames, treeview):
    def generate_nested_combinations(fNames, oNames, parent=""):
        if not fNames:
            return

        first_fName = fNames[0]
        remaining_fNames = fNames[1:]

        combs = list(combinations(oNames, 2))
        combs_sorted = sorted(combs, key=lambda x: (x[0], x[1]))

        for comb in combs_sorted:
            item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} OR {comb[1]}")
            item_id = treeview.insert(parent, 'end', text=f"{comb[0]}")
            item_id = treeview.insert(parent, 'end', text=f"{comb[1]}")
            if remaining_fNames:
                for opponent in comb:
                    nested_oNames = [name for name in oNames if name != opponent]
                    # messagebox.showinfo(title="Current Loop: nested_oNames", message=f"{nested_oNames}")
                    generate_nested_combinations(remaining_fNames, nested_oNames, item_id)

    treeview.delete(*treeview.get_children())  # Clear the treeview

    fNames_sorted = sorted(fNames, key=lambda x: x)
    oNames_sorted = sorted(oNames, key=lambda x: x)

    generate_nested_combinations(fNames_sorted, oNames_sorted)

# BACKUP OF OLD TEXT BASED PRINT OUT    
def generate_combinations_old(fNames, oNames, textbox_bottom):
    def generate_nested_combinations_old(fNames, oNames, depth=0):
        if not fNames:
            return ""
        
        # Extract the first friendly player
        first_fName = fNames[0]
        remaining_fNames = fNames[1:]
        
        # Generate combinations for the first friendly player
        combs = list(combinations(oNames, 2))
        combs_sorted = sorted(combs, key=lambda x: (x[0], x[1]))
        
        result = ""
        indent = "\t" * depth
        
        for comb in combs_sorted:
            result += f"{indent}{first_fName} vs {comb[0]} OR {comb[1]}\n"
            if remaining_fNames:
                for opponent in comb:
                    nested_oNames = [name for name in oNames if name != opponent]
                    nested_result = generate_nested_combinations(remaining_fNames, nested_oNames, depth + 1)
                    if nested_result:
                        result += f"{indent}\tvs {opponent}\n"
                        result += nested_result
                        
        return result

    
def create_ui():
    # Initialize the main window
    root = tk.Tk()
    root.title("Pairing Application")
    
    # Set the window to fullscreen
    # root.state('zoomed')  # For Windows
    # Uncomment the following line for macOS/Linux
    # root.attributes('-fullscreen', True)
    
    # Create a frame for the top section
    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    # Add a combobox for dropdown
    combobox1 = ttk.Combobox(top_frame)
    combobox1.pack(side=tk.LEFT, padx=5)

    # Add a "Lists" button
    tk.Button(top_frame, text="UPDATE", command=lambda: select_directory_and_update_combobox(combobox1)).pack(side=tk.LEFT, padx=5)
    tk.Button(top_frame, text="IMPORT", command=lambda: get_data_from_csv(combobox1,textbox)).pack(side=tk.LEFT, padx=5)

    # Add a label and text widget for file format
    tk.Label(top_frame, text="REMINDER: CSV File format:").pack(side=tk.LEFT, padx=5)
    textbox = tk.Text(top_frame, height=6, wrap=tk.NONE)
    textbox.pack(side=tk.LEFT, padx=5)
    for item in ["EnemyTeam1,Tim Boss,Wout Maerschalck,Bennep,Davy Smets,Laurens Tanguy",
        "Dan,1,2,3,4,5", 
        "Andy,2,3,4,5,1", 
        "Erica,3,4,5,1,2", 
        "Paul,5,4,3,2,1", 
        "Pete,4,5,1,2,3"]:
        textbox.insert(tk.END, item + '\n')
    textbox.config(state=tk.NORMAL)
    tk.Button(top_frame, text="Update Top Box", command=lambda: update_textbox(grid_entries, textbox)).pack(side=tk.BOTTOM, padx=5, pady=3)
    tk.Button(top_frame, text="Move to Grid", command=lambda: update_grid(textbox, grid_entries)).pack(side=tk.BOTTOM, padx=5, pady=3)
    tk.Button(top_frame, text="Toggle Highlights", command=lambda: update_combobox_colors(grid_entries)).pack(side=tk.BOTTOM, padx=5, pady=3)
    tk.Button(top_frame, text="Clear Texbox", command=lambda: clear_textbox(textbox)).pack(side=tk.BOTTOM, padx=5, pady=3)

    # Create a frame for the combobox grid
    combo_grid_frame = tk.Frame(root)
    combo_grid_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    # Create a list to hold references to StringVars for each grid entry
    global grid_entries
    grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
    
    # Add a grid of comboboxes
    for row in range(6):
        for col in range(6):
            if row == 0 or col == 0:
                entry = ttk.Entry(combo_grid_frame, textvariable=grid_entries[row][col])
                entry.grid(row=row, column=col, padx=5, pady=5)
                continue
            combobox = ttk.Combobox(combo_grid_frame, textvariable=grid_entries[row][col], values=[1, 2, 3, 4, 5])
            combobox.grid(row=row, column=col, padx=5, pady=5)
            # Add a trace to update the color whenever the value changes
            grid_entries[row][col].trace_add('write', lambda *args: update_combobox_colors(grid_entries))

    # Add a "Help" label with tooltip
    help_text = (
        "Fill in the table at the top right with the names of the players (your team on the left) and the scores from 1 to 5. "
        "The lower your score, the better you think you are in the match.\n\n"
        "Check the box for the first player or not depending on which team starts, then click on generate to create the corresponding pairing tree.\n\n"
        "Here, you need to start thinking, and start from the principle that according to your pairings, the opponent will do the best possible thing for him and the worst for you.\n\n"
        "So, for example, if you are first (you start the pairing first) you need to choose the player with the lowest maximum score (assuming that the opponent will necessarily choose that score).\n\n"
        "Your opponent then puts in 2 players, you open the corresponding tree and choose from the 2 choices the one with the least weight (which is the one that suits you best).\n\n"
        "Then you put 2 players on the remaining opponent, to choose them you look for the pair with the least possible weight as this is your best tree. Continue like this until the end of the pairing. "
        "Click on a node to display all the info of the chosen matches before that node on the right."
    )
    help_label = tk.Label(root, text="Help (hover)")
    help_label.pack(side=tk.TOP, pady=5)
    ToolTip(help_label, help_text)
    
    # Add a checkbox for "First team"
    check_var = tk.IntVar()
    tk.Checkbutton(root, text="First team", variable=check_var).pack(side=tk.TOP, pady=5)
    
    # Add an entry and label for "Penalty pairing at 5"
    penalty_frame = tk.Frame(root)
    penalty_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    tk.Label(penalty_frame, text="Penalty pairing at 5").pack(side=tk.LEFT, padx=5)
    tk.Entry(penalty_frame, width=5).pack(side=tk.LEFT, padx=5)
    
    # Create a frame for the bottom buttons
    bottom_frame = tk.Frame(root)
    
    # Create an area to display the results of the matchup grid.
    tk.Label(bottom_frame, text="Matchup Planner").pack(side=tk.TOP, padx=5)    
    # Create Treeview widget
    treeview = ttk.Treeview(bottom_frame)
    treeview.pack(fill=tk.BOTH, expand=True)
        
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
    
    # Add the buttons
    tk.Button(bottom_frame, text="Save").pack(side=tk.LEFT, padx=5)
    tk.Button(bottom_frame, text="Generate", command=lambda: generate_combinations(get_friendly_player_names(), get_opponent_player_names(), treeview)).pack(side=tk.LEFT, padx=5)
    tk.Button(bottom_frame, text="Clear Texbox", command=lambda: treeview.delete(*treeview.get_children())).pack(side=tk.LEFT, padx=5)
    
    # Automatically populate the grid with default entries for testing purposes.    
    update_grid(textbox, grid_entries)
    
    # Set up the drop down to select list csv files when the program loads.
    select_directory_and_update_combobox(combobox1)
    
    # Run the main loop
    root.mainloop()

if __name__ == "__main__":
    create_ui()
