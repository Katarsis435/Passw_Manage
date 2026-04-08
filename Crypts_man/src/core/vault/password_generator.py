# src/core/vault/password_generator.py (enhanced with zxcvbn integration)
import secrets
import string
from typing import List, Set, Optional, Dict
from collections import deque


class PasswordGenerator:
    """Secure password generator with configurable options and strength analysis"""

    DEFAULT_LENGTH = 16
    MIN_LENGTH = 8
    MAX_LENGTH = 64

    # Character sets
    LOWERCASE = string.ascii_lowercase
    UPPERCASE = string.ascii_uppercase
    DIGITS = string.digits
    SYMBOLS = "!@#$%^&*"

    # Ambiguous characters to exclude
    AMBIGUOUS = "lI1O0"

    def __init__(self, history_size: int = 20):
        """
        Initialize password generator

        Args:
            history_size: Number of recent passwords to remember for duplicate prevention
        """
        self.history: deque = deque(maxlen=history_size)

        # Try to import zxcvbn for password strength estimation
        self._zxcvbn_available = False
        try:
            from zxcvbn import zxcvbn
            self._zxcvbn = zxcvbn
            self._zxcvbn_available = True
        except ImportError:
            pass

    def generate(
        self,
        length: int = DEFAULT_LENGTH,
        use_upper: bool = True,
        use_lower: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
        exclude_ambiguous: bool = True
    ) -> str:
        """
        Generate a secure password

        Args:
            length: Password length (8-64)
            use_upper: Include uppercase letters
            use_lower: Include lowercase letters
            use_digits: Include digits
            use_symbols: Include symbols
            exclude_ambiguous: Exclude ambiguous characters

        Returns:
            Generated password
        """
        # Validate length
        if not (self.MIN_LENGTH <= length <= self.MAX_LENGTH):
            raise ValueError(f"Length must be between {self.MIN_LENGTH} and {self.MAX_LENGTH}")

        # Build character pool
        pool = ""
        required_chars = []

        if use_lower:
            chars = self.LOWERCASE
            if exclude_ambiguous:
                chars = ''.join(c for c in chars if c not in self.AMBIGUOUS)
            pool += chars
            required_chars.append(secrets.choice(chars))

        if use_upper:
            chars = self.UPPERCASE
            if exclude_ambiguous:
                chars = ''.join(c for c in chars if c not in self.AMBIGUOUS)
            pool += chars
            required_chars.append(secrets.choice(chars))

        if use_digits:
            chars = self.DIGITS
            if exclude_ambiguous:
                chars = ''.join(c for c in chars if c not in self.AMBIGUOUS)
            pool += chars
            required_chars.append(secrets.choice(chars))

        if use_symbols:
            pool += self.SYMBOLS
            required_chars.append(secrets.choice(self.SYMBOLS))

        if not pool:
            raise ValueError("At least one character set must be selected")

        # Fill remaining characters
        remaining_length = length - len(required_chars)
        password_chars = required_chars.copy()

        for _ in range(remaining_length):
            password_chars.append(secrets.choice(pool))

        # Shuffle to avoid predictable pattern (Fisher-Yates)
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

        password = ''.join(password_chars)

        # Check history for duplicates
        if password in self.history:
            return self.generate(length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous)

        self.history.append(password)
        return password

    def estimate_strength(self, password: str) -> Dict[str, any]:
        """
        Estimate password strength using zxcvbn if available, otherwise built-in estimator

        Returns:
            Dictionary with strength score (0-4) and feedback
        """
        if self._zxcvbn_available:
            try:
                result = self._zxcvbn(password)
                score = result['score']  # 0-4
                feedback = []
                if result.get('feedback', {}).get('warning'):
                    feedback.append(result['feedback']['warning'])
                if result.get('feedback', {}).get('suggestions'):
                    feedback.extend(result['feedback']['suggestions'])

                ratings = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
                return {
                    "score": score,
                    "rating": ratings[score],
                    "feedback": feedback,
                    "crack_time": result.get('crack_times_display', {}).get('offline_slow_hashing_1e4_per_second', 'unknown')
                }
            except Exception:
                pass  # Fall back to built-in estimator

        # Built-in strength estimator
        score = 0
        feedback = []

        # Length check (>=12 is good)
        if len(password) >= 12:
            score += 1
        elif len(password) >= 8:
            feedback.append("Use at least 12 characters for better security")
        else:
            feedback.append("Password is too short")

        # Character variety
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in self.SYMBOLS for c in password)

        variety_count = sum([has_upper, has_lower, has_digit, has_symbol])
        score += variety_count

        if variety_count < 3:
            feedback.append("Add more character types (uppercase, digits, symbols)")

        # Common patterns check
        common_patterns = ["password", "123456", "qwerty", "admin", "letmein", "welcome"]
        if any(pattern in password.lower() for pattern in common_patterns):
            feedback.append("Avoid common words or patterns")
            score = max(0, score - 1)

        # Consecutive characters check
        if any(c * 3 in password for c in set(password)):
            feedback.append("Avoid repeating characters")
            score = max(0, score - 1)

        # Score to rating (0-4)
        score = min(4, score)
        ratings = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]

        return {
            "score": score,
            "rating": ratings[score],
            "feedback": feedback
        }

    def generate_memorable(self, words: int = 4, separator: str = "-") -> str:
        """
        Generate a memorable passphrase using word list

        Args:
            words: Number of words (3-6)
            separator: Word separator character

        Returns:
            Memorable passphrase
        """
        word_list = [
            "correct", "horse", "battery", "staple", "coffee", "mountain",
            "ocean", "forest", "thunder", "cloud", "silver", "golden",
            "butterfly", "dragon", "phoenix", "eagle", "summer", "winter",
            "spring", "autumn", "bridge", "castle", "garden", "tower",
            "crystal", "emerald", "sapphire", "ruby", "diamond", "pearl"
        ]

        if not (3 <= words <= 6):
            words = 4

        selected = [secrets.choice(word_list) for _ in range(words)]

        # Capitalize first letter of each word for better memorability
        selected = [word.capitalize() for word in selected]

        passphrase = separator.join(selected)

        # Add a random number for complexity
        passphrase += str(secrets.randbelow(100))

        return passphrase

    def is_duplicate(self, password: str) -> bool:
        """Check if password was recently generated"""
        return password in self.history

    def clear_history(self) -> None:
        """Clear password history"""
        self.history.clear()
