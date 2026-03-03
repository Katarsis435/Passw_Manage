import os
import secrets
from typing import Optional


class KeyManager:
  def __init__(self):
    self.current_key: Optional[bytes] = None

  def derive_key(self, password: str, salt: bytes) -> bytes:
    # Простая заглушка
    key = password.encode() + salt
    return key[:32]  # Обрезаем до 32 байт

  def generate_salt(self) -> bytes:
    return secrets.token_bytes(16)

  def store_key(self, key_id: str, key: bytes) -> None:
    # Заглушка для БД
    self.current_key = key

  def load_key(self, key_id: str) -> Optional[bytes]:
    return self.current_key

  def secure_wipe(self, data: bytearray) -> None:
    for i in range(len(data)):
      data[i] = 0
