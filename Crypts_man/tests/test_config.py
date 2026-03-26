# tests/test_core/test_config.py
import unittest
import os
import tempfile
import json
from src.core.config import Config


class TestConfig(unittest.TestCase):
  """Tests for configuration manager"""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.original_home = os.environ.get('HOME')
    os.environ['HOME'] = self.test_dir

  def tearDown(self):
    if self.original_home:
      os.environ['HOME'] = self.original_home
    import shutil
    shutil.rmtree(self.test_dir, ignore_errors=True)

  def test_default_config(self):
    """Test default configuration values"""
    config = Config()

    self.assertIsNotNone(config.get('database_path'))
    self.assertTrue(config.get('encryption_enabled'))
    self.assertEqual(config.get('clipboard_timeout'), 30)
    self.assertEqual(config.get('auto_lock_minutes'), 5)

  def test_set_and_get(self):
    """Test setting and getting configuration values"""
    config = Config()

    config.set('test_key', 'test_value')
    self.assertEqual(config.get('test_key'), 'test_value')

    config.set('test_key', 'new_value')
    self.assertEqual(config.get('test_key'), 'new_value')

  def test_config_persistence(self):
    """Test configuration persists to file"""
    config = Config()
    config.set('persist_key', 'persist_value')
    config.save()

    # Create new config instance
    new_config = Config()
    self.assertEqual(new_config.get('persist_key'), 'persist_value')

  def test_default_value(self):
    """Test default value for missing keys"""
    config = Config()
    self.assertEqual(config.get('nonexistent', 'default'), 'default')


if __name__ == '__main__':
  unittest.main()
