# src/core/key_manager.py
import os
import hashlib
import secrets
from typing import Optional, Tuple
import ctypes


class KeyManager:
  """Key management stub for Sprint 1"""

  def __init__(self):
    self._master_key: Optional[bytes] = None

  def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive encryption key from password using PBKDF2
    Returns (key, salt)
    """
    if salt is None:
      salt = os.urandom(32)

    # Use PBKDF2 for key derivation (will be enhanced in Sprint 3)
    key = hashlib.pbkdf2_hmac(
      'sha256',
      password.encode('utf-8'),
      salt,
      100000,  # Number of iterations
      dklen=32  # 256-bit key
    )

    return key, salt

  def store_key(self, key_id: str, key: bytes) -> None:
    """
    Store key securely (placeholder - will be implemented in Sprint 2)
    """
    self._master_key = key

  def load_key(self, key_id: str) -> Optional[bytes]:
    """
    Load key (placeholder - will be implemented in Sprint 2)
    """
    return self._master_key

  def secure_zero_key(self, key: bytearray) -> None:
    """Securely zero out a key from memory"""
    ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(key)), 0, len(key))
