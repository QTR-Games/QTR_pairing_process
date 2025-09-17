""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
from tkinter import Label, Button, Tk
from os.path import expanduser
# import filedialog module
from tkinter import filedialog
import os

class DbLoadUi:
    def __init__(self) -> None:
        self.path = None
        self.name = None
        self.window = Tk()
    def create_or_load_database(self):
        window = self.window
        window.title('Initial Database Load')
        window.geometry("400x200")
        window.config(background = "white")
        window.bind('<Escape>', lambda event: window.destroy())

        label_file_explorer = Label(window, 
                                    text = "Select Database File or Create New Database",
                                    width = 50, height = 4, 
                                    fg = "blue")

        button_explore = Button(window, 
                                text = "Browse Files",
                                command = self.browseFiles)

        button_create = Button(window,
                               text = "Create New File",
                               command = self.createNewFile)

        label_file_explorer.grid(column = 1, row = 1)
        button_explore.grid(column = 1, row = 2)
        button_create.grid(column = 1, row = 3)

        window.mainloop()
        print(self.path, self.name)
        return self.path, self.name

    def browseFiles(self):
        home = expanduser("~")
        filename = filedialog.askopenfilename(
            initialdir=home,
            title="Select a File",
            filetypes=(("DB files", "*.db"), ("all files", "*.*"))
        )
        if filename:
            self.path = os.path.dirname(filename)
            self.name = os.path.basename(filename)
            self.window.destroy()

    def createNewFile(self):
        home = expanduser("~")
        filename = filedialog.asksaveasfilename(
            initialdir=home,
            title="Create New Database File",
            defaultextension=".db",
            filetypes=(("DB files", "*.db"), ("all files", "*.*"))
        )
        if filename:
            self.path = os.path.dirname(filename)
            self.name = os.path.basename(filename)
            # Optionally, create an empty file to ensure writability
            try:
                with open(filename, 'w') as f:
                    pass
            except Exception as e:
                print(f"Error creating file: {e}")
                self.path = None
                self.name = None
            self.window.destroy()
        
