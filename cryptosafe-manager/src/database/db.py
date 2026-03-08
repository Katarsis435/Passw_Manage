# src/database/db.py
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


class Database:
  """Thread-safe database helper with migration support"""

  def __init__(self, db_path: str):
    self.db_path = db_path
    self._local = threading.local()
    self._init_database()

  def _get_connection(self):
    """Get thread-local connection"""
    if not hasattr(self._local, 'connection'):
      self._local.connection = sqlite3.connect(
        self.db_path,
        check_same_thread=False,
        timeout=10
      )
      self._local.connection.row_factory = sqlite3.Row
    return self._local.connection

  @contextmanager
  def cursor(self):
    """Get database cursor with context manager"""
    conn = self._get_connection()
    cursor = conn.cursor()
    try:
      yield cursor
      conn.commit()
    except Exception:
      conn.rollback()
      raise
    finally:
      cursor.close()

  def _init_database(self):
    """Initialize database schema"""
    with self.cursor() as c:
      # Check current version
      c.execute("PRAGMA user_version")
      version = c.fetchone()[0]

      if version == 0:
        # Create tables
        c.execute("""
                    CREATE TABLE vault_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        username TEXT,
                        encrypted_password BLOB,
                        url TEXT,
                        notes TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

        c.execute("""
                    CREATE TABLE audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        entry_id INTEGER,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        signature TEXT
                    )
                """)

        c.execute("""
                    CREATE TABLE settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT,
                        encrypted BOOLEAN DEFAULT 0
                    )
                """)

        c.execute("""
                    CREATE TABLE key_store (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_type TEXT NOT NULL,
                        salt BLOB,
                        hash BLOB,
                        params TEXT
                    )
                """)

        # Create indexes
        c.execute("CREATE INDEX idx_vault_tags ON vault_entries(tags)")
        c.execute("CREATE INDEX idx_audit_entry ON audit_log(entry_id)")
        c.execute("CREATE INDEX idx_audit_time ON audit_log(timestamp)")

        # Set version to 1
        c.execute("PRAGMA user_version = 1")

  def add_entry(self, title: str, username: str = "", password: bytes = b"",
                url: str = "", notes: str = "", tags: str = "") -> int:
    """Add a vault entry"""
    with self.cursor() as c:
      c.execute("""
                INSERT INTO vault_entries (title, username, encrypted_password, url, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, username, password, url, notes, tags))
      return c.lastrowid

  def get_entries(self) -> List[Dict[str, Any]]:
    """Get all vault entries"""
    with self.cursor() as c:
      c.execute("SELECT * FROM vault_entries ORDER BY title")
      return [dict(row) for row in c.fetchall()]

  def update_entry(self, entry_id: int, **kwargs) -> bool:
    """Update a vault entry"""
    allowed_fields = ['title', 'username', 'encrypted_password', 'url', 'notes', 'tags']
    updates = []
    values = []

    for field in allowed_fields:
      if field in kwargs:
        updates.append(f"{field} = ?")
        values.append(kwargs[field])

    if not updates:
      return False

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(entry_id)

    with self.cursor() as c:
      c.execute(f"""
                UPDATE vault_entries
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
      return c.rowcount > 0

  def delete_entry(self, entry_id: int) -> bool:
    """Delete a vault entry"""
    with self.cursor() as c:
      c.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
      return c.rowcount > 0

  def add_audit_log(self, action: str, entry_id: Optional[int] = None,
                    details: str = "", signature: str = "") -> int:
    """Add an audit log entry"""
    with self.cursor() as c:
      c.execute("""
                INSERT INTO audit_log (action, entry_id, details, signature)
                VALUES (?, ?, ?, ?)
            """, (action, entry_id, details, signature))
      return c.lastrowid

  def get_setting(self, key: str, default: Any = None) -> Any:
    """Get a setting value"""
    with self.cursor() as c:
      c.execute("SELECT setting_value FROM settings WHERE setting_key = ?", (key,))
      row = c.fetchone()
      if row:
        return json.loads(row[0])
      return default

  def set_setting(self, key: str, value: Any, encrypted: bool = False) -> None:
    """Set a setting value"""
    with self.cursor() as c:
      c.execute("""
                INSERT OR REPLACE INTO settings (setting_key, setting_value, encrypted)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), encrypted))

  def backup(self, backup_path: str) -> bool:
    """Backup database (stub for Sprint 8)"""
    # Simple file copy for now
    import shutil
    try:
      shutil.copy2(self.db_path, backup_path)
      return True
    except:
      return False

  def restore(self, backup_path: str) -> bool:
    """Restore database from backup (stub for Sprint 8)"""
    try:
      import shutil
      shutil.copy2(backup_path, self.db_path)
      return True
    except:
      return False
