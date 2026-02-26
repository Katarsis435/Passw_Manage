import hashlib
import os
import ctypes


class KeyManager:
  @staticmethod
  def derive_key(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    if salt is None:
      salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return key, salt

  @staticmethod
  def secure_zero(data: bytearray):
    ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(data)), 0, len(data))
