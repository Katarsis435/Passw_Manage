# src/core/config.py
import os
import json
from typing import Any, Optional
from pathlib import Path


class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        "database_path": str(Path.home() / ".cryptosafe" / "vault.db"),
        "encryption_enabled": True,
        "clipboard_timeout": 30,
        "auto_lock_minutes": 5,
        "theme": "default",
        "language": "en",
        # Argon2 parameters
        "argon2_time": 3,
        "argon2_memory": 65536,  # 64 MiB
        "argon2_parallelism": 4,
        "pbkdf2_iterations": 100000
    }

    def __init__(self, env: str = "development"):
        self.env = env
        self.config_dir = Path.home() / ".cryptosafe"
        self.config_file = self.config_dir / f"config_{env}.json"
        self._config = self._load_config()

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                loaded = json.load(f)
                return {**self.DEFAULT_CONFIG, **loaded}
        return self.DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value
        self.save()

    @property
    def database_path(self) -> str:
        """Get database path"""
        return self.get("database_path")
