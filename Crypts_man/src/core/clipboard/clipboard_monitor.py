"""Clipboard monitoring and defense against external access"""

import threading
import time
from typing import Optional, Callable
from datetime import datetime


class ClipboardMonitor:
  """Monitors clipboard for external changes and access attempts"""

  def __init__(self, platform_adapter, event_system, config):
    self.platform = platform_adapter
    self.events = event_system
    self.config = config
    self._monitoring = False
    self._monitor_thread: Optional[threading.Thread] = None
    self._last_content: Optional[str] = None
    self._external_changes_detected = 0
    self._suspicious_access_count = 0
    self._lock = threading.RLock()

  def start(self) -> bool:
    """Start clipboard monitoring"""
    if self._monitoring:
      return True
    self._monitoring = True
    self._monitor_thread = threading.Thread(target=self._polling_loop, daemon=True)
    self._monitor_thread.start()
    return True

  def stop(self) -> None:
    """Stop clipboard monitoring"""
    self._monitoring = False
    self.platform.stop_monitoring()

  def _polling_loop(self):
    """Poll clipboard for changes (fallback)"""
    while self._monitoring:
      try:
        current = self.platform.get_clipboard_content()

        if current != self._last_content and self._last_content is not None:
          if current != self._last_content:
            self._on_external_change(current)

        self._last_content = current
        time.sleep(0.5)
      except Exception:
        time.sleep(1)

  def _on_external_change(self, new_content: str):
    """Handle external clipboard change (potential snooping)"""
    with self._lock:
      self._external_changes_detected += 1

      if self.events:
        self.events.publish('ClipboardExternalChange', {
          'timestamp': datetime.now(),
          'detection_count': self._external_changes_detected
        })

      if self.config.get('accelerate_on_detection', True):
        if self.events:
          self.events.publish('AccelerateClipboardClear', {
            'reason': 'external_change'
          })

  def detect_suspicious_access(self) -> None:
    """Record a suspicious clipboard access attempt"""
    with self._lock:
      self._suspicious_access_count += 1

      if self.events:
        self.events.publish('SuspiciousClipboardAccess', {
          'timestamp': datetime.now(),
          'count': self._suspicious_access_count
        })

        threshold = self.config.get('suspicious_threshold', 5)
        if self._suspicious_access_count >= threshold:
          self.events.publish('BlockClipboardOperations', {
            'reason': 'suspicious_access_threshold'
          })

  def reset_counters(self) -> None:
    """Reset detection counters"""
    with self._lock:
      self._external_changes_detected = 0
      self._suspicious_access_count = 0

  def is_secure(self) -> bool:
    """Check if clipboard appears secure"""
    return self._external_changes_detected < 3 and self._suspicious_access_count < 2
