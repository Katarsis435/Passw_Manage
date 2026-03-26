# src/core/events.py
from typing import Callable, Dict, List, Any
from enum import Enum


class EventType(Enum):
  ENTRY_ADDED = "entry_added"
  ENTRY_UPDATED = "entry_updated"
  ENTRY_DELETED = "entry_deleted"
  USER_LOGGED_IN = "user_logged_in"
  USER_LOGGED_OUT = "user_logged_out"
  CLIPBOARD_COPIED = "clipboard_copied"
  CLIPBOARD_CLEARED = "clipboard_cleared"


class EventSystem:
  """Simple event bus for decoupled communication"""

  def __init__(self):
    self._subscribers: Dict[EventType, List[Callable]] = {}

  def subscribe(self, event_type: EventType, callback: Callable) -> None:
    """Subscribe to an event"""
    if event_type not in self._subscribers:
      self._subscribers[event_type] = []
    self._subscribers[event_type].append(callback)

  def publish(self, event_type: EventType, data: Any = None, sync: bool = True) -> None:
    """Publish an event to all subscribers"""
    if event_type not in self._subscribers:
      return

    for callback in self._subscribers[event_type]:
      if sync:
        callback(data)
      else:
        # For async, we could use threading, but keep simple for Sprint 1
        callback(data)

  def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
    """Remove a subscriber"""
    if event_type in self._subscribers:
      if callback in self._subscribers[event_type]:
        self._subscribers[event_type].remove(callback)


# Global event system instance
events = EventSystem()
