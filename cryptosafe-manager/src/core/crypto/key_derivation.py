# SPR_2
import os
import secrets
from argon2 import PasswordHasher, Type
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyDerivation:
  def __init__(self, config):
    self.argon2_time = config.get('argon2_time', 3)
    self.argon2_memory = config.get('argon2_memory', 65536)  # 64 MiB
    self.argon2_parallelism = config.get('argon2_parallelism', 4)
    self.pbkdf2_iterations = config.get('pbkdf2_iterations', 100000)
    self.argon2_hasher = PasswordHasher(
      time_cost=self.argon2_time,
      memory_cost=self.argon2_memory,
      parallelism=self.argon2_parallelism,
      hash_len=32,
      salt_len=16,
      type=Type.ID
    )

  def create_auth_hash(self, password):
    return self.argon2_hasher.hash(password)

  def verify_auth_hash(self, password, stored_hash):
    try:
      self.argon2_hasher.verify(stored_hash, password)
      return True
    except:
      secrets.compare_digest(b'dummy', b'dummy')
      return False

  def generate_salt(self, length=16):
    return os.urandom(length)

  def derive_encryption_key(self, password, salt):
    """AES-256"""
    password_bytes = password.encode('utf-8')
    kdf = PBKDF2HMAC(
      algorithm=hashes.SHA256(),
      length=32,  # 32 bytes = 256 bits
      salt=salt,
      iterations=self.pbkdf2_iterations
    )
    return kdf.derive(password_bytes)

  def get_params(self):
    return {
      'argon2_time': self.argon2_time,
      'argon2_memory': self.argon2_memory,
      'argon2_parallelism': self.argon2_parallelism,
      'pbkdf2_iterations': self.pbkdf2_iterations
    }
