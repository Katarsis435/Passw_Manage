import tkinter as tk
from tkinter import ttk

THEMES = {
  "light": {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "select_bg": "#0078d4",
    "select_fg": "#ffffff",
    "entry_bg": "#ffffff",
    "entry_fg": "#000000",
    "button_bg": "#e0e0e0",
    "button_fg": "#000000",
    "tree_bg": "#ffffff",
    "tree_fg": "#000000",
    "status_bg": "#e0e0e0",
    "frame_bg": "#f0f0f0",
  },
  "dark": {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "select_bg": "#0e639c",  # VS Code style selection
    "select_fg": "#ffffff",
    "entry_bg": "#2d2d2d",
    "entry_fg": "#cccccc",
    "button_bg": "#3c3c3c",
    "button_fg": "#ffffff",
    "tree_bg": "#252526",
    "tree_fg": "#cccccc",
    "status_bg": "#007acc",
    "frame_bg": "#1e1e1e",
  }
}


def apply_theme(widget, theme_name="light"):
  """Apply theme to widget and all children"""
  theme = THEMES.get(theme_name, THEMES["light"])

  # Configure ttk styles
  style = ttk.Style()

  if theme_name == "dark":
    # Try different base themes
    available_themes = style.theme_names()
    if 'clam' in available_themes:
      style.theme_use('clam')
    elif 'alt' in available_themes:
      style.theme_use('alt')

    # Configure individual ttk widgets
    style.configure('.', background=theme["bg"], foreground=theme["fg"])
    style.configure('TFrame', background=theme["bg"])
    style.configure('TLabel', background=theme["bg"], foreground=theme["fg"])
    style.configure('TLabelframe', background=theme["bg"], foreground=theme["fg"])
    style.configure('TLabelframe.Label', background=theme["bg"], foreground=theme["fg"])

    style.configure('TButton', background=theme["button_bg"], foreground=theme["button_fg"],
                    borderwidth=1, focusthickness=3)
    style.map('TButton',
              background=[('active', theme["select_bg"]), ('pressed', theme["select_bg"])],
              foreground=[('active', 'white')])

    style.configure('TEntry', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"],
                    insertcolor=theme["fg"])

    style.configure('TCombobox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])

    style.configure('Treeview', background=theme["tree_bg"], foreground=theme["tree_fg"],
                    fieldbackground=theme["tree_bg"], borderwidth=0)
    style.configure('Treeview.Heading', background=theme["button_bg"], foreground=theme["fg"],
                    relief='flat')
    style.map('Treeview.Heading', background=[('active', theme["select_bg"])])

    style.configure('TSeparator', background=theme["button_bg"])

    style.configure('TProgressbar', background=theme["select_bg"], troughcolor=theme["entry_bg"])

  else:
    # Light theme
    if 'vista' in style.theme_names():
      style.theme_use('vista')
    elif 'clam' in style.theme_names():
      style.theme_use('clam')

    style.configure('.', background=theme["bg"], foreground=theme["fg"])
    style.configure('TFrame', background=theme["bg"])
    style.configure('TLabel', background=theme["bg"], foreground=theme["fg"])
    style.configure('TLabelframe', background=theme["bg"])
    style.configure('TLabelframe.Label', background=theme["bg"])

  # Apply to root window
  if isinstance(widget, (tk.Tk, tk.Toplevel)):
    widget.configure(bg=theme["bg"])

    # Configure any existing frames
    for child in widget.winfo_children():
      _apply_to_widget_tree(child, theme, theme_name)

  return theme


def _apply_to_widget_tree(widget, theme, theme_name):
  """Recursively apply theme to all child widgets"""
  try:
    widget_class = widget.winfo_class()

    # Handle standard tk widgets
    if widget_class in ('Frame', 'LabelFrame'):
      widget.configure(bg=theme["bg"])
    elif widget_class in ('Label', 'Button'):
      widget.configure(bg=theme["bg"], fg=theme["fg"])
    elif widget_class == 'Entry':
      widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"],
                       insertbackground=theme["fg"])
    elif widget_class == 'Text':
      widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"],
                       insertbackground=theme["fg"])
    elif widget_class == 'Listbox':
      widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"])

  except:
    pass

  # Recursively apply to children
  for child in widget.winfo_children():
    _apply_to_widget_tree(child, theme, theme_name)


def set_theme_for_dialog(dialog, theme_name="light"):
  """Apply theme to a dialog window"""
  theme = apply_theme(dialog, theme_name)
  return theme
