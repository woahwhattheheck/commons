# SPDX-License-Identifier: Apache-2.0
"""Create and verify closure-checking entrypoints for the V2 causal screen."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
BOUND_ENTRY = HERE / "bound_entry.py"
OPERATION = "titan-v2-target-domain-ablation-20260909-sol-bulwark-01"
V2_ENTRY_SHA256 = "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"


class BindingError(ValueError):
    """The execution roots, wrappers, sidecars, or receipt are not exact."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_value(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BindingError(f"{label} is not a lowercase SHA-256 digest")
    return value


def strict_object(path: Path) -> dict[str, Any]:
    def reject_pairs(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise BindingError(f"duplicate JSON key {key!r} in {path}")
            output[key] = value
        return output

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BindingError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise BindingError(f"{path} must contain one JSON object")
    return value


def atomic_write(path: Path, data: bytes) -> None:
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


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        raise BindingError(f"package is not a directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BindingError(f"non-regular package member: {relative}")
        data = path.read_bytes()
        result[relative] = {"bytes": len(data), "sha256": sha256(data)}
    if not result:
        raise BindingError(f"package inventory is empty: {root}")
    return result


def closure_sha256(items: Mapping[str, Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def receipt_closures(receipt: Mapping[str, Any]) -> tuple[str, str]:
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
        raise BindingError("materialization receipt identity mismatch")
    source = receipt.get("source")
    ablation = receipt.get("ablation")
    if not isinstance(source, Mapping) or not isinstance(ablation, Mapping):
        raise BindingError("materialization receipt is incomplete")
    source_closure = sha256_value(source.get("closure_sha256"), "source closure")
    candidate_closure = sha256_value(ablation.get("closure_sha256"), "ablation closure")
    if source_closure == candidate_closure:
        raise BindingError("source and ablation closures are equal")
    if ablation.get("changed_files") != ["scheduler.py"]:
        raise BindingError("materialization receipt is not scheduler-only")
    return source_closure, candidate_closure


def sidecar(label: str, closure: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "label": label,
        "package": label,
        "closure_sha256": closure,
        "candidate_entry": "candidate.py",
        "candidate_entry_sha256": V2_ENTRY_SHA256,
    }


def encoded(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def build(source: Path, candidate: Path, root: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    source = source.resolve()
    candidate = candidate.resolve()
    root = root.resolve()
    source_closure, candidate_closure = receipt_closures(receipt)
    source_before = inventory(source)
    if closure_sha256(source_before) != source_closure:
        raise BindingError("live frozen V2 source does not match receipt source closure")
    candidate_items = inventory(candidate)
    if closure_sha256(candidate_items) != candidate_closure:
        raise BindingError("materialized candidate does not match receipt ablation closure")
    for package in (source, candidate):
        entry = package / "candidate.py"
        if not entry.is_file() or sha256(entry.read_bytes()) != V2_ENTRY_SHA256:
            raise BindingError(f"{package.name} candidate.py is not frozen V2")

    root.mkdir(parents=True, exist_ok=True)
    control = root / "control"
    if control.exists():
        raise BindingError(f"control package already exists: {control}")
    shutil.copytree(source, control, symlinks=False)
    if inventory(source) != source_before:
        raise BindingError("frozen V2 source changed during execution binding")
    if closure_sha256(inventory(control)) != source_closure:
        raise BindingError("control copy does not match frozen V2 closure")

    wrapper = BOUND_ENTRY.read_bytes()
    try:
        compile(wrapper.decode("utf-8"), str(BOUND_ENTRY), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise BindingError(f"bound entrypoint does not compile: {exc}") from exc
    wrapper_sha = sha256(wrapper)
    arms: dict[str, Any] = {}
    for label, closure in (("control", source_closure), ("candidate", candidate_closure)):
        entry_path = root / f"{label}_entry.py"
        sidecar_path = root / f"{label}.binding.json"
        if entry_path.exists() or sidecar_path.exists():
            raise BindingError(f"execution binding output already exists for {label}")
        sidecar_bytes = encoded(sidecar(label, closure))
        atomic_write(entry_path, wrapper)
        atomic_write(sidecar_path, sidecar_bytes)
        arms[label] = {
            "entry": entry_path.name,
            "callable": "agent",
            "wrapper_sha256": wrapper_sha,
            "sidecar": sidecar_path.name,
            "sidecar_sha256": sha256(sidecar_bytes),
            "package": label,
            "closure_sha256": closure,
            "candidate_entry": "candidate.py",
            "candidate_entry_sha256": V2_ENTRY_SHA256,
        }
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "wrapper_source": BOUND_ENTRY.name,
        "wrapper_source_sha256": wrapper_sha,
        "arms": arms,
    }


def verify(root: Path, binding: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    source_closure, candidate_closure = receipt_closures(receipt)
    if binding.get("schema_version") != 1 or binding.get("operation") != OPERATION:
        raise BindingError("execution binding identity mismatch")
    wrapper = BOUND_ENTRY.read_bytes()
    wrapper_sha = sha256(wrapper)
    if (
        binding.get("wrapper_source") != BOUND_ENTRY.name
        or binding.get("wrapper_source_sha256") != wrapper_sha
    ):
        raise BindingError("execution binding wrapper source mismatch")
    arms = binding.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != {"control", "candidate"}:
        raise BindingError("execution binding arms are invalid")
    expected_closures = {"control": source_closure, "candidate": candidate_closure}
    normalized: dict[str, Any] = {}
    for label in ("control", "candidate"):
        arm = arms[label]
        if not isinstance(arm, Mapping):
            raise BindingError(f"{label} binding is not an object")
        expected_entry = f"{label}_entry.py"
        expected_sidecar = f"{label}.binding.json"
        if (
            arm.get("entry") != expected_entry
            or arm.get("callable") != "agent"
            or arm.get("wrapper_sha256") != wrapper_sha
            or arm.get("sidecar") != expected_sidecar
            or arm.get("package") != label
            or arm.get("candidate_entry") != "candidate.py"
            or arm.get("candidate_entry_sha256") != V2_ENTRY_SHA256
            or arm.get("closure_sha256") != expected_closures[label]
        ):
            raise BindingError(f"{label} execution-binding fields mismatch")
        entry_path = root / expected_entry
        sidecar_path = root / expected_sidecar
        package = root / label
        if entry_path.read_bytes() != wrapper:
            raise BindingError(f"{label} wrapper bytes mismatch")
        sidecar_bytes = sidecar_path.read_bytes()
        if sha256(sidecar_bytes) != arm.get("sidecar_sha256"):
            raise BindingError(f"{label} sidecar digest mismatch")
        if strict_object(sidecar_path) != sidecar(label, expected_closures[label]):
            raise BindingError(f"{label} sidecar content mismatch")
        if closure_sha256(inventory(package)) != expected_closures[label]:
            raise BindingError(f"{label} package closure mismatch")
        candidate_entry = package / "candidate.py"
        if sha256(candidate_entry.read_bytes()) != V2_ENTRY_SHA256:
            raise BindingError(f"{label} candidate entry drifted")
        normalized[label] = dict(arm)
    if normalized["control"]["entry"] == normalized["candidate"]["entry"]:
        raise BindingError("control and candidate entry names are not distinct")
    if normalized["control"]["closure_sha256"] == normalized["candidate"]["closure_sha256"]:
        raise BindingError("control and candidate package closures are not distinct")
    return {
        "wrapper_source_sha256": wrapper_sha,
        "control": normalized["control"],
        "candidate": normalized["candidate"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    receipt = strict_object(args.receipt)
    if args.verify:
        value = verify(args.root, strict_object(args.binding), receipt)
    else:
        if args.source is None or args.candidate is None:
            parser.error("--source and --candidate are required unless --verify is used")
        value = build(args.source, args.candidate, args.root, receipt)
        atomic_write(args.binding, encoded(value))
        value = verify(args.root, strict_object(args.binding), receipt)
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
