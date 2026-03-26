# SPR_2
import tkinter as tk
from tkinter import ttk, messagebox
from src.gui.widgets.password_entry import PasswordEntry
from src.core.events import event_bus, Event


class LoginDialog:
  def __init__(self, parent, key_manager, is_first_run=False):
    self.parent = parent
    self.key_manager = key_manager
    self.is_first_run = is_first_run
    self.result = None
    self._create_dialog()

  def _create_dialog(self):
    self.dialog = tk.Toplevel(self.parent)
    self.dialog.title("CryptoSafe - First Time Setup" if self.is_first_run else "CryptoSafe - Login")
    self.dialog.geometry("400x250")
    self.dialog.resizable(False, False)
    self.dialog.transient(self.parent)
    self.dialog.grab_set()
    # center on parent
    self.dialog.update_idletasks()
    x = self.parent.winfo_x() + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
    y = self.parent.winfo_y() + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
    self.dialog.geometry(f"+{x}+{y}")
    # main frame
    main_frame = ttk.Frame(self.dialog, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    # Instructions

    if self.is_first_run:
      text = "Welcome to CryptoSafe Manager!\n\nCreate a strong master password to secure your vault."
    else:
      text = "Enter your master password to unlock the vault."
    ttk.Label(main_frame, text=text, wraplength=350).pack(pady=(0, 20))
    # password entry
    password_frame = ttk.Frame(main_frame)
    password_frame.pack(fill=tk.X, pady=10)
    ttk.Label(password_frame, text="Master Password:").pack(anchor=tk.W)
    self.password_entry = PasswordEntry(password_frame, show_strength=self.is_first_run)
    self.password_entry.pack(fill=tk.X, pady=(5, 0))

    if self.is_first_run:
      # confirm password
      ttk.Label(password_frame, text="Confirm Password:").pack(anchor=tk.W, pady=(10, 0))

      self.confirm_entry = PasswordEntry(password_frame, show_strength=False)
      self.confirm_entry.pack(fill=tk.X, pady=(5, 0))
    else:
      self.confirm_entry = None
    # buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(20, 0))
    ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(button_frame, text="Unlock", command=self._submit).pack(side=tk.RIGHT)
    # Bind Enter key
    self.dialog.bind('<Return>', lambda e: self._submit())
    # Focus password entry
    self.password_entry.focus()

  def _submit(self):
    password = self.password_entry.get()
    if self.is_first_run:
      # First time setup
      confirm = self.confirm_entry.get()
      if not password:
        messagebox.showerror("Error", "Password cannot be empty")
        return
      if password != confirm:
        messagebox.showerror("Error", "Passwords do not match")
        return
      # setup master password
      success, errors = self.key_manager.setup_master_password(password)
      if success:
        self.result = password
        self.dialog.destroy()
      else:
        messagebox.showerror("Error", "\n".join(errors))
    else:
      # Login
      if not password:
        messagebox.showerror("Error", "Password cannot be empty")
        return
      success, message = self.key_manager.authenticate(password)
      if success:
        self.result = password
        self.dialog.destroy()
      else:
        messagebox.showerror("Login Failed", message)
        self.password_entry.delete(0, tk.END)
        self.password_entry.focus()

  def _cancel(self):
    self.result = None
    self.dialog.destroy()

  def show(self):
    self.parent.wait_window(self.dialog)
    return self.result

