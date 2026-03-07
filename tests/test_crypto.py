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

  def test_encryption_decryption(self):
    """Test basic encryption and decryption"""
    test_data = b"Hello, World!"
    test_key = b"test_key_16bytes"

    # Encrypt
    encrypted = self.crypto.encrypt(test_data, test_key)
    self.assertIsInstance(encrypted, bytes)
    self.assertNotEqual(encrypted, test_data)

    # Decrypt
    decrypted = self.crypto.decrypt(encrypted, test_key)
    self.assertEqual(decrypted, test_data)

  def test_encryption_different_keys(self):
    """Test that different keys produce different ciphertexts"""
    test_data = b"Test data"
    key1 = b"key1"
    key2 = b"key2"

    encrypted1 = self.crypto.encrypt(test_data, key1)
    encrypted2 = self.crypto.encrypt(test_data, key2)

    self.assertNotEqual(encrypted1, encrypted2)

  def test_encryption_empty_data(self):
    """Test encryption of empty data"""
    test_data = b""
    test_key = b"test_key"

    encrypted = self.crypto.encrypt(test_data, test_key)
    decrypted = self.crypto.decrypt(encrypted, test_key)

    self.assertEqual(decrypted, test_data)

  def test_key_derivation(self):
    """Test key derivation"""
    password = "my_secure_password"

    key, salt = self.key_manager.derive_key(password)

    self.assertEqual(len(key), 32)  # 256 bits
    self.assertEqual(len(salt), 32)

    # Derive same key with same salt
    key2, _ = self.key_manager.derive_key(password, salt)
    self.assertEqual(key, key2)

  def test_key_derivation_different_salts(self):
    """Test that different salts produce different keys"""
    password = "my_secure_password"

    key1, _ = self.key_manager.derive_key(password)
    key2, _ = self.key_manager.derive_key(password)

    self.assertNotEqual(key1, key2)


if __name__ == '__main__':
  unittest.main()
