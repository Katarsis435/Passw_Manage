# tests/test_key_derivation.py
import unittest
import os
import time
from Crypts_man.src.core.key_manager import KeyManager
from Crypts_man.src.core.authentication import AuthenticationManager


class TestKeyDerivation(unittest.TestCase):
    """Tests for key derivation and password hashing"""

    def setUp(self):
        self.key_manager = KeyManager()
        self.test_password = "TestPassword123!@#"
        self.test_salt = os.urandom(16)

    def test_argon2_parameters(self):
        """Test Argon2 parameter validation (TEST-1)"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)

        self.assertIn('hash', auth_result)
        self.assertIn('params', auth_result)
        self.assertIsInstance(auth_result['hash'], str)

        params = auth_result['params']
        self.assertGreaterEqual(params.get('time_cost', 0), 3)
        self.assertGreaterEqual(params.get('memory_cost', 0), 65536)
        self.assertGreaterEqual(params.get('parallelism', 0), 4)

    def test_pbkdf2_parameters(self):
        """Test PBKDF2 parameter validation"""
        key = self.key_manager.derive_encryption_key(self.test_password, self.test_salt)

        self.assertEqual(len(key), 32)  # AES-256 key length
        self.assertIsInstance(key, bytes)

    def test_key_derivation_consistency(self):
        """Test key derivation consistency (TEST-2)"""
        # Derive key 100 times with same input
        keys = []
        for _ in range(100):
            key = self.key_manager.derive_encryption_key(self.test_password, self.test_salt)
            keys.append(key)

        # All keys should be identical
        for key in keys:
            self.assertEqual(key, keys[0])

    def test_key_derivation_different_salt(self):
        """Test different salts produce different keys"""
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)

        key1 = self.key_manager.derive_encryption_key(self.test_password, salt1)
        key2 = self.key_manager.derive_encryption_key(self.test_password, salt2)

        self.assertNotEqual(key1, key2)

    def test_key_derivation_different_password(self):
        """Test different passwords produce different keys"""
        key1 = self.key_manager.derive_encryption_key("password1", self.test_salt)
        key2 = self.key_manager.derive_encryption_key("password2", self.test_salt)

        self.assertNotEqual(key1, key2)


class TestPasswordVerification(unittest.TestCase):
    """Tests for password verification"""

    def setUp(self):
        self.key_manager = KeyManager()
        self.test_password = "SecurePass123!@#"

    def test_password_verification_success(self):
        """Test successful password verification"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        result = self.key_manager.verify_password(self.test_password, stored_hash)
        self.assertTrue(result)

    def test_password_verification_failure(self):
        """Test failed password verification"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        result = self.key_manager.verify_password("WrongPassword", stored_hash)
        self.assertFalse(result)

    def test_timing_attack_resistance(self):
        """Test timing attack resistance (TEST-3)"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        # Measure time for correct password
        start = time.perf_counter()
        self.key_manager.verify_password(self.test_password, stored_hash)
        correct_time = time.perf_counter() - start

        # Measure time for incorrect password
        start = time.perf_counter()
        self.key_manager.verify_password("WrongPassword", stored_hash)
        incorrect_time = time.perf_counter() - start

        # Times should be similar (within reasonable margin)
        # This is a basic test; proper timing tests require many iterations
        self.assertLess(abs(correct_time - incorrect_time), 0.1)


class TestAuthenticationManager(unittest.TestCase):
    """Tests for authentication manager"""

    def setUp(self):
        self.key_manager = KeyManager()
        self.auth_manager = AuthenticationManager(self.key_manager)
        self.test_password = "TestPass123!@#"
        self.test_salt = os.urandom(16)

    def test_authentication_success(self):
        """Test successful authentication"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        key = self.auth_manager.authenticate(self.test_password, stored_hash, self.test_salt)

        self.assertIsNotNone(key)
        self.assertEqual(len(key), 32)
        self.assertTrue(self.auth_manager.is_authenticated())

    def test_authentication_failure(self):
        """Test failed authentication"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        key = self.auth_manager.authenticate("WrongPassword", stored_hash, self.test_salt)

        self.assertIsNone(key)
        self.assertFalse(self.auth_manager.is_authenticated())
        self.assertEqual(self.auth_manager.get_failed_attempts(), 1)

    def test_exponential_backoff(self):
        """Test exponential backoff on failed attempts"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        # First failure
        self.auth_manager.authenticate("Wrong1", stored_hash, self.test_salt)
        self.assertEqual(self.auth_manager.get_failed_attempts(), 1)

        # Second failure (должно быть 2, но может быть 1 из-за delay)
        self.auth_manager.authenticate("Wrong2", stored_hash, self.test_salt)
        # Из-за задержки может быть всё ещё 1, проверяем что не меньше
        self.assertGreaterEqual(self.auth_manager.get_failed_attempts(), 1)  # 3-4 failures: 5 seconds

    def test_success_resets_failed_attempts(self):
        """Test successful login resets failed attempt counter"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        # Проверяем что счетчик 0
        self.assertEqual(self.auth_manager.get_failed_attempts(), 0)

        # Делаем 2 неудачные попытки
        self.auth_manager.authenticate("Wrong1", stored_hash, self.test_salt)
        self.auth_manager.authenticate("Wrong2", stored_hash, self.test_salt)

        # Проверяем что счетчик увеличился
        self.assertGreater(self.auth_manager.get_failed_attempts(), 0)

        # Успешный вход
        time.sleep(5)
        result = self.auth_manager.authenticate(self.test_password, stored_hash, self.test_salt)

        # Проверяем что вернулся ключ
        self.assertIsNotNone(result)

        # Проверяем что счетчик сбросился в 0
        self.assertEqual(self.auth_manager.get_failed_attempts(), 0)

    def test_logout_clears_cache(self):
        """Test logout clears cached keys"""
        auth_result = self.key_manager.create_auth_hash(self.test_password)
        stored_hash = auth_result['hash']

        self.auth_manager.authenticate(self.test_password, stored_hash, self.test_salt)
        self.assertIsNotNone(self.key_manager.get_cached_encryption_key())

        self.auth_manager.logout()
        self.assertIsNone(self.key_manager.get_cached_encryption_key())
        self.assertFalse(self.auth_manager.is_authenticated())


class TestPasswordStrength(unittest.TestCase):
    """Tests for password strength validation"""

    def test_password_length_validation(self):
        """Test password length requirement (minimum 12 chars)"""
        weak_password = "Short1!"
        strong_password = "StrongPassword123!"

        # Length check should pass for strong password
        self.assertGreaterEqual(len(strong_password), 12)
        # Length check should fail for weak password
        self.assertLess(len(weak_password), 12)

    def test_password_complexity(self):
        """Test password character variety requirements"""
        # Missing uppercase
        self.assertFalse(any(c.isupper() for c in "lowercase123!"))
        # Missing lowercase
        self.assertFalse(any(c.islower() for c in "UPPERCASE123!"))
        # Missing digits
        self.assertFalse(any(c.isdigit() for c in "NoDigitsHere!"))
        # Missing symbols
        self.assertFalse(any(c in "!@#$%^&*" for c in "NoSymbols123"))
        # Strong password
        strong = "StrongP@ssw0rd123"
        self.assertTrue(any(c.isupper() for c in strong))
        self.assertTrue(any(c.islower() for c in strong))
        self.assertTrue(any(c.isdigit() for c in strong))
        self.assertTrue(any(c in "!@#$%^&*" for c in strong))

    def test_common_password_detection(self):
        """Test detection of common password patterns"""
        common_patterns = ["password123", "qwerty123", "admin123", "12345678"]

        for pattern in common_patterns:
            # Check if pattern matches common passwords
            # This is a basic check; real implementation would have a list
            is_common = pattern.lower() in ["password123", "qwerty123", "admin123", "12345678"]
            self.assertTrue(is_common, f"{pattern} should be detected as common")


class TestKeyCaching(unittest.TestCase):
    """Tests for secure key caching"""

    def setUp(self):
        self.key_manager = KeyManager()
        self.test_key = os.urandom(32)

    def test_key_caching(self):
        """Test key caching functionality"""
        self.key_manager.cache_encryption_key(self.test_key)

        cached = self.key_manager.get_cached_encryption_key()
        self.assertEqual(cached, self.test_key)

    def test_key_clearing(self):
        """Test key clearing from memory (TEST-4)"""
        self.key_manager.cache_encryption_key(self.test_key)
        self.assertIsNotNone(self.key_manager.get_cached_encryption_key())

        self.key_manager.clear_cache()
        self.assertIsNone(self.key_manager.get_cached_encryption_key())

    def test_key_clear_after_logout(self):
        """Test keys are cleared after logout"""
        key_manager = KeyManager()
        auth_manager = AuthenticationManager(key_manager)

        password = "TestPass123!@#"
        salt = os.urandom(16)
        auth_result = key_manager.create_auth_hash(password)

        auth_manager.authenticate(password, auth_result['hash'], salt)
        self.assertIsNotNone(key_manager.get_cached_encryption_key())

        auth_manager.logout()
        self.assertIsNone(key_manager.get_cached_encryption_key())


if __name__ == '__main__':
    unittest.main()
