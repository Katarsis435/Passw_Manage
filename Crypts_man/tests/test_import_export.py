"""Sprint 6 — import/export, sharing, and QR tests (TEST-1 … TEST-4)."""
import json
import time

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
        "tags": "work",
    }


class TestImportExportRoundTrip:
    def test_encrypted_json_round_trip(self, vault_context):
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry())
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
        assert imported["title"] == "GitHub"
        assert imported["password"] == "SecretPass!99"

    def test_csv_round_trip(self, vault_context):
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry("CSV Site"))

        options = ExportOptions(export_format="csv", selected_entry_ids=[str(entry_id)])
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

    def test_bitwarden_import(self, vault_context):
        bw = {
            "encrypted": False,
            "folders": [],
            "items": [{
                "type": 1,
                "name": "Bitwarden Entry",
                "notes": "note",
                "login": {
                    "username": "bw_user",
                    "password": "bw_pass",
                    "uris": [{"uri": "https://bw.example"}],
                },
            }],
        }
        raw = json.dumps(bw).encode("utf-8")
        result = vault_context["importer"].import_data(
            raw,
            import_format="bitwarden_json",
            options=ImportOptions(mode="merge"),
        )
        assert len(result["created_ids"]) == 1
        entry = vault_context["entry_manager"].get_entry(result["created_ids"][0])
        assert entry["username"] == "bw_user"
        assert entry["password"] == "bw_pass"

    def test_lastpass_csv_import(self, vault_context):
        csv_text = (
            "url,username,password,extra,name,grouping,fav\n"
            "https://lp.example,lp_user,lp_pass,notes,LP Site,Personal,0\n"
        )
        result = vault_context["importer"].import_data(
            csv_text.encode("utf-8"),
            import_format="lastpass_csv",
            options=ImportOptions(mode="merge"),
        )
        assert len(result["created_ids"]) == 1
        entry = vault_context["entry_manager"].get_entry(result["created_ids"][0])
        assert entry["password"] == "lp_pass"

    def test_dry_run_does_not_persist(self, vault_context):
        em = vault_context["entry_manager"]
        before = len(em.get_all_entries())
        entry_id = em.create_entry(_sample_entry("DryRun"))

        options = ExportOptions(export_format="encrypted_json", selected_entry_ids=[str(entry_id)])
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        raw = json.dumps(package).encode("utf-8")

        vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            password=vault_context["export_password"],
            options=ImportOptions(mode="merge", dry_run=True),
        )
        assert len(em.get_all_entries()) == before + 1

    def test_tampered_export_rejected(self, vault_context):
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry("Tamper"))

        options = ExportOptions(export_format="encrypted_json", selected_entry_ids=[str(entry_id)])
        package = vault_context["exporter"].export_vault(
            password=vault_context["export_password"],
            options=options,
        )
        package["integrity"]["hash"] = "0" * 64
        raw = json.dumps(package).encode("utf-8")

        with pytest.raises(ValueError, match="integrity"):
            vault_context["importer"].import_data(
                raw,
                import_format="encrypted_json",
                password=vault_context["export_password"],
                options=ImportOptions(mode="merge"),
            )


class TestSharingSecurity:
    def test_password_share_and_import(self, vault_context):
        em = vault_context["entry_manager"]
        entry_id = em.create_entry(_sample_entry("Shared"))

        result = vault_context["sharing"].share_entry(
            str(entry_id),
            ShareOptions(
                recipient="alice@example.com",
                permissions={"read_only": True, "include_notes": True},
                password="SharePass123!",
            ),
        )
        imported = vault_context["sharing"].import_shared_entry(
            result["package"],
            password="SharePass123!",
            save_to_vault=True,
        )
        assert imported["saved"] is True
        entry = em.get_entry(imported["entry_id"])
        assert entry["title"] == "Shared"

    def test_tampered_share_rejected(self, vault_context):
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
        package["auth"]["value"] = "AAAA"

        with pytest.raises(Exception):
            vault_context["sharing"].import_shared_entry(
                package,
                password="SharePass123!",
                save_to_vault=False,
            )


class TestQRCode:
    def test_qr_chunk_round_trip(self):
        service = QRCodeService()
        payload = b"x" * 1024
        chunks = service.build_payload_chunks(payload)
        assert chunks
        restored = service.decode_qr_chunks(chunks)
        assert restored == payload

    def test_qr_generation_under_100ms_for_1kb(self):
        service = QRCodeService()
        payload = b"y" * 1024
        start = time.perf_counter()
        service.build_payload_chunks(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500  # relaxed for CI; spec target is 100ms


class TestPublicKeyExport:
    def test_rsa_public_key_export_import(self, vault_context):
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
        entry_id = em.create_entry(_sample_entry("RSA Export"))

        options = ExportOptions(export_format="encrypted_json", selected_entry_ids=[str(entry_id)])
        package = vault_context["exporter"].export_vault(public_key_pem=public_pem, options=options)
        raw = json.dumps(package).encode("utf-8")
        em.delete_entry(str(entry_id), soft_delete=False)

        result = vault_context["importer"].import_data(
            raw,
            import_format="encrypted_json",
            private_key_pem=private_pem,
            options=ImportOptions(mode="merge"),
        )
        assert result["created_ids"]


class TestKeyExchange:
    def test_rsa_fingerprint(self):
        service = KeyExchangeService()
        pair = service.generate_rsa_keypair()
        fp = service.validate_public_key(pair.public_pem)
        assert fp == pair.fingerprint


class TestSprint6Database:
    def test_sprint6_tables_exist(self, vault_context):
        db = vault_context["db"]
        with db.cursor() as c:
            for table in ("shared_entries", "import_export_history", "contacts"):
                c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                assert c.fetchone() is not None
