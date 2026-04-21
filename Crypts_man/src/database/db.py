# src/database/db.py
import sqlite3
import threading
import queue
import time
import json
import os
import uuid
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe database helper with connection pooling and async operations"""

    def __init__(self, db_path: str, max_connections: int = 5, pool_timeout: int = 30):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool_timeout = pool_timeout

        # Connection pool
        self._connection_pool = queue.Queue(maxsize=max_connections)
        self._active_connections = 0
        self._pool_lock = threading.Lock()

        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=max_connections, thread_name_prefix="DB_Worker")

        # Thread-local storage for connections
        self._local = threading.local()

        # Initialize database schema first (without using pool)
        self._init_database_schema()

        # Then initialize connection pool
        self._init_connection_pool()
        #self.migrate_to_sprint3()  #ЭТО ВАЖНО

    def _init_database_schema(self):
        """Initialize database schema using a temporary connection"""
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Use a temporary connection for schema initialization
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Check current version
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            version = cursor.fetchone()[0]

            if version == 0:
                # Create tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vault_entries (
                        id TEXT PRIMARY KEY,
                        encrypted_data BLOB,
                        title TEXT NOT NULL,
                        username TEXT,
                        url TEXT,
                        notes TEXT,
                        tags TEXT,
                        category TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        entry_id TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        signature TEXT,
                        FOREIGN KEY (entry_id) REFERENCES vault_entries(id) ON DELETE SET NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT,
                        encrypted BOOLEAN DEFAULT 0
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS key_store (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_type TEXT NOT NULL,
                        salt BLOB,
                        hash BLOB,
                        params TEXT,
                        version INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_title ON vault_entries(title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_tags ON vault_entries(tags)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault_entries(updated_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entry ON audit_log(entry_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_key_type ON key_store(key_type)")

                # Create triggers for updated_at
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_vault_entries_timestamp
                    AFTER UPDATE ON vault_entries
                    BEGIN
                        UPDATE vault_entries SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END;
                """)

                # Set version to 1
                cursor.execute("PRAGMA user_version = 1")

                conn.commit()
                logger.info("Database schema initialized successfully")

            cursor.close()
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
        finally:
            conn.close()

    def _init_connection_pool(self):
        """Initialize connection pool with connections"""
        for i in range(self.max_connections):
            try:
                conn = self._create_connection()
                self._connection_pool.put(conn)
                logger.debug(f"Connection {i + 1} added to pool")
            except Exception as e:
                logger.error(f"Error creating connection {i + 1}: {e}")

    # src/database/db.py (updated schema for Sprint 3)

    def migrate_to_sprint3(self):
        """Migrate database schema to Sprint 3 format - SAFE VERSION"""
        with self.cursor() as c:
            # Проверяем текущую схему
            c.execute("PRAGMA table_info(vault_entries)")
            columns = {row[1]: row[2] for row in c.fetchall()}  # {name: type}

            # 1. Добавляем encrypted_data, если нет
            if 'encrypted_data' not in columns:
                c.execute("ALTER TABLE vault_entries ADD COLUMN encrypted_data BLOB")
                print("✓ Added encrypted_data column")

            # 2. Добавляем category/tags, если нет
            if 'category' not in columns:
                c.execute("ALTER TABLE vault_entries ADD COLUMN category TEXT")
            if 'tags' not in columns:
                c.execute("ALTER TABLE vault_entries ADD COLUMN tags TEXT")

            # 3. ⚠️ ВАЖНО: Если id INTEGER, а нужно TEXT для UUID — миграция данных
            if columns.get('id') == 'INTEGER':
                self._safe_migrate_id_to_text(c)

            # 4. Создаём индексы (без ошибок, если уже есть)
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_vault_category ON vault_entries(category)",
                "CREATE INDEX IF NOT EXISTS idx_vault_tags ON vault_entries(tags)",
                "CREATE INDEX IF NOT EXISTS idx_vault_username ON vault_entries(username)",
                "CREATE INDEX IF NOT EXISTS idx_vault_updated ON vault_entries(updated_at)",
            ]
            for idx_sql in indexes:
                try:
                    c.execute(idx_sql)
                except sqlite3.OperationalError:
                    pass  # Index already exists

            # 5. Таблица для soft delete
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

    def _safe_migrate_id_to_text(self, cursor):
        """Безопасная миграция id INTEGER → TEXT с сохранением данных"""
        print("⚠ Migrating id from INTEGER to TEXT...")

        # Проверяем, есть ли данные
        cursor.execute("SELECT COUNT(*) FROM vault_entries")
        count = cursor.fetchone()[0]

        if count == 0:
            # Пустая таблица — просто пересоздаём
            cursor.execute("DROP TABLE vault_entries")
            cursor.execute("""
                CREATE TABLE vault_entries (
                    id TEXT PRIMARY KEY,
                    encrypted_data BLOB,
                    title TEXT NOT NULL,
                    username TEXT,
                    url TEXT,
                    tags TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            return

        # Есть данные — создаём временную таблицу
        cursor.execute("""
            CREATE TABLE vault_entries_temp (
                id TEXT PRIMARY KEY,
                encrypted_data BLOB,
                title TEXT NOT NULL,
                username TEXT,
                url TEXT,
                tags TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Копируем данные, конвертируя id в TEXT
        cursor.execute("""
            INSERT INTO vault_entries_temp (id, title, username, url, tags, category, created_at, updated_at)
            SELECT CAST(id AS TEXT), title, username, url,
                   COALESCE(tags, ''), COALESCE(category, ''),
                   COALESCE(created_at, CURRENT_TIMESTAMP),
                   COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM vault_entries
        """)

        # Заменяем таблицу
        cursor.execute("DROP TABLE vault_entries")
        cursor.execute("ALTER TABLE vault_entries_temp RENAME TO vault_entries")
        print(f"✓ Migrated {count} entries to TEXT id")

    def _migrate_id_to_text(self, cursor):
        """Миграция id INTEGER → TEXT с сохранением ВСЕХ колонок"""
        print("⚠ Migrating id from INTEGER to TEXT...")

        # Создаём новую таблицу со ВСЕМИ колонками из Sprint 1+2+3
        cursor.execute("""
            CREATE TABLE vault_entries_new (
                id TEXT PRIMARY KEY,
                encrypted_data BLOB,
                title TEXT NOT NULL,
                username TEXT,
                url TEXT,
                notes TEXT,
                tags TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Копируем данные (с учётом старых колонок)
        cursor.execute("""
            INSERT INTO vault_entries_new
            (id, title, username, url, notes, tags, category, created_at, updated_at)
            SELECT
                CAST(id AS TEXT),
                title,
                username,
                url,
                COALESCE(notes, ''),
                COALESCE(tags, ''),
                COALESCE(category, ''),
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM vault_entries
        """)

        # Заменяем таблицу
        cursor.execute("DROP TABLE vault_entries")
        cursor.execute("ALTER TABLE vault_entries_new RENAME TO vault_entries")
        print("✓ Migration completed with all columns")







    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=self.pool_timeout,
            isolation_level=None  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row

        # Enable foreign keys and WAL mode for better concurrency
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -2000")  # 2MB cache

        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool"""
        try:
            # Check if thread already has a connection
            if hasattr(self._local, 'connection'):
                return self._local.connection

            # Get connection from pool with timeout
            try:
                conn = self._connection_pool.get(timeout=self.pool_timeout)
                self._local.connection = conn
                return conn
            except queue.Empty:
                # If pool is empty, create a temporary connection
                logger.warning("Connection pool empty, creating temporary connection")
                conn = self._create_connection()
                self._local.connection = conn
                return conn

        except Exception as e:
            logger.error(f"Error getting connection: {e}")
            # Fallback: create a new connection
            conn = self._create_connection()
            self._local.connection = conn
            return conn

    def _return_connection(self):
        """Return connection to the pool"""
        if hasattr(self._local, 'connection'):
            conn = self._local.connection
            try:
                # Rollback any pending transaction
                conn.rollback()
                # Try to return to pool
                try:
                    self._connection_pool.put_nowait(conn)
                except queue.Full:
                    # If pool is full, close the connection
                    logger.debug("Connection pool full, closing connection")
                    conn.close()
            except:
                # If anything fails, close the connection
                try:
                    conn.close()
                except:
                    pass
            finally:
                delattr(self._local, 'connection')

    @contextmanager
    def cursor(self):
        """Get database cursor with context manager"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            self._return_connection()

    @contextmanager
    def transaction(self):
        """Context manager for explicit transactions"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Transaction error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            self._return_connection()

    def execute_async(self, func: Callable, *args, **kwargs) -> Future:
        """Execute a database function asynchronously"""
        return self._executor.submit(func, *args, **kwargs)

    def execute_many_async(self, funcs: List[Callable]) -> List[Future]:
        """Execute multiple database functions asynchronously"""
        return [self._executor.submit(func) for func in funcs]

    def add_entry(self, title: str, username: str = "", password: bytes = b"",
                  url: str = "", notes: str = "", tags: str = "") -> str:
        """Add a vault entry - password param goes into encrypted_data column"""
        entry_id = str(uuid.uuid4())
        with self.cursor() as c:
            c.execute("""
                INSERT INTO vault_entries (id, title, username, encrypted_data, url, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (entry_id, title, username, password, url, notes, tags))  # password → encrypted_data
            return entry_id






    def add_entry_async(self, title: str, username: str = "", password: bytes = b"",
                        url: str = "", notes: str = "", tags: str = "") -> Future:
        """Add a vault entry asynchronously"""
        return self.execute_async(self.add_entry, title, username, password, url, notes, tags)

    def get_entries(self, limit: int = 100, offset: int = 0,
                    search: str = None, tags: str = None) -> List[Dict[str, Any]]:
        """Get all vault entries with pagination and filtering"""
        with self.cursor() as c:
            query = "SELECT * FROM vault_entries"
            params = []

            if search or tags:
                query += " WHERE 1=1"
                if search:
                    query += " AND (title LIKE ? OR username LIKE ? OR url LIKE ? OR notes LIKE ?)"
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
                if tags:
                    query += " AND tags LIKE ?"
                    params.append(f"%{tags}%")

            query += " ORDER BY title LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]

    def get_entries_async(self, limit: int = 100, offset: int = 0,
                          search: str = None, tags: str = None) -> Future:
        """Get vault entries asynchronously"""
        return self.execute_async(self.get_entries, limit, offset, search, tags)

    def get_entry_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a single entry by ID"""
        with self.cursor() as c:
            c.execute("SELECT * FROM vault_entries WHERE id = ?", (entry_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_entry_by_id_async(self, entry_id: str) -> Future:
        """Get a single entry asynchronously"""
        return self.execute_async(self.get_entry_by_id, entry_id)

    def update_entry(self, entry_id: str, **kwargs) -> bool:
        """Update a vault entry"""
        allowed_fields = ['title', 'username', 'encrypted_data', 'url', 'notes', 'tags']
        updates = []
        values = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])

        if not updates:
            return False

        values.append(entry_id)

        with self.cursor() as c:
            c.execute(f"""
                UPDATE vault_entries
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            return c.rowcount > 0

    def update_entry_async(self, entry_id: str, **kwargs) -> Future:
        """Update a vault entry asynchronously"""
        return self.execute_async(self.update_entry, entry_id, **kwargs)

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a vault entry"""
        with self.transaction() as c:
            # Delete audit logs referencing this entry first
            c.execute("DELETE FROM audit_log WHERE entry_id = ?", (entry_id,))
            # Delete the entry
            c.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))
            return c.rowcount > 0

    def delete_entry_async(self, entry_id: str) -> Future:
        """Delete a vault entry asynchronously"""
        return self.execute_async(self.delete_entry, entry_id)

    def delete_entries_batch(self, entry_ids: List[int]) -> int:
        """Delete multiple entries in a transaction"""
        if not entry_ids:
            return 0

        with self.transaction() as c:
            placeholders = ','.join(['?'] * len(entry_ids))
            # Delete audit logs
            c.execute(f"DELETE FROM audit_log WHERE entry_id IN ({placeholders})", entry_ids)
            # Delete entries
            c.execute(f"DELETE FROM vault_entries WHERE id IN ({placeholders})", entry_ids)
            return c.rowcount

    def delete_entries_batch_async(self, entry_ids: List[int]) -> Future:
        """Delete multiple entries asynchronously"""
        return self.execute_async(self.delete_entries_batch, entry_ids)

    def add_audit_log(self, action: str, entry_id: Optional[str] = None,
                      details: str = "", signature: str = "") -> int:
        """Add an audit log entry"""
        with self.cursor() as c:
            c.execute("""
                INSERT INTO audit_log (action, entry_id, details, signature)
                VALUES (?, ?, ?, ?)
            """, (action, entry_id, details, signature))
            return c.lastrowid

    def add_audit_log_async(self, action: str, entry_id: Optional[str] = None,
                            details: str = "", signature: str = "") -> Future:
        """Add an audit log entry asynchronously"""
        return self.execute_async(self.add_audit_log, action, entry_id, details, signature)

    def get_audit_logs(self, limit: int = 100, offset: int = 0,
                       entry_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit logs with pagination"""
        with self.cursor() as c:
            if entry_id:
                c.execute("""
                    SELECT * FROM audit_log
                    WHERE entry_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (entry_id, limit, offset))
            else:
                c.execute("""
                    SELECT * FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            return [dict(row) for row in c.fetchall()]

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

    def set_setting_async(self, key: str, value: Any, encrypted: bool = False) -> Future:
        """Set a setting value asynchronously"""
        return self.execute_async(self.set_setting, key, value, encrypted)

    def get_settings_batch(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple settings at once"""
        if not keys:
            return {}

        with self.cursor() as c:
            placeholders = ','.join(['?'] * len(keys))
            c.execute(f"SELECT setting_key, setting_value FROM settings WHERE setting_key IN ({placeholders})", keys)
            return {row[0]: json.loads(row[1]) for row in c.fetchall()}

    def store_key(self, key_type: str, salt: bytes = None, hash_data: bytes = None, params: str = "") -> int:
        """Store a key in the key store"""
        with self.cursor() as c:
            c.execute("""
                INSERT INTO key_store (key_type, salt, hash, params)
                VALUES (?, ?, ?, ?)
            """, (key_type, salt, hash_data, params))
            return c.lastrowid

    def get_key(self, key_type: str) -> Optional[Dict[str, Any]]:
        """Get a key from the key store"""
        with self.cursor() as c:
            c.execute("SELECT * FROM key_store WHERE key_type = ? ORDER BY id DESC LIMIT 1", (key_type,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_auth_hash(self) -> Optional[Dict[str, Any]]:
        """Get stored authentication hash"""
        return self.get_key('auth_hash')

    def get_encryption_salt(self) -> Optional[Dict[str, Any]]:
        """Get stored encryption salt"""
        return self.get_key('enc_salt')

    def get_key_params(self) -> Optional[Dict[str, Any]]:
        """Get key derivation parameters"""
        key_data = self.get_key('params')
        if key_data and key_data.get('params'):
            return json.loads(key_data['params'])
        return None

    def store_auth_hash(self, hash_data: str, params: Dict[str, Any]) -> int:
        """Store authentication hash"""
        return self.store_key('auth_hash', None, hash_data.encode(), json.dumps(params))

    def store_encryption_salt(self, salt: bytes) -> int:
        """Store encryption salt"""
        return self.store_key('enc_salt', salt, None, '')

    def store_key_params(self, params: Dict[str, Any]) -> int:
        """Store key derivation parameters"""
        return self.store_key('params', None, None, json.dumps(params))

    def backup(self, backup_path: str) -> bool:
        """Backup database to file"""
        try:
            # Ensure all connections are returned to pool
            self._return_connection()

            # Create backup using SQLite backup API
            source = sqlite3.connect(self.db_path)
            dest = sqlite3.connect(backup_path)
            source.backup(dest)
            source.close()
            dest.close()

            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def backup_async(self, backup_path: str) -> Future:
        """Backup database asynchronously"""
        return self.execute_async(self.backup, backup_path)

    def restore(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Close all connections
            self.close()

            # Restore backup
            import shutil
            shutil.copy2(backup_path, self.db_path)

            # Reinitialize connections
            self._init_connection_pool()

            logger.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def restore_async(self, backup_path: str) -> Future:
        """Restore database asynchronously"""
        return self.execute_async(self.restore, backup_path)

    def vacuum(self) -> bool:
        """Vacuum database to reclaim space"""
        try:
            with self.cursor() as c:
                c.execute("VACUUM")
            logger.info("Database vacuum completed")
            return True
        except Exception as e:
            logger.error(f"Vacuum failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        with self.cursor() as c:
            # Entry count
            c.execute("SELECT COUNT(*) FROM vault_entries")
            stats['entries_count'] = c.fetchone()[0]

            # Audit log count
            c.execute("SELECT COUNT(*) FROM audit_log")
            stats['audit_logs_count'] = c.fetchone()[0]

            # Database size
            c.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            stats['database_size_bytes'] = c.fetchone()[0]

            # Pool stats
            stats['pool_size'] = self.max_connections
            stats['pool_available'] = self._connection_pool.qsize()

        return stats

    def close(self):
        """Close all database connections and shutdown executor"""
        logger.info("Closing database connections...")

        # Shutdown thread pool
        self._executor.shutdown(wait=True)

        # Close all connections in pool
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except:
                pass

        # Clear thread local
        if hasattr(self._local, 'connection'):
            try:
                self._local.connection.close()
            except:
                pass
            delattr(self._local, 'connection')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
