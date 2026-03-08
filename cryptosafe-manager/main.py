# main.py
# !/usr/bin/env python3
"""
CryptoSafe Manager - Main entry point
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import Config
from src.database.db import Database
from src.gui.main_window import MainWindow


def main():
  """Main entry point"""
  # Load configuration
  config = Config(env=os.getenv("CRYPTOSAFE_ENV", "development"))

  # Ensure database directory exists
  db_dir = os.path.dirname(config.database_path)
  if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

  # Initialize database
  db = Database(config.database_path)

  # Start GUI
  app = MainWindow(config, db)
  app.run()


if __name__ == "__main__":
  main()
