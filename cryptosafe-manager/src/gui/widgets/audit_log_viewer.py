# src/gui/widgets/audit_log_viewer.py
import tkinter as tk
from tkinter import ttk


class AuditLogViewer(ttk.Frame):
  """Audit log viewer stub for Sprint 5"""

  def __init__(self, parent, **kwargs):
    super().__init__(parent)

    # Create text widget for log display
    self.text = tk.Text(self, wrap=tk.WORD, **kwargs)
    self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Add scrollbar
    scrollbar = ttk.Scrollbar(self, command=self.text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    self.text.config(yscrollcommand=scrollbar.set)

    # Initial placeholder message
    self.add_entry("Audit log viewer - Sprint 5 implementation")
    self.add_entry("This is a placeholder for future audit log display")

  def add_entry(self, message):
    """Add an entry to the log"""
    self.text.insert(tk.END, f"{message}\n")
    self.text.see(tk.END)

  def clear(self):
    """Clear all log entries"""
    self.text.delete(1.0, tk.END)
