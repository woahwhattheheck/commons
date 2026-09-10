#!/usr/bin/env python3
"""Authenticate and compose TITAN funding town-consumption + plant-decay donors.

This carrier is intentionally additive.  It never edits the canonical TITAN
source.  It proves that two exact donor heads are ancestors of the checkout,
executes the exact town-consumption materializer against the byte-pinned
``frozen_selected.py``, validates that donor's receipt, consumes that exact
postimage as the plant-decay donor's input, and publishes one atomic evidence
directory.  The final receipt also proves that the configured production
runtime selects ``FrozenSelected`` from the composed postimage.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

OPERATION = "TITAN-V3-FUNDING-TOWN-DECAY-AUTHENTICATED-COMPOSITION-20260910-01"
SCHEMA = "titan-v3-funding-town-decay-composition/v1"
BASE_MAIN = "6f6f2f0fefd972050dbfa4c4d1ccbb1a9fe67701"
TOWN_PR = 12053
TOWN_HEAD = "e701b8bf348b8ccacda854722d1e510cfd3c67c6"
DECAY_PR = 12075
DECAY_HEAD = "30d9d09561a07e3f9eef2c7128b6139bf0acdea7"

SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
MECHANICS_GIT_BLOB = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
RUNTIME_GIT_BLOB = "b952c9c228ecbde592bf3d2df01638677abb0d24"
CONFIG_GIT_BLOB = "3a3bef83899d3010fad623b628d9e95d9978111b"
TOWN_MATERIALIZER_GIT_BLOB = "3fd5fd361b5356ad3aa1f8dc7bda3ed2b3cee2b0"
DECAY_MATERIALIZER_GIT_BLOB = "6c215bb626369424051fbe58312ecf225ac32ad3"

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
SOURCE_REL = LAB_REL / "frozen_selected.py"
SCHEDULER_REL = LAB_REL / "scheduler.py"
MECHANICS_REL = LAB_REL / "mechanics.py"
ENGINE_REL = LAB_REL / "reference/engine/kaggriculture.py"
RUNTIME_REL = LAB_REL / "titan_runtime.py"
CONFIG_REL = LAB_REL / "TITAN-CONFIG.json"
TOWN_MATERIALIZER_REL = (
    LAB_REL
    / "candidates/v3-funding-town-consumption-sol-atlas/town_consumption_closure.py"
)
DECAY_MATERIALIZER_REL = (
    LAB_REL
    / "candidates/v3-funding-plant-decay-sol-chronos/materialize.py"
)

OUTPUT_TOWN_SOURCE = "frozen_selected_town.py"
OUTPUT_TOWN_RECEIPT = "TOWN-RECEIPT.json"
OUTPUT_FINAL_SOURCE = "frozen_selected_town_decay.py"
OUTPUT_RECEIPT = "COMPOSITION-RECEIPT.json"


class CompositionError(ValueError):
    """An identity, ancestry, chronology, runtime, or publication contract failed."""


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(data: bytes) -> dict[str, Any]:
    return {
        "git_blob_sha1": git_blob_sha1(data),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
    }


def _read_regular(path: Path, label: str) -> bytes:
    path = Path(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise CompositionError(f"missing {label}: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise CompositionError(f"{label} must be a regular non-symlink file: {path}")
    return path.read_bytes()


def _require_existing_real_directory(path: Path, label: str) -> Path:
    path = Path(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise CompositionError(f"missing {label}: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise CompositionError(f"{label} must be a real directory: {path}")
    return path.resolve(strict=True)


def _reject_symlink_components(path: Path, label: str) -> None:
    absolute = Path(path).absolute()
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        if stat.S_ISLNK(current.lstat().st_mode):
            raise CompositionError(f"{label} contains a symlink component: {current}")


def _strict_json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CompositionError(f"{label} must be UTF-8: {exc}") from exc

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CompositionError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise CompositionError(f"{label} contains non-finite value {value}")

    try:
        parsed = json.loads(text, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    except CompositionError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CompositionError(f"invalid {label}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CompositionError(f"{label} must be a JSON object")
    return parsed


def _run_git(repo_root: Path, *args: str, check: bool = True) -> str:
    process = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check and process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()[:1000]
        raise CompositionError(f"git {' '.join(args)} failed: {detail}")
    return process.stdout.strip()


def _require_repository_path(repo_root: Path, actual: Path, relative: Path, label: str) -> None:
    expected = (repo_root / relative).resolve(strict=True)
    resolved = Path(actual).resolve(strict=True)
    if resolved != expected:
        raise CompositionError(
            f"{label} path mismatch: expected {relative.as_posix()}, got {resolved}"
        )


def verify_git_custody(repo_root: Path) -> dict[str, Any]:
    """Prove the checkout descends from both exact donor heads and current base."""
    repo_root = _require_existing_real_directory(repo_root, "repository root")
    if not (repo_root / ".git").exists():
        raise CompositionError(f"repository root is not a Git checkout: {repo_root}")
    head = _run_git(repo_root, "rev-parse", "HEAD")
    ancestors: dict[str, bool] = {}
    for label, commit in (
        ("base_main", BASE_MAIN),
        ("town_head", TOWN_HEAD),
        ("decay_head", DECAY_HEAD),
    ):
        _run_git(repo_root, "cat-file", "-e", f"{commit}^{{commit}}")
        result = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, head],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        ancestors[label] = result.returncode == 0
        if result.returncode not in (0, 1):
            detail = (result.stderr or result.stdout).strip()[:1000]
            raise CompositionError(f"git ancestry check failed for {label}: {detail}")
        if not ancestors[label]:
            raise CompositionError(f"checkout HEAD {head} does not descend from {label} {commit}")

    expected_paths = {
        TOWN_MATERIALIZER_REL: TOWN_MATERIALIZER_GIT_BLOB,
        DECAY_MATERIALIZER_REL: DECAY_MATERIALIZER_GIT_BLOB,
        SOURCE_REL: SOURCE_GIT_BLOB,
        SCHEDULER_REL: SCHEDULER_GIT_BLOB,
        MECHANICS_REL: MECHANICS_GIT_BLOB,
        ENGINE_REL: ENGINE_GIT_BLOB,
        RUNTIME_REL: RUNTIME_GIT_BLOB,
        CONFIG_REL: CONFIG_GIT_BLOB,
    }
    final_tree_blobs: dict[str, str] = {}
    for path, expected_blob in expected_paths.items():
        actual_blob = _run_git(repo_root, "rev-parse", f"HEAD:{path.as_posix()}")
        if actual_blob != expected_blob:
            raise CompositionError(
                f"HEAD blob mismatch for {path.as_posix()}: {actual_blob} != {expected_blob}"
            )
        final_tree_blobs[path.as_posix()] = actual_blob

    donor_blobs = {
        "town": _run_git(
            repo_root, "rev-parse", f"{TOWN_HEAD}:{TOWN_MATERIALIZER_REL.as_posix()}"
        ),
        "decay": _run_git(
            repo_root, "rev-parse", f"{DECAY_HEAD}:{DECAY_MATERIALIZER_REL.as_posix()}"
        ),
    }
    if donor_blobs["town"] != TOWN_MATERIALIZER_GIT_BLOB:
        raise CompositionError("town donor head does not contain the expected materializer blob")
    if donor_blobs["decay"] != DECAY_MATERIALIZER_GIT_BLOB:
        raise CompositionError("decay donor head does not contain the expected materializer blob")

    return {
        "checkout_head": head,
        "ancestors": ancestors,
        "donor_head_blobs": donor_blobs,
        "final_tree_blobs": final_tree_blobs,
    }


def _load_exact_module(path: Path, name: str, expected_blob: str) -> tuple[ModuleType, bytes]:
    data = _read_regular(path, name)
    actual_blob = git_blob_sha1(data)
    if actual_blob != expected_blob:
        raise CompositionError(
            f"{name} Git blob mismatch: expected {expected_blob}, got {actual_blob}"
        )
    try:
        text = data.decode("utf-8")
        compile(text, f"<{name}>", "exec")
    except (UnicodeDecodeError, SyntaxError, ValueError) as exc:
        raise CompositionError(f"{name} is not valid UTF-8 Python: {exc}") from exc
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CompositionError(f"cannot construct import spec for {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        raise CompositionError(f"cannot load exact {name}: {exc}") from exc
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module, data


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _top_level_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise CompositionError(f"expected exactly one top-level {name}(), found {len(matches)}")
    return matches[0]


def _is_funding_loop(node: ast.stmt) -> bool:
    if not isinstance(node, ast.For):
        return False
    if not isinstance(node.target, ast.Name) or node.target.id != "t":
        return False
    iterator = node.iter
    if not isinstance(iterator, ast.Call) or _name(iterator.func) != "range":
        return False
    if len(iterator.args) != 2:
        return False
    start, stop = iterator.args
    return (
        isinstance(start, ast.Name)
        and start.id == "now"
        and isinstance(stop, ast.BinOp)
        and isinstance(stop.op, ast.Add)
        and isinstance(stop.left, ast.Name)
        and stop.left.id == "end"
        and isinstance(stop.right, ast.Constant)
        and stop.right.value == 1
    )


def _direct_call_name(statement: ast.stmt) -> str:
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return _name(statement.value.func)
    return ""


def inspect_composed_postimage(source_text: str) -> dict[str, Any]:
    """Require the exact guard and per-turn town -> decay chronology."""
    try:
        tree = ast.parse(source_text)
        compile(source_text, "<town-decay-postimage>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise CompositionError(f"composed postimage is not valid Python: {exc}") from exc

    town_helpers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_funding_apply_town_consumption"
    ]
    lifecycle_helpers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_funding_require_static_shop_lifecycle"
    ]
    if len(town_helpers) != 1 or len(lifecycle_helpers) != 1:
        raise CompositionError(
            "composed postimage must contain exactly one town helper and lifecycle helper"
        )

    funding = _top_level_function(tree, "_funding_trace")
    loops = [node for node in funding.body if _is_funding_loop(node)]
    if len(loops) != 1:
        raise CompositionError(f"composed postimage has {len(loops)} outer funding loops")
    loop = loops[0]
    direct_calls = [_direct_call_name(statement) for statement in loop.body]
    town_indices = [
        index
        for index, name in enumerate(direct_calls)
        if name == "_funding_apply_town_consumption"
    ]
    decay_indices = [
        index for index, name in enumerate(direct_calls) if name == "m._decay_plants"
    ]
    if len(town_indices) != 1 or len(decay_indices) != 1:
        raise CompositionError(
            "composed funding loop must directly call town consumption and plant decay once"
        )
    town_index = town_indices[0]
    decay_index = decay_indices[0]
    if decay_index != town_index + 1:
        raise CompositionError("town consumption must be immediately followed by plant decay")
    if decay_index != len(loop.body) - 1:
        raise CompositionError("plant decay must be the final projected stage of each turn")

    guard_indices = [
        index
        for index, statement in enumerate(funding.body)
        if _direct_call_name(statement) == "_funding_require_static_shop_lifecycle"
    ]
    loop_index = funding.body.index(loop)
    if len(guard_indices) != 1 or guard_indices[0] >= loop_index:
        raise CompositionError("shop-lifecycle guard must execute exactly once before the funding loop")
    if loop_index + 1 >= len(funding.body) or not isinstance(
        funding.body[loop_index + 1], ast.Return
    ):
        raise CompositionError("funding loop must still flow directly to its result return")

    return {
        "funding_function_line": funding.lineno,
        "lifecycle_guard_line": funding.body[guard_indices[0]].lineno,
        "loop_line": loop.lineno,
        "town_line": loop.body[town_index].lineno,
        "decay_line": loop.body[decay_index].lineno,
        "town_immediately_before_decay": True,
        "decay_is_final_stage": True,
        "loop_flows_directly_to_return": True,
    }


def verify_selected_consumer(runtime_text: str, config: Mapping[str, Any]) -> dict[str, Any]:
    """Bind the configured runtime path to ``FrozenSelected`` construction."""
    if config.get("consumer") != "frozen":
        raise CompositionError("TITAN config does not select consumer='frozen'")
    if config.get("terminal_route") is not False:
        raise CompositionError("TITAN config must select the nonterminal frozen consumer")
    try:
        tree = ast.parse(runtime_text)
        compile(runtime_text, "<titan-runtime>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise CompositionError(f"titan runtime is not valid Python: {exc}") from exc

    feature_classes = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Features"
    ]
    agent_classes = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TitanAgent"
    ]
    if len(feature_classes) != 1 or len(agent_classes) != 1:
        raise CompositionError("runtime must define exactly one Features and TitanAgent class")

    consumer_defaults = [
        node
        for node in feature_classes[0].body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "consumer"
        and isinstance(node.value, ast.Constant)
        and node.value.value == "frozen"
    ]
    if len(consumer_defaults) != 1:
        raise CompositionError("Features.consumer default is not exactly 'frozen'")

    initializers = [
        node
        for node in agent_classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == "_initialize"
    ]
    if len(initializers) != 1:
        raise CompositionError("TitanAgent must define exactly one _initialize()")
    initializer = initializers[0]
    imports = [
        node
        for node in ast.walk(initializer)
        if isinstance(node, ast.ImportFrom)
        and node.module == "frozen_selected"
        and any(alias.name == "FrozenSelected" for alias in node.names)
    ]
    constructions: list[ast.Assign] = []
    for node in ast.walk(initializer):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if _name(node.value.func) != "FrozenSelected" or node.value.args or node.value.keywords:
            continue
        if any(
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and target.attr == "consumer"
            for target in node.targets
        ):
            constructions.append(node)
    if len(imports) != 1 or len(constructions) != 1:
        raise CompositionError(
            "TitanAgent._initialize must import FrozenSelected once and assign self.consumer once"
        )
    return {
        "config_consumer": "frozen",
        "config_terminal_route": False,
        "features_default_line": consumer_defaults[0].lineno,
        "runtime_import_line": imports[0].lineno,
        "runtime_construction_line": constructions[0].lineno,
        "runtime_constructor": "FrozenSelected()",
    }


def _validate_town_receipt(
    receipt: Mapping[str, Any],
    pristine_source: bytes,
    town_postimage: bytes,
    engine_source: bytes,
) -> bytes:
    if receipt.get("schema") != "titan-v3-funding-town-consumption/v2":
        raise CompositionError("town donor receipt schema mismatch")
    if receipt.get("complete") is not True:
        raise CompositionError("town donor receipt is not complete")
    if receipt.get("source_blob_sha1") != SOURCE_GIT_BLOB:
        raise CompositionError("town donor receipt source blob mismatch")
    if receipt.get("source_sha256") != sha256_bytes(pristine_source):
        raise CompositionError("town donor receipt source SHA-256 mismatch")
    if receipt.get("engine_blob_sha1") != ENGINE_GIT_BLOB:
        raise CompositionError("town donor receipt engine blob mismatch")
    if receipt.get("engine_sha256") != sha256_bytes(engine_source):
        raise CompositionError("town donor receipt engine SHA-256 mismatch")
    if receipt.get("patched_source_sha256") != sha256_bytes(town_postimage):
        raise CompositionError("town donor receipt postimage SHA-256 mismatch")
    for key in (
        "town_helper_count",
        "town_call_count",
        "lifecycle_guard_count",
        "lifecycle_call_count",
    ):
        if receipt.get(key) != 1:
            raise CompositionError(f"town donor receipt {key} is not exactly one")
    if receipt.get("shop_lifecycle_policy") != "same-day exact; cross-day fail-closed":
        raise CompositionError("town donor lifecycle policy mismatch")
    if receipt.get("canonical_runtime_modified") is not False:
        raise CompositionError("town donor receipt claims canonical runtime mutation")
    try:
        encoded = (
            json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CompositionError(f"town donor receipt is not strict JSON: {exc}") from exc
    reparsed = _strict_json_object(encoded, "town donor receipt")
    if reparsed != dict(receipt):
        raise CompositionError("town donor receipt did not round-trip exactly")
    return encoded


def consume_authenticated_town_postimage(
    *,
    town_postimage: str,
    town_receipt: Mapping[str, Any],
    pristine_source: bytes,
    scheduler_text: str,
    mechanics_text: str,
    engine_text: str,
    engine_source: bytes,
    decay_module: ModuleType,
) -> tuple[str, dict[str, Any]]:
    """Apply decay only after authenticating the exact town donor postimage."""
    town_bytes = town_postimage.encode("utf-8")
    _validate_town_receipt(
        town_receipt, pristine_source, town_bytes, engine_source
    )
    if getattr(decay_module, "SOURCE_GIT_BLOB", None) != SOURCE_GIT_BLOB:
        raise CompositionError("decay donor pristine-source pin drift")
    if getattr(decay_module, "SCHEDULER_GIT_BLOB", None) != SCHEDULER_GIT_BLOB:
        raise CompositionError("decay donor scheduler pin drift")
    if getattr(decay_module, "MECHANICS_GIT_BLOB", None) != MECHANICS_GIT_BLOB:
        raise CompositionError("decay donor mechanics pin drift")
    if getattr(decay_module, "ENGINE_GIT_BLOB", None) != ENGINE_GIT_BLOB:
        raise CompositionError("decay donor engine pin drift")

    try:
        engine_contract = decay_module.verify_engine(engine_text)
        binding_contract = decay_module.verify_runtime_decay_binding(
            town_postimage, scheduler_text, mechanics_text, engine_text
        )
        final_source, decay_patch = decay_module.patch_source(town_postimage)
    except Exception as exc:
        raise CompositionError(f"decay donor rejected authenticated town postimage: {exc}") from exc
    composition = inspect_composed_postimage(final_source)
    if decay_patch.get("prior_stage_call") != "_funding_apply_town_consumption":
        raise CompositionError(
            "decay donor did not observe town consumption as its immediate predecessor stage"
        )
    return final_source, {
        "engine_contract": engine_contract,
        "runtime_decay_binding": binding_contract,
        "decay_patch_contract": decay_patch,
        "composition_contract": composition,
    }


def compose_texts(
    *,
    source_text: str,
    scheduler_text: str,
    mechanics_text: str,
    engine_text: str,
    town_module: ModuleType,
    decay_module: ModuleType,
) -> tuple[str, dict[str, Any], bytes, str, dict[str, Any]]:
    """Run the exact donor chain in the only accepted order."""
    if getattr(town_module, "EXPECTED_SOURCE_BLOB_SHA1", None) != SOURCE_GIT_BLOB:
        raise CompositionError("town donor pristine-source pin drift")
    if getattr(town_module, "EXPECTED_ENGINE_BLOB_SHA1", None) != ENGINE_GIT_BLOB:
        raise CompositionError("town donor engine pin drift")
    try:
        town_module.verify_official_engine(engine_text)
        town_postimage = town_module.materialize(source_text)
        town_receipt = town_module.receipt(source_text, town_postimage, engine_text)
    except Exception as exc:
        raise CompositionError(f"town donor materialization failed: {exc}") from exc
    pristine_bytes = source_text.encode("utf-8")
    engine_bytes = engine_text.encode("utf-8")
    town_receipt_bytes = _validate_town_receipt(
        town_receipt,
        pristine_bytes,
        town_postimage.encode("utf-8"),
        engine_bytes,
    )
    final_source, decay_evidence = consume_authenticated_town_postimage(
        town_postimage=town_postimage,
        town_receipt=town_receipt,
        pristine_source=pristine_bytes,
        scheduler_text=scheduler_text,
        mechanics_text=mechanics_text,
        engine_text=engine_text,
        engine_source=engine_bytes,
        decay_module=decay_module,
    )
    return town_postimage, town_receipt, town_receipt_bytes, final_source, decay_evidence


_RUNTIME_PROBE = r'''
import importlib.util
import json
from pathlib import Path
import sys

lab = Path(sys.argv[1]).resolve()
candidate_path = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(lab))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

candidate = load("frozen_selected", candidate_path)
runtime = load("_titan_runtime_town_decay_probe", lab / "titan_runtime.py")
features = runtime.Features(
    consumer="frozen",
    seed=False,
    funding=False,
    redundant_hire=False,
    terminal_route=False,
    committed=False,
    terminal_history=False,
    spatial_pathing=False,
    spatial_tempo=False,
    fourth_quadrant=False,
    market_pressure=False,
    committed_seed_retry=False,
    operating_stock=False,
    idle_fertilizer=False,
    crop_release=False,
    early_capital=False,
)
agent = runtime.TitanAgent(features)
agent._initialize()
bound_globals = agent.consumer.transform.__func__.__globals__
trace = bound_globals.get("_funding_trace")
assert agent.consumer.__class__ is candidate.FrozenSelected
assert trace is candidate._funding_trace
assert bound_globals.get("_funding_apply_town_consumption") is candidate._funding_apply_town_consumption
assert bound_globals.get("_funding_require_static_shop_lifecycle") is candidate._funding_require_static_shop_lifecycle
print(json.dumps({
    "consumer_class": agent.consumer.__class__.__name__,
    "consumer_module": agent.consumer.__class__.__module__,
    "funding_trace_module": trace.__module__,
    "town_helper_bound": True,
    "lifecycle_guard_bound": True,
    "selected_postimage": True,
}, sort_keys=True))
'''


def run_runtime_probe(lab_root: Path, candidate_path: Path) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = "/tmp/titan-town-decay-runtime-probe-pycache"
    process = subprocess.run(
        [sys.executable, "-I", "-c", _RUNTIME_PROBE, str(lab_root), str(candidate_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
        env=environment,
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()[-2000:]
        raise CompositionError(f"selected-consumer runtime probe failed: {detail}")
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if not lines:
        raise CompositionError("selected-consumer runtime probe produced no JSON")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise CompositionError(f"runtime probe output is not JSON: {lines[-1]!r}") from exc
    expected = {
        "consumer_class": "FrozenSelected",
        "consumer_module": "frozen_selected",
        "funding_trace_module": "frozen_selected",
        "town_helper_bound": True,
        "lifecycle_guard_bound": True,
        "selected_postimage": True,
    }
    if result != expected:
        raise CompositionError(f"unexpected selected-consumer runtime probe: {result}")
    result["probe_source_sha256"] = sha256_bytes(_RUNTIME_PROBE.encode("utf-8"))
    return result


def _write_fsynced(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _maybe_fault(label: str, fault_after: str | None) -> None:
    if fault_after == label:
        raise CompositionError(f"injected publication fault after {label}")


def compose(
    *,
    repo_root: Path,
    source_path: Path,
    scheduler_path: Path,
    mechanics_path: Path,
    engine_path: Path,
    runtime_path: Path,
    config_path: Path,
    town_materializer_path: Path,
    decay_materializer_path: Path,
    output_dir: Path,
    fault_after: str | None = None,
) -> dict[str, Any]:
    """Create one deterministic, all-or-nothing composition evidence directory."""
    repo_root = _require_existing_real_directory(repo_root, "repository root")
    output_dir = Path(output_dir)
    _reject_symlink_components(output_dir.parent, "output parent")
    output_parent = _require_existing_real_directory(output_dir.parent, "output parent")
    if output_dir.exists() or output_dir.is_symlink():
        raise CompositionError(f"refusing to overwrite output directory: {output_dir}")
    resolved_output = output_dir.resolve(strict=False)
    if resolved_output == repo_root or repo_root in resolved_output.parents:
        raise CompositionError("output directory must be outside the repository checkout")

    paths = {
        "source": Path(source_path),
        "scheduler": Path(scheduler_path),
        "mechanics": Path(mechanics_path),
        "engine": Path(engine_path),
        "runtime": Path(runtime_path),
        "config": Path(config_path),
        "town_materializer": Path(town_materializer_path),
        "decay_materializer": Path(decay_materializer_path),
    }
    expected_repository_paths = {
        "source": SOURCE_REL,
        "scheduler": SCHEDULER_REL,
        "mechanics": MECHANICS_REL,
        "engine": ENGINE_REL,
        "runtime": RUNTIME_REL,
        "config": CONFIG_REL,
        "town_materializer": TOWN_MATERIALIZER_REL,
        "decay_materializer": DECAY_MATERIALIZER_REL,
    }
    resolved_inputs: dict[str, Path] = {}
    for label, path in paths.items():
        _reject_symlink_components(path, label)
        _require_repository_path(repo_root, path, expected_repository_paths[label], label)
        resolved_inputs[label] = path.resolve(strict=True)
    if len(set(resolved_inputs.values())) != len(resolved_inputs):
        raise CompositionError("all composition input paths must be distinct")
    for label, path in resolved_inputs.items():
        if resolved_output == path or resolved_output in path.parents or path in resolved_output.parents:
            raise CompositionError(f"output directory aliases {label}")

    git_custody = verify_git_custody(repo_root)
    payloads = {label: _read_regular(path, label) for label, path in paths.items()}
    expected_blobs = {
        "source": SOURCE_GIT_BLOB,
        "scheduler": SCHEDULER_GIT_BLOB,
        "mechanics": MECHANICS_GIT_BLOB,
        "engine": ENGINE_GIT_BLOB,
        "runtime": RUNTIME_GIT_BLOB,
        "config": CONFIG_GIT_BLOB,
        "town_materializer": TOWN_MATERIALIZER_GIT_BLOB,
        "decay_materializer": DECAY_MATERIALIZER_GIT_BLOB,
    }
    for label, expected in expected_blobs.items():
        actual = git_blob_sha1(payloads[label])
        if actual != expected:
            raise CompositionError(
                f"{label} Git blob mismatch: expected {expected}, got {actual}"
            )

    texts: dict[str, str] = {}
    for label in ("source", "scheduler", "mechanics", "engine", "runtime"):
        try:
            texts[label] = payloads[label].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CompositionError(f"{label} must be UTF-8: {exc}") from exc
    config = _strict_json_object(payloads["config"], "TITAN config")
    selected_consumer = verify_selected_consumer(texts["runtime"], config)
    town_module, _ = _load_exact_module(
        paths["town_materializer"],
        "_titan_exact_town_materializer",
        TOWN_MATERIALIZER_GIT_BLOB,
    )
    decay_module, _ = _load_exact_module(
        paths["decay_materializer"],
        "_titan_exact_decay_materializer",
        DECAY_MATERIALIZER_GIT_BLOB,
    )

    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=str(output_parent))
    )
    published = False
    try:
        town_source, town_receipt, town_receipt_bytes, final_source, decay_evidence = (
            compose_texts(
                source_text=texts["source"],
                scheduler_text=texts["scheduler"],
                mechanics_text=texts["mechanics"],
                engine_text=texts["engine"],
                town_module=town_module,
                decay_module=decay_module,
            )
        )
        town_source_bytes = town_source.encode("utf-8")
        final_source_bytes = final_source.encode("utf-8")
        _write_fsynced(staging / OUTPUT_TOWN_SOURCE, town_source_bytes)
        _write_fsynced(staging / OUTPUT_TOWN_RECEIPT, town_receipt_bytes)
        _maybe_fault("town", fault_after)
        _write_fsynced(staging / OUTPUT_FINAL_SOURCE, final_source_bytes)
        _maybe_fault("final", fault_after)

        runtime_probe = run_runtime_probe(
            repo_root / LAB_REL,
            staging / OUTPUT_FINAL_SOURCE,
        )
        _maybe_fault("probe", fault_after)

        # Re-read every input before publication.  A donor/source swap during the
        # runtime probe invalidates the transaction instead of being silently sealed.
        for label, path in paths.items():
            if _read_regular(path, label) != payloads[label]:
                raise CompositionError(f"{label} changed during composition")

        receipt_body: dict[str, Any] = {
            "schema": SCHEMA,
            "operation": OPERATION,
            "status": "PASS",
            "git_custody": git_custody,
            "donors": {
                "town_consumption": {
                    "pr": TOWN_PR,
                    "head": TOWN_HEAD,
                    "materializer_path": TOWN_MATERIALIZER_REL.as_posix(),
                    "materializer": _identity(payloads["town_materializer"]),
                    "receipt_schema": town_receipt["schema"],
                },
                "plant_decay": {
                    "pr": DECAY_PR,
                    "head": DECAY_HEAD,
                    "materializer_path": DECAY_MATERIALIZER_REL.as_posix(),
                    "materializer": _identity(payloads["decay_materializer"]),
                    "operation": getattr(decay_module, "OPERATION", None),
                },
            },
            "inputs": {
                label: _identity(payloads[label])
                for label in (
                    "source",
                    "scheduler",
                    "mechanics",
                    "engine",
                    "runtime",
                    "config",
                )
            },
            "composition": {
                "order": ["town_consumption", "plant_decay"],
                "town_postimage": _identity(town_source_bytes),
                "town_receipt": _identity(town_receipt_bytes),
                "town_receipt_postimage_sha256": town_receipt["patched_source_sha256"],
                "decay_authenticated_input_sha256": sha256_bytes(town_source_bytes),
                "final_postimage": _identity(final_source_bytes),
                **decay_evidence,
            },
            "selected_consumer": {
                "static": selected_consumer,
                "dynamic": runtime_probe,
            },
            "publication": {
                "atomic_directory": True,
                "output_files": [
                    OUTPUT_TOWN_SOURCE,
                    OUTPUT_TOWN_RECEIPT,
                    OUTPUT_FINAL_SOURCE,
                    OUTPUT_RECEIPT,
                ],
                "canonical_repository_modified": False,
                "game_or_seed_spend": False,
                "promotion_or_submission_claim": False,
            },
        }
        body_bytes = json.dumps(
            receipt_body, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        receipt = dict(receipt_body)
        receipt["body_sha256"] = sha256_bytes(body_bytes)
        receipt_bytes = (
            json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8")
        _strict_json_object(receipt_bytes, "composition receipt")
        _write_fsynced(staging / OUTPUT_RECEIPT, receipt_bytes)
        _maybe_fault("receipt", fault_after)
        _fsync_directory(staging)

        if output_dir.exists() or output_dir.is_symlink():
            raise CompositionError(f"output directory appeared during publication: {output_dir}")
        os.rename(staging, output_dir)
        published = True
        _fsync_directory(output_parent)
        return receipt
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--scheduler", required=True, type=Path)
    parser.add_argument("--mechanics", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--town-materializer", required=True, type=Path)
    parser.add_argument("--decay-materializer", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = compose(
        repo_root=args.repo_root,
        source_path=args.source,
        scheduler_path=args.scheduler,
        mechanics_path=args.mechanics,
        engine_path=args.engine,
        runtime_path=args.runtime,
        config_path=args.config,
        town_materializer_path=args.town_materializer,
        decay_materializer_path=args.decay_materializer,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "checkout_head": receipt["git_custody"]["checkout_head"],
                "final_postimage_sha256": receipt["composition"]["final_postimage"][
                    "sha256"
                ],
                "body_sha256": receipt["body_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
