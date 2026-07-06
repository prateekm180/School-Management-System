"""
===============================================================================
 utils.py
-------------------------------------------------------------------------------
 Shared helpers used by every GUI module so we don't repeat ourselves:
   - A consistent ttk theme/style for the whole application
   - A reusable Treeview factory (with scrollbars wired up)
   - Common dialog helpers (info / error / confirm)
   - A simple form-builder for "label + entry" data-entry screens
===============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# COLOR PALETTE / THEME
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#1F4E79",     # deep school-blue for headers/sidebar
    "accent": "#2E86AB",
    "bg": "#F4F6F8",
    "white": "#FFFFFF",
    "text": "#1B1B1B",
    "success": "#2E7D32",
    "danger": "#C62828",
    "warning": "#EF6C00",
}


def apply_theme(root: tk.Tk):
    """Applies a single consistent ttk theme to the whole app."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Header.TFrame", background=COLORS["primary"])
    style.configure("Sidebar.TFrame", background=COLORS["primary"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.configure("Header.TLabel", background=COLORS["primary"], foreground="white",
                     font=("Segoe UI", 16, "bold"))
    style.configure("SubHeader.TLabel", background=COLORS["bg"], foreground=COLORS["primary"],
                     font=("Segoe UI", 13, "bold"))

    style.configure("Sidebar.TButton", font=("Segoe UI", 10), padding=8)
    style.configure("TButton", font=("Segoe UI", 10), padding=6)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
    root.configure(bg=COLORS["bg"])
    return style


def make_treeview(parent, columns, headings=None, widths=None, height=15):
    """
    Creates a Treeview with vertical + horizontal scrollbars already packed.
    columns : list of column keys, e.g. ["id", "name", "class"]
    headings: optional dict {col: "Display Text"}
    widths  : optional dict {col: pixel_width}
    Returns the Treeview widget (already gridded inside its own container frame,
    which is returned as the second value so the caller can place it).
    """
    container = ttk.Frame(parent)
    tree = ttk.Treeview(container, columns=columns, show="headings", height=height)

    for col in columns:
        text = headings.get(col, col.title()) if headings else col.title()
        width = widths.get(col, 120) if widths else 120
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor="w")

    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)

    return tree, container


def clear_tree(tree: ttk.Treeview):
    for row in tree.get_children():
        tree.delete(row)


def info(title, msg):
    messagebox.showinfo(title, msg)


def error(title, msg):
    messagebox.showerror(title, msg)


def confirm(title, msg) -> bool:
    return messagebox.askyesno(title, msg)


def build_form(parent, fields):
    """
    Quickly builds a label+entry form.
    fields: list of tuples (key, label_text, widget_type)
            widget_type is 'entry', 'date', 'combo:opt1,opt2,...' or 'text'
    Returns dict {key: widget}
    """
    widgets = {}
    for i, (key, label_text, wtype) in enumerate(fields):
        ttk.Label(parent, text=label_text + ":").grid(row=i, column=0, sticky="e", padx=6, pady=5)
        if wtype.startswith("combo:"):
            options = wtype.split(":", 1)[1].split(",")
            var = tk.StringVar(value=options[0])
            widget = ttk.Combobox(parent, textvariable=var, values=options, state="readonly", width=27)
            widget.grid(row=i, column=1, padx=6, pady=5, sticky="w")
        elif wtype == "text":
            widget = tk.Text(parent, width=30, height=4)
            widget.grid(row=i, column=1, padx=6, pady=5, sticky="w")
        else:  # plain entry / date (date is just a formatted text entry: YYYY-MM-DD)
            widget = ttk.Entry(parent, width=30)
            widget.grid(row=i, column=1, padx=6, pady=5, sticky="w")
        widgets[key] = widget
    return widgets


def get_value(widget):
    """Reads the current value out of an entry/combobox/text widget uniformly."""
    if isinstance(widget, tk.Text):
        return widget.get("1.0", "end").strip()
    return widget.get().strip()


def set_value(widget, value):
    if isinstance(widget, tk.Text):
        widget.delete("1.0", "end")
        widget.insert("1.0", value if value is not None else "")
    else:
        widget.delete(0, "end")
        widget.insert(0, value if value is not None else "")