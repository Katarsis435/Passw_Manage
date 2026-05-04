"""Secure clipboard module for CryptoSafe Manager"""

from .clipboard_service import ClipboardService
from .platform_adapter import ClipboardAdapter, WindowsClipboardAdapter, MacOSClipboardAdapter, LinuxClipboardAdapter, FallbackClipboardAdapter, create_platform_adapter
from .clipboard_monitor import ClipboardMonitor
from .secure_memory import SecureMemory

__all__ = [
    'ClipboardService',
    'ClipboardAdapter',
    'WindowsClipboardAdapter',
    'MacOSClipboardAdapter',
    'LinuxClipboardAdapter',
    'FallbackClipboardAdapter',
    'create_platform_adapter',
    'ClipboardMonitor',
    'SecureMemory'
]
