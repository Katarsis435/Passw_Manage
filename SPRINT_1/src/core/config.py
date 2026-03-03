import os
import json
from pathlib import Path


class Config:
  def __init__(self, env: str = 'development'):
    self.env = env
    self.data_dir = Path.home() / '.cryptosafe'
    self.data_dir.mkdir(exist_ok=True)

    self.db_path = self.data_dir / 'vault.db'
    self.settings_file = self.data_dir / 'settings.json'

    # Настройки по умолчанию
    self.settings = {
      'clipboard_timeout': 30,
      'auto_lock_minutes': 5,
      'theme': 'default',
      'language': 'ru'
    }

    self.load()

  def load(self):
    if self.settings_file.exists():
      try:
        with open(self.settings_file, 'r') as f:
          self.settings.update(json.load(f))
      except:
        pass

  def save(self):
    with open(self.settings_file, 'w') as f:
      json.dump(self.settings, f, indent=2)

  def get(self, key: str, default=None):
    return self.settings.get(key, default)

  def set(self, key: str, value):
    self.settings[key] = value
    self.save()
