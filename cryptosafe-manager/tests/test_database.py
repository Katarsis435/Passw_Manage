# tests/test_database.py
import unittest
import os
import tempfile
from src.database.db import Database


class TestDatabase(unittest.TestCase):
  """Test database functionality"""

  def setUp(self):
    self.temp_db = tempfile.NamedTemporaryFile(delete=False)
    self.db_path = self.temp_db.name
    self.temp_db.close()

    self.db = Database(self.db_path)

  def tearDown(self):
    os.unlink(self.db_path)

  def test_add_entry(self):
    """Test adding vault entry"""
    entry_id = self.db.add_entry(
      title="Test Entry",
      username="testuser",
      password=b"encrypted_pass",
      url="https://example.com",
      notes="Test notes",
      tags="test,example"
    )

    self.assertIsNotNone(entry_id)
    self.assertGreater(entry_id, 0)

  def test_get_entries(self):
    """Test retrieving entries"""
    # Add test entry
    self.db.add_entry(title="Test Entry 1")
    self.db.add_entry(title="Test Entry 2")

    entries = self.db.get_entries()

    self.assertEqual(len(entries), 2)
    self.assertEqual(entries[0]['title'], "Test Entry 1")

  def test_update_entry(self):
    """Test updating entry"""
    entry_id = self.db.add_entry(title="Original Title")

    updated = self.db.update_entry(entry_id, title="Updated Title")
    self.assertTrue(updated)

    entries = self.db.get_entries()
    self.assertEqual(entries[0]['title'], "Updated Title")

  def test_delete_entry(self):
    """Test deleting entry"""
    entry_id = self.db.add_entry(title="To Delete")

    deleted = self.db.delete_entry(entry_id)
    self.assertTrue(deleted)

    entries = self.db.get_entries()
    self.assertEqual(len(entries), 0)

  def test_audit_log(self):
    """Test audit log"""
    log_id = self.db.add_audit_log(
      action="test_action",
      entry_id=1,
      details="Test details"
    )

    self.assertIsNotNone(log_id)

  def test_settings(self):
    """Test settings"""
    self.db.set_setting("test_key", "test_value")

    value = self.db.get_setting("test_key")
    self.assertEqual(value, "test_value")


if __name__ == '__main__':
  unittest.main()
