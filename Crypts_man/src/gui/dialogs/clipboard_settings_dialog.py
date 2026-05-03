"""Clipboard settings dialog"""

import tkinter as tk
from tkinter import ttk, messagebox


class ClipboardSettingsDialog:
  """Dialog for configuring clipboard behavior"""

  def __init__(self, parent, clipboard_service, config):
    self.parent = parent
    self.clipboard = clipboard_service
    self.config = config

    self.dialog = tk.Toplevel(parent)
    self.dialog.title("Clipboard Settings")
    self.dialog.geometry("450x400")
    self.dialog.transient(parent)
    self.dialog.grab_set()

    self._create_widgets()
    self._center_dialog()

  def _center_dialog(self):
    self.dialog.update_idletasks()
    x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
    y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
    self.dialog.geometry(f"+{x}+{y}")

  def _create_widgets(self):
    """Create dialog widgets"""
    main_frame = ttk.Frame(self.dialog, padding="15")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Security level
    level_frame = ttk.LabelFrame(main_frame, text="Security Level", padding="10")
    level_frame.pack(fill=tk.X, pady=5)

    self.security_var = tk.StringVar(value=self.config.get('clipboard_security_level', 'standard'))

    levels = [
      ("Standard (30s auto-clear, notifications on)", "standard"),
      ("Secure (15s auto-clear, enhanced monitoring)", "secure"),
      ("Paranoid (5s auto-clear, max protection)", "paranoid")
    ]

    for text, value in levels:
      ttk.Radiobutton(
        level_frame, text=text, variable=self.security_var,
        value=value, command=self._on_level_change
      ).pack(anchor=tk.W, pady=3)

    # Custom timeout
    timeout_frame = ttk.LabelFrame(main_frame, text="Auto-Clear Timeout", padding="10")
    timeout_frame.pack(fill=tk.X, pady=5)

    self.timeout_var = tk.IntVar(value=self.config.get('clipboard_timeout', 30))

    timeout_scale = ttk.Scale(
      timeout_frame, from_=5, to=300, variable=self.timeout_var,
      orient=tk.HORIZONTAL, command=self._update_timeout_label
    )
    timeout_scale.pack(fill=tk.X)

    self.timeout_label = ttk.Label(timeout_frame, text=f"Timeout: {self.timeout_var.get()} seconds")
    self.timeout_label.pack(pady=5)

    # Monitoring options
    monitor_frame = ttk.LabelFrame(main_frame, text="Security Monitoring", padding="10")
    monitor_frame.pack(fill=tk.X, pady=5)

    self.accelerate_var = tk.BooleanVar(value=self.config.get('accelerate_on_detection', True))
    ttk.Checkbutton(
      monitor_frame, text="Accelerate auto-clear when external access detected",
      variable=self.accelerate_var
    ).pack(anchor=tk.W)

    # Notifications
    notif_frame = ttk.LabelFrame(main_frame, text="Notifications", padding="10")
    notif_frame.pack(fill=tk.X, pady=5)

    self.show_notify_var = tk.BooleanVar(value=self.config.get('clipboard_notifications', True))
    ttk.Checkbutton(
      notif_frame, text="Show notifications when clipboard is copied/cleared",
      variable=self.show_notify_var
    ).pack(anchor=tk.W)

    # Buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=10)

    ttk.Button(button_frame, text="Apply", command=self._apply).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Clear Now", command=self._clear_now).pack(side=tk.RIGHT, padx=5)

  def _update_timeout_label(self, *args):
    self.timeout_label.config(text=f"Timeout: {int(self.timeout_var.get())} seconds")

  def _on_level_change(self):
    """Handle security level change"""
    level = self.security_var.get()
    if level == 'standard':
      self.timeout_var.set(30)
    elif level == 'secure':
      self.timeout_var.set(15)
    elif level == 'paranoid':
      self.timeout_var.set(5)
    self._update_timeout_label()

  def _apply(self):
    """Apply settings"""
    timeout = self.timeout_var.get()
    level = self.security_var.get()

    self.clipboard.update_settings(timeout=timeout, security_level=level)

    # Save other settings
    self.config.set('accelerate_on_detection', self.accelerate_var.get())
    self.config.set('clipboard_notifications', self.show_notify_var.get())

    messagebox.showinfo("Settings", "Clipboard settings applied")
    self.dialog.destroy()

  def _clear_now(self):
    """Clear clipboard immediately"""
    if messagebox.askyesno("Clear Clipboard", "Clear clipboard content now?"):
      self.clipboard.clear(force=True, reason="manual")
      messagebox.showinfo("Cleared", "Clipboard has been cleared")
