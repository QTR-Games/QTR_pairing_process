import tkinter as tk
from tkinter import ttk, messagebox

class DeleteTeamDialog:
    def __init__(self, parent, team_names):
        self.top = tk.Toplevel(parent)
        self.top.title("Select Team to Delete")
        
        self.label = tk.Label(self.top, text="Choose a team to delete:")
        self.label.pack(pady=5)
        
        self.combobox = ttk.Combobox(self.top, values=team_names, state="readonly")
        self.combobox.pack(pady=5)
        
        self.delete_button = tk.Button(self.top, text="Delete", command=self.on_delete)
        self.delete_button.pack(pady=5)
        
        self.cancel_button = tk.Button(self.top, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack(pady=5)

        self.selected_team = None
    
    def on_delete(self):
        self.selected_team = self.combobox.get()
        if self.selected_team:
            self.top.destroy()
        else:
            messagebox.showerror("Error", "Please select a team")

    def on_cancel(self):
        self.top.destroy()
