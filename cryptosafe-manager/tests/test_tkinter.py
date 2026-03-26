# test_tkinter.py
import tkinter as tk
from tkinter import ttk, messagebox


def test_gui():
  """Простой тест GUI"""
  root = tk.Tk()
  root.title("Test Window")
  root.geometry("300x200")

  label = ttk.Label(root, text="If you see this window, tkinter works!")
  label.pack(pady=20)

  def show_message():
    messagebox.showinfo("Test", "Button works!")

  button = ttk.Button(root, text="Click me", command=show_message)
  button.pack(pady=10)

  root.mainloop()


if __name__ == "__main__":
  print("Starting test GUI...")
  test_gui()
