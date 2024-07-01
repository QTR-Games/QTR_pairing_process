""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

from tkinter import ttk, messagebox

class LazyTreeView(ttk.Frame):
    def __init__(self, print_output, master, **kwargs):
        self.print_output = print_output
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
        if self.print_output:
            print(f"Opened {item}")
        if not self.tree.get_children(item):
            self.populate_tree(item)

    def on_select(self, event):
        item = self.tree.focus()
        if self.print_output:
            print(f"Selected {item}")
                
    def on_close(self, event):
        item = self.tree.focus()
        if self.print_output:
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
