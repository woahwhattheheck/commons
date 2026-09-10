# SPDX-License-Identifier: Apache-2.0
"""Exact-source materializer for the bounded zero-exposure pressure repair."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any


EXPECTED_PARENT_GIT_BLOB_SHA1 = "7261674962d10fc8bc6af5ff73ff9212c40f61ad"
EXPECTED_MECHANICS_GIT_BLOB_SHA1 = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
SCHEMA = "titan-v3-pressure-zero-exposure-materialization/v1"

_IMPORT_OLD = "from sell_priority import PRODUCTS, _quote"
_IMPORT_NEW = _IMPORT_OLD + "\nfrom pressure_zero_exposure import stable_certified_partition"

_SIGNATURE_OLD = '''def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction,
              rival_supply: Mapping[str, int] | None = None) -> dict:'''
_SIGNATURE_NEW = '''def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction,
              rival_supply: Mapping[str, int] | None = None,
              zero_exposure_bound: int | None = None) -> dict:'''

_DOC_OLD = '''    Preserve all orders, quantities, duplicate lots, economic barriers,
    executable-prefix boundaries and unit instructions. Known empty slots can'''
_DOC_NEW = '''    ``zero_exposure_bound`` selects the fail-closed stable partition: exposed
    lots preserve parent order and may cross only lots whose own receipt is
    certified invariant for every hidden same-slot rival quantity through that
    externally justified bound. Invalid or non-monotone evidence is a barrier.

    Preserve all orders, quantities, duplicate lots, economic barriers,
    executable-prefix boundaries and unit instructions. Known empty slots can'''

_RANKING_OLD = '''        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])
        orders[start:stop] = [order for order, _ in ranked]'''
_RANKING_NEW = '''        if zero_exposure_bound is None:
            ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])
            orders[start:stop] = [order for order, _ in ranked]
        else:
            orders[start:stop], _certificates = stable_certified_partition(
                orders[start:stop], market, quote, zero_exposure_bound,
                max_units=MAX_SCORING_UNITS,
            )'''


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _replace_once(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{name} anchor count must be 1, got {count}")
    return source.replace(old, new, 1)


def patch_source(source: str) -> str:
    """Return a compiled postimage from the exact semantic anchors."""

    if not isinstance(source, str):
        raise TypeError("source must be text")
    patched = _replace_once(source, _IMPORT_OLD, _IMPORT_NEW, "import")
    patched = _replace_once(patched, _SIGNATURE_OLD, _SIGNATURE_NEW, "signature")
    patched = _replace_once(patched, _DOC_OLD, _DOC_NEW, "documentation")
    patched = _replace_once(patched, _RANKING_OLD, _RANKING_NEW, "ranking")
    ast.parse(patched, filename="pressure_priority.py")
    compile(patched, "pressure_priority.py", "exec")
    return patched


def _regular_file(path: Path, name: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"{name} cannot be statted") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{name} must be a regular non-symlink file")
    return info


def _strict_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize(
    source_path: Path,
    helper_path: Path,
    mechanics_path: Path,
    output_path: Path,
    receipt_path: Path,
    *,
    expected_parent_git_blob_sha1: str = EXPECTED_PARENT_GIT_BLOB_SHA1,
    expected_mechanics_git_blob_sha1: str = EXPECTED_MECHANICS_GIT_BLOB_SHA1,
) -> dict[str, Any]:
    """Verify, patch, atomically write, and read back one detached postimage."""

    source_path = Path(source_path)
    helper_path = Path(helper_path)
    mechanics_path = Path(mechanics_path)
    output_path = Path(output_path)
    receipt_path = Path(receipt_path)
    _regular_file(source_path, "source")
    _regular_file(helper_path, "helper")
    _regular_file(mechanics_path, "mechanics")

    for target, label in ((output_path, "output"), (receipt_path, "receipt")):
        if target.exists() or target.is_symlink():
            _regular_file(target, label)
            try:
                if (
                    os.path.samefile(source_path, target)
                    or os.path.samefile(helper_path, target)
                    or os.path.samefile(mechanics_path, target)
                ):
                    raise ValueError(f"{label} aliases an input file")
            except OSError as exc:
                raise ValueError(f"{label} alias check failed") from exc
    if output_path.resolve(strict=False) == receipt_path.resolve(strict=False):
        raise ValueError("output and receipt paths must differ")

    parent_bytes = source_path.read_bytes()
    actual_parent_blob = git_blob_sha1(parent_bytes)
    if actual_parent_blob != expected_parent_git_blob_sha1:
        raise ValueError(
            f"parent git blob drift: expected {expected_parent_git_blob_sha1}, "
            f"got {actual_parent_blob}"
        )
    try:
        parent_text = parent_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("parent source must be UTF-8") from exc

    helper_bytes = helper_path.read_bytes()
    try:
        helper_text = helper_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("helper source must be UTF-8") from exc
    ast.parse(helper_text, filename=helper_path.name)
    compile(helper_text, helper_path.name, "exec")

    mechanics_bytes = mechanics_path.read_bytes()
    actual_mechanics_blob = git_blob_sha1(mechanics_bytes)
    if actual_mechanics_blob != expected_mechanics_git_blob_sha1:
        raise ValueError(
            f"mechanics git blob drift: expected {expected_mechanics_git_blob_sha1}, "
            f"got {actual_mechanics_blob}"
        )
    try:
        mechanics_text = mechanics_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("mechanics source must be UTF-8") from exc
    ast.parse(mechanics_text, filename=mechanics_path.name)
    compile(mechanics_text, mechanics_path.name, "exec")
    if "def market_price(" not in mechanics_text:
        raise ValueError("mechanics source lacks market_price")

    patched = patch_source(parent_text)
    postimage = patched.encode("utf-8")
    receipt = {
        "schema": SCHEMA,
        "parent_git_blob_sha1": actual_parent_blob,
        "parent_sha256": hashlib.sha256(parent_bytes).hexdigest(),
        "helper_sha256": hashlib.sha256(helper_bytes).hexdigest(),
        "mechanics_git_blob_sha1": actual_mechanics_blob,
        "mechanics_sha256": hashlib.sha256(mechanics_bytes).hexdigest(),
        "postimage_git_blob_sha1": git_blob_sha1(postimage),
        "postimage_sha256": hashlib.sha256(postimage).hexdigest(),
        "parent_bytes": len(parent_bytes),
        "helper_bytes": len(helper_bytes),
        "mechanics_bytes": len(mechanics_bytes),
        "postimage_bytes": len(postimage),
        "anchors": {
            "import": 1,
            "signature": 1,
            "documentation": 1,
            "ranking": 1,
        },
        "default_behavior_preserved": True,
        "certificate_mode_default_off": True,
        "canonical_runtime_mutated": False,
    }
    receipt_bytes = _strict_json_bytes(receipt)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_paths: list[Path] = []
    try:
        for target, payload in ((output_path, postimage), (receipt_path, receipt_bytes)):
            handle = tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{target.name}.",
                dir=target.parent,
                delete=False,
            )
            temp = Path(handle.name)
            temporary_paths.append(temp)
            with handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
            temporary_paths.remove(temp)
    finally:
        for temp in temporary_paths:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    if output_path.read_bytes() != postimage:
        raise ValueError("postimage readback mismatch")
    parsed_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if parsed_receipt != receipt:
        raise ValueError("receipt readback mismatch")
    _regular_file(source_path, "source")
    _regular_file(helper_path, "helper")
    _regular_file(mechanics_path, "mechanics")
    if (
        source_path.read_bytes() != parent_bytes
        or helper_path.read_bytes() != helper_bytes
        or mechanics_path.read_bytes() != mechanics_bytes
    ):
        raise ValueError("an input changed during materialization")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--mechanics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(
        args.source, args.helper, args.mechanics, args.output, args.receipt
    )
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
