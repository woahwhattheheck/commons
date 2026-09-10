# SPDX-License-Identifier: Apache-2.0
"""Materialize and bind the current TITAN intent-priority reachability arms.

The live canonical configuration selects ``FrozenSelected``.  A scheduler-only
patch is therefore a predecessor arm, not a live candidate.  This module builds
three disjoint closures without mutating the checked-in archive:

* control: exact current archive;
* scheduler_only: historical patch applied only to ``scheduler.py``;
* frozen_priority: the same one-factor traversal patch applied to the live
  ``frozen_selected.py`` consumer.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile
from typing import Any, Iterable, Mapping

EXPERIMENT = "titan-v3-intent-priority-frozen-reachability-20260910-01"
EXPECTED_ARCHIVE_SHA256 = (
    "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
)
EXPECTED_ARCHIVE_BYTES = 428_158
EXPECTED_SOURCE_SHA256 = (
    "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
)
EXPECTED_RUNTIME_FILES = 109
EXPECTED_MAIN_SHA256 = (
    "c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1"
)
EXPECTED_TITAN_RUNTIME_SHA256 = (
    "da391af2dbdec0f6e4a25749ed539cdd39578ace8861c0e225b5fbfef90d75a8"
)
EXPECTED_FROZEN_SHA256 = (
    "5ca1bc39efed756de71207f46926744ea69f9d2f300dd7b9c1a8cc4dbefeb9ef"
)
EXPECTED_SCHEDULER_SHA256 = (
    "00d72a5c6b511e73ed1923ea402c4a36e0f9490f3b4c177490ddc72440f4a64a"
)
EXPECTED_CONFIG_SHA256 = (
    "6096a8f120d79aa1e9fae1aab64e2135de483fb11961ab5062708f7dc9c92b12"
)
EXPECTED_PATCHED_FROZEN_SHA256 = (
    "211bd8057e9b9b42797630dde210a7e63b579509048cebcbbd5a11b23a7300ca"
)
EXPECTED_PATCHED_SCHEDULER_SHA256 = (
    "04e48a466131ce9fe3824e3f18083f90c5fa0b5d98d2d5720d35dc0c11a4406d"
)
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024

OLD = (
    "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}\n"
)
NEW = (
    "        target_order={\n"
    "            **{p:0 for p in self.pending if p in PRODUCTS},\n"
    "            **{p:0 for p in baseline_q},\n"
    "            **{p:0 for p in PRODUCTS},\n"
    "        }\n"
    "        targets={p:max(0,int(shed.get(p,0))) for p in target_order "
    "if shed.get(p,0)>0}\n"
)


class ReachabilityError(ValueError):
    """The archive, call path, patch seam, or closure failed exact validation."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    def pairs(items):
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ReachabilityError(f"duplicate key {key!r} in {label}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data,
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ReachabilityError(f"non-finite token {token!r} in {label}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReachabilityError(f"invalid strict JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReachabilityError(f"{label} must be one object")
    return value


def _parts(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ReachabilityError("invalid archive member name")
    path = PurePosixPath(name)
    parts = path.parts
    if path.is_absolute() or not parts or any(p in ("", ".", "..") for p in parts):
        raise ReachabilityError(f"unsafe archive member {name!r}")
    if PurePosixPath(*parts).as_posix() != name:
        raise ReachabilityError(f"noncanonical archive member {name!r}")
    return tuple(parts)


def _read_archive(archive: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    archive = archive.resolve()
    if not archive.is_file() or archive.is_symlink():
        raise ReachabilityError(f"archive is not one regular file: {archive}")
    raw = archive.read_bytes()
    if len(raw) != EXPECTED_ARCHIVE_BYTES:
        raise ReachabilityError(
            f"archive byte drift: expected {EXPECTED_ARCHIVE_BYTES}, got {len(raw)}"
        )
    if sha256(raw) != EXPECTED_ARCHIVE_SHA256:
        raise ReachabilityError("archive SHA-256 drift")

    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as bundle:
            for member in bundle:
                if not member.isfile():
                    raise ReachabilityError(
                        f"non-regular archive member {member.name!r}"
                    )
                _parts(member.name)
                if member.name in members:
                    raise ReachabilityError(f"duplicate archive member {member.name!r}")
                if type(member.size) is not int or not 0 <= member.size <= MAX_MEMBER_BYTES:
                    raise ReachabilityError(
                        f"rejected archive size for {member.name!r}: {member.size!r}"
                    )
                stream = bundle.extractfile(member)
                if stream is None:
                    raise ReachabilityError(f"cannot read {member.name!r}")
                data = stream.read(member.size + 1)
                if len(data) != member.size:
                    raise ReachabilityError(f"length mismatch for {member.name!r}")
                total += len(data)
                if total > MAX_TOTAL_BYTES:
                    raise ReachabilityError("archive exceeds materialization ceiling")
                members[member.name] = data
    except tarfile.TarError as exc:
        raise ReachabilityError(f"invalid gzip tar: {exc}") from exc

    if len(members) != EXPECTED_RUNTIME_FILES + 1:
        raise ReachabilityError(
            f"member cardinality drift: expected {EXPECTED_RUNTIME_FILES + 1}, "
            f"got {len(members)}"
        )
    source = members.get("SOURCE.json")
    if source is None or sha256(source) != EXPECTED_SOURCE_SHA256:
        raise ReachabilityError("SOURCE.json identity drift")
    manifest = _strict_json(source, "SOURCE.json")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise ReachabilityError("runtime manifest cardinality drift")
    expected_names = set(runtime) | {"SOURCE.json"}
    if set(members) != expected_names:
        raise ReachabilityError("archive members do not match SOURCE.json")
    for name, record in runtime.items():
        _parts(name)
        if not isinstance(record, dict):
            raise ReachabilityError(f"invalid manifest record for {name}")
        data = members[name]
        if record.get("bytes") != len(data) or record.get("sha256") != sha256(data):
            raise ReachabilityError(f"manifest identity drift for {name}")

    required = {
        "main.py": EXPECTED_MAIN_SHA256,
        "titan_runtime.py": EXPECTED_TITAN_RUNTIME_SHA256,
        "frozen_selected.py": EXPECTED_FROZEN_SHA256,
        "scheduler.py": EXPECTED_SCHEDULER_SHA256,
        "TITAN-CONFIG.json": EXPECTED_CONFIG_SHA256,
    }
    for name, digest in required.items():
        if sha256(members.get(name, b"")) != digest:
            raise ReachabilityError(f"current source identity drift for {name}")
    return members, manifest


def priority_targets(
    products: Iterable[str],
    pending: Mapping[str, Any],
    baseline_q: Mapping[str, Any],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    """Return unchanged positive-shed membership/quantities in priority order."""
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


def control_targets(products: Iterable[str], shed: Mapping[str, Any]) -> dict[str, int]:
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in products
        if shed.get(product, 0) > 0
    }


def _bind_live_path(members: Mapping[str, bytes]) -> dict[str, Any]:
    config = _strict_json(members["TITAN-CONFIG.json"], "TITAN-CONFIG.json")
    if config.get("consumer") != "frozen":
        raise ReachabilityError(
            f"live consumer drift: expected 'frozen', got {config.get('consumer')!r}"
        )
    main = members["main.py"].decode("utf-8")
    runtime = members["titan_runtime.py"].decode("utf-8")
    frozen = members["frozen_selected.py"].decode("utf-8")
    scheduler = members["scheduler.py"].decode("utf-8")
    checks = {
        "entrypoint": "def agent(observation, configuration=None):" in main,
        "runtime_imports_frozen": "from frozen_selected import FrozenSelected" in runtime,
        "runtime_constructs_frozen": "self.consumer = FrozenSelected()" in runtime,
        "runtime_returns_frozen_transform": (
            "return self.consumer.transform(obs, cfg, selected" in runtime
        ),
        "frozen_owns_target_seam": frozen.count(OLD) == 1,
        "scheduler_has_predecessor_seam": scheduler.count(OLD) == 1,
    }
    failed = sorted(key for key, value in checks.items() if not value)
    if failed:
        raise ReachabilityError(f"canonical call-path binding failed: {failed}")
    return {"consumer": "frozen", "checks": checks}


def _write_closure(root: Path, members: Mapping[str, bytes]) -> None:
    if root.exists():
        raise ReachabilityError(f"output already exists: {root}")
    root.mkdir(parents=True)
    try:
        for name, data in sorted(members.items()):
            target = root.joinpath(*_parts(name))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _patch(data: bytes, label: str) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReachabilityError(f"{label} is not UTF-8") from exc
    if text.count(OLD) != 1 or NEW in text:
        raise ReachabilityError(
            f"{label} target seam drift: old={text.count(OLD)}, new={text.count(NEW)}"
        )
    patched = text.replace(OLD, NEW, 1)
    try:
        compile(patched, label, "exec")
    except SyntaxError as exc:
        raise ReachabilityError(f"patched {label} does not compile: {exc}") from exc
    return patched.encode("utf-8")


def _inventory(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ReachabilityError(f"non-regular output member: {path}")
        data = path.read_bytes()
        result[path.relative_to(root).as_posix()] = {
            "bytes": len(data),
            "sha256": sha256(data),
        }
    return result


def _atomic_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def materialize(archive: Path, output: Path) -> dict[str, Any]:
    archive = archive.resolve()
    output = output.resolve()
    if output.exists():
        raise ReachabilityError(f"output must not exist: {output}")
    original = archive.read_bytes()
    members, manifest = _read_archive(archive)
    call_path = _bind_live_path(members)

    variants: dict[str, dict[str, bytes]] = {
        "control": dict(members),
        "scheduler_only": dict(members),
        "frozen_priority": dict(members),
    }
    variants["scheduler_only"]["scheduler.py"] = _patch(
        members["scheduler.py"], "scheduler.py"
    )
    variants["frozen_priority"]["frozen_selected.py"] = _patch(
        members["frozen_selected.py"], "frozen_selected.py"
    )

    output.mkdir(parents=True)
    try:
        for name, variant in variants.items():
            _write_closure(output / name, variant)
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise

    inventories = {name: _inventory(output / name) for name in variants}
    control = inventories["control"]
    expected_changes = {
        "control": [],
        "scheduler_only": ["scheduler.py"],
        "frozen_priority": ["frozen_selected.py"],
    }
    receipt_variants: dict[str, Any] = {}
    for name, inventory in inventories.items():
        if set(inventory) != set(control):
            raise ReachabilityError(f"{name} closure membership drift")
        changed = [path for path in sorted(control) if inventory[path] != control[path]]
        if changed != expected_changes[name]:
            raise ReachabilityError(
                f"{name} one-factor boundary failed: expected {expected_changes[name]}, "
                f"got {changed}"
            )
        receipt_variants[name] = {
            "files": len(inventory),
            "changed_from_control": changed,
            "main_sha256": inventory["main.py"]["sha256"],
            "scheduler_sha256": inventory["scheduler.py"]["sha256"],
            "frozen_selected_sha256": inventory["frozen_selected.py"]["sha256"],
        }

    if receipt_variants["scheduler_only"]["scheduler_sha256"] != EXPECTED_PATCHED_SCHEDULER_SHA256:
        raise ReachabilityError("patched scheduler identity drift")
    if receipt_variants["frozen_priority"]["frozen_selected_sha256"] != EXPECTED_PATCHED_FROZEN_SHA256:
        raise ReachabilityError("patched frozen consumer identity drift")
    if archive.read_bytes() != original:
        raise ReachabilityError("canonical archive mutated during materialization")

    receipt = {
        "schema_version": 1,
        "experiment": EXPERIMENT,
        "archive": {
            "sha256": EXPECTED_ARCHIVE_SHA256,
            "bytes": EXPECTED_ARCHIVE_BYTES,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "runtime_files": len(manifest["runtime"]),
        },
        "call_path": call_path,
        "variants": receipt_variants,
        "interpretation": {
            "scheduler_only": "predecessor/dormant under consumer=frozen",
            "frozen_priority": "live one-factor reachability arm",
        },
    }
    _atomic_json(output / "MATERIALIZATION.json", receipt)
    return receipt


def _default_archive() -> Path:
    here = Path(__file__).resolve()
    root = here
    while root != root.parent:
        candidate = root / "revenue/kaggriculture/cloud-execution-lab/exports/titan-current.tar.gz"
        if candidate.is_file():
            return candidate
        root = root.parent
    raise ReachabilityError("cannot locate titan-current.tar.gz from analysis path")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.archive or _default_archive(), args.output)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
