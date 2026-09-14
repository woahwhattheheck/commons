from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from core_common import ValidationError, loads_strict, sha256_bytes, _exact_keys

def verify_bundle(bundle: bytes) -> dict[str, Any]:
    if len(bundle) > 5_000_000:
        raise ValidationError("bundle exceeds 5,000,000 bytes")
    try:
        with zipfile.ZipFile(io.BytesIO(bundle), "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != sorted(names) or len(names) != len(set(names)):
                raise ValidationError("bundle members must be sorted and unique")
            required = {"manifest.json", "plan.json", "shopping-list.csv", "summary.md"}
            if set(names) != required:
                raise ValidationError("bundle member set is invalid")
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise ValidationError("unsafe bundle path")
            if any(info.is_dir() or (info.flag_bits & 0x1) for info in infos):
                raise ValidationError("directories and encrypted ZIP members are forbidden")
            if any(info.file_size > 5_000_000 for info in infos) or sum(info.file_size for info in infos) > 5_000_000:
                raise ValidationError("uncompressed bundle exceeds 5,000,000 bytes")
            content = {name: archive.read(name) for name in names}
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValidationError("invalid ZIP bundle") from exc
    manifest = loads_strict(content["manifest.json"])
    manifest = _exact_keys(manifest, "manifest", {"schema", "plan_id", "plan_revision", "workspace_revision", "files", "authority"}, {"schema", "plan_id", "plan_revision", "workspace_revision", "files", "authority"})
    if manifest["schema"] != "creator-niche-export-manifest/v1":
        raise ValidationError("unsupported manifest schema")
    expected_manifest_files = {"plan.json", "shopping-list.csv", "summary.md"}
    if not isinstance(manifest["files"], dict) or set(manifest["files"]) != expected_manifest_files:
        raise ValidationError("manifest file membership is invalid")
    for name in sorted(expected_manifest_files):
        row = manifest["files"].get(name)
        if (
            not isinstance(row, dict)
            or set(row) != {"sha256", "bytes"}
            or row.get("sha256") != sha256_bytes(content[name])
            or row.get("bytes") != len(content[name])
        ):
            raise ValidationError(f"bundle digest mismatch: {name}")
    authority = manifest["authority"]
    expected_authority = {
        "outbound_authorized",
        "provider_mutation_authorized",
        "payment_authorized",
        "revenue_recognized",
    }
    if not isinstance(authority, dict) or set(authority) != expected_authority or any(authority.values()):
        raise ValidationError("bundle authority must remain exact and false")
    plan_packet = loads_strict(content["plan.json"])
    if plan_packet.get("authority") != authority:
        raise ValidationError("plan authority does not match manifest")
    return {
        "status": "VERIFIED",
        "bundle_sha256": sha256_bytes(bundle),
        "plan_id": manifest["plan_id"],
        "plan_revision": manifest["plan_revision"],
        "workspace_revision": manifest["workspace_revision"],
    }
