# SPDX-License-Identifier: Apache-2.0
"""Fail-closed identity audit for the Capillary action-bound panel."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent

ARCHIVE = LAB / "exports" / "titan-current.tar.gz"
CANDIDATE = LAB / "candidates" / "capillary-executable-sol-prism" / "candidate.py"
CONTROL = HERE / "control.py"
EVALUATOR = KAG / "cloud-eval" / "evaluate.py"
LOADER = KAG / "20260907-offline-agent" / "evaluate.py"
ENGINE = LAB / "reference" / "engine"
OPPONENTS = {
    "arlene": LAB / "runtime" / "variants" / "v1" / "reference" / "next-panel" / "vendor" / "arlene.py",
    "v1": LAB / "runtime" / "variants" / "v1" / "candidate.py",
}
OVERLAYS = {
    "jit_seed_staging.py": "e1cf2485ab869cf3c6f5eec455b0a25f6aeaa505",
    "jit_seed_order_rail.py": "f5d2c3775bc527ef7f950a850eac8036bd71e865",
    "titan_capillary.py": "afbfb0859d7a3219d2f3e5c4178d72c128f31911",
    "capillary_main.py": "e545a65d99f81f7982ee70fd4c336b78ad957afc",
}
EXPECTED = {
    "archive_sha256": "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86",
    "archive_bytes": 427_870,
    "source_manifest_sha256": "1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083",
    "runtime_files": 109,
    "candidate_git_blob": "f373dfd20cdc1573f09eb9d4e31901b411161c54",
    "evaluator_git_blob": "077feb2208b6e0c1727835eb4f8089709bf67f3b",
    "engine_git_blobs": {
        "kaggriculture.py": "3c202c7ee921da239356789e266b694635103fc4",
        "kaggriculture.json": "b354d06b742fe48402513792253f1a5c29366b20",
        "utils.py": "91c8822ee6201ba4a5a8416c7dbe34f95dd61c87",
    },
}


class AuditError(ValueError):
    """The panel inputs do not match the admitted source identities."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def regular_bytes(path: Path, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise AuditError(f"{label} is not one regular file: {path}")
    return path.read_bytes()


def identity(path: Path, label: str) -> dict[str, Any]:
    data = regular_bytes(path, label)
    return {
        "path": str(path.relative_to(KAG.parent.parent)),
        "bytes": len(data),
        "sha256": sha256(data),
        "git_blob_sha1": git_blob(data),
    }


def literal_constants(path: Path, names: set[str]) -> dict[str, Any]:
    tree = ast.parse(regular_bytes(path, path.name).decode("utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in names:
                try:
                    values[target.id] = ast.literal_eval(value)
                except (ValueError, TypeError) as exc:
                    raise AuditError(
                        f"{path.name} constant {target.id} is not literal"
                    ) from exc
    missing = sorted(names - values.keys())
    if missing:
        raise AuditError(f"{path.name} missing constants: {missing}")
    return values


def inspect_archive(path: Path) -> dict[str, Any]:
    raw = regular_bytes(path, "canonical archive")
    if len(raw) != EXPECTED["archive_bytes"] or sha256(raw) != EXPECTED["archive_sha256"]:
        raise AuditError("canonical archive identity drift")
    members: dict[str, bytes] = {}
    with tarfile.open(path, mode="r:gz") as bundle:
        for member in bundle:
            pure = PurePosixPath(member.name)
            if (
                not member.isfile()
                or pure.is_absolute()
                or not pure.parts
                or any(part in ("", ".", "..") for part in pure.parts)
                or "\\" in member.name
                or PurePosixPath(*pure.parts).as_posix() != member.name
                or member.name in members
            ):
                raise AuditError(f"unsafe or duplicate archive member: {member.name!r}")
            stream = bundle.extractfile(member)
            if stream is None:
                raise AuditError(f"unreadable archive member: {member.name}")
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise AuditError(f"archive member length mismatch: {member.name}")
            members[member.name] = data
    source = members.get("SOURCE.json")
    if source is None or sha256(source) != EXPECTED["source_manifest_sha256"]:
        raise AuditError("canonical SOURCE.json drift")
    try:
        manifest = json.loads(source)
    except ValueError as exc:
        raise AuditError("canonical SOURCE.json is invalid") from exc
    runtime = manifest.get("runtime")
    if (
        manifest.get("entrypoint") != "main.py::agent"
        or manifest.get("config") != "TITAN-CONFIG.json"
        or not isinstance(runtime, dict)
        or len(runtime) != EXPECTED["runtime_files"]
        or set(members) != set(runtime) | {"SOURCE.json"}
    ):
        raise AuditError("canonical archive manifest contract drift")
    for name, metadata in runtime.items():
        data = members[name]
        if (
            not isinstance(metadata, dict)
            or metadata.get("bytes") != len(data)
            or metadata.get("sha256") != sha256(data)
            or not isinstance(metadata.get("source_path"), str)
        ):
            raise AuditError(f"canonical manifest member drift: {name}")
    return {
        "path": str(path.relative_to(KAG.parent.parent)),
        "bytes": len(raw),
        "sha256": sha256(raw),
        "source_manifest_sha256": sha256(source),
        "runtime_files": len(runtime),
        "archive_members": len(members),
        "entrypoint": manifest["entrypoint"],
        "config": manifest["config"],
    }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def build_receipt(head: str) -> dict[str, Any]:
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise AuditError("head must be one lowercase 40-hex commit")

    candidate_constants = literal_constants(
        CANDIDATE,
        {
            "EXPECTED_ARCHIVE_SHA256",
            "EXPECTED_ARCHIVE_BYTES",
            "EXPECTED_SOURCE_MANIFEST_SHA256",
            "EXPECTED_RUNTIME_FILES",
        },
    )
    control_constants = literal_constants(
        CONTROL,
        {
            "EXPECTED_ARCHIVE_SHA256",
            "EXPECTED_ARCHIVE_BYTES",
            "EXPECTED_SOURCE_MANIFEST_SHA256",
            "EXPECTED_RUNTIME_FILES",
        },
    )
    expected_constants = {
        "EXPECTED_ARCHIVE_SHA256": EXPECTED["archive_sha256"],
        "EXPECTED_ARCHIVE_BYTES": EXPECTED["archive_bytes"],
        "EXPECTED_SOURCE_MANIFEST_SHA256": EXPECTED["source_manifest_sha256"],
        "EXPECTED_RUNTIME_FILES": EXPECTED["runtime_files"],
    }
    if candidate_constants != expected_constants:
        raise AuditError(f"candidate archive constants drift: {candidate_constants}")
    if control_constants != expected_constants:
        raise AuditError(f"control archive constants drift: {control_constants}")

    candidate_identity = identity(CANDIDATE, "Capillary carrier")
    if candidate_identity["git_blob_sha1"] != EXPECTED["candidate_git_blob"]:
        raise AuditError("Capillary carrier blob drift")
    evaluator_identity = identity(EVALUATOR, "source evaluator")
    if evaluator_identity["git_blob_sha1"] != EXPECTED["evaluator_git_blob"]:
        raise AuditError("source evaluator blob drift")

    overlay_receipts = {}
    for name, expected_blob in OVERLAYS.items():
        row = identity(LAB / name, f"Capillary overlay {name}")
        if row["git_blob_sha1"] != expected_blob:
            raise AuditError(f"Capillary overlay blob drift: {name}")
        overlay_receipts[name] = row

    engine_receipts = {}
    for name, expected_blob in EXPECTED["engine_git_blobs"].items():
        row = identity(ENGINE / name, f"official engine {name}")
        if row["git_blob_sha1"] != expected_blob:
            raise AuditError(f"official engine blob drift: {name}")
        engine_receipts[name] = row

    try:
        checkout_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=KAG.parent.parent, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError("cannot bind checkout head") from exc
    if checkout_head != head:
        raise AuditError(f"checkout/head mismatch: {checkout_head} != {head}")

    return {
        "schema_version": 1,
        "operation": "titan-v3-capillary-action-bound-panel-20260910-sol-cambium-01",
        "git_head": head,
        "archive": inspect_archive(ARCHIVE),
        "control": identity(CONTROL, "exact control carrier"),
        "candidate": candidate_identity,
        "candidate_constants": candidate_constants,
        "control_constants": control_constants,
        "overlays": overlay_receipts,
        "evaluator_source": evaluator_identity,
        "loader": identity(LOADER, "official loader"),
        "engine": engine_receipts,
        "opponents": {
            name: identity(path, f"opponent {name}")
            for name, path in OPPONENTS.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_receipt(args.head)
    atomic_json(args.output, receipt)
    print(json.dumps({
        "git_head": receipt["git_head"],
        "archive_sha256": receipt["archive"]["sha256"],
        "control_sha256": receipt["control"]["sha256"],
        "candidate_sha256": receipt["candidate"]["sha256"],
        "overlay_blobs": {
            key: value["git_blob_sha1"]
            for key, value in receipt["overlays"].items()
        },
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
