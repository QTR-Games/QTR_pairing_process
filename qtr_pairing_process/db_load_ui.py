""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
from tkinter import Label, Button, Tk
from os.path import expanduser
# import filedialog module
from tkinter import filedialog

class DbLoadUi:
    def __init__(self) -> None:
        self.path = None
        self.name = None
        self.window = Tk()
    def create_or_load_database(self):
        # Create the root window
        
        window = self.window
        # Set window title
        window.title('Initial Database Load')
        
        # Set window size
        window.geometry("400x200")
        
        #Set window background color
        window.config(background = "white")

        # set key bindings
        window.bind('<Escape>', lambda event: window.destroy())
        # self.window.bind('<Return>', lambda event: self.on_generate_combinations())
        
        # Create a File Explorer label
        label_file_explorer = Label(window, 
                                    text = "Select Database File or Create New Database",
                                    width = 50, height = 4, 
                                    fg = "blue")
        
            
        button_explore = Button(window, 
                                text = "Browse Files",
                                command = self.browseFiles) 
        
        button_exit = Button(window, 
                            text = "Create New File",
                            command =window.destroy) 
        
        # Grid method is chosen for placing
        # the widgets at respective positions 
        # in a table like structure by
        # specifying rows and columns
        label_file_explorer.grid(column = 1, row = 1)
        
        button_explore.grid(column = 1, row = 2)
        
        button_exit.grid(column = 1,row = 3)
        
        # Let the window wait for any events
        window.mainloop()
        print(self.path, self.name)
        return self.path, self.name

    def browseFiles(self):
        home = expanduser("~")

        filename = filedialog.askopenfilename(initialdir = home,
                                            title = "Select a File",
                                            filetypes = (("DB files",
                                                            "*.db"),
                                                        ("all files",
                                                            "*.*")))
        
        self.path = '/'.join(filename.split('/')[:-1])
        self.name = filename.split('/')[-1]
        self.window.destroy()
        
