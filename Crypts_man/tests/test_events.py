# tests/test_core/test_events.py
import unittest
from Crypts_man.src.core.events import EventSystem, EventType


class TestEventSystem(unittest.TestCase):
  """Tests for event system"""

  def setUp(self):
    self.events = EventSystem()
    self.callback_called = False
    self.callback_data = None

  def callback(self, data):
    self.callback_called = True
    self.callback_data = data

  def test_subscribe_and_publish(self):
    """Test subscribing to and publishing events"""
    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)

    test_data = {'id': 1, 'title': 'Test'}
    self.events.publish(EventType.ENTRY_ADDED, test_data)

    self.assertTrue(self.callback_called)
    self.assertEqual(self.callback_data, test_data)

  def test_multiple_subscribers(self):
    """Test multiple subscribers to same event"""
    callback2_called = False

    def callback2(data):
      nonlocal callback2_called
      callback2_called = True

    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)
    self.events.subscribe(EventType.ENTRY_ADDED, callback2)

    self.events.publish(EventType.ENTRY_ADDED, {})

    self.assertTrue(self.callback_called)
    self.assertTrue(callback2_called)

  def test_unsubscribe(self):
    """Test unsubscribing from events"""
    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)
    self.events.unsubscribe(EventType.ENTRY_ADDED, self.callback)

    self.events.publish(EventType.ENTRY_ADDED, {})

    self.assertFalse(self.callback_called)

  def test_different_event_types(self):
    """Test events don't trigger wrong callbacks"""
    self.events.subscribe(EventType.ENTRY_ADDED, self.callback)

    self.events.publish(EventType.ENTRY_UPDATED, {})

    self.assertFalse(self.callback_called)


if __name__ == '__main__':
  unittest.main()
