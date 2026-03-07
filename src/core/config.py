# src/core/config.py
import json
import os
import sqlite3
from typing import Any, Optional
from pathlib import Path


class Config:
  """Configuration manager for the application"""

  DEFAULT_CONFIG = {
    "database_path": str(Path.home() / ".cryptosafe" / "vault.db"),
    "encryption_algorithm": "AES256Placeholder",  # Will be upgraded in Sprint 3
    "key_derivation_iterations": 100000,
    "clipboard_timeout": 30,  # seconds
    "auto_lock_minutes": 5,
    "theme": "default",
    "language": "en",
    "backup_enabled": True,
    "backup_interval_days": 7,
    "dev_mode": False
  }

  def __init__(self):
    self._config = self.DEFAULT_CONFIG.copy()
    self._config_path = Path.home() / ".cryptosafe" / "config.json"
    self._db_connection = None

    # Create config directory if it doesn't exist
    self._config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create default
    self._load_or_create_config()

  def _load_or_create_config(self) -> None:
    """Load configuration from file or create default"""
    if self._config_path.exists():
      try:
        with open(self._config_path, 'r') as f:
          loaded_config = json.load(f)
          self._config.update(loaded_config)
      except Exception as e:
        print(f"Error loading config: {e}")
    else:
      self.save_config()

  def save_config(self) -> None:
    """Save configuration to file"""
    try:
      with open(self._config_path, 'w') as f:
        json.dump(self._config, f, indent=4)
    except Exception as e:
      print(f"Error saving config: {e}")

  def get(self, key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return self._config.get(key, default)

  def set(self, key: str, value: Any) -> None:
    """Set configuration value"""
    self._config[key] = value
    self.save_config()

  @property
  def database_path(self) -> str:
    """Get database path"""
    return self._config["database_path"]

  def is_dev_mode(self) -> bool:
    """Check if running in development mode"""
    return self._config.get("dev_mode", False)
