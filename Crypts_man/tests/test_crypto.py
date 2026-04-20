# tests/test_crypto.py
import unittest
import os
from Crypts_man.src.core.crypto.placeholder import AES256Placeholder
from Crypts_man.src.core.key_manager import KeyManager


class TestCrypto(unittest.TestCase):
  """Tests for cryptographic operations"""

  def setUp(self):
    self.crypto = AES256Placeholder()
    self.key_manager = KeyManager()

  def test_encrypt_decrypt(self):
    """Test encryption and decryption"""
    key = os.urandom(32)
    data = b"Secret password 123!"

    encrypted = self.crypto.encrypt(data, key)
    decrypted = self.crypto.decrypt(encrypted, key)

    self.assertNotEqual(data, encrypted)
    self.assertEqual(data, decrypted)

  def test_key_derivation(self):
    """Test key derivation"""
    password = "test_password"
    salt = os.urandom(16)

    # Используем правильный метод
    key = self.key_manager.derive_encryption_key(password, salt)

    self.assertEqual(len(key), 32)
    self.assertIsInstance(key, bytes)

    # Проверяем что одинаковые пароли дают одинаковый ключ
    key2 = self.key_manager.derive_encryption_key(password, salt)
    self.assertEqual(key, key2)

    # Разные соли дают разные ключи
    salt2 = os.urandom(16)
    key3 = self.key_manager.derive_encryption_key(password, salt2)
    self.assertNotEqual(key, key3)


if __name__ == '__main__':
  unittest.main()
