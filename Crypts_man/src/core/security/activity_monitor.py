import threading
import time
from datetime import datetime
from typing import Callable, Optional


class ActivityMonitor:
  def __init__(self, lock_callback: Callable, config: dict):
    self.lock_callback = lock_callback
    self.config = config
    self.last_activity = datetime.now()
    self.monitoring = False
    self.monitor_thread: Optional[threading.Thread] = None
    self._lock = threading.Lock()
    self._is_locking = False  # <--- ДОБАВИТЬ

  def start_monitoring(self):
    if self.monitoring:
      return
    self.monitoring = True
    self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
    self.monitor_thread.start()

  def stop_monitoring(self):
    self.monitoring = False

  def record_activity(self):
    with self._lock:
      self.last_activity = datetime.now()

  def _monitor_loop(self):
    while self.monitoring:
      timeout_minutes = self.config.get('auto_lock_minutes', 5)
      timeout_seconds = timeout_minutes * 60

      with self._lock:
        idle = (datetime.now() - self.last_activity).total_seconds()

      # НЕ блокируем если уже в процессе блокировки
      if idle > timeout_seconds and timeout_seconds > 0 and not self._is_locking:
        with self._lock:
          self._is_locking = True
        self.lock_callback()
        # После разблокировки сбрасываем флаг и активность
        with self._lock:
          self.last_activity = datetime.now()
          self._is_locking = False

      time.sleep(5)

  def get_idle_time(self) -> float:
    with self._lock:
      return (datetime.now() - self.last_activity).total_seconds()

  def reset_activity(self):  # <--- ДОБАВИТЬ МЕТОД
    """Reset activity timer after unlock"""
    with self._lock:
      self.last_activity = datetime.now()
      self._is_locking = False
