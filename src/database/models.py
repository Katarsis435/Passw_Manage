# src/database/models.py
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any


class VaultEntry:
  """Model for vault entry"""

  def __init__(self, id: Optional[int] = None, title: str = "", username: str = "",
               encrypted_password: bytes = b"", url: str = "", notes: str = "",
               tags: str = "", created_at: Optional[datetime] = None,
               updated_at: Optional[datetime] = None):
    self.id = id
    self.title = title
    self.username = username
    self.encrypted_password = encrypted_password
    self.url = url
    self.notes = notes
    self.tags = tags
    self.created_at = created_at or datetime.now()
    self.updated_at = updated_at or datetime.now()

  def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary"""
    return {
      "id": self.id,
      "title": self.title,
      "username": self.username,
      "encrypted_password": self.encrypted_password,
      "url": self.url,
      "notes": self.notes,
      "tags": self.tags,
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "updated_at": self.updated_at.isoformat() if self.updated_at else None
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'VaultEntry':
    """Create from dictionary"""
    return cls(
      id=data.get("id"),
      title=data.get("title", ""),
      username=data.get("username", ""),
      encrypted_password=data.get("encrypted_password", b""),
      url=data.get("url", ""),
      notes=data.get("notes", ""),
      tags=data.get("tags", ""),
      created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
      updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
    )


class AuditLog:
  """Model for audit log entry"""

  def __init__(self, id: Optional[int] = None, action: str = "",
               timestamp: Optional[datetime] = None, entry_id: Optional[int] = None,
               details: str = "", signature: str = ""):
    self.id = id
    self.action = action
    self.timestamp = timestamp or datetime.now()
    self.entry_id = entry_id
    self.details = details
    self.signature = signature


class Setting:
  """Model for application settings"""

  def __init__(self, id: Optional[int] = None, setting_key: str = "",
               setting_value: str = "", encrypted: bool = False):
    self.id = id
    self.setting_key = setting_key
    self.setting_value = setting_value
    self.encrypted = encrypted


class KeyStore:
  """Model for key storage"""

  def __init__(self, id: Optional[int] = None, key_type: str = "",
               salt: bytes = b"", hash: bytes = b"", params: str = ""):
    self.id = id
    self.key_type = key_type
    self.salt = salt
    self.hash = hash
    self.params = params
