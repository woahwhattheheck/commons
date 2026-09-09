# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source and private-carrier audit for SOL-QUOIN."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
REPO = LAB.parents[2]
FROZEN = LAB / "frozen_selected.py"
SCHEDULER = LAB / "scheduler.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
ARCHIVE = LAB / "exports" / "titan-current.tar.gz"
POINTER = LAB / "runtime" / "integrated-selected" / "CURRENT-ARCHIVE.json"
PATCH = HERE / "executable_receipt_profile.py"
CANDIDATE = HERE / "candidate.py"
SMOKE = HERE / "carrier_smoke.py"
WORKFLOW = REPO / ".github" / "workflows" / "titan-v3-executable-receipt-profile-sol-quoin.yml"
EVALUATOR = KAG / "cloud-eval" / "evaluate.py"
LOADER = KAG / "20260907-offline-agent" / "evaluate.py"

OPERATION = "titan-v3-executable-receipt-profile-20260909-sol-quoin-01"
EXPECTED_FROZEN = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_SCHEDULER = "a483b24dd72b580d7d8811636b54d2d44f391575"
EXPECTED_PATCH = "8e984812e15a84db14ee7311b047e0c8483132da"
EXPECTED_EVALUATOR = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_LOADER = "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5"
EXPECTED_ARCHIVE_SHA256 = "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86"
EXPECTED_ARCHIVE_BYTES = 427_870
EXPECTED_SOURCE_MANIFEST_SHA256 = "1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083"
EXPECTED_RUNTIME_FILES = 109
EXPECTED_ARCHIVE_MEMBERS = 110
EXPECTED_ARCHIVED_ROOT_BLOBS = {
    "frozen_selected.py": EXPECTED_FROZEN,
    "scheduler.py": EXPECTED_SCHEDULER,
    "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
    "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def git_blob_sha1(path: Path) -> str:
    return git_blob_sha1_bytes(path.read_bytes())


def function_source(path: Path, class_name: str, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == function_name
                ):
                    segment = ast.get_source_segment(source, child)
                    if segment is None:
                        raise RuntimeError("could not recover function source")
                    return segment
    raise RuntimeError(f"missing {class_name}.{function_name}")


def returned_dict_keys(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(functions) != 1:
        raise RuntimeError(f"expected one {function_name} function")
    returns = [node for node in ast.walk(functions[0]) if isinstance(node, ast.Return)]
    dictionaries = [node.value for node in returns if isinstance(node.value, ast.Dict)]
    if len(dictionaries) != 1:
        raise RuntimeError(f"expected one direct dict return in {function_name}")
    keys: set[str] = set()
    for key in dictionaries[0].keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise RuntimeError(f"nonliteral environment key in {function_name}")
        keys.add(key.value)
    return keys


def safe_archive_name(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise RuntimeError("invalid canonical archive member name")
    pure = PurePosixPath(name)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
        or PurePosixPath(*pure.parts).as_posix() != name
    ):
        raise RuntimeError(f"unsafe canonical archive member: {name!r}")
    return tuple(pure.parts)


def audit_archive() -> dict[str, Any]:
    if not ARCHIVE.is_file() or ARCHIVE.is_symlink():
        raise RuntimeError("canonical archive is not a regular file")
    data = ARCHIVE.read_bytes()
    if len(data) != EXPECTED_ARCHIVE_BYTES:
        raise RuntimeError("canonical archive length drift")
    if sha256_bytes(data) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("canonical archive digest drift")

    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    expected_pointer = {
        "path": "exports/titan-current.tar.gz",
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "sha256": EXPECTED_ARCHIVE_SHA256,
        "bytes": EXPECTED_ARCHIVE_BYTES,
        "runtime_files": EXPECTED_RUNTIME_FILES,
        "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
    }
    if pointer != expected_pointer:
        raise RuntimeError("canonical archive pointer drift")

    members: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as bundle:
        for member in bundle:
            if not member.isfile():
                raise RuntimeError(f"nonregular canonical member: {member.name!r}")
            safe_archive_name(member.name)
            if member.name in members:
                raise RuntimeError(f"duplicate canonical member: {member.name}")
            stream = bundle.extractfile(member)
            if stream is None:
                raise RuntimeError(f"unreadable canonical member: {member.name}")
            payload = stream.read(member.size + 1)
            if len(payload) != member.size:
                raise RuntimeError(f"canonical member length mismatch: {member.name}")
            members[member.name] = payload
    if len(members) != EXPECTED_ARCHIVE_MEMBERS:
        raise RuntimeError("canonical archive member cardinality drift")
    manifest_bytes = members.get("SOURCE.json")
    if manifest_bytes is None or sha256_bytes(manifest_bytes) != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("canonical source manifest drift")
    manifest = json.loads(manifest_bytes)
    runtime = manifest.get("runtime")
    if (
        not isinstance(runtime, dict)
        or len(runtime) != EXPECTED_RUNTIME_FILES
        or manifest.get("entrypoint") != "main.py::agent"
        or manifest.get("config") != "TITAN-CONFIG.json"
    ):
        raise RuntimeError("canonical source manifest contract drift")
    if set(members) != set(runtime) | {"SOURCE.json"}:
        raise RuntimeError("canonical manifest/member set drift")
    for name, metadata in runtime.items():
        if not isinstance(metadata, dict):
            raise RuntimeError(f"invalid runtime metadata: {name}")
        payload = members[name]
        if metadata.get("bytes") != len(payload) or metadata.get("sha256") != sha256_bytes(payload):
            raise RuntimeError(f"runtime member identity drift: {name}")
    for name, expected in EXPECTED_ARCHIVED_ROOT_BLOBS.items():
        if git_blob_sha1_bytes(members[name]) != expected:
            raise RuntimeError(f"archived root source drift: {name}")
    return {
        "sha256": EXPECTED_ARCHIVE_SHA256,
        "bytes": EXPECTED_ARCHIVE_BYTES,
        "runtime_files": EXPECTED_RUNTIME_FILES,
        "archive_members": len(members),
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "root_git_blobs": dict(EXPECTED_ARCHIVED_ROOT_BLOBS),
    }


def audit() -> dict[str, Any]:
    required = [
        FROZEN,
        SCHEDULER,
        ENGINE,
        ARCHIVE,
        POINTER,
        PATCH,
        CANDIDATE,
        SMOKE,
        WORKFLOW,
        EVALUATOR,
        LOADER,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source: " + ", ".join(missing))
    if git_blob_sha1(FROZEN) != EXPECTED_FROZEN:
        raise RuntimeError("frozen_selected.py drift")
    if git_blob_sha1(SCHEDULER) != EXPECTED_SCHEDULER:
        raise RuntimeError("scheduler.py drift")
    if git_blob_sha1(PATCH) != EXPECTED_PATCH:
        raise RuntimeError("candidate patch drift")
    if git_blob_sha1(EVALUATOR) != EXPECTED_EVALUATOR:
        raise RuntimeError("pinned evaluator drift")
    if git_blob_sha1(LOADER) != EXPECTED_LOADER:
        raise RuntimeError("pinned evaluator loader drift")

    profile = function_source(SCHEDULER, "SellScheduler", "receipt_profile")
    engine = ENGINE.read_text(encoding="utf-8")
    patch = PATCH.read_text(encoding="utf-8")
    candidate = CANDIDATE.read_text(encoding="utf-8")
    smoke = SMOKE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    archive = audit_archive()

    checks = {
        "predecessor_has_one_raw_market_loop": profile.count("for o in orders:") == 1,
        "predecessor_has_no_first_n_projection": "orders[:max_orders]" not in profile,
        "official_engine_has_one_first_n_slice": engine.count("queues.append(q[:max_orders])") == 1,
        "official_engine_normalizes_minimum_one": engine.count(
            'max_orders = max(1, int(get(env.configuration, "maxMarketOrdersPerTurn", 10)))'
        ) == 1,
        "patch_has_one_prefix_transform": patch.count("market[:max_orders]") == 1,
        "candidate_uses_exact_archive_not_mutable_lab_main": (
            '_ARENA_ROOT / "main.py"' in candidate
            and 'LAB / "main.py"' not in candidate
            and "_materialize_private_runtime()" in candidate
            and "_ARENA_OWNER" in candidate
        ),
        "candidate_rejects_archive_path_and_type_attacks": (
            "_safe_member_parts" in candidate
            and "member.isfile()" in candidate
            and "duplicate canonical archive member" in candidate
            and ".extractall(" not in candidate
            and ".extract(" not in candidate
        ),
        "candidate_verifies_complete_manifest_before_execution": all(
            value in candidate
            for value in (
                EXPECTED_ARCHIVE_SHA256,
                EXPECTED_SOURCE_MANIFEST_SHA256,
                str(EXPECTED_RUNTIME_FILES),
                EXPECTED_PATCH,
                "canonical archive/member manifest mismatch",
                "private runtime materialization drift",
            )
        ),
        "candidate_checks_arena_import_origins": (
            candidate.count("_assert_private_runtime_modules()") >= 3
            and '_assert_arena_module(frozen_selected, "frozen_selected.py")' in candidate
            and '_assert_arena_module(titan_runtime, "titan_runtime.py")' in candidate
            and "ambient runtime module collision" in candidate
        ),
        "candidate_patches_before_canonical_construction": (
            candidate.index("install_receipt = _install(frozen_selected)")
            < candidate.index("instance = _ORIGINAL_NEW_INSTANCE(root, feature_data)")
            and candidate.count("_CANONICAL._new_instance = _candidate_new_instance") == 1
        ),
        "smoke_environment_is_stripped": returned_dict_keys(SMOKE, "minimal_environment")
        == {
            "PATH",
            "HOME",
            "LANG",
            "PYTHONHASHSEED",
            "PYTHONDONTWRITEBYTECODE",
        },
        "smoke_uses_python_isolated_mode_and_private_origin_checks": (
            '"-I"' in smoke
            and "origins_inside_private_arena" in smoke
            and "ambient_lab_on_sys_path" in smoke
            and EXPECTED_ARCHIVE_SHA256 in smoke
            and "ExecutableReceiptProfileFrozenSelected" in smoke
        ),
        "smoke_runs_actual_pinned_evaluator_in_both_seats": (
            str(EXPECTED_EVALUATOR) in smoke
            and str(EXPECTED_LOADER) in smoke
            and '"--candidate"' in smoke
            and '"--episode-steps"' in smoke
            and "seen_seats != {0, 1}" in smoke
            and "candidate_actor_calls" in smoke
        ),
        "workflow_gates_and_retains_carrier_smoke": (
            'python "$ROOT/carrier_smoke.py" --json "$RUNNER_TEMP/CARRIER-SMOKE.json"'
            in workflow
            and "carrier_smoke.py test_executable_receipt_profile.py" in workflow
            and "${{ runner.temp }}/CARRIER-SMOKE.json" in workflow
            and "build_integrated.py --check" in workflow
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError("source/carrier audit failed: " + ", ".join(failed))
    return {
        "schema_version": 2,
        "operation": OPERATION,
        "decision": "PASS",
        "checks": checks,
        "frozen_selected_git_blob": EXPECTED_FROZEN,
        "scheduler_git_blob": EXPECTED_SCHEDULER,
        "patch_git_blob": EXPECTED_PATCH,
        "candidate_git_blob": git_blob_sha1(CANDIDATE),
        "carrier_smoke_git_blob": git_blob_sha1(SMOKE),
        "evaluator_git_blob": EXPECTED_EVALUATOR,
        "loader_git_blob": EXPECTED_LOADER,
        "canonical_archive": archive,
        "factor": "exclude raw rows after maxMarketOrdersPerTurn from receipt_profile only",
        "carrier": "exact 109-file canonical archive materialized into a private arena",
        "evidence_boundary": "source/physics and executable first actions only; no strength claim",
        "canonical_files_modified": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    result = audit()
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
