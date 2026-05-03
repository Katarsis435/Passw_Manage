"""Secure memory management for sensitive clipboard data"""

import ctypes
import sys
from typing import Optional


class SecureMemory:
  """Secure memory with automatic zeroing and page-locking"""

  def __init__(self):
    self._locked_pages = []

  def create_secure_buffer(self, size: int) -> bytearray:
    """Create a buffer that can be locked and zeroed"""
    # Allocate non-pageable memory if possible
    try:
      if sys.platform == 'win32':
        kernel32 = ctypes.windll.kernel32
        ptr = kernel32.VirtualAlloc(
          None, size, 0x2000,  # MEM_COMMIT
          0x04  # PAGE_READWRITE
        )
        if ptr:
          buffer = (ctypes.c_char * size).from_address(ptr)
          return bytearray(buffer)
    except Exception:
      pass

    return bytearray(size)

  def lock_memory(self, buffer: bytearray) -> bool:
    """Lock memory to prevent swapping to disk"""
    if not buffer:
      return False

    try:
      if sys.platform == 'win32':
        kernel32 = ctypes.windll.kernel32
        return kernel32.VirtualLock(
          ctypes.cast(id(buffer), ctypes.c_void_p),
          len(buffer)
        ) != 0
      elif sys.platform.startswith('linux'):
        libc = ctypes.CDLL("libc.so.6")
        return libc.mlock(
          ctypes.cast(id(buffer), ctypes.c_void_p),
          len(buffer)
        ) == 0
      elif sys.platform == 'darwin':
        libc = ctypes.CDLL("libc.dylib")
        return libc.mlock(
          ctypes.cast(id(buffer), ctypes.c_void_p),
          len(buffer)
        ) == 0
      return False
    except Exception:
      return False

  def secure_zero(self, buffer: bytearray) -> None:
    """Securely zero memory"""
    if buffer:
      try:
        ctypes.memset(id(buffer), 0, len(buffer))
      except Exception:
        for i in range(len(buffer)):
          buffer[i] = 0

  def xor_obfuscate(self, data: bytes, key: bytes) -> bytes:
    """Simple XOR obfuscation for in-memory data"""
    if not data:
      return b''
    key_len = len(key)
    return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

  def xor_deobfuscate(self, obfuscated: bytes, key: bytes) -> bytes:
    """Deobfuscate XORed data"""
    return self.xor_obfuscate(obfuscated, key)
