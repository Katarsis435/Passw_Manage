import ctypes
import platform
from typing import Optional, Any


class SecureMemory:
  def __init__(self):
    self.system = platform.system()
    self._setup_platform_functions()

  def _setup_platform_functions(self):
    if self.system == 'Windows':
      self.kernel32 = ctypes.windll.kernel32
      self._VirtualLock = self.kernel32.VirtualLock
      self._RtlSecureZeroMemory = self.kernel32.RtlSecureZeroMemory
    else:
      self.libc = ctypes.CDLL(None)
      self._mlock = self.libc.mlock
      self._memset = self.libc.memset

  def allocate_secure(self, size: int) -> Any:
    buffer = (ctypes.c_char * size)()
    if self.system == 'Windows':
      self._VirtualLock(buffer, size)
    else:
      self._mlock(buffer, size)
    return buffer

  def secure_zero(self, buffer: Any, size: int) -> None:
    if self.system == 'Windows':
      self._RtlSecureZeroMemory(buffer, size)
    else:
      self._memset(buffer, 0, size)
    ctypes.memset(buffer, 0, size)  # Prevent optimization

  def free_secure(self, buffer: Any, size: int) -> None:
    self.secure_zero(buffer, size)
    del buffer
