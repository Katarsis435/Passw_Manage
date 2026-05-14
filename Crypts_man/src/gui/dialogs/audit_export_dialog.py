# Crypts_man/src/gui/dialogs/audit_export_dialog.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading
import os


class AuditExportDialog:
    """Export audit logs in various formats"""

    def __init__(self, parent, audit_logger, audit_signer=None):
        self.parent = parent
        self.audit_logger = audit_logger
        self.audit_signer = audit_signer

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Export Audit Logs")
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

        # Format selection
        format_frame = ttk.LabelFrame(main_frame, text="Export Format", padding="10")
        format_frame.pack(fill=tk.X, pady=5)

        self.format_var = tk.StringVar(value="json")

        ttk.Radiobutton(format_frame, text="Signed JSON (with signatures)",
                        variable=self.format_var, value="json_signed").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(format_frame, text="JSON (without signatures)",
                        variable=self.format_var, value="json").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(format_frame, text="CSV (for spreadsheets)",
                        variable=self.format_var, value="csv").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(format_frame, text="PDF Report",
                        variable=self.format_var, value="pdf").pack(anchor=tk.W, pady=2)

        # Date range
        range_frame = ttk.LabelFrame(main_frame, text="Date Range", padding="10")
        range_frame.pack(fill=tk.X, pady=5)

        range_row = ttk.Frame(range_frame)
        range_row.pack(fill=tk.X)

        ttk.Label(range_row, text="From:").pack(side=tk.LEFT)
        self.start_date = ttk.Entry(range_row, width=20)
        self.start_date.pack(side=tk.LEFT, padx=5)

        ttk.Label(range_row, text="To:").pack(side=tk.LEFT, padx=(10, 0))
        self.end_date = ttk.Entry(range_row, width=20)
        self.end_date.pack(side=tk.LEFT, padx=5)

        # Buttons for quick ranges
        quick_frame = ttk.Frame(range_frame)
        quick_frame.pack(fill=tk.X, pady=5)
        ttk.Button(quick_frame, text="All", command=self._set_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Last 7 Days", command=lambda: self._set_range('week')).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Last 30 Days", command=lambda: self._set_range('month')).pack(side=tk.LEFT, padx=2)

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)

        self.include_details = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include full entry details",
                        variable=self.include_details).pack(anchor=tk.W)

        self.encrypt_export = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Encrypt export file (requires master password)",
                        variable=self.encrypt_export).pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Export", command=self._export).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _set_all(self):
        """Clear date filters"""
        self.start_date.delete(0, tk.END)
        self.end_date.delete(0, tk.END)

    def _set_range(self, range_type):
        """Set date range preset"""
        from datetime import datetime, timedelta
        now = datetime.now()

        if range_type == 'week':
            start = now - timedelta(days=7)
        elif range_type == 'month':
            start = now - timedelta(days=30)
        else:
            return

        self.start_date.delete(0, tk.END)
        self.start_date.insert(0, start.date().isoformat())
        self.end_date.delete(0, tk.END)
        self.end_date.insert(0, now.date().isoformat())

    def _export(self):
        """Perform export"""
        # Get date range
        start = self.start_date.get() or None
        end = self.end_date.get() or None

        # Get file path
        format_type = self.format_var.get()
        ext = {
            'json': '.json',
            'json_signed': '.json',
            'csv': '.csv',
            'pdf': '.pdf'
        }.get(format_type, '.json')

        file_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(f"{format_type.upper()} files", f"*{ext}"), ("All files", "*.*")]
        )

        if not file_path:
            return

        # Confirm if encryption requested
        password = None
        if self.encrypt_export.get():
            from tkinter import simpledialog
            password = simpledialog.askstring("Encryption Password",
                                              "Enter encryption password:",
                                              show='*', parent=self.dialog)
            if not password:
                messagebox.showwarning("Cancelled", "Export cancelled - no password provided")
                return

        # Show progress
        progress = tk.Toplevel(self.dialog)
        progress.title("Exporting...")
        progress.geometry("300x100")
        progress.transient(self.dialog)

        label = ttk.Label(progress, text="Exporting audit logs...")
        label.pack(pady=20)

        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(fill=tk.X, padx=20)
        progress_bar.start()

        def do_export():
            try:
                # Fetch entries
                entries = self.audit_logger.get_entries(
                    start_date=start, end_date=end, limit=10000
                )

                # Format
                from Crypts_man.src.core.audit.log_formatters import LogFormatter

                if format_type == 'csv':
                    content = LogFormatter.format_csv(entries)
                elif format_type == 'pdf':
                    content = LogFormatter.format_pdf(entries)
                elif format_type == 'json_signed' and self.audit_signer:
                    public_key = self.audit_signer.get_public_key() or ''
                    algorithm = self.audit_signer.get_algorithm()
                    content = LogFormatter.format_signed_export(entries, public_key, algorithm)
                else:  # json
                    content = LogFormatter.format_json(entries, include_signatures=False)

                # Save to file
                if isinstance(content, bytes):
                    with open(file_path, 'wb') as f:
                        f.write(content)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                # Encrypt if requested
                if password:
                    self._encrypt_file(file_path, password)

                self.dialog.after(0, lambda: self._export_complete(file_path, progress))
            except Exception as e:
                self.dialog.after(0, lambda: self._export_error(str(e), progress))

        threading.Thread(target=do_export, daemon=True).start()

    def _encrypt_file(self, file_path, password):
        """Encrypt exported file"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import os

            # Read file
            with open(file_path, 'rb') as f:
                data = f.read()

            # Derive key
            import hashlib
            key = hashlib.pbkdf2_hmac('sha256', password.encode(), b'cryptosafe_export', 100000, 32)

            # Encrypt
            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, data, None)

            # Write encrypted file
            with open(file_path + '.encrypted', 'wb') as f:
                f.write(nonce + ciphertext)

            # Remove original
            os.remove(file_path)
        except Exception as e:
            raise Exception(f"Encryption failed: {e}")

    def _export_complete(self, file_path, progress_dialog):
        """Handle export completion"""
        progress_dialog.destroy()
        messagebox.showinfo("Export Complete", f"Audit logs exported to:\n{file_path}")
        self.dialog.destroy()

    def _export_error(self, error, progress_dialog):
        """Handle export error"""
        progress_dialog.destroy()
        messagebox.showerror("Export Failed", f"Error exporting logs: {error}")
