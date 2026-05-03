"""Main clipboard service with auto-clear and secure operations"""

import threading
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from Crypts_man.src.core.clipboard.platform_adapter import create_platform_adapter
from Crypts_man.src.core.clipboard.clipboard_monitor import ClipboardMonitor
from Crypts_man.src.core.clipboard.secure_memory import SecureMemory
from Crypts_man.src.core.events import EventType


class SecureClipboardItem:
  """Secure clipboard item with memory protection"""

  def __init__(self, data: str, data_type: str, source_entry_id: Optional[str],
               copied_at: datetime, timeout: int, mask: bytes):
    self.data = data
    self.data_type = data_type
    self.source_entry_id = source_entry_id
    self.copied_at = copied_at
    self.timeout = timeout
    self.mask = mask


class ClipboardService:
  """Main clipboard service with auto-clear and security features"""

  def __init__(self, config, event_system, root=None):
    self.config = config
    self.events = event_system
    self.root = root
    self.platform = create_platform_adapter(root)
    self.memory = SecureMemory()
    self.monitor = ClipboardMonitor(self.platform, event_system, config)

    self.current_item: Optional[SecureClipboardItem] = None
    self.timer: Optional[threading.Timer] = None
    self.lock = threading.RLock()
    self._blocked = False

    self.timeout = config.get('clipboard_timeout', 30)
    self.security_level = config.get('clipboard_security_level', 'standard')

    self.monitor.start()
    self._setup_event_handlers()

  def _setup_event_handlers(self):
    """Setup internal event handlers"""
    if not self.events:
      return

    try:
      self.events.subscribe('AccelerateClipboardClear', self._accelerate_clear)
      self.events.subscribe('BlockClipboardOperations', self._block_operations)
      self.events.subscribe(EventType.USER_LOGGED_OUT, lambda _: self.clear(force=True))
    except Exception:
      pass

  def copy_to_clipboard(self, data: str, data_type: str = "password",
                        source_entry_id: Optional[str] = None) -> bool:
    """Securely copy data to system clipboard with auto-clear"""
    if self._blocked:
      if self.events:
        self.events.publish('ClipboardBlocked', {'reason': 'security_block'})
      return False

    with self.lock:
      self._clear_clipboard(notify=False)

      if not self.platform.copy_to_clipboard(data):
        return False

      self.current_item = SecureClipboardItem(
        data=data,
        data_type=data_type,
        source_entry_id=source_entry_id,
        copied_at=datetime.now(),
        timeout=self.timeout,
        mask=secrets.token_bytes(32)
      )

      self._start_timer()

      if self.events:
        self.events.publish(EventType.CLIPBOARD_COPIED, {
          'data_type': data_type,
          'source_entry_id': source_entry_id,
          'timeout': self.timeout
        })

      return True

  def _start_timer(self):
    """Start auto-clear timer"""
    if self.timer:
      self.timer.cancel()

    self.timer = threading.Timer(self.timeout, self._on_timeout)
    self.timer.daemon = True
    self.timer.start()

    if self.timeout > 5:
      warning_timer = threading.Timer(self.timeout - 5, self._on_warning)
      warning_timer.daemon = True
      warning_timer.start()

  def _on_warning(self):
    """Send warning before auto-clear"""
    if self.current_item and self.events:
      self.events.publish('ClipboardWillClear', {
        'seconds': 5,
        'data_type': self.current_item.data_type
      })

  def _on_timeout(self):
    """Handle auto-clear timeout"""
    with self.lock:
      was_active = self.current_item is not None
      self._clear_clipboard(notify=True)
      if was_active and self.events:
        self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': 'timeout'})

  def _accelerate_clear(self, data=None):
    """Accelerate auto-clear due to security detection"""
    with self.lock:
      if self.current_item:
        self._clear_clipboard(notify=True)
        if self.events:
          self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': 'accelerated_security'})

  def _block_operations(self, data=None):
    """Block all clipboard operations due to suspicious activity"""
    self._blocked = True
    self._clear_clipboard(notify=True)
    if self.events:
      self.events.publish('ClipboardOperationsBlocked', {})

  def clear(self, force: bool = False, reason: str = "manual") -> bool:
    """Manually clear clipboard"""
    with self.lock:
      if force or self.current_item:
        result = self._clear_clipboard(notify=True)
        if result and self.events:
          self.events.publish(EventType.CLIPBOARD_CLEARED, {'reason': reason})
        return result
    return False

  def _clear_clipboard(self, notify: bool = True) -> bool:
    """Internal method to securely clear clipboard"""
    success = self.platform.clear_clipboard()

    if self.current_item:
      self.current_item = None

    if self.timer:
      self.timer.cancel()
      self.timer = None

    self.monitor.reset_counters()

    return success

  def get_status(self) -> Dict[str, Any]:
    """Get current clipboard status"""
    with self.lock:
      if not self.current_item:
        return {'active': False, 'blocked': self._blocked}

      remaining = self._get_remaining_time()
      return {
        'active': True,
        'blocked': self._blocked,
        'data_type': self.current_item.data_type,
        'remaining_seconds': remaining.total_seconds() if remaining else 0,
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

  def shutdown(self):
    """Clean shutdown of clipboard service"""
    self.monitor.stop()
    self.clear(force=True)
