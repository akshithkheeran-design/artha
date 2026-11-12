"""Envelope encryption (AES-256-GCM), Ed25519 signing and hashing helpers."""
import base64
import hashlib
import hmac
import json
import os
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .config import INDEX_KEY, MASTER_KEY, SIGNING_SEED


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def _open(key: bytes, blob: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], aad)


def new_wrapped_dek(user_id: int) -> bytes:
    """Generate a per-user data-encryption key, wrapped by the master key."""
    return _seal(MASTER_KEY, AESGCM.generate_key(bit_length=256), f"dek:{user_id}".encode())


def unwrap_dek(wrapped: bytes, user_id: int) -> bytes:
    return _open(MASTER_KEY, wrapped, f"dek:{user_id}".encode())


def encrypt_json(dek: bytes, obj: Any, context: str) -> bytes:
    return _seal(dek, canonical(obj), context.encode())


def decrypt_json(dek: bytes, blob: bytes, context: str) -> Any:
    return json.loads(_open(dek, blob, context.encode()))


def encrypt_bytes(dek: bytes, data: bytes, context: str) -> bytes:
    return _seal(dek, data, context.encode())


def decrypt_bytes(dek: bytes, blob: bytes, context: str) -> bytes:
    return _open(dek, blob, context.encode())


def blind_index(value: str, scope: str = "") -> str:
    """Keyed hash so identifiers (e.g. UPI VPAs) can be grouped without storing them."""
    return hmac.new(INDEX_KEY, f"{scope}:{value.strip().lower()}".encode(), hashlib.sha256).hexdigest()[:16]


_SIGNER = Ed25519PrivateKey.from_private_bytes(SIGNING_SEED)
_PUBLIC: Ed25519PublicKey = _SIGNER.public_key()


def sign(data: bytes) -> str:
    return base64.b64encode(_SIGNER.sign(data)).decode()


def verify(signature_b64: str, data: bytes) -> bool:
    try:
        _PUBLIC.verify(base64.b64decode(signature_b64), data)
        return True
    except Exception:
        return False


def public_key_b64() -> str:
    return base64.b64encode(_PUBLIC.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
