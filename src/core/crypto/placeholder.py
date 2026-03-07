# src/core/crypto/placeholder.py
import os
import secrets
from typing import Optional
from .abstract import EncryptionService


class AES256Placeholder(EncryptionService):
  """Placeholder encryption service using XOR (for Sprint 1 only)"""

  def __init__(self):
    self._name = "AES256 Placeholder (XOR)"

  def encrypt(self, data: bytes, key: bytes) -> bytes:
    """
    Simple XOR encryption (placeholder - NOT secure!)
    Will be replaced with real AES-GCM in Sprint 3
    """
    if not key:
      raise ValueError("Key cannot be empty")

    # Generate a random nonce/IV (in real implementation this would be proper)
    nonce = secrets.token_bytes(16)

    # Simple XOR "encryption" - just for demonstration
    encrypted = bytearray()
    for i, byte in enumerate(data):
      encrypted.append(byte ^ key[i % len(key)])

    # Return nonce + encrypted data
    return nonce + bytes(encrypted)

  def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
    """
    Simple XOR decryption (placeholder)
    """
    if len(ciphertext) < 16:
      raise ValueError("Ciphertext too short")

    # Extract nonce and actual encrypted data
    nonce = ciphertext[:16]
    encrypted_data = ciphertext[16:]

    # Simple XOR "decryption"
    decrypted = bytearray()
    for i, byte in enumerate(encrypted_data):
      decrypted.append(byte ^ key[i % len(key)])

    return bytes(decrypted)

  def secure_zero(self, data: bytearray) -> None:
    """Securely zero out sensitive data"""
    for i in range(len(data)):
      data[i] = 0
