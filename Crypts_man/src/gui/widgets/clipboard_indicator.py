"""Clipboard status indicator widget"""

import tkinter as tk
from tkinter import ttk


class ClipboardIndicator(ttk.Frame):
  """Widget showing clipboard status and remaining time"""

  def __init__(self, parent, main_window):
    super().__init__(parent)
    self.main_window = main_window
    self.clipboard = None
    self._update_job = None

    self._create_widgets()

  def _create_widgets(self):
    """Create indicator widgets"""
    self.icon_label = ttk.Label(self, text="📋", font=('Arial', 10))
    self.icon_label.pack(side=tk.LEFT)

    self.status_label = ttk.Label(self, text="", font=('Arial', 9))
    self.status_label.pack(side=tk.LEFT, padx=5)

    self.clear_btn = ttk.Button(
      self,
      text="✖",
      width=2,
      command=self._on_clear_click,
      state=tk.DISABLED
    )
    self.clear_btn.pack(side=tk.RIGHT, padx=2)

  def set_clipboard_service(self, clipboard):
    """Set clipboard service reference"""
    self.clipboard = clipboard

  def start_updates(self):
    """Start periodic status updates"""
    self._update_status_loop()

  def _update_status_loop(self):
    """Update status every 0.5 seconds"""
    self.update_status()
    if self.clipboard and self.clipboard.current_item:
      self._update_job = self.after(500, self._update_status_loop)
    else:
      if self._update_job:
        self.after_cancel(self._update_job)
        self._update_job = None

  def update_status(self):
    """Update status display"""
    if not self.clipboard:
      self._set_inactive()
      return

    status = self.clipboard.get_status()

    if status.get('active'):
      remaining = status.get('remaining_seconds', 0)
      data_type = status.get('data_type', 'data')

      if remaining > 0:
        self.status_label.config(
          text=f"{data_type} • {remaining:.0f}s",
          foreground="orange"
        )
        self.icon_label.config(text="📋⏱")
        self.clear_btn.config(state=tk.NORMAL)
      else:
        self._set_inactive()
    elif status.get('blocked'):
      self.status_label.config(text="🚫 blocked", foreground="red")
      self.icon_label.config(text="🚫")
    else:
      self._set_inactive()

    if self.clipboard and self.clipboard.current_item:
      if self._update_job:
        self.after_cancel(self._update_job)
      self._update_job = self.after(500, self._update_status_loop)

  def _set_inactive(self):
    """Set indicator to inactive state"""
    self.status_label.config(text="empty", foreground="gray")
    self.icon_label.config(text="📋")
    self.clear_btn.config(state=tk.DISABLED)

    if self._update_job:
      self.after_cancel(self._update_job)
      self._update_job = None

  def _on_clear_click(self):
    """Handle clear button click"""
    if self.clipboard:
      self.clipboard.clear(force=True, reason="manual")
      self.update_status()
