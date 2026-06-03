from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from Crypts_man.src.core.import_export.formats.csv_format import CSVFormat, LastPassCSVFormat
from Crypts_man.src.core.import_export.formats.json_format import BitwardenJSONFormat

class ImportOptions:
    def __init__(self, mode: str = "merge", dry_run: bool = False,
                 max_file_size: int = 10 * 1024 * 1024,
                 timeout_seconds: int = 30, duplicate_strategy: str = "skip"):
        self.mode = mode
        self.dry_run = dry_run
        self.max_file_size = max_file_size
        self.timeout_seconds = timeout_seconds
        self.duplicate_strategy = duplicate_strategy


class VaultImporter:
    SCRIPT_PATTERNS = [
        re.compile(r"<script", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"onerror\s*=", re.IGNORECASE),
        re.compile(r"onload\s*=", re.IGNORECASE)
    ]

    def __init__(self, entry_manager, audit_logger=None):
        self.entry_manager = entry_manager
        self.audit_logger = audit_logger

    def import_data(self, raw: bytes, import_format: str | None = None,
                    password: str | None = None, private_key_pem: bytes | None = None,
                    options: ImportOptions | None = None) -> dict[str, Any]:
        options = options or ImportOptions()
        started = time.time()

        print(f"=== IMPORT DEBUG ===")
        print(f"1. File size: {len(raw)} bytes")
        print(f"2. import_format arg: {import_format}")
        print(f"3. password provided: {password is not None}")
        print(f"4. private_key_pem provided: {private_key_pem is not None}")
        print(f"5. options.mode: {options.mode}, dry_run: {options.dry_run}")


        if len(raw) > options.max_file_size:
            raise ValueError("Import file exceeds configured size limit")

        detected_format = import_format or self._detect_format(raw)
        if not detected_format:
            raise ValueError("Could not detect import format")

        if time.time() - started > options.timeout_seconds:
            raise TimeoutError("Import timed out")

        if detected_format == "encrypted_json":
            print(f"7. Processing encrypted_json format")
            package = json.loads(raw.decode("utf-8"))
            print(f"8. Package keys: {package.keys()}")
            print(f"9. Has 'encryption'? {'encryption' in package}")
            print(f"10. Has 'data'? {'data' in package}")

            plaintext = self._decrypt_native_package(raw, password=password, private_key_pem=private_key_pem)
            print(f"11. Decrypted plaintext length: {len(plaintext)} bytes")
            print(f"12. Plaintext preview: {plaintext[:200]}")
            inner_format = package.get("format", "encrypted_json")
            print(f"13. inner_format: {inner_format}")
            if inner_format == "csv":
                entries = CSVFormat.import_data(plaintext)
            elif inner_format == "bitwarden_json":
                entries = BitwardenJSONFormat.import_data(plaintext)
            elif inner_format == "lastpass_csv":
                entries = LastPassCSVFormat.import_data(plaintext)
            else:
                entries = self._parse_native_decrypted_payload(plaintext)
        elif detected_format == "csv":
            entries = CSVFormat.import_data(raw)
        elif detected_format == "bitwarden_json":
            entries = BitwardenJSONFormat.import_data(raw)
        elif detected_format == "lastpass_csv":
            entries = LastPassCSVFormat.import_data(raw)
        else:
            raise ValueError(f"Unsupported format: {detected_format}")

        sanitized = [self._sanitize_entry(e) for e in entries]
        sanitized = [e for e in sanitized if self._is_valid_entry(e)]

        existing = self.entry_manager.get_all_entries()

        if options.mode == "replace":
            planned_create = list(sanitized)
        else:
            existing_keys = {(e.get("ХУЙ", ""), e.get("username", ""), e.get("url", "")) for e in existing}
            planned_create = []
            for e in sanitized:
                key = (e.get("title", ""), e.get("username", ""), e.get("url", ""))
                if key in existing_keys and options.duplicate_strategy == "skip":
                    continue
                planned_create.append(e)

        summary = {
            "format": detected_format,
            "detected_entries": len(entries),
            "sanitized_entries": len(sanitized),
            "to_create": len(planned_create),
            "dry_run": options.dry_run
        }

        if options.dry_run:
            return {"summary": summary, "entries": planned_create}

        if options.mode == "replace":
            for e in existing:
                self.entry_manager.delete_entry(str(e["id"]), soft_delete=False)

        created_ids = []
        for e in planned_create:
            entry_id = self.entry_manager.create_entry(e)
            created_ids.append(str(entry_id))

        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="VAULT_IMPORT", severity="INFO", source="import_export",
                details={"format": detected_format, "detected_entries": len(entries),
                         "imported_entries": len(created_ids), "mode": options.mode}
            )

        return {"summary": summary, "created_ids": created_ids}

    def _detect_format(self, raw: bytes) -> str | None:
        text = raw[:4096].decode("utf-8", errors="ignore").lstrip()
        print(f"=== DETECT FORMAT DEBUG ===")
        print(f"First 500 chars of file: {text[:500]}")

        if '"cryptosafe_export"' in text or '"cryptosafe_share"' in text:
            print("-> Detected: encrypted_json")
            return "encrypted_json"
        if '"folders"' in text and '"items"' in text:
            print("-> Detected: bitwarden_json")
            return "bitwarden_json"
        if "url,username,password" in text.lower() or "title,username,password" in text.lower():
            print("-> Detected: csv")
            return "csv"
        if "url,username,password,extra,name,grouping" in text.lower():
            print("-> Detected: lastpass_csv")
            return "lastpass_csv"
        print("-> Detected: None")
        return None

    def _decrypt_native_package(self, raw: bytes, password: str | None, private_key_pem: bytes | None) -> bytes:
        print(f"=== DECRYPT DEBUG ===")
        print(f"Password provided: {password is not None}")
        print(f"Password value: '{password}'")
        print(f"Private key provided: {private_key_pem is not None}")

        package = json.loads(raw.decode("utf-8"))
        encrypted_blob = base64.b64decode(package["data"])
        encryption = package["encryption"]

        if "encrypted_key" in package:
            print("Using public key decryption path")
            if not private_key_pem:
                raise ValueError("Private key required for this package")

            private_key = serialization.load_pem_private_key(private_key_pem, password=None)
            symmetric_key = private_key.decrypt(
                base64.b64decode(package["encrypted_key"]),
                rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                                 algorithm=hashes.SHA256(), label=None)
            )
            nonce = base64.b64decode(encryption["nonce"])
            plaintext = AESGCM(symmetric_key).decrypt(nonce, encrypted_blob, None)

        else:
            print("Using password decryption path")
            if not password:
                print("ERROR: No password provided but package requires password!")
                raise ValueError("Password required for this package")

            salt = base64.b64decode(encryption["salt"])
            nonce = base64.b64decode(encryption["nonce"])
            iterations = int(encryption.get("iterations", 100000))
            alg = encryption.get("algorithm", "AES-256-GCM")
            length = 32 if "256" in alg else 16

            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=length, salt=salt, iterations=iterations)
            key = kdf.derive(password.encode("utf-8"))

            auth = package.get("auth", {})
            if auth.get("mode") == "hmac-sha256":
                export_hmac_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                                       info=b"cryptosafe-export-hmac").derive(key)
                h = hmac.HMAC(export_hmac_key, hashes.SHA256())
                h.update(encrypted_blob)
                h.verify(base64.b64decode(auth["value"]))

            plaintext = AESGCM(key).decrypt(nonce, encrypted_blob, None)

        if package.get("compressed"):
            plaintext = gzip.decompress(plaintext)

        integrity = package.get("integrity", {})
        expected_hash = integrity.get("hash")
        if expected_hash and hashlib.sha256(plaintext).hexdigest() != expected_hash:
            raise ValueError("Export integrity check failed — file may be corrupted or tampered")
        return plaintext

    def _parse_native_decrypted_payload(self, plaintext: bytes) -> list[dict[str, Any]]:
        data = json.loads(plaintext.decode("utf-8"))
        if "entries" in data:
            return list(data["entries"])
        raise ValueError("Invalid native payload")

    def _sanitize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, value in entry.items():
            if value is None:
                cleaned[key] = ""
                continue
            text = str(value).replace("\x00", "").strip()
            for pat in self.SCRIPT_PATTERNS:
                text = pat.sub("[REMOVED]", text)
            cleaned[key] = text[:10000]
        return cleaned

    @staticmethod
    def _is_valid_entry(entry: dict[str, Any]) -> bool:
        return bool(entry.get("title")) and bool(entry.get("password"))
