import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
import ctypes
from itertools import combinations

class LazyTreeview(ttk.Treeview):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind('<<TreeviewOpen>>', self.on_open)
        self.bind('<<TreeviewSelect>>', self.on_select)
        self.bind('<<TreeviewClose>>', self.on_close)

    def on_open(self, event):
        item = self.focus()
        print(f"Opened {item}")
        if not self.get_children(item):
            self.populate_tree(item)

    def on_select(self, event):
        item = self.focus()
        print(f"Selected {item}")
                
    def on_close(self, event):
        item = self.focus()
        print(f"Closed {item}")
        
    
    def populate_tree(self, parent=''):
        for i in range(5):
            node_id = self.insert(parent, 'end', text=f"Node {parent}-{i}")
            # print(node_id)
            self.insert(node_id, 'end')
            
    def show_info(self):
        item = self.focus()
        messagebox.showerror("NODE INFO", item)
        print(self.selection()[0])
        
    def get_item(self):
        item = self.selection()[0]
        return item
    
    def get_item_details(self):
        item = self.selection()[0]
        # Get and display the text of the selected item.
        text = self.item(item, option="text")
        value = self.item(item, option="value")
        details = {text,value[0]}
        print(details)
        return details
        
    def get_selected_value(self):
        item = self.selection()[0]
        # Get and display the text of the selected item.
        value = self.item(item, option="value")
        print(value[0])
        return value
        
    def item_details(self):
        item = self.selection()[0]
        print(f"item id = {item}")
        details = {item}
        print(set(item))
        
    def show_selection(self):
        item = self.selection()[0]
        # Get and display the text of the selected item.
        text = self.item(item, option="text")
        messagebox.showinfo(message=text, title="Selection")
        messagebox.showinfo(message=self.set(item), title="details")
        

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


def select_directory_and_update_combobox(combobox, directory):
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


def update_combobox_colors(grid_entries, color_map):
    for row in range(1, 6):
        for col in range(1, 6):
            value = grid_entries[row][col].get()
            if value in color_map:
                grid_widgets[row][col].config(bg=color_map[value])
                
def update_color_on_change(var, index, mode, row, col, color_map):
    value = var.get()
    if value in color_map:
        grid_widgets[row][col].config(bg=color_map[value])
    else:
        grid_widgets[row][col].config(bg='white')  # Default to white if no matching value

def get_data_from_csv(combobox, textbox, directory):
    try:
        file_name = combobox.get()
        if not file_name:
            raise ValueError("No file selected")

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

def save_textbox_content(textbox, directory):
    file_path = filedialog.asksaveasfilename(initialdir=directory, defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if not file_path:
        return

    content = textbox.get(1.0, tk.END).strip()
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for line in content.split('\n'):
            writer.writerow(line.split(','))

def generate_trees(fNames, oNames, fRatings,oRatings, treeview):
    treeview.delete(*treeview.get_children())
    tree_names = fNames
    for name in fNames:
        generate_combinations(tree_names, oNames, fRatings,oRatings, treeview)
        tree_names[:] = cycle_list(fNames)
        # generate_combinations(tree_names, oNames, fRatings,oRatings, treeview)
        # tree_names[:] = cycle_list(tree_names)
        # generate_combinations(tree_names, oNames, fRatings,oRatings, treeview)
        # tree_names[:] = cycle_list(tree_names)
        # generate_combinations(tree_names, oNames, fRatings,oRatings, treeview)
        # tree_names[:] = cycle_list(tree_names)
        # generate_combinations(tree_names, oNames, fRatings,oRatings, treeview)
    

def generate_combinations(fNames, oNames, fRatings,oRatings, treeview):

    # treeview.delete(*treeview.get_children())
    # tree_top = treeview.insert("", 'end', text=f"Pairings")
    # for name in fNames:
        # breakpoint()
    generate_nested_combinations(fNames, oNames, fRatings, oRatings, treeview,"")
    # fNames[:] = cycle_list(fNames)
    # oNames[:] = cycle_list(oNames)

def generate_nested_combinations(fNames, oNames, fRatings, oRatings, treeview,parent):
    if not fNames:
        return
    
    current_value = 0
    first_fName = fNames[0]
    remaining_fNames = fNames[1:]
    first_oName = oNames[0]
    remaining_oNames = oNames[1:]
    combs = list(combinations(oNames, 2))
    combs_sorted = sorted(combs, key=lambda x: (x[0], x[1]))
    
    for comb in combs_sorted:
        
        rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
        rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
        recommend = comb[1]+"@"+rating_1
        if rating_0 > rating_1:
            recommend = comb[0]+"@"+rating_0
        # item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=(f"{recommend}"))
        item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)")
        
        if remaining_fNames:
            
            for opponent in comb:
                current_value = current_value+int(fRatings[first_fName].get(opponent))
                child_id = treeview.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=current_value)
                
                # print(current_value)
                nested_oNames = [name for name in oNames if name != opponent]
                # nested_fNames = [name for name in fNames if name != first_fName]
                generate_nested_combinations(nested_oNames, remaining_fNames, oRatings, fRatings, treeview, child_id)
    
def sort_names(fNames, oNames, check_alpha):
    if check_alpha.get():
        print("Sorting...")
        fNames_sorted = sorted(fNames, key=lambda x: x)
        oNames_sorted = sorted(oNames, key=lambda x: x)
    else:
        fNames_sorted = fNames
        oNames_sorted = oNames
    return fNames_sorted, oNames_sorted
    
def update_grid_from_textbox(textbox, grid_entries):
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

def extract_ratings():
    ratings = {}
    fNames = get_friendly_player_names()
    oNames = get_opponent_player_names()
    for row in range(1, 6):
        player = grid_entries[row][0].get()
        ratings[player] = {}
        for col in range(1, 6):
            opponent = grid_entries[0][col].get()
            rating = int(grid_entries[row][col].get())
            ratings[player][opponent] = rating
    # print(f"{ratings}")
    return ratings

def cycle_list(lst):
    return lst[1:] + lst[:1]


def create_ui():
    global grid_entries, grid_widgets, print_ratings, color_map, directory
    print_ratings = True
    color_map = {
        '1': 'orangered',
        '2': 'orange',
        '3': 'yellow',
        '4': 'yellowgreen',
        '5': 'deepskyblue'
    }
    directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"

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
    grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
    grid_widgets = [[None for _ in range(6)] for _ in range(6)]
    for r in range(6):
        for c in range(6):
            entry = tk.Entry(left_frame, textvariable=grid_entries[r][c], width=10)
            entry.grid(row=r+2, column=c, padx=5, pady=5)
            grid_widgets[r][c] = entry
            grid_entries[r][c].trace_add('write', lambda name, index, mode, var=grid_entries[r][c], row=r, col=c: update_color_on_change(var, index, mode, row, col, color_map))


    # Combobox and buttons (left side)
    tk.Label(left_frame, text='Select File:').grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)
    combobox = ttk.Combobox(left_frame, state='readonly', width=20)
    combobox.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)
    select_directory_and_update_combobox(combobox, directory)
    
    # tk.Button(left_frame, text='UPDATE COLOR', command=lambda: update_combobox_colors(grid_entries,color_map)).grid(row=8, column=2, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="IMPORT CSV", command=lambda: get_data_from_csv(combobox, textbox, directory)).grid(row=8, column=3, padx=5, pady=5, sticky=tk.W)
    # Add buttons to save and load the grid state:
    tk.Button(left_frame, text="Load Grid", command=lambda: load_grid_state(grid_entries)).grid(row=8, column=4, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="Save Grid", command=lambda: save_grid_state(grid_entries)).grid(row=8, column=5, padx=5, pady=5, sticky=tk.W)
    
    # Textbox (right side)
    textbox = tk.Text(right_frame, width=60, height=7)
    textbox.pack(expand=1, fill='both')

    tk.Button(right_frame, text="Update Grid", command=lambda: update_grid_from_textbox(textbox, grid_entries)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Update Text", command=lambda: update_textbox(grid_entries, textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Clear Text", command=lambda: clear_textbox(textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Save", command=lambda: save_textbox_content(textbox, directory)).pack(side=tk.LEFT, padx=5, pady=3)
    
    team_b = tk.IntVar()
    pairingLead = tk.Checkbutton(right_frame, text="Our team first", variable=team_b)
    pairingLead.pack(side=tk.BOTTOM, padx=5, pady=3)
    pairingLead.select()
    
    # Treeview (bottom side)
    treeview = LazyTreeview(bottom_frame, columns=("Rating"))
    # treeview = ttk.Treeview(bottom_frame, columns=("Rating"))
    # treeview.heading("#0", text="Pairing")
    # treeview.heading("Rating", text="Rating & Node_Id")
    treeview.pack(expand=1, fill='both')
    
    
    
    sort_alpha = tk.IntVar()
    alphaBox = tk.Checkbutton(bottom_frame, text="Sort Pairings Alphabetically", variable=sort_alpha)
    alphaBox.pack(pady=5)
    # alphaBox.select()
    
    def on_generate_combinations():
        fNames = [grid_entries[i][0].get() for i in range(1, 6)]
        oNames = [grid_entries[0][i].get() for i in range(1, 6)]
        fRatings = {fNames[i]: {oNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
        oRatings = {oNames[i]: {fNames[j]: grid_entries[j+1][i+1].get() for j in range(5)} for i in range(5)}
        sorted_fNames, sorted_oNames = sort_names(fNames, oNames, sort_alpha)

        if print_ratings:
            print(f"fRatings: {fRatings}\n")
            print(f"oRatings: {oRatings}\n")
            print(f"fNames: {fNames}; sorted fNames: {sorted_fNames}")
            print(f"oNames: {oNames}; sorted oNames: {sorted_oNames}")
        validate_grid_data(grid_entries)
        # this uses the "OUR TEAM FIRST" checkbox to drive which team starts the pairing process.
        if team_b.get():
            generate_trees(sorted_fNames, sorted_oNames, fRatings, oRatings, treeview)
        else:
            generate_trees(sorted_oNames, sorted_fNames, oRatings, fRatings, treeview)

    generateButton = tk.Button(bottom_frame, text="Generate Combinations", command=on_generate_combinations)
    generateButton.pack(pady=10)
    show_info_button = tk.Button(text="Show Info", command=treeview.item_details)
    show_info_button.pack()
    show_selection_button = tk.Button(text="Show Selection", command=treeview.show_selection)
    show_selection_button.pack(side=tk.LEFT, padx=5, pady=3)
    get_node_data = tk.Button(text="Get Rating", command=treeview.get_selected_value)
    get_node_data.pack(side=tk.LEFT, padx=5, pady=3)
    

    create_tooltip(combobox, "Select a CSV file to import")
    create_tooltip(textbox, "Enter CSV data here")
    create_tooltip(treeview, "Generated combinations will be displayed here")
    
    get_data_from_csv(combobox, textbox, directory)
    update_grid_from_textbox(textbox, grid_entries)
    update_combobox_colors(grid_entries, color_map)
    root.mainloop()

if __name__ == '__main__':
    create_ui()
