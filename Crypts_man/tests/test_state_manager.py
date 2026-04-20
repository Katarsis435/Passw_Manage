# tests/test_core/test_state_manager.py
import unittest
import time
from Crypts_man.src.core.state_manager import StateManager


class TestStateManager(unittest.TestCase):
  """Tests for state manager"""

  def setUp(self):
    self.state = StateManager()

  def test_initial_state_locked(self):
    """Test initial state is locked"""
    self.assertTrue(self.state.is_locked)
    self.assertIsNone(self.state.current_user)

  def test_unlock_and_lock(self):
    """Test unlocking and locking"""
    self.state.unlock("test_user")
    self.assertFalse(self.state.is_locked)
    self.assertEqual(self.state.current_user, "test_user")

    self.state.lock()
    self.assertTrue(self.state.is_locked)
    self.assertIsNone(self.state.current_user)

  def test_clipboard_management(self):
    """Test clipboard content management"""
    test_content = "test_password"

    self.state.set_clipboard(test_content)
    self.assertEqual(self.state._clipboard_content, test_content)
    self.assertIsNotNone(self.state._clipboard_timestamp)

    self.state.clear_clipboard()
    self.assertIsNone(self.state._clipboard_content)
    self.assertIsNone(self.state._clipboard_timestamp)

  def test_activity_tracking(self):
    """Test activity timestamp updates"""
    initial_time = self.state._last_activity

    time.sleep(0.1)
    self.state.update_activity()

    self.assertGreater(self.state._last_activity, initial_time)

  def test_inactive_seconds(self):
    """Test inactive seconds calculation"""
    self.state.update_activity()
    time.sleep(0.1)

    inactive = self.state.get_inactive_seconds()
    self.assertGreaterEqual(inactive, 0.09)

  def test_auto_lock_check(self):
    """Test auto-lock condition check"""
    self.state.unlock()

    # Should not auto-lock with timeout 1 minute
    self.assertFalse(self.state.should_auto_lock(1))

    # Manually set last activity to long ago
    import datetime
    self.state._last_activity = datetime.datetime.now() - datetime.timedelta(minutes=2)
    self.assertTrue(self.state.should_auto_lock(1))

    # Locked vault should not auto-lock
    self.state.lock()
    self.assertFalse(self.state.should_auto_lock(1))


if __name__ == '__main__':
  unittest.main()
