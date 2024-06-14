import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
from itertools import combinations, permutations

# BETA COPY FROM pairings_debug.py WORKING AS OF 20240614
# WRITTEN AND TESTED BY DANIEL P. RAVEN & MATT RUSSELL

class LazyTreeview(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master)
        
        self.tree = ttk.Treeview(self, **kwargs)
        self.tree.grid(row=0, column=0, sticky='nsew')
        
        self.vsb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=self._on_yscroll, xscrollcommand=self._on_xscroll)
        
        self.vsb_visible = False
        self.hsb_visible = False
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tree.bind('<Configure>', self._update_scrollbars)

        self.tree.bind('<<TreeviewOpen>>', self.on_open)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<<TreeviewClose>>', self.on_close)

    def _on_yscroll(self, *args):
        self.vsb.set(*args)
        self._toggle_scrollbar(self.vsb, 'y', *args)

    def _on_xscroll(self, *args):
        self.hsb.set(*args)
        self._toggle_scrollbar(self.hsb, 'x', *args)

    def _toggle_scrollbar(self, scrollbar, orient, *args):
        if float(args[1]) - float(args[0]) < 1.0:
            if orient == 'y' and not self.vsb_visible:
                self.vsb.grid(row=0, column=1, sticky='ns')
                self.vsb_visible = True
            elif orient == 'x' and not self.hsb_visible:
                self.hsb.grid(row=1, column=0, sticky='ew')
                self.hsb_visible = True
        else:
            if orient == 'y' and self.vsb_visible:
                self.vsb.grid_remove()
                self.vsb_visible = False
            elif orient == 'x' and self.hsb_visible:
                self.hsb.grid_remove()
                self.hsb_visible = False

    def _update_scrollbars(self, event):
        self.tree.update_idletasks()
        self._toggle_scrollbar(self.vsb, 'y', *self.tree.yview())
        self._toggle_scrollbar(self.hsb, 'x', *self.tree.xview())

    def on_open(self, event):
        item = self.tree.focus()
        if print_output:
            print(f"Opened {item}")
        if not self.tree.get_children(item):
            self.populate_tree(item)

    def on_select(self, event):
        item = self.tree.focus()
        if print_output:
            print(f"Selected {item}")
                
    def on_close(self, event):
        item = self.tree.focus()
        if print_output:
            print(f"Closed {item}")
        
    def populate_tree(self, parent=''):
        for i in range(6):
            node_id = self.tree.insert(parent, 'end', text=f"Node {parent}-{i}")
            self.tree.insert(node_id, 'end')
            
    def show_info(self):
        item = self.tree.focus()
        messagebox.showerror("NODE INFO", item)
        print(self.tree.selection()[0])
        
    def get_item(self):
        item = self.tree.selection()[0]
        return item
    
    def get_item_details(self):
        item = self.tree.selection()[0]
        text = self.tree.item(item, option="text")
        value = self.tree.item(item, option="value")
        details = {text, value[0]}
        print(details)
        return details
        
    def get_selected_value(self):
        item = self.tree.selection()[0]
        value = self.tree.item(item, option="value")
        print(value[0])
        return value
        
    def item_details(self):
        item = self.tree.selection()[0]
        print(f"item id = {item}")
        details = {item}
        print(set(item))
        
    def show_selection(self):
        item = self.tree.selection()[0]
        text = self.tree.item(item, option="text")
        details = self.tree.item(item, option="value")
        messagebox.showinfo(message=text, title="Selection")
        messagebox.showinfo(message=details, title="details")

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

def update_combobox(combobox, directory):
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

def clear_grid(grid_entries):
    try:
        if not grid_entries:
            raise ValueError("The Grid is not populated")
        for row in range(0, 6):
            for col in range(0, 6):
                grid_entries[row][col].set("")
        update_grid_colors(grid_entries, color_map)
    except Exception as e:
        messagebox.showerror("Error", str(e))

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

def update_grid_colors(grid_entries, color_map):
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
        grid_widgets[row][col].config(bg='white')

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
        update_grid_colors(grid_entries, color_map)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def save_textbox_content(textbox, directory):
    try:
        file_path = filedialog.asksaveasfilename(initialdir=directory, defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return

        content = textbox.get(1.0, tk.END).strip()
        if not content:
            raise ValueError("No Data found in TextBox")
        else:    
            with open(file_path, 'w', newline='') as file:
                writer = csv.writer(file)
                for line in content.split('\n'):
                    writer.writerow(line.split(','))
        get_csv_files(directory)
    except Exception as e:
        messagebox.showerror("Error", str(e))
    

def prep_names():
    fNames = [grid_entries[i][0].get() for i in range(1, 6)]
    oNames = [grid_entries[0][i].get() for i in range(1, 6)]
    fRatings = {fNames[i]: {oNames[j]: grid_entries[i+1][j+1].get() for j in range(5)} for i in range(5)}
    oRatings = {oNames[i]: {fNames[j]: grid_entries[j+1][i+1].get() for j in range(5)} for i in range(5)}
    return fNames, oNames, fRatings, oRatings

def generate_combinations(fNames, oNames, fRatings, oRatings, treeview, sort_alpha):
    treeview.tree.delete(*treeview.tree.get_children())
    # tree_top = treeview.tree.insert("", 'end', text=f"Pairings")
    fNames_sorted = sorted(fNames, key=lambda x: x) if sort_alpha else fNames
    oNames_sorted = sorted(oNames, key=lambda x: x) if sort_alpha else oNames
    
    for name in fNames_sorted:
        fnames_filtered = [x for x in fNames_sorted if x!=name]
        # print(f"Top Level: {name} in {fNames_sorted}")
        generate_nested_combinations(name,fnames_filtered, oNames_sorted, fRatings, oRatings, treeview.tree, "", sort_alpha)
        fNames_sorted[:] = cycle_list(fNames_sorted)
        # oNames_sorted[:] = cycle_list(oNames_sorted)
        
        
def generate_nested_combinations(first_fName, fNames, oNames, fRatings, oRatings, treeview, parent, sort_alpha):

    first_oName = oNames[0]
    combs = list(combinations(oNames, 2))
    if oNames and not combs:
        combs = list(combinations([first_oName,first_oName], 2))
    combs_sorted = sorted(combs, key=lambda x: (x[0], x[1])) if sort_alpha else combs
    
    for comb in combs_sorted:
        rating_0 = fRatings[first_fName].get(comb[0], 'N/A')
        rating_1 = fRatings[first_fName].get(comb[1], 'N/A')
        
        item_id = treeview.insert(parent, 'end', text=f"{first_fName} vs {comb[0]} ({rating_0}/5) OR {comb[1]} ({rating_1}/5)", values=fNames, tags=maximum(rating_0, rating_1))
        
        if fNames:
            # print(f"Remaining Names: {remaining_fNames}")
            checkpoint_2 = 0
            opponent_perms = list(permutations(comb, 2))
            for opponent, next_fName in opponent_perms:
                
                nested_oNames = [name for name in oNames if name != opponent and name!=next_fName]
                nested_fNames = [name for name in fNames if name != first_fName]
                
                child_id = treeview.insert(item_id, 'end', text=f"{opponent} rating {fRatings[first_fName].get(opponent)}", values=opponent, tags=fRatings[first_fName].get(opponent))
                
                generate_nested_combinations(next_fName, nested_oNames, fNames, oRatings, fRatings, treeview, child_id, sort_alpha)
        
def maximum(a, b):
    return a if a >= b else b

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
        if len(row.split(',') != 6):
            messagebox.showerror("Error", "Invalid number of columns in textbox. Expected 6 columns per row.")
            return False
    return True

def save_grid_state(grid_entries): # SAVES THE CONTENTS OF THE GRID TO A CSV FILE
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if not file_path:
        return

    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in grid_entries:
            writer.writerow([entry.get() for entry in row])
    update_grid_colors(grid_entries, color_map)

def load_grid_state(grid_entries, combobox, textbox):
    try:
        file_name = combobox.get()
        if not file_name:
            file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if not file_path:
                raise ValueError("Invalid File Path")

            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                for r, row in enumerate(reader):
                    for c, value in enumerate(row):
                        if r < 6 and c < 6:
                            grid_entries[r][c].set(value)
        else:
            file_path = os.path.join(directory, file_name + '.csv')
            if not file_path:
                raise ValueError("Invalid File Path")
            
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                for r, row in enumerate(reader):
                    for c, value in enumerate(row):
                        if r < 6 and c < 6:
                            grid_entries[r][c].set(value)

        copy_grid_to_textbox(combobox, textbox)
        update_grid_colors(grid_entries, color_map)
        
    except Exception as e:
        messagebox.showerror("Error", str(e))
    
    

def copy_grid_to_textbox(combobox, textbox):
    try:
        file_name = combobox.get()
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
    update_grid_colors(grid_entries, color_map)
    

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
    return ratings

def cycle_list(lst):
    return lst[1:] + lst[:1]

def create_ui():
    
    global grid_entries, grid_widgets, print_output, color_map, directory
    color_map = {
        '1': 'orangered',
        '2': 'orange',
        '3': 'yellow',
        '4': 'yellowgreen',
        '5': 'deepskyblue'
    }
    # directory = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
    # print(f"GETTING CWD: {os.getcwd()}")
    directory = os.getcwd()
    # directory = '.'
    print_output = False
    if print_output:
        print(f"GETTING CWD: {directory}")
    

    root = tk.Tk()
    root.geometry('+0+0')
    root.title('Pairings Debug')
    if print_output:
        print(f"TKINTER VERSION: {tk.TkVersion}")
    

    root.bind('<Escape>', lambda event: root.quit())
    root.bind('<Return>', lambda event: on_generate_combinations())

    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X)

    left_frame = tk.Frame(top_frame)
    left_frame.pack(side=tk.LEFT, padx=10, pady=10)

    right_frame = tk.Frame(top_frame)
    right_frame.pack(side=tk.LEFT, padx=10, pady=10)

    bottom_frame = tk.Frame(root)
    bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    grid_entries = [[tk.StringVar() for _ in range(6)] for _ in range(6)]
    grid_widgets = [[None for _ in range(6)] for _ in range(6)]
    for r in range(6):
        for c in range(6):
            entry = tk.Entry(left_frame, textvariable=grid_entries[r][c], width=10)
            entry.grid(row=r+2, column=c, padx=5, pady=5)
            grid_widgets[r][c] = entry
            grid_entries[r][c].trace_add('write', lambda name, index, mode, var=grid_entries[r][c], row=r, col=c: update_color_on_change(var, index, mode, row, col, color_map))

    tk.Label(left_frame, text='Select File:').grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)
    combobox = ttk.Combobox(left_frame, state='readonly', width=20)
    combobox.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)
    update_combobox(combobox, directory)
    
    tk.Button(left_frame, text="Load From File", command=lambda: load_grid_state(grid_entries, combobox, textbox)).grid(row=8, column=2, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="Save Grid\nTo File", command=lambda: save_grid_state(grid_entries)).grid(row=8, column=3, padx=5, pady=5, sticky=tk.W)
    tk.Button(left_frame, text="Clear Grid", command=lambda: clear_grid(grid_entries)).grid(row=8, column=4, padx=5, pady=5, sticky=tk.W) # .pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(left_frame, text="Update Text", command=lambda: update_textbox(grid_entries, textbox)).grid(row=8, column=5, padx=5, pady=5, sticky=tk.W) # .pack(side=tk.LEFT, padx=5, pady=3)

    textbox = tk.Text(right_frame, width=60, height=7)
    textbox.pack(expand=1, fill='both')

    tk.Button(right_frame, text="IMPORT CSV\nTO TEXT", command=lambda: get_data_from_csv(combobox, textbox, directory)).pack(side=tk.LEFT, padx=5, pady=3) # grid(row=8, column=3, padx=5, pady=5, sticky=tk.W)
    tk.Button(right_frame, text="Update Grid", command=lambda: update_grid_from_textbox(textbox, grid_entries)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Clear Text", command=lambda: clear_textbox(textbox)).pack(side=tk.LEFT, padx=5, pady=3)
    tk.Button(right_frame, text="Save", command=lambda: save_textbox_content(textbox, directory)).pack(side=tk.LEFT, padx=5, pady=3)
    
    team_b = tk.IntVar()
    pairingLead = tk.Checkbutton(right_frame, text="Our team first", variable=team_b)
    pairingLead.pack(side=tk.BOTTOM, padx=5, pady=3)
    pairingLead.select()
    
    treeview = LazyTreeview(bottom_frame, columns=("Rating"))
    treeview.tree.heading("#0", text="Pairing")
    treeview.tree.heading("Rating", text="Rating")
    treeview.tree.tag_configure('1', background="orangered")
    treeview.tree.tag_configure('2', background="orange")
    treeview.tree.tag_configure('3', background="yellow")
    treeview.tree.tag_configure('4', background="yellowgreen")
    treeview.tree.tag_configure('5', background="deepskyblue")
    treeview.pack(expand=1, fill='both')

    sort_alpha = tk.IntVar()
    alphaBox = tk.Checkbutton(bottom_frame, text="Sort Pairings Alphabetically", variable=sort_alpha)
    alphaBox.pack(pady=5)
    alphaBox.select()

    def on_generate_combinations():
        fNames, oNames, fRatings, oRatings = prep_names()
        if print_output:
            print(f"fRatings: {fRatings}\n")
            print(f"oRatings: {oRatings}\n")
        validate_grid_data(grid_entries)
        if team_b.get():
            generate_combinations(fNames, oNames, fRatings, oRatings, treeview, sort_alpha=sort_alpha.get())
        else:
            generate_combinations(oNames, fNames, oRatings, fRatings, treeview, sort_alpha=sort_alpha.get())

    generateButton = tk.Button(bottom_frame, text="Generate Combinations", command=on_generate_combinations)
    generateButton.pack(pady=10)
    show_info_button = tk.Button(text="Show Info", command=treeview.item_details)
    show_info_button.pack(padx=5, pady=3)
    update_colors_button = tk.Button(text="Update Colors", command=update_grid_colors(grid_entries, color_map))
    update_colors_button.pack(side=tk.LEFT, padx=5, pady=3)
    show_selection_button = tk.Button(text="Show Selection", command=treeview.show_selection)
    show_selection_button.pack(side=tk.LEFT, padx=5, pady=3)
    get_node_data = tk.Button(text="Get Rating", command=treeview.get_selected_value)
    get_node_data.pack(side=tk.LEFT, padx=5, pady=3)

    create_tooltip(combobox, "Select a CSV file to import")
    create_tooltip(textbox, "Enter CSV data here")
    create_tooltip(treeview, "Generated combinations will be displayed here")
    
    # THIS SECTION USED TO PREPOPULATE THE APPLICATION WITH DATA ON LOAD. USED FOR TESTING.
    # get_data_from_csv(combobox, textbox, directory)
    # update_grid_from_textbox(textbox, grid_entries)
    update_grid_colors(grid_entries, color_map)
    # END PRE-POPULATION TESTING SECTION
    root.mainloop()

if __name__ == '__main__':
    create_ui()
