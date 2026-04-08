# src/core/vault/encryption_service.py (already good, but let me ensure it's complete)
import os
import json
from typing import Dict, Any, Tuple
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    """Per-entry AES-256-GCM encryption service"""

    NONCE_LENGTH = 12
    TAG_LENGTH = 16

    def __init__(self, encryption_key: bytes):
        """
        Initialize encryption service with AES-256 key

        Args:
            encryption_key: 32-byte AES-256 key
        """
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes for AES-256")
        self.key = encryption_key
        self._aesgcm = AESGCM(self.key)

    def encrypt_entry(self, data: Dict[str, Any]) -> bytes:
        """
        Encrypt entry data with AES-256-GCM

        Args:
            data: Dictionary containing entry fields

        Returns:
            BLOB: nonce (12B) || ciphertext || tag (16B)
        """
        # Add metadata to payload
        payload = {
            **data,
            'version': 2  # Version for future compatibility
        }

        # Convert to JSON and encode
        plaintext = json.dumps(payload, default=str).encode('utf-8')

        # Generate unique nonce
        nonce = os.urandom(self.NONCE_LENGTH)

        # Encrypt (returns ciphertext with tag appended)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)

        # Combine nonce + ciphertext (which includes tag)
        return nonce + ciphertext

    def decrypt_entry(self, encrypted_blob: bytes) -> Dict[str, Any]:
        """
        Decrypt entry data and verify authentication tag

        Args:
            encrypted_blob: BLOB (nonce (12B) || ciphertext || tag (16B))

        Returns:
            Decrypted entry dictionary

        Raises:
            ValueError: If authentication fails (tampering detected)
        """
        if len(encrypted_blob) < self.NONCE_LENGTH:
            raise ValueError("Invalid encrypted blob")

        # Extract nonce
        nonce = encrypted_blob[:self.NONCE_LENGTH]
        ciphertext = encrypted_blob[self.NONCE_LENGTH:]

        # Decrypt (automatically verifies tag)
        try:
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError(f"Decryption failed - possible tampering: {e}")

        # Parse JSON
        return json.loads(plaintext.decode('utf-8'))

    @staticmethod
    def create_empty_entry_template() -> Dict[str, Any]:
        """Create template for new entry"""
        return {
            "title": "",
            "username": "",
            "password": "",
            "url": "",
            "notes": "",
            "category": "",
            "version": 2
        }
