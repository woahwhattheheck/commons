# SPDX-License-Identifier: Apache-2.0
"""Build closure-verifying control and ablation entrypoints for exact execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import materialize as base

EXPECTED_ENTRY_SHA256 = "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"


class BindingError(ValueError):
    """Execution inputs cannot be bound to the materialized closures."""


def strict_object(path: Path) -> dict[str, Any]:
    def pairs(rows):
        out: dict[str, Any] = {}
        for key, value in rows:
            if key in out:
                raise BindingError(f"duplicate JSON key {key!r} in {path}")
            out[key] = value
        return out

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BindingError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError(
            f"cannot read {path}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise BindingError(f"{path} must contain one JSON object")
    return value


def digest_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_digest(value: Any, label: str, length: int = 64) -> str:
    alphabet = "0123456789abcdef"
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in alphabet for char in value)
    ):
        raise BindingError(f"{label} is not a lowercase hex digest")
    return value


def validate_materialization(receipt: Mapping[str, Any]) -> dict[str, str]:
    if receipt.get("schema_version") != 2:
        raise BindingError("ordered materialization receipt schema mismatch")
    if receipt.get("repair") != "sol-vector-execution-custody-and-order-v1":
        raise BindingError("ordered materialization repair identity mismatch")
    source = receipt.get("source")
    ablation = receipt.get("ablation")
    if not isinstance(source, Mapping) or not isinstance(ablation, Mapping):
        raise BindingError("ordered materialization receipt is incomplete")
    if ablation.get("changed_files") != ["scheduler.py"]:
        raise BindingError("ablation is not scheduler-only")
    if ablation.get("target_iteration_order") != "PRODUCTS":
        raise BindingError("ablation did not preserve V2 PRODUCTS order")
    return {
        "source_closure": require_digest(
            source.get("closure_sha256"), "source closure"
        ),
        "source_scheduler": require_digest(
            source.get("scheduler_sha256"), "source scheduler"
        ),
        "ablation_closure": require_digest(
            ablation.get("closure_sha256"), "ablation closure"
        ),
        "ablation_scheduler": require_digest(
            ablation.get("scheduler_sha256"), "ablation scheduler"
        ),
    }


def wrapper_source(
    *,
    payload_closure: str,
    scheduler_sha256: str,
    arm: str,
) -> bytes:
    module_tag = hashlib.sha256(
        f"{arm}:{payload_closure}:{scheduler_sha256}".encode("ascii")
    ).hexdigest()[:24]
    source = f'''# SPDX-License-Identifier: Apache-2.0
"""Generated closure-verifying entrypoint for the {arm} arm."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import stat
import sys

EXPECTED_CLOSURE = "{payload_closure}"
EXPECTED_SCHEDULER_SHA256 = "{scheduler_sha256}"
EXPECTED_ENTRY_SHA256 = "{EXPECTED_ENTRY_SHA256}"
ARM = "{arm}"
PAYLOAD = Path(__file__).resolve().parent / "payload"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _inventory(root):
    if not root.is_dir():
        raise RuntimeError("bound payload is not a directory")
    result = {{}}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("bound payload contains non-regular member: " + relative)
        data = path.read_bytes()
        result[relative] = (len(data), _sha256(data))
    if not result:
        raise RuntimeError("bound payload is empty")
    return result


def _closure(items):
    digest = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\\0")
        digest.update(str(record[0]).encode("ascii"))
        digest.update(b"\\0")
        digest.update(record[1].encode("ascii"))
        digest.update(b"\\0")
    return digest.hexdigest()


_items = _inventory(PAYLOAD)
if _closure(_items) != EXPECTED_CLOSURE:
    raise RuntimeError("bound payload closure mismatch for " + ARM)
if _items.get("scheduler.py", (None, None))[1] != EXPECTED_SCHEDULER_SHA256:
    raise RuntimeError("bound scheduler digest mismatch for " + ARM)
if _items.get("candidate.py", (None, None))[1] != EXPECTED_ENTRY_SHA256:
    raise RuntimeError("bound candidate entry digest mismatch for " + ARM)
if "scheduler" in sys.modules or "mechanics" in sys.modules:
    raise RuntimeError("ambiguous bare-module state before bound payload import")
sys.path.insert(0, str(PAYLOAD))
_spec = importlib.util.spec_from_file_location(
    "titan_bound_payload_{module_tag}", PAYLOAD / "candidate.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load bound candidate payload")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)
agent = getattr(_module, "agent")
if not callable(agent):
    raise RuntimeError("bound payload agent is not callable")
'''
    return source.encode("utf-8")


def copy_checked(source: Path, destination: Path) -> dict[str, dict[str, Any]]:
    before = base.inventory(source)
    shutil.copytree(source, destination, symlinks=False)
    after = base.inventory(destination)
    if after != before:
        raise BindingError(
            f"copied payload differs from source: {source} -> {destination}"
        )
    return after


def bind_execution(
    source: Path,
    ablation: Path,
    materialization_receipt: Path,
    output: Path,
) -> dict[str, Any]:
    source = source.resolve()
    ablation = ablation.resolve()
    materialization_receipt = materialization_receipt.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise BindingError(f"output already exists: {output}")
    materialization = strict_object(materialization_receipt)
    expected = validate_materialization(materialization)

    source_before = base.inventory(source)
    ablation_before = base.inventory(ablation)
    if base.closure_sha256(source_before) != expected["source_closure"]:
        raise BindingError("source tree does not match materialization receipt")
    if base.closure_sha256(ablation_before) != expected["ablation_closure"]:
        raise BindingError("ablation tree does not match materialization receipt")
    if source_before.get("scheduler.py", {}).get("sha256") != expected[
        "source_scheduler"
    ]:
        raise BindingError("source scheduler does not match materialization receipt")
    if ablation_before.get("scheduler.py", {}).get("sha256") != expected[
        "ablation_scheduler"
    ]:
        raise BindingError(
            "ablation scheduler does not match materialization receipt"
        )
    for label, inventory in (
        ("source", source_before),
        ("ablation", ablation_before),
    ):
        if inventory.get("candidate.py", {}).get("sha256") != EXPECTED_ENTRY_SHA256:
            raise BindingError(f"{label} candidate.py bytes drifted")

    output.mkdir(parents=True)
    arms: dict[str, Any] = {}
    for arm, payload_source, closure, scheduler in (
        (
            "control",
            source,
            expected["source_closure"],
            expected["source_scheduler"],
        ),
        (
            "ablation",
            ablation,
            expected["ablation_closure"],
            expected["ablation_scheduler"],
        ),
    ):
        arm_root = output / arm
        payload = arm_root / "payload"
        inventory = copy_checked(payload_source, payload)
        wrapper = wrapper_source(
            payload_closure=closure,
            scheduler_sha256=scheduler,
            arm=arm,
        )
        try:
            compile(
                wrapper.decode("utf-8"),
                str(arm_root / "bound_entry.py"),
                "exec",
            )
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise BindingError(f"{arm} wrapper does not compile: {exc}") from exc
        base.atomic_write(arm_root / "bound_entry.py", wrapper)
        arms[arm] = {
            "payload_closure_sha256": base.closure_sha256(inventory),
            "scheduler_sha256": inventory["scheduler.py"]["sha256"],
            "payload_entry_sha256": inventory["candidate.py"]["sha256"],
            "wrapper_sha256": base.sha256(wrapper),
            "wrapper_git_blob_sha1": base.git_blob_sha1(wrapper),
            "wrapper": f"{arm}/bound_entry.py::agent",
        }

    if arms["control"]["wrapper_sha256"] == arms["ablation"][
        "wrapper_sha256"
    ]:
        raise BindingError("control and ablation wrapper identities are equal")
    if base.inventory(source) != source_before:
        raise BindingError("source tree changed while binding execution")
    if base.inventory(ablation) != ablation_before:
        raise BindingError("ablation tree changed while binding execution")

    return {
        "schema_version": 1,
        "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
        "repair": "sol-vector-bound-arm-entrypoints-v1",
        "materialization_receipt_sha256": digest_text(
            materialization_receipt
        ),
        "arms": arms,
    }


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    base.atomic_write(
        path,
        (
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ablation", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = bind_execution(
        args.source,
        args.ablation,
        args.materialization_receipt,
        args.output,
    )
    atomic_json(args.receipt, receipt)
    print(
        json.dumps(
            {
                "control_wrapper": receipt["arms"]["control"][
                    "wrapper_sha256"
                ],
                "ablation_wrapper": receipt["arms"]["ablation"][
                    "wrapper_sha256"
                ],
                "source_closure": receipt["arms"]["control"][
                    "payload_closure_sha256"
                ],
                "ablation_closure": receipt["arms"]["ablation"][
                    "payload_closure_sha256"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
