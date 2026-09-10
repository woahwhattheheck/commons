# SPDX-License-Identifier: Apache-2.0
"""Materialize current TITAN with an optional intent-first SELL priority factor.

The default-off arm extracts the exact current canonical archive without changing
one member.  The enabled arm changes exactly one source expression in
``scheduler.py``.  Target membership and quantities stay identical; only Python
mapping insertion order changes the first-wins traversal of equal-ranked SELL
candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any, Iterable, Mapping


EXPERIMENT = "titan-v3-current-intent-priority-integration-20260910-01"
FEATURE = "intent_first_sell_priority"
CANONICAL_BASE_HEAD = "98a98108998efac9e53a8b045f0fb2c85a4b19e2"
EXPECTED_ARCHIVE_SHA256 = (
    "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86"
)
EXPECTED_ARCHIVE_BYTES = 427_870
EXPECTED_RUNTIME_FILES = 109
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083"
)
EXPECTED_SCHEDULER_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"

OLD = (
    b"        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    b"if shed.get(p,0)>0}\n"
)
NEW = (
    b"        target_order={\n"
    b"            **{p:0 for p in self.pending if p in PRODUCTS},\n"
    b"            **{p:0 for p in baseline_q},\n"
    b"            **{p:0 for p in PRODUCTS},\n"
    b"        }\n"
    b"        targets={p:max(0,int(shed.get(p,0))) for p in target_order "
    b"if shed.get(p,0)>0}\n"
)


class MaterializeError(ValueError):
    """The canonical archive drifted or the one-factor boundary was violated."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
    temporary.replace(path)


def priority_targets(
    *,
    pending: Mapping[str, Any],
    baseline_q: Mapping[str, Any],
    products: Iterable[str],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    """Mirror the enabled target map and its first-insertion priority."""
    product_order = tuple(products)
    product_set = set(product_order)
    order: dict[str, None] = {}
    for product in pending:
        if product in product_set:
            order.setdefault(product, None)
    for product in baseline_q:
        if product in product_set:
            order.setdefault(product, None)
    for product in product_order:
        order.setdefault(product, None)
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in order
        if shed.get(product, 0) > 0
    }


def canonical_targets(
    *,
    products: Iterable[str],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    """Mirror current canonical target membership, quantity, and order."""
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in products
        if shed.get(product, 0) > 0
    }


def _member_name(member: tarfile.TarInfo) -> str:
    raw = member.name
    path = PurePosixPath(raw)
    if (
        not raw
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
        or "\\" in raw
    ):
        raise MaterializeError(f"unsafe archive member path: {raw!r}")
    return path.as_posix()


def read_archive(archive: Path) -> dict[str, bytes]:
    """Read a regular-file-only tarball with no path or link ambiguity."""
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise MaterializeError(f"canonical archive is not one regular file: {archive}")
    data = archive.read_bytes()
    if len(data) != EXPECTED_ARCHIVE_BYTES:
        raise MaterializeError(
            f"canonical archive size drifted: {len(data)} != {EXPECTED_ARCHIVE_BYTES}"
        )
    digest = sha256(data)
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise MaterializeError(
            f"canonical archive SHA-256 drifted: {digest}"
        )

    files: dict[str, bytes] = {}
    directories: set[str] = set()
    try:
        with tarfile.open(archive, mode="r:gz") as bundle:
            for member in bundle.getmembers():
                name = _member_name(member)
                if name in files or name in directories:
                    raise MaterializeError(f"duplicate archive member: {name}")
                if member.isdir():
                    directories.add(name)
                    continue
                if not member.isfile():
                    raise MaterializeError(
                        f"archive member is not a regular file/directory: {name}"
                    )
                stream = bundle.extractfile(member)
                if stream is None:
                    raise MaterializeError(f"cannot read archive member: {name}")
                files[name] = stream.read()
    except (tarfile.TarError, OSError) as exc:
        raise MaterializeError(f"cannot parse canonical archive: {exc}") from exc
    return files


def _verify_receipt(lab: Path, archive: Path) -> Mapping[str, Any]:
    receipt_path = lab / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise MaterializeError("current archive receipt is missing")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializeError(f"invalid current archive receipt: {exc}") from exc
    expected = {
        "path": "exports/titan-current.tar.gz",
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "sha256": EXPECTED_ARCHIVE_SHA256,
        "bytes": EXPECTED_ARCHIVE_BYTES,
        "runtime_files": EXPECTED_RUNTIME_FILES,
        "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
    }
    if receipt != expected:
        raise MaterializeError("current archive receipt drifted from pinned canonical")
    if archive.resolve() != (lab / expected["path"]).resolve():
        raise MaterializeError("archive path is detached from current receipt")
    return receipt


def _verify_source_manifest(files: Mapping[str, bytes]) -> Mapping[str, Any]:
    source_bytes = files.get("SOURCE.json")
    if source_bytes is None:
        raise MaterializeError("canonical archive is missing SOURCE.json")
    if sha256(source_bytes) != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise MaterializeError("archive SOURCE.json drifted from current receipt")
    try:
        source = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializeError(f"invalid archive SOURCE.json: {exc}") from exc
    runtime = source.get("runtime")
    if not isinstance(runtime, Mapping) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise MaterializeError("SOURCE.json runtime inventory cardinality drifted")
    expected_names = set(runtime) | {"SOURCE.json"}
    if set(files) != expected_names:
        missing = sorted(expected_names - set(files))
        extra = sorted(set(files) - expected_names)
        raise MaterializeError(
            f"archive/member manifest mismatch; missing={missing}, extra={extra}"
        )
    for name, raw in files.items():
        if name == "SOURCE.json":
            continue
        record = runtime.get(name)
        if not isinstance(record, Mapping):
            raise MaterializeError(f"manifest record is invalid: {name}")
        if record.get("bytes") != len(raw) or record.get("sha256") != sha256(raw):
            raise MaterializeError(f"manifest digest/size mismatch: {name}")
    scheduler = files.get("scheduler.py")
    if scheduler is None:
        raise MaterializeError("canonical archive is missing scheduler.py")
    if git_blob_sha1(scheduler) != EXPECTED_SCHEDULER_BLOB:
        raise MaterializeError("canonical scheduler Git blob drifted")
    if scheduler.count(OLD) != 1:
        raise MaterializeError(
            f"expected one canonical target expression, found {scheduler.count(OLD)}"
        )
    if scheduler.count(NEW) != 0:
        raise MaterializeError("intent-priority expression already exists in canonical")
    return source


def inventory_bytes(files: Mapping[str, bytes]) -> dict[str, dict[str, Any]]:
    return {
        name: {"sha256": sha256(raw), "bytes": len(raw)}
        for name, raw in sorted(files.items())
    }


def closure_sha256(inventory: Mapping[str, Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        inventory,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded)


def inventory_tree(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise MaterializeError(f"materialized tree contains symlink: {relative}")
        if path.is_file():
            raw = path.read_bytes()
            rows[relative.as_posix()] = {
                "sha256": sha256(raw),
                "bytes": len(raw),
            }
        elif not path.is_dir():
            raise MaterializeError(f"materialized tree contains special path: {relative}")
    return rows


def materialize(
    *,
    lab: Path,
    output: Path,
    integration_head: str,
    enabled: bool = False,
) -> dict[str, Any]:
    """Extract current canonical and optionally apply the one-factor patch."""
    lab = Path(lab).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise MaterializeError(f"output already exists: {output}")
    archive = lab / "exports/titan-current.tar.gz"
    archive_receipt = _verify_receipt(lab, archive)
    source_files = read_archive(archive)
    _verify_source_manifest(source_files)

    source_inventory = inventory_bytes(source_files)
    source_closure = closure_sha256(source_inventory)
    candidate_files = dict(source_files)
    if enabled:
        scheduler = candidate_files["scheduler.py"]
        patched = scheduler.replace(OLD, NEW, 1)
        try:
            compile(patched.decode("utf-8"), "scheduler.py", "exec")
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise MaterializeError(
                f"enabled scheduler does not compile: {exc}"
            ) from exc
        candidate_files["scheduler.py"] = patched

    candidate_inventory = inventory_bytes(candidate_files)
    changed = [
        name
        for name in sorted(source_inventory)
        if source_inventory[name] != candidate_inventory[name]
    ]
    expected_changed = ["scheduler.py"] if enabled else []
    if changed != expected_changed:
        raise MaterializeError(
            f"one-factor boundary violated: changed={changed!r}"
        )

    output.mkdir(parents=True)
    for name, raw in candidate_files.items():
        target = output / PurePosixPath(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(target, raw)

    disk_inventory = inventory_tree(output)
    if disk_inventory != candidate_inventory:
        raise MaterializeError("written tree is detached from in-memory materialization")

    source_scheduler = source_files["scheduler.py"]
    candidate_scheduler = candidate_files["scheduler.py"]
    receipt = {
        "schema_version": 1,
        "operation": EXPERIMENT,
        "experiment": EXPERIMENT,
        "integration_head": integration_head,
        "canonical_base_head": CANONICAL_BASE_HEAD,
        "feature": {
            "name": FEATURE,
            "enabled": bool(enabled),
            "default": False,
            "target_domain": (
                "all positive non-operating PRODUCTS in the post-unit shed"
            ),
            "target_quantity": "full post-unit shed quantity for every target",
            "control_priority": "PRODUCTS order",
            "enabled_priority": [
                "existing pending scheduler intent",
                "inherited baseline SELL first-seen order",
                "remaining PRODUCTS order",
            ],
            "selection_effect": (
                "first-wins priority under unchanged strict-greater rank comparison"
            ),
        },
        "source": {
            "archive_path": archive_receipt["path"],
            "archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "archive_bytes": EXPECTED_ARCHIVE_BYTES,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "runtime_files": EXPECTED_RUNTIME_FILES,
            "materialized_files": len(source_inventory),
            "closure_sha256": source_closure,
            "scheduler_git_blob_sha1": git_blob_sha1(source_scheduler),
            "scheduler_sha256": sha256(source_scheduler),
        },
        "candidate": {
            "changed_files": changed,
            "closure_sha256": closure_sha256(candidate_inventory),
            "scheduler_git_blob_sha1": git_blob_sha1(candidate_scheduler),
            "scheduler_sha256": sha256(candidate_scheduler),
            "old_occurrences_before": source_scheduler.count(OLD),
            "old_occurrences_after": candidate_scheduler.count(OLD),
            "new_occurrences_before": source_scheduler.count(NEW),
            "new_occurrences_after": candidate_scheduler.count(NEW),
        },
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--enable-intent-priority", action="store_true")
    args = parser.parse_args()

    try:
        receipt = materialize(
            lab=args.lab,
            output=args.output,
            integration_head=args.head,
            enabled=args.enable_intent_priority,
        )
    except (MaterializeError, OSError, ValueError) as exc:
        parser.error(str(exc))
    atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "experiment": receipt["experiment"],
                "enabled": receipt["feature"]["enabled"],
                "changed_files": receipt["candidate"]["changed_files"],
                "source_closure": receipt["source"]["closure_sha256"],
                "candidate_closure": receipt["candidate"]["closure_sha256"],
                "source_scheduler": receipt["source"][
                    "scheduler_git_blob_sha1"
                ],
                "candidate_scheduler": receipt["candidate"][
                    "scheduler_git_blob_sha1"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
