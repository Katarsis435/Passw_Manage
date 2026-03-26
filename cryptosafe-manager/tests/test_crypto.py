# tests/test_crypto.py
import unittest
import os
from src.core.crypto.placeholder import AES256Placeholder
from src.core.key_manager import KeyManager


class TestCrypto(unittest.TestCase):
  """Test cryptographic functionality"""

  def setUp(self):
    self.crypto = AES256Placeholder()
    self.key_manager = KeyManager()

  def test_encrypt_decrypt(self):
    """Test encryption and decryption"""
    key = b"0" * 32
    data = b"Secret password 123"

    encrypted = self.crypto.encrypt(data, key)
    decrypted = self.crypto.decrypt(encrypted, key)

    self.assertEqual(data, decrypted)

  def test_key_derivation(self):
    """Test key derivation"""
    password = "test_password"
    salt = os.urandom(16)

    key1 = self.key_manager.derive_key(password, salt)
    key2 = self.key_manager.derive_key(password, salt)

    self.assertEqual(key1, key2)

    # Different salt should produce different key
    salt2 = os.urandom(16)
    key3 = self.key_manager.derive_key(password, salt2)
    self.assertNotEqual(key1, key3)


if __name__ == '__main__':
  unittest.main()
