"""Synthetic-only vault contract.

This is not production encryption. The stub stores a secret verifier so a
wrong secret fails closed. It never claims authenticated encryption and it
cannot unlock protected or real-record material.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, Mapping, Optional


VAULT_MODE = "SYNTHETIC_STUB_NOT_ENCRYPTED"
SYNTHETIC_RELEASED = False
KDF_NAME = "pbkdf2-hmac-sha256"
KDF_ITERATIONS = 210_000
SCHEMA_VERSION = 2


class VaultError(PermissionError):
    """Raised when unlock or persistence violates the synthetic stub contract."""


def initialize_verifier(secret: str) -> Dict[str, Any]:
    if not isinstance(secret, str) or not secret:
        raise VaultError("Unlock requires a nonempty local secret.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), salt, KDF_ITERATIONS
    )
    return {
        "kdf": KDF_NAME,
        "iterations": KDF_ITERATIONS,
        "salt_hex": salt.hex(),
        "digest_hex": digest.hex(),
    }


def verify_secret(secret: str, verifier: Mapping[str, Any]) -> None:
    if not isinstance(secret, str) or not secret:
        raise VaultError("Unlock requires a nonempty local secret.")
    if not isinstance(verifier, Mapping):
        raise VaultError("Vault verifier is missing.")
    if verifier.get("kdf") != KDF_NAME:
        raise VaultError("Unsupported vault verifier.")
    try:
        iterations = int(verifier["iterations"])
        salt = bytes.fromhex(str(verifier["salt_hex"]))
        expected = bytes.fromhex(str(verifier["digest_hex"]))
    except (KeyError, ValueError, TypeError) as error:
        raise VaultError("Vault verifier is corrupt.") from error
    if iterations != KDF_ITERATIONS or len(salt) != 16 or len(expected) != 32:
        raise VaultError("Vault verifier is corrupt.")
    actual = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    if not hmac.compare_digest(actual, expected):
        raise VaultError("Wrong local secret.")


def assert_synthetic_stub(envelope: Mapping[str, Any]) -> None:
    """Refuse claimed encryption or protected-data unlock."""
    if envelope.get("encryption_claimed") is True:
        raise VaultError(
            "Synthetic stub cannot unlock claimed-encrypted protected data."
        )
    mode = envelope.get("vault_mode")
    if mode not in {None, VAULT_MODE}:
        raise VaultError("Unknown vault mode; refusing to unlock.")
    if envelope.get("protected_data_present") is True:
        raise VaultError("Synthetic stub cannot unlock protected data.")
    if envelope.get("synthetic_released") is True:
        raise VaultError("Synthetic stub cannot claim SYNTHETIC_RELEASED.")
    if envelope.get("can_unlock_protected_data") is True:
        raise VaultError("Synthetic stub cannot unlock protected data.")


def inspect_envelope(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify a state file without unlocking case material."""
    if not envelope:
        return {"kind": "empty", "legacy_plaintext": False}
    schema = envelope.get("schema_version")
    verifier = envelope.get("secret_verifier")
    has_material = bool(envelope.get("cases") or envelope.get("consent"))
    if schema != SCHEMA_VERSION or not verifier:
        return {
            "kind": "legacy_plaintext",
            "legacy_plaintext": True,
            "has_material": has_material,
        }
    assert_synthetic_stub(envelope)
    return {
        "kind": "synthetic_stub",
        "legacy_plaintext": False,
        "has_material": has_material,
        "secret_verifier": verifier,
        "vault_mode": VAULT_MODE,
        "encryption_claimed": False,
        "synthetic_released": SYNTHETIC_RELEASED,
    }


def persistable_case_stub(case_value: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop PHI-adjacent fields. Names, sources, and peer output stay out of disk."""
    return {
        "case_id": str(case_value.get("case_id", "")),
        "lifecycle": str(case_value.get("lifecycle", "")),
        "created_at": str(case_value.get("created_at", "")),
        "updated_at": str(case_value.get("updated_at", "")),
        "recipient": {
            "recipient": None,
            "recipient_role": case_value.get("recipient", {}).get("recipient_role"),
            "authorized_by": None,
            "authorized_at": None,
            "authorization_version": None,
            "authorization_epoch": None,
        },
        "retention_hold_reason": None,
        "deleted_at": case_value.get("deleted_at"),
        "sources": [],
        "peer_outputs": [],
        "receipts": [],
        "name": "",
        "human_reviewed_by": None,
    }


def build_envelope(
    *,
    verifier: Mapping[str, Any],
    consent: Mapping[str, Any],
    cases: list,
    app_version: str,
    build_label: str,
    signing_state: str,
) -> Dict[str, Any]:
    stubs = [persistable_case_stub(case) for case in cases]
    return {
        "schema_version": SCHEMA_VERSION,
        "vault_mode": VAULT_MODE,
        "encryption_claimed": False,
        "synthetic_released": SYNTHETIC_RELEASED,
        "protected_data_present": False,
        "can_unlock_protected_data": False,
        "app_version": app_version,
        "build_label": build_label,
        "signing_state": signing_state,
        "secret_verifier": dict(verifier),
        "consent": dict(consent),
        "cases": stubs,
    }


def envelope_contains_protected_fields(envelope: Mapping[str, Any]) -> Optional[str]:
    for case in envelope.get("cases", []):
        if not isinstance(case, Mapping):
            return "non-object case"
        if case.get("name"):
            return "case name"
        if case.get("sources"):
            return "source seals"
        if case.get("peer_outputs"):
            return "peer outputs"
        recipient = case.get("recipient") or {}
        if recipient.get("recipient"):
            return "named recipient"
    return None
