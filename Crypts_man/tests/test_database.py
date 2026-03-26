# tests/test_database.py
import unittest
import os
import tempfile
import shutil
from src.database.db import Database


class TestDatabase(unittest.TestCase):
  """Tests for database operations"""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.db_path = os.path.join(self.test_dir, "test.db")
    self.db = Database(self.db_path)

  def tearDown(self):
    self.db.close()
    shutil.rmtree(self.test_dir, ignore_errors=True)

  def test_add_entry(self):
    """Test adding vault entry"""
    entry_id = self.db.add_entry(
      title="Test Entry",
      username="testuser",
      password=b"encrypted_pass"
    )
    self.assertIsNotNone(entry_id)

  def test_get_entries(self):
    """Test retrieving entries"""
    self.db.add_entry(title="Entry 1")
    self.db.add_entry(title="Entry 2")

    entries = self.db.get_entries()
    self.assertEqual(len(entries), 2)

  def test_update_entry(self):
    """Test updating entry"""
    entry_id = self.db.add_entry(title="Original")
    self.db.update_entry(entry_id, title="Updated")

    entry = self.db.get_entry_by_id(entry_id)
    self.assertEqual(entry['title'], "Updated")

  def test_delete_entry(self):
    """Test deleting entry"""
    entry_id = self.db.add_entry(title="To Delete")
    result = self.db.delete_entry(entry_id)

    self.assertTrue(result)
    self.assertIsNone(self.db.get_entry_by_id(entry_id))

  def test_audit_log(self):
    """Test audit log"""
    entry_id = self.db.add_entry(title="Audit Test")

    log_id = self.db.add_audit_log(
      action="test_action",
      entry_id=entry_id,
      details="Test details"
    )
    self.assertIsNotNone(log_id)

    logs = self.db.get_audit_logs()
    self.assertGreaterEqual(len(logs), 1)

  def test_settings(self):
    """Test settings"""
    self.db.set_setting("test_key", {"value": "test"})
    value = self.db.get_setting("test_key")
    self.assertEqual(value, {"value": "test"})


if __name__ == '__main__':
  unittest.main()
