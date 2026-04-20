#CRUD-1, TEST-1, TEST-2
import pytest
from Crypts_man.src.core.vault.entry_manager import EntryManager
from Crypts_man.src.core.key_manager import KeyManager
from Crypts_man.src.database.db import Database
from Crypts_man.src.core.config import Config


class TestEntryManager:
    @pytest.fixture
    def setup(self):
        config = Config(env="test")
        db = Database(config.database_path)
        km = KeyManager(config)
        # Создать тестовый ключ
        salt = b'test_salt_123456'
        key = km.derive_encryption_key("TestPassword123!", salt)
        km.cache_encryption_key(key)
        return EntryManager(db, km)

    def test_create_and_get_entry(self, setup):
        manager = setup
        entry_data = {
            'title': 'Test Entry',
            'username': 'test@example.com',
            'password': 'SecurePass123!',
            'url': 'https://example.com',
            'category': 'Test',
            'tags': 'test, temp',
            'notes': 'Test notes'
        }
        entry_id = manager.create_entry(entry_data)
        assert entry_id is not None

        retrieved = manager.get_entry(entry_id)
        assert retrieved['title'] == 'Test Entry'
        assert retrieved['password'] == 'SecurePass123!'

    def test_update_entry(self, setup):
        manager = setup
        entry_id = manager.create_entry({'title': 'Original', 'password': 'pass1'})
        updated = manager.update_entry(entry_id, {'title': 'Updated', 'password': 'pass2'})
        assert updated['title'] == 'Updated'

        retrieved = manager.get_entry(entry_id)
        assert retrieved['title'] == 'Updated'

    def test_delete_entry(self, setup):
        manager = setup
        entry_id = manager.create_entry({'title': 'ToDelete', 'password': 'pass'})
        assert manager.delete_entry(entry_id, soft_delete=True) is True

        # При soft delete запись не должна быть доступна
        retrieved = manager.get_entry(entry_id)
        assert retrieved is None

    def test_get_all_entries(self, setup):
        manager = setup
        for i in range(10):
            manager.create_entry({'title': f'Entry {i}', 'password': f'pass{i}'})

        entries = manager.get_all_entries()
        assert len(entries) >= 10
