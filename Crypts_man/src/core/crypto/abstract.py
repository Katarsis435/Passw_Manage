# src/core/crypto/abstract.py
from abc import ABC, abstractmethod


class EncryptionService(ABC):
    """Abstract base class for encryption services"""

    @abstractmethod
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        """Encrypt data with given key"""
        pass

    @abstractmethod
    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt ciphertext with given key"""
        pass
