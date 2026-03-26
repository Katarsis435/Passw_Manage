#!/usr/bin/env python3
# main.py
import sys
import os
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point for CryptoSafe Manager"""
    try:
        from src.core.config import Config
        from src.database.db import Database
        from src.gui.main_window import MainWindow

        print("Initializing CryptoSafe Manager...")

        # Load configuration
        config = Config()

        # Initialize database (will be created if needed)
        db = Database(config.database_path)

        # Create and run main window
        app = MainWindow(config, db)
        app.run()

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
