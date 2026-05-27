from __future__ import annotations

import hashlib
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

import qrcode

from src.core.import_export.exporter import ExportOptions
from src.core.import_export.importer import ImportOptions
from src.core.import_export.sharing_service import ShareOptions


EXPORT_FORMAT_HELP = {
    "encrypted_json": "Encrypted JSON — основной безопасный формат CryptoSafe Manager.\nПодходит для резервных копий.",
    "csv": "CSV — простой табличный формат.\nПодходит для миграции в другие менеджеры паролей.",
    "bitwarden_json": "Bitwarden JSON — формат совместимости с Bitwarden.",
    "lastpass_csv": "LastPass CSV — формат совместимости с LastPass."
}

EXPORT_METHOD_HELP = {
    "password": "Password — файл защищён паролем экспорта.",
    "public_key": "Public key — файл зашифрован на публичный ключ получателя."
}

IMPORT_MODE_HELP = {
    "merge": "Merge — добавить новые записи в текущее хранилище.",
    "replace": "Replace — очистить текущее хранилище и загрузить импорт заново."
}


def _stored_auth_hash(db) -> str | None:
    auth_hash_data = db.get_auth_hash()
    if not auth_hash_data or not auth_hash_data.get("hash"):
        return None
    stored = auth_hash_data["hash"]
    return stored.decode("utf-8") if isinstance(stored, bytes) else str(stored)


def verify_master_password(auth, db, password: str) -> bool:
    """Confirm master password before import/export (EXP-4, IMP-4)."""
    if not auth or not auth.is_authenticated():
        print(f"DEBUG: auth={auth}, is_authenticated={auth.is_authenticated() if auth else None}")
        return False
    stored_hash = _stored_auth_hash(db)
    if not stored_hash:
        print("DEBUG: No stored hash found")
        return False
    print(f"DEBUG: Verifying password, stored_hash type={type(stored_hash)}")
    # Убедимся, что stored_hash это строка
    if isinstance(stored_hash, bytes):
        stored_hash = stored_hash.decode('utf-8')
    result = auth.key_manager.verify_password(password, stored_hash)
    print(f"DEBUG: Verification result = {result}")
    return result


class QRViewerDialog(tk.Toplevel):
    def __init__(self, master, payload_text: str, title: str = "QR Viewer"):
        super().__init__(master)
        self.title(title)
        self.geometry("720x760")
        self.payload_text = payload_text
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="QR payload preview", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        preview = tk.Text(top, height=6, wrap="word")
        preview.pack(fill="x", expand=False, pady=(8, 0))
        preview.insert("1.0", self.payload_text[:2000])
        preview.configure(state="disabled")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(body, bg="white")
        canvas.pack(fill="both", expand=True)

        self.update_idletasks()
        self._draw_qr(canvas, self.payload_text)

    @staticmethod
    def _draw_qr(canvas: tk.Canvas, text: str):
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=4)
        qr.add_data(text)
        qr.make(fit=True)
        matrix = qr.get_matrix()

        canvas_width = max(600, canvas.winfo_width())
        canvas_height = max(600, canvas.winfo_height())

        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        if not rows or not cols:
            return

        cell = min((canvas_width - 40) // cols, (canvas_height - 40) // rows)
        cell = max(4, cell)
        offset_x = 20
        offset_y = 20

        canvas.delete("all")
        canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill="white", outline="white")

        for y, row in enumerate(matrix):
            for x, bit in enumerate(row):
                if bit:
                    x1 = offset_x + x * cell
                    y1 = offset_y + y * cell
                    canvas.create_rectangle(x1, y1, x1 + cell, y1 + cell, fill="black", outline="black")


class ExportDialog(tk.Toplevel):
    def __init__(self, master, db, auth, entry_manager, exporter):
        super().__init__(master)
        self.title("Vault Export")
        self.geometry("900x620")
        self.minsize(800, 560)
        self.db = db
        self.auth = auth
        self.entry_manager = entry_manager
        self.exporter = exporter
        self.entries = self.entry_manager.get_all_entries()
        self._build()
        self._update_help()

    def _build(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        content = ttk.Frame(root)
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        ttk.Label(left, text="Export Settings", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

        self.format_var = tk.StringVar(value="encrypted_json")
        self.compress_var = tk.BooleanVar(value=False)
        self.include_notes_var = tk.BooleanVar(value=True)
        self.include_tags_var = tk.BooleanVar(value=True)
        self.key_bits_var = tk.StringVar(value="256")
        self.method_var = tk.StringVar(value="password")

        ttk.Label(left, text="Format").pack(anchor="w", pady=(8, 0))
        format_box = ttk.Combobox(left, textvariable=self.format_var,
                                  values=["encrypted_json", "csv", "bitwarden_json", "lastpass_csv"],
                                  state="readonly")
        format_box.pack(fill="x")
        format_box.bind("<<ComboboxSelected>>", lambda e: self._update_help())

        ttk.Checkbutton(left, text="Include notes", variable=self.include_notes_var).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(left, text="Include tags", variable=self.include_tags_var).pack(anchor="w")
        ttk.Checkbutton(left, text="Compress (GZIP)", variable=self.compress_var).pack(anchor="w")

        ttk.Label(left, text="Encryption method").pack(anchor="w", pady=(10, 0))
        method_box = ttk.Combobox(left, textvariable=self.method_var,
                                  values=["password", "public_key"], state="readonly")
        method_box.pack(fill="x")
        method_box.bind("<<ComboboxSelected>>", lambda e: self._update_help())

        ttk.Label(left, text="AES key size").pack(anchor="w", pady=(8, 0))
        ttk.Combobox(left, textvariable=self.key_bits_var, values=["128", "256"], state="readonly").pack(fill="x")

        ttk.Label(left, text="Export password (for password method)").pack(anchor="w", pady=(10, 0))
        self.export_password_entry = ttk.Entry(left, show="*")
        self.export_password_entry.pack(fill="x", pady=(2, 0))

        ttk.Label(left, text="Recipient public key (PEM, for public key method)").pack(anchor="w", pady=(10, 0))
        self.public_key_text = tk.Text(left, height=3, wrap="word")
        self.public_key_text.pack(fill="x")

        entries_frame = ttk.LabelFrame(left, text="Select entries to export")
        entries_frame.pack(fill="both", expand=True, pady=(10, 0))

        inner_canvas = tk.Canvas(entries_frame, height=160)
        inner_scrollbar_y = ttk.Scrollbar(entries_frame, orient="vertical", command=inner_canvas.yview)
        inner_scrollable = ttk.Frame(inner_canvas)

        inner_scrollable.bind(
            "<Configure>",
            lambda e: inner_canvas.configure(scrollregion=inner_canvas.bbox("all"))
        )
        inner_canvas.create_window((0, 0), window=inner_scrollable, anchor="nw")
        inner_canvas.configure(yscrollcommand=inner_scrollbar_y.set)

        self.entry_vars: dict[str, tk.BooleanVar] = {}
        for row in self.entries:
            entry_id = str(row["id"])
            var = tk.BooleanVar(value=True)
            self.entry_vars[entry_id] = var
            title = str(row.get("title", ""))[:40]
            username = str(row.get("username", ""))[:30]
            ttk.Checkbutton(
                inner_scrollable,
                text=f"{title} | {username}",
                variable=var
            ).pack(fill="x", padx=5, pady=2, anchor="w")

        inner_canvas.pack(side="left", fill="both", expand=True)
        inner_scrollbar_y.pack(side="right", fill="y")

        ttk.Label(right, text="Help", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.help_text = tk.Text(right, height=14, wrap="word", state="disabled")
        self.help_text.pack(fill="x", expand=False)

        ttk.Label(right, text="Preview", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.preview = tk.Text(right, height=12, wrap="word")
        self.preview.pack(fill="both", expand=True)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Button(bottom, text="Select All", command=self._select_all).pack(side="left")
        ttk.Button(bottom, text="Preview", command=self._preview).pack(side="left", padx=(8, 0))
        ttk.Button(bottom, text="Export", command=self._export).pack(side="right")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))

    def _update_help(self):
        fmt = self.format_var.get()
        method = self.method_var.get()

        notes = [
            "Format:", EXPORT_FORMAT_HELP.get(fmt, ""), "",
            "Encryption:", EXPORT_METHOD_HELP.get(method, ""), "",
            "Recommendations:"
        ]

        if fmt == "encrypted_json":
            notes.append("- Best for backup and migration between CryptoSafe instances.")
        if fmt == "csv":
            notes.append("- Use only if you need a universal spreadsheet format.")
        if fmt == "bitwarden_json":
            notes.append("- Use this format to migrate to Bitwarden.")
        if fmt == "lastpass_csv":
            notes.append("- Use this format to import into LastPass.")
        if method == "password":
            notes.append("- Recipient needs the export password (separate from master password).")
        if method == "public_key":
            notes.append("- Recipient must have the corresponding private key.")

        self.help_text.config(state="normal")
        self.help_text.delete("1.0", "end")
        self.help_text.insert("1.0", "\n".join(notes))
        self.help_text.config(state="disabled")

    def _select_all(self):
        for var in self.entry_vars.values():
            var.set(True)

    def _selected_entry_ids(self) -> list[str]:
        return [entry_id for entry_id, var in self.entry_vars.items() if var.get()]

    def _build_options(self) -> ExportOptions:
        return ExportOptions(
            export_format=self.format_var.get(),
            include_notes=self.include_notes_var.get(),
            include_tags=self.include_tags_var.get(),
            compress=self.compress_var.get(),
            key_bits=int(self.key_bits_var.get()),
            selected_entry_ids=self._selected_entry_ids()
        )

    def _preview(self):
        selected = self._selected_entry_ids()
        if not selected:
            messagebox.showwarning("Preview", "Select at least one entry to export.")
            return

        options = self._build_options()
        entries_data = []
        for entry_id in selected[:5]:
            entry = self.entry_manager.get_entry(entry_id)
            if entry:
                entries_data.append({
                    "id": entry_id,
                    "title": entry.get("title", ""),
                    "username": entry.get("username", ""),
                    "url": entry.get("url", "")
                })

        preview_data = {
            "format": options.export_format,
            "entry_count": len(selected),
            "entries_preview": entries_data,
            "include_notes": options.include_notes,
            "include_tags": options.include_tags,
            "compress": options.compress,
            "method": self.method_var.get()
        }
        if len(selected) > 5:
            preview_data["note"] = f"... and {len(selected) - 5} more entries"

        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(preview_data, indent=2, ensure_ascii=False))

    def _export(self):
        selected = self._selected_entry_ids()
        if not selected:
            messagebox.showerror("Error", "Select at least one entry to export.")
            return

        confirm = simpledialog.askstring(
            "Confirm",
            "Enter master password to confirm export:",
            show="*",
            parent=self
        )
        if not confirm:
            return

        if not verify_master_password(self.auth, self.db, confirm):
            messagebox.showerror("Error", "Master password verification failed")
            return

        options = self._build_options()
        method = self.method_var.get()
        password = None
        public_key_pem = None

        if method == "password":
            password = self.export_password_entry.get().strip()
            if not password:
                messagebox.showerror("Error", "Export password is required for password encryption.")
                return
        else:
            public_key_raw = self.public_key_text.get("1.0", "end").strip()
            if not public_key_raw:
                messagebox.showerror("Error", "Recipient public key is required.")
                return
            public_key_pem = public_key_raw.encode("utf-8")

        try:
            package = self.exporter.export_vault(
                password=password,
                public_key_pem=public_key_pem,
                options=options
            )
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return

        default_ext = ".json"
        if options.export_format in {"csv", "lastpass_csv"}:
            default_ext = ".csv"

        path = filedialog.asksaveasfilename(defaultextension=default_ext)
        if not path:
            return

        raw = json.dumps(package, indent=2).encode("utf-8")
        try:
            with open(path, "wb") as f:
                f.write(raw)
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not save file:\n{exc}")
            return

        self.db.insert_import_export_history(
            operation_type="export",
            data_format=options.export_format,
            encryption_used=method,
            entry_count=package.get("entry_count", len(selected)),
            file_size=len(raw),
            checksum=hashlib.sha256(raw).hexdigest(),
            verification_status="ok",
            created_at=package.get("timestamp", "")
        )

        messagebox.showinfo("Export", f"Export saved to:\n{path}")
        self.destroy()


class ImportDialog(tk.Toplevel):
    def __init__(self, master, db, auth, importer):
        super().__init__(master)
        self.title("Vault Import")
        self.geometry("1020x760")
        self.minsize(940, 700)
        self.db = db
        self.auth = auth
        self.importer = importer
        self.raw = None
        self._build()
        self._update_help()

    def _build(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        content = ttk.Frame(root)
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        top = ttk.Frame(left)
        top.pack(fill="x")

        self.format_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="merge")
        self.dup_var = tk.StringVar(value="skip")

        ttk.Button(top, text="Choose File", command=self._choose_file).pack(side="left")
        ttk.Label(top, text="Format").pack(side="left", padx=(12, 4))
        format_box = ttk.Combobox(
            top, textvariable=self.format_var,
            values=["", "encrypted_json", "csv", "bitwarden_json", "lastpass_csv"],
            width=18
        )
        format_box.pack(side="left")
        format_box.bind("<<ComboboxSelected>>", lambda e: self._update_help())

        ttk.Label(top, text="Mode").pack(side="left", padx=(12, 4))
        mode_box = ttk.Combobox(top, textvariable=self.mode_var, values=["merge", "replace"],
                                width=12, state="readonly")
        mode_box.pack(side="left")
        mode_box.bind("<<ComboboxSelected>>", lambda e: self._update_help())

        ttk.Label(top, text="Duplicates").pack(side="left", padx=(12, 4))
        ttk.Combobox(top, textvariable=self.dup_var, values=["skip"], width=12, state="readonly").pack(side="left")

        pw_frame = ttk.Frame(left)
        pw_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(pw_frame, text="Import / export password (for encrypted native JSON)").pack(anchor="w")
        self.password_entry = ttk.Entry(pw_frame, show="*")
        self.password_entry.pack(fill="x")

        ttk.Label(left, text="Preview / Summary", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.preview = tk.Text(left, wrap="word")
        self.preview.pack(fill="both", expand=True)

        ttk.Label(right, text="Help", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.help_text = tk.Text(right, wrap="word", height=18)
        self.help_text.pack(fill="x", expand=False)

        tips = ttk.LabelFrame(right, text="What to choose")
        tips.pack(fill="x", pady=(10, 0))
        ttk.Label(tips, text=(
            "• encrypted_json — if exported from CryptoSafe Manager\n"
            "• csv — for simple table files\n"
            "• bitwarden_json — if exported from Bitwarden\n"
            "• lastpass_csv — if exported from LastPass\n"
            "• merge — safer for normal import\n"
            "• replace — only if you want to completely replace the vault"
        ), justify="left").pack(anchor="w", padx=10, pady=8)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Button(bottom, text="Dry Run", command=self._dry_run).pack(side="left")
        ttk.Button(bottom, text="Import", command=self._import).pack(side="right")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))

    def _update_help(self):
        fmt = self.format_var.get()
        mode = self.mode_var.get()

        notes = ["Format:"]
        if fmt == "encrypted_json":
            notes.append("Encrypted JSON — native CryptoSafe Manager format.")
        elif fmt == "csv":
            notes.append("CSV — simple table format.")
        elif fmt == "bitwarden_json":
            notes.append("Bitwarden JSON — for Bitwarden exports.")
        elif fmt == "lastpass_csv":
            notes.append("LastPass CSV — for LastPass exports.")
        else:
            notes.append("Auto-detection — will try to detect format automatically.")

        notes.extend(["", "Mode:", IMPORT_MODE_HELP.get(mode, ""), "", "Notes:"])

        if fmt == "encrypted_json":
            notes.append("- If the file is password-protected, enter the export password above.")
        if mode == "replace":
            notes.append("- All current entries will be deleted before import.")

        self.help_text.delete("1.0", "end")
        self.help_text.insert("1.0", "\n".join(notes))

    def _choose_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("All supported", "*.json *.csv"), ("JSON", "*.json"), ("CSV", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                self.raw = f.read()
        except OSError as exc:
            messagebox.showerror("Error", f"Could not read file:\n{exc}")
            return

        detected = self.importer._detect_format(self.raw)
        if detected and not self.format_var.get():
            self.format_var.set(detected)

        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", f"Loaded file: {path}\nSize: {len(self.raw)} bytes\nDetected: {detected or 'unknown'}\n")
        self._update_help()

    def _build_options(self, dry_run: bool) -> ImportOptions:
        return ImportOptions(
            mode=self.mode_var.get(),
            dry_run=dry_run,
            duplicate_strategy=self.dup_var.get()
        )

    def _dry_run(self):
        if not self.raw:
            messagebox.showerror("Error", "Choose a file first")
            return

        try:
            result = self.importer.import_data(
                self.raw,
                import_format=self.format_var.get() or None,
                password=self.password_entry.get().strip() or None,
                options=self._build_options(dry_run=True)
            )
        except Exception as exc:
            messagebox.showerror("Dry run failed", str(exc))
            return

        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(result, indent=2, ensure_ascii=False))

    def _import(self):
        if not self.raw:
            messagebox.showerror("Error", "Choose a file first")
            return

        confirm = simpledialog.askstring(
            "Confirm",
            "Enter master password to confirm import:",
            show="*",
            parent=self
        )
        if not confirm:
            return

        if not verify_master_password(self.auth, self.db, confirm):
            messagebox.showerror("Error", "Master password verification failed")
            return

        try:
            result = self.importer.import_data(
                self.raw,
                import_format=self.format_var.get() or None,
                password=self.password_entry.get().strip() or None,
                options=self._build_options(dry_run=False)
            )
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))
            return

        summary = result.get("summary", {})
        created = result.get("created_ids", [])

        self.db.insert_import_export_history(
            operation_type="import",
            data_format=summary.get("format", self.format_var.get() or "auto"),
            encryption_used="password" if self.password_entry.get().strip() else "none",
            entry_count=len(created),
            file_size=len(self.raw),
            checksum=hashlib.sha256(self.raw).hexdigest(),
            verification_status="ok",
            created_at="imported"
        )

        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(result, indent=2, ensure_ascii=False))
        messagebox.showinfo("Import", f"Imported entries: {len(created)}")
        self.destroy()


class ContactsDialog(tk.Toplevel):
    def __init__(self, master, db, key_exchange_service):
        super().__init__(master)
        self.title("Contacts")
        self.geometry("950x520")
        self.db = db
        self.key_exchange_service = key_exchange_service
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Add Contact", command=self._add_contact).pack(side="left")
        ttk.Button(top, text="Generate RSA Keypair", command=lambda: self._generate_keypair("rsa")).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Generate EC Keypair", command=lambda: self._generate_keypair("ec")).pack(side="left", padx=(8, 0))

        self.tree = ttk.Treeview(self, columns=("name", "identifier", "fingerprint", "last_used"), show="headings")
        for col, title, width in [("name", "Name", 180), ("identifier", "Identifier", 220),
                                  ("fingerprint", "Fingerprint", 360), ("last_used", "Last Used", 140)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.list_contacts():
            self.tree.insert("", "end", values=(
                row.get("contact_name", ""), row.get("contact_identifier", ""),
                row.get("fingerprint", ""), row.get("last_used_at") or ""
            ))

    def _add_contact(self):
        name = simpledialog.askstring("Contact", "Contact name:", parent=self)
        if not name:
            return
        identifier = simpledialog.askstring("Contact", "Identifier / email:", parent=self)
        if not identifier:
            return

        editor = tk.Toplevel(self)
        editor.title("Paste Public Key")
        editor.geometry("700x400")

        txt = tk.Text(editor, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        def save():
            public_key = txt.get("1.0", "end").strip()
            if not public_key:
                messagebox.showerror("Error", "Public key required")
                return
            try:
                fingerprint = self.key_exchange_service.validate_public_key(public_key.encode("utf-8"))
            except Exception as e:
                messagebox.showerror("Error", f"Invalid public key:\n{e}")
                return
            self.db.add_contact(name, identifier, public_key, fingerprint)
            editor.destroy()
            self.refresh()

        ttk.Button(editor, text="Save", command=save).pack(pady=(0, 10))

    def _generate_keypair(self, mode: str):
        pair = (self.key_exchange_service.generate_rsa_keypair() if mode == "rsa"
                else self.key_exchange_service.generate_ec_keypair())

        win = tk.Toplevel(self)
        win.title("Generated Keypair")
        win.geometry("900x620")

        ttk.Label(win, text=f"Algorithm: {pair.algorithm}").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Label(win, text=f"Fingerprint: {pair.fingerprint}").pack(anchor="w", padx=10, pady=(4, 10))

        txt = tk.Text(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", "PRIVATE KEY:\n\n" + pair.private_pem.decode("utf-8") +
                   "\n\nPUBLIC KEY:\n\n" + pair.public_pem.decode("utf-8"))
        txt.configure(state="disabled")


class ShareDialog(tk.Toplevel):
    def __init__(self, master, db, entry_manager, sharing_service, key_exchange_service, qr_service, entry_id: str):
        super().__init__(master)
        self.title("Share Entry")
        self.geometry("980x720")
        self.db = db
        self.entry_manager = entry_manager
        self.sharing_service = sharing_service
        self.key_exchange_service = key_exchange_service
        self.qr_service = qr_service
        self.entry_id = str(entry_id)
        self._last_share_package = None
        self._build()

    def _build(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        left = ttk.Frame(root)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.recipient_var = tk.StringVar()
        self.method_var = tk.StringVar(value="password")
        self.days_var = tk.StringVar(value="7")
        self.read_only_var = tk.BooleanVar(value=True)
        self.include_notes_var = tk.BooleanVar(value=True)

        ttk.Label(left, text="Recipient").pack(anchor="w")
        ttk.Entry(left, textvariable=self.recipient_var).pack(fill="x")

        ttk.Label(left, text="Method").pack(anchor="w", pady=(8, 0))
        ttk.Combobox(left, textvariable=self.method_var, values=["password", "public_key"], state="readonly").pack(fill="x")

        ttk.Label(left, text="Share password").pack(anchor="w", pady=(8, 0))
        self.password_entry = ttk.Entry(left, show="*")
        self.password_entry.pack(fill="x")

        ttk.Label(left, text="Recipient public key (PEM)").pack(anchor="w", pady=(8, 0))
        self.public_key_text = tk.Text(left, height=10, wrap="word")
        self.public_key_text.pack(fill="x")

        ttk.Label(left, text="Expiration (days)").pack(anchor="w", pady=(8, 0))
        ttk.Combobox(left, textvariable=self.days_var, values=[str(i) for i in range(1, 31)], state="readonly").pack(fill="x")

        ttk.Checkbutton(left, text="Read only", variable=self.read_only_var).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(left, text="Include notes", variable=self.include_notes_var).pack(anchor="w")

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Create Share", command=self._share).pack(side="left")
        ttk.Button(btns, text="Show QR", command=self._show_qr).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")

        ttk.Label(right, text="Generated Package", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.preview = tk.Text(right, wrap="word")
        self.preview.pack(fill="both", expand=True)

    def _share(self):
        recipient = self.recipient_var.get().strip()
        if not recipient:
            messagebox.showerror("Error", "Recipient is required")
            return

        method = self.method_var.get()
        password = self.password_entry.get().strip() or None
        public_key_raw = self.public_key_text.get("1.0", "end").strip()

        options = ShareOptions(
            recipient=recipient,
            permissions={
                "read_only": self.read_only_var.get(),
                "include_notes": self.include_notes_var.get()
            },
            expires_in_days=int(self.days_var.get()),
            method=method,
            password=password,
            public_key_pem=public_key_raw.encode("utf-8") if public_key_raw else None
        )

        try:
            result = self.sharing_service.share_entry(self.entry_id, options)
        except Exception as exc:
            messagebox.showerror("Share failed", str(exc))
            return

        self._last_share_package = result["package"]
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(result, indent=2))

    def _show_qr(self):
        if not self._last_share_package:
            messagebox.showerror("Error", "Create share package first")
            return

        payload = json.dumps(self._last_share_package)
        QRViewerDialog(self, payload, title="Share Package QR")
