#!/usr/bin/env python3
"""CryptoSafe Manager - Main Entry Point"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import Config
from src.database.db import Database
from src.gui.main_window import MainWindow


def main():
    try:
        print("Starting CryptoSafe Manager...")
        config = Config()
        db = Database(config.database_path)
        app = MainWindow(config, db)
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
