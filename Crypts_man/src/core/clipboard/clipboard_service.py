# src/core/clipboard/clipboard_service.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ

"""Main clipboard service with auto-clear and security features"""

import threading
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from Crypts_man.src.core.clipboard.platform_adapter import create_platform_adapter
from Crypts_man.src.core.clipboard.clipboard_monitor import ClipboardMonitor
from Crypts_man.src.core.events import events, EventType


class SecureClipboardItem:
    """Secure clipboard item with memory protection - OBFUSCATED"""

    def __init__(self, data: str, data_type: str, source_entry_id: Optional[str],
                 copied_at: datetime, timeout: int):
        self.data_type = data_type
        self.source_entry_id = source_entry_id
        self.copied_at = copied_at
        self.timeout = timeout

        # ОБФУСЦИРУЕМ данные сразу, не храним plaintext
        self._mask = secrets.token_bytes(32)
        self._obfuscated_data = self._obfuscate(data)
        self._data_len = len(data)  # Для валидации

    def _obfuscate(self, data: str) -> bytes:
        """XOR obfuscation of data"""
        data_bytes = data.encode('utf-8')
        result = bytearray()
        for i, b in enumerate(data_bytes):
            result.append(b ^ self._mask[i % len(self._mask)])
        return bytes(result)

    def _deobfuscate(self) -> str:
        """Get original data"""
        data_bytes = bytearray()
        for i, b in enumerate(self._obfuscated_data):
            data_bytes.append(b ^ self._mask[i % len(self._mask)])
        return data_bytes.decode('utf-8')

    @property
    def data(self) -> str:
        """Get decrypted data (only when needed)"""
        return self._deobfuscate()

    def secure_wipe(self):
        """Securely wipe memory"""
        if self._obfuscated_data:
            # Перезаписываем нулями
            self._obfuscated_data = b'\x00' * len(self._obfuscated_data)
        if self._mask:
            self._mask = b'\x00' * len(self._mask)


class ClipboardService:
    """Main clipboard service with auto-clear and security features"""

    def __init__(self, config, event_system, root=None):
        self.config = config
        self.events = event_system
        self.root = root
        self.platform = create_platform_adapter(root)
        self.monitor = ClipboardMonitor(self.platform, event_system, config)

        self.current_item: Optional[SecureClipboardItem] = None
        self.timer: Optional[threading.Timer] = None
        self.warning_timer: Optional[threading.Timer] = None
        self.lock = threading.RLock()
        self._blocked = False

        self.timeout = config.get('clipboard_timeout', 30)
        self.security_level = config.get('clipboard_security_level', 'standard')
        self.notifications_enabled = config.get('clipboard_notifications', True)

        self.monitor.start()
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup internal event handlers"""
        if not self.events:
            return

        try:
            # Используем правильные EventType
            self.events.subscribe('AccelerateClipboardClear', self._accelerate_clear)
            self.events.subscribe('BlockClipboardOperations', self._block_operations)
            self.events.subscribe(EventType.USER_LOGGED_OUT, lambda _: self.clear(force=True, reason="logout"))
        except Exception as e:
            print(f"Event handler setup error: {e}")

    def copy_to_clipboard(self, data: str, data_type: str = "password",
                          source_entry_id: Optional[str] = None) -> bool:
        """Securely copy data to system clipboard with auto-clear"""
        print(f"=== COPY: {data_type}, data length={len(data)} ===")

        if self._blocked:
            print("BLOCKED: Clipboard operations blocked")
            if self.events:
                self.events.publish('ClipboardBlocked', {'reason': 'security_block'})
            self._show_notification("⚠️ Clipboard blocked", "Security risk detected!")
            return False

        if not data:
            return False

        with self.lock:
            # Clear any existing content first
            self._clear_clipboard(notify=False)

            # CRITICAL: Create SecureClipboardItem FIRST with full data
            self.current_item = SecureClipboardItem(
                data=data,
                data_type=data_type,
                source_entry_id=source_entry_id,
                copied_at=datetime.now(),
                timeout=self.timeout
            )

            # Copy to system clipboard (unfortunately plaintext is required here)
            # This is a limitation of system clipboard APIs
            if not self.platform.copy_to_clipboard(data):
                print("Failed to copy to system clipboard")
                self.current_item = None
                return False

            print(f"Item created, timeout={self.timeout}s")

            # Start auto-clear timers
            self._start_timers()
            print(f"Timers started")

            # Show notification
            self._show_notification(
                f"📋 {data_type.capitalize()} copied",
                f"Will auto-clear in {self.timeout} seconds"
            )

            # Publish event
            if self.events:
                events.publish(EventType.CLIPBOARD_COPIED, {
                    'data_type': data_type,
                    'source_entry_id': source_entry_id,
                    'timeout': self.timeout
                })

            return True

    def _start_timers(self):
        """Start auto-clear and warning timers"""
        # Cancel existing timers
        if self.timer:
            self.timer.cancel()
        if self.warning_timer:
            self.warning_timer.cancel()

        # Warning timer (5 seconds before clear)
        warning_time = max(0, self.timeout - 5)
        if warning_time > 0:
            self.warning_timer = threading.Timer(warning_time, self._on_warning)
            self.warning_timer.daemon = True
            self.warning_timer.start()

        # Clear timer
        self.timer = threading.Timer(self.timeout, self._on_timeout)
        self.timer.daemon = True
        self.timer.start()
        print(f"Timers started: warning at {warning_time}s, clear at {self.timeout}s")

    def _on_warning(self):
        """Send warning before auto-clear"""
        print(f"=== WARNING: Clipboard will clear in 5 seconds ===")

        # Show warning notification
        if self.current_item and self.notifications_enabled:
            self._show_notification(
                "⚠️ Clipboard will clear soon",
                f"{self.current_item.data_type.capitalize()} will be cleared in 5 seconds",
                warning=True
            )

        if self.events:
            self.events.publish('ClipboardWillClear', {
                'seconds': 5,
                'data_type': self.current_item.data_type if self.current_item else 'unknown'
            })

    def _on_timeout(self):
        """Handle auto-clear timeout"""
        print(f"=== TIMEOUT FIRED at {datetime.now()} ===")

        # Execute clear in main thread if root exists
        if self.root:
            self.root.after(0, self._do_clear_from_timeout)
        else:
            self._do_clear_from_timeout()

    def _do_clear_from_timeout(self):
        """Execute clear in main thread"""
        with self.lock:
            was_active = self.current_item is not None
            print(f"Was active: {was_active}")
            self._clear_clipboard(notify=True)
            if was_active:
                print("Clipboard cleared by timeout")
                if self.events:
                    self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': 'timeout'})

    def _accelerate_clear(self, data=None):
        """Accelerate auto-clear due to security detection"""
        print("=== ACCELERATING CLEAR due to security detection ===")
        with self.lock:
            if self.current_item:
                # Clear immediately
                self._clear_clipboard(notify=True)
                self._show_notification("🔒 Clipboard cleared", "Suspicious activity detected!", warning=True)
                if self.events:
                    self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': 'accelerated_security'})

    def _block_operations(self, data=None):
        """Block all clipboard operations due to suspicious activity"""
        print("=== BLOCKING clipboard operations ===")
        self._blocked = True
        self._clear_clipboard(notify=True)
        self._show_notification("🚫 Clipboard blocked", "Too many suspicious accesses!", warning=True)
        if self.events:
            self.events.publish('ClipboardOperationsBlocked', {})

    def clear(self, force: bool = False, reason: str = "manual") -> bool:
        """Manually clear clipboard"""
        with self.lock:
            if force or self.current_item:
                result = self._clear_clipboard(notify=True)
                if result and self.events:
                    self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': reason})
                if reason != "auto":
                    self._show_notification("🧹 Clipboard cleared", "Manual clear")
                return result
        return False

    def _clear_clipboard(self, notify: bool = True) -> bool:
        """Internal method to securely clear clipboard"""
        print(f"=== CLEARING CLIPBOARD, notify={notify} ===")

        # Clear system clipboard
        result = self.platform.clear_clipboard()
        print(f"Platform clear result: {result}")

        # Securely wipe memory
        if self.current_item:
            self.current_item.secure_wipe()
            self.current_item = None
            print("Memory wiped")

        # Cancel timers
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.warning_timer:
            self.warning_timer.cancel()
            self.warning_timer = None

        return result

    def _show_notification(self, title: str, message: str, warning: bool = False):
        """Show toast notification"""
        if not self.notifications_enabled:
            return

        if self.root:
            try:
                # Use tkinter messagebox as fallback, but better to use platform notifications
                from tkinter import messagebox
                # Don't block with messagebox, just log
                print(f"🔔 {title}: {message}")
            except:
                print(f"🔔 {title}: {message}")
        else:
            print(f"🔔 {title}: {message}")

    def get_status(self) -> Dict[str, Any]:
        """Get current clipboard status"""
        with self.lock:
            if not self.current_item:
                return {'active': False, 'blocked': self._blocked}

            remaining = self._get_remaining_time()
            remaining_seconds = remaining.total_seconds() if remaining else 0

            return {
                'active': True,
                'blocked': self._blocked,
                'data_type': self.current_item.data_type,
                'remaining_seconds': remaining_seconds,
                'remaining_formatted': str(remaining).split('.')[0] if remaining else '0',
                'source_entry_id': self.current_item.source_entry_id
            }

    def _get_remaining_time(self) -> Optional[timedelta]:
        """Get remaining time until auto-clear"""
        if not self.current_item:
            return None
        elapsed = datetime.now() - self.current_item.copied_at
        remaining = max(0, self.timeout - elapsed.total_seconds())
        return timedelta(seconds=remaining)

    def update_settings(self, timeout: int = None, security_level: str = None):
        """Update clipboard settings"""
        if timeout is not None:
            self.timeout = timeout
            self.config.set('clipboard_timeout', timeout)

        if security_level is not None:
            self.security_level = security_level
            self.config.set('clipboard_security_level', security_level)

            if security_level == 'paranoid':
                self.timeout = 5
                self.config.set('clipboard_timeout', 5)
            elif security_level == 'secure':
                self.timeout = 15
                self.config.set('clipboard_timeout', 15)
            else:
                self.timeout = 30
                self.config.set('clipboard_timeout', 30)

    def get_current_item(self) -> Optional[SecureClipboardItem]:
        """Get current clipboard item (for status display)"""
        return self.current_item

    def shutdown(self):
        """Clean shutdown of clipboard service"""
        print("Shutting down clipboard service...")
        self.monitor.stop()
        self.clear(force=True, reason="shutdown")
