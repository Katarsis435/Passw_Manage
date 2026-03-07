# src/gui/widgets/password_entry.py
import tkinter as tk
from tkinter import ttk


class PasswordEntry(ttk.Frame):
  """Password entry widget with show/hide functionality"""

  def __init__(self, parent, label="Password:", show_password=True, **kwargs):
    super().__init__(parent)

    self.show_password = tk.BooleanVar(value=not show_password)
    self.password_var = tk.StringVar()

    # Create label if provided
    if label:
      ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 5))

    # Password entry
    self.entry = ttk.Entry(
      self,
      textvariable=self.password_var,
      show="*" if show_password else "",
      width=kwargs.get('width', 30)
    )
    self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Show/hide checkbox
    self.show_check = ttk.Checkbutton(
      self,
      text="Show",
      variable=self.show_password,
      command=self._toggle_show
    )
    self.show_check.pack(side=tk.LEFT, padx=(5, 0))

  def _toggle_show(self):
    """Toggle password visibility"""
    if self.show_password.get():
      self.entry.config(show="")
    else:
      self.entry.config(show="*")

  def get(self) -> str:
    """Get password value"""
    return self.password_var.get()

  def set(self, value: str):
    """Set password value"""
    self.password_var.set(value)

  def clear(self):
    """Clear password"""
    self.password_var.set("")


class SecureTable(ttk.Treeview):
  """Secure table widget for vault entries"""

  def __init__(self, parent, **kwargs):
    # Define columns
    columns = ('id', 'title', 'username', 'url', 'tags', 'updated')

    super().__init__(
      parent,
      columns=columns,
      show='headings',
      selectmode='browse',
      **kwargs
    )

    # Configure columns
    self.heading('id', text='ID')
    self.heading('title', text='Title')
    self.heading('username', text='Username')
    self.heading('url', text='URL')
    self.heading('tags', text='Tags')
    self.heading('updated', text='Updated')

    # Set column widths
    self.column('id', width=50, anchor='center')
    self.column('title', width=150)
    self.column('username', width=120)
    self.column('url', width=150)
    self.column('tags', width=100)
    self.column('updated', width=120)

    # Add scrollbars
    vsb = ttk.Scrollbar(parent, orient="vertical", command=self.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.xview)
    self.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Grid layout
    self.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')

    # Configure grid weights
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)

  def add_entry(self, entry_data):
    """Add an entry to the table"""
    values = (
      entry_data.get('id', ''),
      entry_data.get('title', ''),
      entry_data.get('username', ''),
      entry_data.get('url', ''),
      entry_data.get('tags', ''),
      entry_data.get('updated_at', '')[:10] if entry_data.get('updated_at') else ''
    )
    self.insert('', 'end', values=values, iid=str(entry_data.get('id', '')))

  def update_entry(self, entry_data):
    """Update an entry in the table"""
    iid = str(entry_data.get('id', ''))
    if self.exists(iid):
      values = (
        entry_data.get('id', ''),
        entry_data.get('title', ''),
        entry_data.get('username', ''),
        entry_data.get('url', ''),
        entry_data.get('tags', ''),
        entry_data.get('updated_at', '')[:10] if entry_data.get('updated_at') else ''
      )
      self.item(iid, values=values)

  def remove_entry(self, entry_id):
    """Remove an entry from the table"""
    iid = str(entry_id)
    if self.exists(iid):
      self.delete(iid)

  def get_selected_id(self):
    """Get ID of selected entry"""
    selection = self.selection()
    if selection:
      return int(selection[0])
    return None


class AuditLogViewer(ttk.Frame):
  """Audit log viewer widget (stub for Sprint 5)"""

  def __init__(self, parent, **kwargs):
    super().__init__(parent)

    # Create treeview for logs
    columns = ('timestamp', 'action', 'entry_id', 'details')

    self.tree = ttk.Treeview(
      self,
      columns=columns,
      show='headings',
      **kwargs
    )

    # Configure columns
    self.tree.heading('timestamp', text='Timestamp')
    self.tree.heading('action', text='Action')
    self.tree.heading('entry_id', text='Entry ID')
    self.tree.heading('details', text='Details')

    self.tree.column('timestamp', width=150)
    self.tree.column('action', width=100)
    self.tree.column('entry_id', width=70, anchor='center')
    self.tree.column('details', width=300)

    # Add scrollbar
    scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
    self.tree.configure(yscrollcommand=scrollbar.set)

    # Pack
    self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

  def add_log(self, log_data):
    """Add a log entry"""
    values = (
      log_data.get('timestamp', ''),
      log_data.get('action', ''),
      log_data.get('entry_id', ''),
      log_data.get('details', '')
    )
    self.tree.insert('', 0, values=values)

  def clear(self):
    """Clear all logs"""
    for item in self.tree.get_children():
      self.tree.delete(item)
