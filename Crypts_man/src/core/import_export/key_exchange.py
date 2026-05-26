from __future__ import annotations

import base64
import hashlib
import json
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import qrcode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa


@dataclass
class GeneratedKeyPair:
    private_pem: bytes
    public_pem: bytes
    fingerprint: str
    algorithm: str


class KeyExchangeService:
    def generate_rsa_keypair(self, bits: int = 2048) -> GeneratedKeyPair:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_pem).hexdigest()
        return GeneratedKeyPair(private_pem=private_pem, public_pem=public_pem,
                                fingerprint=fingerprint, algorithm="RSA-2048")

    def generate_ec_keypair(self) -> GeneratedKeyPair:
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        fingerprint = hashlib.sha256(public_pem).hexdigest()
        return GeneratedKeyPair(private_pem=private_pem, public_pem=public_pem,
                                fingerprint=fingerprint, algorithm="EC-P256")

    @staticmethod
    def validate_public_key(public_pem: bytes) -> str:
        key = serialization.load_pem_public_key(public_pem)
        normalized = key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(normalized).hexdigest()


class QRCodeService:
    def __init__(self):
        try:
            from qrcode.image.svg import SvgImage
            self.image_factory = SvgImage
        except ImportError:
            self.image_factory = None

    def build_payload_chunks(self, data: bytes, chunk_size: int = 1800,
                             valid_minutes: int = 5) -> list[str]:
        """Build JSON chunk strings (for encoding into QR or tests)."""
        compressed = zlib.compress(data)
        total_chunks = (len(compressed) + chunk_size - 1) // chunk_size
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=valid_minutes)).isoformat()

        chunks = []
        for idx in range(total_chunks):
            chunk = compressed[idx * chunk_size:(idx + 1) * chunk_size]
            chunk_obj = {
                "chunk": idx + 1,
                "total": total_chunks,
                "expires_at": expires_at,
                "checksum": hashlib.sha256(chunk).hexdigest()[:12],
                "data": base64.b64encode(chunk).decode("ascii")
            }
            chunks.append(json.dumps(chunk_obj))
        return chunks

    def generate_qr_code(self, data: bytes, chunk_size: int = 1800, valid_minutes: int = 5) -> list[str]:
        chunk_strings = self.build_payload_chunks(data, chunk_size=chunk_size, valid_minutes=valid_minutes)

        images = []
        for chunk_str in chunk_strings:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                               box_size=10, border=4)
            qr.add_data(chunk_str)
            qr.make(fit=True)
            if self.image_factory is not None:
                img = qr.make_image(image_factory=self.image_factory)
                images.append(img.to_string().decode("utf-8"))
            else:
                import io
                img = qr.make_image()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                images.append(base64.b64encode(buf.getvalue()).decode("ascii"))
        return images

    def decode_qr_chunks(self, chunk_strings: list[str]) -> bytes | None:
        parsed = []
        for chunk_str in chunk_strings:
            try:
                obj = json.loads(chunk_str)
                raw = base64.b64decode(obj["data"])
                checksum = hashlib.sha256(raw).hexdigest()[:12]
                if checksum != obj["checksum"]:
                    return None
                parsed.append((int(obj["chunk"]), raw))
            except Exception:
                return None

        parsed.sort(key=lambda x: x[0])
        payload = b"".join(item[1] for item in parsed)
        try:
            return zlib.decompress(payload)
        except Exception:
            return None
