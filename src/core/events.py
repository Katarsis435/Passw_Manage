from enum import Enum, auto
from typing import Callable, Dict, List, Any


class EventType(Enum):
  ENTRY_ADDED = auto()
  ENTRY_UPDATED = auto()
  ENTRY_DELETED = auto()
  USER_LOGGED_IN = auto()
  USER_LOGGED_OUT = auto()
  CLIPBOARD_COPIED = auto()
  CLIPBOARD_CLEARED = auto()


class EventBus:
  def __init__(self):
    self._subscribers: Dict[EventType, List[Callable]] = {}

  def subscribe(self, event_type: EventType, callback: Callable):
    if event_type not in self._subscribers:
      self._subscribers[event_type] = []
    self._subscribers[event_type].append(callback)

  def publish(self, event_type: EventType, data: Any = None):
    for callback in self._subscribers.get(event_type, []):
      callback(data)
