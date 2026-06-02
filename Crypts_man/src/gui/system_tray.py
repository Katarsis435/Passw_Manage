import threading
import pystray
from PIL import Image, ImageDraw
from pathlib import Path


class SystemTray:
  def __init__(self, main_window, config):
    self.main_window = main_window
    self.config = config
    self.icon = None
    self.is_locked = True
    self._running = False

  def create_tray_icon(self):
    """Create tray icon with menu"""
    # Try to load custom icon
    icon_image = self._load_custom_icon()
    if icon_image is None:
      icon_image = self._create_default_icon()

    menu = pystray.Menu(
      pystray.MenuItem('🔓 Unlock Vault', self._unlock, enabled=lambda: self.is_locked),
      pystray.MenuItem('🔒 Lock Vault', self._lock, enabled=lambda: not self.is_locked),
      pystray.MenuItem('Show Window', self._show_window),
      pystray.MenuItem('Clear Clipboard', self._clear_clipboard),
      pystray.Menu.SEPARATOR,
      pystray.MenuItem('Panic Mode', self._panic),
      pystray.Menu.SEPARATOR,
      pystray.MenuItem('Exit', self._exit)
    )

    self.icon = pystray.Icon("cryptosafe", icon_image, "CryptoSafe Manager", menu)

  def _load_custom_icon(self):
    """Load custom icon from resources"""
    # Путь к иконке трея
    base_dir = Path(__file__).parent.parent  # Crypts_man/

    icon_paths = [
      base_dir / "resources" / "icons" / "tray_icon.png",
      base_dir / "resources" / "icons" / "tray_icon.ico",
      base_dir / "resources" / "icons" / "app_icon.png",
      base_dir / "resources" / "icons" / "app_icon.ico",
    ]

    for icon_path in icon_paths:
      if icon_path.exists():
        try:
          print(f"✓ Loading tray icon from: {icon_path}")
          return Image.open(icon_path)
        except Exception as e:
          print(f"⚠ Failed to load icon {icon_path}: {e}")

    print("⚠ No custom tray icon found, using default")
    return None

  def _create_default_icon(self):
    """Create default icon if file not found"""
    size = 64
    image = Image.new('RGB', (size, size), color='#2c3e50')
    draw = ImageDraw.Draw(image)

    # Draw a simple lock icon
    draw.rectangle([20, 30, 44, 50], fill='#3498db', outline='white', width=2)
    draw.arc([22, 18, 42, 38], start=0, end=180, fill='#3498db', width=4)
    draw.ellipse([28, 38, 36, 46], fill='white')
    draw.rectangle([31, 40, 33, 46], fill='#2c3e50')

    return image


  def run(self):
    """Run the tray icon (blocking)"""
    if self.icon:
      self._running = True
      self.icon.run()

  def stop(self):
    """Stop the tray icon"""
    self._running = False
    if self.icon:
      self.icon.stop()

  def _unlock(self):
    """Unlock vault - show login"""
    print("[TRAY] Unlock clicked")
    self.main_window.root.after(0, self.main_window._show_login)

  def _lock(self):
    """Lock vault"""
    print("[TRAY] Lock clicked")
    self.main_window.root.after(0, self.main_window._lock_vault)

  def _show_window(self):
    """Show main window"""
    print("[TRAY] Show window clicked")
    self.main_window.root.after(0, self._restore_window)

  def _restore_window(self):
    """Restore minimized window"""
    try:
      self.main_window.root.deiconify()  # Show window
      self.main_window.root.lift()  # Bring to front
      self.main_window.root.focus_force()  # Force focus
      print("[TRAY] Window restored")
    except Exception as e:
      print(f"[TRAY] Error restoring window: {e}")

  def _clear_clipboard(self):
    """Clear clipboard"""
    print("[TRAY] Clear clipboard clicked")
    if self.main_window.clipboard:
      self.main_window.clipboard.clear(force=True, reason="tray")
      # Update status
      self.main_window.root.after(0, lambda: self.main_window.status_label.config(text="Clipboard cleared via tray"))

  def _panic(self):
    """Activate panic mode"""
    print("[TRAY] Panic mode clicked")
    self.main_window.root.after(0, self.main_window._activate_panic_mode)

  def _exit(self):
    """Exit application"""
    print("[TRAY] Exit clicked")
    self.main_window.root.after(0, self.main_window._quit)

  def update_lock_status(self, locked: bool):
    """Update lock status (affects menu)"""
    self.is_locked = locked
    # Update icon color based on status
    if self.icon:
      if locked:
        # Red icon for locked
        icon_image = self._create_locked_icon()
      else:
        # Green icon for unlocked
        icon_image = self._create_unlocked_icon()
      self.icon.icon = icon_image

  def _create_locked_icon(self):
    """Create locked state icon (red)"""
    size = 64
    image = Image.new('RGB', (size, size), color='#8B0000')  # Dark red
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 30, 44, 50], fill='#DC143C', outline='white', width=2)
    draw.arc([22, 18, 42, 38], start=0, end=180, fill='#DC143C', width=4)
    draw.ellipse([28, 38, 36, 46], fill='white')
    draw.rectangle([31, 40, 33, 46], fill='#8B0000')
    return image

  def _create_unlocked_icon(self):
    """Create unlocked state icon (green)"""
    size = 64
    image = Image.new('RGB', (size, size), color='#006400')  # Dark green
    draw = ImageDraw.Draw(image)
    # Open lock (arc rotated)
    draw.rectangle([20, 30, 44, 50], fill='#32CD32', outline='white', width=2)
    draw.arc([22, 18, 42, 38], start=180, end=360, fill='#32CD32', width=4)
    draw.ellipse([28, 38, 36, 46], fill='white')
    draw.rectangle([31, 40, 33, 46], fill='#006400')
    return image
