# Python program to create 
# a file explorer in Tkinter
  
# import all components
# from the tkinter library
from tkinter import *
from os.path import expanduser
# import filedialog module
from tkinter import filedialog
  

from db_load_ui import DbLoadUi
# Function for opening the 
# file explorer window
def browseFiles():
    home = expanduser("~")

    filename = filedialog.askopenfilename(initialdir = home,
                                          title = "Select a File",
                                          filetypes = (("Text files",
                                                        "*.txt*"),
                                                       ("all files",
                                                        "*.*")))
      
    # Change label contents
    label_file_explorer.configure(text="File Opened: "+filename)
      
x = DbLoadUi()
path, name = x.create_or_load_database()
                                                                                                  
# Create the root window
window = Tk()
  
# Set window title
window.title(f'{path}, {name}')
  
# Set window size
window.geometry("500x500")
  
#Set window background color
window.config(background = "white")
  
# Create a File Explorer label
label_file_explorer = Label(window, 
                            text = "File Explorer using Tkinter",
                            width = 50, height = 4, 
                            fg = "blue")
  
      
button_explore = Button(window, 
                        text = "Browse Files",
                        command = browseFiles) 
  
button_exit = Button(window, 
                     text = "Exit",
                     command = window.destroy) 
  
# Grid method is chosen for placing
# the widgets at respective positions 
# in a table like structure by
# specifying rows and columns
label_file_explorer.grid(column = 1, row = 1)
  
button_explore.grid(column = 1, row = 2)
  
button_exit.grid(column = 1,row = 3)
  
# Let the window wait for any events
window.mainloop()