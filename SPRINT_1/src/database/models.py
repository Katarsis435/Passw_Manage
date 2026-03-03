import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class VaultEntry:
    id: Optional[int] = None
    title: str = ''
    username: str = ''
    encrypted_password: bytes = b''
    url: str = ''
    notes: str = ''
    tags: str = ''
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class AuditLog:
    id: Optional[int] = None
    action: str = ''
    timestamp: Optional[str] = None
    entry_id: Optional[int] = None
    details: str = ''
    signature: str = ''  # Заглушка для спринта 5

@dataclass
class Setting:
    id: Optional[int] = None
    setting_key: str = ''
    setting_value: str = ''
    encrypted: bool = False

@dataclass
class KeyStore:
    id: Optional[int] = None
    key_type: str = ''
    salt: bytes = b''
    hash: bytes = b''
    params: str = ''
