import tkinter as tk
from tkinter import ttk


class AuditLogViewer(ttk.Frame):
  """Заглушка для спринта 5"""

  def __init__(self, parent, **kwargs):
    super().__init__(parent, **kwargs)

    label = ttk.Label(self, text='Журнал аудита (заглушка)')
    label.pack(pady=10)

    self.text = tk.Text(self, height=10, width=60)
    self.text.pack(fill=tk.BOTH, expand=True)

    self.add_log('Приложение запущено')

  def add_log(self, message):
    import time
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    self.text.insert(tk.END, f'[{timestamp}] {message}\n')
    self.text.see(tk.END)
