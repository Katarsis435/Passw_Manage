# Crypts_man/src/core/audit/log_signer.py
import hashlib
import hmac
import secrets
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

import logging

logger = logging.getLogger(__name__)


class AuditLogSigner:
    """Cryptographic signing and verification for audit logs"""

    # Algorithm preference: Ed25519 first, HMAC-SHA256 fallback
    ALGORITHM_ED25519 = "Ed25519"
    ALGORITHM_HMAC = "HMAC-SHA256"

    def __init__(self, key_manager, config=None):
        """
        Initialize signer with key derivation from master password

        Args:
            key_manager: Key manager for key derivation
            config: Configuration manager
        """
        self.key_manager = key_manager
        self.config = config
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._public_key: Optional[ed25519.Ed25519PublicKey] = None
        self._hmac_key: Optional[bytes] = None
        self._algorithm = self.ALGORITHM_ED25519

        self._init_signing_key()

    def _init_signing_key(self):
        """Initialize signing key from master password"""
        try:
            # Try to use Ed25519
            self._private_key = self._derive_ed25519_key()
            self._public_key = self._private_key.public_key()
            self._algorithm = self.ALGORITHM_ED25519
            logger.info("Audit signing initialized with Ed25519")
        except Exception as e:
            logger.warning(f"Ed25519 initialization failed: {e}, falling back to HMAC-SHA256")
            self._init_hmac_key()
            self._algorithm = self.ALGORITHM_HMAC

    def _derive_ed25519_key(self) -> ed25519.Ed25519PrivateKey:
        """Derive Ed25519 key from master password using HKDF"""
        # Get key material from master password with audit context
        key_material = self._derive_key_material(purpose="audit-signing", length=32)

        # Create Ed25519 private key from seed
        return ed25519.Ed25519PrivateKey.from_private_bytes(key_material)

    def _init_hmac_key(self):
        """Initialize HMAC-SHA256 key as fallback"""
        self._hmac_key = self._derive_key_material(purpose="audit-hmac", length=32)

    def _derive_key_material(self, purpose: str, length: int) -> bytes:
        """
        Derive key material using HKDF from master password
        """
        encryption_key = None
        if self.key_manager:
            encryption_key = self.key_manager.get_cached_encryption_key()

        # If no encryption key available, generate a temporary one for testing
        if encryption_key is None:
            import secrets
            print(f"⚠ No encryption key available, using temporary key for {purpose}")
            encryption_key = secrets.token_bytes(32)

        # Use HKDF to derive a separate key for audit signing
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=None,
            info=f"cryptosafe-{purpose}".encode()
        )
        return hkdf.derive(encryption_key)


    def sign(self, data: bytes) -> bytes:
        """
        Sign data with current signing key

        Args:
            data: Data to sign

        Returns:
            Signature bytes
        """
        if self._algorithm == self.ALGORITHM_ED25519 and self._private_key:
            return self._private_key.sign(data)
        elif self._hmac_key:
            return hmac.new(self._hmac_key, data, hashlib.sha256).digest()
        else:
            raise RuntimeError("No signing key available")

    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        Verify signature

        Args:
            data: Original data
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        if self._algorithm == self.ALGORITHM_ED25519 and self._public_key:
            try:
                self._public_key.verify(signature, data)
                return True
            except InvalidSignature:
                return False
        elif self._hmac_key:
            expected = hmac.new(self._hmac_key, data, hashlib.sha256).digest()
            return hmac.compare_digest(signature, expected)
        else:
            return False

    def get_public_key(self) -> Optional[str]:
        """Get public key in hex format for storage"""
        if self._algorithm == self.ALGORITHM_ED25519 and self._public_key:
            return self._public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ).hex()
        elif self._hmac_key:
            # For HMAC, store a key ID instead
            return hashlib.sha256(self._hmac_key).hexdigest()[:32]
        return None

    def get_algorithm(self) -> str:
        """Get the algorithm being used"""
        return self._algorithm

    def store_public_key(self, db):
        """Store public key in database for future verification"""
        public_key_hex = self.get_public_key()
        if public_key_hex:
            with db.cursor() as c:
                c.execute("""
                    INSERT INTO audit_keys (public_key, key_algorithm)
                    VALUES (?, ?)
                """, (public_key_hex, self._algorithm))

    @staticmethod
    def verify_with_public_key(data: bytes, signature: bytes, public_key_hex: str, algorithm: str) -> bool:
        """
        Verify signature using stored public key (for external verification)

        Args:
            data: Original data
            signature: Signature bytes
            public_key_hex: Public key in hex
            algorithm: Algorithm used

        Returns:
            True if signature is valid
        """
        if algorithm == AuditLogSigner.ALGORITHM_ED25519:
            try:
                public_key_bytes = bytes.fromhex(public_key_hex)
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
                public_key.verify(signature, data)
                return True
            except Exception:
                return False
        return False
