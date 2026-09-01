"""Immutable recipient-specific .ctpkg builder.

Changed bytes or wrong recipient fail closed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from charttrace.export.packet import ExportPacket


class CtpkgBuildError(ValueError):
    """Fail-closed package construction or verification error."""


def _canonical_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class CtpkgPackage:
    recipient_id: str
    release_version: str
    payload: Dict[str, Any]
    package_hash: str
    signature_state: str  # UNSIGNED_SYNTHETIC | SIGNED | INVALID
    schema_version: str = "charttrace.ctpkg.v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipient_id": self.recipient_id,
            "release_version": self.release_version,
            "package_hash": self.package_hash,
            "signature_state": self.signature_state,
            "payload": self.payload,
        }


def build_ctpkg(
    export: ExportPacket,
    *,
    signature_state: str = "UNSIGNED_SYNTHETIC",
) -> CtpkgPackage:
    if not export.recipient_id:
        raise CtpkgBuildError("recipient_id required")
    if signature_state not in ("UNSIGNED_SYNTHETIC", "SIGNED"):
        raise CtpkgBuildError(f"Unknown signature_state: {signature_state}")

    sealed_payload = {
        "reviewed_tables": export.reviewed_tables,
        "weak_appendix": export.weak_appendix,
        "source_manifest": export.source_manifest,
        "source_hashes": [s.get("sha256") for s in export.source_manifest],
        "citation_index": export.citation_index,
        "json": export.json_rows,
        "csv": export.csv_rows,
        "grounding_versions": export.grounding_versions,
        "peer_review_release_manifest": export.peer_review_release_manifest,
        "sections": export.sections,
        "section_order": list(export.section_order()),
        "recipient_id": export.recipient_id,
        "release_version": export.release_version,
        "export_schema_version": export.schema_version,
    }

    body = {
        "schema_version": "charttrace.ctpkg.v1",
        "recipient_id": export.recipient_id,
        "release_version": export.release_version,
        "payload": sealed_payload,
        "signature_state": signature_state,
    }
    package_hash = _sha256(_canonical_bytes(body))
    return CtpkgPackage(
        recipient_id=export.recipient_id,
        release_version=export.release_version,
        payload=sealed_payload,
        package_hash=package_hash,
        signature_state=signature_state,
    )


def verify_ctpkg(
    package: CtpkgPackage,
    *,
    expected_recipient_id: str,
    expected_hash: Optional[str] = None,
) -> None:
    if package.recipient_id != expected_recipient_id:
        raise CtpkgBuildError(
            f"Wrong recipient: package={package.recipient_id} expected={expected_recipient_id}"
        )
    body = {
        "schema_version": package.schema_version,
        "recipient_id": package.recipient_id,
        "release_version": package.release_version,
        "payload": package.payload,
        "signature_state": package.signature_state,
    }
    recomputed = _sha256(_canonical_bytes(body))
    if recomputed != package.package_hash:
        raise CtpkgBuildError("Package hash mismatch — changed bytes fail closed")
    if expected_hash is not None and expected_hash != package.package_hash:
        raise CtpkgBuildError("Package hash does not match expected release hash")


def mutate_payload_bytes(package: CtpkgPackage, path: str, value: Any) -> CtpkgPackage:
    """Test helper: produce a tampered package retaining the old hash (should fail verify)."""
    payload = copy.deepcopy(package.payload)
    cursor: Any = payload
    parts = path.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value
    return CtpkgPackage(
        recipient_id=package.recipient_id,
        release_version=package.release_version,
        payload=payload,
        package_hash=package.package_hash,  # intentionally stale
        signature_state=package.signature_state,
        schema_version=package.schema_version,
    )
