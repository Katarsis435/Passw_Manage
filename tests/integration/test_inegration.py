# tests/integration/test_integration.py
import unittest
import tempfile
import os
import tkinter as tk
from tkinter import messagebox
from unittest.mock import patch, MagicMock

from src.core.config import Config
from src.core.state_manager import StateManager
from src.core.events import EventBus, Event, EventType
from src.database.db import DatabaseManager
from src.database.models import VaultEntry
from src.gui.main_window import MainWindow


class TestIntegration(unittest.TestCase):
  """Integration tests for CryptoSafe Manager"""

  @classmethod
  def setUpClass(cls):
    """Set up test environment"""
    # Create temporary directory for test files
    cls.temp_dir = tempfile.mkdtemp()
    cls.db_path = os.path.join(cls.temp_dir, "test_integration.db")

    # Create test config
    cls.config = Config()
    cls.config.set("database_path", cls.db_path)
    cls.config.set("dev_mode", True)
    cls.config.set("clipboard_timeout", 5)
    cls.config.set("auto_lock_minutes", 1)

  @classmethod
  def tearDownClass(cls):
    """Clean up test environment"""
    if os.path.exists(cls.db_path):
      os.remove(cls.db_path)
    os.rmdir(cls.temp_dir)

  def setUp(self):
    """Set up each test"""
    # Create fresh database for each test
    if os.path.exists(self.db_path):
      os.remove(self.db_path)

    # Mock tkinter to avoid actual GUI during tests
    self.root_patcher = patch('tkinter.Tk')
    self.mock_tk = self.root_patcher.start()

    # Create application instance
    self.app = MainWindow(self.config)

    # Mock messagebox to avoid popups
    self.messagebox_patcher = patch('tkinter.messagebox')
    self.mock_messagebox = self.messagebox_patcher.start()

  def tearDown(self):
    """Clean up after each test"""
    self.root_patcher.stop()
    self.messagebox_patcher.stop()

    # Clean up database connections
    if hasattr(self.app, 'db'):
      self.app.db.close_all_connections()

  def test_application_initialization(self):
    """Test application initializes correctly"""
    self.assertIsNotNone(self.app.config)
    self.assertIsNotNone(self.app.state_manager)
    self.assertIsNotNone(self.app.event_bus)
    self.assertIsNotNone(self.app.db)
    self.assertIsNotNone(self.app.table)
    self.assertIsNotNone(self.app.statusbar)

    # Check initial state
    self.assertTrue(self.app.state_manager.is_locked)

  def test_database_creation(self):
    """Test database is created on first run"""
    # Database should be created during initialization
    self.assertTrue(os.path.exists(self.db_path))

    # Verify tables exist
    with self.app.db.transaction() as conn:
      cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
      )
      tables = [row['name'] for row in cursor.fetchall()]

      expected_tables = ['vault_entries', 'audit_log', 'settings', 'key_store']
      for table in expected_tables:
        self.assertIn(table, tables)

  def test_event_bus_integration(self):
    """Test event bus integration with database"""
    events_received = []

    def test_handler(event):
      events_received.append(event)

    # Subscribe to events
    self.app.event_bus.subscribe(EventType.ENTRY_ADDED, test_handler)

    # Add entry (should trigger event)
    entry = VaultEntry(
      title="Event Test",
      username="test_user",
      encrypted_password=b"test_pass"
    )
    entry_id = self.app.db.add_entry(entry)

    # Verify event was received
    self.assertEqual(len(events_received), 1)
    self.assertEqual(events_received[0].type, EventType.ENTRY_ADDED)
    self.assertEqual(events_received[0].data['entry_id'], entry_id)

  def test_state_manager_integration(self):
    """Test state manager integration with events"""
    login_events = []

    def login_handler(event):
      login_events.append(event)

    self.app.event_bus.subscribe(EventType.USER_LOGGED_IN, login_handler)

    # Unlock
    self.app.state_manager.unlock("test_user")

    # Verify state and events
    self.assertFalse(self.app.state_manager.is_locked)
    self.assertEqual(self.app.state_manager.current_user, "test_user")
    self.assertEqual(len(login_events), 1)

    # Test clipboard
    self.app.state_manager.set_clipboard("test_password")
    self.assertEqual(self.app.state_manager.get_clipboard(), "test_password")

    # Test auto-lock (fast-forward time)
    self.app.state_manager._auto_lock_minutes = 0  # Immediate lock
    self.app.state_manager._auto_lock()
    self.assertTrue(self.app.state_manager.is_locked)
    self.assertIsNone(self.app.state_manager.get_clipboard())

  def test_configuration_persistence(self):
    """Test configuration is persisted correctly"""
    # Change config
    self.app.config.set("clipboard_timeout", 60)
    self.app.config.set("theme", "dark")

    # Create new instance (should load saved config)
    new_app = MainWindow(self.config)

    # Verify config was loaded
    self.assertEqual(new_app.config.get("clipboard_timeout"), 60)
    self.assertEqual(new_app.config.get("theme"), "dark")

    new_app.db.close_all_connections()

  def test_database_backup_stub(self):
    """Test database backup stub"""
    backup_path = os.path.join(self.temp_dir, "backup.db")

    # Add some data first
    entry = VaultEntry(
      title="Backup Test",
      username="backup_user",
      encrypted_password=b"backup_pass"
    )
    self.app.db.add_entry(entry)

    # Create backup
    result = self.app.db.backup_database(backup_path)
    self.assertTrue(result)
    self.assertTrue(os.path.exists(backup_path))

    # Verify backup contains data
    backup_config = Config()
    backup_config.set("database_path", backup_path)
    backup_db = DatabaseManager(backup_config)

    entries = backup_db.get_all_entries()
    self.assertEqual(len(entries), 1)
    self.assertEqual(entries[0].title, "Backup Test")

    backup_db.close_all_connections()

  def test_error_handling(self):
    """Test error handling in various components"""
    # Test encryption with invalid key
    with self.assertRaises(ValueError):
      self.app.crypto.encrypt(b"data", b"")

    # Test database with invalid entry
    invalid_entry = VaultEntry(
      title="",  # Empty title should be allowed but might cause issues
      username="test",
      encrypted_password=b"pass"
    )
    # This should not raise an exception
    try:
      entry_id = self.app.db.add_entry(invalid_entry)
      self.assertIsNotNone(entry_id)
    except Exception as e:
      self.fail(f"add_entry raised {e}")

  def test_concurrent_operations(self):
    """Test database with concurrent operations"""
    import threading

    results = []

    def add_entry_thread(thread_id):
      try:
        entry = VaultEntry(
          title=f"Thread {thread_id}",
          username=f"user{thread_id}",
          encrypted_password=b"pass"
        )
        entry_id = self.app.db.add_entry(entry)
        results.append((thread_id, entry_id, True))
      except Exception as e:
        results.append((thread_id, None, False))

    # Create multiple threads
    threads = []
    for i in range(5):
      t = threading.Thread(target=add_entry_thread, args=(i,))
      threads.append(t)
      t.start()

    # Wait for all threads
    for t in threads:
      t.join()

    # Verify results
    self.assertEqual(len(results), 5)
    self.assertTrue(all(r[2] for r in results))  # All successful

    # Verify all entries were added
    entries = self.app.db.get_all_entries()
    self.assertEqual(len(entries), 5)

  def test_first_run_wizard_stub(self):
    """Test first-run wizard stub functionality"""
    # Simulate first run by creating new config
    new_config = Config()
    new_config.set("database_path", os.path.join(self.temp_dir, "new.db"))

    # Create app with new config
    new_app = MainWindow(new_config)

    # Verify database was created
    self.assertTrue(os.path.exists(new_config.database_path))

    new_app.db.close_all_connections()

  def test_settings_dialog_stub(self):
    """Test settings dialog stub"""
    # This test just verifies the settings dialog doesn't crash
    try:
      # We need to create a real Tk root for this test
      self.root_patcher.stop()

      # Create a real root for the dialog
      root = tk.Tk()
      root.withdraw()  # Hide the window

      # Recreate app with real root
      self.app.root = root
      self.app._show_settings()

      # Clean up
      root.destroy()

    except Exception as e:
      self.fail(f"Settings dialog raised {e}")
    finally:
      # Restart patcher
      self.root_patcher.start()

  def test_audit_log_integration(self):
    """Test audit log integration with events"""
    # Perform various operations
    entry = VaultEntry(
      title="Audit Integration",
      username="audit_user",
      encrypted_password=b"audit_pass"
    )
    entry_id = self.app.db.add_entry(entry)

    # Update entry
    entry.id = entry_id
    entry.title = "Updated Audit"
    self.app.db.update_entry(entry)

    # Get audit logs
    logs = self.app.db.get_audit_logs()

    # Should have at least 2 logs (ADD and UPDATE)
    self.assertGreaterEqual(len(logs), 2)

    # Verify actions
    actions = [log.action for log in logs]
    self.assertIn("ADD", actions)
    self.assertIn("UPDATE", actions)


if __name__ == '__main__':
  unittest.main()
