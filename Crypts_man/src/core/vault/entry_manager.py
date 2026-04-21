# src/core/vault/entry_manager.py (updated with full CRUD)
import uuid
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from Crypts_man.src.core.vault.encryption_service import EncryptionService
from Crypts_man.src.core.events import events, EventType

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

        # Ensure tables exist
        self._init_tables()

    def _init_tables(self):
        """Initialize vault tables with proper schema for Sprint 3"""
        with self.db.cursor() as c:
            # Create vault_entries table with new schema
            c.execute("""
                CREATE TABLE IF NOT EXISTS vault_entries (
                    id TEXT PRIMARY KEY,
                    encrypted_data BLOB NOT NULL,
                    title TEXT NOT NULL,
                    username TEXT,
                    url TEXT,
                    tags TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create deleted_entries table for soft delete
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

            # Create indexes for performance
            c.execute("CREATE INDEX IF NOT EXISTS idx_vault_title ON vault_entries(title)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_vault_username ON vault_entries(username)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_vault_url ON vault_entries(url)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_vault_category ON vault_entries(category)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault_entries(updated_at)")

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

        # Extract fields for indexing (not encrypted for search performance)
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
        """Get entries formatted for GUI table."""
        query = """
            SELECT id, encrypted_data, title, username, url, category, tags, created_at, updated_at
            FROM vault_entries
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ? OR category LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.cursor() as c:
            c.execute(query, params)
            rows = c.fetchall()

        entries = []
        for row in rows:
            # Безопасное извлечение полей независимо от row_factory
            if isinstance(row, sqlite3.Row):
                entry_id = row['id']
                encrypted_blob = row['encrypted_data']
                title = row['title'] or ''
                username = row['username'] or ''
                url = row['url'] or ''
                category_val = row['category'] or ''
                tags_val = row['tags'] or ''
                updated_at = row['updated_at'] or ''
            else:  # tuple fallback
                entry_id = row[0]
                encrypted_blob = row[1] if len(row) > 1 else None
                title = row[2] if len(row) > 2 else ''
                username = row[3] if len(row) > 3 else ''
                url = row[4] if len(row) > 4 else ''
                category_val = row[5] if len(row) > 5 else ''
                tags_val = row[6] if len(row) > 6 else ''
                updated_at = row[8] if len(row) > 8 else ''

            # Базовая структура для таблицы (всегда возвращаем эти поля)
            table_entry = {
                'id': str(entry_id),  # Гарантируем строку для UUID
                'title': title,
                'username': username,
                'url': url,
                'category': category_val,
                'tags': tags_val,
                'updated_at': str(updated_at)[:10] if updated_at else '',  # Только дата
                'password': '',  # По умолчанию скрыт
                'notes': '',
            }

            # Расшифровка только если есть encrypted_data
            if encrypted_blob:
                try:
                    decrypted = self.encryption_service.decrypt_entry(encrypted_blob)
                    # Объединяем, приоритет у расшифрованных полей
                    table_entry.update({
                        k: v for k, v in decrypted.items()
                        if k in ['password', 'notes', 'version']
                    })
                except Exception as e:
                    logger.warning(f"Decrypt failed for {entry_id}: {e}")
                    table_entry['notes'] = '[Error]'

            entries.append(table_entry)

        return entries















    def update_entry(self, entry_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update existing entry with transaction support

        Args:
            entry_id: Entry identifier
            data: Updated entry fields

        Returns:
            Updated entry dictionary or None if not found
        """
        with self.db.transaction() as c:
            # Check if entry exists
            c.execute("SELECT encrypted_data FROM vault_entries WHERE id = ?", (entry_id,))
            row = c.fetchone()

            if not row:
                logger.warning(f"Entry not found for update: {entry_id}")
                return None

            # Get existing entry
            existing_blob = row[0] if isinstance(row, tuple) else row['encrypted_data']
            existing = self.encryption_service.decrypt_entry(existing_blob)

            # Merge updates
            updated = {**existing, **data}
            updated['updated_at'] = datetime.utcnow().isoformat()

            # Re-encrypt
            encrypted_blob = self.encryption_service.encrypt_entry(updated)

            # Update database
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
        Delete entry with transaction support

        Args:
            entry_id: Entry identifier
            soft_delete: If True, move to deleted_entries table

        Returns:
            True if successful
        """
        with self.db.transaction() as c:
            # Get entry before deletion
            c.execute("SELECT encrypted_data, title FROM vault_entries WHERE id = ?", (entry_id,))
            row = c.fetchone()

            if not row:
                return False

            if soft_delete:
                # Move to deleted_entries table
                encrypted_blob = row[0] if isinstance(row, tuple) else row['encrypted_data']
                title = row[1] if isinstance(row, tuple) else row['title']
                expires_at = datetime.utcnow()  # Can set expiration for auto-cleanup
                c.execute("""
                    INSERT INTO deleted_entries (original_id, encrypted_data, title, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (entry_id, encrypted_blob, title, expires_at))

            # Delete from main table
            c.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))

            # Delete audit logs (if exists)
            c.execute("DELETE FROM audit_log WHERE entry_id = ?", (entry_id,))

        # Publish event
        events.publish(EventType.ENTRY_DELETED, {
            'id': entry_id,
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
            encrypted_blob = row[0] if isinstance(row, tuple) else row['encrypted_data']
            decrypted = self.encryption_service.decrypt_entry(encrypted_blob)

            # Remove old ID to create new one
            if 'id' in decrypted:
                del decrypted['id']

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

    def get_entry_count(self) -> int:
        """Get total number of entries"""
        with self.db.cursor() as c:
            c.execute("SELECT COUNT(*) FROM vault_entries")
            return c.fetchone()[0]

    def search_entries(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search entries with fuzzy matching across multiple fields

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
                WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ? OR category LIKE ?
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

    def get_entries_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get entries filtered by category"""
        return self.get_all_entries(category=category)

    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get entries within date range"""
        with self.db.cursor() as c:
            c.execute("""
                SELECT id, encrypted_data FROM vault_entries
                WHERE updated_at BETWEEN ? AND ?
                ORDER BY updated_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))
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

    def delete_entries_batch(self, entry_ids: List[str], soft_delete: bool = True) -> int:
        """Delete multiple entries in a transaction"""
        deleted = 0
        for entry_id in entry_ids:
            if self.delete_entry(entry_id, soft_delete):
                deleted += 1
        return deleted
