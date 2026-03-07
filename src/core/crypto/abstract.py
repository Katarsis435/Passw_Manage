# src/core/crypto/abstract.py
from abc import ABC, abstractmethod


class EncryptionService(ABC):
  """Abstract base class for encryption services"""

  @abstractmethod
  def encrypt(self, data: bytes, key: bytes) -> bytes:
    """Encrypt data using provided key"""
    pass

  @abstractmethod
  def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt ciphertext using provided key"""
    pass
