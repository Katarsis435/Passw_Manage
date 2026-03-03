import tkinter as tk
from tkinter import ttk


class PasswordEntry(ttk.Frame):
  def __init__(self, parent, **kwargs):
    super().__init__(parent)

    self.show_password = tk.BooleanVar(value=False)

    self.entry = ttk.Entry(self, show='*', **kwargs)
    self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    self.btn_show = ttk.Button(
      self,
      text='👁',
      width=3,
      command=self.toggle_show
    )
    self.btn_show.pack(side=tk.RIGHT)

  def toggle_show(self):
    self.show_password.set(not self.show_password.get())
    self.entry.config(show='' if self.show_password.get() else '*')

  def get(self):
    return self.entry.get()

  def set(self, value):
    self.entry.delete(0, tk.END)
    self.entry.insert(0, value)
