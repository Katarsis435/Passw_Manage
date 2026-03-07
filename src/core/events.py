# src/core/events.py
from typing import Dict, Any, Callable, List
from enum import Enum
import threading
import logging


class EventType(Enum):
  """Application event types"""
  ENTRY_ADDED = "entry_added"
  ENTRY_UPDATED = "entry_updated"
  ENTRY_DELETED = "entry_deleted"
  USER_LOGGED_IN = "user_logged_in"
  USER_LOGGED_OUT = "user_logged_out"
  CLIPBOARD_COPIED = "clipboard_copied"
  CLIPBOARD_CLEARED = "clipboard_cleared"
  DATABASE_BACKUP = "database_backup"
  SETTINGS_CHANGED = "settings_changed"


class Event:
  """Event object containing type and data"""

  def __init__(self, event_type: EventType, data: Dict[str, Any] = None):
    self.type = event_type
    self.data = data or {}


class EventBus:
  """Central event bus for application-wide communication"""

  _instance = None
  _lock = threading.Lock()

  def __new__(cls):
    with cls._lock:
      if cls._instance is None:
        cls._instance = super().__new__(cls)
        cls._instance._subscribers = {event_type: [] for event_type in EventType}
        cls._instance._async_handlers = []
        cls._instance._logger = logging.getLogger(__name__)
      return cls._instance

  def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
    """Subscribe to an event type"""
    if event_type not in self._subscribers:
      self._subscribers[event_type] = []
    self._subscribers[event_type].append(callback)
    self._logger.debug(f"Subscribed to {event_type.value}")

  def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
    """Unsubscribe from an event type"""
    if event_type in self._subscribers:
      if callback in self._subscribers[event_type]:
        self._subscribers[event_type].remove(callback)
        self._logger.debug(f"Unsubscribed from {event_type.value}")

  def publish(self, event: Event, sync: bool = True) -> None:
    """Publish an event to all subscribers"""
    self._logger.debug(f"Publishing event: {event.type.value}")

    if sync:
      self._publish_sync(event)
    else:
      self._publish_async(event)

  def _publish_sync(self, event: Event) -> None:
    """Publish event synchronously"""
    if event.type in self._subscribers:
      for callback in self._subscribers[event.type]:
        try:
          callback(event)
        except Exception as e:
          self._logger.error(f"Error in event handler: {e}")

  def _publish_async(self, event: Event) -> None:
    """Publish event asynchronously"""
    thread = threading.Thread(target=self._publish_sync, args=(event,))
    thread.daemon = True
    thread.start()
