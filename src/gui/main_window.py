# src/gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional
import logging

from ..core.config import Config
from ..core.state_manager import StateManager
from ..core.events import EventBus, Event, EventType
from ..core.key_manager import KeyManager
from ..core.crypto.placeholder import AES256Placeholder
from ..database.db import DatabaseManager
from ..database.models import VaultEntry
from .widgets.password_entry import PasswordEntry, SecureTable, AuditLogViewer


class MainWindow:
  """Main application window"""

  def __init__(self, config: Config):
    self.config = config
    self.logger = logging.getLogger(__name__)

    # Core components
    self.state_manager = StateManager(config)
    self.event_bus = EventBus()
    self.key_manager = KeyManager()
    self.crypto = AES256Placeholder()
    self.db = DatabaseManager(config)

    # Setup UI
    self.root = tk.Tk()
    self.root.title("CryptoSafe Manager")
    self.root.geometry("900x600")

    # Set icon (placeholder)
    # self.root.iconbitmap('icon.ico')

    # Subscribe to events
    self._setup_event_handlers()

    # Build UI
    self._create_menu()
    self._create_toolbar()
    self._create_main_area()
    self._create_statusbar()

    # Load initial data (if unlocked)
    self._check_initial_state()

  def _setup_event_handlers(self):
    """Setup event handlers"""
    self.event_bus.subscribe(EventType.ENTRY_ADDED, self._on_entry_added)
    self.event_bus.subscribe(EventType.ENTRY_UPDATED, self._on_entry_updated)
    self.event_bus.subscribe(EventType.ENTRY_DELETED, self._on_entry_deleted)
    self.event_bus.subscribe(EventType.USER_LOGGED_IN, self._on_user_logged_in)
    self.event_bus.subscribe(EventType.USER_LOGGED_OUT, self._on_user_logged_out)

  def _create_menu(self):
    """Create menu bar"""
    menubar = tk.Menu(self.root)
    self.root.config(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New Database...", command=self._new_database)
    file_menu.add_command(label="Open Database...", command=self._open_database)
    file_menu.add_separator()
    file_menu.add_command(label="Backup Database...", command=self._backup_database)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)

    # Edit menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(label="Add Entry...", command=self._add_entry, accelerator="Ctrl+N")
    edit_menu.add_command(label="Edit Entry...", command=self._edit_entry, accelerator="Ctrl+E")
    edit_menu.add_command(label="Delete Entry", command=self._delete_entry, accelerator="Del")
    edit_menu.add_separator()
    edit_menu.add_command(label="Copy Password", command=self._copy_password, accelerator="Ctrl+C")

    # View menu
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)
    view_menu.add_command(label="Audit Logs", command=self._show_audit_logs)
    view_menu.add_command(label="Settings", command=self._show_settings)

    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=self._show_about)

    # Bind shortcuts
    self.root.bind('<Control-n>', lambda e: self._add_entry())
    self.root.bind('<Control-e>', lambda e: self._edit_entry())
    self.root.bind('<Delete>', lambda e: self._delete_entry())
    self.root.bind('<Control-c>', lambda e: self._copy_password())

  def _create_toolbar(self):
    """Create toolbar"""
    toolbar = ttk.Frame(self.root)
    toolbar.pack(side=tk.TOP, fill=tk.X)

    # Add buttons
    ttk.Button(toolbar, text="Add", command=self._add_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text="Edit", command=self._edit_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text="Delete", command=self._delete_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text="Copy Password", command=self._copy_password).pack(side=tk.LEFT, padx=2)

    # Separator
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    # Lock/Unlock button
    self.lock_btn = ttk.Button(toolbar, text="Lock", command=self._toggle_lock)
    self.lock_btn.pack(side=tk.LEFT, padx=2)

  def _create_main_area(self):
    """Create main area with table"""
    # Main paned window
    self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
    self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Left frame for table
    left_frame = ttk.Frame(self.paned)
    self.paned.add(left_frame, weight=3)

    # Search bar
    search_frame = ttk.Frame(left_frame)
    search_frame.pack(fill=tk.X, pady=(0, 5))

    ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
    self.search_var = tk.StringVar()
    self.search_var.trace('w', self._on_search)
    ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # Table
    table_frame = ttk.Frame(left_frame)
    table_frame.pack(fill=tk.BOTH, expand=True)
    self.table = SecureTable(table_frame)
    self.table.bind('<Double-Button-1>', lambda e: self._edit_entry())

    # Right frame for details (hidden by default)
    self.details_frame = ttk.Frame(self.paned)
    self.paned.add(self.details_frame, weight=1)
    self._create_details_panel()

    # Hide details panel initially
    self.paned.forget(self.details_frame)

  def _create_details_panel(self):
    """Create details panel"""
    # Title
    ttk.Label(self.details_frame, text="Entry Details", font=('TkDefaultFont', 12, 'bold')).pack(pady=5)

    # Details form
    form = ttk.Frame(self.details_frame)
    form.pack(fill=tk.BOTH, expand=True, padx=5)

    # Title
    ttk.Label(form, text="Title:").grid(row=0, column=0, sticky='w', pady=2)
    self.detail_title = ttk.Label(form, text="", font=('TkDefaultFont', 10, 'bold'))
    self.detail_title.grid(row=0, column=1, sticky='w', pady=2)

    # Username
    ttk.Label(form, text="Username:").grid(row=1, column=0, sticky='w', pady=2)
    self.detail_username = ttk.Label(form, text="")
    self.detail_username.grid(row=1, column=1, sticky='w', pady=2)

    # URL
    ttk.Label(form, text="URL:").grid(row=2, column=0, sticky='w', pady=2)
    self.detail_url = ttk.Label(form, text="")
    self.detail_url.grid(row=2, column=1, sticky='w', pady=2)

    # Tags
    ttk.Label(form, text="Tags:").grid(row=3, column=0, sticky='w', pady=2)
    self.detail_tags = ttk.Label(form, text="")
    self.detail_tags.grid(row=3, column=1, sticky='w', pady=2)

    # Notes
    ttk.Label(form, text="Notes:").grid(row=4, column=0, sticky='nw', pady=2)
    self.detail_notes = tk.Text(form, height=5, width=30, wrap=tk.WORD)
    self.detail_notes.grid(row=4, column=1, sticky='w', pady=2)
    self.detail_notes.config(state=tk.DISABLED)

    # Buttons
    btn_frame = ttk.Frame(self.details_frame)
    btn_frame.pack(fill=tk.X, pady=5)

    ttk.Button(btn_frame, text="Copy Password",
               command=self._copy_password).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Edit",
               command=self._edit_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Hide",
               command=self._toggle_details).pack(side=tk.RIGHT, padx=2)

  def _create_statusbar(self):
    """Create status bar"""
    self.statusbar = ttk.Frame(self.root)
    self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    # Status label
    self.status_label = ttk.Label(self.statusbar, text="Ready", relief=tk.SUNKEN)
    self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Lock state
    self.lock_label = ttk.Label(self.statusbar, text="🔒 Locked", relief=tk.SUNKEN)
    self.lock_label.pack(side=tk.RIGHT)

    # Clipboard timer placeholder
    self.clipboard_label = ttk.Label(self.statusbar, text="", relief=tk.SUNKEN)
    self.clipboard_label.pack(side=tk.RIGHT)

  def _check_initial_state(self):
    """Check initial application state"""
    if self.state_manager.is_locked:
      self._show_login_dialog()
    else:
      self._load_entries()

  def _show_login_dialog(self):
    """Show login dialog"""
    dialog = tk.Toplevel(self.root)
    dialog.title("Unlock Database")
    dialog.geometry("300x150")
    dialog.transient(self.root)
    dialog.grab_set()

    ttk.Label(dialog, text="Enter master password:").pack(pady=10)

    password_entry = PasswordEntry(dialog, label="")
    password_entry.pack(pady=5, padx=10, fill=tk.X)

    def login():
      password = password_entry.get()
      if password:
        # In Sprint 1, just unlock with any password
        self.state_manager.unlock()
        self._load_entries()
        dialog.destroy()
      else:
        messagebox.showerror("Error", "Password cannot be empty")

    ttk.Button(dialog, text="Unlock", command=login).pack(pady=10)
    password_entry.entry.focus()
    dialog.bind('<Return>', lambda e: login())

  def _load_entries(self):
    """Load entries into table"""
    if self.state_manager.is_locked:
      return

    # Clear table
    for item in self.table.get_children():
      self.table.delete(item)

    # Load entries from database
    entries = self.db.get_all_entries()
    for entry in entries:
      self.table.add_entry(entry.to_dict())

    self.status_label.config(text=f"Loaded {len(entries)} entries")

  def _on_search(self, *args):
    """Handle search"""
    search_term = self.search_var.get().lower()

    # Clear table
    for item in self.table.get_children():
      self.table.delete(item)

    # Filter and display entries
    entries = self.db.get_all_entries()
    for entry in entries:
      if (search_term in entry.title.lower() or
        search_term in entry.username.lower() or
        search_term in entry.url.lower() or
        search_term in entry.tags.lower()):
        self.table.add_entry(entry.to_dict())

  def _toggle_lock(self):
    """Toggle lock state"""
    if self.state_manager.is_locked:
      self._show_login_dialog()
    else:
      self.state_manager.lock()

  def _toggle_details(self):
    """Toggle details panel"""
    try:
      self.paned.add(self.details_frame)
    except tk.TclError:
      self.paned.forget(self.details_frame)

  def _add_entry(self):
    """Add new entry"""
    if self.state_manager.is_locked:
      messagebox.showwarning("Locked", "Please unlock the database first")
      return

    dialog = tk.Toplevel(self.root)
    dialog.title("Add Entry")
    dialog.geometry("400x300")
    dialog.transient(self.root)
    dialog.grab_set()

    # Form fields
    fields = {}
    row = 0

    for label in ['Title:', 'Username:', 'Password:', 'URL:', 'Tags:', 'Notes:']:
      ttk.Label(dialog, text=label).grid(row=row, column=0, sticky='w', padx=5, pady=2)

      if label == 'Password:':
        entry = PasswordEntry(dialog, label="")
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        fields[label] = entry
      elif label == 'Notes:':
        entry = tk.Text(dialog, height=3, width=30)
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        fields[label] = entry
      else:
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var)
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        fields[label] = var

      row += 1

    # Make form expandable
    dialog.grid_columnconfigure(1, weight=1)

    def save():
      try:
        # Create entry
        entry = VaultEntry(
          title=fields['Title:'].get(),
          username=fields['Username:'].get(),
          encrypted_password=self.crypto.encrypt(
            fields['Password:'].get().encode(),
            b'placeholder_key'  # Will be replaced in Sprint 3
          ),
          url=fields['URL:'].get(),
          notes=fields['Notes:'].get('1.0', tk.END).strip(),
          tags=fields['Tags:'].get()
        )

        # Save to database
        entry_id = self.db.add_entry(entry)

        # Add to table
        self.table.add_entry(entry.to_dict())

        dialog.destroy()
        self.status_label.config(text=f"Entry '{entry.title}' added")

      except Exception as e:
        messagebox.showerror("Error", f"Failed to add entry: {e}")

    ttk.Button(dialog, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=10)

  def _edit_entry(self):
    """Edit selected entry"""
    if self.state_manager.is_locked:
      messagebox.showwarning("Locked", "Please unlock the database first")
      return

    entry_id = self.table.get_selected_id()
    if not entry_id:
      messagebox.showinfo("Info", "Please select an entry to edit")
      return

    # Get entry from database
    entry = self.db.get_entry(entry_id)
    if not entry:
      messagebox.showerror("Error", "Entry not found")
      return

    # Similar to add dialog but populated with existing data
    # (Implementation omitted for brevity - similar to _add_entry)
    messagebox.showinfo("Info", "Edit functionality will be implemented in Sprint 2")

  def _delete_entry(self):
    """Delete selected entry"""
    if self.state_manager.is_locked:
      messagebox.showwarning("Locked", "Please unlock the database first")
      return

    entry_id = self.table.get_selected_id()
    if not entry_id:
      messagebox.showinfo("Info", "Please select an entry to delete")
      return

    if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?"):
      self.db.delete_entry(entry_id)
      self.table.remove_entry(entry_id)
      self.status_label.config(text="Entry deleted")

  def _copy_password(self):
    """Copy password to clipboard"""
    if self.state_manager.is_locked:
      messagebox.showwarning("Locked", "Please unlock the database first")
      return

    entry_id = self.table.get_selected_id()
    if not entry_id:
      messagebox.showinfo("Info", "Please select an entry")
      return

    entry = self.db.get_entry(entry_id)
    if entry and entry.encrypted_password:
      try:
        password = self.crypto.decrypt(
          entry.encrypted_password,
          b'placeholder_key'  # Will be replaced in Sprint 3
        ).decode()

        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(password)

        # Update state manager
        self.state_manager.set_clipboard(password)

        self.status_label.config(text="Password copied to clipboard")

      except Exception as e:
        messagebox.showerror("Error", f"Failed to decrypt password: {e}")

  def _new_database(self):
    """Create new database"""
    if messagebox.askyesno("New Database", "This will create a new database. Continue?"):
      # In Sprint 1, just reinitialize
      self.db._init_database()
      self._load_entries()
      self.status_label.config(text="New database created")

  def _open_database(self):
    """Open existing database"""
    from tkinter import filedialog

    filename = filedialog.askopenfilename(
      title="Open Database",
      filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
    )

    if filename:
      # Update config
      self.config.set("database_path", filename)

      # Reinitialize database
      self.db = DatabaseManager(self.config)
      self._load_entries()
      self.status_label.config(text=f"Opened database: {filename}")

  def _backup_database(self):
    """Backup database"""
    from tkinter import filedialog
    from datetime import datetime

    default_name = f"cryptosafe_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    filename = filedialog.asksaveasfilename(
      title="Backup Database",
      defaultextension=".db",
      initialvalue=default_name,
      filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
    )

    if filename:
      if self.db.backup_database(filename):
        messagebox.showinfo("Success", f"Database backed up to:\n{filename}")
      else:
        messagebox.showerror("Error", "Backup failed")

  def _show_audit_logs(self):
    """Show audit logs"""
    dialog = tk.Toplevel(self.root)
    dialog.title("Audit Logs")
    dialog.geometry("600x400")
    dialog.transient(self.root)

    viewer = AuditLogViewer(dialog)
    viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Load logs
    logs = self.db.get_audit_logs(100)
    for log in logs:
      viewer.add_log({
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
        'action': log.action,
        'entry_id': log.entry_id,
        'details': log.details
      })

  def _show_settings(self):
    """Show settings dialog"""
    dialog = tk.Toplevel(self.root)
    dialog.title("Settings")
    dialog.geometry("500x400")
    dialog.transient(self.root)

    # Create notebook for tabs
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Security tab
    security_frame = ttk.Frame(notebook)
    notebook.add(security_frame, text="Security")

    ttk.Label(security_frame, text="Clipboard timeout (seconds):").grid(row=0, column=0, sticky='w', pady=5)
    timeout_var = tk.StringVar(value=str(self.config.get("clipboard_timeout", 30)))
    ttk.Entry(security_frame, textvariable=timeout_var, width=10).grid(row=0, column=1, sticky='w', pady=5)

    ttk.Label(security_frame, text="Auto-lock (minutes):").grid(row=1, column=0, sticky='w', pady=5)
    lock_var = tk.StringVar(value=str(self.config.get("auto_lock_minutes", 5)))
    ttk.Entry(security_frame, textvariable=lock_var, width=10).grid(row=1, column=1, sticky='w', pady=5)

    # Appearance tab
    appearance_frame = ttk.Frame(notebook)
    notebook.add(appearance_frame, text="Appearance")

    ttk.Label(appearance_frame, text="Theme:").grid(row=0, column=0, sticky='w', pady=5)
    theme_var = tk.StringVar(value=self.config.get("theme", "default"))
    ttk.Combobox(appearance_frame, textvariable=theme_var,
                 values=["default", "dark", "light"], state="readonly").grid(row=0, column=1, sticky='w', pady=5)

    ttk.Label(appearance_frame, text="Language:").grid(row=1, column=0, sticky='w', pady=5)
    lang_var = tk.StringVar(value=self.config.get("language", "en"))
    ttk.Combobox(appearance_frame, textvariable=lang_var,
                 values=["en", "ru", "es"], state="readonly").grid(row=1, column=1, sticky='w', pady=5)

    # Advanced tab
    advanced_frame = ttk.Frame(notebook)
    notebook.add(advanced_frame, text="Advanced")

    ttk.Checkbutton(advanced_frame, text="Enable automatic backups").grid(row=0, column=0, sticky='w', pady=5)
    ttk.Checkbutton(advanced_frame, text="Development mode").grid(row=1, column=0, sticky='w', pady=5)

    def save_settings():
      # Update config
      self.config.set("clipboard_timeout", int(timeout_var.get()))
      self.config.set("auto_lock_minutes", int(lock_var.get()))
      self.config.set("theme", theme_var.get())
      self.config.set("language", lang_var.get())

      # Update state manager
      self.state_manager._clipboard_timeout = int(timeout_var.get())
      self.state_manager._auto_lock_minutes = int(lock_var.get())

      dialog.destroy()
      self.status_label.config(text="Settings saved")

    # Buttons
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)

    ttk.Button(btn_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=2)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

  def _show_about(self):
    """Show about dialog"""
    about_text = """CryptoSafe Manager
Version: 1.0 (Sprint 1)

A secure password manager with:
- Encrypted database
- Audit logging
- Clipboard protection
- Auto-lock feature

Built with modular architecture for future enhancements."""

    messagebox.showinfo("About CryptoSafe Manager", about_text)

  # Event handlers
  def _on_entry_added(self, event: Event):
    """Handle entry added event"""
    self.logger.info(f"Entry added: {event.data}")

  def _on_entry_updated(self, event: Event):
    """Handle entry updated event"""
    self.logger.info(f"Entry updated: {event.data}")

    # Refresh table if needed
    entry_id = event.data.get('entry_id')
    if entry_id:
      entry = self.db.get_entry(entry_id)
      if entry:
        self.table.update_entry(entry.to_dict())

  def _on_entry_deleted(self, event: Event):
    """Handle entry deleted event"""
    self.logger.info(f"Entry deleted: {event.data}")

  def _on_user_logged_in(self, event: Event):
    """Handle user login"""
    self.lock_btn.config(text="Lock")
    self.lock_label.config(text="Unlocked")
    self._load_entries()

  def _on_user_logged_out(self, event: Event):
    """Handle user logout"""
    self.lock_btn.config(text="Unlock")
    self.lock_label.config(text="Locked")

    # Clear table
    for item in self.table.get_children():
      self.table.delete(item)

  def run(self):
    """Run the application"""
    self.root.mainloop()
