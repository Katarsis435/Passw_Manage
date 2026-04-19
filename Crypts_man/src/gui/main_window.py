# src/gui/main_window.py
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from Crypts_man.src.core.events import events, EventType
from Crypts_man.src.core.vault.password_generator import PasswordGenerator
from Crypts_man.src.gui.dialogs.password_generator_dialog import PasswordGeneratorDialog
from Crypts_man.src.gui.widgets.secure_table import SecureTable


class MainWindow:
    """Main application window with vault management"""

    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("1200x700")

        # Buttons
        self.add_button = None
        self.edit_button = None
        self.delete_button = None
        self.gen_button = None

        # Managers (initialized after auth)
        self.entry_manager = None
        self.password_generator = PasswordGenerator()
        self.key_manager = None
        self.auth_manager = None
        self._vault_ready = False

        # UI state
        self.show_passwords = False
        self.current_search = ""
        self._search_after = None

        self._setup_ui()
        self._bind_events()
        self._bind_shortcuts()

        # Show login after UI is rendered
        self.root.after(100, self._show_login)

    def _setup_ui(self):
        """Setup main UI components"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Lock Vault", command=self._lock_vault, accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label="Backup Database", command=self._backup_database)
        file_menu.add_command(label="Restore Database", command=self._restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._quit)

        vault_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Vault", menu=vault_menu)
        vault_menu.add_command(label="Add Entry", command=self._add_entry, accelerator="Ctrl+N")
        vault_menu.add_command(label="Edit Entry", command=self._edit_entry, accelerator="Ctrl+E")
        vault_menu.add_command(label="Delete Entry", command=self._delete_entry, accelerator="Del")
        vault_menu.add_separator()
        vault_menu.add_command(label="Generate Password", command=self._show_password_generator, accelerator="Ctrl+G")

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Password Visibility", command=self._toggle_password_visibility,
                              accelerator="Ctrl+Shift+P")
        view_menu.add_separator()
        view_menu.add_command(label="Refresh", command=self._load_vault_data, accelerator="F5")

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.add_button = ttk.Button(toolbar, text="Add Entry", command=self._add_entry, state=tk.DISABLED)
        self.add_button.pack(side=tk.LEFT, padx=2)
        self.edit_button = ttk.Button(toolbar, text="Edit", command=self._edit_entry, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = ttk.Button(toolbar, text="Delete", command=self._delete_entry, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        self.gen_button = ttk.Button(toolbar, text="Generate Password", command=self._show_password_generator,
                                     state=tk.DISABLED)
        self.gen_button.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        # Search frame
        search_frame = ttk.Frame(self.root)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Search: ").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self._on_search_change)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=2)

        # Filter frame
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(filter_frame, text="Filter by Category: ").pack(side=tk.LEFT, padx=5)
        self.category_filter = ttk.Combobox(filter_frame, values=["All", "Work", "Personal", "Finance", "Social"],
                                            state="readonly", width=15)
        self.category_filter.set("All")
        self.category_filter.bind('<<ComboboxSelected>>', self._on_filter_change)
        self.category_filter.pack(side=tk.LEFT, padx=5)

        # Main table
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.table = SecureTable(table_frame)
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.parent = self.root
        self.table.edit_entry_callback = self._edit_entry
        self.table.delete_entry_callback = self._delete_entry

        # Status bar
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(self.status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lock_status = ttk.Label(self.status_frame, text="🔒 Locked", foreground="red")
        self.lock_status.pack(side=tk.RIGHT, padx=5)

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind('<Control-n>', lambda e: self._add_entry())
        self.root.bind('<Control-e>', lambda e: self._edit_entry())
        self.root.bind('<Delete>', lambda e: self._delete_entry())
        self.root.bind('<Control-Shift-P>', lambda e: self._toggle_password_visibility())
        self.root.bind('<F5>', lambda e: self._load_vault_data())
        self.root.bind('<Control-l>', lambda e: self._lock_vault())
        self.root.bind('<Control-g>', lambda e: self._show_password_generator())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())

    def _bind_events(self):
        """Bind event system callbacks"""
        events.subscribe(EventType.ENTRY_ADDED, self._on_entry_changed)
        events.subscribe(EventType.ENTRY_UPDATED, self._on_entry_changed)
        events.subscribe(EventType.ENTRY_DELETED, self._on_entry_changed)
        events.subscribe(EventType.USER_LOGGED_IN, self._on_user_logged_in)
        events.subscribe(EventType.USER_LOGGED_OUT, self._on_user_logged_out)

    def _on_entry_changed(self, data):
        """Handle entry changes"""
        self._load_vault_data()

    def _on_user_logged_in(self, data):
        """Handle user login event - FIXED & STREAMLINED"""
        print("🔓 USER LOGGED IN EVENT")
        self.lock_status.config(text="🔓 Unlocked", foreground="green")

        # Безопасная инициализация (защита от двойного вызова)
        if not self._vault_ready:
            self._init_vault_components()
            self._load_vault_data()

        # Надёжное включение кнопок через after()
        def enable_buttons_safe():
            try:
                btns = [self.add_button, self.edit_button, self.delete_button, self.gen_button]
                for btn in btns:
                    if btn and btn.winfo_exists():
                        btn.config(state=tk.NORMAL)
                print("✅ Vault buttons enabled")
            except tk.TclError:
                pass

        self.root.after(50, enable_buttons_safe)

    def _on_user_logged_out(self, data):
        """Handle user logout event"""
        self.lock_status.config(text="🔒 Locked", foreground="red")
        self.table.set_data([])
        self.entry_manager = None
        self._vault_ready = False

        # Отключаем кнопки
        btns = [self.add_button, self.edit_button, self.delete_button, self.gen_button]
        for btn in btns:
            if btn and btn.winfo_exists():
                btn.config(state=tk.DISABLED)

    def _init_vault_components(self):
        """Initialize vault components AFTER authentication"""
        from Crypts_man.src.core.vault.entry_manager import EntryManager

        print("=== _init_vault_components called ===")

        # НЕ пересоздаём менеджеры! Используем уже аутентифицированные
        if not hasattr(self, 'key_manager') or self.key_manager is None:
            print("⚠ KeyManager missing, creating fallback")
            from Crypts_man.src.core.key_manager import KeyManager
            self.key_manager = KeyManager(self.config)

        if not hasattr(self, 'auth_manager') or self.auth_manager is None:
            print("⚠ AuthManager missing, creating fallback")
            from Crypts_man.src.core.authentication import AuthenticationManager
            self.auth_manager = AuthenticationManager(self.key_manager)

        # Берём ключ, который уже закеширован в do_login()
        encryption_key = self.key_manager.get_cached_encryption_key()
        if not encryption_key:
            encryption_key = self.auth_manager.get_encryption_key()

        print(f"Encryption key loaded: {encryption_key is not None}")

        if encryption_key and len(encryption_key) == 32:
            try:
                self.entry_manager = EntryManager(self.db, self.key_manager)
                self._vault_ready = True
                print("✓ EntryManager initialized successfully")
            except Exception as e:
                print(f"✗ EntryManager failed: {e}")
                import traceback;
                traceback.print_exc()
                self._vault_ready = False
                messagebox.showerror("Vault Error", f"Failed to init vault: {e}")
        else:
            print("✗ No valid encryption key")
            self._vault_ready = False











    def _show_login(self):
        """Show login dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Login - CryptoSafe")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="CryptoSafe Manager", font=('Arial', 16, 'bold')).pack(pady=10)

        # Check if first run
        auth_hash = self.db.get_auth_hash()
        if not auth_hash:
            self._show_first_run_setup(dialog)
            return

        ttk.Label(main_frame, text="Enter Master Password: ").pack(pady=5)
        # Фрейм для пароля + кнопка "глаз"
        pwd_frame = ttk.Frame(main_frame)
        pwd_frame.pack(pady=5)
        password_entry = ttk.Entry(pwd_frame, show="*", width=30)
        password_entry.pack(side=tk.LEFT)
        password_entry.focus()
        show_pwd = tk.BooleanVar(value=False)

        def toggle_password():
            show_pwd.set(not show_pwd.get())  # Переключаем значение
            if show_pwd.get():
                password_entry.config(show="")
            else:
                password_entry.config(show="*")

        ttk.Button(pwd_frame, text="👁", width=3, command=toggle_password).pack(side=tk.LEFT, padx=(5, 0))
        error_label = ttk.Label(main_frame, text="", foreground="red")
        error_label.pack()

        # ВНУТРЕННЯЯ ФУНКЦИЯ do_login
        def do_login():
            password = password_entry.get()
            if not password:
                error_label.config(text="Please enter password")
                return

            auth_hash_data = self.db.get_auth_hash()
            salt_data = self.db.get_encryption_salt()

            if not auth_hash_data or not salt_data:
                error_label.config(text="Authentication data not found")
                return

            from Crypts_man.src.core.key_manager import KeyManager
            key_manager = KeyManager(self.config)

            from Crypts_man.src.core.authentication import AuthenticationManager
            auth_manager = AuthenticationManager(key_manager)

            encryption_key = auth_manager.authenticate(
                password,
                auth_hash_data['hash'].decode() if isinstance(auth_hash_data['hash'], bytes) else auth_hash_data['hash'],
                salt_data['salt']
            )

            if encryption_key:
                # СОХРАНЯЕМ менеджеры
                self.auth_manager = auth_manager
                self.key_manager = key_manager

                # КРИТИЧНО: кэшируем ключ
                key_manager.cache_encryption_key(encryption_key)

                print(f"✓ Login successful, key length: {len(encryption_key)}")

                # Инициализируем vault
                self._init_vault_components()
                self._load_vault_data()

                # Включаем кнопки
                if hasattr(self, 'add_button'):
                    self.add_button.config(state=tk.NORMAL)
                if hasattr(self, 'edit_button'):
                    self.edit_button.config(state=tk.NORMAL)
                if hasattr(self, 'delete_button'):
                    self.delete_button.config(state=tk.NORMAL)
                if hasattr(self, 'gen_button'):
                    self.gen_button.config(state=tk.NORMAL)

                dialog.destroy()
            else:
                error_label.config(text="Invalid password")

        # Кнопка Login вызывает do_login
        ttk.Button(main_frame, text="Login", command=do_login).pack(pady=10)

        # Bind Enter key
        password_entry.bind('<Return>', lambda e: do_login())

    def _show_first_run_setup(self, parent):
        for widget in parent.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(parent, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Welcome to CryptoSafe Manager!", font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(main_frame, text="Create your master password").pack(pady=5)

        ttk.Label(main_frame, text="Master Password: ").pack(pady=5)
        pwd_frame1 = ttk.Frame(main_frame)
        pwd_frame1.pack(pady=5)
        password_entry = ttk.Entry(pwd_frame1, show="*", width=30)
        password_entry.pack(side=tk.LEFT)
        show1 = tk.BooleanVar(value=False)
        ttk.Button(pwd_frame1, text="👁", width=3,
                   command=lambda: password_entry.config(show="" if show1.get() else "*")).pack(side=tk.LEFT, padx=(5, 0))
        show1.trace_add("write", lambda *args: password_entry.config(show="" if show1.get() else "*"))

        ttk.Label(main_frame, text="Confirm Password: ").pack(pady=5)
        pwd_frame2 = ttk.Frame(main_frame)
        pwd_frame2.pack(pady=5)
        confirm_entry = ttk.Entry(pwd_frame2, show="*", width=30)
        confirm_entry.pack(side=tk.LEFT)
        show2 = tk.BooleanVar(value=False)
        ttk.Button(pwd_frame2, text="👁", width=3,
                   command=lambda: confirm_entry.config(show="" if show2.get() else "*")).pack(side=tk.LEFT, padx=(5, 0))
        show2.trace_add("write", lambda *args: confirm_entry.config(show="" if show2.get() else "*"))

        error_label = ttk.Label(main_frame, text="", foreground="red")
        error_label.pack()

        def do_setup():
            pwd = password_entry.get()
            conf = confirm_entry.get()
            if not pwd:
                error_label.config(text="Please enter a password");
                return
            if pwd != conf:
                error_label.config(text="Passwords do not match");
                return
            if len(pwd) < 8:
                error_label.config(text="Password must be at least 8 characters");
                return

            from Crypts_man.src.core.key_manager import KeyManager
            km = KeyManager(self.config)
            auth_res = km.create_auth_hash(pwd)
            salt = os.urandom(16)

            self.db.store_auth_hash(auth_res['hash'], auth_res['params'])
            self.db.store_encryption_salt(salt)
            self.db.store_key_params(auth_res['params'])

            parent.destroy()
            self._show_login()

        ttk.Button(main_frame, text="Create Vault", command=do_setup).pack(pady=10)












    def _lock_vault(self):
        """Lock the vault"""
        if self.auth_manager:
            self.auth_manager.logout()
        self._on_user_logged_out(None)
        self.root.after(100, self._show_login)

    def _load_vault_data(self):
        """Load vault data using EntryManager"""
        if not self._vault_ready or not self.entry_manager:
            return

        try:
            category = self.category_filter.get()
            if category == "All":
                category = None
            search = self.search_var.get().strip() or None

            entries = self.entry_manager.get_all_entries(search=search, category=category)

            table_data = []
            for entry in entries:
                table_data.append({
                    'id': str(entry.get('id', '')),
                    'title': entry.get('title', ''),
                    'username': entry.get('username', ''),
                    'url': entry.get('url', ''),
                    'updated_at': str(entry.get('updated_at', ''))[:10] if entry.get('updated_at') else '',
                    'category': entry.get('category', '')
                })

            self.table.set_data(table_data, self.show_passwords)
            self.status_label.config(text=f"Loaded {len(table_data)} entries")
        except Exception as e:
            print(f"Error loading entries: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.config(text="Error loading entries")

    def _add_entry(self):
        """Add new vault entry with enhanced dialog"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Entry")
        dialog.geometry("550x650")
        dialog.transient(self.root)
        dialog.grab_set()

        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        form_frame = ttk.Frame(scrollable_frame, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        fields = {}
        row = 0

        # Title
        ttk.Label(form_frame, text="Title*: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        title_entry = ttk.Entry(form_frame, width=40)
        title_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['title'] = title_entry
        row += 1

        # Username
        ttk.Label(form_frame, text="Username: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['username'] = username_entry
        row += 1

        # Password
        ttk.Label(form_frame, text="Password: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        pwd_frame = ttk.Frame(form_frame)
        pwd_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        password_entry = ttk.Entry(pwd_frame, show="*", width=30)
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        strength_label = ttk.Label(form_frame, text="")

        def update_strength(*args):
            self._update_password_strength(password_entry.get(), strength_label)
        password_entry.bind('<KeyRelease>', update_strength)

        def generate_and_set():
            def set_password(pwd):
                password_entry.delete(0, tk.END)
                password_entry.insert(0, pwd)
                update_strength()
            PasswordGeneratorDialog(dialog, self.password_generator, set_password)

        ttk.Button(pwd_frame, text="Generate", command=generate_and_set).pack(side=tk.RIGHT, padx=(5, 0))
        fields['password'] = password_entry
        row += 1

        # URL
        ttk.Label(form_frame, text="URL: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        url_entry = ttk.Entry(form_frame, width=40)
        url_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['url'] = url_entry
        row += 1

        # Category
        ttk.Label(form_frame, text="Category: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        category_combo = ttk.Combobox(form_frame, values=["Work", "Personal", "Finance", "Social", "Other"],width=37, state="readonly")
        category_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['category'] = category_combo
        row += 1

        # Tags
        ttk.Label(form_frame, text="Tags: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        tags_entry = ttk.Entry(form_frame, width=40)
        tags_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['tags'] = tags_entry
        row += 1

        # Notes
        ttk.Label(form_frame, text="Notes: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        notes_text = tk.Text(form_frame, height=5, width=40)
        notes_text.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['notes'] = notes_text
        row += 1

        form_frame.grid_columnconfigure(1, weight=1)

        def save():
            title = fields['title'].get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required")
                return
            password = fields['password'].get()
            if not password:
                if not messagebox.askyesno("Warning", "Password is empty. Continue?"):
                    return

            if password:
                strength = self.password_generator.estimate_strength(password)
                if strength['score'] < 2:
                    if not messagebox.askyesno("Weak Password", f"Password is {strength['rating']}. Continue anyway?"):
                        return

            entry_data = {
                'title': title,
                'username': fields['username'].get().strip(),
                'password': password,
                'url': fields['url'].get().strip(),
                'category': fields['category'].get(),
                'tags': fields['tags'].get().strip(),
                'notes': fields['notes'].get(1.0, tk.END).strip()
            }

            try:
                self.entry_manager.create_entry(entry_data)
                dialog.destroy()
                self._load_vault_data()
                self.status_label.config(text=f"Entry added: {title}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save entry: {e}")

        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _update_password_strength(self, password, label):
        """Update password strength display"""
        if not password:
            label.config(text="")
            return
        strength = self.password_generator.estimate_strength(password)
        label.config(text=f"Strength: {strength['rating']}")

    def _edit_entry(self):
        """Edit selected entry with full form"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        selected = self.table.get_selected_row()
        if not selected:
            messagebox.showinfo("Info", "Please select an entry to edit")
            return

        entry_id = selected.get('id')
        try:
            entry = self.entry_manager.get_entry(entry_id)
        except Exception:
            messagebox.showerror("Error", "Failed to decrypt entry")
            return
        if not entry:
            messagebox.showerror("Error", "Entry not found")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Entry")
        dialog.geometry("550x650")
        dialog.transient(self.root)
        dialog.grab_set()

        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        form_frame = ttk.Frame(scrollable_frame, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        fields = {}
        row = 0

        # Title
        ttk.Label(form_frame, text="Title*: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        title_entry = ttk.Entry(form_frame, width=40)
        title_entry.insert(0, entry.get('title', ''))
        title_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['title'] = title_entry
        row += 1

        # Username
        ttk.Label(form_frame, text="Username: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.insert(0, entry.get('username', ''))
        username_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['username'] = username_entry
        row += 1

        # Password
        ttk.Label(form_frame, text="Password: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        pwd_frame = ttk.Frame(form_frame)
        pwd_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        password_entry = ttk.Entry(pwd_frame, show="*", width=30)
        password_entry.insert(0, entry.get('password', ''))
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        strength_label = ttk.Label(form_frame, text="")

        def update_strength(*args):
            self._update_password_strength(password_entry.get(), strength_label)

        password_entry.bind('<KeyRelease>', update_strength)
        update_strength()

        def generate_and_set():
            def set_password(pwd):
                password_entry.delete(0, tk.END)
                password_entry.insert(0, pwd)
                update_strength()
            PasswordGeneratorDialog(dialog, self.password_generator, set_password)

        ttk.Button(pwd_frame, text="Generate", command=generate_and_set).pack(side=tk.RIGHT, padx=(5, 0))
        fields['password'] = password_entry
        row += 1

        # URL
        ttk.Label(form_frame, text="URL: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        url_entry = ttk.Entry(form_frame, width=40)
        url_entry.insert(0, entry.get('url', ''))
        url_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['url'] = url_entry
        row += 1

        # Category
        ttk.Label(form_frame, text="Category: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        category_combo = ttk.Combobox(form_frame, values=["Work", "Personal", "Finance", "Social", "Other"],
                                      width=37, state="readonly")
        category_combo.set(entry.get('category', ''))
        category_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['category'] = category_combo
        row += 1

        # Tags
        ttk.Label(form_frame, text="Tags: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        tags_entry = ttk.Entry(form_frame, width=40)
        tags_entry.insert(0, entry.get('tags', ''))
        tags_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['tags'] = tags_entry
        row += 1

        # Notes
        ttk.Label(form_frame, text="Notes: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        notes_text = tk.Text(form_frame, height=5, width=40)
        notes_text.insert(1.0, entry.get('notes', ''))
        notes_text.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['notes'] = notes_text
        row += 1

        form_frame.grid_columnconfigure(1, weight=1)

        def save():
            updated_data = {
                'title': fields['title'].get().strip(),
                'username': fields['username'].get().strip(),
                'password': fields['password'].get(),
                'url': fields['url'].get().strip(),
                'category': fields['category'].get(),
                'tags': fields['tags'].get().strip(),
                'notes': fields['notes'].get(1.0, tk.END).strip()
            }
            if not updated_data['title']:
                messagebox.showerror("Error", "Title is required")
                return

            try:
                result = self.entry_manager.update_entry(entry_id, updated_data)
                if result:
                    dialog.destroy()
                    self._load_vault_data()
                    self.status_label.config(text=f"Entry updated: {updated_data['title']}")
                else:
                    messagebox.showerror("Error", "Failed to update entry")
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")

        ttk.Button(form_frame, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(form_frame, text="Cancel", command=dialog.destroy).grid(row=row + 1, column=0, columnspan=2, pady=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _delete_entry(self):
        """Delete selected entry with confirmation"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        selected_rows = self.table.get_selected_rows()
        if not selected_rows:
            messagebox.showinfo("Info", "Please select an entry to delete")
            return

        count = len(selected_rows)
        msg = f"Are you sure you want to delete {count} entry{'s' if count > 1 else ''}?\n\nDeleted entries can be restored from the backup."
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        deleted = 0
        for row in selected_rows:
            try:
                if self.entry_manager.delete_entry(str(row.get('id', '')), soft_delete=True):
                    deleted += 1
            except Exception as e:
                print(f"Error deleting {row.get('id')}: {e}")

        self._load_vault_data()
        self.status_label.config(text=f"Deleted {deleted} entries")

    def _toggle_password_visibility(self):
        """Toggle password visibility in table"""
        self.show_passwords = not self.show_passwords
        self.table.toggle_password_visibility()

    def _show_password_generator(self):
        """Show standalone password generator"""
        if not self._vault_ready:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        def use_password(password):
            # Placeholder for future clipboard/integration
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            self.status_label.config(text="Password copied to clipboard")

        PasswordGeneratorDialog(self.root, self.password_generator, use_password)

    def _on_search_change(self, *args):
        """Handle search text change with debouncing"""
        if hasattr(self, '_search_after'):
            self.root.after_cancel(self._search_after)
        self._search_after = self.root.after(300, self._perform_search)

    def _perform_search(self):
        """Perform actual search"""
        self._load_vault_data()

    def _clear_search(self):
        """Clear search field"""
        self.search_var.set("")
        self.search_entry.focus()

    def _on_filter_change(self, event=None):
        """Handle category filter change"""
        self._load_vault_data()

    def _backup_database(self):
        """Backup database"""
        from tkinter import filedialog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"cryptosafe_backup_{timestamp}.db"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db", initialfile=default_name,
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
        if file_path:
            if self.db.backup(file_path):
                messagebox.showinfo("Success", f"Backup saved to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Backup failed")

    def _restore_database(self):
        """Restore database from backup"""
        from tkinter import filedialog
        if not messagebox.askyesno("Warning",
                                   "Restoring will overwrite current data.\nMake sure you have a backup.\n\nContinue?"):
            return
        file_path = filedialog.askopenfilename(filetypes=[("Database files", "*.db"), ("All files", "*.*")])
        if file_path:
            if self.db.restore(file_path):
                messagebox.showinfo("Success", "Database restored successfully")
                self._load_vault_data()
            else:
                messagebox.showerror("Error", "Restore failed")

    def _show_about(self):
        """Show about dialog"""
        about_text = """CryptoSafe Manager
    Version 1.0 (Sprint 3)
    A secure password manager with AES-256-GCM encryption.
    Features:
    • Per-entry AES-256-GCM encryption
    • Secure password generator with strength analysis
    • Full-text search and filtering
    • Soft delete with restore capability
    © 2026 CryptoSafe Team"""
        messagebox.showinfo("About", about_text)

    def _quit(self):
        """Quit application"""
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            if self.auth_manager:
                self.auth_manager.logout()
            self.db.close()
            self.root.quit()
            self.root.destroy()

    def run(self):
        """Run the main application"""
        self.root.mainloop()
