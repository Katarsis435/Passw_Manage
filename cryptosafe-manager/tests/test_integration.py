# tests/test_integration.py
import unittest
import tempfile
import os
from src.core.config import Config
from src.database.db import Database
from src.core.state_manager import StateManager
from src.core.events import events, EventType


class TestIntegration(unittest.TestCase):
  """Integration tests"""

  def setUp(self):
    # Create temp config and db
    self.temp_dir = tempfile.mkdtemp()
    self.db_path = os.path.join(self.temp_dir, "test.db")

    # Override config
    self.config = Config()
    self.config.set("database_path", self.db_path)

    # Create database
    self.db = Database(self.db_path)

    # Reset events
    global events
    from src.core.events import EventSystem
    events = EventSystem()

  def tearDown(self):
    import shutil
    shutil.rmtree(self.temp_dir)

  def test_database_creation(self):
    """Test database is created"""
    self.assertTrue(os.path.exists(self.db_path))

  def test_config_loading(self):
    """Test config loading"""
    self.assertEqual(self.config.get("database_path"), self.db_path)
    self.assertEqual(self.config.get("clipboard_timeout"), 30)

  def test_first_run_flow(self):
    """Test first run flow (simulated)"""
    # This would normally be tested through GUI,
    # but we test the underlying functionality
    from src.core.key_manager import KeyManager

    km = KeyManager()
    password = "test_master_password"
    salt = os.urandom(16)
    key = km.derive_key(password, salt)

    self.assertIsNotNone(key)
    self.assertEqual(len(key), 32)  # 256 bits

    # Store key (stub)
    km.store_key("master", key)

    # Add test entry
    from src.core.crypto.placeholder import AES256Placeholder
    crypto = AES256Placeholder()

    encrypted = crypto.encrypt(b"test_password", key)
    entry_id = self.db.add_entry(
      title="Test Entry",
      username="test",
      password=encrypted
    )

    self.assertGreater(entry_id, 0)

    # Verify can decrypt
    entries = self.db.get_entries()
    self.assertEqual(len(entries), 1)

    decrypted = crypto.decrypt(entries[0]['encrypted_password'], key)
    self.assertEqual(decrypted, b"test_password")

  def test_event_integration(self):
    """Test event system integration"""
    event_received = []

    def test_handler(data):
      event_received.append(data)

    events.subscribe(EventType.ENTRY_ADDED, test_handler)

    # Simulate adding entry
    test_data = {"id": 1, "title": "Test", "action": "added"}
    events.publish(EventType.ENTRY_ADDED, test_data)

    self.assertEqual(len(event_received), 1)
    self.assertEqual(event_received[0], test_data)


if __name__ == '__main__':
  unittest.main()
