# Crypts_man/src/gui/dialogs/audit_viewer_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
import threading


class AuditViewerDialog:
    """Audit log viewer dialog with filtering and visualization"""


    def __init__(self, parent, audit_logger, audit_verifier):
        self.parent = parent
        self.audit_logger = audit_logger
        self.audit_verifier = audit_verifier
        self.current_page = 0
        self.page_size = 50
        self.total_entries = 0
        # Создаем окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Audit Log Viewer")
        self.dialog.geometry("1200x700")
        self.dialog.minsize(900, 600)
        self.dialog.transient(parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        self._create_widgets()
        self._load_entries()
        self._center_dialog()


    def _on_close(self):
        """Закрыть окно"""
        self.dialog.destroy()


    def _center_dialog(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (700 // 2)
        self.dialog.geometry(f"+{x}+{y}")


    def _create_widgets(self):
        """Create dialog widgets"""

        # Canvas для скролла
        main_canvas = tk.Canvas(self.dialog)
        main_scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        main_canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")

        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== FILTER FRAME ==========
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)

        # Row 1: Event Type + Severity
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Event Type:").pack(side=tk.LEFT, padx=5)
        self.event_type_var = tk.StringVar(value="All")
        self.event_type_combo = ttk.Combobox(row1, textvariable=self.event_type_var, width=25)
        self.event_type_combo['values'] = ['All'] + self._get_event_types()
        self.event_type_combo.set('All')
        self.event_type_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filters())
        self.event_type_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="Severity:").pack(side=tk.LEFT, padx=5)
        self.severity_var = tk.StringVar(value="All")
        self.severity_combo = ttk.Combobox(row1, textvariable=self.severity_var, width=15)
        self.severity_combo['values'] = ['All', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
        self.severity_combo.set('All')
        self.severity_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filters())
        self.severity_combo.pack(side=tk.LEFT, padx=5)

        # Row 2: Date Range
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="Date Range:").pack(side=tk.LEFT, padx=5)

        ttk.Button(row2, text="Today", command=lambda: self._set_date_range('today')).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Last 7 Days", command=lambda: self._set_date_range('week')).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Last 30 Days", command=lambda: self._set_date_range('month')).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="Clear", command=self._clear_date_range).pack(side=tk.LEFT, padx=2)

        ttk.Label(row2, text="From (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        self.start_date_var = tk.StringVar()
        self.start_date_entry = ttk.Entry(row2, textvariable=self.start_date_var, width=15)
        self.start_date_entry.pack(side=tk.LEFT, padx=2)
        self.start_date_entry.bind('<Return>', lambda e: self._apply_filters())

        ttk.Label(row2, text="To (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        self.end_date_var = tk.StringVar()
        self.end_date_entry = ttk.Entry(row2, textvariable=self.end_date_var, width=15)
        self.end_date_entry.pack(side=tk.LEFT, padx=2)
        self.end_date_entry.bind('<Return>', lambda e: self._apply_filters())

        # Row 3: Buttons
        row3 = ttk.Frame(filter_frame)
        row3.pack(fill=tk.X, pady=5)

        ttk.Button(row3, text="Apply Filters", command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="Reset", command=self._reset_filters).pack(side=tk.LEFT, padx=2)

        # ========== TABLE FRAME ==========
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ('seq', 'timestamp', 'event_type', 'severity', 'user_id', 'source', 'details')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='browse', height=15)

        self.tree.heading('seq', text='#')
        self.tree.heading('timestamp', text='Timestamp')
        self.tree.heading('event_type', text='Event Type')
        self.tree.heading('severity', text='Severity')
        self.tree.heading('user_id', text='User')
        self.tree.heading('source', text='Source')
        self.tree.heading('details', text='Details')

        self.tree.column('seq', width=50, minwidth=50)
        self.tree.column('timestamp', width=180, minwidth=150)
        self.tree.column('event_type', width=200, minwidth=150)
        self.tree.column('severity', width=80, minwidth=70)
        self.tree.column('user_id', width=100, minwidth=80)
        self.tree.column('source', width=120, minwidth=100)
        self.tree.column('details', width=400, minwidth=200)

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # ========== DETAILS FRAME ==========
        details_frame = ttk.LabelFrame(main_frame, text="Entry Details", padding="10")
        details_frame.pack(fill=tk.X, pady=5)

        self.details_text = tk.Text(details_frame, height=8, wrap=tk.WORD, state='disabled')
        self.details_text.pack(fill=tk.BOTH, expand=True)

        details_scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ========== STATUS FRAME ==========
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(status_frame, text="")
        self.status_label.pack(side=tk.LEFT)

        self.verify_status_label = ttk.Label(status_frame, text="", foreground="green")
        self.verify_status_label.pack(side=tk.RIGHT)

        # ========== PAGINATION FRAME ==========
        page_frame = ttk.Frame(main_frame)
        page_frame.pack(fill=tk.X, pady=5)

        ttk.Button(page_frame, text="<<", command=self._first_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(page_frame, text="<", command=self._prev_page).pack(side=tk.LEFT, padx=2)

        self.page_label = ttk.Label(page_frame, text="Page 0 / 0")
        self.page_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(page_frame, text=">", command=self._next_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(page_frame, text=">>", command=self._last_page).pack(side=tk.LEFT, padx=2)

        ttk.Button(page_frame, text="Refresh", command=self._load_entries).pack(side=tk.RIGHT, padx=2)
        ttk.Button(page_frame, text="Export", command=self._export).pack(side=tk.RIGHT, padx=2)
        ttk.Button(page_frame, text="Verify Integrity", command=self._verify_integrity).pack(side=tk.RIGHT, padx=2)


    def _get_event_types(self):
        """Get list of event types from database"""
        try:
            stats = self.audit_logger.get_stats()
            event_types = stats.get('by_event_type', [])
            if isinstance(event_types, list):
                return [e.get('event_type', '') for e in event_types if e.get('event_type')]
            return []
        except Exception as e:
            print(f"Error getting event types: {e}")
            return []


    def _set_date_range(self, range_type):
        """Set date range preset"""
        now = datetime.now()
        if range_type == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_type == 'week':
            start = now - timedelta(days=7)
            end = now
        elif range_type == 'month':
            start = now - timedelta(days=30)
            end = now
        else:
            return
        self.start_date_var.set(start.strftime("%Y-%m-%d"))
        self.end_date_var.set(end.strftime("%Y-%m-%d"))
        self._apply_filters()


    def _clear_date_range(self):
        """Clear date range filters"""
        self.start_date_var.set('')
        self.end_date_var.set('')
        self._apply_filters()


    def _apply_filters(self):
        """Apply filters and reload"""
        self.current_page = 0
        self._load_entries()


    def _reset_filters(self):
        """Reset all filters"""
        self.event_type_var.set('All')
        self.severity_var.set('All')
        self.start_date_var.set('')
        self.end_date_var.set('')
        self.current_page = 0
        self._load_entries()


    def _load_entries(self):
        """Load entries from database"""
        def load():
            try:
                event_type = None if self.event_type_var.get() == 'All' else self.event_type_var.get()
                severity = None if self.severity_var.get() == 'All' else self.severity_var.get()
                start_date = self.start_date_var.get() or None
                end_date = self.end_date_var.get() or None
                # Получаем общее количество
                total = self.audit_logger.get_entry_count(
                    event_type=event_type,
                    severity=severity
                )
                self.total_entries = total
                # Получаем записи для текущей страницы
                offset = self.current_page * self.page_size
                entries = self.audit_logger.get_entries(
                    event_type=event_type,
                    severity=severity,
                    start_date=start_date,
                    end_date=end_date,
                    limit=self.page_size,
                    offset=offset
                )
                self.dialog.after(0, lambda: self._display_entries(entries))
            except Exception as e:
                self.dialog.after(0, lambda: self._show_error(str(e)))
                import traceback
                traceback.print_exc()
        threading.Thread(target=load, daemon=True).start()


    def _display_entries(self, entries):
        """Display entries in tree"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not entries:
            self.status_label.config(text="No entries found")
            total_pages = 1
            self.page_label.config(text=f"Page 1 / 1 (0 entries)")
            return
        for entry in entries:
            # Get details
            entry_data = entry.get('entry_data', {})
            if isinstance(entry_data, str):
                try:
                    entry_data = json.loads(entry_data)
                except:
                    entry_data = {'raw': entry_data[:100]}
            if isinstance(entry_data, dict):
                details_summary = entry_data.get('message', '') or entry_data.get('title', '') or str(entry_data)[:80]
            else:
                details_summary = str(entry_data)[:80]
            severity = entry.get('severity', '')
            tags = ()
            if severity == 'CRITICAL':
                tags = ('critical',)
            elif severity == 'ERROR':
                tags = ('error',)
            elif severity == 'WARN':
                tags = ('warning',)
            self.tree.insert('', 'end', values=(
                entry.get('sequence_number', ''),
                entry.get('timestamp', '')[:19] if entry.get('timestamp') else '',
                entry.get('event_type', ''),
                severity,
                entry.get('user_id', ''),
                entry.get('source', ''),
                details_summary
            ), tags=tags)
        # Configure colors
        self.tree.tag_configure('critical', background='#ffcccc')
        self.tree.tag_configure('error', background='#ffe6cc')
        self.tree.tag_configure('warning', background='#ffffcc')
        # Update pagination
        total_pages = (self.total_entries + self.page_size - 1) // self.page_size if self.total_entries > 0 else 1
        self.page_label.config(text=f"Page {self.current_page + 1} / {total_pages} ({self.total_entries} entries)")
        self.status_label.config(text=f"Loaded {len(entries)} entries")


    def _on_select(self, event):
        """Handle entry selection"""
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return
        seq = values[0]
        try:
            entries = self.audit_logger.get_entries(start_seq=int(seq), end_seq=int(seq), limit=1)
            if entries:
                entry = entries[0]
                details = entry.get('entry_data', {})
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except:
                        pass
                details_text = json.dumps(details, indent=2, ensure_ascii=False, default=str)
                self.details_text.config(state='normal')
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(tk.END, f"Sequence: {entry.get('sequence_number')}\n")
                self.details_text.insert(tk.END, f"Timestamp: {entry.get('timestamp')}\n")
                self.details_text.insert(tk.END, f"Event: {entry.get('event_type')}\n")
                self.details_text.insert(tk.END, f"Severity: {entry.get('severity')}\n")
                self.details_text.insert(tk.END, f"User: {entry.get('user_id')}\n")
                self.details_text.insert(tk.END, f"Source: {entry.get('source')}\n")
                self.details_text.insert(tk.END, f"Hash: {entry.get('entry_hash', '')[:48]}...\n")
                self.details_text.insert(tk.END, f"\nDetails:\n{details_text}")
                self.details_text.config(state='disabled')
        except Exception as e:
            self.details_text.config(state='normal')
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Error loading details: {e}")
            self.details_text.config(state='disabled')


    def _first_page(self):
        self.current_page = 0
        self._load_entries()


    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._load_entries()


    def _next_page(self):
        max_page = (self.total_entries + self.page_size - 1) // self.page_size if self.total_entries > 0 else 1
        if self.current_page + 1 < max_page:
            self.current_page += 1
            self._load_entries()


    def _last_page(self):
        max_page = (self.total_entries + self.page_size - 1) // self.page_size if self.total_entries > 0 else 1
        self.current_page = max_page - 1
        self._load_entries()


    def _verify_integrity(self):
        """Run integrity verification"""
        def verify():
            try:
                result = self.audit_verifier.verify_full()
                self.dialog.after(0, lambda: self._show_verification_result(result))
            except Exception as e:
                self.dialog.after(0, lambda: self._show_error(f"Verification failed: {e}"))
        self.verify_status_label.config(text="Verifying...", foreground="orange")
        threading.Thread(target=verify, daemon=True).start()


    def _show_verification_result(self, result):
        """Show verification result"""
        if result.verified:
            self.verify_status_label.config(text="✓ Integrity Verified", foreground="green")
            messagebox.showinfo(
                "Verification Complete",
                f"Audit log integrity verified!\n\n"
                f"Entries checked: {result.total_entries}\n"
                f"Valid signatures: {result.valid_entries}\n"
                f"Time: {result.verification_time:.2f}s"
            )
        else:
            self.verify_status_label.config(text="✗ Tampering Detected!", foreground="red")
            messagebox.showwarning(
                "Integrity Check Failed",
                f"Audit log tampering detected!\n\n"
                f"Invalid signatures: {len(result.invalid_signatures)}\n"
                f"Chain breaks: {len(result.chain_breaks)}\n"
                f"Hash mismatches: {len(result.hash_mismatches)}"
            )


    def _export(self):
        """Export audit logs"""
        try:
            from Crypts_man.src.gui.dialogs.audit_export_dialog import AuditExportDialog
            AuditExportDialog(self.dialog, self.audit_logger, None)
        except ImportError as e:
            messagebox.showerror("Error", f"Could not open export dialog: {e}")


    def _show_error(self, error):
        """Show error message"""
        messagebox.showerror("Error", error)
        self.status_label.config(text=f"Error: {error}")
