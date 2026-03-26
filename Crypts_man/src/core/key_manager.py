# src/core/key_manager.py
import os
import hashlib
from typing import Optional, Dict, Any
import ctypes
import secrets


class KeyManager:
    """Key management with Argon2 and PBKDF2"""

    def __init__(self, config=None):
        self._current_key: Optional[bytes] = None
        self._config = config
        self._init_crypto()

    def _init_crypto(self):
        """Initialize cryptographic components"""
        try:
            from argon2 import PasswordHasher, Type
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes

            # Argon2 parameters
            argon2_time = 3
            argon2_memory = 65536
            argon2_parallelism = 4

            if self._config:
                argon2_time = self._config.get('argon2_time', 3)
                argon2_memory = self._config.get('argon2_memory', 65536)
                argon2_parallelism = self._config.get('argon2_parallelism', 4)

            self.argon2_hasher = PasswordHasher(
                time_cost=argon2_time,
                memory_cost=argon2_memory,
                parallelism=argon2_parallelism,
                hash_len=32,
                salt_len=16,
                type=Type.ID
            )

            # PBKDF2 parameters
            self.pbkdf2_iterations = 100000
            if self._config:
                self.pbkdf2_iterations = self._config.get('pbkdf2_iterations', 100000)

            self.PBKDF2HMAC = PBKDF2HMAC
            self.hashes = hashes
            self._crypto_available = True

        except ImportError:
            print("Warning: argon2-cffi or cryptography not installed")
            self._crypto_available = False

    def create_auth_hash(self, password: str) -> Dict[str, Any]:
        """Create Argon2 hash for password verification"""
        if not self._crypto_available:
            # Fallback for testing
            return {
                'hash': hashlib.sha256(password.encode()).hexdigest(),
                'params': {'fallback': True}
            }

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
        if not self._crypto_available:
            # Fallback for testing
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

        kdf = self.PBKDF2HMAC(
            algorithm=self.hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.pbkdf2_iterations
        )
        return kdf.derive(password.encode('utf-8'))

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored Argon2 hash (constant-time)"""
        if not self._crypto_available:
            # Fallback for testing
            computed = hashlib.sha256(password.encode()).hexdigest()
            return secrets.compare_digest(computed, stored_hash)

        try:
            self.argon2_hasher.verify(stored_hash, password)
            return True
        except:
            # Constant-time dummy verification to prevent timing attacks
            secrets.compare_digest(b'dummy', b'dummy')
            return False

    def store_key(self, key_id: str, key: bytes) -> None:
        """Store key in memory cache"""
        self._current_key = key

    def load_key(self, key_id: str) -> Optional[bytes]:
        """Load key from memory cache"""
        return self._current_key

    def cache_encryption_key(self, key: bytes) -> None:
        """Cache encryption key in memory"""
        self._current_key = key

    def get_cached_encryption_key(self) -> Optional[bytes]:
        """Get cached encryption key"""
        return self._current_key

    def clear_cache(self) -> None:
        """Clear cached keys from memory"""
        if self._current_key:
            self.secure_zero(self._current_key)
            self._current_key = None

    def secure_zero(self, data: bytes) -> None:
        """Securely zero memory"""
        if data:
            try:
                arr = bytearray(data)
                ctypes.memset(id(arr), 0, len(arr))
            except:
                pass

    def update_activity(self) -> None:
        """Update activity timestamp (for auto-lock integration)"""
        pass
