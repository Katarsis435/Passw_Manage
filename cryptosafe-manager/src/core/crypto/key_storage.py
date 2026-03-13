# SPR_2
import time
import ctypes
import platform
from threading import Timer


class SecureMemory:
  @staticmethod
  def lock_memory(pointer, size):
    system = platform.system()
    try:
      if system == 'Windows':
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.VirtualLock(pointer, size)
      else:  # Linux/Mac
        libc = ctypes.CDLL('libc.so.6' if system == 'Linux' else 'libc.dylib')
        libc.mlock(pointer, size)
    except:
      pass  # Fallback silently

  @staticmethod
  def zero_memory(pointer, size):
    ctypes.memset(pointer, 0, size)


class KeyCache:
  def __init__(self, timeout=3600):  # 1 hour default
    self._key = None
    self._key_ref = None  # For memory locking
    self._key_size = 32  # AES-256 key size
    self.timeout = timeout
    self.last_activity = 0
    self.timer = None

  def store_key(self, key):
    self.clear()
    # Allocate memory
    self._key = bytearray(key)
    self._key_ref = (ctypes.c_byte * self._key_size).from_buffer(self._key)
    # Lock memory
    SecureMemory.lock_memory(ctypes.addressof(self._key_ref), self._key_size)
    # Update activity
    self.update_activity()

  def get_key(self):
    if self._key and not self.is_expired():
      self.update_activity()
      return bytes(self._key)
    return None

  def update_activity(self):
    self.last_activity = time.time()
    # Reset timer
    if self.timer:
      self.timer.cancel()
    self.timer = Timer(self.timeout, self.clear)
    self.timer.daemon = True
    self.timer.start()

  def is_expired(self):
    if not self._key:
      return True
    return (time.time() - self.last_activity) > self.timeout

  def clear(self):
    if self._key and self._key_ref:
      SecureMemory.zero_memory(ctypes.addressof(self._key_ref), self._key_size)
    self._key = None
    self._key_ref = None
    if self.timer:
      self.timer.cancel()
      self.timer = None


class KeychainStorage:
  def __init__(self, use_keychain=True):
    self.use_keychain = use_keychain
    self.keyring = None
    if use_keychain:
      try:
        import keyring
        self.keyring = keyring
      except ImportError:
        self.use_keychain = False

  def save_key(self, service, username, key):
    if self.use_keychain:
      try:
        self.keyring.set_password(service, username, key.hex())
        return True
      except:
        return False
    return False

  def load_key(self, service, username):
    if self.use_keychain:
      try:
        key_hex = self.keyring.get_password(service, username)
        if key_hex:
          return bytes.fromhex(key_hex)
      except:
        pass
    return None

  def delete_key(self, service, username):
    if self.use_keychain:
      try:
        self.keyring.delete_password(service, username)
      except:
        pass
