# src/gui/widgets/secure_table.py
import tkinter as tk
from tkinter import ttk


class SecureTable(ttk.Frame):
  """Table widget for displaying vault entries"""

  def __init__(self, parent, columns=None, **kwargs):
    super().__init__(parent)

    if columns is None:
      columns = [
        ("id", "ID", 50),
        ("title", "Title", 200),
        ("username", "Username", 150),
        ("url", "URL", 200),
        ("updated_at", "Updated", 150)
      ]

    self.columns = columns
    self.selected_item = None

    # Create treeview
    self.tree = ttk.Treeview(
      self,
      columns=[col[0] for col in columns],
      show="headings",
      **kwargs
    )

    # Configure columns
    for col_id, col_name, width in columns:
      self.tree.heading(col_id, text=col_name)
      self.tree.column(col_id, width=width, minwidth=50)

    # Add scrollbars
    vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
    hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
    self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Grid layout
    self.tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # Configure grid weights
    self.grid_rowconfigure(0, weight=1)
    self.grid_columnconfigure(0, weight=1)

    # Bind selection event
    self.tree.bind('<<TreeviewSelect>>', self._on_select)

  def _on_select(self, event):
    """Handle item selection"""
    selection = self.tree.selection()
    if selection:
      self.selected_item = selection[0]
    else:
      self.selected_item = None

  def set_data(self, data):
    """Populate table with data"""
    # Clear existing items
    for item in self.tree.get_children():
      self.tree.delete(item)

    # Add new data
    for row in data:
      values = [row.get(col[0], "") for col in self.columns]
      self.tree.insert("", tk.END, values=values, iid=str(row.get('id', 0)))

  def get_selected(self):
    """Get selected item ID"""
    return self.selected_item

  def get_selected_row(self):
    """Get selected row data"""
    if self.selected_item:
      return self.tree.item(self.selected_item)['values']
    return None

  def clear_selection(self):
    """Clear current selection"""
    self.tree.selection_remove(self.tree.selection())
    self.selected_item = None
