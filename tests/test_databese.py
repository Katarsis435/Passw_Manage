# tests/test_database.py
import unittest
import tempfile
import os
from datetime import datetime
from src.core.config import Config
from src.database.db import DatabaseManager
from src.database.models import VaultEntry, AuditLog


class TestDatabase(unittest.TestCase):
  """Test database functionality"""

  def setUp(self):
    """Set up test database"""
    # Create temporary config
    self.temp_dir = tempfile.mkdtemp()
    self.db_path = os.path.join(self.temp_dir, "test.db")

    self.config = Config()
    self.config.set("database_path", self.db_path)
    self.config.set("dev_mode", True)

    self.db = DatabaseManager(self.config)

  def tearDown(self):
    """Clean up test database"""
    self.db.close_all_connections()
    if os.path.exists(self.db_path):
      os.remove(self.db_path)
    os.rmdir(self.temp_dir)

  def test_database_initialization(self):
    """Test database initialization"""
    # Database should be initialized in setUp
    self.assertTrue(os.path.exists(self.db_path))

  def test_add_entry(self):
    """Test adding a vault entry"""
    entry = VaultEntry(
      title="Test Entry",
      username="testuser",
      encrypted_password=b"encrypted_password",
      url="https://example.com",
      notes="Test notes",
      tags="test,example"
    )

    entry_id = self.db.add_entry(entry)
    self.assertIsNotNone(entry_id)

    # Retrieve and verify
    retrieved = self.db.get_entry(entry_id)
    self.assertIsNotNone(retrieved)
    self.assertEqual(retrieved.title, "Test Entry")
    self.assertEqual(retrieved.username, "testuser")
    self.assertEqual(retrieved.encrypted_password, b"encrypted_password")

  def test_get_all_entries(self):
    """Test retrieving all entries"""
    # Add multiple entries
    entries = []
    for i in range(3):
      entry = VaultEntry(
        title=f"Entry {i}",
        username=f"user{i}",
        encrypted_password=b"pass",
        url=f"https://example{i}.com"
      )
      entry_id = self.db.add_entry(entry)
      entries.append(entry_id)

    # Retrieve all
    all_entries = self.db.get_all_entries()
    self.assertEqual(len(all_entries), 3)

  def test_update_entry(self):
    """Test updating an entry"""
    # Add entry
    entry = VaultEntry(
      title="Original Title",
      username="original_user",
      encrypted_password=b"original_pass"
    )
    entry_id = self.db.add_entry(entry)

    # Update
    entry.id = entry_id
    entry.title = "Updated Title"
    entry.username = "updated_user"

    result = self.db.update_entry(entry)
    self.assertTrue(result)

    # Verify update
    updated = self.db.get_entry(entry_id)
    self.assertEqual(updated.title, "Updated Title")
    self.assertEqual(updated.username, "updated_user")

  def test_delete_entry(self):
    """Test deleting an entry"""
    # Add entry
    entry = VaultEntry(
      title="To Delete",
      username="delete_user",
      encrypted_password=b"delete_pass"
    )
    entry_id = self.db.add_entry(entry)

    # Delete
    result = self.db.delete_entry(entry_id)
    self.assertTrue(result)

    # Verify deletion
    deleted = self.db.get_entry(entry_id)
    self.assertIsNone(deleted)

  def test_audit_log(self):
    """Test audit log functionality"""
    # Add entry (should create audit log)
    entry = VaultEntry(
      title="Audit Test",
      username="audit_user",
      encrypted_password=b"audit_pass"
    )
    entry_id = self.db.add_entry(entry)

    # Get audit logs
    logs = self.db.get_audit_logs()
    self.assertTrue(len(logs) > 0)

    # Find our log
    found = False
    for log in logs:
      if log.entry_id == entry_id and log.action == "ADD":
        found = True
        self.assertIn("Audit Test", log.details)
        break

    self.assertTrue(found)

  def test_settings(self):
    """Test settings functionality"""
    # Set setting
    self.db.set_setting("test_key", "test_value")

    # Get setting
    value = self.db.get_setting("test_key")
    self.assertEqual(value, "test_value")

    # Get non-existent setting
    default = self.db.get_setting("non_existent", "default")
    self.assertEqual(default, "default")

    # Update setting
    self.db.set_setting("test_key", "updated_value")
    value = self.db.get_setting("test_key")
    self.assertEqual(value, "updated_value")

  def test_key_store(self):
    """Test key store functionality"""
    # Store key data
    salt = b"test_salt_16bytes"
    hash_data = b"test_hash_16bytes"
    self.db.store_key_data("master", salt, hash_data, "iterations=100000")

    # Retrieve key data
    data = self.db.get_key_data("master")
    self.assertIsNotNone(data)
    self.assertEqual(data[0], salt)
    self.assertEqual(data[1], hash_data)
    self.assertEqual(data[2], "iterations=100000")

    # Non-existent key type
    data = self.db.get_key_data("non_existent")
    self.assertIsNone(data)


if __name__ == '__main__':
  unittest.main()
