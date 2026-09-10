# SPDX-License-Identifier: Apache-2.0
"""Build closure-verifying V2, strict-ablation, and repair entrypoints."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import materialize as lane

OPERATION = lane.OPERATION
STRICT_OPERATION = "titan-v2-forced-feasibility-ablation-20260909-sol-keel-01"
EXPECTED_STRICT_SCHEDULER_BLOB = "31461a47b94bd6a99d4db6dcbed16998dc521a54"
EXPECTED_STRICT_SCHEDULER_SHA256 = (
    "0e8933cdd11a9460a391d10d97cebea4c978067831610a5f293876d2edb86085"
)
EXPECTED_SOURCE_CLOSURE = (
    "0fdad260b528f721e32e39bf72a65d99275b8ce64f669b286d6fbdf78be33e3d"
)
EXPECTED_STRICT_CLOSURE = (
    "d473d50fca0e6978a5c9c3dd4aef7a3bb05cfa3e0aed019e72a3af2fea14ee1e"
)
EXPECTED_REPAIR_CLOSURE = (
    "4cc914ec132ffd6986bee072f6952c19cc8119f20e404ab15633af16da4cf7c1"
)


class BindingError(ValueError):
    """An execution input is not byte-bound to the intended arm."""


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


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BindingError(f"{label} is not a lowercase hex digest")
    return value


def validate_repair_receipt(receipt: Mapping[str, Any]) -> dict[str, str]:
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
        raise BindingError("repair materialization identity mismatch")
    source = receipt.get("source")
    candidate = receipt.get("candidate")
    if not isinstance(source, Mapping) or not isinstance(candidate, Mapping):
        raise BindingError("repair materialization receipt is incomplete")
    if source.get("scheduler_git_blob_sha1") != lane.EXPECTED_V2_SCHEDULER_BLOB:
        raise BindingError("repair receipt is not bound to frozen V2")
    if source.get("scheduler_sha256") != lane.EXPECTED_V2_SCHEDULER_SHA256:
        raise BindingError("repair source scheduler SHA-256 mismatch")
    if source.get("candidate_entry_sha256") != lane.EXPECTED_CANDIDATE_ENTRY_SHA256:
        raise BindingError("repair source candidate entry mismatch")
    if source.get("closure_sha256") != EXPECTED_SOURCE_CLOSURE:
        raise BindingError("repair source closure mismatch")
    if receipt.get("frozen_v1_scheduler_git_blob_sha1") != (
        lane.EXPECTED_V1_SCHEDULER_BLOB
    ):
        raise BindingError("repair receipt is not bound to frozen V1")
    markers = candidate.get("preserved_v2_markers")
    if (
        not isinstance(markers, Mapping)
        or set(markers) != set(lane.PRESERVED_MARKERS)
        or any(value is not True for value in markers.values())
    ):
        raise BindingError("repair preserved-marker custody mismatch")
    if candidate.get("kind") != "minimum_partial_future_capacity_repair":
        raise BindingError("repair kind mismatch")
    if candidate.get("changed_files") != ["scheduler.py"]:
        raise BindingError("repair is not scheduler-only")
    if candidate.get("scheduler_git_blob_sha1") != lane.EXPECTED_PATCHED_SCHEDULER_BLOB:
        raise BindingError("repair scheduler blob mismatch")
    if candidate.get("scheduler_sha256") != lane.EXPECTED_PATCHED_SCHEDULER_SHA256:
        raise BindingError("repair scheduler SHA-256 mismatch")
    if candidate.get("closure_sha256") != EXPECTED_REPAIR_CLOSURE:
        raise BindingError("repair closure mismatch")
    patches = candidate.get("patches")
    if not isinstance(patches, list) or [row.get("label") for row in patches] != [
        row[0] for row in lane.PATCHES
    ]:
        raise BindingError("repair patch ledger mismatch")
    for row in patches:
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_before") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise BindingError("repair patch cardinality mismatch")
    return {
        "source_closure": EXPECTED_SOURCE_CLOSURE,
        "source_scheduler": lane.EXPECTED_V2_SCHEDULER_SHA256,
        "repair_closure": EXPECTED_REPAIR_CLOSURE,
        "repair_scheduler": lane.EXPECTED_PATCHED_SCHEDULER_SHA256,
    }


def validate_strict_receipt(receipt: Mapping[str, Any]) -> dict[str, str]:
    if (
        receipt.get("schema_version") != 1
        or receipt.get("operation") != STRICT_OPERATION
    ):
        raise BindingError("strict materialization identity mismatch")
    source = receipt.get("source")
    ablation = receipt.get("ablation")
    if not isinstance(source, Mapping) or not isinstance(ablation, Mapping):
        raise BindingError("strict materialization receipt is incomplete")
    if source.get("scheduler_git_blob_sha1") != lane.EXPECTED_V2_SCHEDULER_BLOB:
        raise BindingError("strict receipt is not bound to frozen V2")
    if source.get("scheduler_sha256") != lane.EXPECTED_V2_SCHEDULER_SHA256:
        raise BindingError("strict source scheduler SHA-256 mismatch")
    if source.get("closure_sha256") != EXPECTED_SOURCE_CLOSURE:
        raise BindingError("strict source closure mismatch")
    if receipt.get("frozen_v1_scheduler_git_blob_sha1") != (
        lane.EXPECTED_V1_SCHEDULER_BLOB
    ):
        raise BindingError("strict receipt is not bound to frozen V1")
    strict_markers = ablation.get("preserved_v2_markers")
    expected_strict_markers = {
        "all_shed_target_domain",
        "next_turn_rival_scenario",
        "delayed_rival_scenario",
        "full_continuation_value",
        "per_index_queue_rewrite",
    }
    if (
        not isinstance(strict_markers, Mapping)
        or set(strict_markers) != expected_strict_markers
        or any(value is not True for value in strict_markers.values())
    ):
        raise BindingError("strict preserved-marker custody mismatch")
    if ablation.get("kind") != "forced_feasibility_admission_and_rank":
        raise BindingError("strict ablation kind mismatch")
    if ablation.get("changed_files") != ["scheduler.py"]:
        raise BindingError("strict ablation is not scheduler-only")
    if ablation.get("scheduler_git_blob_sha1") != EXPECTED_STRICT_SCHEDULER_BLOB:
        raise BindingError("strict scheduler blob mismatch")
    if ablation.get("scheduler_sha256") != EXPECTED_STRICT_SCHEDULER_SHA256:
        raise BindingError("strict scheduler SHA-256 mismatch")
    if ablation.get("closure_sha256") != EXPECTED_STRICT_CLOSURE:
        raise BindingError("strict closure mismatch")
    return {
        "source_closure": EXPECTED_SOURCE_CLOSURE,
        "source_scheduler": lane.EXPECTED_V2_SCHEDULER_SHA256,
        "strict_closure": EXPECTED_STRICT_CLOSURE,
        "strict_scheduler": EXPECTED_STRICT_SCHEDULER_SHA256,
    }


def wrapper_source(
    *, arm: str, payload_closure: str, scheduler_sha256: str
) -> bytes:
    tag = hashlib.sha256(
        f"{arm}:{payload_closure}:{scheduler_sha256}".encode("ascii")
    ).hexdigest()[:24]
    source = f'''# SPDX-License-Identifier: Apache-2.0
# Generated closure-verifying entrypoint for the {arm} arm.
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import stat
import sys

ARM = {arm!r}
EXPECTED_CLOSURE = {payload_closure!r}
EXPECTED_SCHEDULER_SHA256 = {scheduler_sha256!r}
EXPECTED_ENTRY_SHA256 = {lane.EXPECTED_CANDIDATE_ENTRY_SHA256!r}
PAYLOAD = Path(__file__).resolve().parent / "payload"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _inventory(root):
    if not root.is_dir():
        raise RuntimeError("bound payload is not a directory")
    result={{}}
    for path in sorted(root.rglob("*")):
        relative=path.relative_to(root).as_posix()
        info=path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("bound payload contains non-regular member: "+relative)
        data=path.read_bytes()
        result[relative]=(len(data),_sha256(data))
    if not result:
        raise RuntimeError("bound payload is empty")
    return result


def _closure(items):
    digest=hashlib.sha256()
    for relative,record in sorted(items.items()):
        digest.update(relative.encode("utf-8"));digest.update(b"\\0")
        digest.update(str(record[0]).encode("ascii"));digest.update(b"\\0")
        digest.update(record[1].encode("ascii"));digest.update(b"\\0")
    return digest.hexdigest()


_items=_inventory(PAYLOAD)
if _closure(_items)!=EXPECTED_CLOSURE:
    raise RuntimeError("bound payload closure mismatch for "+ARM)
if _items.get("scheduler.py",(None,None))[1]!=EXPECTED_SCHEDULER_SHA256:
    raise RuntimeError("bound scheduler digest mismatch for "+ARM)
if _items.get("candidate.py",(None,None))[1]!=EXPECTED_ENTRY_SHA256:
    raise RuntimeError("bound candidate entry digest mismatch for "+ARM)
if "scheduler" in sys.modules or "mechanics" in sys.modules:
    raise RuntimeError("ambiguous bare-module state before bound payload import")
sys.path.insert(0,str(PAYLOAD))
_spec=importlib.util.spec_from_file_location("titan_bound_payload_{tag}",PAYLOAD/"candidate.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load bound candidate payload")
_module=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=_module
_spec.loader.exec_module(_module)
agent=getattr(_module,"agent")
if not callable(agent):
    raise RuntimeError("bound payload agent is not callable")
'''
    return source.encode("utf-8")


def copy_checked(source: Path, destination: Path) -> dict[str, dict[str, Any]]:
    before = lane.inventory(source)
    shutil.copytree(source, destination, symlinks=False)
    after = lane.inventory(destination)
    if after != before:
        raise BindingError(f"copied payload differs: {source} -> {destination}")
    return after


def bind_execution(
    source: Path,
    strict: Path,
    repair: Path,
    strict_receipt_path: Path,
    repair_receipt_path: Path,
    output: Path,
) -> dict[str, Any]:
    source = Path(source).resolve()
    strict = Path(strict).resolve()
    repair = Path(repair).resolve()
    strict_receipt_path = Path(strict_receipt_path).resolve(strict=True)
    repair_receipt_path = Path(repair_receipt_path).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise BindingError(f"output already exists: {output}")
    roots = {"control": source, "strict": strict, "repair": repair}
    if len(set(roots.values())) != 3:
        raise BindingError("control, strict, and repair roots must be distinct")
    for arm, root in roots.items():
        try:
            output.relative_to(root)
        except ValueError:
            pass
        else:
            raise BindingError(f"output may not be nested inside {arm} source")

    strict_expected = validate_strict_receipt(strict_object(strict_receipt_path))
    repair_expected = validate_repair_receipt(strict_object(repair_receipt_path))
    if strict_expected["source_closure"] != repair_expected["source_closure"]:
        raise BindingError("strict and repair receipts disagree on source closure")

    before = {
        "control": lane.inventory(source),
        "strict": lane.inventory(strict),
        "repair": lane.inventory(repair),
    }
    expected = {
        "control": (
            EXPECTED_SOURCE_CLOSURE,
            lane.EXPECTED_V2_SCHEDULER_SHA256,
        ),
        "strict": (EXPECTED_STRICT_CLOSURE, EXPECTED_STRICT_SCHEDULER_SHA256),
        "repair": (
            EXPECTED_REPAIR_CLOSURE,
            lane.EXPECTED_PATCHED_SCHEDULER_SHA256,
        ),
    }
    for arm, inventory in before.items():
        closure, scheduler = expected[arm]
        if lane.closure_sha256(inventory) != closure:
            raise BindingError(f"{arm} payload closure mismatch")
        if inventory.get("scheduler.py", {}).get("sha256") != scheduler:
            raise BindingError(f"{arm} scheduler mismatch")
        if (
            inventory.get("candidate.py", {}).get("sha256")
            != lane.EXPECTED_CANDIDATE_ENTRY_SHA256
        ):
            raise BindingError(f"{arm} candidate entry mismatch")

    output.mkdir(parents=True)
    arms: dict[str, Any] = {}
    for arm in ("control", "strict", "repair"):
        arm_root = output / arm
        payload = arm_root / "payload"
        inventory = copy_checked(roots[arm], payload)
        closure, scheduler = expected[arm]
        wrapper = wrapper_source(
            arm=arm, payload_closure=closure, scheduler_sha256=scheduler
        )
        try:
            compile(wrapper.decode("utf-8"), str(arm_root / "bound_entry.py"), "exec")
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise BindingError(f"{arm} wrapper does not compile: {exc}") from exc
        lane.atomic_write(arm_root / "bound_entry.py", wrapper)
        arms[arm] = {
            "payload_closure_sha256": lane.closure_sha256(inventory),
            "scheduler_sha256": inventory["scheduler.py"]["sha256"],
            "payload_entry_sha256": inventory["candidate.py"]["sha256"],
            "wrapper_sha256": lane.sha256(wrapper),
            "wrapper_git_blob_sha1": lane.git_blob_sha1(wrapper),
            "wrapper": f"{arm}/bound_entry.py::agent",
        }

    if len({row["wrapper_sha256"] for row in arms.values()}) != 3:
        raise BindingError("arm wrapper identities are not distinct")
    for arm, root in roots.items():
        if lane.inventory(root) != before[arm]:
            raise BindingError(f"{arm} source changed while binding")
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "strict_operation": STRICT_OPERATION,
        "strict_receipt_sha256": digest_file(strict_receipt_path),
        "repair_receipt_sha256": digest_file(repair_receipt_path),
        "arms": arms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--strict", type=Path, required=True)
    parser.add_argument("--repair", type=Path, required=True)
    parser.add_argument("--strict-receipt", type=Path, required=True)
    parser.add_argument("--repair-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = bind_execution(
        args.source,
        args.strict,
        args.repair,
        args.strict_receipt,
        args.repair_receipt,
        args.output,
    )
    lane.atomic_write(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "arms": {
                    arm: row["wrapper_sha256"]
                    for arm, row in receipt["arms"].items()
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
