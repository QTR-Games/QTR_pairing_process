""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
from os.path import expanduser
# import filedialog module
from tkinter import filedialog
  

def browseFiles():
    home = expanduser("~")

    filename = filedialog.askopenfilename(initialdir = home,
                                          title = "Select a File",
                                          filetypes = (("Text files",
                                                        "*.txt*"),
                                                       ("all files",
                                                        "*.*")))
      

    