"""Immutable recipient-specific .ctpkg manifest and verification.

This module hashes canonical package bytes. It does not claim production
encryption, code signing, or counsel approval.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json


SIGNING_STATE = "UNSIGNED_SYNTHETIC"
INTEGRITY = "SHA256_MANIFEST_ONLY"
CTPKG_VERSION = "charttrace-ctpkg-v1"


@dataclass(frozen=True, slots=True)
class CtpkgPackage:
    case_id: str
    recipient_id: str
    release_id: str
    payload: dict[str, object]
    package_sha256: str
    signing_state: str = SIGNING_STATE
    integrity: str = INTEGRITY
    counsel_approved: bool = False
    production_crypto: bool = False

    def to_bytes(self) -> bytes:
        body = asdict(self)
        body.pop("package_sha256")
        return (
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_ctpkg(
    case_id: str,
    recipient_id: str,
    release_id: str,
    payload: dict[str, object],
) -> CtpkgPackage:
    if not case_id or not recipient_id or not release_id:
        raise ValueError("case, recipient, and release identifiers are required")
    draft = CtpkgPackage(
        case_id=case_id,
        recipient_id=recipient_id,
        release_id=release_id,
        payload=payload,
        package_sha256="",
    )
    digest = _digest(draft.to_bytes())
    return CtpkgPackage(
        case_id=case_id,
        recipient_id=recipient_id,
        release_id=release_id,
        payload=payload,
        package_sha256=digest,
    )


def verify_ctpkg(
    package: CtpkgPackage,
    expected_recipient: str,
    expected_bytes: bytes | None = None,
) -> None:
    if package.recipient_id != expected_recipient:
        raise ValueError("package recipient does not match the authorized recipient")
    recomputed = _digest(package.to_bytes())
    if recomputed != package.package_sha256:
        raise ValueError("package hash does not match canonical bytes")
    if expected_bytes is not None and expected_bytes != package.to_bytes():
        raise ValueError("package bytes changed; fail closed")
    if package.signing_state != SIGNING_STATE:
        raise ValueError("synthetic package must remain labeled unsigned")
    if package.production_crypto or package.counsel_approved:
        raise ValueError("package must not claim production crypto or counsel approval")
