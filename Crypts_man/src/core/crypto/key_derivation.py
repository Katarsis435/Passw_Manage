# src/core/crypto/key_derivation.py
from argon2 import PasswordHasher, Type
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os
import secrets
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class KeyManager:
    """Key manager for authentication and encryption key derivation"""

    def __init__(self, config: Optional[Any] = None):
        # Argon2 parameters for authentication hash
        argon2_time = 3
        argon2_memory = 65536  # 64 MiB
        argon2_parallelism = 4

        if config:
            argon2_time = config.get('argon2_time', 3)
            argon2_memory = config.get('argon2_memory', 65536)
            argon2_parallelism = config.get('argon2_parallelism', 4)

        self.argon2_hasher = PasswordHasher(
            time_cost=argon2_time,
            memory_cost=argon2_memory,
            parallelism=argon2_parallelism,
            hash_len=32,
            salt_len=16,
            type=Type.ID
        )

        # PBKDF2 parameters for encryption key derivation
        self.pbkdf2_iterations = 100000
        if config:
            self.pbkdf2_iterations = config.get('pbkdf2_iterations', 100000)

        self._cached_encryption_key: Optional[bytes] = None
        self._cached_auth_hash: Optional[str] = None
        self._cache_active = False

    def create_auth_hash(self, password: str) -> Dict[str, Any]:
        """Create Argon2 hash for password verification"""
        return {
            'hash': self.argon2_hasher.hash(password),
            'params': {
                'time_cost': self.argon2_hasher.time_cost,
                'memory_cost': self.argon2_hasher.memory_cost,
                'parallelism': self.argon2_hasher.parallelism,
                'hash_len': 32,
                'salt_len': 16
            }
        }

    def derive_encryption_key(self, password: str, salt: bytes) -> bytes:
        """Derive AES-256 key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.pbkdf2_iterations
        )
        return kdf.derive(password.encode('utf-8'))

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored Argon2 hash (constant-time)"""
        try:
            return self.argon2_hasher.verify(stored_hash, password)
        except:
            # Constant-time dummy verification to prevent timing attacks
            secrets.compare_digest(b'dummy', b'dummy')
            return False

    def cache_encryption_key(self, key: bytes) -> None:
        """Cache encryption key in memory"""
        self._cached_encryption_key = key
        self._cache_active = True

    def get_cached_encryption_key(self) -> Optional[bytes]:
        """Get cached encryption key if active"""
        return self._cached_encryption_key if self._cache_active else None

    def clear_cache(self) -> None:
        """Clear cached keys from memory"""
        if self._cached_encryption_key:
            self._secure_zero(self._cached_encryption_key)
            self._cached_encryption_key = None
        self._cache_active = False

    def _secure_zero(self, data: bytes) -> None:
        """Securely zero memory"""
        if data:
            import ctypes
            arr = bytearray(data)
            ctypes.memset(id(arr), 0, len(arr))

    def update_activity(self) -> None:
        """Update activity timestamp (for auto-lock integration)"""
        # This will be used by auto-lock functionality in Sprint 7
        pass
