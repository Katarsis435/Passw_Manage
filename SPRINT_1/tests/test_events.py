import unittest
from src.core.events import EventBus, EventType


class TestEvents(unittest.TestCase):
  def setUp(self):
    self.bus = EventBus()
    self.called = False
    self.data = None

  def test_subscribe_publish(self):
    def callback(data):
      self.called = True
      self.data = data

    self.bus.subscribe(EventType.ENTRY_ADDED, callback)
    self.bus.publish(EventType.ENTRY_ADDED, {'id': 1})

    self.assertTrue(self.called)
    self.assertEqual(self.data, {'id': 1})

  def test_multiple_subscribers(self):
    count = 0

    def inc(data):
      nonlocal count
      count += 1

    self.bus.subscribe(EventType.USER_LOGIN, inc)
    self.bus.subscribe(EventType.USER_LOGIN, inc)
    self.bus.publish(EventType.USER_LOGIN)

    self.assertEqual(count, 2)


if __name__ == '__main__':
  unittest.main()
