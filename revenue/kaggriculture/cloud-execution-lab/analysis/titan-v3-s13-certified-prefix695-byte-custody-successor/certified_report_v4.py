#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Single-read byte-custody successor for the S13 provenance report.

The reviewed v3 report authenticates provenance but reopens evaluator paths between
hashing, validation, and inherited v2 score/verdict math. This wrapper pins that
reviewed v3 source and supplies immutable path-shaped snapshots so every consumer
sees the exact bytes captured by the sole filesystem read of each evaluator file.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-certified-prefix-report/v4"
V3_BLOB = "a9e4be0c5e67f56fd1ceda6baf2d82b5000e6d3a"
HERE = Path(__file__).resolve().parent
V3_PATH = (
    HERE.parent
    / "titan-v3-s13-certified-prefix695-provenance-successor"
    / "certified_report_v3.py"
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_v3():
    data = V3_PATH.read_bytes()
    actual = git_blob_sha(data)
    if actual != V3_BLOB:
        raise RuntimeError(f"v3 report blob drift: expected={V3_BLOB} actual={actual}")
    name = "titan_s13_certified_report_v3"
    spec = importlib.util.spec_from_file_location(name, V3_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {V3_PATH}")
    module = importlib.util.module_from_spec(spec)
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
    return module


v3 = load_v3()
CertifiedReportError = v3.CertifiedReportError


class CapturedJsonPath:
    """Immutable JSON bytes retaining the original path only for diagnostics."""

    __slots__ = ("_path", "_data")

    def __init__(self, path: Path, data: bytes):
        self._path = path
        self._data = data

    @classmethod
    def capture(cls, path: Path) -> "CapturedJsonPath":
        path = Path(path)
        return cls(path, path.read_bytes())

    @property
    def data(self) -> bytes:
        return self._data

    def read_bytes(self) -> bytes:
        return self._data

    def read_text(self, encoding: str = "utf-8") -> str:
        return self._data.decode(encoding)

    def __str__(self) -> str:
        return str(self._path)

    def __fspath__(self) -> str:
        return str(self._path)


def _capture_inputs(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
) -> dict[str, CapturedJsonPath]:
    # These are the only filesystem reads of the three evaluator reports.
    return {
        "control": CapturedJsonPath.capture(control_path),
        "unsafe_prefix": CapturedJsonPath.capture(unsafe_path),
        "certified_prefix": CapturedJsonPath.capture(certified_path),
    }


def build_report(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    source_seat: int,
    identities: Mapping[str, str],
    bindings: Mapping[str, Path],
) -> dict[str, Any]:
    captured = _capture_inputs(control_path, unsafe_path, certified_path)
    report = v3.build_report(
        captured["control"],
        captured["unsafe_prefix"],
        captured["certified_prefix"],
        source_seat=source_seat,
        identities=identities,
        bindings=bindings,
    )

    custody: dict[str, Any] = {}
    for label, snapshot in captured.items():
        expected_sha = v3.sha256_bytes(snapshot.data)
        expected_bytes = len(snapshot.data)
        receipt = report["input_reports"][label]
        if receipt.get("sha256") != expected_sha or receipt.get("bytes") != expected_bytes:
            raise CertifiedReportError(
                f"{label} immutable input receipt disagrees with captured bytes"
            )
        custody[label] = {"bytes": expected_bytes, "sha256": expected_sha}

    result = dict(report)
    result["schema"] = SCHEMA
    result["byte_custody"] = {
        "mode": "single-read-immutable-snapshot",
        "inputs": custody,
    }
    result["scope"] = (
        "reused frozen seeds only; evaluator files are read once and the same immutable "
        "bytes feed hashing, provenance validation, activation validation, and inherited "
        "v2 score/verdict math; no promotion, provider, Kaggle, or submission mutation"
    )
    return result


def markdown(report: Mapping[str, Any]) -> str:
    base = v3.markdown(report).rstrip()
    return "\n".join(
        [
            base,
            "",
            "## Byte custody",
            "",
            "- Evaluator input mode: `single-read-immutable-snapshot`",
            "- Hashing, provenance checks, activation checks, and inherited v2 math consume the same captured bytes.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--unsafe-prefix", type=Path, required=True)
    parser.add_argument("--certified-prefix", type=Path, required=True)
    parser.add_argument("--source-seat", type=int, required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--binding", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.control,
        args.unsafe_prefix,
        args.certified_prefix,
        source_seat=args.source_seat,
        identities={
            "git_head": args.git_head,
            "archive_sha256": args.archive_sha256,
            "source_manifest_sha256": args.source_manifest_sha256,
        },
        bindings=v3._parse_bindings(args.binding),
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
