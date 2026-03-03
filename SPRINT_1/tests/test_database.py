import unittest
import tempfile
from pathlib import Path
from src.database.db import Database
from src.database.models import VaultEntry


class TestDatabase(unittest.TestCase):
  def setUp(self):
    self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    self.db = Database(Path(self.temp_db.name))

  def tearDown(self):
    Path(self.temp_db.name).unlink()

  def test_add_entry(self):
    entry = VaultEntry(
      title='Test',
      username='user',
      encrypted_password=b'secret'
    )
    entry_id = self.db.add_entry(entry)
    self.assertIsNotNone(entry_id)

  def test_get_entries(self):
    # Добавляем тестовую запись
    entry = VaultEntry(title='Test', username='user')
    self.db.add_entry(entry)

    # Получаем записи
    entries = self.db.get_entries()
    self.assertEqual(len(entries), 1)
    self.assertEqual(entries[0]['title'], 'Test')

  def test_settings(self):
    self.db.set_setting('test_key', 'test_value')
    value = self.db.get_setting('test_key')
    self.assertEqual(value, 'test_value')


if __name__ == '__main__':
  unittest.main()
