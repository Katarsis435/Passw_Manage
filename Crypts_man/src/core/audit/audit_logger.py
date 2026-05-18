# Crypts_man/src/core/audit/audit_logger.py
import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEventType(Enum):
    # Authentication
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_PASSWORD_CHANGE = "auth.password.change"
    # Vault operations
    VAULT_ENTRY_CREATE = "vault.entry.create"
    VAULT_ENTRY_READ = "vault.entry.read"
    VAULT_ENTRY_UPDATE = "vault.entry.update"
    VAULT_ENTRY_DELETE = "vault.entry.delete"
    VAULT_SEARCH = "vault.search"
    # Clipboard operations
    CLIPBOARD_COPY = "clipboard.copy"
    CLIPBOARD_CLEAR = "clipboard.clear"
    CLIPBOARD_AUTO_CLEAR = "clipboard.auto_clear"
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_LOCK = "system.lock"
    SYSTEM_UNLOCK = "system.unlock"
    # Security events
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious"
    SECURITY_TAMPER_DETECTED = "security.tamper_detected"
    SECURITY_EXTERNAL_ACCESS = "security.external_access"
    # Config changes
    CONFIG_CHANGE = "config.change"


@dataclass
class AuditEntry:
    """Structured audit log entry"""
    timestamp: str
    event_type: str
    severity: str
    user_id: str
    source: str
    details: Dict[str, Any]
    sequence_number: int
    previous_hash: str
    entry_id: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'severity': self.severity,
            'user_id': self.user_id,
            'source': self.source,
            'details': self.details,
            'sequence_number': self.sequence_number,
            'previous_hash': self.previous_hash,
            'entry_id': self.entry_id
        }


    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the entry"""
        return hashlib.sha256(self.to_json().encode()).hexdigest()


class AuditLogger:
    """Main audit logging controller with integrity protection"""


    def __init__(self, db_connection, signer, config):
        """
        Initialize audit logger

        Args:
            db_connection: Database connection instance
            signer: LogSigner instance for cryptographic signing
            config: Configuration manager
        """
        self.db = db_connection
        self.signer = signer
        self.config = config
        self._event_callbacks = {}
        self._init_log_structure()


    def _init_log_structure(self):
        """Initialize audit log tables and create genesis entry if empty"""
        self._create_tables()
        with self.db.cursor() as c:
            c.execute("SELECT COUNT(*) FROM audit_log")
            count = c.fetchone()[0]
        if count == 0:
            self._create_genesis_entry()


    def _create_tables(self):
        """Create audit log tables with proper schema"""
        with self.db.cursor() as c:
            # Check if old audit_log table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
            table_exists = c.fetchone()
            if table_exists:
                # Check if table has the new structure (sequence_number column)
                c.execute("PRAGMA table_info(audit_log)")
                columns = [row[1] for row in c.fetchall()]
                # If old table structure (missing sequence_number), drop and recreate
                if 'sequence_number' not in columns:
                    print("⚠ Old audit_log structure detected, recreating table...")
                    # Backup old data if needed (optional)
                    c.execute("DROP TABLE IF EXISTS audit_log")
                    c.execute("DROP TABLE IF EXISTS audit_keys")
                    c.execute("DROP TABLE IF EXISTS audit_integrity_checks")
                    table_exists = False
            if not table_exists:
                # Create fresh table with correct schema
                c.execute("""
                          CREATE TABLE audit_log (
                              sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
                              previous_hash TEXT NOT NULL,
                              entry_data BLOB NOT NULL,
                              entry_hash TEXT NOT NULL,
                              signature TEXT NOT NULL,
                              timestamp TEXT NOT NULL,
                              event_type TEXT,
                              severity TEXT,
                              user_id TEXT,
                              source TEXT,
                              entry_id TEXT
                          )
                      """)
                print("✓ Created audit_log table with correct schema")
                # Create indexes
                c.execute("CREATE INDEX idx_audit_timestamp ON audit_log(timestamp)")
                c.execute("CREATE INDEX idx_audit_event_type ON audit_log(event_type)")
                c.execute("CREATE INDEX idx_audit_sequence ON audit_log(sequence_number)")
                c.execute("CREATE INDEX idx_audit_user ON audit_log(user_id)")
                c.execute("CREATE INDEX idx_audit_entry ON audit_log(entry_id)")
            # Public key storage
            c.execute("""
                    CREATE TABLE IF NOT EXISTS audit_keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        public_key TEXT NOT NULL,
                        key_algorithm TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
            # Integrity check results
            c.execute("""
                    CREATE TABLE IF NOT EXISTS audit_integrity_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_entries INTEGER,
                        valid_entries INTEGER,
                        tampered_entries INTEGER,
                        hash_chain_breaks INTEGER,
                        check_result TEXT,
                        details TEXT
                    )
                """)


    def _create_genesis_entry(self):
        """Create first log entry to start hash chain"""
        genesis_entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=AuditEventType.SYSTEM_STARTUP.value,
            severity=AuditSeverity.INFO.value,
            user_id="system",
            source="audit_logger",
            details={'message': 'Audit log initialized', 'version': '1.0'},
            sequence_number=0,
            previous_hash='0' * 64  # 64 zeros for SHA-256
        )
        self._write_entry(genesis_entry)
        logger.info("Genesis audit entry created")


    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        with self.db.cursor() as c:
            c.execute("SELECT MAX(sequence_number) FROM audit_log")
            result = c.fetchone()[0]
            return (result + 1) if result is not None else 0


    def _get_last_hash(self) -> str:
        """Get hash of the last entry for chain linking"""
        with self.db.cursor() as c:
            c.execute("SELECT entry_hash FROM audit_log ORDER BY sequence_number DESC LIMIT 1")
            row = c.fetchone()
            return row[0] if row else '0' * 64


    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from log details"""
        sensitive_fields = ['password', 'key', 'secret', 'token', 'master_password']
        sanitized = {}
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized


    def log_event(
        self,
        event_type: str,
        severity: str,
        source: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        entry_id: Optional[str] = None
    ) -> int:
        """
        Log an event with cryptographic integrity protection

        Returns:
            Sequence number of the created entry
        """
        # Get previous hash for chain
        previous_hash = self._get_last_hash()
        sequence_number = self._get_next_sequence()
        # Sanitize sensitive data
        sanitized_details = self._sanitize_details(details)
        # Build entry
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id or 'anonymous',
            source=source,
            details=sanitized_details,
            sequence_number=sequence_number,
            previous_hash=previous_hash,
            entry_id=entry_id
        )
        # Write to log
        seq = self._write_entry(entry)
        # Trigger callbacks
        if event_type in self._event_callbacks:
            for callback in self._event_callbacks[event_type]:
                try:
                    callback(entry)
                except Exception as e:
                    logger.error(f"Event callback failed: {e}")
        return seq


    def _write_entry(self, entry: AuditEntry) -> int:
        """Write signed entry to database"""
        # Serialize entry data
        entry_json = entry.to_json()
        entry_hash = entry.compute_hash()
        # Sign the entry
        signature = self.signer.sign(entry_json.encode())
        # Store in database
        with self.db.cursor() as c:
            c.execute("""
                INSERT INTO audit_log
                (sequence_number, previous_hash, entry_data, entry_hash, signature,
                 timestamp, event_type, severity, user_id, source, entry_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.sequence_number,
                entry.previous_hash,
                entry_json,
                entry_hash,
                signature.hex(),
                entry.timestamp,
                entry.event_type,
                entry.severity,
                entry.user_id,
                entry.source,
                entry.entry_id
            ))
        logger.debug(f"Audit entry written: seq={entry.sequence_number}, type={entry.event_type}")
        return entry.sequence_number


    def get_entries(
        self,
        start_seq: int = 0,
        end_seq: Optional[int] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query audit log entries with filters"""
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if start_seq > 0:
            query += " AND sequence_number >= ?"
            params.append(start_seq)
        if end_seq:
            query += " AND sequence_number <= ?"
            params.append(end_seq)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if start_date:
            # Ищем записи с датой >= start_date (начало дня)
            query += " AND date(timestamp) >= date(?)"
            params.append(start_date)
        if end_date:
            # Ищем записи с датой <= end_date (конец дня)
            query += " AND date(timestamp) <= date(?)"
            params.append(end_date)
        query += " ORDER BY sequence_number DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.db.cursor() as c:
            c.execute(query, params)
            rows = c.fetchall()
        entries = []
        for row in rows:
            if isinstance(row, sqlite3.Row):
                entries.append({
                    'sequence_number': row['sequence_number'],
                    'timestamp': row['timestamp'],
                    'event_type': row['event_type'],
                    'severity': row['severity'],
                    'user_id': row['user_id'],
                    'source': row['source'],
                    'entry_data': json.loads(row['entry_data']),
                    'entry_hash': row['entry_hash'],
                    'signature': row['signature'],
                    'signature_valid': None  # To be filled by verifier
                })
            else:
                entries.append({
                    'sequence_number': row[0],
                    'previous_hash': row[1],
                    'entry_data': json.loads(row[3]),
                    'entry_hash': row[4],
                    'signature': row[5],
                    'timestamp': row[6],
                    'event_type': row[7],
                    'severity': row[8],
                    'user_id': row[9],
                    'source': row[10],
                    'entry_id': row[11]
                })
        return entries


    def get_entry_count(self, **filters) -> int:
        """Get total count of entries matching filters"""
        query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
        params = []
        if filters.get('event_type'):
            query += " AND event_type = ?"
            params.append(filters['event_type'])
        if filters.get('severity'):
            query += " AND severity = ?"
            params.append(filters['severity'])
        with self.db.cursor() as c:
            c.execute(query, params)
            return c.fetchone()[0]


    def subscribe(self, event_type: str, callback):
        """Subscribe to specific event types"""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)


    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics"""
        with self.db.cursor() as c:
            c.execute("SELECT COUNT(*) FROM audit_log")
            total = c.fetchone()[0]
            c.execute("""
                SELECT event_type, COUNT(*) as count
                FROM audit_log
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            """)
            by_type = [{'event_type': row[0], 'count': row[1]} for row in c.fetchall()]
            c.execute("""
                SELECT severity, COUNT(*) as count
                FROM audit_log
                GROUP BY severity
            """)
            by_severity = [{'severity': row[0], 'count': row[1]} for row in c.fetchall()]
            c.execute("""
                SELECT date(timestamp) as date, COUNT(*) as count
                FROM audit_log
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY date(timestamp)
                ORDER BY date DESC
            """)
            by_date = [{'date': row[0], 'count': row[1]} for row in c.fetchall()]
        return {
            'total_entries': total,
            'by_event_type': by_type,
            'by_severity': by_severity,
            'by_date': by_date
        }
