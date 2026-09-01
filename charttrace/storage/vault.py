"""Offline encrypted-vault contract for the ChartTrace synthetic build.

This stdlib-only envelope uses independent HMAC-SHA256 encryption-stream and
authentication keys.  The metadata labels it truthfully as an unsigned,
synthetic-build implementation; production use requires an audited platform
keystore and signed distribution.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Union


VAULT_FORMAT_VERSION = 1
VAULT_SECURITY_LABEL = "SYNTHETIC_ONLY_UNSIGNED_LOCAL_VAULT"
VAULT_SIGNATURE_STATE = "UNSIGNED"
VAULT_NETWORK_POLICY = "DENY"
PUBLIC_TCP_LISTENER = False
_MAGIC = b"CTVLT1\x00"
_SALT_BYTES = 16
_NONCE_BYTES = 16
_TAG_BYTES = 32
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class VaultError(RuntimeError):
    pass


class VaultLockedError(VaultError):
    pass


class VaultIntegrityError(VaultError):
    pass


def _secret_bytes(secret: Union[str, bytes, bytearray]) -> bytes:
    if isinstance(secret, str):
        encoded = secret.encode("utf-8")
    else:
        encoded = bytes(secret)
    if not encoded:
        raise ValueError("unlock secret cannot be empty")
    return encoded


def _derive_wrapping_key(secret: bytes, salt: bytes) -> bytes:
    return hashlib.scrypt(
        secret,
        salt=salt,
        n=1 << 14,
        r=8,
        p=1,
        dklen=32,
    )


def _expand_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        output.extend(
            hmac.new(
                key, b"ChartTrace-stream\x00" + nonce + counter.to_bytes(8, "big"),
                hashlib.sha256,
            ).digest()
        )
        counter += 1
    return bytes(output[:length])


def _seal(key: bytes, plaintext: bytes, *, aad: bytes) -> bytes:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    encryption_key = hmac.new(key, b"encryption", hashlib.sha256).digest()
    authentication_key = hmac.new(key, b"authentication", hashlib.sha256).digest()
    stream = _expand_stream(encryption_key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream))
    tag = hmac.new(
        authentication_key,
        _MAGIC + nonce + len(aad).to_bytes(8, "big") + aad + ciphertext,
        hashlib.sha256,
    ).digest()
    return _MAGIC + nonce + ciphertext + tag


def _open(key: bytes, envelope: bytes, *, aad: bytes) -> bytes:
    minimum = len(_MAGIC) + _NONCE_BYTES + _TAG_BYTES
    if len(envelope) < minimum or not envelope.startswith(_MAGIC):
        raise VaultIntegrityError("invalid encrypted envelope")
    nonce_start = len(_MAGIC)
    ciphertext_start = nonce_start + _NONCE_BYTES
    nonce = envelope[nonce_start:ciphertext_start]
    ciphertext = envelope[ciphertext_start:-_TAG_BYTES]
    supplied_tag = envelope[-_TAG_BYTES:]
    encryption_key = hmac.new(key, b"encryption", hashlib.sha256).digest()
    authentication_key = hmac.new(key, b"authentication", hashlib.sha256).digest()
    expected_tag = hmac.new(
        authentication_key,
        _MAGIC + nonce + len(aad).to_bytes(8, "big") + aad + ciphertext,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise VaultIntegrityError("wrong unlock secret or modified encrypted bytes")
    stream = _expand_stream(encryption_key, nonce, len(ciphertext))
    return bytes(left ^ right for left, right in zip(ciphertext, stream))


def _canonical_json(value: Dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _metadata_aad(metadata: Dict[str, Any]) -> bytes:
    return _canonical_json(
        {
            key: value
            for key, value in metadata.items()
            if key != "wrapped_case_key"
        }
    )


def _safe_relative_path(relative_name: str) -> PurePosixPath:
    candidate = PurePosixPath(relative_name)
    if (
        not relative_name
        or candidate.is_absolute()
        or ".." in candidate.parts
        or "." in candidate.parts
    ):
        raise ValueError("vault object name must be a safe relative path")
    return candidate


class LocalCaseVault:
    """An unlocked per-case vault whose case key is wrapped by a local secret."""

    def __init__(
        self, root: Path, metadata: Dict[str, Any], case_key: bytes
    ) -> None:
        self.root = root
        self.metadata = dict(metadata)
        self._case_key: Optional[bytearray] = bytearray(case_key)
        self.sealed_dir = root / "sealed"
        self.sealed_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.sealed_dir, 0o700)

    @classmethod
    def create(
        cls,
        root: Union[str, os.PathLike[str]],
        *,
        case_id: str,
        unlock_secret: Union[str, bytes, bytearray],
    ) -> "LocalCaseVault":
        if not _CASE_ID_RE.fullmatch(case_id):
            raise ValueError("case_id is not a stable identifier")
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root_path, 0o700)
        metadata_path = root_path / "vault.json"
        if metadata_path.exists():
            raise FileExistsError(metadata_path)

        salt = secrets.token_bytes(_SALT_BYTES)
        metadata: Dict[str, Any] = {
            "format_version": VAULT_FORMAT_VERSION,
            "case_id": case_id,
            "security_label": VAULT_SECURITY_LABEL,
            "signature_state": VAULT_SIGNATURE_STATE,
            "network_policy": VAULT_NETWORK_POLICY,
            "public_tcp_listener": PUBLIC_TCP_LISTENER,
            "key_wrapping": "scrypt+HMAC-SHA256-STREAM+HMAC-SHA256",
            "salt": base64.b64encode(salt).decode("ascii"),
        }
        wrapping_key = _derive_wrapping_key(_secret_bytes(unlock_secret), salt)
        case_key = secrets.token_bytes(32)
        metadata["wrapped_case_key"] = base64.b64encode(
            _seal(wrapping_key, case_key, aad=_metadata_aad(metadata))
        ).decode("ascii")
        encoded = json.dumps(
            metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        file_descriptor = os.open(
            metadata_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        try:
            with os.fdopen(file_descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            metadata_path.unlink(missing_ok=True)
            raise
        return cls(root_path, metadata, case_key)

    @classmethod
    def unlock(
        cls,
        root: Union[str, os.PathLike[str]],
        *,
        unlock_secret: Union[str, bytes, bytearray],
    ) -> "LocalCaseVault":
        root_path = Path(root)
        metadata_path = root_path / "vault.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="ascii"))
            if metadata.get("format_version") != VAULT_FORMAT_VERSION:
                raise VaultIntegrityError("unsupported vault format")
            if metadata.get("security_label") != VAULT_SECURITY_LABEL:
                raise VaultIntegrityError("vault security label was changed")
            if metadata.get("signature_state") != VAULT_SIGNATURE_STATE:
                raise VaultIntegrityError("vault signature state was changed")
            if metadata.get("network_policy") != VAULT_NETWORK_POLICY:
                raise VaultIntegrityError("vault network policy was changed")
            if metadata.get("public_tcp_listener") is not PUBLIC_TCP_LISTENER:
                raise VaultIntegrityError("vault TCP policy was changed")
            salt = base64.b64decode(metadata["salt"], validate=True)
            wrapped = base64.b64decode(metadata["wrapped_case_key"], validate=True)
        except VaultIntegrityError:
            raise
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VaultIntegrityError("vault metadata is missing or invalid") from exc
        wrapping_key = _derive_wrapping_key(_secret_bytes(unlock_secret), salt)
        case_key = _open(wrapping_key, wrapped, aad=_metadata_aad(metadata))
        if len(case_key) != 32:
            raise VaultIntegrityError("wrapped case key has invalid length")
        return cls(root_path, metadata, case_key)

    @property
    def case_id(self) -> str:
        return str(self.metadata["case_id"])

    @property
    def is_unlocked(self) -> bool:
        return self._case_key is not None

    def _key(self) -> bytes:
        if self._case_key is None:
            raise VaultLockedError("case vault is locked")
        return bytes(self._case_key)

    def seal_bytes(self, relative_name: str, plaintext: bytes) -> Path:
        relative = _safe_relative_path(relative_name)
        target = self.sealed_dir.joinpath(*relative.parts).with_suffix(
            relative.suffix + ".ctenc"
        )
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(target.parent, 0o700)
        aad = f"{self.case_id}:{relative.as_posix()}".encode("utf-8")
        envelope = _seal(self._key(), bytes(plaintext), aad=aad)
        temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            os.chmod(target, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def open_bytes(self, relative_name: str) -> bytes:
        relative = _safe_relative_path(relative_name)
        target = self.sealed_dir.joinpath(*relative.parts).with_suffix(
            relative.suffix + ".ctenc"
        )
        aad = f"{self.case_id}:{relative.as_posix()}".encode("utf-8")
        try:
            envelope = target.read_bytes()
        except OSError as exc:
            raise VaultIntegrityError("sealed vault object is unavailable") from exc
        return _open(self._key(), envelope, aad=aad)

    def lock(self) -> None:
        if self._case_key is not None:
            for index in range(len(self._case_key)):
                self._case_key[index] = 0
            self._case_key = None

    def __enter__(self) -> "LocalCaseVault":
        self._key()
        return self

    def __exit__(self, *_: object) -> None:
        self.lock()
