# src/core/crypto/placeholder.py
from src.core.crypto.abstract import EncryptionService
import os


class AES256Placeholder(EncryptionService):
  """Placeholder encryption using XOR (to be replaced with real AES-GCM in Sprint 3)"""

  def encrypt(self, data: bytes, key: bytes) -> bytes:
    """Simple XOR encryption (placeholder only!)"""
    # Ensure key is at least as long as data
    extended_key = key * (len(data) // len(key) + 1)
    return bytes(a ^ b for a, b in zip(data, extended_key))

  def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
    """XOR decryption (same as encryption)"""
    extended_key = key * (len(ciphertext) // len(key) + 1)
    return bytes(a ^ b for a, b in zip(ciphertext, extended_key))

  def generate_key(self) -> bytes:
    """Generate a random key"""
    return os.urandom(32)  # 256 bits
