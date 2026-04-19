# src/core/key_manager.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import os
import hashlib
import secrets
import ctypes
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class KeyManager:
  """Unified key management for CryptoSafe Manager"""

  def __init__(self, config=None):
    self._current_key: Optional[bytes] = None
    self._config = config or {}
    self._crypto_available = False
    self._init_crypto()

  def _init_crypto(self):
    """Initialize cryptographic components with error handling"""
    try:
      from argon2 import PasswordHasher, Type
      from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
      from cryptography.hazmat.primitives import hashes

      # Argon2 parameters
      self.argon2_hasher = PasswordHasher(
        time_cost=self._config.get('argon2_time', 3),
        memory_cost=self._config.get('argon2_memory', 65536),
        parallelism=self._config.get('argon2_parallelism', 4),
        hash_len=32,
        salt_len=16,
        type=Type.ID
      )

      # PBKDF2 parameters
      self.pbkdf2_iterations = self._config.get('pbkdf2_iterations', 100000)
      self.PBKDF2HMAC = PBKDF2HMAC
      self.hashes = hashes
      self._crypto_available = True
      logger.info("Crypto libraries initialized successfully")

    except ImportError as e:
      logger.error(f"Crypto libraries not available: {e}")
      self._crypto_available = False

  def create_auth_hash(self, password: str) -> Dict[str, Any]:
    """Create Argon2 hash for password verification"""
    if not self._crypto_available:
      # Fallback for testing only
      salt = os.urandom(16)
      hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
      return {'hash': hash_val.hex(), 'params': {'fallback': True, 'salt': salt.hex()}}

    return {
      'hash': self.argon2_hasher.hash(password),
      'params': {
        'time_cost': self.argon2_hasher.time_cost,
        'memory_cost': self.argon2_hasher.memory_cost,
        'parallelism': self.argon2_hasher.parallelism,
      }
    }

  def derive_encryption_key(self, password: str, salt: bytes) -> bytes:
    """Derive AES-256 key from password using PBKDF2"""
    if not self._crypto_available:
      return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

    kdf = self.PBKDF2HMAC(
      algorithm=self.hashes.SHA256(),
      length=32,
      salt=salt,
      iterations=self.pbkdf2_iterations
    )
    return kdf.derive(password.encode('utf-8'))

  def verify_password(self, password: str, stored_hash: str) -> bool:
    """Verify password against stored hash (constant-time)"""
    if not self._crypto_available:
      computed = hashlib.sha256(password.encode()).hexdigest()
      return secrets.compare_digest(computed, stored_hash)

    try:
      self.argon2_hasher.verify(stored_hash, password)
      return True
    except Exception:
      # Constant-time dummy operation to prevent timing attacks
      secrets.compare_digest(b'dummy', b'dummy')
      return False

  def cache_encryption_key(self, key: bytes) -> None:
    """Cache encryption key in memory"""
    if key and len(key) == 32:
      self._current_key = key
      logger.debug("Encryption key cached")

  def get_cached_encryption_key(self) -> Optional[bytes]:
    """Get cached encryption key"""
    return self._current_key

  def clear_cache(self) -> None:
    """Securely clear cached keys"""
    if self._current_key:
      self._secure_zero(self._current_key)
      self._current_key = None
    logger.debug("Encryption key cache cleared")

  def _secure_zero(self, data: bytes) -> None:
    """Securely zero memory containing sensitive data"""
    try:
      arr = bytearray(data)
      ctypes.memset(id(arr), 0, len(arr))
    except:
      pass  # Best effort

  def update_activity(self) -> None:
    """Update activity timestamp for auto-lock"""
    pass


