# src/core/key_manager.py
import os
import hashlib
from typing import Optional
import ctypes


class KeyManager:
  """Key management stub for Sprint 1 (to be enhanced in Sprint 2)"""

  def __init__(self):
    self._current_key: Optional[bytes] = None

  def derive_key(self, password: str, salt: Optional[bytes] = None) -> bytes:
    """Derive a key from password (placeholder using SHA256)"""
    if salt is None:
      salt = os.urandom(16)

    # Simple key derivation (will be replaced with proper KDF in Sprint 3)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return key

  def store_key(self, key_id: str, key: bytes) -> None:
    """Stub for storing key (will be implemented in Sprint 2)"""
    self._current_key = key

  def load_key(self, key_id: str) -> Optional[bytes]:
    """Stub for loading key (will be implemented in Sprint 2)"""
    return self._current_key

  def secure_zero(self, data: bytes) -> None:
    """Securely zero memory"""
    if data:
      # Create a mutable array from bytes
      arr = bytearray(data)
      ctypes.memset(id(arr), 0, len(arr))
