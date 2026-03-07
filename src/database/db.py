# src/database/db.py
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Optional, List, Generator
from pathlib import Path
from datetime import datetime
from ..core.config import Config
from ..core.events import EventBus, Event, EventType
from .models import VaultEntry, AuditLog, Setting, KeyStore


class DatabaseManager:
  """Database helper with connection pooling and thread safety"""

  DATABASE_VERSION = 1  # Increment when schema changes

  def __init__(self, config: Config):
    self.config = config
    self.logger = logging.getLogger(__name__)
    self.event_bus = EventBus()
    self._local = threading.local()
    self._lock = threading.RLock()

    # Initialize database
    self._init_database()

  def _get_connection(self) -> sqlite3.Connection:
    """Get thread-local database connection"""
    if not hasattr(self._local, 'connection'):
      db_path = self.config.database_path

      # Create directory if it doesn't exist
      Path(db_path).parent.mkdir(parents=True, exist_ok=True)

      self._local.connection = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False  # We handle threading with locks
      )
      self._local.connection.row_factory = sqlite3.Row

      # Enable foreign keys
      self._local.connection.execute("PRAGMA foreign_keys = ON")

    return self._local.connection

  @contextmanager
  def transaction(self) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions"""
    conn = self._get_connection()
    with self._lock:
      try:
        yield conn
        conn.commit()
      except Exception:
        conn.rollback()
        raise

  def _init_database(self) -> None:
    """Initialize database schema"""
    with self.transaction() as conn:
      # Check current schema version
      cursor = conn.execute("PRAGMA user_version")
      version = cursor.fetchone()[0]

      if version < self.DATABASE_VERSION:
        self._create_schema(conn)
        conn.execute(f"PRAGMA user_version = {self.DATABASE_VERSION}")
        self.logger.info(f"Database initialized to version {self.DATABASE_VERSION}")

  def _create_schema(self, conn: sqlite3.Connection) -> None:
    """Create database schema"""
    # Vault entries table
    conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password BLOB NOT NULL,
                url TEXT,
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)

    # Create index on title for faster searches
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_entries_title ON vault_entries(title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_entries_tags ON vault_entries(tags)")

    # Audit log table
    conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                entry_id INTEGER,
                details TEXT,
                signature TEXT,
                FOREIGN KEY (entry_id) REFERENCES vault_entries(id) ON DELETE SET NULL
            )
        """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)")

    # Settings table
    conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                encrypted BOOLEAN DEFAULT 0
            )
        """)

    # Key store table
    conn.execute("""
            CREATE TABLE IF NOT EXISTS key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_type TEXT NOT NULL,
                salt BLOB NOT NULL,
                hash BLOB NOT NULL,
                params TEXT
            )
        """)

  # Vault entry methods
  def add_entry(self, entry: VaultEntry) -> int:
    """Add a new vault entry"""
    with self.transaction() as conn:
      cursor = conn.execute("""
                INSERT INTO vault_entries
                (title, username, encrypted_password, url, notes, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
        entry.title, entry.username, entry.encrypted_password,
        entry.url, entry.notes, entry.tags,
        entry.created_at, entry.updated_at
      ))

      entry_id = cursor.lastrowid

      # Publish event
      self.event_bus.publish(Event(EventType.ENTRY_ADDED, {
        "entry_id": entry_id,
        "title": entry.title
      }))

      # Add audit log
      self._add_audit_log(conn, "ADD", entry_id, f"Added entry: {entry.title}")

      return entry_id

  def get_entry(self, entry_id: int) -> Optional[VaultEntry]:
    """Get a vault entry by ID"""
    with self.transaction() as conn:
      cursor = conn.execute(
        "SELECT * FROM vault_entries WHERE id = ?",
        (entry_id,)
      )
      row = cursor.fetchone()

      if row:
        return VaultEntry(
          id=row['id'],
          title=row['title'],
          username=row['username'],
          encrypted_password=row['encrypted_password'],
          url=row['url'],
          notes=row['notes'],
          tags=row['tags'],
          created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
          updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
      return None

  def get_all_entries(self) -> List[VaultEntry]:
    """Get all vault entries"""
    with self.transaction() as conn:
      cursor = conn.execute(
        "SELECT * FROM vault_entries ORDER BY title"
      )
      return [VaultEntry(
        id=row['id'],
        title=row['title'],
        username=row['username'],
        encrypted_password=row['encrypted_password'],
        url=row['url'],
        notes=row['notes'],
        tags=row['tags'],
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
      ) for row in cursor.fetchall()]

  def update_entry(self, entry: VaultEntry) -> bool:
    """Update a vault entry"""
    if not entry.id:
      return False

    entry.updated_at = datetime.now()

    with self.transaction() as conn:
      conn.execute("""
                UPDATE vault_entries
                SET title = ?, username = ?, encrypted_password = ?,
                    url = ?, notes = ?, tags = ?, updated_at = ?
                WHERE id = ?
            """, (
        entry.title, entry.username, entry.encrypted_password,
        entry.url, entry.notes, entry.tags,
        entry.updated_at, entry.id
      ))

      # Publish event
      self.event_bus.publish(Event(EventType.ENTRY_UPDATED, {
        "entry_id": entry.id,
        "title": entry.title
      }))

      # Add audit log
      self._add_audit_log(conn, "UPDATE", entry.id, f"Updated entry: {entry.title}")

      return True

  def delete_entry(self, entry_id: int) -> bool:
    """Delete a vault entry"""
    with self.transaction() as conn:
      # Get entry details for audit log
      entry = self.get_entry(entry_id)

      conn.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))

      # Publish event
      self.event_bus.publish(Event(EventType.ENTRY_DELETED, {
        "entry_id": entry_id
      }))

      # Add audit log
      if entry:
        self._add_audit_log(conn, "DELETE", entry_id, f"Deleted entry: {entry.title}")

      return True

  # Audit log methods
  def _add_audit_log(self, conn: sqlite3.Connection, action: str,
                     entry_id: Optional[int], details: str) -> None:
    """Add an audit log entry (internal)"""
    conn.execute("""
            INSERT INTO audit_log (action, timestamp, entry_id, details, signature)
            VALUES (?, ?, ?, ?, ?)
        """, (action, datetime.now(), entry_id, details, ""))  # Signature placeholder

  def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
    """Get recent audit logs"""
    with self.transaction() as conn:
      cursor = conn.execute("""
                SELECT * FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

      return [AuditLog(
        id=row['id'],
        action=row['action'],
        timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
        entry_id=row['entry_id'],
        details=row['details'],
        signature=row['signature']
      ) for row in cursor.fetchall()]

  # Settings methods
  def get_setting(self, key: str, default: str = "") -> str:
    """Get a setting value"""
    with self.transaction() as conn:
      cursor = conn.execute(
        "SELECT setting_value FROM settings WHERE setting_key = ?",
        (key,)
      )
      row = cursor.fetchone()
      return row['setting_value'] if row else default

  def set_setting(self, key: str, value: str, encrypted: bool = False) -> None:
    """Set a setting value"""
    with self.transaction() as conn:
      conn.execute("""
                INSERT OR REPLACE INTO settings (setting_key, setting_value, encrypted)
                VALUES (?, ?, ?)
            """, (key, value, encrypted))

  # Key store methods
  def store_key_data(self, key_type: str, salt: bytes, hash: bytes, params: str = "") -> None:
    """Store key derivation data"""
    with self.transaction() as conn:
      conn.execute("""
                INSERT INTO key_store (key_type, salt, hash, params)
                VALUES (?, ?, ?, ?)
            """, (key_type, salt, hash, params))

  def get_key_data(self, key_type: str) -> Optional[tuple]:
    """Get key derivation data"""
    with self.transaction() as conn:
      cursor = conn.execute(
        "SELECT salt, hash, params FROM key_store WHERE key_type = ?",
        (key_type,)
      )
      row = cursor.fetchone()
      if row:
        return (row['salt'], row['hash'], row['params'])
      return None

  # Backup methods (stub for Sprint 8)
  def backup_database(self, backup_path: str) -> bool:
    """Create a database backup"""
    try:
      with self._lock:
        # Close all connections temporarily
        self.close_all_connections()

        # Copy the database file
        import shutil
        shutil.copy2(self.config.database_path, backup_path)

        # Reopen connections
        self._init_database()

        # Publish event
        self.event_bus.publish(Event(EventType.DATABASE_BACKUP, {
          "backup_path": backup_path
        }))

        return True
    except Exception as e:
      self.logger.error(f"Backup failed: {e}")
      return False

  def close_all_connections(self) -> None:
    """Close all database connections"""
    if hasattr(self._local, 'connection'):
      self._local.connection.close()
      delattr(self._local, 'connection')
