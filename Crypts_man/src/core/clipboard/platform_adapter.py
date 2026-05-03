"""Platform-specific clipboard implementations"""

import sys
import platform
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable


class PlatformAdapter(ABC):
  """Abstract base class for clipboard adapters"""

  @abstractmethod
  def copy_to_clipboard(self, data: str) -> bool:
    pass

  @abstractmethod
  def clear_clipboard(self) -> bool:
    pass

  @abstractmethod
  def get_clipboard_content(self) -> Optional[str]:
    pass

  def start_monitoring(self, callback: Callable) -> bool:
    """Start monitoring clipboard changes (optional)"""
    return False

  def stop_monitoring(self) -> None:
    pass


class WindowsClipboardAdapter(PlatformAdapter):
  """Windows implementation using win32clipboard"""

  def __init__(self):
    self._callback = None
    self._monitoring = False
    self._last_content = ""

  def copy_to_clipboard(self, data: str) -> bool:
    try:
      import win32clipboard
      import win32con

      win32clipboard.OpenClipboard()
      win32clipboard.EmptyClipboard()
      win32clipboard.SetClipboardText(data, win32con.CF_UNICODETEXT)
      win32clipboard.CloseClipboard()
      self._last_content = data
      return True
    except Exception:
      return False

  def clear_clipboard(self) -> bool:
    try:
      import win32clipboard
      win32clipboard.OpenClipboard()
      win32clipboard.EmptyClipboard()
      win32clipboard.CloseClipboard()
      self._last_content = ""
      return True
    except Exception:
      return False

  def get_clipboard_content(self) -> Optional[str]:
    try:
      import win32clipboard
      win32clipboard.OpenClipboard()
      result = None
      if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
        result = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
      win32clipboard.CloseClipboard()
      return result
    except Exception:
      return None


class macOSClipboardAdapter(PlatformAdapter):
  """macOS implementation using pyobjc"""

  def copy_to_clipboard(self, data: str) -> bool:
    try:
      from Foundation import NSPasteboard
      pb = NSPasteboard.generalPasteboard()
      pb.clearContents()
      pb.setString_forType_(data, "public.utf8-plain-text")
      return True
    except Exception:
      return False

  def clear_clipboard(self) -> bool:
    try:
      from Foundation import NSPasteboard
      pb = NSPasteboard.generalPasteboard()
      pb.clearContents()
      return True
    except Exception:
      return False

  def get_clipboard_content(self) -> Optional[str]:
    try:
      from Foundation import NSPasteboard
      pb = NSPasteboard.generalPasteboard()
      return pb.stringForType_("public.utf8-plain-text")
    except Exception:
      return None


class LinuxClipboardAdapter(PlatformAdapter):
  """Linux implementation using pyperclip"""

  def __init__(self):
    try:
      import pyperclip
      self._pyperclip = pyperclip
    except ImportError:
      self._pyperclip = None

  def copy_to_clipboard(self, data: str) -> bool:
    if self._pyperclip:
      try:
        self._pyperclip.copy(data)
        return True
      except Exception:
        return False
    return False

  def clear_clipboard(self) -> bool:
    return self.copy_to_clipboard("")

  def get_clipboard_content(self) -> Optional[str]:
    if self._pyperclip:
      try:
        return self._pyperclip.paste()
      except Exception:
        return None
    return None


class FallbackClipboardAdapter(PlatformAdapter):
  """Fallback using tkinter clipboard"""

  def __init__(self, root=None):
    self._root = root

  def copy_to_clipboard(self, data: str) -> bool:
    try:
      if self._root:
        self._root.clipboard_clear()
        self._root.clipboard_append(data)
        return True
    except Exception:
      pass
    return False

  def clear_clipboard(self) -> bool:
    return self.copy_to_clipboard("")

  def get_clipboard_content(self) -> Optional[str]:
    try:
      if self._root:
        return self._root.clipboard_get()
    except Exception:
      pass
    return None


def create_platform_adapter(root=None):
  """Factory to create appropriate platform adapter"""
  system = platform.system()

  if system == 'Windows':
    try:
      return WindowsClipboardAdapter()
    except ImportError:
      pass
  elif system == 'Darwin':
    try:
      return macOSClipboardAdapter()
    except ImportError:
      pass
  elif system == 'Linux':
    try:
      return LinuxClipboardAdapter()
    except ImportError:
      pass

  return FallbackClipboardAdapter(root)
