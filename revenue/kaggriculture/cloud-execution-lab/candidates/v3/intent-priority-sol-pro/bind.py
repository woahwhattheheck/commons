# SPDX-License-Identifier: Apache-2.0
"""Create closure-checking entrypoints for a matched current/candidate panel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


EXPERIMENT = "titan-v3-current-intent-priority-integration-20260910-01"


class BindError(ValueError):
    """Materialized roots or receipts are detached from the requested panel."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
    temporary.replace(path)


def strict_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BindError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise BindError(f"JSON root is not an object: {path}")
    return value


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise BindError(f"materialized root is not one directory: {root}")
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise BindError(f"materialized tree contains symlink: {relative}")
        if path.is_file():
            raw = path.read_bytes()
            rows[relative.as_posix()] = {
                "sha256": sha256(raw),
                "bytes": len(raw),
            }
        elif not path.is_dir():
            raise BindError(f"materialized tree contains special path: {relative}")
    return rows


def closure_sha256(rows: Mapping[str, Mapping[str, Any]]) -> str:
    return sha256(
        json.dumps(
            rows,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _validate_receipts(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    head: str,
) -> None:
    for label, receipt in (("control", control), ("candidate", candidate)):
        if receipt.get("schema_version") != 1:
            raise BindError(f"{label} receipt schema mismatch")
        if receipt.get("experiment") != EXPERIMENT:
            raise BindError(f"{label} receipt experiment mismatch")
        if receipt.get("integration_head") != head:
            raise BindError(f"{label} receipt head mismatch")
    control_feature = control.get("feature")
    candidate_feature = candidate.get("feature")
    if not isinstance(control_feature, Mapping) or not isinstance(
        candidate_feature, Mapping
    ):
        raise BindError("feature receipts are invalid")
    if control_feature.get("enabled") is not False:
        raise BindError("control is not default-off")
    if candidate_feature.get("enabled") is not True:
        raise BindError("candidate feature is not enabled")
    if control_feature.get("default") is not False:
        raise BindError("control default is not false")
    if candidate_feature.get("default") is not False:
        raise BindError("candidate default is not false")

    control_source = control.get("source")
    candidate_source = candidate.get("source")
    control_result = control.get("candidate")
    candidate_result = candidate.get("candidate")
    for label, value in (
        ("control source", control_source),
        ("candidate source", candidate_source),
        ("control result", control_result),
        ("candidate result", candidate_result),
    ):
        if not isinstance(value, Mapping):
            raise BindError(f"{label} is invalid")
    if dict(control_source) != dict(candidate_source):
        raise BindError("control and candidate do not share one canonical source")
    if control_result.get("changed_files") != []:
        raise BindError("default-off control changed canonical files")
    if candidate_result.get("changed_files") != ["scheduler.py"]:
        raise BindError("enabled candidate is not scheduler-only")
    if (
        control_result.get("closure_sha256")
        != control_source.get("closure_sha256")
    ):
        raise BindError("default-off closure is not canonical-exact")
    if (
        candidate_result.get("scheduler_git_blob_sha1")
        == candidate_source.get("scheduler_git_blob_sha1")
    ):
        raise BindError("enabled scheduler did not change")


def wrapper_source(root: Path, expected_closure: str, module_name: str) -> bytes:
    """Render a self-contained wrapper that refuses closure drift before import."""
    return f"""# Generated by {EXPERIMENT}; do not edit.
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path({str(root)!r})
EXPECTED_CLOSURE = {expected_closure!r}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _closure():
    rows = {{}}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise RuntimeError(f"bound TITAN closure contains symlink: {{relative}}")
        if path.is_file():
            raw = path.read_bytes()
            rows[relative.as_posix()] = {{"sha256": _sha256(raw), "bytes": len(raw)}}
        elif not path.is_dir():
            raise RuntimeError(f"bound TITAN closure contains special path: {{relative}}")
    encoded = json.dumps(
        rows, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return _sha256(encoded)


actual = _closure()
if actual != EXPECTED_CLOSURE:
    raise RuntimeError(
        f"bound TITAN closure drifted: {{actual}} != {{EXPECTED_CLOSURE}}"
    )
if not (ROOT / "main.py").is_file():
    raise RuntimeError("bound TITAN main.py is missing")
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location({module_name!r}, ROOT / "main.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load bound TITAN main.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def agent(observation, configuration=None):
    return _module.agent(observation, configuration)
""".encode("utf-8")


def bind(
    *,
    control_root: Path,
    candidate_root: Path,
    control_receipt_path: Path,
    candidate_receipt_path: Path,
    output_dir: Path,
    head: str,
) -> dict[str, Any]:
    control_receipt = strict_json(control_receipt_path)
    candidate_receipt = strict_json(candidate_receipt_path)
    _validate_receipts(control_receipt, candidate_receipt, head=head)

    control_rows = inventory(control_root)
    candidate_rows = inventory(candidate_root)
    control_closure = closure_sha256(control_rows)
    candidate_closure = closure_sha256(candidate_rows)
    expected_control = control_receipt["candidate"]["closure_sha256"]
    expected_candidate = candidate_receipt["candidate"]["closure_sha256"]
    if control_closure != expected_control:
        raise BindError("control root closure is detached from receipt")
    if candidate_closure != expected_candidate:
        raise BindError("candidate root closure is detached from receipt")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    control_wrapper = output_dir / "control_bound.py"
    candidate_wrapper = output_dir / "candidate_bound.py"
    control_bytes = wrapper_source(
        Path(control_root).resolve(),
        control_closure,
        "_titan_current_control_bound",
    )
    candidate_bytes = wrapper_source(
        Path(candidate_root).resolve(),
        candidate_closure,
        "_titan_current_intent_priority_bound",
    )
    atomic_write(control_wrapper, control_bytes)
    atomic_write(candidate_wrapper, candidate_bytes)
    compile(control_bytes.decode("utf-8"), str(control_wrapper), "exec")
    compile(candidate_bytes.decode("utf-8"), str(candidate_wrapper), "exec")

    return {
        "schema_version": 1,
        "operation": EXPERIMENT,
        "experiment": EXPERIMENT,
        "integration_head": head,
        "control": {
            "root": str(Path(control_root).resolve()),
            "closure_sha256": control_closure,
            "entry": str(control_wrapper.resolve()),
            "entry_sha256": sha256(control_bytes),
            "callable": "agent",
        },
        "candidate": {
            "root": str(Path(candidate_root).resolve()),
            "closure_sha256": candidate_closure,
            "entry": str(candidate_wrapper.resolve()),
            "entry_sha256": sha256(candidate_bytes),
            "callable": "agent",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--control-receipt", type=Path, required=True)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        receipt = bind(
            control_root=args.control_root,
            candidate_root=args.candidate_root,
            control_receipt_path=args.control_receipt,
            candidate_receipt_path=args.candidate_receipt,
            output_dir=args.output_dir,
            head=args.head,
        )
    except (BindError, OSError, ValueError, KeyError, TypeError) as exc:
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
                "experiment": EXPERIMENT,
                "control_closure": receipt["control"]["closure_sha256"],
                "candidate_closure": receipt["candidate"]["closure_sha256"],
                "control_wrapper": receipt["control"]["entry_sha256"],
                "candidate_wrapper": receipt["candidate"]["entry_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
