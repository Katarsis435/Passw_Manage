# src/core/state_manager.py
from typing import Optional
from datetime import datetime, timedelta


class StateManager:
  """Centralized state management"""

  def __init__(self):
    self._locked = True
    self._current_user: Optional[str] = None
    self._clipboard_content: Optional[str] = None
    self._clipboard_timestamp: Optional[datetime] = None
    self._last_activity: datetime = datetime.now()

  @property
  def is_locked(self) -> bool:
    """Check if vault is locked"""
    return self._locked

  def lock(self) -> None:
    """Lock the vault"""
    self._locked = True
    self._current_user = None

  def unlock(self, username: str = "user") -> None:
    """Unlock the vault"""
    self._locked = False
    self._current_user = username
    self.update_activity()

  @property
  def current_user(self) -> Optional[str]:
    """Get current logged in user"""
    return self._current_user

  def set_clipboard(self, content: str) -> None:
    """Set clipboard content with timestamp"""
    self._clipboard_content = content
    self._clipboard_timestamp = datetime.now()

  def clear_clipboard(self) -> None:
    """Clear clipboard content"""
    self._clipboard_content = None
    self._clipboard_timestamp = None

  def update_activity(self) -> None:
    """Update last activity timestamp"""
    self._last_activity = datetime.now()

  def get_inactive_seconds(self) -> float:
    """Get seconds since last activity"""
    return (datetime.now() - self._last_activity).total_seconds()

  def should_auto_lock(self, timeout_minutes: int) -> bool:
    """Check if auto-lock should trigger"""
    if self.is_locked:
      return False
    return self.get_inactive_seconds() > (timeout_minutes * 60)
