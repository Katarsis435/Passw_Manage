#GEN-4, TEST-4
import pytest
from Crypts_man.src.core.vault.password_generator import PasswordGenerator


class TestPasswordGenerator:
    def test_generate_basic(self):
        gen = PasswordGenerator()
        pwd = gen.generate(length=16)
        assert len(pwd) == 16
        assert pwd != gen.generate(length=16)  # Уникальность

    def test_generate_with_all_sets(self):
        gen = PasswordGenerator()
        pwd = gen.generate(length=20, use_upper=True, use_lower=True,
                           use_digits=True, use_symbols=True)
        assert len(pwd) == 20

    def test_strength_estimation(self):
        gen = PasswordGenerator()
        strength = gen.estimate_strength("Weak1")
        assert 'score' in strength
        assert 'rating' in strength

    def test_no_duplicates_in_history(self):
        gen = PasswordGenerator(history_size=5)
        passwords = [gen.generate(length=12) for _ in range(100)]
        # Проверяем, что нет полных дубликатов
        assert len(set(passwords)) == 100
