# src/core/authentication.py
from typing import Optional, Dict, Any
from datetime import datetime
import time
import logging
from src.core.key_manager import KeyManager
from src.core.events import events, EventType

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages user authentication and session"""

    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self._failed_attempts = 0
        self._last_failed_time = 0
        self._login_time: Optional[datetime] = None
        self._last_activity: datetime = datetime.now()
        self._authenticated = False
        self._encryption_key: Optional[bytes] = None

    def get_delay(self) -> float:
        """Calculate exponential backoff delay"""
        if self._failed_attempts <= 2:
            return 1.0
        elif self._failed_attempts <= 4:
            return 5.0
        else:
            return 30.0

    def should_delay(self) -> bool:
        """Check if delay is still active"""
        if self._failed_attempts == 0:
            return False

        delay = self.get_delay()
        elapsed = time.time() - self._last_failed_time
        return elapsed < delay

    def authenticate(self, password: str, stored_hash: str,
                     salt: bytes) -> Optional[bytes]:
        """Authenticate user and return encryption key if successful"""
        # Check exponential backoff
        if self.should_delay():
            remaining = self.get_delay() - (time.time() - self._last_failed_time)
            logger.warning(f"Authentication delayed: {remaining:.1f}s remaining")
            return None

        # Verify password
        if not self.key_manager.verify_password(password, stored_hash):
            self._failed_attempts += 1
            self._last_failed_time = time.time()
            logger.warning(f"Failed login attempt #{self._failed_attempts}")
            return None

        # Success - reset failed attempts
        self._failed_attempts = 0
        self._last_failed_time = 0

        # Derive encryption key
        encryption_key = self.key_manager.derive_encryption_key(password, salt)
        self._encryption_key = encryption_key

        # Cache the key
        self.key_manager.cache_encryption_key(encryption_key)

        # Update session
        self._login_time = datetime.now()
        self._last_activity = datetime.now()
        self._authenticated = True

        # Publish event
        events.publish(EventType.USER_LOGGED_IN, {"timestamp": self._login_time})

        return encryption_key

    def logout(self) -> None:
        """Log out user and clear cached keys"""
        self.key_manager.clear_cache()
        self._encryption_key = None
        self._authenticated = False
        self._login_time = None
        events.publish(EventType.USER_LOGGED_OUT)

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self._last_activity = datetime.now()
        if self._authenticated:
            self.key_manager.update_activity()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self._authenticated

    def get_encryption_key(self) -> Optional[bytes]:
        """Get current encryption key"""
        return self._encryption_key

    def get_inactive_seconds(self) -> float:
        """Get seconds since last activity"""
        return (datetime.now() - self._last_activity).total_seconds()

    def should_auto_lock(self, timeout_minutes: int) -> bool:
        """Check if auto-lock should trigger"""
        if not self._authenticated:
            return False
        return self.get_inactive_seconds() > (timeout_minutes * 60)

    def get_failed_attempts(self) -> int:
        """Get number of failed attempts"""
        return self._failed_attempts

    def reset_failed_attempts(self) -> None:
        """Reset failed attempts counter"""
        self._failed_attempts = 0
        self._last_failed_time = 0
