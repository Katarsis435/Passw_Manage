import unittest
import json
from Crypts_man.src.core.vault.encryption_service import EncryptionService


class TestEncryptionService(unittest.TestCase):
    def setUp(self):
        self.key = b'0123456789abcdef0123456789abcdef'  # 32 bytes
        self.service = EncryptionService(self.key)

    def test_encrypt_decrypt_roundtrip(self):  # TEST-1
        data = {'title': 'Test', 'password': 'secret'}
        encrypted = self.service.encrypt_entry(data)

        # Verify it's not plaintext
        self.assertNotIn(b'secret', encrypted)

        # Decrypt and verify
        decrypted = self.service.decrypt_entry(encrypted)
        self.assertEqual(decrypted['password'], 'secret')

    def test_tampering_detection(self):  # ENC-5
        data = {'title': 'Test', 'password': 'secret'}
        encrypted = self.service.encrypt_entry(data)

        # Tamper with ciphertext
        tampered = bytearray(encrypted)
        tampered[20] ^= 0xFF  #Flip a bit

        with self.assertRaises(ValueError):
            self.service.decrypt_entry(bytes(tampered))
