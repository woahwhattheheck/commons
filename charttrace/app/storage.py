"""Fail-closed authenticated synthetic persistence.

This is explicitly not production encryption.  The payload is base64 encoded
and authenticated with a secret-derived MAC so plaintext legacy JSON, tampered
state, and a wrong secret cannot unlock.  A production deployment requires a
separately reviewed OS-backed encrypted vault.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Mapping
from uuid import uuid4

from .paths import (
    PathBoundaryError,
    validate_local_directory,
    validate_local_file,
)


VAULT_FORMAT = "charttrace-synthetic-authenticated-vault-v1"
SECURITY_MODEL = "authenticated-obfuscation-not-production-encryption"
KDF_NAME = "scrypt"
KDF_N = 1 << 14
KDF_R = 8
KDF_P = 1
KDF_DKLEN = 32


class VaultError(PermissionError):
    pass


class VaultFormatError(VaultError):
    pass


class VaultAuthenticationError(VaultError):
    pass


def _derive_key(secret: str, salt: bytes) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise VaultAuthenticationError("A local vault secret is required.")
    return hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt,
        n=KDF_N,
        r=KDF_R,
        p=KDF_P,
        dklen=KDF_DKLEN,
    )


def _decode_b64(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise VaultFormatError(f"Vault field {field!r} is invalid.")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as error:
        raise VaultFormatError(f"Vault field {field!r} is invalid.") from error


class LocalStateStore:
    """Synthetic authentication boundary for local-only test and demo state."""

    def __init__(self, data_dir: Path):
        try:
            self.data_dir = validate_local_directory(data_dir)
        except PathBoundaryError as error:
            raise VaultFormatError(str(error)) from error
        self.state_path = self.data_dir / "charttrace-state.json"

    @property
    def exists(self) -> bool:
        return self.state_path.exists() or self.state_path.is_symlink()

    def load(self, secret: str) -> Dict[str, Any]:
        if not self.exists:
            return {}
        try:
            state_path = validate_local_file(self.state_path)
        except PathBoundaryError as error:
            raise VaultFormatError(str(error)) from error
        try:
            with state_path.open("r", encoding="utf-8") as handle:
                envelope = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise VaultFormatError("State is not a valid ChartTrace vault.") from error
        if not isinstance(envelope, dict):
            raise VaultFormatError("State is not a ChartTrace vault envelope.")
        if (
            envelope.get("format") != VAULT_FORMAT
            or envelope.get("security_model") != SECURITY_MODEL
            or envelope.get("production_crypto") is not False
            or envelope.get("signing_state") != "unsigned"
            or envelope.get("artifact_label") != "UNSIGNED_SYNTHETIC"
            or envelope.get("payload_encoding") != "base64-not-encryption"
            or envelope.get("kdf")
            != {
                "name": KDF_NAME,
                "n": KDF_N,
                "r": KDF_R,
                "p": KDF_P,
                "dklen": KDF_DKLEN,
            }
        ):
            raise VaultFormatError(
                "Plaintext, production-crypto claims, and unknown vault formats "
                "are rejected."
            )

        salt = _decode_b64(envelope.get("salt_b64"), "salt_b64")
        verifier = _decode_b64(envelope.get("verifier_b64"), "verifier_b64")
        payload = _decode_b64(envelope.get("payload_b64"), "payload_b64")
        payload_mac = _decode_b64(
            envelope.get("payload_mac_b64"), "payload_mac_b64"
        )
        if len(salt) != 16:
            raise VaultFormatError("Vault salt length is invalid.")
        key = _derive_key(secret, salt)
        expected_verifier = hmac.digest(
            key, b"charttrace-local-vault-verifier-v1", "sha256"
        )
        expected_mac = hmac.digest(key, b"payload:" + payload, "sha256")
        if not hmac.compare_digest(verifier, expected_verifier) or not hmac.compare_digest(
            payload_mac, expected_mac
        ):
            raise VaultAuthenticationError("Vault authentication failed.")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise VaultFormatError("Authenticated vault payload is invalid.") from error
        if not isinstance(value, dict):
            raise VaultFormatError("Authenticated vault payload must be an object.")
        return value

    def save(self, value: Mapping[str, Any], secret: str) -> None:
        if not isinstance(value, Mapping):
            raise VaultFormatError("ChartTrace state root must be an object.")
        key_salt = secrets.token_bytes(16)
        key = _derive_key(secret, key_salt)
        payload = json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        envelope = {
            "format": VAULT_FORMAT,
            "security_model": SECURITY_MODEL,
            "production_crypto": False,
            "signing_state": "unsigned",
            "artifact_label": "UNSIGNED_SYNTHETIC",
            "payload_encoding": "base64-not-encryption",
            "kdf": {
                "name": KDF_NAME,
                "n": KDF_N,
                "r": KDF_R,
                "p": KDF_P,
                "dklen": KDF_DKLEN,
            },
            "salt_b64": base64.b64encode(key_salt).decode("ascii"),
            "verifier_b64": base64.b64encode(
                hmac.digest(
                    key, b"charttrace-local-vault-verifier-v1", "sha256"
                )
            ).decode("ascii"),
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "payload_mac_b64": base64.b64encode(
                hmac.digest(key, b"payload:" + payload, "sha256")
            ).decode("ascii"),
        }

        try:
            validate_local_directory(self.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            validate_local_directory(self.data_dir, must_exist=True)
        except (OSError, PathBoundaryError) as error:
            raise VaultFormatError("Local vault directory is unavailable.") from error

        temporary = self.data_dir / f".charttrace-state-{uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(envelope, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if self.state_path.is_symlink():
                raise VaultFormatError("Vault destination may not be a symbolic link.")
            os.replace(temporary, self.state_path)
        finally:
            if temporary.exists():
                temporary.unlink()
