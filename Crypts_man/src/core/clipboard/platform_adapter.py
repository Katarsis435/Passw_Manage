"""Platform-specific clipboard implementations"""

import sys
import platform
from abc import ABC, abstractmethod
from typing import Optional


class ClipboardAdapter(ABC):
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


class WindowsClipboardAdapter(ClipboardAdapter):
    """Windows implementation using win32clipboard"""

    def __init__(self):
        self._available = False
        try:
            import win32clipboard
            import win32con
            self.win32clipboard = win32clipboard
            self.win32con = win32con
            self._available = True
        except ImportError:
            print("Warning: pywin32 not installed, clipboard will use fallback")

    def copy_to_clipboard(self, data: str) -> bool:
        if not self._available:
            return False
        try:
            self.win32clipboard.OpenClipboard()
            self.win32clipboard.EmptyClipboard()
            self.win32clipboard.SetClipboardText(data, self.win32clipboard.CF_UNICODETEXT)
            self.win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            print(f"Windows copy failed: {e}")
            return False

    def clear_clipboard(self) -> bool:
        if not self._available:
            return False
        try:
            self.win32clipboard.OpenClipboard()
            self.win32clipboard.EmptyClipboard()
            self.win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            print(f"Windows clear failed: {e}")
            return False

    def get_clipboard_content(self) -> Optional[str]:
        if not self._available:
            return None
        try:
            self.win32clipboard.OpenClipboard()
            result = None
            if self.win32clipboard.IsClipboardFormatAvailable(self.win32clipboard.CF_UNICODETEXT):
                result = self.win32clipboard.GetClipboardData(self.win32clipboard.CF_UNICODETEXT)
            self.win32clipboard.CloseClipboard()
            return result
        except Exception:
            return None


class MacOSClipboardAdapter(ClipboardAdapter):
    """macOS implementation using pyobjc"""

    def __init__(self):
        self._available = False
        try:
            from Foundation import NSPasteboard
            self.NSPasteboard = NSPasteboard
            self._available = True
        except ImportError:
            print("Warning: pyobjc not installed, clipboard will use fallback")

    def _get_pasteboard(self):
        if self._available:
            return self.NSPasteboard.generalPasteboard()
        return None

    def copy_to_clipboard(self, data: str) -> bool:
        pb = self._get_pasteboard()
        if pb:
            try:
                pb.clearContents()
                pb.setString_forType_(data, "public.utf8-plain-text")
                return True
            except Exception:
                return False
        return False

    def clear_clipboard(self) -> bool:
        pb = self._get_pasteboard()
        if pb:
            try:
                pb.clearContents()
                return True
            except Exception:
                return False
        return False

    def get_clipboard_content(self) -> Optional[str]:
        pb = self._get_pasteboard()
        if pb:
            try:
                return pb.stringForType_("public.utf8-plain-text")
            except Exception:
                return None
        return None


class LinuxClipboardAdapter(ClipboardAdapter):
    """Linux implementation using pyperclip"""

    def __init__(self):
        self._available = False
        try:
            import pyperclip
            self._pyperclip = pyperclip
            self._available = True
        except ImportError:
            print("Warning: pyperclip not installed, clipboard will use fallback")

    def copy_to_clipboard(self, data: str) -> bool:
        if self._available:
            try:
                self._pyperclip.copy(data)
                return True
            except Exception:
                return False
        return False

    def clear_clipboard(self) -> bool:
        return self.copy_to_clipboard("")

    def get_clipboard_content(self) -> Optional[str]:
        if self._available:
            try:
                return self._pyperclip.paste()
            except Exception:
                return None
        return None


class FallbackClipboardAdapter(ClipboardAdapter):
    """Fallback using basic pyperclip when platform-specific fails"""

    def __init__(self):
        self._available = False
        try:
            import pyperclip
            self._pyperclip = pyperclip
            self._available = True
        except ImportError:
            print("ERROR: pyperclip not installed. Please run: pip install pyperclip")

    def copy_to_clipboard(self, data: str) -> bool:
        if self._available:
            try:
                self._pyperclip.copy(data)
                return True
            except Exception:
                return False
        return False

    def clear_clipboard(self) -> bool:
        return self.copy_to_clipboard("")

    def get_clipboard_content(self) -> Optional[str]:
        if self._available:
            try:
                return self._pyperclip.paste()
            except Exception:
                return None
        return None


def create_platform_adapter(root=None) -> ClipboardAdapter:
    """Factory to create appropriate platform adapter"""
    system = platform.system()

    if system == 'Windows':
        adapter = WindowsClipboardAdapter()
        if adapter._available:
            return adapter
    elif system == 'Darwin':
        adapter = MacOSClipboardAdapter()
        if adapter._available:
            return adapter
    elif system == 'Linux':
        adapter = LinuxClipboardAdapter()
        if adapter._available:
            return adapter

    # Fallback
    return FallbackClipboardAdapter()
