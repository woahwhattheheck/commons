"""Fail-closed manifest contract for a caller-provided encrypted case vault.

This module does not claim to implement encryption.  It defines and verifies
the byte-integrity and separation rules that an encrypted local vault adapter
must satisfy before ChartTrace may use it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re


VAULT_CONTRACT_VERSION = "charttrace-vault-contract-v1"
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactKind(str, Enum):
    ORIGINAL = "ORIGINAL"
    DERIVATIVE = "DERIVATIVE"


@dataclass(frozen=True, slots=True)
class VaultArtifact:
    artifact_id: str
    case_id: str
    kind: ArtifactKind
    sha256: str
    byte_length: int
    source_sha256: str | None
    encryption_state: str
    read_only: bool

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.artifact_id) or not _ID_RE.fullmatch(self.case_id):
            raise ValueError("artifact_id and case_id must be stable non-sensitive identifiers")
        if not _SHA_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be lowercase SHA-256 hex")
        if self.byte_length < 0:
            raise ValueError("byte_length must not be negative")
        if self.encryption_state != "CALLER_VERIFIED_ENCRYPTED":
            raise ValueError("vault adapter must attest encrypted-at-rest state")
        if not self.read_only:
            raise ValueError("registered vault artifacts must be read-only")
        if self.kind is ArtifactKind.ORIGINAL and self.source_sha256 is not None:
            raise ValueError("an original cannot point to another source")
        if self.kind is ArtifactKind.DERIVATIVE:
            if self.source_sha256 is None or not _SHA_RE.fullmatch(self.source_sha256):
                raise ValueError("a derivative requires its original source SHA-256")
            if self.source_sha256 == self.sha256:
                raise ValueError("originals and derivatives must remain separate artifacts")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def exact_original_manifest(artifact_id: str, case_id: str, content: bytes) -> VaultArtifact:
    """Describe exact input bytes after the caller has encrypted the vault."""

    return VaultArtifact(
        artifact_id=artifact_id,
        case_id=case_id,
        kind=ArtifactKind.ORIGINAL,
        sha256=sha256_bytes(content),
        byte_length=len(content),
        source_sha256=None,
        encryption_state="CALLER_VERIFIED_ENCRYPTED",
        read_only=True,
    )


def derivative_manifest(
    artifact_id: str,
    case_id: str,
    content: bytes,
    source: VaultArtifact,
) -> VaultArtifact:
    if source.case_id != case_id or source.kind is not ArtifactKind.ORIGINAL:
        raise ValueError("derivative source must be an original from the same case")
    return VaultArtifact(
        artifact_id=artifact_id,
        case_id=case_id,
        kind=ArtifactKind.DERIVATIVE,
        sha256=sha256_bytes(content),
        byte_length=len(content),
        source_sha256=source.sha256,
        encryption_state="CALLER_VERIFIED_ENCRYPTED",
        read_only=True,
    )


def verify_exact_bytes(artifact: VaultArtifact, content: bytes) -> None:
    if len(content) != artifact.byte_length or sha256_bytes(content) != artifact.sha256:
        raise ValueError("vault bytes do not match the immutable artifact manifest")


def validate_case_manifest(artifacts: tuple[VaultArtifact, ...]) -> None:
    if not artifacts:
        raise ValueError("case manifest must not be empty")
    case_ids = {artifact.case_id for artifact in artifacts}
    artifact_ids = {artifact.artifact_id for artifact in artifacts}
    if len(case_ids) != 1:
        raise ValueError("a manifest cannot cross case boundaries")
    if len(artifact_ids) != len(artifacts):
        raise ValueError("artifact identifiers must be unique")
    original_hashes = {artifact.sha256 for artifact in artifacts if artifact.kind is ArtifactKind.ORIGINAL}
    for artifact in artifacts:
        if artifact.kind is ArtifactKind.DERIVATIVE and artifact.source_sha256 not in original_hashes:
            raise ValueError("derivative source is absent from the manifest")
