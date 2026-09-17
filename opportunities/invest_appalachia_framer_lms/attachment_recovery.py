from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from pathlib import PurePosixPath
from typing import Any

SOURCE_URL = "https://investappalachia.org/wp-content/uploads/2026/08/Zipped-RFP-Docs.zip"
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_MEMBER_BYTES = 25 * 1024 * 1024
EXPECTED_LABELS = ("A", "B", "C", "D")
_RETRIEVED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ATTACHMENT = re.compile(r"(?:^|[^a-z0-9])attachment[\s._-]*([a-d])(?:[^a-z0-9]|$)", re.I)
_LEADING = re.compile(r"^([a-d])(?:[\s._-]+)", re.I)


class AttachmentRecoveryError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise AttachmentRecoveryError("member name must be non-empty text without NUL")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AttachmentRecoveryError(f"unsafe ZIP member path: {name!r}")
    return normalized


def _attachment_label(name: str) -> str | None:
    base = PurePosixPath(name).name
    stem = base.rsplit(".", 1)[0]
    match = _ATTACHMENT.search(stem) or _LEADING.match(stem)
    return match.group(1).upper() if match else None


def analyze_zip(data: bytes, *, retrieved_at_utc: str, source_url: str = SOURCE_URL) -> dict[str, Any]:
    if not isinstance(data, (bytes, bytearray)):
        raise AttachmentRecoveryError("ZIP payload must be bytes")
    data = bytes(data)
    if not data:
        raise AttachmentRecoveryError("ZIP payload is empty")
    if len(data) > MAX_ZIP_BYTES:
        raise AttachmentRecoveryError("ZIP payload exceeds bounded size")
    if source_url != SOURCE_URL:
        raise AttachmentRecoveryError("source URL must remain bound to the official buyer ZIP")
    if not isinstance(retrieved_at_utc, str) or not _RETRIEVED_AT.fullmatch(retrieved_at_utc):
        raise AttachmentRecoveryError("retrieved_at_utc must be exact UTC YYYY-MM-DDTHH:MM:SSZ")

    members: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    unexpected: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = _safe_name(info.filename)
                if info.file_size > MAX_MEMBER_BYTES:
                    raise AttachmentRecoveryError(f"member exceeds bounded size: {name}")
                payload = archive.read(info)
                if len(payload) != info.file_size:
                    raise AttachmentRecoveryError(f"member size mismatch: {name}")
                label = _attachment_label(name)
                members.append({
                    "name": name,
                    "attachment_label": label,
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "sha256": _sha256(payload),
                })
                if label is None:
                    unexpected.append(name)
                elif label in labels:
                    raise AttachmentRecoveryError(
                        f"duplicate attachment label {label}: {labels[label]!r} and {name!r}"
                    )
                else:
                    labels[label] = name
    except AttachmentRecoveryError:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError) as exc:
        raise AttachmentRecoveryError(f"invalid ZIP payload: {exc}") from exc

    found = tuple(sorted(labels))
    missing = [label for label in EXPECTED_LABELS if label not in labels]
    extra_labels = [label for label in labels if label not in EXPECTED_LABELS]
    exact = not missing and not extra_labels and not unexpected and len(members) == len(EXPECTED_LABELS)
    status = "RECOVERED_EXACT_A_D_UNREVIEWED" if exact else "RECOVERED_MEMBER_SET_HOLD"

    receipt: dict[str, Any] = {
        "schema": "invest_appalachia_framer_lms.attachment_recovery_receipt.v1",
        "source_url": SOURCE_URL,
        "retrieved_at_utc": retrieved_at_utc,
        "zip_sha256": _sha256(data),
        "zip_size_bytes": len(data),
        "members": sorted(members, key=lambda item: item["name"]),
        "attachment_labels_found": list(found),
        "missing_attachment_labels": missing,
        "unexpected_members": sorted(unexpected),
        "member_set_status": status,
        "attachments_complete_authorized": False,
        "qualification_or_budget_promotion_authorized": False,
        "external_contact_or_submission_authorized": False,
    }
    canonical = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_sha256"] = _sha256(canonical)
    return receipt


def fetch_official_zip(*, timeout_seconds: float = 30.0) -> bytes:
    if timeout_seconds <= 0:
        raise AttachmentRecoveryError("timeout_seconds must be positive")
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "TJLabs-Invest-Appalachia-Attachment-Recovery/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if final_url != SOURCE_URL:
                raise AttachmentRecoveryError(f"unexpected redirect target: {final_url}")
            data = response.read(MAX_ZIP_BYTES + 1)
    except AttachmentRecoveryError:
        raise
    except Exception as exc:
        raise AttachmentRecoveryError(f"official ZIP fetch failed: {exc}") from exc
    if len(data) > MAX_ZIP_BYTES:
        raise AttachmentRecoveryError("ZIP payload exceeds bounded size")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recover and verify Invest Appalachia Framer LMS attachment ZIP")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--zip", dest="zip_path", help="analyze already-retained official ZIP bytes")
    source.add_argument("--fetch", action="store_true", help="fetch the exact official buyer ZIP URL")
    parser.add_argument("--retrieved-at-utc", required=True, help="exact UTC timestamp, e.g. 2026-09-17T07:00:00Z")
    parser.add_argument("--output", help="optional JSON receipt path")
    args = parser.parse_args(argv)

    if args.fetch:
        data = fetch_official_zip()
    else:
        try:
            with open(args.zip_path, "rb") as handle:
                data = handle.read(MAX_ZIP_BYTES + 1)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot read ZIP: {exc}") from exc

    receipt = analyze_zip(data, retrieved_at_utc=args.retrieved_at_utc)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot write receipt: {exc}") from exc
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
