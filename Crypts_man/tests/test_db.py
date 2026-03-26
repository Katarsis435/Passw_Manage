# tests/test_database/test_db.py
import unittest
import os
import tempfile
import shutil
from src.database.db import Database


class TestDatabase(unittest.TestCase):
  """Tests for database operations"""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.test_db_path = os.path.join(self.test_dir, "test.db")
    self.db = Database(self.test_db_path)

  def tearDown(self):
    self.db.close()
    shutil.rmtree(self.test_dir, ignore_errors=True)

  def test_database_initialization(self):
    """Test database initializes correctly"""
    stats = self.db.get_stats()
    self.assertEqual(stats['entries_count'], 0)
    self.assertEqual(stats['audit_logs_count'], 0)

  def test_add_and_get_entry(self):
    """Test adding and retrieving entries"""
    entry_id = self.db.add_entry(
      title="Test Entry",
      username="testuser",
      password=b"encrypted_pass",
      url="https://test.com",
      notes="Test notes",
      tags="test,example"
    )

    self.assertIsNotNone(entry_id)

    entry = self.db.get_entry_by_id(entry_id)
    self.assertEqual(entry['title'], "Test Entry")
    self.assertEqual(entry['username'], "testuser")
    self.assertEqual(entry['url'], "https://test.com")

  def test_get_entries_pagination(self):
    """Test pagination for entries"""
    for i in range(25):
      self.db.add_entry(title=f"Entry {i}")

    # First page
    entries = self.db.get_entries(limit=10, offset=0)
    self.assertEqual(len(entries), 10)

    # Second page
    entries = self.db.get_entries(limit=10, offset=10)
    self.assertEqual(len(entries), 10)

    # All entries
    entries = self.db.get_entries(limit=100)
    self.assertEqual(len(entries), 25)

  def test_update_entry(self):
    """Test updating entries"""
    entry_id = self.db.add_entry(title="Original Title")

    self.db.update_entry(entry_id, title="Updated Title")

    entry = self.db.get_entry_by_id(entry_id)
    self.assertEqual(entry['title'], "Updated Title")

  def test_delete_entry(self):
    """Test deleting entries"""
    entry_id = self.db.add_entry(title="To Delete")

    result = self.db.delete_entry(entry_id)
    self.assertTrue(result)

    entry = self.db.get_entry_by_id(entry_id)
    self.assertIsNone(entry)

  def test_audit_log(self):
    """Test audit log operations"""
    entry_id = self.db.add_entry(title="Audit Test")

    log_id = self.db.add_audit_log(
      action="create",
      entry_id=entry_id,
      details="Created entry"
    )

    self.assertIsNotNone(log_id)

    logs = self.db.get_audit_logs()
    self.assertGreaterEqual(len(logs), 1)

  def test_settings(self):
    """Test settings storage"""
    self.db.set_setting("test_key", {"value": "test"})

    value = self.db.get_setting("test_key")
    self.assertEqual(value, {"value": "test"})


if __name__ == '__main__':
  unittest.main()
