import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from .models import VaultEntry, AuditLog, Setting, KeyStore
from ..core.config import Config


class Database:
  def __init__(self, db_path: Path):
    self.db_path = db_path
    self._local = threading.local()
    self._init_db()

  def _get_conn(self):
    if not hasattr(self._local, 'conn'):
      self._local.conn = sqlite3.connect(self.db_path)
      self._local.conn.row_factory = sqlite3.Row
    return self._local.conn

  @contextmanager
  def transaction(self):
    conn = self._get_conn()
    try:
      yield conn
      conn.commit()
    except:
      conn.rollback()
      raise

  def _init_db(self):
    with self.transaction() as conn:
      # Версия схемы
      conn.execute('PRAGMA user_version = 1')

      # vault_entries
      conn.execute('''
                CREATE TABLE IF NOT EXISTS vault_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    username TEXT,
                    encrypted_password BLOB,
                    url TEXT,
                    notes TEXT,
                    tags TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
      conn.execute('CREATE INDEX IF NOT EXISTS idx_title ON vault_entries(title)')

      # audit_log
      conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP,
                    entry_id INTEGER,
                    details TEXT,
                    signature TEXT
                )
            ''')

      # settings
      conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    encrypted INTEGER DEFAULT 0
                )
            ''')

      # key_store
      conn.execute('''
                CREATE TABLE IF NOT EXISTS key_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_type TEXT NOT NULL,
                    salt BLOB,
                    hash BLOB,
                    params TEXT
                )
            ''')

  def backup(self, backup_path: Path):
    # Заглушка для спринта 8
    with self._get_conn() as conn:
      backup_conn = sqlite3.connect(backup_path)
      conn.backup(backup_conn)
      backup_conn.close()

  def restore(self, backup_path: Path):
    # Заглушка для спринта 8
    pass

  # CRUD для записей
  def add_entry(self, entry: VaultEntry) -> int:
    with self.transaction() as conn:
      now = datetime.now().isoformat()
      cursor = conn.execute('''
                INSERT INTO vault_entries
                (title, username, encrypted_password, url, notes, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (entry.title, entry.username, entry.encrypted_password,
                  entry.url, entry.notes, entry.tags, now, now))
      return cursor.lastrowid

  def get_entries(self) -> List[VaultEntry]:
    with self.transaction() as conn:
      cursor = conn.execute('SELECT * FROM vault_entries ORDER BY title')
      return [dict(row) for row in cursor.fetchall()]

  def update_entry(self, entry_id: int, entry: VaultEntry):
    with self.transaction() as conn:
      now = datetime.now().isoformat()
      conn.execute('''
                UPDATE vault_entries SET
                    title=?, username=?, encrypted_password=?, url=?,
                    notes=?, tags=?, updated_at=?
                WHERE id=?
            ''', (entry.title, entry.username, entry.encrypted_password,
                  entry.url, entry.notes, entry.tags, now, entry_id))

  def delete_entry(self, entry_id: int):
    with self.transaction() as conn:
      conn.execute('DELETE FROM vault_entries WHERE id=?', (entry_id,))

  # Настройки
  def get_setting(self, key: str, default=None):
    with self.transaction() as conn:
      cursor = conn.execute(
        'SELECT setting_value FROM settings WHERE setting_key=?',
        (key,)
      )
      row = cursor.fetchone()
      return row['setting_value'] if row else default

  def set_setting(self, key: str, value: str, encrypted: bool = False):
    with self.transaction() as conn:
      conn.execute('''
                INSERT OR REPLACE INTO settings (setting_key, setting_value, encrypted)
                VALUES (?, ?, ?)
            ''', (key, value, 1 if encrypted else 0))
