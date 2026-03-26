# debug_main.py
# !/usr/bin/env python3
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

print("=" * 50)
print("Debug mode - Simplified CryptoSafe")
print("=" * 50)

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
  from Crypts_man.src.core import Config
  from Crypts_man.src.database.db import Database

  print("✓ Imports successful")
except Exception as e:
  print(f"✗ Import error: {e}")
  traceback.print_exc()
  input("Press Enter to exit...")
  sys.exit(1)


class DebugWindow:
  def __init__(self):
    print("Creating main window...")
    self.root = tk.Tk()
    self.root.title("CryptoSafe Debug")
    self.root.geometry("800x600")

    # Create simple UI
    main_frame = ttk.Frame(self.root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Title
    title = ttk.Label(main_frame, text="CryptoSafe Manager - Debug Mode",
                      font=('Arial', 16, 'bold'))
    title.pack(pady=10)

    # Info frame
    info_frame = ttk.LabelFrame(main_frame, text="System Info", padding="10")
    info_frame.pack(fill=tk.X, pady=10)

    # Python version
    ttk.Label(info_frame, text=f"Python: {sys.version}").pack(anchor=tk.W)
    ttk.Label(info_frame, text=f"Path: {os.getcwd()}").pack(anchor=tk.W)

    # Test config
    try:
      config = Config()
      ttk.Label(info_frame, text=f"Config: ✓ Loaded").pack(anchor=tk.W)
      ttk.Label(info_frame, text=f"DB Path: {config.database_path}").pack(anchor=tk.W)
    except Exception as e:
      ttk.Label(info_frame, text=f"Config Error: {e}", foreground="red").pack(anchor=tk.W)

    # Test database
    try:
      config = Config()
      db = Database(config.database_path)
      ttk.Label(info_frame, text=f"Database: ✓ Initialized").pack(anchor=tk.W)
    except Exception as e:
      ttk.Label(info_frame, text=f"DB Error: {e}", foreground="red").pack(anchor=tk.W)

    # Buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=20)

    ttk.Button(button_frame, text="Test Message",
               command=lambda: messagebox.showinfo("Test", "Message box works!")).pack(side=tk.LEFT, padx=5)

    ttk.Button(button_frame, text="Show Error",
               command=lambda: messagebox.showerror("Error", "Test error message")).pack(side=tk.LEFT, padx=5)

    ttk.Button(button_frame, text="Exit",
               command=self.root.quit).pack(side=tk.LEFT, padx=5)

    print("Window created, starting mainloop...")

  def run(self):
    self.root.mainloop()
    print("Mainloop ended")


def main():
  try:
    app = DebugWindow()
    app.run()
  except Exception as e:
    print(f"Error in main: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")


if __name__ == "__main__":
  main()
