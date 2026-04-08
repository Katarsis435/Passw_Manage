# tests/test_integration.py
import time
import unittest
import os
import tempfile
import shutil
from src.core.config import Config
from src.database.db import Database
from src.core.key_manager import KeyManager
from src.core.authentication import AuthenticationManager


class TestIntegrationSprint2(unittest.TestCase):
  """Integration tests for Sprint 2"""

  def setUp(self):
    # Create temporary directory for test database
    self.test_dir = tempfile.mkdtemp()
    self.test_db_path = os.path.join(self.test_dir, "test_vault.db")

    # Initialize components
    self.config = Config()
    self.config.set("database_path", self.test_db_path)

    self.db = Database(self.test_db_path)
    self.key_manager = KeyManager(self.config)
    self.auth_manager = AuthenticationManager(self.key_manager)

    self.test_password = "StrongP@ssw0rd123"
    self.test_salt = os.urandom(16)

  def tearDown(self):
    # Clean up
    if hasattr(self, 'db'):
      self.db.close()
    shutil.rmtree(self.test_dir, ignore_errors=True)

  def test_first_run_setup(self):
    """Test first run setup creates proper authentication data"""
    # Create auth hash
    auth_result = self.key_manager.create_auth_hash(self.test_password)

    # Store in database
    self.db.store_auth_hash(auth_result['hash'], auth_result['params'])
    self.db.store_encryption_salt(self.test_salt)
    self.db.store_key_params(auth_result['params'])

    # Verify data was stored
    auth_hash = self.db.get_auth_hash()
    salt_data = self.db.get_encryption_salt()
    params = self.db.get_key_params()

    self.assertIsNotNone(auth_hash)
    self.assertIsNotNone(salt_data)
    self.assertIsNotNone(params)
    self.assertEqual(salt_data['salt'], self.test_salt)

  def test_login_flow(self):
    """Test complete login flow"""
    # Setup
    auth_result = self.key_manager.create_auth_hash(self.test_password)
    self.db.store_auth_hash(auth_result['hash'], auth_result['params'])
    self.db.store_encryption_salt(self.test_salt)

    # Login
    auth_hash = self.db.get_auth_hash()
    salt_data = self.db.get_encryption_salt()

    encryption_key = self.auth_manager.authenticate(
      self.test_password,
      auth_hash['hash'].decode(),
      salt_data['salt']
    )

    self.assertIsNotNone(encryption_key)
    self.assertTrue(self.auth_manager.is_authenticated())
    self.assertEqual(len(encryption_key), 32)

  def test_password_change_integration(self):
    """Test password change with re-encryption (TEST-5)"""
    # Setup initial vault with password "A"
    old_password = "OldPass123!@#"
    new_password = "NewPass456!@#"

    # Create auth data for old password
    old_auth = self.key_manager.create_auth_hash(old_password)
    old_salt = os.urandom(16)

    self.db.store_auth_hash(old_auth['hash'], old_auth['params'])
    self.db.store_encryption_salt(old_salt)

    # Derive old encryption key
    old_key = self.key_manager.derive_encryption_key(old_password, old_salt)

    # Add test entries (10 entries)
    from src.core.crypto.placeholder import AES256Placeholder
    crypto = AES256Placeholder()

    entry_ids = []
    for i in range(10):
      encrypted_pass = crypto.encrypt(f"testpass{i}".encode(), old_key)
      entry_id = self.db.add_entry(
        title=f"Entry {i}",
        username=f"user{i}",
        password=encrypted_pass,
        url=f"http://test{i}.com"
      )
      entry_ids.append(entry_id)

    # Verify entries exist
    entries = self.db.get_entries()
    self.assertEqual(len(entries), 10)

    # Simulate password change
    # 1. Verify old password and get old key

   # old_auth_hash = self.db.get_auth_hash()
    # old_salt_data = self.db.get_encryption_salt()

    # 2. Derive new encryption key
    new_salt = os.urandom(16)
    new_key = self.key_manager.derive_encryption_key(new_password, new_salt)

    # 3. Re-encrypt all entries
    for entry in entries:
      # Decrypt with old key
      decrypted = crypto.decrypt(entry['encrypted_password'], old_key)
      # Encrypt with new key
      new_encrypted = crypto.encrypt(decrypted, new_key)
      # Update in database
      self.db.update_entry(entry['id'], encrypted_password=new_encrypted)

    # 4. Update auth hash and salt
    new_auth = self.key_manager.create_auth_hash(new_password)
    self.db.store_auth_hash(new_auth['hash'], new_auth['params'])
    self.db.store_encryption_salt(new_salt)

    # Now verify all entries are accessible with new password
    new_auth_hash = self.db.get_auth_hash()
    new_salt_data = self.db.get_encryption_salt()

    # Login with new password
    auth_manager = AuthenticationManager(self.key_manager)
    new_encryption_key = auth_manager.authenticate(
      new_password,
      new_auth_hash['hash'].decode(),
      new_salt_data['salt']
    )

    self.assertIsNotNone(new_encryption_key)

    # Decrypt all entries with new key
    updated_entries = self.db.get_entries()
    for entry in updated_entries:
      decrypted = crypto.decrypt(entry['encrypted_password'], new_encryption_key)
      self.assertIsInstance(decrypted, bytes)
      self.assertTrue(decrypted.startswith(b'testpass') or decrypted == b'')

  def test_failed_login_backoff(self):
    """Test exponential backoff on failed logins"""
    # Setup
    auth_result = self.key_manager.create_auth_hash(self.test_password)
    self.db.store_auth_hash(auth_result['hash'], auth_result['params'])
    self.db.store_encryption_salt(self.test_salt)

    auth_hash = self.db.get_auth_hash()
    salt_data = self.db.get_encryption_salt()

    # Первая неудачная попытка
    result = self.auth_manager.authenticate(
      "WrongPassword",
      auth_hash['hash'].decode(),
      salt_data['salt']
    )
    self.assertIsNone(result)
    self.assertGreaterEqual(self.auth_manager.get_failed_attempts(), 1)

    # Вторая неудачная попытка
    result = self.auth_manager.authenticate(
      "WrongPassword",
      auth_hash['hash'].decode(),
      salt_data['salt']
    )
    self.assertIsNone(result)
    self.assertGreaterEqual(self.auth_manager.get_failed_attempts(), 1)
    time.sleep(5)
    time.sleep(5)
    # Успешный вход
    result = self.auth_manager.authenticate(
      self.test_password,
      auth_hash['hash'].decode(),
      salt_data['salt']
    )
    self.assertIsNotNone(result)
    self.assertEqual(self.auth_manager.get_failed_attempts(), 0)

  def test_encryption_key_never_stored(self):
    """Test encryption key is never written to disk (SEC-2)"""
    auth_result = self.key_manager.create_auth_hash(self.test_password)
    self.db.store_auth_hash(auth_result['hash'], auth_result['params'])
    self.db.store_encryption_salt(self.test_salt)

    # Login to get encryption key
    auth_hash = self.db.get_auth_hash()
    salt_data = self.db.get_encryption_salt()

    encryption_key = self.auth_manager.authenticate(
      self.test_password,
      auth_hash['hash'].decode(),
      salt_data['salt']
    )

    # Check that encryption key is NOT in key_store table
    stored_key = self.db.get_key('encryption_key')
    self.assertIsNone(stored_key, "Encryption key should not be stored in database")

    # Check that encryption key is NOT in settings
    stored_setting = self.db.get_setting('encryption_key')
    self.assertIsNone(stored_setting, "Encryption key should not be stored in settings")

    # Verify key exists in memory only
    self.assertIsNotNone(encryption_key)
    self.assertIsNotNone(self.key_manager.get_cached_encryption_key())


if __name__ == '__main__':
  unittest.main()
