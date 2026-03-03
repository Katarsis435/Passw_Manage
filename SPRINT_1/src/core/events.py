from typing import Callable, Dict, List, Any
from enum import Enum


class EventType(Enum):
  ENTRY_ADDED = 'entry_added'
  ENTRY_UPDATED = 'entry_updated'
  ENTRY_DELETED = 'entry_deleted'
  USER_LOGIN = 'user_login'
  USER_LOGOUT = 'user_logout'
  CLIPBOARD_COPIED = 'clipboard_copied'
  CLIPBOARD_CLEARED = 'clipboard_cleared'


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

  # Асинхронная заглушка
  async def publish_async(self, event_type: EventType, data: Any = None):
    self.publish(event_type, data)


# Глобальная шина событий
event_bus = EventBus()
