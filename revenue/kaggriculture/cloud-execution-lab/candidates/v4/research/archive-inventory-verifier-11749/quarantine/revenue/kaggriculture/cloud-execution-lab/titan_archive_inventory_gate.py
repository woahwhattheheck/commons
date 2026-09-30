#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail closed when TITAN's canonical tar receipt disagrees with its bytes.

The archive is snapshotted exactly once and never extracted.  The established
release contract counts regular runtime members separately from the one root
``SOURCE.json`` provenance manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any, Mapping, Sequence

DEFAULT_RECEIPT = Path("runtime/integrated-selected/CURRENT-ARCHIVE.json")
REQUIRED = (
    "path",
    "entrypoint",
    "sha256",
    "bytes",
    "runtime_files",
    "source_manifest",
    "source_manifest_sha256",
)
MAX_EMBEDDED_SOURCE_BYTES = 16 * 1024 * 1024


class GateError(ValueError):
    pass


def issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code, "message": message}
    if details:
        row["details"] = details
    return row


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=no_duplicate_object,
        )
    except FileNotFoundError as exc:
        raise GateError(f"missing receipt: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read receipt {path}: {exc}") from exc


def archive_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GateError("archive receipt must be a JSON object")
    for key in ("candidate_archive", "current_archive", "archive_receipt"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            return dict(nested)
    return dict(value)


def nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GateError(f"{field} must be a nonnegative integer")
    return value


def digest_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise GateError(f"{field} must be a 64-character SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise GateError(f"{field} must be hexadecimal") from exc
    return value.lower()


def normalize_name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise GateError(f"{field} must be a nonempty NUL-free string")
    if "\\" in value:
        raise GateError(f"{field} uses a backslash path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise GateError(f"{field} escapes the archive root: {value!r}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise GateError(f"{field} has no usable relative path: {value!r}")
    return normalized


def validate_receipt(value: Any) -> dict[str, Any]:
    receipt = archive_record(value)
    missing = [field for field in REQUIRED if field not in receipt]
    if missing:
        raise GateError(f"archive receipt omits required fields: {missing}")
    receipt["path"] = normalize_name(receipt["path"], "path")
    receipt["source_manifest"] = normalize_name(
        receipt["source_manifest"], "source_manifest"
    )
    if not isinstance(receipt["entrypoint"], str) or not receipt["entrypoint"].strip():
        raise GateError("entrypoint must be a nonempty string")
    receipt["sha256"] = digest_text(receipt["sha256"], "sha256")
    receipt["source_manifest_sha256"] = digest_text(
        receipt["source_manifest_sha256"], "source_manifest_sha256"
    )
    receipt["bytes"] = nonnegative_int(receipt["bytes"], "bytes")
    receipt["runtime_files"] = nonnegative_int(
        receipt["runtime_files"], "runtime_files"
    )
    return receipt


def fingerprint(names: list[str]) -> str:
    payload = b"\x00".join(name.encode("utf-8") for name in sorted(names))
    return hashlib.sha256(payload).hexdigest()


def inspect_archive(
    root: str | Path,
    receipt_rel: str | Path = DEFAULT_RECEIPT,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = Path(receipt_rel)
    if not receipt_path.is_absolute():
        receipt_path = root_path / receipt_path
    receipt = validate_receipt(load_json(receipt_path))
    archive_path = root_path / receipt["path"]
    external_source_path = root_path / receipt["source_manifest"]
    blockers: list[dict[str, Any]] = []

    try:
        archive_data = archive_path.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        return {
            "schema_version": 2,
            "verdict": "BLOCKED",
            "root": str(root_path),
            "receipt_path": str(receipt_path),
            "receipt": receipt,
            "blockers": [
                issue("ARCHIVE_MISSING", "cannot read canonical archive", error=str(exc))
            ],
        }

    actual_sha = hashlib.sha256(archive_data).hexdigest()
    if actual_sha != receipt["sha256"]:
        blockers.append(issue(
            "ARCHIVE_HASH_MISMATCH",
            "archive bytes do not match the receipt SHA-256",
            expected=receipt["sha256"],
            actual=actual_sha,
        ))
    if len(archive_data) != receipt["bytes"]:
        blockers.append(issue(
            "ARCHIVE_SIZE_MISMATCH",
            "archive byte length does not match the receipt",
            expected=receipt["bytes"],
            actual=len(archive_data),
        ))

    try:
        external_source = external_source_path.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        external_source = None
        blockers.append(issue(
            "EXTERNAL_SOURCE_MISSING",
            "cannot read the external source manifest",
            path=str(external_source_path),
            error=str(exc),
        ))
    else:
        external_sha = hashlib.sha256(external_source).hexdigest()
        if external_sha != receipt["source_manifest_sha256"]:
            blockers.append(issue(
                "EXTERNAL_SOURCE_HASH_MISMATCH",
                "external source manifest does not match the receipt",
                expected=receipt["source_manifest_sha256"],
                actual=external_sha,
            ))

    try:
        archive = tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:*")
    except (tarfile.TarError, EOFError, OSError) as exc:
        blockers.append(issue(
            "ARCHIVE_UNREADABLE",
            "canonical archive is not a readable tar payload",
            error=str(exc),
        ))
        return {
            "schema_version": 2,
            "verdict": "BLOCKED",
            "root": str(root_path),
            "receipt_path": str(receipt_path),
            "receipt": receipt,
            "actual": {"sha256": actual_sha, "bytes": len(archive_data)},
            "blockers": blockers,
        }

    seen: dict[str, str] = {}
    regular_names: list[str] = []
    source_headers = 0
    embedded_source: bytes | None = None
    try:
        members = archive.getmembers()
        for index, member in enumerate(members):
            raw = member.name
            if member.isdir() and PurePosixPath(raw).as_posix() in {"", "."}:
                continue
            try:
                normalized = normalize_name(raw, f"member[{index}]")
            except GateError as exc:
                blockers.append(issue(
                    "UNSAFE_ARCHIVE_PATH", str(exc), member=raw, index=index
                ))
                continue

            if member.isfile() and normalized == "SOURCE.json":
                source_headers += 1
            if normalized in seen:
                blockers.append(issue(
                    "DUPLICATE_ARCHIVE_PATH",
                    "multiple headers normalize to the same path",
                    normalized=normalized,
                    first=seen[normalized],
                    duplicate=raw,
                ))
                continue
            seen[normalized] = raw

            if member.isfile():
                regular_names.append(normalized)
                if normalized == "SOURCE.json":
                    if member.size > MAX_EMBEDDED_SOURCE_BYTES:
                        blockers.append(issue(
                            "EMBEDDED_SOURCE_TOO_LARGE",
                            "embedded SOURCE.json exceeds the audit limit",
                            bytes=member.size,
                            limit=MAX_EMBEDDED_SOURCE_BYTES,
                        ))
                    else:
                        stream = archive.extractfile(member)
                        if stream is None:
                            blockers.append(issue(
                                "EMBEDDED_SOURCE_UNREADABLE",
                                "tar reader could not open root SOURCE.json",
                            ))
                        else:
                            embedded_source = stream.read(
                                MAX_EMBEDDED_SOURCE_BYTES + 1
                            )
            elif not member.isdir():
                blockers.append(issue(
                    "UNSAFE_ARCHIVE_MEMBER_TYPE",
                    "runtime archive may contain only regular files and directories",
                    member=raw,
                    type=repr(member.type),
                    linkname=member.linkname or None,
                ))
    finally:
        archive.close()

    if source_headers != 1:
        blockers.append(issue(
            "SOURCE_MANIFEST_CARDINALITY",
            "archive must contain exactly one regular root SOURCE.json",
            actual=source_headers,
        ))

    if embedded_source is not None:
        embedded_sha = hashlib.sha256(embedded_source).hexdigest()
        if embedded_sha != receipt["source_manifest_sha256"]:
            blockers.append(issue(
                "EMBEDDED_SOURCE_HASH_MISMATCH",
                "embedded SOURCE.json does not match the receipt",
                expected=receipt["source_manifest_sha256"],
                actual=embedded_sha,
            ))
        if external_source is not None and embedded_source != external_source:
            blockers.append(issue(
                "EMBEDDED_EXTERNAL_SOURCE_MISMATCH",
                "embedded and external source manifests differ byte-for-byte",
            ))

    runtime_names = [name for name in regular_names if name != "SOURCE.json"]
    if len(runtime_names) != receipt["runtime_files"]:
        blockers.append(issue(
            "RUNTIME_MEMBER_COUNT_MISMATCH",
            "non-SOURCE regular member count does not match runtime_files",
            expected=receipt["runtime_files"],
            actual=len(runtime_names),
            regular_files=len(regular_names),
        ))

    entry_file = normalize_name(
        receipt["entrypoint"].split("::", 1)[0].strip(), "entrypoint file"
    )
    if entry_file not in set(runtime_names):
        blockers.append(issue(
            "ENTRYPOINT_MEMBER_MISSING",
            "declared entrypoint file is absent from the runtime members",
            entrypoint=receipt["entrypoint"],
            expected_member=entry_file,
        ))

    return {
        "schema_version": 2,
        "verdict": "PASS" if not blockers else "BLOCKED",
        "root": str(root_path),
        "receipt_path": str(receipt_path),
        "receipt": receipt,
        "count_contract": "runtime_files excludes the one regular root SOURCE.json",
        "actual": {
            "sha256": actual_sha,
            "bytes": len(archive_data),
            "members": len(members),
            "regular_files": len(regular_names),
            "runtime_files": len(runtime_names),
            "embedded_source_files": source_headers,
            "regular_names_sha256": fingerprint(regular_names),
            "runtime_names_sha256": fingerprint(runtime_names),
            "entrypoint_member": entry_file,
        },
        "blockers": blockers,
    }


def write_report(report: Mapping[str, Any], target: str | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if target:
        Path(target).write_text(text, encoding="utf-8")
    print(text, end="")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    parser.add_argument("--report-json")
    args = parser.parse_args(argv)
    try:
        report = inspect_archive(args.root, args.receipt)
    except GateError as exc:
        report = {"schema_version": 2, "verdict": "REFUSED", "error": str(exc)}
        write_report(report, args.report_json)
        return 4
    write_report(report, args.report_json)
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
