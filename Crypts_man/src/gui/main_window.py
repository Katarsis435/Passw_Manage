# src/gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import time
from datetime import datetime

from Crypts_man.src.core.events import events, EventType
from Crypts_man.src.core.state_manager import StateManager
from Crypts_man.src.core.config import Config
from Crypts_man.src.database.db import Database
from Crypts_man.src.core.crypto.placeholder import AES256Placeholder
from Crypts_man.src.core.key_manager import KeyManager
from Crypts_man.src.core.authentication import AuthenticationManager
from Crypts_man.src.gui.widgets.password_entry import PasswordEntry
from Crypts_man.src.gui.widgets.secure_table import SecureTable
from Crypts_man.src.gui.widgets.audit_log_viewer import AuditLogViewer



class MainWindow:
    """Main application window"""

    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.state = StateManager()
        self.crypto = AES256Placeholder()
        self.key_manager = KeyManager(config)
        self.auth_manager = AuthenticationManager(self.key_manager)

        # Create main window
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("900x600")

        # Setup UI
        self._create_menu()
        self._create_toolbar()
        self._create_main_content()
        self._create_statusbar()

        # Bind events
        self._setup_events()

        # Check if first run
        self._check_first_run()

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Vault", command=self._new_vault)
        file_menu.add_command(label="Open Vault", command=self._open_vault)
        file_menu.add_separator()
        file_menu.add_command(label="Backup", command=self._backup_vault)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add Entry", command=self._add_entry)
        edit_menu.add_command(label="Edit Entry", command=self._edit_entry)
        edit_menu.add_command(label="Delete Entry", command=self._delete_entry)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Audit Logs", command=self._show_audit_logs)
        view_menu.add_command(label="Settings", command=self._show_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="Add", command=self._add_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit", command=self._edit_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_entry).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="Lock", command=self._lock_vault).pack(side=tk.LEFT, padx=2)

    def _create_main_content(self):
        """Create main content area"""
        # Paned window for resizable sections
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left frame for vault entries
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        ttk.Label(left_frame, text="Vault Entries", font=('Arial', 12, 'bold')).pack(anchor=tk.W)

        # Secure table
        self.table = SecureTable(left_frame)
        self.table.pack(fill=tk.BOTH, expand=True, pady=5)

        # Right frame for details/audit
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Details tab
        details_frame = ttk.Frame(self.notebook)
        self.notebook.add(details_frame, text="Details")

        self.details_text = tk.Text(details_frame, wrap=tk.WORD, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # Audit log viewer (stub)
        self.audit_viewer = AuditLogViewer(self.notebook, height=10)
        self.notebook.add(self.audit_viewer, text="Audit Log")

    def _create_statusbar(self):
        """Create status bar"""
        self.statusbar = ttk.Frame(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(self.statusbar, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.lock_label = ttk.Label(self.statusbar, text="Locked", relief=tk.SUNKEN)
        self.lock_label.pack(side=tk.RIGHT, padx=5)

        self.clipboard_label = ttk.Label(self.statusbar, text="Clipboard: --", relief=tk.SUNKEN)
        self.clipboard_label.pack(side=tk.RIGHT, padx=5)

    def _setup_events(self):
        """Setup event subscriptions"""
        events.subscribe(EventType.ENTRY_ADDED, self._on_entry_added)
        events.subscribe(EventType.ENTRY_UPDATED, self._on_entry_updated)
        events.subscribe(EventType.ENTRY_DELETED, self._on_entry_deleted)
        events.subscribe(EventType.USER_LOGGED_IN, self._on_user_logged_in)
        events.subscribe(EventType.USER_LOGGED_OUT, self._on_user_logged_out)

        # Audit log stubs
        events.subscribe(EventType.ENTRY_ADDED, self._log_audit_event)
        events.subscribe(EventType.ENTRY_UPDATED, self._log_audit_event)
        events.subscribe(EventType.ENTRY_DELETED, self._log_audit_event)

    def _log_audit_event(self, data):
        """Stub for audit logging"""
        if data:
            action = f"Entry {data.get('action', 'unknown')}: {data.get('title', '')}"
            self.db.add_audit_log(action, data.get('id'))
            self.audit_viewer.add_entry(f"{datetime.now()}: {action}")

    def _check_first_run(self):
        """Check if first run and show setup wizard or login"""
        if not os.path.exists(self.config.database_path):
            self._show_first_run_wizard()
        else:
            # Проверяем, есть ли данные аутентификации
            auth_hash = self.db.get_auth_hash()
            if not auth_hash:
                # Нет данных аутентификации - первый запуск
                self._show_first_run_wizard()
            else:
                # Показываем диалог входа
                self._show_login_dialog()

    def _show_login_dialog(self):
        """Show login dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Login")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")

        # Password input
        ttk.Label(dialog, text="Enter Master Password:", font=('Arial', 10, 'bold')).pack(pady=(20, 5))
        password_entry = PasswordEntry(dialog, label="")
        password_entry.pack(padx=20, pady=5, fill=tk.X)

        # Error label
        error_label = ttk.Label(dialog, text="", foreground="red")
        error_label.pack(pady=5)

        # Status label for backoff
        status_label = ttk.Label(dialog, text="")
        status_label.pack()

        def login():
            # Check backoff
            if self.auth_manager.should_delay():
                remaining = int(self.auth_manager.get_delay() -
                               (time.time() - self.auth_manager._last_failed_time))
                status_label.config(text=f"Please wait {remaining} seconds...")
                dialog.after(1000, login)
                return

            password = password_entry.get()
            if not password:
                error_label.config(text="Password required")
                return

            # Get stored data
            auth_hash = self.db.get_auth_hash()
            salt_data = self.db.get_encryption_salt()

            if not auth_hash or not salt_data:
                error_label.config(text="Authentication data not found")
                return

            # Authenticate
            encryption_key = self.auth_manager.authenticate(
                password,
                auth_hash['hash'].decode(),
                salt_data['salt']
            )

            if encryption_key:
                dialog.destroy()
                self._unlock_vault()
            else:
                error_label.config(text="Invalid password")
                password_entry.clear()
                password_entry.focus()

        ttk.Button(dialog, text="Login", command=login).pack(pady=20)

        # Bind Enter key
        dialog.bind('<Return>', lambda e: login())
        password_entry.focus()

    def _show_first_run_wizard(self):
        """First run setup wizard"""
        wizard = tk.Toplevel(self.root)
        wizard.title("First Run Setup")
        wizard.geometry("400x350")
        wizard.transient(self.root)
        wizard.grab_set()

        ttk.Label(wizard, text="Welcome to CryptoSafe Manager!",
                  font=('Arial', 14, 'bold')).pack(pady=10)

        # Master password
        password_frame = ttk.Frame(wizard)
        password_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(password_frame, text="Create Master Password:").pack(anchor=tk.W)
        password_entry = PasswordEntry(password_frame, label="")
        password_entry.pack(fill=tk.X, pady=5)

        ttk.Label(password_frame, text="Confirm Password:").pack(anchor=tk.W)
        confirm_entry = PasswordEntry(password_frame, label="")
        confirm_entry.pack(fill=tk.X, pady=5)

        # Password strength indicator
        strength_label = ttk.Label(password_frame, text="")
        strength_label.pack()

        def check_strength(*args):
            pwd = password_entry.get()
            if len(pwd) < 12:
                strength_label.config(text="❌ Too short (min 12 chars)", foreground="red")
            elif not any(c.isupper() for c in pwd):
                strength_label.config(text="⚠️ Add uppercase letters", foreground="orange")
            elif not any(c.islower() for c in pwd):
                strength_label.config(text="⚠️ Add lowercase letters", foreground="orange")
            elif not any(c.isdigit() for c in pwd):
                strength_label.config(text="⚠️ Add numbers", foreground="orange")
            elif not any(c in "!@#$%^&*" for c in pwd):
                strength_label.config(text="⚠️ Add symbols (!@#$%^&*)", foreground="orange")
            else:
                strength_label.config(text="✓ Strong password", foreground="green")

        password_entry.entry.bind('<KeyRelease>', check_strength)

        # Database location
        location_frame = ttk.Frame(wizard)
        location_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(location_frame, text="Database Location:").pack(anchor=tk.W)

        location_entry = ttk.Entry(location_frame)
        location_entry.insert(0, self.config.database_path)
        location_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_location():
            filename = filedialog.asksaveasfilename(
                title="Select Database Location",
                defaultextension=".db",
                filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
            )
            if filename:
                location_entry.delete(0, tk.END)
                location_entry.insert(0, filename)

        ttk.Button(location_frame, text="Browse", command=browse_location).pack(side=tk.RIGHT, padx=(5, 0))

        def finish_setup():
            password = password_entry.get()
            confirm = confirm_entry.get()

            if not password:
                messagebox.showerror("Error", "Password cannot be empty")
                return

            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match")
                return

            # Password strength check
            if len(password) < 12:
                messagebox.showerror("Error", "Password must be at least 12 characters")
                return

            # Save configuration
            self.config.set("database_path", location_entry.get())

            # Initialize database
            self.db = Database(self.config.database_path)

            # Create authentication hash
            auth_result = self.key_manager.create_auth_hash(password)
            self.db.store_auth_hash(auth_result['hash'], auth_result['params'])

            # Generate and store encryption salt
            encryption_salt = os.urandom(16)
            self.db.store_encryption_salt(encryption_salt)

            # Store key parameters
            self.db.store_key_params(auth_result['params'])

            wizard.destroy()

            # Derive and cache encryption key
            encryption_key = self.key_manager.derive_encryption_key(password, encryption_salt)
            self.key_manager.cache_encryption_key(encryption_key)

            # Unlock vault
            self._unlock_vault()

        ttk.Button(wizard, text="Finish", command=finish_setup).pack(pady=20)

    def _load_vault_data(self):
        """Load vault data into table"""
        entries = self.db.get_entries()

        # Format data for table
        table_data = []
        for entry in entries:
            table_data.append({
                'id': entry['id'],
                'title': entry['title'],
                'username': entry['username'] or '',
                'url': entry['url'] or '',
                'updated_at': entry['updated_at'][:10] if entry['updated_at'] else ''
            })
        self.table.set_data(table_data)

    def _unlock_vault(self):
        """Unlock the vault"""
        self.state.unlock()
        self.lock_label.config(text="Unlocked")
        self._load_vault_data()
        # Event already published by auth_manager

    def _lock_vault(self):
        """Lock the vault"""
        self.auth_manager.logout()
        self.state.lock()
        self.lock_label.config(text="Locked")
        self.table.set_data([])

    def _add_entry(self):
        """Add new vault entry"""
        if not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Entry")
        dialog.geometry("400x350")
        dialog.transient(self.root)

        # Create form
        fields = {}
        row = 0

        for field in ['Title', 'Username', 'Password', 'URL', 'Notes', 'Tags']:
            ttk.Label(dialog, text=f"{field}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

            if field == 'Password':
                entry = PasswordEntry(dialog, label="")
                entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
                fields[field.lower()] = entry
            elif field == 'Notes':
                entry = tk.Text(dialog, height=3, width=30)
                entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
                fields[field.lower()] = entry
            else:
                entry = ttk.Entry(dialog)
                entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
                fields[field.lower()] = entry
            row += 1

        dialog.grid_columnconfigure(1, weight=1)

        def save():
            # Get values
            title = fields['title'].get()
            if not title:
                messagebox.showerror("Error", "Title is required")
                return

            username = fields['username'].get()
            password = fields['password'].get()
            url = fields['url'].get()
            notes = fields['notes'].get(1.0, tk.END).strip()
            tags = fields['tags'].get()

            # Encrypt password
            key = self.auth_manager.get_encryption_key() or b"0" * 32
            encrypted = self.crypto.encrypt(password.encode(), key)

            # Save to database
            entry_id = self.db.add_entry(title, username, encrypted, url, notes, tags)
            dialog.destroy()

            # Publish event
            events.publish(EventType.ENTRY_ADDED, {
                'id': entry_id,
                'title': title,
                'action': 'added'
            })
            # Reload data
            self._load_vault_data()

        ttk.Button(dialog, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=10)

    def _edit_entry(self):
        """Edit selected entry"""
        if not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        selected_id = self.table.get_selected()
        if not selected_id:
            messagebox.showinfo("Info", "Please select an entry to edit")
            return
        messagebox.showinfo("Info", "Edit functionality - Sprint 2 implementation")

    def _delete_entry(self):
        """Delete selected entry"""
        if not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        selected_id = self.table.get_selected()
        if not selected_id:
            messagebox.showinfo("Info", "Please select an entry to delete")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?"):
            self.db.delete_entry(int(selected_id))
            # Publish event
            events.publish(EventType.ENTRY_DELETED, {
                'id': int(selected_id),
                'action': 'deleted'
            })

            self._load_vault_data()

    def _on_entry_added(self, data):
        """Handle entry added event"""
        self.status_label.config(text=f"Entry added: {data.get('title', '')}")

    def _on_entry_updated(self, data):
        """Handle entry updated event"""
        self.status_label.config(text=f"Entry updated: {data.get('title', '')}")

    def _on_entry_deleted(self, data):
        """Handle entry deleted event"""
        self.status_label.config(text=f"Entry deleted (ID: {data.get('id', '')})")

    def _on_user_logged_in(self, data):
        """Handle user login event"""
        self.status_label.config(text="User logged in")

    def _on_user_logged_out(self, data=None):
        """Handle user logout event"""
        self.status_label.config(text="User logged out")

    def _new_vault(self):
        """Create new vault"""
        if messagebox.askyesno("New Vault", "Create a new vault? This will overwrite existing data."):
            pass

    def _open_vault(self):
        """Open existing vault"""
        filename = filedialog.askopenfilename(
            title="Open Vault",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if filename:
            self.config.set("database_path", filename)
            self.db = Database(filename)
            self._show_login_dialog()

    def _backup_vault(self):
        """Backup vault"""
        if not os.path.exists(self.config.database_path):
            messagebox.showwarning("No Vault", "No vault to backup")
            return

        filename = filedialog.asksaveasfilename(
            title="Backup Vault",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if filename:
            if self.db.backup(filename):
                messagebox.showinfo("Success", "Vault backed up successfully")
            else:
                messagebox.showerror("Error", "Backup failed")

    def _show_audit_logs(self):
        """Show audit logs"""
        self.notebook.select(1)

    def _show_settings(self):
        """Show settings dialog (stub for Sprint 4)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("500x400")
        dialog.transient(self.root)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Security tab
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Security")

        ttk.Label(security_frame, text="Clipboard timeout (seconds):").pack(anchor=tk.W, pady=5)
        timeout_var = tk.StringVar(value=str(self.config.get("clipboard_timeout", 30)))
        ttk.Entry(security_frame, textvariable=timeout_var).pack(fill=tk.X)

        ttk.Label(security_frame, text="Auto-lock (minutes):").pack(anchor=tk.W, pady=5)
        lock_var = tk.StringVar(value=str(self.config.get("auto_lock_minutes", 5)))
        ttk.Entry(security_frame, textvariable=lock_var).pack(fill=tk.X)

        # Appearance tab
        appearance_frame = ttk.Frame(notebook)
        notebook.add(appearance_frame, text="Appearance")

        ttk.Label(appearance_frame, text="Theme:").pack(anchor=tk.W, pady=5)
        theme_var = tk.StringVar(value=self.config.get("theme", "default"))
        ttk.Combobox(appearance_frame, textvariable=theme_var,
                     values=["default", "dark", "light"]).pack(fill=tk.X)

        ttk.Label(appearance_frame, text="Language:").pack(anchor=tk.W, pady=5)
        lang_var = tk.StringVar(value=self.config.get("language", "en"))
        ttk.Combobox(appearance_frame, textvariable=lang_var,
                     values=["en", "es", "fr", "de"]).pack(fill=tk.X)

        # Advanced tab
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")

        ttk.Button(advanced_frame, text="Backup Now",
                   command=self._backup_vault).pack(pady=5)
        ttk.Button(advanced_frame, text="Export Data (CSV)",
                   command=lambda: messagebox.showinfo("Info", "Export - Sprint 6")).pack(pady=5)

        def save_settings():
            self.config.set("clipboard_timeout", int(timeout_var.get()))
            self.config.set("auto_lock_minutes", int(lock_var.get()))
            self.config.set("theme", theme_var.get())
            self.config.set("language", lang_var.get())
            dialog.destroy()
            messagebox.showinfo("Settings", "Settings saved")

        ttk.Button(dialog, text="Save", command=save_settings).pack(pady=10)

    def _show_about(self):
        """Show about dialog"""
        about_text = """CryptoSafe Manager
Version: Sprint 2
Secure password manager with audit logging and encryption.

Sprint 2 Features:
- Master password authentication with Argon2id
- Secure key derivation with PBKDF2
- Exponential backoff for failed logins
- Password strength validation

Coming in Sprints 3-8:
- Real AES-GCM encryption
- Auto-lock functionality
- TOTP support
- Secure sharing
- And more..."""

        messagebox.showinfo("About", about_text)

    def run(self):
        """Run the application"""
        self.root.mainloop()
