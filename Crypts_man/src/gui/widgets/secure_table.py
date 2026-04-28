# src/gui/widgets/secure_table.py (updated with all Sprint 3 features)
import tkinter as tk
from tkinter import ttk, Menu
import re


class SecureTable(ttk.Frame):
    """Table widget for displaying vault entries with enhanced features"""

    def __init__(self, parent, columns=None, **kwargs):
        super().__init__(parent)

        self.parent = parent

        if columns is None:
            self.columns = [
                ("id", "ID", 0, False),  # hidden
                ("title", "Title", 200, True),
                ("username", "Username", 150, True),
                ("url", "URL", 200, True),
                ("updated_at", "Last Modified", 150, True),
                ("category", "Category", 100, True)
            ]
        else:
            self.columns = columns

        self.selected_item = None
        self.show_passwords = False
        self.data = []
        self.column_order = [col[0] for col in self.columns if col[3]]

        # Create treeview with scrollbars
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # Create treeview with visible columns only
        visible_columns = [col[0] for col in self.columns if col[3]]
        self.tree = ttk.Treeview(
            container,
            columns=visible_columns,
            show="headings",
            selectmode="extended",
            **kwargs
        )

        # Configure columns
        for col_id, col_name, width, visible in self.columns:
            if visible:
                self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_by_column(c))
                self.tree.column(col_id, width=width, minwidth=50)

        # Add scrollbars
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Button-3>', self._show_context_menu)
        self.tree.bind('<Control-a>', self._select_all)
        self.tree.bind('<Control-c>', self._copy_selected)
        self.tree.bind('<Delete>', self._delete_selected)

        # Context menu
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy Username", command=self._copy_username)
        self.context_menu.add_command(label="Copy Password", command=self._copy_password)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit", command=self._edit_entry)
        self.context_menu.add_command(label="Delete", command=self._delete_entry)

        # Enable column reordering
        self._setup_drag_drop()

    def _sort_by_column(self, col):
        """Sort tree by column"""
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        items.sort(key=lambda x: x[0].lower())

        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)

    def _setup_drag_drop(self):
        """Setup column reordering via drag and drop"""
        def start_move(event):
            self.drag_column = self.tree.identify_column(event.x)

        def drag(event):
            if hasattr(self, 'drag_column'):
                col = self.tree.identify_column(event.x)
                if col and col != self.drag_column:
                    col_index = int(col.replace('#', '')) - 1
                    drag_index = int(self.drag_column.replace('#', '')) - 1

                    if 0 <= col_index < len(self.column_order) and 0 <= drag_index < len(self.column_order):
                        # Swap column order
                        self.column_order[col_index], self.column_order[drag_index] = \
                            self.column_order[drag_index], self.column_order[col_index]

                        # Reconfigure tree columns
                        for i, col_id in enumerate(self.column_order):
                            self.tree.heading(col_id, text=self._get_column_name(col_id))
                            self.tree.column(col_id, width=self._get_column_width(col_id))

                        self.drag_column = col
                        self.refresh()

        self.tree.bind('<Button-1>', start_move)
        self.tree.bind('<B1-Motion>', drag)

    def _get_column_name(self, col_id):
        """Get column display name"""
        for cid, name, width, visible in self.columns:
            if cid == col_id:
                return name
        return col_id

    def _get_column_width(self, col_id):
        """Get column width"""
        for cid, name, width, visible in self.columns:
            if cid == col_id:
                return width
        return 100

    def _on_select(self, event):
        """Handle item selection"""
        selection = self.tree.selection()
        if selection:
            self.selected_item = selection[0]
        else:
            self.selected_item = None

        # Trigger callback if set
        if hasattr(self.parent, 'on_table_select'):
            self.parent.on_table_select(self.get_selected_rows())

    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _select_all(self, event):
        """Select all items (Ctrl+A)"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        return "break"

    def _copy_selected(self, event):
        """Copy selected item details (Ctrl+C)"""
        selected = self.get_selected_rows()
        if selected:
            import tkinter as tk
            text = "\n".join([f"{k}: {v}" for k, v in selected[0].items() if v])
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)

    def _delete_selected(self, event):
        """Delete selected items (Delete key)"""
        self._delete_entry()

    def _copy_username(self):
        """Copy username to clipboard"""
        selected = self.get_selected_rows()
        if selected and selected[0].get('username'):
            self.parent.clipboard_clear()
            self.parent.clipboard_append(selected[0]['username'])

    def _copy_password(self):
        """Copy password to clipboard (will be implemented in Sprint 4)"""
        # Placeholder for Sprint 4 clipboard integration
        if hasattr(self.parent, 'copy_password_callback'):
            self.parent.copy_password_callback()

    def _edit_entry(self):
        """Edit entry (trigger from context menu)"""
        if hasattr(self.parent, 'edit_entry_callback'):
            self.parent.edit_entry_callback()

    def _delete_entry(self):
        """Delete entry (trigger from context menu)"""
        if hasattr(self.parent, 'delete_entry_callback'):
            self.parent.delete_entry_callback()

    def set_data(self, data, show_passwords=False):
        """Populate table with data"""
        self.data = data
        self.show_passwords = show_passwords

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add new data
        for row in data:
            values = []
            for col_id in self.column_order:
                value = row.get(col_id, '')

                if col_id == 'username' and not show_passwords and value:
                    # Mask username after 4 characters
                    if len(value) > 4:
                        value = value[:4] + '••••'
                elif col_id == 'password' and not show_passwords and value:
                    value = '••••••••'
                elif col_id == 'url' and value:
                    # Extract domain from URL
                    domain = self._extract_domain(value)
                    if domain:
                        value = domain

                values.append(value)

            self.tree.insert("", tk.END, values=values, iid=str(row.get('id', 0)))

    def _extract_domain(self, url):
        """Extract domain from URL"""
        if not url:
            return ""

        # Remove protocol
        domain = re.sub(r'^https?://', '', url)
        # Remove path
        domain = domain.split('/')[0]
        # Remove www
        domain = re.sub(r'^www\.', '', domain)

        return domain

    def toggle_password_visibility(self):
        """Toggle password column visibility"""
        self.show_passwords = not self.show_passwords
        self.set_data(self.data, self.show_passwords)

    def get_selected(self):
        """Get selected item ID"""
        return self.selected_item

    def get_selected_rows(self):
        """Get all selected rows data"""
        selected = []
        for item in self.tree.selection():
            values = self.tree.item(item)['values']
            row = {}
            for i, col_id in enumerate(self.column_order):
                if i < len(values):
                    row[col_id] = values[i]
            # Also store the actual item ID
            row['_id'] = item
            selected.append(row)
        return selected

    def get_selected_row(self):
        """Get first selected row data"""
        selection = self.tree.selection()
        if not selection:
            return None
        item = selection[0]
        values = self.tree.item(item)['values']
        if not values:
            return None
        row = {}
        for i, col_id in enumerate(self.column_order):
            if i < len(values):
                row[col_id] = values[i]
        row['id'] = item  # ID из iid
        return row

    def clear_selection(self):
        """Clear current selection"""
        self.tree.selection_remove(self.tree.selection())
        self.selected_item = None

    def refresh(self):
        """Refresh table display"""
        self.set_data(self.data, self.show_passwords)

    def resize_column(self, col_id, width):
        """Resize a column"""
        self.tree.column(col_id, width=width)

    def get_decrypted_entry(self, entry_id, entry_manager):
        """Get decrypted entry on demand (SEC-1 compliance)"""
        if hasattr(self, '_decrypted_cache'):
            return self._decrypted_cache.get(entry_id)
        return None

    def clear_decrypted_cache(self):
        """Clear cached decrypted entries"""
        if hasattr(self, '_decrypted_cache'):
            self._decrypted_cache.clear()
