# src/core/state_manager.py
import time
from typing import Optional, Any
from datetime import datetime, timedelta
from threading import Timer
from .events import EventBus, Event, EventType


class StateManager:
  """Centralized state management for the application"""

  def __init__(self, config):
    self._config = config
    self._event_bus = EventBus()

    # Session state
    self._is_locked = True
    self._current_user = None
    self._last_activity = datetime.now()

    # Clipboard state
    self._clipboard_content = None
    self._clipboard_timer = None
    self._clipboard_timeout = config.get("clipboard_timeout", 30)

    # Inactivity timer for auto-lock
    self._inactivity_timer = None
    self._auto_lock_minutes = config.get("auto_lock_minutes", 5)

    # Start monitoring
    self._start_inactivity_monitor()

  def _start_inactivity_monitor(self) -> None:
    """Start monitoring user inactivity"""
    self._reset_inactivity_timer()

  def _reset_inactivity_timer(self) -> None:
    """Reset the inactivity timer"""
    if self._inactivity_timer:
      self._inactivity_timer.cancel()

    if not self._is_locked and self._auto_lock_minutes > 0:
      self._inactivity_timer = Timer(
        self._auto_lock_minutes * 60,
        self._auto_lock
      )
      self._inactivity_timer.daemon = True
      self._inactivity_timer.start()

  def _auto_lock(self) -> None:
    """Auto-lock the application due to inactivity"""
    if not self._is_locked:
      self.lock()

  def update_activity(self) -> None:
    """Update last activity timestamp"""
    self._last_activity = datetime.now()
    self._reset_inactivity_timer()

  def unlock(self, user: str = "default") -> None:
    """Unlock the application"""
    self._is_locked = False
    self._current_user = user
    self.update_activity()
    self._event_bus.publish(Event(EventType.USER_LOGGED_IN, {"user": user}))

  def lock(self) -> None:
    """Lock the application"""
    self._is_locked = True
    self._current_user = None
    self._event_bus.publish(Event(EventType.USER_LOGGED_OUT, {}))

    # Clear clipboard on lock
    self.clear_clipboard()

  @property
  def is_locked(self) -> bool:
    """Check if application is locked"""
    return self._is_locked

  @property
  def current_user(self) -> Optional[str]:
    """Get current user"""
    return self._current_user

  def set_clipboard(self, content: str) -> None:
    """Set clipboard content with timeout"""
    self._clipboard_content = content

    # Cancel existing timer
    if self._clipboard_timer:
      self._clipboard_timer.cancel()

    # Set new timer for clipboard clearing
    if self._clipboard_timeout > 0:
      self._clipboard_timer = Timer(
        self._clipboard_timeout,
        self.clear_clipboard
      )
      self._clipboard_timer.daemon = True
      self._clipboard_timer.start()

    self._event_bus.publish(Event(EventType.CLIPBOARD_COPIED, {
      "content_length": len(content)
    }))

  def clear_clipboard(self) -> None:
    """Clear clipboard content"""
    if self._clipboard_content:
      self._clipboard_content = None
      self._event_bus.publish(Event(EventType.CLIPBOARD_CLEARED, {}))

  def get_clipboard(self) -> Optional[str]:
    """Get clipboard content"""
    return self._clipboard_content

  def get_inactivity_minutes(self) -> float:
    """Get minutes since last activity"""
    delta = datetime.now() - self._last_activity
    return delta.total_seconds() / 60
