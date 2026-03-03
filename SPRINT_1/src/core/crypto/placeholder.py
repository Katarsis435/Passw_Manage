from .abstract import EncryptionService
import secrets


class AES256Placeholder(EncryptionService):
  """Временная XOR-заглушка. В спринте 3 заменится на AES-GCM"""

  def encrypt(self, data: bytes, key: bytes) -> bytes:
    # Простое XOR для демонстрации
    key = key[:len(data)] if len(key) >= len(data) else key * (len(data) // len(key) + 1)
    return bytes([a ^ b for a, b in zip(data, key)])

  def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
    # То же самое для XOR
    return self.encrypt(ciphertext, key)


class KeyManager:
  def derive_key(self, password: str, salt: bytes) -> bytes:
    # Заглушка. Вернёт 32 байта
    from hashlib import pbkdf2_hmac
    return pbkdf2_hmac('sha256', password.encode(), salt, 100000, 32)

  def store_key(self, key_id: str, key_data: bytes):
    # Заглушка для спринта 2
    pass

  def load_key(self, key_id: str) -> bytes:
    # Заглушка для спринта 2
    return b''
