import unittest
from src.core.crypto.abstract import EncryptionService
from src.core.crypto.placeholder import AES256Placeholder


class TestCrypto(unittest.TestCase):
  def setUp(self):
    self.crypto = AES256Placeholder()
    self.key = b'0123456789abcdef0123456789abcdef'

  def test_encrypt_decrypt(self):
    data = b'secret data'
    encrypted = self.crypto.encrypt(data, self.key)
    decrypted = self.crypto.decrypt(encrypted, self.key)
    self.assertEqual(data, decrypted)

  def test_different_keys(self):
    data = b'test'
    key1 = b'key1' * 8
    key2 = b'key2' * 8
    e1 = self.crypto.encrypt(data, key1)
    e2 = self.crypto.encrypt(data, key2)
    self.assertNotEqual(e1, e2)


if __name__ == '__main__':
  unittest.main()
