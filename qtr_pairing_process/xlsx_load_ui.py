""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
from tkinter import Label, Button, Tk, Toplevel
from os.path import expanduser
# import filedialog module
from tkinter import filedialog

class XlsxLoadUi:
    def __init__(self) -> None:
        self.path = None
        self.name = None
        self.window = Toplevel()
    def load_xslx_file(self):
        # Create the root window
        
        window = self.window
        # Set window title
        window.title('XLSX to load to Database')
        
        # Set window size
        window.geometry("400x200")
        
        #Set window background color
        window.config(background = "white")
        
        # Create a File Explorer label
        label_file_explorer = Label(window, 
                                    text = "Select XLSX File to import",
                                    width = 50, height = 4,
                                    fg = "blue")
        
            
        button_explore = Button(window, 
                                text = "Browse Files",
                                command = self.browse_files) 
        
        
        # Grid method is chosen for placing
        # the widgets at respective positions 
        # in a table like structure by
        # specifying rows and columns
        label_file_explorer.grid(column = 1, row = 1)
        
        button_explore.grid(column = 1, row = 2)
                
        # Let the window wait for any events
        window.mainloop()
        window.destroy()
        print('Returning XLSX values')
        return self.path, self.name

    def browse_files(self):
        home = expanduser("~")

        filename = filedialog.askopenfilename(initialdir = home,
                                            title = "Select a File",
                                            filetypes = (("XSLX files",
                                                            "*.xlsx"),
                                                        ("all files",
                                                            "*.*")))
        
        self.path = '/'.join(filename.split('/')[:-1])
        self.name = filename.split('/')[-1]
        print(self.path, self.name)
        self.window.quit()
        print('destroying window...')
        
