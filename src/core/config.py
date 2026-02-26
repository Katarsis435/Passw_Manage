import json
from pathlib import Path


class Config:
  def __init__(self):
    self.config_dir = Path.home() / '.cryptosafe'
    self.config_file = self.config_dir / 'config.json'
    self._ensure_config_dir()
    self.settings = self._load_defaults()

  def _ensure_config_dir(self):
    self.config_dir.mkdir(exist_ok=True)

  def _load_defaults(self):
    defaults = {
      'db_path': str(self.config_dir / 'vault.db'),
      'encryption': 'placeholder',
      'clipboard_timeout': 30,
      'auto_lock': 5,
      'theme': 'default'
    }

    if self.config_file.exists():
      with open(self.config_file) as f:
        defaults.update(json.load(f))

    return defaults

  def save(self):
    with open(self.config_file, 'w') as f:
      json.dump(self.settings, f, indent=2)

  def get(self, key, default=None):
    return self.settings.get(key, default)

  def set(self, key, value):
    self.settings[key] = value
    self.save()
