import time


class StateManager:
  def __init__(self):
    self.locked = True
    self.last_activity = time.time()
    self.clipboard_content = None
    self.clipboard_timer = None

  def update_activity(self):
    self.last_activity = time.time()

  def check_auto_lock(self, timeout_minutes):
    if not self.locked:
      inactive = (time.time() - self.last_activity) / 60
      if inactive >= timeout_minutes:
        self.locked = True
        return True
    return False
