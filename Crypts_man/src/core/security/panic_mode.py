import sys
from typing import List, Callable


class PanicMode:
  def __init__(self, config: dict):
    self.config = config
    self.activated = False
    self.handlers: List[Callable] = []
    self._register_default_handlers()

  def _register_default_handlers(self):
    self.handlers.append(self._clear_clipboard)
    self.handlers.append(self._lock_vault)
    self.handlers.append(self._close_windows)

  def activate(self, method: str = "hotkey"):
    if self.activated:
      return
    self.activated = True
    for handler in self.handlers:
      try:
        handler()
      except Exception as e:
        print(f"Panic handler failed: {e}")

    if self.config.get('stealth_mode', False):
      self._show_fake_error()

    self._log_panic(method)

  def _clear_clipboard(self):
    import pyperclip
    pyperclip.copy('')

  def _lock_vault(self):
    from Crypts_man.src.core.events import events, EventType
    events.publish(EventType.USER_LOGGED_OUT)

  def _close_windows(self):
    # Will be integrated with MainWindow
    pass

  def _show_fake_error(self):
    import tkinter.messagebox as mb
    mb.showerror("Application Error", "An unexpected error has occurred.")

  def _log_panic(self, method: str):
    print(f"[PANIC] Activated via {method}")
