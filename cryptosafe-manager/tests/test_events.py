# tests/test_events.py
import unittest
from src.core.events import EventSystem, EventType


class TestEvents(unittest.TestCase):
  """Test event system"""

  def setUp(self):
    self.events = EventSystem()
    self.callback_called = False
    self.callback_data = None

  def callback(self, data):
    self.callback_called = True
    self.callback_data = data

  def test_subscribe_publish(self):
    """Test subscribing and publishing"""
    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)

    test_data = {"id": 1, "title": "Test"}
    self.events.publish(EventType.ENTRY_ADDED, test_data)

    self.assertTrue(self.callback_called)
    self.assertEqual(self.callback_data, test_data)

  def test_unsubscribe(self):
    """Test unsubscribing"""
    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)
    self.events.unsubscribe(EventType.ENTRY_ADDED, self.callback)

    self.events.publish(EventType.ENTRY_ADDED, {"test": "data"})

    self.assertFalse(self.callback_called)

  def test_multiple_subscribers(self):
    """Test multiple subscribers"""
    callbacks_called = [False, False]

    def cb1(data):
      callbacks_called[0] = True

    def cb2(data):
      callbacks_called[1] = True

    self.events.subscribe(EventType.ENTRY_ADDED, cb1)
    self.events.subscribe(EventType.ENTRY_ADDED, cb2)

    self.events.publish(EventType.ENTRY_ADDED)

    self.assertTrue(all(callbacks_called))


if __name__ == '__main__':
  unittest.main()
