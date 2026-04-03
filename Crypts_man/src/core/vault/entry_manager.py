# src/core/vault/entry_manager.py
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from src.core.vault.encryption_service import EncryptionService
from src.core.events import events, EventType

logger = logging.getLogger(__name__)


class EntryManager:
  """Main CRUD operations controller for vault entries"""

  def __init__(self, db_connection, key_manager):
    """
    Initialize entry manager

    Args:
        db_connection: Database connection instance
        key_manager: Key manager with cached encryption key
    """
    self.db = db_connection
    self.key_manager = key_manager

    # Initialize encryption service
    encryption_key = key_manager.get_cached_encryption_key()
    if encryption_key is None:
      raise ValueError("Encryption key not available - user must be authenticated")

    self.encryption_service = EncryptionService(encryption_key)

    # Ensure soft delete table exists
    self._init_soft_delete_table()

  def _init_soft_delete_table(self):
    """Initialize soft delete table if not exists"""
    with self.db.cursor() as c:
      c.execute("""
                CREATE TABLE IF NOT EXISTS deleted_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id TEXT,
                    encrypted_data BLOB,
                    title TEXT,
                    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

  def create_entry(self, data: Dict[str, Any]) -> str:
    """
    Create new vault entry with encryption

    Args:
        data: Dictionary with entry fields (title, username, password, url, notes, category)

    Returns:
        Entry ID (UUID string)
    """
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Prepare payload with metadata
    payload = {
      **data,
      'id': entry_id,
      'created_at': now.isoformat(),
      'updated_at': now.isoformat(),
      'version': 2
    }

    # Encrypt the entire payload
    encrypted_blob = self.encryption_service.encrypt_entry(payload)

    # Extract title for search index (not encrypted for performance)
    title = data.get('title', '')
    username = data.get('username', '')
    url = data.get('url', '')
    tags = data.get('tags', '')
    category = data.get('category', '')

    # Store in database
    with self.db.cursor() as c:
      c.execute("""
                INSERT INTO vault_entries
                (id, encrypted_data, title, username, url, tags, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry_id, encrypted_blob, title, username, url, tags, category, now, now))

    # Publish event
    events.publish(EventType.ENTRY_ADDED, {
      'id': entry_id,
      'title': title,
      'action': 'created'
    })

    logger.info(f"Entry created: {entry_id}")
    return entry_id

  def get_entry(self, entry_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    """
    Retrieve and decrypt entry

    Args:
        entry_id: Entry identifier
        include_deleted: Include soft-deleted entries

    Returns:
        Decrypted entry dictionary or None if not found
    """
    with self.db.cursor() as c:
      c.execute(
        "SELECT encrypted_data FROM vault_entries WHERE id = ?",
        (entry_id,)
      )
      row = c.fetchone()

    if not row and include_deleted:
      # Check deleted entries table
      with self.db.cursor() as c:
        c.execute(
          "SELECT encrypted_data FROM deleted_entries WHERE original_id = ?",
          (entry_id,)
        )
        row = c.fetchone()

    if not row:
      return None

    try:
      encrypted_blob = row[0] if isinstance(row, tuple) else row['encrypted_data']
      decrypted = self.encryption_service.decrypt_entry(encrypted_blob)
      return decrypted
    except Exception as e:
      logger.error(f"Failed to decrypt entry {entry_id}: {e}")
      return None

  def get_all_entries(self, limit: int = 1000, offset: int = 0,
                      search: str = None, category: str = None) -> List[Dict[str, Any]]:
    """
    Get all entries (decrypted)

    Args:
        limit: Maximum number of entries
        offset: Pagination offset
        search: Search query
        category: Filter by category

    Returns:
        List of decrypted entries
    """
    query = "SELECT id, encrypted_data FROM vault_entries WHERE 1=1"
    params = []

    if search:
      query += " AND (title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?)"
      search_pattern = f"%{search}%"
      params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if category:
      query += " AND category = ?"
      params.append(category)

    query += " ORDER BY title LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with self.db.cursor() as c:
      c.execute(query, params)
      rows = c.fetchall()

    entries = []
    for row in rows:
      try:
        encrypted_blob = row[1] if isinstance(row, tuple) else row['encrypted_data']
        decrypted = self.encryption_service.decrypt_entry(encrypted_blob)
        entries.append(decrypted)
      except Exception as e:
        logger.error(f"Failed to decrypt entry: {e}")
        continue

    return entries

  def update_entry(self, entry_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update existing entry

    Args:
        entry_id: Entry identifier
        data: Updated entry fields

    Returns:
        Updated entry dictionary or None if not found
    """
    # Get existing entry
    existing = self.get_entry(entry_id)
    if not existing:
      logger.warning(f"Entry not found for update: {entry_id}")
      return None

    # Merge updates
    updated = {**existing, **data}
    updated['updated_at'] = datetime.utcnow().isoformat()

    # Re-encrypt
    encrypted_blob = self.encryption_service.encrypt_entry(updated)

    # Update database
    with self.db.cursor() as c:
      c.execute("""
                UPDATE vault_entries
                SET encrypted_data = ?, title = ?, username = ?, url = ?,
                    tags = ?, category = ?, updated_at = ?
                WHERE id = ?
            """, (
        encrypted_blob,
        updated.get('title', ''),
        updated.get('username', ''),
        updated.get('url', ''),
        updated.get('tags', ''),
        updated.get('category', ''),
        datetime.utcnow(),
        entry_id
      ))

    # Publish event
    events.publish(EventType.ENTRY_UPDATED, {
      'id': entry_id,
      'title': updated.get('title'),
      'action': 'updated'
    })

    logger.info(f"Entry updated: {entry_id}")
    return updated

  def delete_entry(self, entry_id: str, soft_delete: bool = True) -> bool:
    """
    Delete entry

    Args:
        entry_id: Entry identifier
        soft_delete: If True, move to deleted_entries table

    Returns:
        True if successful
    """
    # Get entry before deletion
    entry = self.get_entry(entry_id)
    if not entry:
      return False

    with self.db.transaction() as c:
      if soft_delete:
        # Move to deleted_entries table
        # Get encrypted data first
        c.execute("SELECT encrypted_data, title FROM vault_entries WHERE id = ?", (entry_id,))
        row = c.fetchone()

        if row:
          expires_at = datetime.utcnow()  # Can set expiration for auto-cleanup
          c.execute("""
                        INSERT INTO deleted_entries (original_id, encrypted_data, title, expires_at)
                        VALUES (?, ?, ?, ?)
                    """, (entry_id, row[0], row[1], expires_at))

      # Delete from main table
      c.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))

      # Delete audit logs
      c.execute("DELETE FROM audit_log WHERE entry_id = ?", (entry_id,))

    # Publish event
    events.publish(EventType.ENTRY_DELETED, {
      'id': entry_id,
      'title': entry.get('title'),
      'action': 'deleted',
      'soft': soft_delete
    })

    logger.info(f"Entry deleted: {entry_id} (soft={soft_delete})")
    return True

  def restore_entry(self, entry_id: str) -> Optional[str]:
    """
    Restore a soft-deleted entry

    Args:
        entry_id: Original entry ID

    Returns:
        New entry ID if restored
    """
    with self.db.cursor() as c:
      c.execute(
        "SELECT encrypted_data, title FROM deleted_entries WHERE original_id = ?",
        (entry_id,)
      )
      row = c.fetchone()

    if not row:
      return None

    try:
      # Decrypt to verify integrity
      encrypted_blob = row[0]
      decrypted = self.encryption_service.decrypt_entry(encrypted_blob)

      # Create new entry
      new_id = self.create_entry(decrypted)

      # Remove from deleted table
      with self.db.cursor() as c:
        c.execute("DELETE FROM deleted_entries WHERE original_id = ?", (entry_id,))

      logger.info(f"Entry restored: {entry_id} -> {new_id}")
      return new_id
    except Exception as e:
      logger.error(f"Failed to restore entry {entry_id}: {e}")
      return None

  def get_entry_count(self, include_deleted: bool = False) -> int:
    """Get total number of entries"""
    with self.db.cursor() as c:
      if include_deleted:
        c.execute("SELECT COUNT(*) FROM vault_entries")
      else:
        c.execute("SELECT COUNT(*) FROM vault_entries")
      return c.fetchone()[0]

  def search_entries(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search entries with fuzzy matching

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching entries
    """
    # Use full-text search on indexed fields
    with self.db.cursor() as c:
      c.execute("""
                SELECT id, encrypted_data
                FROM vault_entries
                WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR notes LIKE ? OR tags LIKE ?
                ORDER BY
                    CASE
                        WHEN title = ? THEN 1
                        WHEN title LIKE ? THEN 2
                        ELSE 3
                    END
                LIMIT ?
            """, (
        f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
        query, f"{query}%", limit
      ))
      rows = c.fetchall()

    entries = []
    for row in rows:
      try:
        encrypted_blob = row[1] if isinstance(row, tuple) else row['encrypted_data']
        decrypted = self.encryption_service.decrypt_entry(encrypted_blob)
        entries.append(decrypted)
      except Exception:
        continue

    return entries
