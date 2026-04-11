""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

from tkinter import ttk, messagebox

class LazyTreeView(ttk.Frame):
    def __init__(self, print_output, master, **kwargs):
        self.print_output = print_output
        # Default is production-safe: never auto-insert synthetic placeholder nodes.
        # Demo/tests that want placeholder expansion must opt in explicitly.
        self.enable_demo_population = bool(kwargs.pop("enable_demo_population", False))
        super().__init__(master)
        
        self.tree = ttk.Treeview(self, **kwargs)
        self.tree.grid(row=0, column=0, sticky='nsew')

        # Create scrollbars lazily only when content overflows.
        self.vsb = None
        self.hsb = None
        
        self.tree.configure(yscrollcommand=self._on_yscroll, xscrollcommand=self._on_xscroll)
        
        self.vsb_visible = False
        self.hsb_visible = False
        self._scrollbar_refresh_job = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tree.bind('<Configure>', self._schedule_scrollbar_update)

        if self.enable_demo_population or self.print_output:
            self.tree.bind('<<TreeviewOpen>>', self.on_open)
            self.tree.bind('<<TreeviewSelect>>', self.on_select)
            self.tree.bind('<<TreeviewClose>>', self.on_close)

    def _ensure_scrollbar(self, orient):
        if orient == 'y':
            if self.vsb is None:
                self.vsb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
            return self.vsb

        if self.hsb is None:
            self.hsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        return self.hsb

    def _on_yscroll(self, *args):
        if self.vsb is not None:
            self.vsb.set(*args)
        self._toggle_scrollbar('y', *args)

    def _on_xscroll(self, *args):
        if self.hsb is not None:
            self.hsb.set(*args)
        self._toggle_scrollbar('x', *args)

    def _toggle_scrollbar(self, orient, *args):
        scrollbar = self._ensure_scrollbar(orient)
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

    def _schedule_scrollbar_update(self, _event=None):
        if self._scrollbar_refresh_job is not None:
            return
        self._scrollbar_refresh_job = self.after_idle(self._run_scrollbar_update)

    def _run_scrollbar_update(self):
        self._scrollbar_refresh_job = None
        self._toggle_scrollbar('y', *self.tree.yview())
        self._toggle_scrollbar('x', *self.tree.xview())

    def on_open(self, event):
        item = self.tree.focus()
        if self.print_output:
            print(f"Opened {item}")
        # Demo placeholder expansion is disabled for production trees.
        # Real children are created by TreeGenerator. Use enable_demo_population=True
        # only for isolated demo/test scenarios that intentionally need fake nodes.
        if self.enable_demo_population and not self.tree.get_children(item):
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
