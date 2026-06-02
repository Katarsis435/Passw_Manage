# src/gui/main_window.py
import tkinter as tk
import threading
import os


from pathlib import Path
from tkinter import messagebox as mb
from datetime import datetime
from tkinter import ttk, messagebox


from Crypts_man.src.core.authentication import AuthenticationManager
from Crypts_man.src.core.key_manager import KeyManager
from Crypts_man.src.core.events import events, EventType
from Crypts_man.src.core.vault.password_generator import PasswordGenerator
from Crypts_man.src.gui.dialogs.password_generator_dialog import PasswordGeneratorDialog
from Crypts_man.src.gui.widgets.secure_table import SecureTable
from Crypts_man.src.core.clipboard.clipboard_service import ClipboardService
from Crypts_man.src.gui.widgets.clipboard_indicator import ClipboardIndicator
from Crypts_man.src.gui.dialogs.clipboard_settings_dialog import ClipboardSettingsDialog
from Crypts_man.src.core.security.profiles import SECURITY_PROFILES, apply_profile
from Crypts_man.src.gui.system_tray import SystemTray
from Crypts_man.src.core.security.panic_mode import PanicMode
from Crypts_man.src.core.audit.audit_logger import AuditEventType, AuditSeverity



class MainWindow:
    """Main application window with vault management"""
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("1200x600")

        # UI state - ДО _setup_ui
        self.show_passwords = False
        self.current_search = ""
        self._search_after = None
        self.current_theme = self.config.get('theme', 'light')

        # System tray
        self.login_dialog = None
        self.tray = None
        self.tray_thread = None
        self.config.set('system_tray_enabled', False)

        # Managers
        self.entry_manager = None
        self.password_generator = PasswordGenerator()
        self.key_manager = None
        self.auth_manager = None
        self._vault_ready = False
        self.clipboard = None

        # Audit components
        self.audit_logger = None
        self.audit_signer = None
        self.audit_verifier = None
        self.periodic_verification_job = None

        self._setup_ui()
        self._bind_events()
        self._bind_shortcuts()

        # Show login after UI is rendered
        self.root.after(100, self._show_login)

        self.root.configure(bg='#1e1e1e')
        self._apply_theme()
        self._set_window_icon()


    def _setup_ui(self):
        """Setup main UI components"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background='#1e1e1e')
        style.configure('Light.TFrame', background='#f0f0f0')
        style.configure('TFrame', background='#f0f0f0')
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
        vault_menu.add_command(label="🗑️ Корзина", command=self._show_trash)
        vault_menu.add_command(label="Generate Password", command=self._show_password_generator, accelerator="Ctrl+G")
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Password Visibility", command=self._toggle_password_visibility,
                              accelerator="Ctrl+Shift+P")
        view_menu.add_separator()
        view_menu.add_command(label="Clipboard Settings", command=self._show_clipboard_settings)
        view_menu.add_command(label="Clear Clipboard Now", command=self._clear_clipboard_manually,
                              accelerator="Ctrl+Shift+C")
        view_menu.add_command(label="Refresh", command=self._load_vault_data, accelerator="F5")
        #view_menu.add_command(label="Toggle Dark/Light Theme", command=self._toggle_theme)
        # Security menu (Spr 5 + spr 7)
        security_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Security", menu=security_menu)
        security_menu.add_command(label="View Audit Log", command=self._show_audit_viewer, accelerator="Ctrl+Shift+A")
        security_menu.add_command(label="Verify Audit Integrity", command=self._verify_audit_logs)
        security_menu.add_separator()
        security_menu.add_command(label="Export Audit Logs", command=self._export_audit_logs)
        security_menu.add_command(label="Auto-Lock Settings", command=self._show_auto_lock_settings)  # Spr 7
        security_menu.add_command(label="Security Profiles",
                                  command=self._show_security_profiles)  # Spr 7 (опционально)
        security_menu.add_separator()
        #security_menu.add_command(label="TEST: Force Audit Entry", command=self._test_audit)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        # Tools menu (Sprint 6)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Export Vault...", command=self._show_export_dialog)
        tools_menu.add_command(label="Import Vault...", command=self._show_import_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Share Entry...", command=self._show_share_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Contacts...", command=self._show_contacts_dialog)
        security_menu.add_separator()
        #security_menu.add_command(label="TEST: Force Audit Entry", command=self._test_audit)
        #Toolbar
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        style.configure('Toolbar.TButton', padding=(10, 5))
        self.add_button = ttk.Button(self.toolbar, text="Add Entry", command=self._add_entry,state=tk.DISABLED, style='Toolbar.TButton')
        self.add_button.pack(side=tk.LEFT, padx=2)
        self.edit_button = ttk.Button(self.toolbar, text="Edit", command=self._edit_entry,state=tk.DISABLED, style='Toolbar.TButton')
        self.edit_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = ttk.Button(self.toolbar, text="Delete", command=self._delete_entry,state=tk.DISABLED, style='Toolbar.TButton')
        self.delete_button.pack(side=tk.LEFT, padx=2)
        self.gen_button = ttk.Button(self.toolbar, text="Generate Password", command=self._show_password_generator,state=tk.DISABLED, style='Toolbar.TButton')
        self.gen_button.pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        # Search frame
        self.search_frame = ttk.Frame(self.root, style='TFrame')
        self.search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(self.search_frame, text="Search: ").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self._on_search_change)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=2)
        # Filter frame
        self.filter_frame = ttk.Frame(self.root, style='TFrame')
        self.filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Label(self.filter_frame, text="Filter by Category: ").pack(side=tk.LEFT, padx=5)

        self.category_filter = ttk.Combobox(self.filter_frame, values=["All", "Work", "Personal", "Finance", "Social"],
                                            state="readonly", width=15)
        self.category_filter.set("All")
        self.category_filter.bind('<<ComboboxSelected>>', self._on_filter_change)
        self.category_filter.pack(side=tk.LEFT, padx=5)
        # Main table
        self.table_frame = ttk.Frame(self.root, style='TFrame')
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.table = SecureTable(self.table_frame)
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.parent = self
        self.table.edit_entry_callback = self._edit_entry
        self.table.delete_entry_callback = self._delete_entry
        # Status bar
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_frame, text="Ready", relief=tk.SUNKEN, bg='#1e1e1e', fg='#ffffff', anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Clipboard indicator
        self.clipboard_indicator = ClipboardIndicator(self.status_frame, self)
        self.clipboard_indicator.pack(side=tk.RIGHT, padx=5)
        self.lock_status = tk.Label(self.status_frame, text="🔒 Locked", fg="red", bg='#1e1e1e')
        self.lock_status.pack(side=tk.RIGHT, padx=5)


    def _bind_shortcuts(self):
        self.root.bind('<Control-n>', lambda e: self._add_entry())
        self.root.bind('<Control-e>', lambda e: self._edit_entry())
        self.root.bind('<Delete>', lambda e: self._delete_entry())
        self.root.bind('<Control-Shift-P>', lambda e: self._toggle_password_visibility())
        self.root.bind('<F5>', lambda e: self._load_vault_data())
        self.root.bind('<Control-l>', lambda e: self._lock_vault())
        self.root.bind('<Control-g>', lambda e: self._show_password_generator())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())
        self.root.bind('<Control-Shift-C>', lambda e: self._clear_clipboard_manually())
        self.root.bind('<Control-Shift-A>', lambda e: self._show_audit_viewer()) #spr 5
        self.root.bind('<Control-Shift-X>', lambda e: self._activate_panic_mode())  #spr 7


    def _activate_panic_mode(self):
        """Emergency panic mode - Ctrl+Shift+X"""
        try:
            print("[PANIC] Activating panic mode...")

            # 1. Clear clipboard immediately
            if self.clipboard:
                self.clipboard.clear(force=True, reason="panic")
                print("[PANIC] Clipboard cleared")

            # 2. Clear cached keys
            if self.key_manager:
                self.key_manager.clear_cache()
                print("[PANIC] Keys cleared")

            # 3. Reset vault state
            self._vault_ready = False
            self.entry_manager = None

            # 4. Update UI
            self.lock_status.config(text="🔒 Locked", foreground="red")
            self.table.set_data([])

            # 5. Disable all buttons
            for btn in [self.add_button, self.edit_button, self.delete_button, self.gen_button]:
                if btn and btn.winfo_exists():
                    btn.config(state=tk.DISABLED)

            # 6. Minimize window
            self.root.withdraw()
            self.root.lower()
            print("[PANIC] Window minimized")

            # 7. Show panic status
            self.status_label.config(text="⚠ PANIC MODE ACTIVATED - Vault Locked", foreground="red")
            self.status_label.update()

            # 8. Stealth mode - fake error
            if self.config.get('stealth_mode', False):
                mb.showerror("System Error", "The application has encountered a critical error and must close.")

            # 9. Log to audit
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="security.panic.activated",
                    severity="CRITICAL",
                    source="panic_mode",
                    details={"method": "hotkey"},
                    user_id='user'
                )
                print("[PANIC] Event logged")

            # Close any open login dialog
            if self.login_dialog is not None:
                try:
                    self.login_dialog.destroy()
                    self.login_dialog = None
                except:
                    pass

            # 10. Show login window after delay
            print("[PANIC] Attempting to show login window...")
            self.root.after(500, self._show_login)
            # 11. Update tray
            self._update_tray_status(locked=True)

            print("[PANIC] Panic mode completed")

        except Exception as e:
            print(f"[PANIC] Error: {e}")
            import traceback
            traceback.print_exc()

    def _show_trash(self):
        """Show trash dialog for restoring deleted entries"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Заблокировано", "Сначала разблокируйте хранилище")
            return

        from Crypts_man.src.gui.dialogs.trash_dialog import TrashDialog
        TrashDialog(self.root, self.entry_manager)

    def _debug_show_login(self):
        """Debug version of show_login"""
        print("[DEBUG] _debug_show_login called")
        try:
            # Check if window exists
            if self.root.winfo_exists():
                print("[DEBUG] Root window exists")
                # Show login
                self._show_login()
                print("[DEBUG] _show_login completed")
            else:
                print("[DEBUG] Root window does not exist!")
        except Exception as e:
            print(f"[DEBUG] Error in _debug_show_login: {e}")
            import traceback
            traceback.print_exc()


    def _bind_events(self):
        """Bind event system callbacks"""
        events.subscribe(EventType.ENTRY_ADDED, self._on_entry_changed)
        events.subscribe(EventType.ENTRY_UPDATED, self._on_entry_changed)
        events.subscribe(EventType.ENTRY_DELETED, self._on_entry_changed)
        events.subscribe(EventType.USER_LOGGED_IN, self._on_user_logged_in)
        events.subscribe(EventType.USER_LOGGED_OUT, self._on_user_logged_out)


    def _apply_theme(self):
        """Apply current theme - changes only colors, not widgets"""
        from src.gui.themes import apply_theme
        theme = apply_theme(self.root, self.current_theme)

        style = ttk.Style()

        if self.current_theme == "dark":
            # ===== СТИЛИ ДЛЯ ТЕМНОЙ ТЕМЫ =====

            # Фреймы
            style.configure('TFrame', background='#1e1e1e')

            # Поля ввода
            style.configure('TEntry', fieldbackground='#2d2d2d', foreground='#ffffff', insertcolor='#ffffff')
            style.configure('TCombobox', fieldbackground='#2d2d2d', foreground='#ffffff')

            # Надписи
            style.configure('TLabel', background='#1e1e1e', foreground='#ffffff')

            # Кнопки
            style.configure('TButton', background='#3c3c3c', foreground='#ffffff',
                            borderwidth=1, focuscolor='none')
            style.map('TButton',
                      background=[('active', '#0e639c'), ('pressed', '#0e639c')])

            # Скроллбары
            style.configure('Vertical.TScrollbar', background='#3c3c3c', troughcolor='#2d2d2d')
            style.configure('Horizontal.TScrollbar', background='#3c3c3c', troughcolor='#2d2d2d')

            # МЕНЮ (добавлено)
            self.root.option_add('*Menu.background', '#2d2d2d')
            self.root.option_add('*Menu.foreground', '#ffffff')
            self.root.option_add('*Menu.selectColor', '#0e639c')

            # Корневое окно
            self.root.configure(bg='#1e1e1e')

            # Статус бар
            self.status_label.configure(bg='#1e1e1e', fg='#ffffff')
            self.lock_status.configure(bg='#1e1e1e', fg='red')

            # Combobox
            #self.category_filter.configure(background='#2d2d2d', foreground='#ffffff')

        else:
            # ===== СТИЛИ ДЛЯ СВЕТЛОЙ ТЕМЫ =====
            style.configure('TFrame', background='#f0f0f0')
            style.configure('TEntry', fieldbackground='#ffffff', foreground='#000000', insertcolor='#000000')
            style.configure('TCombobox', fieldbackground='#ffffff', foreground='#000000')
            style.configure('TLabel', background='#f0f0f0', foreground='#000000')
            style.configure('TButton', background='#e0e0e0', foreground='#000000')
            style.map('TButton', background=[('active', '#0078d4')])
            style.configure('Vertical.TScrollbar', background='#e0e0e0', troughcolor='#f0f0f0')
            style.configure('Horizontal.TScrollbar', background='#e0e0e0', troughcolor='#f0f0f0')

            # МЕНЮ (добавлено)
            self.root.option_add('*Menu.background', '#f0f0f0')
            self.root.option_add('*Menu.foreground', '#000000')
            self.root.option_add('*Menu.selectColor', '#0078d4')
            self.root.configure(bg='#f0f0f0')
            self.status_label.configure(bg='#f0f0f0', fg='#000000')
            self.lock_status.configure(bg='#f0f0f0', fg='red')
            self.category_filter.configure(background='#ffffff', foreground='#000000')
        # Принудительно обновляем все фреймы
        for frame in [self.search_frame, self.filter_frame, self.table_frame, self.status_frame]:
            if frame:
                frame.configure(style='TFrame')
        # Обновляем таблицу
        if hasattr(self, 'table') and self._vault_ready:
            self._load_vault_data()
        self.root.update_idletasks()
        return theme


    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.config.set('theme', self.current_theme)
        self._apply_theme()
        # self.status_label.config(text=f"Theme changed to {self.current_theme}")


    def _on_entry_changed(self, data):
        """Handle entry changes"""
        self._load_vault_data()
        # Log to audit
        if self.audit_logger:
            event_type = data.get('action', 'modified')
            self.audit_logger.log_event(
                event_type=f"vault.entry.{event_type}",
                severity="INFO",
                source="vault",
                details={'entry_id': data.get('id'), 'title': data.get('title')},
                user_id='user',
                entry_id=data.get('id')
            )


    def _on_user_logged_in(self, data):
        """Handle user login event"""
        print("🔓 USER LOGGED IN EVENT")
        self.lock_status.config(text="🔓 Unlocked", foreground="green")
        if not self._vault_ready:
            self._init_vault_components()
            self._load_vault_data()
            self._init_clipboard_service()
        if hasattr(self, 'activity_monitor'):
            self.activity_monitor.start_monitoring()
            self.activity_monitor.reset_activity()

        def enable_buttons_safe():
            try:
                btns = [self.add_button, self.edit_button, self.delete_button, self.gen_button]
                for btn in btns:
                    if btn and btn.winfo_exists():
                        btn.config(state=tk.NORMAL)
                print("✓ Vault buttons enabled")
            except tk.TclError:
                pass
        self.root.after(50, enable_buttons_safe)
        #if self.config.get('system_tray_enabled', True):
        #    self.root.after(100, self._init_system_tray)
        #    self._update_tray_status(locked=False)


    def _retry_audit_init(self):
        """Retry audit initialization after key is available"""
        if self.key_manager and self.key_manager.get_cached_encryption_key():
            print("✓ Retry: encryption key available, initializing audit...")
            self._init_audit_system()
        else:
            print("⚠ Still waiting for encryption key...")
            self.root.after(1000, self._retry_audit_init)

        def enable_buttons_safe():
            try:
                btns = [self.add_button, self.edit_button, self.delete_button, self.gen_button]
                for btn in btns:
                    if btn and btn.winfo_exists():
                        btn.config(state=tk.NORMAL)
                print("✓ Vault buttons enabled")
            except tk.TclError:
                pass
        self.root.after(50, enable_buttons_safe)


    def _init_audit_system(self):
        """Initialize audit logging system after authentication"""
        try:
            from Crypts_man.src.core.audit.audit_logger import AuditLogger, AuditEventType, AuditSeverity
            from Crypts_man.src.core.audit.log_signer import AuditLogSigner
            from Crypts_man.src.core.audit.log_verifier import LogVerifier
            print("=== INITIALIZING AUDIT SYSTEM ===")
            # Create signer
            self.audit_signer = AuditLogSigner(self.key_manager, self.config)
            print("✓ Audit signer created")
            # Create logger
            self.audit_logger = AuditLogger(self.db, self.audit_signer, self.config)
            print("✓ Audit logger created")
            # Create verifier
            self.audit_verifier = LogVerifier(self.db, self.audit_signer)
            print("✓ Audit verifier created")
            # Store public key
            self.audit_signer.store_public_key(self.db)
            print("✓ Public key stored")
            # Subscribe to events for automatic logging
            self._subscribe_audit_events()
            print("✓ Subscribed to audit events")
            # Log successful initialization
            self.audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_UNLOCK.value,
                severity=AuditSeverity.INFO.value,
                source="main_window",
                details={'message': 'Audit system initialized'},
                user_id='user'
            )
            print("✓ Audit system initialized successfully")
        except Exception as e:
            print(f"⚠ Audit system initialization failed: {e}")
            import traceback
            traceback.print_exc()


    def _subscribe_audit_events(self):
        """Subscribe to system events for automatic audit logging"""
        from Crypts_man.src.core.audit.audit_logger import AuditEventType, AuditSeverity
        if not self.audit_logger:
            print("No audit logger, skipping subscriptions")
            return
        print("Setting up audit event subscriptions...")

        # Subscribe to entry events
        def log_entry_added(data):
            print(f"AUDIT: Entry added - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.VAULT_ENTRY_CREATE.value,
                severity=AuditSeverity.INFO.value,
                source="vault",
                details={'entry_id': data.get('id'), 'title': data.get('title')},
                user_id='user',
                entry_id=data.get('id')
            )

        def log_entry_updated(data):
            print(f"AUDIT: Entry updated - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.VAULT_ENTRY_UPDATE.value,
                severity=AuditSeverity.INFO.value,
                source="vault",
                details={'entry_id': data.get('id'), 'title': data.get('title')},
                user_id='user',
                entry_id=data.get('id')
            )

        def log_entry_deleted(data):
            print(f"AUDIT: Entry deleted - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.VAULT_ENTRY_DELETE.value,
                severity=AuditSeverity.WARN.value,
                source="vault",
                details={'entry_id': data.get('id'), 'soft': data.get('soft', True)},
                user_id='user',
                entry_id=data.get('id')
            )

        # Subscribe to auth events
        def log_login(data):
            print(f"AUDIT: User logged in - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS.value,
                severity=AuditSeverity.INFO.value,
                source="auth",
                details={'timestamp': str(data.get('timestamp')) if data else ''},
                user_id='user'
            )

        def log_logout(data):
            print("AUDIT: User logged out")
            self.audit_logger.log_event(
                event_type=AuditEventType.AUTH_LOGOUT.value,
                severity=AuditSeverity.INFO.value,
                source="auth",
                details={},
                user_id='user'
            )

        # Subscribe to clipboard events
        def log_clipboard_copy(data):
            print(f"AUDIT: Clipboard copy - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.CLIPBOARD_COPY.value,
                severity=AuditSeverity.INFO.value,
                source="clipboard",
                details={'data_type': data.get('data_type'), 'entry_id': data.get('source_entry_id')},
                user_id='user',
                entry_id=data.get('source_entry_id')
            )

        def log_clipboard_clear(data):
            print(f"AUDIT: Clipboard cleared - {data}")
            self.audit_logger.log_event(
                event_type=AuditEventType.CLIPBOARD_CLEAR.value,
                severity=AuditSeverity.INFO.value,
                source="clipboard",
                details={'reason': data.get('reason') if data else 'manual'},
                user_id='user'
            )

        # Register callbacks
        events.subscribe(EventType.ENTRY_ADDED, log_entry_added)
        events.subscribe(EventType.ENTRY_UPDATED, log_entry_updated)
        events.subscribe(EventType.ENTRY_DELETED, log_entry_deleted)
        events.subscribe(EventType.USER_LOGGED_IN, log_login)
        events.subscribe(EventType.USER_LOGGED_OUT, log_logout)
        events.subscribe(EventType.CLIPBOARD_COPIED, log_clipboard_copy)
        events.subscribe(EventType.CLIPBOARD_CLEARED, log_clipboard_clear)
        print(
            "✓ Subscribed to: ENTRY_ADDED, ENTRY_UPDATED, ENTRY_DELETED, USER_LOGGED_IN, USER_LOGGED_OUT, CLIPBOARD_COPIED, CLIPBOARD_CLEARED")


    def _start_periodic_verification(self):
        """Start periodic log verification"""

        def verify_periodically():
            if self.audit_verifier and self._vault_ready:
                try:
                    result = self.audit_verifier.verify_recent(count=100)
                    if not result.verified:
                        self._handle_audit_tampering(result)
                except Exception as e:
                    print(f"Periodic verification failed: {e}")
            if self.periodic_verification_job:
                self.root.after_cancel(self.periodic_verification_job)
            self.periodic_verification_job = self.root.after(86400000, verify_periodically)  # 24 hours
        self.root.after(60000, verify_periodically)  # Start after 1 minute


    def _handle_audit_tampering(self, result):
        """Handle detected audit log tampering"""
        messagebox.showwarning(
            "Security Alert",
            f"Audit log tampering detected!\n\n"
            f"Tampered entries: {len(result.tampered_entries)}\n"
            f"Chain breaks: {len(result.chain_breaks)}\n\n"
            f"Please verify your database integrity."
        )


    def _show_audit_viewer(self):
        """Show audit log viewer dialog"""
        if not self._vault_ready or not self.auth_manager or not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first to view audit logs")
            return
        if not hasattr(self, 'audit_logger') or not self.audit_logger:
            messagebox.showwarning("Not Available", "Audit system not initialized yet.\nPlease wait or re-login.")
            return
        try:
            from Crypts_man.src.gui.dialogs.audit_viewer_dialog import AuditViewerDialog
            from Crypts_man.src.gui.themes import apply_theme
            dialog = AuditViewerDialog(self.root, self.audit_logger, self.audit_verifier)
            apply_theme(dialog, self.current_theme)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open audit viewer: {e}")


    def _verify_audit_logs(self):
        """Manually verify audit logs"""
        if not self._vault_ready or not self.auth_manager or not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first to view audit logs")
            return
        if not hasattr(self, 'audit_verifier') or not self.audit_verifier:
            messagebox.showwarning("Not Available", "Audit system not initialized")
            return
        # Show progress dialog
        progress = tk.Toplevel(self.root)
        progress.title("Verifying...")
        progress.geometry("300x100")
        progress.transient(self.root)
        label = ttk.Label(progress, text="Verifying audit log integrity...")
        label.pack(pady=20)
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(fill=tk.X, padx=20)
        progress_bar.start()

        def do_verify():
            try:
                result = self.audit_verifier.verify_full()
                self.root.after(0, lambda: self._show_verification_result(result, progress))
            except Exception as e:
                self.root.after(0, lambda: self._show_verification_error(str(e), progress))
        import threading
        threading.Thread(target=do_verify, daemon=True).start()


    def _show_verification_result(self, result, progress_dialog):
        """Show verification result"""
        progress_dialog.destroy()
        if result.verified:
            messagebox.showinfo(
                "Verification Complete",
                f"✓ Audit log integrity verified!\n\n"
                f"Entries checked: {result.total_entries}\n"
                f"Valid signatures: {result.valid_entries}\n"
                f"Verification time: {result.verification_time:.2f}s"
            )
        else:
            messagebox.showerror(
                "Verification Failed",
                f"✗ Audit log tampering detected!\n\n"
                f"Total entries: {result.total_entries}\n"
                f"Valid entries: {result.valid_entries}\n"
                f"Invalid signatures: {len(result.invalid_signatures)}\n"
                f"Chain breaks: {len(result.chain_breaks)}\n"
                f"Hash mismatches: {len(result.hash_mismatches)}"
            )


    def _show_verification_error(self, error, progress_dialog):
        """Show verification error"""
        progress_dialog.destroy()
        messagebox.showerror("Verification Error", f"Failed to verify logs: {error}")


    def _export_audit_logs(self):
        """Export audit logs"""
        if not self._vault_ready or not self.auth_manager or not self.auth_manager.is_authenticated():
            messagebox.showwarning("Locked", "Please unlock the vault first to view audit logs")
            return #если заблок -- нелья
        if not hasattr(self, 'audit_logger') or not self.audit_logger:
            messagebox.showwarning("Not Available", "Audit system not initialized")
            return
        try:
            from Crypts_man.src.gui.dialogs.audit_export_dialog import AuditExportDialog
            AuditExportDialog(self.root, self.audit_logger, self.audit_signer)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open export dialog: {e}")


    def _show_auto_lock_settings(self):
        """Show auto-lock configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Auto-Lock Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Lock vault after inactivity:", font=('Arial', 10, 'bold')).pack(anchor=tk.W,
                                                                                                    pady=(0, 10))
        timeout_frame = ttk.Frame(main_frame)
        timeout_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timeout_frame, text="Minutes:").pack(side=tk.LEFT)
        timeout_var = tk.IntVar(value=self.config.get('auto_lock_minutes', 5))
        spinbox = ttk.Spinbox(timeout_frame, from_=1, to=60, textvariable=timeout_var, width=10)
        spinbox.pack(side=tk.LEFT, padx=10)
        ttk.Label(timeout_frame, text="(1-60 minutes)").pack(side=tk.LEFT)
        preview_label = ttk.Label(main_frame, text=f"Will lock after {timeout_var.get()} minutes of inactivity",
                                  foreground="gray")
        preview_label.pack(pady=10)

        def update_preview(*args):
            preview_label.config(text=f"Will lock after {timeout_var.get()} minutes of inactivity")
        timeout_var.trace_add('write', update_preview)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)

        def save():
            self.config.set('auto_lock_minutes', timeout_var.get())
            dialog.destroy()
            messagebox.showinfo("Settings", f"Auto-lock set to {timeout_var.get()} minutes")

        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)


    def _show_security_profiles(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Security Profiles")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Select Security Level:", font=('Arial', 12, 'bold')).pack(pady=10)
        current_profile = self.config.get('security_profile', 'standard')
        profiles = [
            ("Standard", "standard",
             "Balanced security and usability\n• 10 min auto-lock\n• 30 sec clipboard timeout\n• Standard monitoring"),
            ("Enhanced", "enhanced",
             "Extra protection with some inconvenience\n• 3 min auto-lock\n• 15 sec clipboard timeout\n• Enhanced monitoring"),
            ("Paranoid", "paranoid",
             "Maximum security, minimal convenience\n• 1 min auto-lock\n• 5 sec clipboard timeout\n• Stealth mode enabled")
        ]
        profile_var = tk.StringVar(value=current_profile)
        for name, value, desc in profiles:
            frame = ttk.Frame(main_frame)
            frame.pack(fill=tk.X, pady=5)
            rb = ttk.Radiobutton(frame, text=name, variable=profile_var, value=value)
            rb.pack(side=tk.LEFT)
            desc_label = ttk.Label(frame, text=desc, foreground="gray", font=('Arial', 8))
            desc_label.pack(side=tk.LEFT, padx=20)

        def apply():
            selected = profile_var.get()
            apply_profile(self.config, selected)
            self.config.set('security_profile', selected)
            dialog.destroy()
            messagebox.showinfo("Profile Applied",
                                f"Security profile set to {selected.upper()}\nSome settings may require restart.")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        ttk.Button(button_frame, text="Apply", command=apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)


    def _init_clipboard_service(self):
        """Initialize clipboard service after login"""
        if not self.clipboard:
            self.clipboard = ClipboardService(self.config, events, self.root)
            if self.clipboard_indicator:
                self.clipboard_indicator.set_clipboard_service(self.clipboard)
                self.clipboard_indicator.start_updates()


    def _init_system_tray(self):
        if self.tray is not None:
            return
        try:
            self.tray = SystemTray(self, self.config)
            self.tray.create_tray_icon()
            self.tray_thread = threading.Thread(target=self.tray.run, daemon=True)
            self.tray_thread.start()
            print("✓ System tray initialized")
        except ImportError as e:
            print(f"⚠ System tray not available: {e}")
            self.tray = None
        except Exception as e:
            print(f"⚠ Failed to initialize system tray: {e}")
            self.tray = None


    def _update_tray_status(self, locked: bool):
        if self.tray:
            self.tray.update_lock_status(locked)


    def _on_user_logged_out(self, data):
        """Handle user logout event"""
        self.lock_status.config(text="🔒 Locked", foreground="red")
        self.table.set_data([])
        if self.clipboard:
            self.clipboard.clear(force=True, reason="vault_locked")
        self.entry_manager = None
        self._vault_ready = False
        btns = [self.add_button, self.edit_button, self.delete_button, self.gen_button]
        for btn in btns:
            if btn and btn.winfo_exists():
                btn.config(state=tk.DISABLED)
        self._update_tray_status(locked=True)
        if hasattr(self, 'activity_monitor'):
            self.activity_monitor.stop_monitoring()


    def _init_vault_components(self):
        """Initialize vault components AFTER authentication"""
        from Crypts_man.src.core.vault.entry_manager import EntryManager
        print("=== _init_vault_components called ===")
        if not hasattr(self, 'key_manager') or self.key_manager is None:
            self.key_manager = KeyManager(self.config)
        if not hasattr(self, 'auth_manager') or self.auth_manager is None:
            self.auth_manager = AuthenticationManager(self.key_manager)
        encryption_key = self.key_manager.get_cached_encryption_key()
        if not encryption_key:
            encryption_key = self.auth_manager.get_encryption_key()
        print(f"Encryption key loaded: {encryption_key is not None}")
        if encryption_key and len(encryption_key) == 32:
            try:
                self.entry_manager = EntryManager(self.db, self.key_manager)
                self._vault_ready = True
                print("✓ EntryManager initialized successfully")
                # Инициализация аудит-системы ТОЛЬКО ЕСЛИ ЕЩЕ НЕ ИНИЦИАЛИЗИРОВАНА
                if not hasattr(self, 'audit_logger') or self.audit_logger is None:
                    self._init_audit_system()
            except Exception as e:
                print(f"✗ EntryManager failed: {e}")
                import traceback
                traceback.print_exc()
                self._vault_ready = False
                messagebox.showerror("Vault Error", f"Failed to init vault: {e}")
        else:
          print("✗ No valid encryption key")
          self._vault_ready = False
        self._init_activity_monitor()


    def _init_activity_monitor(self):
        """Initialize activity monitor for auto-lock"""
        try:
            from Crypts_man.src.core.security.activity_monitor import ActivityMonitor

            def on_lock():
                self.root.after(0, self._lock_vault)

            self.activity_monitor = ActivityMonitor(on_lock, self.config)
            self.activity_monitor.start_monitoring()

            # Привязываем события для отслеживания активности
            self.root.bind('<Key>', lambda e: self.activity_monitor.record_activity())
            self.root.bind('<Button-1>', lambda e: self.activity_monitor.record_activity())
            self.root.bind('<Motion>', lambda e: self.activity_monitor.record_activity())

            print("✓ Activity monitor started")
        except Exception as e:
            print(f"⚠ Activity monitor failed: {e}")


    def _show_login(self):
        """Show login dialog"""
        print("[DEBUG] _show_login called")

        # Check if dialog already exists and is visible
        if self.login_dialog is not None:
            try:
                if self.login_dialog.winfo_exists():
                    self.login_dialog.lift()
                    self.login_dialog.focus_force()
                    print("[DEBUG] Login dialog already exists, lifted")
                    return
            except:
                self.login_dialog = None

        # Restore main window if minimized
        try:
            if self.root.winfo_exists():
                if self.root.state() == 'iconic':
                    self.root.deiconify()
                    print("[DEBUG] Main window restored from minimized")
                self.root.lift()
        except Exception as e:
            print(f"[DEBUG] Error restoring window: {e}")

        # Create login dialog
        dialog = tk.Toplevel(self.root)
        self.login_dialog = dialog
        dialog.title("Login - CryptoSafe")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"+{x}+{y}")

        # Handle dialog close (X button)
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._cancel_login(dialog))

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="CryptoSafe Manager", font=('Arial', 16, 'bold')).pack(pady=10)

        auth_hash = self.db.get_auth_hash()
        if not auth_hash:
            self._show_first_run_setup(dialog)
            return

        ttk.Label(main_frame, text="Enter Master Password: ").pack(pady=5)

        pwd_frame = ttk.Frame(main_frame)
        pwd_frame.pack(pady=5)

        password_entry = ttk.Entry(pwd_frame, show="*", width=30)
        password_entry.pack(side=tk.LEFT)
        password_entry.focus()

        show_pwd = tk.BooleanVar(value=False)

        def toggle_password():
            show_pwd.set(not show_pwd.get())
            password_entry.config(show="" if show_pwd.get() else "*")

        ttk.Button(pwd_frame, text="👁", width=3, command=toggle_password).pack(side=tk.LEFT, padx=(5, 0))

        error_label = ttk.Label(main_frame, text="", foreground="red")
        error_label.pack()

        def login_wrapper():
            self._do_login_action(password_entry, error_label, dialog)

        login_btn = ttk.Button(main_frame, text="Login", command=login_wrapper)
        login_btn.pack(pady=10)

        password_entry.bind('<Return>', lambda e: self._do_login_action(password_entry, error_label, dialog))

        print("[DEBUG] Login dialog created successfully")


    def _cancel_login(self, dialog):
      """Cancel login and exit if needed"""
      self.login_dialog = None
      dialog.destroy()
      # Optionally exit app if user cancels login
      # self.root.quit()


    def _do_login_action(self, password_entry, error_label, dialog):
        """Handle login action"""
        print("=== _do_login_action CALLED ===")
        password = password_entry.get()
        print(f"Password length: {len(password)}")
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

        stored_hash = auth_hash_data['hash'].decode() if isinstance(auth_hash_data['hash'], bytes) else auth_hash_data[
          'hash']

        encryption_key = auth_manager.authenticate(
            password,
            stored_hash,
            salt_data['salt']
        )

        if encryption_key:
            self.auth_manager = auth_manager
            self.key_manager = key_manager
            key_manager.cache_encryption_key(encryption_key)

            self._init_vault_components()
            self._init_audit_system()
            self._load_vault_data()

            if hasattr(self, 'activity_monitor'):
                self.activity_monitor.reset_activity()
                print("✓ Activity monitor reset after unlock")

            if hasattr(self, 'add_button'):
                self.add_button.config(state=tk.NORMAL)
            if hasattr(self, 'edit_button'):
                self.edit_button.config(state=tk.NORMAL)
            if hasattr(self, 'delete_button'):
                self.delete_button.config(state=tk.NORMAL)
            if hasattr(self, 'gen_button'):
                self.gen_button.config(state=tk.NORMAL)

            self._init_clipboard_service()
            self.login_dialog = None
            dialog.destroy()
            if self.root.state() == 'iconic':
                self.root.deiconify()
            self.status_label.config(text="Ready", foreground="black")

        else:
            error_label.config(text="Invalid password")


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
                error_label.config(text="Please enter a password")
                return
            if pwd != conf:
                error_label.config(text="Passwords do not match")
                return
            if len(pwd) < 8:
                error_label.config(text="Password must be at least 8 characters")
                return

            from Crypts_man.src.core.vault.password_generator import PasswordGenerator
            pg = PasswordGenerator()
            strength = pg.estimate_strength(pwd)
            if strength['score'] < 2:
                if not messagebox.askyesno("Weak Password",
                                             f"Your password is {strength['rating']}.\n\n"
                                             f"Continue anyway?"):
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
        if hasattr(self, 'activity_monitor'):
            self.activity_monitor.stop_monitoring()
        if self.auth_manager:
            self.auth_manager.logout()
        self._on_user_logged_out(None)
        self.root.after(100, self._show_login)


    def _load_vault_data(self):
        """Load vault data using EntryManager"""
        with self.db.cursor() as c:
            c.execute("PRAGMA table_info(vault_entries)")
            columns = c.fetchall()
            print("=== КОЛОНКИ В ТАБЛИЦЕ ===")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        if not self._vault_ready or not self.entry_manager:
            return

        try:
            category = self.category_filter.get()
            if category == "All":
                category = None

            search = self.search_var.get().strip() or None
            entries = self.entry_manager.get_all_entries_metadata(search=search, category=category)

            table_data = []
            for entry in entries:
                table_data.append({
                    'id': str(entry.get('id', '')),
                    'title': entry.get('title', ''),
                    'username': entry.get('username', ''),
                    'password_masked': '••••••••',
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
        """Add new vault entry"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Entry")
        dialog.geometry("550x650")
        dialog.transient(self.root)
        dialog.grab_set()
        # Привязка клавиш для диалога
        dialog.bind('<Control-n>', lambda e: None)  # Блокируем создание нового окна
        dialog.bind('<Control-e>', lambda e: None)  # Блокируем редактирование
        dialog.bind('<Return>', lambda e: save())  # Enter = Save
        dialog.bind('<Escape>', lambda e: dialog.destroy())  # Escape = Cancel
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
        ttk.Label(form_frame, text="Title*: ", foreground="black").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        title_entry = ttk.Entry(form_frame, width=40)
        title_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['title'] = title_entry
        row += 1
        ttk.Label(form_frame, text="Username: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['username'] = username_entry
        row += 1
        ttk.Label(form_frame, text="Password*: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        pwd_frame = ttk.Frame(form_frame)
        pwd_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        password_entry = ttk.Entry(pwd_frame, show="*", width=25)
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        show_password_var = tk.BooleanVar(value=False)

        def toggle_password_visibility():
            if show_password_var.get():
                password_entry.config(show="")
            else:
                password_entry.config(show="*")
        eye_btn = ttk.Button(pwd_frame, text="👁", width=3,
                             command=lambda: [show_password_var.set(not show_password_var.get()),
                                              toggle_password_visibility()])
        eye_btn.pack(side=tk.RIGHT, padx=(2, 0))
        strength_frame = ttk.Frame(form_frame)
        strength_frame.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=2)
        strength_label = ttk.Label(strength_frame, text="")
        strength_label.pack(side=tk.LEFT)

        def update_strength(*args):
            pwd = password_entry.get()
            if not pwd:
                strength_label.config(text="")
                return
            strength = self.password_generator.estimate_strength(pwd)
            ratings = ["Очень слабый", "Слабый", "Средний", "Сильный", "Очень сильный"]
            colors = ["red", "orange", "gold", "lightgreen", "green"]
            strength_label.config(text=ratings[strength['score']], foreground=colors[strength['score']])
        password_entry.bind('<KeyRelease>', update_strength)

        def generate_and_set():
            def set_password(pwd):
                password_entry.delete(0, tk.END)
                password_entry.insert(0, pwd)
                update_strength()
            PasswordGeneratorDialog(dialog, self.password_generator, set_password)
        ttk.Button(pwd_frame, text="Generate", command=generate_and_set).pack(side=tk.RIGHT, padx=(5, 0))
        fields['password'] = password_entry
        row += 2
        ttk.Label(form_frame, text="URL: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        url_entry = ttk.Entry(form_frame, width=40)
        url_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['url'] = url_entry
        row += 1
        ttk.Label(form_frame, text="Category: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        category_combo = ttk.Combobox(form_frame, values=["Work", "Personal", "Finance", "Social", "Other"], width=37,
                                      state="readonly")
        category_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['category'] = category_combo
        row += 1
        ttk.Label(form_frame, text="Tags: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        tags_entry = ttk.Entry(form_frame, width=40)
        tags_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['tags'] = tags_entry
        row += 1
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
            if not any(c.isalpha() for c in title):
                messagebox.showerror("Error", "Title must contain at least one letter")
                return
            # ПРОВЕРКА URL (БЛОКИРУЮЩАЯ)
            url = fields['url'].get().strip()
            if url:
                import re
                # Простая проверка на валидный URL
                is_valid_url = ('.' in url or '://' in url or url.startswith('localhost'))
                if not is_valid_url:
                    messagebox.showerror("Error", f"'{url}' is not a valid URL!\n\nExample: https://example.com")
                    return
            tags = fields['tags'].get().strip()
            if tags:
                allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789, -_#')
                if not all(c in allowed for c in tags):
                    messagebox.showerror("Error", "Tags can only contain letters, numbers, commas, spaces, hyphens and #")
                    return
            password = fields['password'].get()
            #ПРОВЕРКА ПАРОЛЯ (БЛОКИРУЮЩАЯ)
            if not password:
                messagebox.showerror("Error", "Password cannot be empty!")
                return
            # Оценка силы пароля - запрещаем слабые и очень слабые
            strength = self.password_generator.estimate_strength(password)
            if strength['score'] <= 1:  # 0=Very Weak, 1=Weak
                messagebox.showerror(
                    "Weak Password",
                    f"Your password is {strength['rating']}.\n\n"
                    f"Please use a stronger password with:\n"
                    f"• At least 12 characters\n"
                    f"• Uppercase and lowercase letters\n"
                    f"• Numbers\n"
                    f"• Special characters (!@#$%^&*)\n\n"
                    f"Try using the password generator (Ctrl+G)."
                )
                return
            entry_data = {
                'title': title,
                'username': fields['username'].get().strip(),
                'password': password,
                'url': url,
                'category': fields['category'].get(),
                'tags': tags,
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

        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _edit_entry(self):
        """Edit selected entry"""
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
        # Привязка клавиш для диалога
        dialog.bind('<Return>', lambda e: save())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
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
        ttk.Label(form_frame, text="Title*: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        title_entry = ttk.Entry(form_frame, width=40)
        title_entry.insert(0, entry.get('title', ''))
        title_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['title'] = title_entry
        row += 1
        ttk.Label(form_frame, text="Username: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.insert(0, entry.get('username', ''))
        username_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['username'] = username_entry
        row += 1
        ttk.Label(form_frame, text="Password: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        pwd_frame = ttk.Frame(form_frame)
        pwd_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        password_entry = ttk.Entry(pwd_frame, show="*", width=30)
        password_entry.insert(0, entry.get('password', ''))
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        show_password_var = tk.BooleanVar(value=False)

        def toggle_password():
          password_entry.config(show="" if show_password_var.get() else "*")

        eye_btn = ttk.Button(pwd_frame, text="👁", width=3,
                             command=lambda: [show_password_var.set(not show_password_var.get()), toggle_password()])
        eye_btn.pack(side=tk.RIGHT, padx=(2, 0))
        strength_label = ttk.Label(form_frame, text="")
        strength_label.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=2)

        def update_strength(*args):
            pwd = password_entry.get()
            if not pwd:
                strength_label.config(text="")
                return
            strength = self.password_generator.estimate_strength(pwd)
            ratings = ["Очень слабый", "Слабый", "Средний", "Сильный", "Очень сильный"]
            colors = ["red", "orange", "gold", "lightgreen", "green"]
            strength_label.config(text=ratings[strength['score']], foreground=colors[strength['score']])

        password_entry.bind('<KeyRelease>', update_strength)

        def generate_and_set():

            def set_password(pwd):
                password_entry.delete(0, tk.END)
                password_entry.insert(0, pwd)
                update_strength()
            PasswordGeneratorDialog(dialog, self.password_generator, set_password)
        ttk.Button(pwd_frame, text="Generate", command=generate_and_set).pack(side=tk.RIGHT, padx=(2, 0))
        fields['password'] = password_entry
        row += 1
        ttk.Label(form_frame, text="URL: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        url_entry = ttk.Entry(form_frame, width=40)
        url_entry.insert(0, entry.get('url', ''))
        url_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['url'] = url_entry
        row += 1
        ttk.Label(form_frame, text="Category: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        category_combo = ttk.Combobox(form_frame, values=["Work", "Personal", "Finance", "Social", "Other"],
                                      width=37, state="readonly")
        category_combo.set(entry.get('category', ''))
        category_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['category'] = category_combo
        row += 1
        ttk.Label(form_frame, text="Tags: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        tags_entry = ttk.Entry(form_frame, width=40)
        tags_entry.insert(0, entry.get('tags', ''))
        tags_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['tags'] = tags_entry
        row += 1
        ttk.Label(form_frame, text="Notes: ").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        notes_text = tk.Text(form_frame, height=5, width=40)
        notes_text.insert(1.0, entry.get('notes', ''))
        notes_text.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        fields['notes'] = notes_text
        row += 1
        form_frame.grid_columnconfigure(1, weight=1)

        def save():
            title = fields['title'].get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required")
                return
            #  ПРОВЕРКА URL ДЛЯ EDIT
            url = fields['url'].get().strip()
            if url:
                is_valid_url = ('.' in url or '://' in url or url.startswith('localhost'))
                if not is_valid_url:
                    messagebox.showerror("Error", f"'{url}' is not a valid URL!\n\nExample: https://example.com")
                    return
            # ПРОВЕРКА ПАРОЛЯ ДЛЯ EDIT
            password = fields['password'].get()
            if not password:
                messagebox.showerror("Error", "Password cannot be empty!")
                return
            # Оценка силы пароля - запрещаем слабые и очень слабые
            strength = self.password_generator.estimate_strength(password)
            if strength['score'] <= 1:  # 0=Very Weak, 1=Weak
                messagebox.showerror(
                    "Weak Password",
                    f"Your password is {strength['rating']}.\n\n"
                    f"Please use a stronger password with:\n"
                    f"• At least 12 characters\n"
                    f"• Uppercase and lowercase letters\n"
                    f"• Numbers\n"
                    f"• Special characters (!@#$%^&*)\n\n"
                    f"Try using the password generator."
                )
                return
            updated_data = {
                'title': title,
                'username': fields['username'].get().strip(),
                'password': password,
                'url': fields['url'].get().strip(),
                'category': fields['category'].get(),
                'tags': fields['tags'].get().strip(),
                'notes': fields['notes'].get(1.0, tk.END).strip()
            }
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
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _delete_entry(self):
        """Delete selected entry"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return
        selected_rows = self.table.get_selected_rows()
        if not selected_rows:
            messagebox.showinfo("Info", "Please select an entry to delete")
            return
        count = len(selected_rows)
        msg = f"Are you sure you want to delete {count} entry{'s' if count > 1 else ''}?"
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


    def delete_entry_by_id(self, entry_id):
        """Delete entry by ID"""
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return

        if not entry_id:
            messagebox.showerror("Error", "No entry selected")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete this entry?"):
            return

        try:
            if self.entry_manager.delete_entry(str(entry_id), soft_delete=True):
                self._load_vault_data()
                self.status_label.config(text="Entry deleted")
            else:
                messagebox.showerror("Error", "Failed to delete entry")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")


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
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            self.status_label.config(text="Password copied to clipboard")
        from Crypts_man.src.gui.themes import apply_theme
        dialog = PasswordGeneratorDialog(self.root, self.password_generator, use_password)


    def _on_search_change(self, *args):
        """Handle search text change"""
        if hasattr(self, '_search_after') and self._search_after is not None:
            try:
                self.root.after_cancel(self._search_after)
            except:
                pass
        self._search_after = self.root.after(500, self._perform_search)


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
        if not messagebox.askyesno("Warning", "Restoring will overwrite current data.\nContinue?"):
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
        from Crypts_man.src.gui.dialogs.about_dialog import AboutDialog
        AboutDialog(self.root)



    def _show_export_dialog(self):
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return
        try:
            from Crypts_man.src.core.import_export.exporter import VaultExporter, ExportOptions
            from Crypts_man.src.gui.dialogs.import_export_dialogs import ExportDialog
            from Crypts_man.src.gui.themes import apply_theme
            exporter = VaultExporter(self.entry_manager, self.auth_manager, self.audit_logger)
            dialog = ExportDialog(self.root, self.db, self.auth_manager, self.entry_manager, exporter)
            apply_theme(dialog, self.current_theme)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open export dialog: {e}")
            import traceback
            traceback.print_exc()

        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _show_import_dialog(self):
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return
        try:
            from Crypts_man.src.core.import_export.importer import VaultImporter, ImportOptions
            from Crypts_man.src.gui.dialogs.import_export_dialogs import ImportDialog
            from Crypts_man.src.gui.themes import apply_theme
            importer = VaultImporter(self.entry_manager, self.audit_logger)
            dialog = ImportDialog(self.root, self.db, self.auth_manager, importer)
            apply_theme(dialog, self.current_theme)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open import dialog: {e}")
            import traceback
            traceback.print_exc()
        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _show_share_dialog(self):
        if not self._vault_ready or not self.entry_manager:
            messagebox.showwarning("Locked", "Please unlock the vault first")
            return
        selected = self.table.get_selected_row()
        if not selected:
            messagebox.showinfo("Info", "Please select an entry to share")
            return
        try:
            from Crypts_man.src.core.import_export.sharing_service import SharingService, ShareOptions
            from Crypts_man.src.core.import_export.key_exchange import KeyExchangeService, QRCodeService
            from Crypts_man.src.gui.dialogs.import_export_dialogs import ShareDialog
            from Crypts_man.src.gui.themes import apply_theme
            sharing_service = SharingService(self.db, self.entry_manager, self.audit_logger)
            key_exchange = KeyExchangeService()
            qr_service = QRCodeService()
            dialog = ShareDialog(self.root, self.db, self.entry_manager, sharing_service,
                                 key_exchange, qr_service, str(selected.get('id')))  # ← ИЗМЕНИТЬ
            apply_theme(dialog, self.current_theme)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open share dialog: {e}")
            import traceback
            traceback.print_exc()
        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _show_contacts_dialog(self):
        try:
            from Crypts_man.src.core.import_export.key_exchange import KeyExchangeService
            from Crypts_man.src.gui.dialogs.import_export_dialogs import ContactsDialog
            from Crypts_man.src.gui.themes import apply_theme
            key_exchange = KeyExchangeService()
            dialog = ContactsDialog(self.root, self.db, key_exchange)
            apply_theme(dialog, self.current_theme)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open contacts dialog: {e}")
            import traceback
            traceback.print_exc()
            """Show contacts dialog"""
            try:
                from src.core.import_export import KeyExchangeService
                from src.gui.dialogs.import_export_dialogs import ContactsDialog

                key_exchange = KeyExchangeService()
                ContactsDialog(self.root, self.db, key_exchange)
            except ImportError as e:
                messagebox.showerror("Error", f"Could not open contacts dialog: {e}")
        from src.gui.themes import apply_theme
        apply_theme(dialog, self.current_theme)


    def _quit(self):
        """Quit application"""
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            if self.auth_manager:
                self.auth_manager.logout()
            self.db.close()
            self.root.quit()
            self.root.destroy()


    def _show_clipboard_settings(self):
        if not self.clipboard:
            messagebox.showwarning("Not Ready", "Clipboard service not initialized")
            return
        from Crypts_man.src.gui.themes import apply_theme
        dialog = ClipboardSettingsDialog(self.root, self.clipboard, self.config)
        apply_theme(dialog, self.current_theme)


    def _clear_clipboard_manually(self):
        """Manually clear clipboard"""
        if self.clipboard:
            if self.clipboard.clear(force=True, reason="manual"):
                self.status_label.config(text="Clipboard cleared")
                if self.clipboard_indicator:
                    self.clipboard_indicator.update_status()


    def copy_to_clipboard(self, text: str, data_type: str = "password", entry_id: str = None):
        """Copy text to clipboard"""
        if not self.clipboard:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_label.config(text=f"Copied {data_type} (basic mode)")
            return

        if self.clipboard.copy_to_clipboard(text, data_type, entry_id):
            self.status_label.config(text=f"Copied {data_type} - will clear in {self.clipboard.timeout}s")
        else:
            self.status_label.config(text=f"Failed to copy {data_type}")


    def _test_audit(self):
        """Test audit logging manually"""
        if not self.audit_logger:
            messagebox.showwarning("No Audit", "Audit logger not initialized")
            return

        from Crypts_man.src.core.audit.audit_logger import AuditEventType, AuditSeverity

        seq = self.audit_logger.log_event(
            event_type="test.manual",
            severity="INFO",
            source="test_button",
            details={'message': 'Manual test entry'},
            user_id='test_user'
        )

        messagebox.showinfo("Test", f"Audit entry created with sequence: {seq}")

        # Проверим сколько всего записей
        entries = self.audit_logger.get_entries(limit=10)
        messagebox.showinfo("Audit Stats", f"Total entries in log: {len(entries)}")


    def _get_app_icon_path(self):
        """Get path to application icon"""
        # Варианты путей для поиска иконки
        base_dir = Path(__file__).parent.parent  # Crypts_man/

        icon_paths = [
            base_dir / "resources" / "icons" / "app_icon.ico",
            base_dir / "resources" / "icons" / "app_icon.png",
            base_dir / "resources" / "icons" / "tray_icon.ico",
            base_dir / "resources" / "icons" / "tray_icon.png",
            base_dir / "resources" / "icons" / "icon.ico",
            base_dir / "resources" / "app_icon.ico",
        ]

        for path in icon_paths:
            if path.exists():
                print(f"✓ Found icon: {path}")
                return str(path)

        print("⚠ No icon found at:")
        for path in icon_paths:
            print(f"  - {path}")
        return None


    def _set_window_icon(self):
        """Set window icon"""
        icon_path = self._get_app_icon_path()
        if icon_path and os.path.exists(icon_path):
            try:
                # Для Windows .ico файлов
                if icon_path.endswith('.ico'):
                    self.root.iconbitmap(icon_path)
                    print(f"✓ Window icon set (iconbitmap): {icon_path}")
                else:
                    # Для PNG
                    img = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(True, img)
                    self.root._icon_image = img  # Keep reference to prevent garbage collection
                    print(f"✓ Window icon set (iconphoto): {icon_path}")
            except Exception as e:
                print(f"⚠ Failed to set icon: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠ No window icon found, using default")


    def toggle_favorite(self, entry_id: str):
        """Переключить избранное (звёздочка)"""
        if not self._vault_ready or not self.entry_manager:
            return
        try:
            self.entry_manager.toggle_favorite(entry_id)
            self._load_vault_data()  # Обновить таблицу
        except Exception as e:
            print(f"Error toggling favorite: {e}")

    def run(self):
        """Run the main application"""
        self.root.mainloop()
