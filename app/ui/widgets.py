import tkinter as tk
from tkinter import ttk

BG = '#F3F6FA'
INK = '#172F47'
MUTED = '#60758A'
BLUE = '#176BCE'


def label(parent, text, size=10, bold=False, color=INK, **kw):
    return tk.Label(parent, text=text, font=('Segoe UI', size, 'bold' if bold else 'normal'), fg=color, bg=kw.pop('bg', parent.cget('bg')), **kw)


def button(parent, text, command, primary=False):
    return ttk.Button(parent, text=text, command=command, style='Primary.TButton' if primary else 'TButton')


class ScrollFrame(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.bind_id = self.winfo_toplevel().bind('<MouseWheel>', self.wheel, add='+')

    def wheel(self, event):
        widget = event.widget
        while widget:
            if widget == self:
                self.canvas.yview_scroll(-int(event.delta / 120), 'units')
                break
            widget = getattr(widget, 'master', None)

    def destroy(self):
        self.winfo_toplevel().unbind('<MouseWheel>', self.bind_id)
        super().destroy()


def table(parent, columns):
    frame = tk.Frame(parent, bg='white')
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', selectmode='browse')
    for key, title, width in columns:
        tree.heading(key, text=title, command=lambda k=key: sort_tree(tree, k))
        tree.column(key, width=width, minwidth=65)
    scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
    horizontal.pack(side='bottom', fill='x')
    scroll.pack(side='right', fill='y')
    tree.pack(fill='both', expand=True)
    frame.pack(fill='both', expand=True, pady=(15, 0))
    return tree


def sort_tree(tree, key):
    reverse = getattr(tree, '_sort', None) == (key, False)
    rows = sorted(tree.get_children(), key=lambda i: str(tree.set(i, key)).casefold(), reverse=reverse)
    for position, iid in enumerate(rows):
        tree.move(iid, '', position)
    tree._sort = (key, reverse)


class Dialog(tk.Toplevel):
    def __init__(self, app, title, width=520, height=550):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(bg='white')
        self.geometry(f'{width}x{height}')
        self.minsize(width, height)
        self.transient(app)
        self.grab_set()
        self.body = tk.Frame(self, bg='white', padx=26, pady=22)
        self.body.pack(fill='both', expand=True)
        label(self.body, title, 20, True).pack(anchor='w', pady=(0, 18))
        self.bind('<Escape>', lambda e: self.destroy())

    def field(self, title, value=''):
        label(self.body, title, color=MUTED).pack(anchor='w', pady=(8, 4))
        var = tk.StringVar(value=value)
        entry = ttk.Entry(self.body, textvariable=var)
        entry.pack(fill='x')
        return var
