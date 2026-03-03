import time
from typing import Optional


class StateManager:
  def __init__(self):
    self.locked = True
    self.last_activity = time.time()
    self.clipboard_content = None
    self.clipboard_timer = None

  def login(self):
    self.locked = False
    self.update_activity()

  def logout(self):
    self.locked = True

  def update_activity(self):
    self.last_activity = time.time()

  def check_auto_lock(self, timeout_minutes: int) -> bool:
    if self.locked:
      return True
    inactive = (time.time() - self.last_activity) / 60
    if inactive >= timeout_minutes:
      self.logout()
      return True
    return False

  def set_clipboard(self, content: str):
    self.clipboard_content = content
    self.clipboard_timer = time.time()

  def clear_clipboard(self):
    self.clipboard_content = None
    self.clipboard_timer = None
