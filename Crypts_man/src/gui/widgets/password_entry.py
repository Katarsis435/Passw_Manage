# src/gui/widgets/password_entry.py
import tkinter as tk
from tkinter import ttk


class PasswordEntry(ttk.Frame):
  """Password input widget with show/hide functionality"""

  def __init__(self, parent, label="Password:", **kwargs):
    super().__init__(parent)

    self.show_password = tk.BooleanVar(value=False)

    # Label
    if label:
      ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 5))

    # Entry frame
    entry_frame = ttk.Frame(self)
    entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Password entry
    self.entry = ttk.Entry(entry_frame, show="*", **kwargs)
    self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Show/Hide button
    self.toggle_btn = ttk.Button(
      entry_frame,
      text="👁",
      width=3,
      command=self._toggle_show
    )
    self.toggle_btn.pack(side=tk.LEFT, padx=(2, 0))

    # Bind to variable
    self.show_password.trace_add('write', self._update_show)

  def _toggle_show(self):
    """Toggle password visibility"""
    self.show_password.set(not self.show_password.get())

  def _update_show(self, *args):
    """Update entry show/hide based on variable"""
    if self.show_password.get():
      self.entry.config(show="")
      self.toggle_btn.config(text="👁")
    else:
      self.entry.config(show="*")
      self.toggle_btn.config(text="👁")

  def get(self):
    """Get password value"""
    return self.entry.get()

  def set(self, value):
    """Set password value"""
    self.entry.delete(0, tk.END)
    self.entry.insert(0, value)

  def clear(self):
    """Clear password"""
    self.entry.delete(0, tk.END)
