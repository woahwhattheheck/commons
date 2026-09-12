# SPDX-License-Identifier: Apache-2.0
"""Exact-loader oracle for cross-episode process-state isolation.

Run the same two full games in opposite order in two isolated workers. Each
scenario is therefore observed once as the first game in a fresh process and
once after another complete game while the candidate callable, imported runtime
modules and process caches remain alive. Exact action hashes and terminal
outcomes must agree, and step 0 must replace the prior TitanAgent instance.

The candidate is called on one persistent worker thread per process, matching
the existing 719-call worker-episode oracle and exercising the thread deadline
guard across the episode boundary.

This is a verification harness only; it does not alter production policy.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SCENARIOS = {
    "A": {"seed": 9922999, "seat": 0},
    "B": {"seed": 1909087201, "seat": 1},
}


def _load_official(root: Path):
    """Load the same pinned raw-loader helpers as test_worker_episode.py."""
    sys.path.insert(0, str(root))
    sys.path.insert(1, str(root / "checks"))

    def offline(event, args):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise RuntimeError("offline reset-invariance worker")

    sys.addaudithook(offline)
    from test_engine_semantics import EngineSemantics

    EngineSemantics.setUpClass()
    namespace = dict(globals(), InvalidArgument=ValueError, NotFound=FileNotFoundError)
    for path, names in [
        (root / "checks/reference/engine/utils.py", {"read_file"}),
        (
            root / "checks/reference/evaluator/official_agent.py",
            {"is_url", "get_last_callable", "build_agent"},
        ),
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        nodes = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in names
        ]
        if len(nodes) != len(names):
            raise AssertionError(f"raw-loader helper mismatch in {path}")
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    candidate, _ = namespace["build_agent"](str(root / "main.py"), {}, "kaggriculture")
    return EngineSemantics, candidate


def _entrypoint(candidate):
    """Recover loaded main.py::agent without assuming raw-loader closure order."""
    for cell in candidate.__closure__ or ():
        try:
            value = cell.cell_contents
        except ValueError:
            continue
        globals_dict = getattr(value, "__globals__", None)
        if callable(value) and isinstance(globals_dict, dict) and "_INSTANCE" in globals_dict:
            return value
    raise AssertionError("official raw-loader closure does not expose main.py::agent")


def _configuration(engine, evaluator, seed: int):
    cfg = evaluator.Struct(
        {
            key: value.get("default") if isinstance(value, dict) else value
            for key, value in engine.specification["configuration"].items()
        }
    )
    cfg.seed = seed
    return cfg


def _run_game(
    engine_semantics,
    candidate,
    executor: ThreadPoolExecutor,
    scenario: dict[str, int],
    prior_instance,
):
    engine = engine_semantics.engine
    evaluator = engine_semantics.ev
    cfg = _configuration(engine, evaluator, scenario["seed"])
    seat = scenario["seat"]
    rival = 1 - seat
    env = evaluator.Struct(configuration=cfg, done=False, info={})
    state = [
        evaluator.Struct(observation=evaluator.Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    engine.interpreter(state, env)

    trace = hashlib.sha256()
    loaded_entrypoint = _entrypoint(candidate)
    active_instance = None
    replacement_verified = False
    calls = 0
    last_step = None

    for step in range(720):
        for player in (0, 1):
            state[player].observation.step = step
        action = executor.submit(
            candidate, copy.deepcopy(state[seat].observation), cfg
        ).result(timeout=2)
        encoded = json.dumps(action, sort_keys=True, separators=(",", ":"), allow_nan=False)
        current = loaded_entrypoint.__globals__.get("_INSTANCE")
        if current is None:
            raise AssertionError(("missing canonical singleton", scenario, step))
        diagnostics = dict(current.diagnostics)
        if diagnostics.get("parent_calls") != 1 or diagnostics.get("status") != "completed":
            raise AssertionError(("non-completed action", scenario, step, diagnostics))
        if step == 0:
            if prior_instance is not None and current is prior_instance:
                raise AssertionError(("step zero reused prior TitanAgent", scenario))
            active_instance = current
            replacement_verified = True
        elif current is not active_instance:
            raise AssertionError(("singleton changed inside completed episode", scenario, step))

        trace.update(encoded.encode("utf-8") + b"\n")
        state[seat].action = json.loads(encoded)
        state[rival].action = engine.starter_agent(copy.deepcopy(state[rival].observation))
        engine.interpreter(state, env)
        calls += 1
        last_step = step
        if any(player.status == "DONE" for player in state):
            break

    if not replacement_verified or active_instance is None:
        raise AssertionError(("episode never verified singleton replacement", scenario))
    return {
        "seed": scenario["seed"],
        "seat": seat,
        "calls": calls,
        "last_step": last_step,
        "action_sha256": trace.hexdigest(),
        "status": [player.status for player in state],
        "rewards": [player.reward for player in state],
        "singleton_replaced": True,
    }, active_instance


def worker(root: Path, order: list[str]) -> dict[str, Any]:
    engine_semantics, candidate = _load_official(root)
    results = {}
    prior_instance = None
    with ThreadPoolExecutor(1) as executor:
        for name in order:
            result, prior_instance = _run_game(
                engine_semantics, candidate, executor, SCENARIOS[name], prior_instance
            )
            results[name] = result

    import titan_runtime

    cache_keys = sorted(f"{name}:{Path(path).name}" for name, path in titan_runtime._MODULE_CACHE)
    return {
        "method": (
            "Exact official raw-loader helpers + official interpreter; same candidate callable "
            "on one persistent worker thread for two full games; offline; reverse-order differential"
        ),
        "order": order,
        "results": results,
        "module_cache_keys": cache_keys,
        "engine_sha256": engine_semantics.hashes,
        "raw_loader_sha256": hashlib.sha256(
            (root / "checks/reference/evaluator/official_agent.py").read_bytes()
        ).hexdigest(),
        "source_manifest_sha256": hashlib.sha256((root / "SOURCE.json").read_bytes()).hexdigest(),
    }


def _run_worker(script: Path, root: Path, order: list[str], output: Path):
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            str(script),
            "--worker",
            str(root),
            "--order",
            *order,
            "--output",
            str(output),
        ],
        cwd=root.parent,
        capture_output=True,
        text=True,
        timeout=360,
    )
    if process.returncode:
        raise RuntimeError(process.stdout + process.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def _scenario_projection(result: dict[str, Any], name: str):
    game = result["results"][name]
    return {
        key: game[key]
        for key in ("seed", "seat", "calls", "last_step", "action_sha256", "status", "rewards")
    }


def verify() -> dict[str, Any]:
    from build_integrated import verify_current

    receipt = verify_current()
    archive = ROOT / "exports/titan-current.tar.gz"
    with tempfile.TemporaryDirectory(prefix="titan-reset-clean-", dir="/tmp") as folder:
        base = Path(folder)
        extracted = base / "candidate"
        extracted.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(extracted, filter="data")
        ab_path = base / "ab.json"
        ba_path = base / "ba.json"
        ab = _run_worker(Path(__file__).resolve(), extracted, ["A", "B"], ab_path)
        ba = _run_worker(Path(__file__).resolve(), extracted, ["B", "A"], ba_path)

    mismatches = {}
    for name in sorted(SCENARIOS):
        first = _scenario_projection(ab, name)
        second = _scenario_projection(ba, name)
        if first != second:
            mismatches[name] = {"AB": first, "BA": second}
    if ab["module_cache_keys"] != ba["module_cache_keys"]:
        mismatches["module_cache_keys"] = {
            "AB": ab["module_cache_keys"],
            "BA": ba["module_cache_keys"],
        }
    if mismatches:
        raise AssertionError(json.dumps(mismatches, indent=2, sort_keys=True))

    return {
        "schema": "titan-v4-reset-invariance/v1",
        "archive_sha256": receipt["sha256"],
        "source_manifest_sha256": ab["source_manifest_sha256"],
        "raw_loader_sha256": ab["raw_loader_sha256"],
        "engine_sha256": ab["engine_sha256"],
        "orders": [ab["order"], ba["order"]],
        "scenarios": {name: _scenario_projection(ab, name) for name in sorted(SCENARIOS)},
        "module_cache_keys": ab["module_cache_keys"],
        "result": "PASS",
        "claim": (
            "For these two full official-interpreter games on one persistent worker thread, "
            "action trace and terminal result are identical whether the game runs first in a "
            "fresh process or second after the other game; step zero replaces the prior "
            "TitanAgent singleton."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--order", nargs="+", choices=sorted(SCENARIOS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        if not args.order or args.output is None:
            parser.error("--worker requires --order and --output")
        report = worker(args.worker, args.order)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    if args.order or args.output:
        parser.error("--order/--output are worker-only")
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
