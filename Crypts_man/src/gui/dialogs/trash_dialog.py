"""Trash dialog for restoring deleted entries"""
import tkinter as tk
from tkinter import ttk, messagebox


class TrashDialog:
    """Dialog showing soft-deleted entries"""

    def __init__(self, parent, entry_manager):
        self.parent = parent
        self.entry_manager = entry_manager
        self.deleted_entries = []
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Корзина — Удалённые записи")
        self.dialog.geometry("1200x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self._create_widgets()
        self._load_deleted_entries()
        self._center_dialog()


    def _center_dialog(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (450 // 2)
        self.dialog.geometry(f"+{x}+{y}")


    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # Заголовок
        ttk.Label(main_frame, text="🗑️Корзина", font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(main_frame, text="Здесь хранятся мягко удалённые записи. Их можно восстановить.",
                  font=('Arial', 9), foreground="gray").pack(anchor=tk.W, pady=(0, 10))
        # Таблица
        columns = ('id', 'title', 'deleted_at')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=12)
        self.tree.heading('id', text='ID')
        self.tree.heading('title', text='Название')
        self.tree.heading('deleted_at', text='Дата удаления')
        self.tree.column('id', width=200)
        self.tree.column('title', width=250)
        self.tree.column('deleted_at', width=150)
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Восстановить выбранную", command=self._restore_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить корзину", command=self._clear_trash).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)


    def _load_deleted_entries(self):
        """Load deleted entries from database"""
        # Сначала убедимся, что таблица имеет правильную структуру
        with self.entry_manager.db.cursor() as c:
            # Проверяем наличие UNIQUE ограничения
            c.execute("PRAGMA index_list(deleted_entries)")
            indexes = c.fetchall()
            has_unique = False
            for idx in indexes:
                if 'idx_deleted_original_id' in str(idx):
                    has_unique = True
            if not has_unique:
                #Создаём уникальный индекс (без удаления данных)
                try:
                    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_deleted_original_id ON deleted_entries(original_id)")
                    print("✓ Создан уникальный индекс")
                except Exception as e:
                    print(f"⚠ Индекс не создан (есть дубли): {e}")
                    # Удаляем дубли и создаём индекс
                    c.execute("""
                              DELETE FROM deleted_entries
                              WHERE rowid NOT IN (
                                  SELECT MIN(rowid)
                                  FROM deleted_entries
                                  GROUP BY original_id
                              )
                          """)
                    print(f"✓ Удалено дублей: {c.rowcount}")
                    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_deleted_original_id ON deleted_entries(original_id)")
                    print("✓ Создан уникальный индекс после очистки")
        # Загружаем записи
        with self.entry_manager.db.cursor() as c:
            c.execute("""
                  SELECT original_id, title, deleted_at
                  FROM deleted_entries
                  ORDER BY deleted_at DESC
              """)
            rows = c.fetchall()
        # Очищаем UI
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.deleted_entries = []
        for row in rows:
            entry = {
                'original_id': row[0],
                'title': row[1],
                'deleted_at': row[2]
            }
            self.deleted_entries.append(entry)
            self.tree.insert('', 'end', values=(
                entry['original_id'],
                entry['title'],
                entry['deleted_at'][:19] if entry['deleted_at'] else ''
            ))
        if not self.deleted_entries:
            self.tree.insert('', 'end', values=('', 'Корзина пуста', ''))
            self.tree.item(self.tree.get_children()[0], tags=('empty',))
            self.tree.tag_configure('empty', foreground='gray')
        else:
            #Настраиваем ширину колонок
            self.tree.column('id', width=350)


    def _restore_selected(self):
        """Restore selected entry"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Восстановление", "Выберите запись для восстановления")
            return
        item = selection[0]
        # Получаем ID строки (IID) — это порядковый номер
        children = self.tree.get_children()
        if not children:
            return
        # Находим индекс выбранной строки
        index = -1
        for i, child in enumerate(children):
            if child == item:
                index = i
                break
        if index == -1 or index >= len(self.deleted_entries):
            messagebox.showerror("Ошибка", "Не удалось найти запись")
            return
        # Берём original_id по индексу
        original_id = self.deleted_entries[index]['original_id']
        title = self.deleted_entries[index]['title']
        # Подтверждение
        if not messagebox.askyesno("Подтверждение", f"Восстановить запись «{title}»?"):
            return
        # Восстанавливаем
        new_id = self.entry_manager.restore_entry(original_id)
        if new_id:
            messagebox.showinfo("Успех", "Запись восстановлена!")
            self._load_deleted_entries()  # Обновить список
            if hasattr(self.parent, '_load_vault_data'):
                self.parent._load_vault_data()  # Обновить главную таблицу
        else:
            messagebox.showerror("Ошибка", "Не удалось восстановить запись")


    def _clear_trash(self):
        """Permanently delete all entries in trash"""
        if not self.deleted_entries:
            messagebox.showinfo("Корзина", "Корзина уже пуста")
            return
        if not messagebox.askyesno("Очистка корзины",
                                   f"Вы уверены? Будет безвозвратно удалено {len(self.deleted_entries)} записей.\n"
                                   "Это действие нельзя отменить!"):
            return
        with self.entry_manager.db.cursor() as c:
            c.execute("DELETE FROM deleted_entries")
        self.deleted_entries = []
        self._load_deleted_entries()
        messagebox.showinfo("Успех", "Корзина очищена")
