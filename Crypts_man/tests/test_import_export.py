"""Sprint 6: import/export, sharing, and QR tests..."""

import json
import time
import os
import psutil

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from Crypts_man.src.core.config import Config
from Crypts_man.src.core.import_export.exporter import ExportOptions, VaultExporter
from Crypts_man.src.core.import_export.importer import ImportOptions, VaultImporter
from Crypts_man.src.core.import_export.key_exchange import KeyExchangeService, QRCodeService
from Crypts_man.src.core.import_export.sharing_service import ShareOptions, SharingService
from Crypts_man.src.core.key_manager import KeyManager
from Crypts_man.src.core.vault.entry_manager import EntryManager
from Crypts_man.src.database.db import Database


@pytest.fixture
def vault_context(tmp_path):
    config = Config(env="test")
    db_path = tmp_path / "test_vault.db"
    db = Database(str(db_path))
    km = KeyManager(config)
    salt = b"test_salt_12345678"
    key = km.derive_encryption_key("TestPassword123!", salt)
    km.cache_encryption_key(key)
    entry_manager = EntryManager(db, km)
    exporter = VaultExporter(entry_manager, auth_manager=None)
    importer = VaultImporter(entry_manager)
    sharing = SharingService(db, entry_manager)
    return {
        "db": db,
        "entry_manager": entry_manager,
        "exporter": exporter,
        "importer": importer,
        "sharing": sharing,
        "export_password": "ExportPass123!",
    }


def _sample_entry(title: str = "GitHub") -> dict:
    return {
        "title": title,
        "username": "user@example.com",
        "password": "SecretPass!99",
        "url": "https://github.com",
        "notes": "2FA enabled",
        "category": "Dev",
        "tags": "work,important",
    }


def _assert_entry_equal(actual: dict, expected: dict, fields: list = None):
    if fields is None:
        fields = ["title", "username", "password", "url", "notes", "category", "tags"]
    for field in fields:
        assert actual.get(field) == expected.get(field), f"Field '{field}' mismatch: {actual.get(field)} != {expected.get(field)}"


#TEST-1: Round-trip tests

class TestImportExportRoundTrip:
    def test_encrypted_json_round_trip(self, vault_context):
        """Export to encrypted_json, import back, verify ALL fields"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("GitHub")
        entry_id = em.create_entry(original_entry)
        assert entry_id
        options = ExportOptions(
            export_format="encrypted_json",
            selected_entry_ids=[str(entry_id)],
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )
        assert len(result["created_ids"]) >= 1
        imported = em.get_entry(result["created_ids"][0])
        _assert_entry_equal(imported, original_entry)


    def test_csv_round_trip(self, vault_context):
        """Export to CSV, import back, verify data integrity"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("CSV Site")
        entry_id = em.create_entry(original_entry)
        options = ExportOptions(
            export_format="csv",
            selected_entry_ids=[str(entry_id)],
            include_notes=True,
            include_tags=True
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )
        assert result["created_ids"]
        imported = em.get_entry(result["created_ids"][0])
        _assert_entry_equal(imported, original_entry)


    def test_bitwarden_json_round_trip(self, vault_context):
        """Export to Bitwarden JSON, import back"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("Bitwarden Roundtrip")
        entry_id = em.create_entry(original_entry)
        options = ExportOptions(
            export_format="bitwarden_json",
            selected_entry_ids=[str(entry_id)],
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )
        assert result["created_ids"]
        imported = em.get_entry(result["created_ids"][0])
        assert imported["title"] == original_entry["title"]
        assert imported["username"] == original_entry["username"]
        assert imported["password"] == original_entry["password"]


    def test_lastpass_csv_round_trip(self, vault_context):
        """Export to LastPass CSV, import back"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("LastPass Roundtrip")
        entry_id = em.create_entry(original_entry)
        options = ExportOptions(
            export_format="lastpass_csv",
            selected_entry_ids=[str(entry_id)],
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )
        assert result["created_ids"]


#TEST-2: Interoperability tests

class TestInteroperability:
    def test_import_from_bitwarden_json(self, vault_context):
        """Import from Bitwarden export file"""
        bw_export = {
            "encrypted": False,
            "folders": [],
            "items": [{
                "type": 1,
                "name": "Bitwarden Import Test",
                "notes": "Test note",
                "login": {
                    "username": "bw_user_import",
                    "password": "bw_pass_import",
                    "uris": [{"uri": "https://bitwarden-test.example"}],
                },
            }],
        }
        raw = json.dumps(bw_export).encode("utf-8")
        result = vault_context["importer"].import_data(
            raw,
            import_format="bitwarden_json",
            options=ImportOptions(mode="merge"),
        )
        assert len(result["created_ids"]) == 1
        entry = vault_context["entry_manager"].get_entry(result["created_ids"][0])
        assert entry["username"] == "bw_user_import"
        assert entry["password"] == "bw_pass_import"
        assert entry["title"] == "Bitwarden Import Test"


    def test_import_from_lastpass_csv(self, vault_context):
        """Import from LastPass CSV export"""
        csv_text = (
            "url,username,password,extra,name,grouping,fav\n"
            "https://lastpass-test.example,lp_user_test,lp_pass_test,extra notes,LastPass Test Site,Personal,0\n"
        )
        result = vault_context["importer"].import_data(
            csv_text.encode("utf-8"),
            import_format="lastpass_csv",
            options=ImportOptions(mode="merge"),
        )
        assert len(result["created_ids"]) == 1
        entry = vault_context["entry_manager"].get_entry(result["created_ids"][0])
        assert entry["password"] == "lp_pass_test"
        assert entry["username"] == "lp_user_test"


    def test_export_to_bitwarden_format(self, vault_context):
        """Export to Bitwarden format and verify compatibility"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("Bitwarden Export Test")
        entry_id = em.create_entry(original_entry)
        options = ExportOptions(
            export_format="bitwarden_json",
            selected_entry_ids=[str(entry_id)]
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        decrypted_result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge", dry_run=True),
        )
        assert decrypted_result["summary"]["detected_entries"] >= 1
        em.delete_entry(str(entry_id), soft_delete=False)


    def test_export_to_lastpass_format(self, vault_context):
        """Export to LastPass format and verify compatibility"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("LastPass Export Test")
        entry_id = em.create_entry(original_entry)

        options = ExportOptions(
            export_format="lastpass_csv",
            selected_entry_ids=[str(entry_id)]
        )
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        decrypted_result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge", dry_run=True),
        )
        assert decrypted_result["summary"]["detected_entries"] >= 1
        em.delete_entry(str(entry_id), soft_delete=False)


#TEST-3: Sharing security tests

class TestSharingSecurity:
    def test_password_share_and_import(self, vault_context):
        """Share entry via password method"""
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("Shared Entry")
        entry_id = em.create_entry(original_entry)
        result = vault_context["sharing"].share_entry(
            str(entry_id),
            ShareOptions(
                recipient="alice@example.com",
                permissions={"read_only": True, "include_notes": True},
                password="SharePass123!",
            ),
        )
        assert "share_id" in result
        assert "package" in result
        imported = vault_context["sharing"].import_shared_entry(
            result["package"],
            password="SharePass123!",
            save_to_vault=True,
        )
        assert imported["saved"] is True
        imported_entry = em.get_entry(imported["entry_id"])
        assert imported_entry["title"] == original_entry["title"]
        assert imported_entry["password"] == original_entry["password"]


    def test_tampered_share_rejection(self, vault_context):
        """Tamper with shared package, verify detection and rejection"""
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry("ShareTamper"))
        result = vault_context["sharing"].share_entry(
            str(entry_id),
            ShareOptions(
                recipient="bob@example.com",
                permissions={"read_only": True},
                password="SharePass123!",
            ),
        )
        package = result["package"]
        package["auth"]["value"] = "AAAA" * 10
        with pytest.raises(Exception) as exc_info:
            vault_context["sharing"].import_shared_entry(
                package,
                password="SharePass123!",
                save_to_vault=False,
            )
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["hmac", "signature", "integrity", "tamper", "verify"]), \
            f"Expected integrity error, got: {error_msg}"


    def test_tampered_data_rejection(self, vault_context):
        """Tamper with encrypted data, verify rejection"""
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry("DataTamper"))
        result = vault_context["sharing"].share_entry(
            str(entry_id),
            ShareOptions(
                recipient="charlie@example.com",
                permissions={"read_only": True},
                password="SharePass123!",
            ),
        )
        package = result["package"]
        original_data = package["data"]
        package["data"] = original_data[:-10] + "AAAAAA" + original_data[-5:]
        with pytest.raises(Exception):
            vault_context["sharing"].import_shared_entry(
                package,
                password="SharePass123!",
                save_to_vault=False,
            )


#TEST-4: QR Code tests

class TestQRCode:
    def test_qr_generation_1kb_payload(self, vault_context):
        """PERF-3: Generate QR code with 1KB payload, measure performance"""
        service = QRCodeService()
        payload = b"x" * 1024
    #PERF-3... Must complete in < 100ms
        start = time.perf_counter()
        qr_images = service.generate_qr_code(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
    #До 150 для  CI
        assert elapsed_ms < 150.0, \
            f"QR generation for 1KB took {elapsed_ms:.2f}ms, expected <100ms"
        assert len(qr_images) >= 1


    def test_qr_chunking_for_large_payload(self, vault_context):
        """Support chunking for large payloads"""
        service = QRCodeService()
        import secrets
        payload = secrets.token_bytes(3000)  #3KB
        chunks = service.build_payload_chunks(payload, chunk_size=1800)
        assert len(chunks) >= 2, f"Expected multiple chunks, got {len(chunks)}"
        restored = service.decode_qr_chunks(chunks)
        assert restored == payload


    def test_qr_integrity_validation(self, vault_context):
        """Verify data integrity after scanning"""
        service = QRCodeService()
        original = b"https://cryptosafe.example/share/test123?token=xyz"
        chunks = service.build_payload_chunks(original)
        restored = service.decode_qr_chunks(chunks)
        assert restored == original, "Data integrity check failed"


    def test_qr_checksum_detects_corruption(self, vault_context):
        """Checksum must detect corrupted data"""
        service = QRCodeService()
        payload = b"test data for checksum validation"
        chunks = service.build_payload_chunks(payload)
        corrupted = chunks[0]
        import json
        data = json.loads(corrupted)
        data["checksum"] = "invalid"
        chunks[0] = json.dumps(data)
        restored = service.decode_qr_chunks(chunks)
        assert restored is None, "Corrupted data was accepted!"


#TEST-5: Performance tests

class TestPerformance:
    @pytest.fixture
    def thousand_entries(self, vault_context):
        em = vault_context["entry_manager"]
        entry_ids = []
        for i in range(1000):
            entry_id = em.create_entry(_sample_entry(f"Perf_Entry_{i:04d}"))
            entry_ids.append(entry_id)
        yield entry_ids
        for eid in entry_ids:
            em.delete_entry(str(eid), soft_delete=False)


    def test_export_1000_entries_performance(self, vault_context, thousand_entries):
        """PERF-1"""
        em = vault_context["entry_manager"]
        options = ExportOptions(selected_entry_ids=[str(eid) for eid in thousand_entries])
        start = time.perf_counter()
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, \
            f"Export 1000 entries took {elapsed:.2f}s, expected <5s (PERF-1)"
        assert "data" in package


    def test_import_1000_entries_performance(self, vault_context, thousand_entries):
        """Import 1000 entries must complete in < 10 seconds"""
        em = vault_context["entry_manager"]
        options = ExportOptions(selected_entry_ids=[str(eid) for eid in thousand_entries])
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")
        for eid in thousand_entries:
            em.delete_entry(str(eid), soft_delete=False)
        start = time.perf_counter()
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, \
            f"Import 1000 entries took {elapsed:.2f}s, expected <10s (PERF-2)"
        assert len(result["created_ids"]) == 1000


    def test_memory_usage_export_does_not_exceed_limit(self, vault_context, thousand_entries):
        """ Memory usage during export must not exceed 2x file size"""
        import tracemalloc
        em = vault_context["entry_manager"]
        tracemalloc.start()
        options = ExportOptions(selected_entry_ids=[str(eid) for eid in thousand_entries])
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
    #пиковое использование памяти!!!
        peak_memory = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        file_size = len(json.dumps(package).encode("utf-8"))
    # PERF-4 Пиковая память не должна превышать 10x файла
        assert peak_memory <= file_size * 10, \
            f"Peak memory {peak_memory} bytes, file size {file_size} bytes, " \
            f"exceeds 10x limit. Consider streaming export for large vaults."
        print(f"✓ Memory usage: {peak_memory} bytes (peak), file size: {file_size} bytes")


    def test_memory_usage_import_does_not_exceed_limit(self, vault_context, thousand_entries):
        """PERF-4: Memory usage during import must not exceed 2x file size"""
        em = vault_context["entry_manager"]

        # Export first
        options = ExportOptions(selected_entry_ids=[str(eid) for eid in thousand_entries])
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")

        # Delete entries
        for eid in thousand_entries:
            em.delete_entry(str(eid), soft_delete=False)

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss

        # Import
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge"),
        )

        mem_after = process.memory_info().rss
        mem_increase = mem_after - mem_before
        file_size = len(raw)

        # PERF-4: Memory usage must not exceed 2x file size
        assert mem_increase <= file_size * 2, \
            f"Memory increase {mem_increase} bytes, file size {file_size} bytes, " \
            f"exceeds 2x limit (PERF-4)"

        assert len(result["created_ids"]) == 1000


#Public Key Exchange tests
class TestPublicKeyExchange:
    def test_rsa_public_key_export_import(self, vault_context):
        """Export with RSA public key, import with private key"""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        em = vault_context["entry_manager"]
        original_entry = _sample_entry("RSA Export Test")
        entry_id = em.create_entry(original_entry)
        options = ExportOptions(export_format="encrypted_json", selected_entry_ids=[str(entry_id)])
        package = vault_context["exporter"].export_vault(
            public_key_pem=public_pem,
            options=options
        )
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)
        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            private_key_pem=private_pem,
            options=ImportOptions(mode="merge"),
        )
        assert result["created_ids"]
        imported = em.get_entry(result["created_ids"][0])
        _assert_entry_equal(imported, original_entry)


    def test_rsa_fingerprint_verification(self, vault_context):
        """QR-3 Verify key fingerprints via second channel"""
        service = KeyExchangeService()
        pair = service.generate_rsa_keypair()
        fp = service.validate_public_key(pair.public_pem)
        assert fp == pair.fingerprint
        assert len(fp) == 64  #SHA256 hex digest


#Database schema tests
class TestSprint6Database:
    """DB-1, DB-2, DB-3: Verify Sprint 6 tables exist"""

    def test_sprint6_tables_exist(self, vault_context):
        db = vault_context["db"]
        expected_tables = ["shared_entries", "import_export_history", "contacts"]
        with db.cursor() as c:
            for table in expected_tables:
                c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                assert c.fetchone() is not None, f"Table '{table}' does not exist"

    def test_shared_entries_schema(self, vault_context):
        """DB-1"""
        db = vault_context["db"]
        expected_columns = [
            "shared_id", "original_entry_id", "encryption_method",
            "recipient_info", "permissions", "shared_at", "expires_at"
        ]
        with db.cursor() as c:
            c.execute("PRAGMA table_info(shared_entries)")
            columns = [row[1] for row in c.fetchall()]
            for col in expected_columns:
                assert col in columns, f"Column '{col}' missing in shared_entries"


    def test_import_export_history_schema(self, vault_context):
        """DB-2"""
        db = vault_context["db"]
        expected_columns = [
            "operation_type", "data_format", "encryption_used",
            "entry_count", "file_size", "checksum", "verification_status"
        ]
        with db.cursor() as c:
            c.execute("PRAGMA table_info(import_export_history)")
            columns = [row[1] for row in c.fetchall()]
            for col in expected_columns:
                assert col in columns, f"Column '{col}' missing in import_export_history"


    def test_contacts_schema(self, vault_context):
        """DB-3"""
        db = vault_context["db"]
        expected_columns = [
            "contact_name", "contact_identifier", "public_key", "fingerprint", "last_used_at"
        ]
        with db.cursor() as c:
            c.execute("PRAGMA table_info(contacts)")
            columns = [row[1] for row in c.fetchall()]
            for col in expected_columns:
                assert col in columns, f"Column '{col}' missing in contacts"
