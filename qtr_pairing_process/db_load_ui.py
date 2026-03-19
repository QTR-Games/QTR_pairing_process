""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
import tkinter as tk
from os.path import expanduser
# import filedialog module
from tkinter import filedialog

class DbLoadUi:
    def __init__(self) -> None:
        self.path = None
        self.name = None
        self.window = tk.Tk()
        self.ui_theme = {
            "font_title": ("Arial", 14, "bold"),
            "font_body": ("Arial", 10),
            "font_body_bold": ("Arial", 10, "bold"),
            "pad_sm": 8,
            "pad_md": 12,
            "pad_lg": 18,
            "bg_surface": "#f7fbff",
            "bg_card": "#eef4f8",
            "bg_primary": "#d8efe5",
            "bg_secondary": "#e8eef5",
            "fg_primary": "#103d2b",
            "fg_body": "#2f3b4a",
            "fg_subtle": "#5b6675",
        }

    def create_or_load_database(self):
        window = self.window
        theme = self.ui_theme
        window.title('Initial Database Load')
        window.geometry("520x280")
        window.minsize(480, 250)
        window.resizable(True, True)
        window.config(background=theme["bg_surface"])

        window.bind('<Escape>', lambda event: window.destroy())

        container = tk.Frame(window, bg=theme["bg_surface"])
        container.pack(fill=tk.BOTH, expand=True, padx=theme["pad_lg"], pady=theme["pad_lg"])

        card = tk.Frame(container, bg=theme["bg_card"], relief=tk.GROOVE, borderwidth=2)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            card,
            text="Database Setup",
            font=theme["font_title"],
            bg=theme["bg_card"],
            fg=theme["fg_primary"],
        ).pack(pady=(theme["pad_md"], theme["pad_sm"]))

        tk.Label(
            card,
            text="Select an existing database file, or continue to create a new database.",
            font=theme["font_body"],
            bg=theme["bg_card"],
            fg=theme["fg_body"],
            wraplength=440,
            justify=tk.LEFT,
        ).pack(padx=theme["pad_md"], pady=(0, theme["pad_md"]))

        buttons = tk.Frame(card, bg=theme["bg_card"])
        buttons.pack(fill=tk.X, padx=theme["pad_md"], pady=(0, theme["pad_md"]))

        tk.Button(
            buttons,
            text="Browse Database Files",
            command=self.browseFiles,
            font=theme["font_body_bold"],
            bg=theme["bg_primary"],
            fg=theme["fg_primary"],
            relief=tk.RAISED,
            borderwidth=2,
            height=1,
        ).pack(fill=tk.X, pady=(0, theme["pad_sm"]))

        tk.Button(
            buttons,
            text="Create New Database",
            command=window.destroy,
            font=theme["font_body"],
            bg=theme["bg_secondary"],
            fg=theme["fg_body"],
            relief=tk.RAISED,
            borderwidth=1,
            height=1,
        ).pack(fill=tk.X)

        tk.Label(
            card,
            text="Tip: You can change databases later from Data Management.",
            font=("Arial", 8),
            bg=theme["bg_card"],
            fg=theme["fg_subtle"],
        ).pack(pady=(0, theme["pad_md"]))

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
        
