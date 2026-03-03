import tkinter as tk
from tkinter import ttk


class SecureTable(ttk.Treeview):
  def __init__(self, parent, **kwargs):
    columns = ('id', 'title', 'username', 'url', 'updated')
    super().__init__(parent, columns=columns, show='headings', **kwargs)

    self.heading('id', text='ID')
    self.heading('title', text='Название')
    self.heading('username', text='Логин')
    self.heading('url', text='URL')
    self.heading('updated', text='Обновлено')

    self.column('id', width=50)
    self.column('title', width=200)
    self.column('username', width=150)
    self.column('url', width=200)
    self.column('updated', width=150)

    # Добавляем скроллбар
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.yview)
    self.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

  def set_data(self, entries):
    # Очищаем
    for item in self.get_children():
      self.delete(item)

    # Добавляем данные
    for entry in entries:
      self.insert('', tk.END, values=(
        entry.get('id', ''),
        entry.get('title', ''),
        entry.get('username', ''),
        entry.get('url', ''),
        entry.get('updated_at', '')[:10]  # Только дата
      ))
