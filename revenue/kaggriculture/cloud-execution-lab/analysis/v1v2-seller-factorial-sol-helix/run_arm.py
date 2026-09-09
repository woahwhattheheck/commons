# SPDX-License-Identifier: Apache-2.0
"""Run one closure-bound factorial arm through the official paired engine grid."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
BASE_RUNNER = LAB / "candidates/v3-l02-ledger-tranche/run_panel.py"
OPERATION = "titan-v3-v1v2-seller-factorial-20260909-01"


def _load_base():
    spec = importlib.util.spec_from_file_location("_sol_helix_base_panel", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load base panel runner {BASE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _compact(text: Any, limit: int = 1000) -> str:
    value = " ".join(str(text).split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    status = str(report.get("status", "unknown"))
    arm = str(report.get("arm", "unknown"))
    lines = [
        f"# TITAN V1/V2 seller factorial — `{arm}`",
        "",
        f"Status: **{status.upper()}**",
        f"Expected cells: {report.get('expected_cells', 0)}",
        f"Accepted cells: {(report.get('gate') or {}).get('accepted', 0)}",
        "",
    ]
    errors = list((report.get("gate") or {}).get("errors") or [])
    if report.get("error"):
        errors.insert(0, report["error"])
    if errors:
        lines += ["## Compact errors", ""]
        lines.extend(f"- {_compact(item, 300)}" for item in errors[:24])
    else:
        games = list(report.get("games") or [])
        own = []
        for game in games:
            seat = int(game["candidate_seat"])
            own.append(float(game["scores"][seat]))
        if own:
            lines += [
                "## Absolute arm result",
                "",
                f"Mean own cash: {sum(own) / len(own):.3f}",
                f"Minimum own cash: {min(own):.3f}",
                f"Maximum own cash: {max(own):.3f}",
                "",
            ]
    lines += [
        "This is one arm of a source-level causal screen. It is not a promotion or leaderboard claim.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _preflight_entry(entry: Path, pythonpath: str) -> None:
    code = (
        "import importlib.util, pathlib, sys\n"
        f"p=pathlib.Path({str(entry)!r})\n"
        "s=importlib.util.spec_from_file_location('_sol_helix_bound_probe',p)\n"
        "assert s is not None and s.loader is not None\n"
        "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)\n"
        "assert callable(m.agent)\n"
    )
    with tempfile.TemporaryDirectory(prefix="sol-helix-bound-probe-") as temp:
        env = {
            "PATH": os.defpath,
            "HOME": temp,
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": pythonpath,
        }
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=temp,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            "bound entry preflight failed: "
            + _compact(completed.stderr or completed.stdout, 2000)
        )


def _validate_receipt(receipt: Mapping[str, Any], arm: str, entry: Path, base: Any) -> None:
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
        raise RuntimeError("materialization receipt operation/schema mismatch")
    if receipt.get("arm") != arm:
        raise RuntimeError("materialization receipt arm mismatch")
    expected = ((receipt.get("entrypoint") or {}).get("sha256"))
    actual = base.sha256_file(entry)
    if expected != actual:
        raise RuntimeError(f"entry digest mismatch: expected={expected} actual={actual}")
    closure = receipt.get("closure_bound_at_entry") or {}
    if not isinstance(closure.get("sha256"), str) or int(closure.get("files", 0)) <= 0:
        raise RuntimeError("materialization receipt lacks a valid closure")


def run(
    *,
    arm: str,
    entry: Path,
    receipt_path: Path,
    head: str,
    seeds: Sequence[int],
    opponents: Sequence[str],
    workers: int,
    action_timeout: float,
    startup_timeout: float,
    game_timeout: float,
    output: Path,
    markdown: Path,
) -> int:
    base = _load_base()
    entry = entry.resolve()
    receipt_path = receipt_path.resolve()
    if not entry.is_file() or not receipt_path.is_file():
        raise FileNotFoundError(f"entry/receipt missing: {entry}, {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _validate_receipt(receipt, arm, entry, base)

    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / f"{arm}-shards"
    work.mkdir(parents=True, exist_ok=True)
    patched_evaluator = work / "evaluate-sol-helix.py"
    base.patch_evaluator(base.EVALUATOR, patched_evaluator)
    source_path = base.isolated_source_pythonpath(LAB)
    pythonpath = str(entry.parent) + os.pathsep + source_path
    _preflight_entry(entry, pythonpath)
    base.assert_isolated_source_imports(LAB, pythonpath)

    base._agent_spec = lambda _variant: str(entry) + "::agent"
    opponent_entry_digests = {
        name: base.sha256_file(base.OPPONENTS[name]) for name in opponents
    }
    opponent_roots = {
        "arlene": base.OPPONENTS["arlene"],
        "apex": base.OPPONENTS["apex"].parent,
        "kaito_v43": base.OPPONENTS["kaito_v43"],
        "cok_v10": base.OPPONENTS["cok_v10"],
        "public_bt12": base.OPPONENTS["public_bt12"].parent,
        "v1": base.OPPONENTS["v1"].parent,
    }
    identity = {
        "operation": OPERATION,
        "git_head": head,
        "arm": arm,
        "entrypoint": str(entry),
        "entry_sha256": base.sha256_file(entry),
        "closure": receipt["closure_bound_at_entry"],
        "materialization_receipt_sha256": base.sha256_file(receipt_path),
        "evaluator_source_sha256": base.sha256_file(base.EVALUATOR),
        "evaluator_effective_sha256": base.sha256_file(patched_evaluator),
        "loader_sha256": base.sha256_file(base.LOADER),
        "engine_ref": base.ENGINE_REF,
        "opponent_entry_sha256": opponent_entry_digests,
        "opponent_bundles": {
            name: base.tree_sha256(opponent_roots[name]) for name in opponents
        },
    }
    apex_binary = base.OPPONENTS["apex"].parent / "agent.so"
    if "apex" in opponents:
        if not apex_binary.is_file():
            raise FileNotFoundError(f"compiled Apex binary missing: {apex_binary}")
        identity["generated_apex_binary"] = {
            "sha256": base.sha256_file(apex_binary),
            "bytes": apex_binary.stat().st_size,
        }
    initial: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "status": "running",
        "phase": "development",
        "arm": arm,
        "identity": identity,
        "seeds": list(seeds),
        "opponents": list(opponents),
        "expected_cells": len(base.expected_keys(seeds, opponents)),
        "completed_shards": [],
    }
    base.atomic_json(output, initial)
    _write_markdown(markdown, initial)

    groups = base.shard(list(seeds), workers)
    results: list[dict[str, Any]] = []
    try:
        with ThreadPoolExecutor(max_workers=len(groups)) as executor:
            futures = {
                executor.submit(
                    base.run_evaluator,
                    arm,
                    group,
                    opponents,
                    work,
                    index,
                    action_timeout=action_timeout,
                    startup_timeout=startup_timeout,
                    game_timeout=game_timeout,
                    evaluator=patched_evaluator,
                    pythonpath=pythonpath,
                ): (index, list(group))
                for index, group in enumerate(groups)
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                initial["completed_shards"] = [
                    {
                        "shard": item["shard"],
                        "seeds": item["seeds"],
                        "returncode": item["returncode"],
                    }
                    for item in sorted(results, key=lambda row: int(row["shard"]))
                ]
                base.atomic_json(output, initial)

        games, gate = base.collect_games(
            results,
            arm,
            seeds,
            opponents,
            expected_candidate_sha256=identity["entry_sha256"],
            expected_opponent_sha256=opponent_entry_digests,
            expected_evaluator_sha256=identity["evaluator_effective_sha256"],
            expected_loader_sha256=identity["loader_sha256"],
        )
        report = {
            **initial,
            "status": "complete" if gate["valid"] else "invalid",
            "gate": gate,
            "games": [games[key] for key in sorted(games)],
        }
        base.atomic_json(output, report)
        _write_markdown(markdown, report)
        print(
            json.dumps(
                {
                    "arm": arm,
                    "status": report["status"],
                    "accepted": gate["accepted"],
                    "expected": gate["expected"],
                },
                sort_keys=True,
            )
        )
        return 0 if gate["valid"] else 2
    except BaseException as exc:
        failed = {
            **initial,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}"[:2000],
        }
        try:
            base.atomic_json(output, failed)
            _write_markdown(markdown, failed)
        except Exception:
            pass
        print(json.dumps({"arm": arm, "status": "failed", "error": failed["error"]}))
        return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--entry", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--seeds", default="2611092201,2611092203,2611092205,2611092207")
    parser.add_argument("--opponents", default="arlene,apex,public_bt12,v1")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--game-timeout", type=float, default=180.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    seeds = [int(part) for part in args.seeds.split(",") if part]
    opponents = [part for part in args.opponents.split(",") if part]
    base = _load_base()
    if not seeds or len(seeds) != len(set(seeds)):
        parser.error("seeds must be distinct and nonempty")
    if not opponents or len(opponents) != len(set(opponents)):
        parser.error("opponents must be distinct and nonempty")
    unknown = [name for name in opponents if name not in base.OPPONENTS]
    if unknown:
        parser.error(f"unknown opponents: {unknown}")
    if args.workers <= 0 or any(
        not math.isfinite(value) or value <= 0
        for value in (args.action_timeout, args.startup_timeout, args.game_timeout)
    ):
        parser.error("workers/timeouts must be positive and finite")
    return run(
        arm=args.arm,
        entry=args.entry,
        receipt_path=args.receipt,
        head=args.head,
        seeds=seeds,
        opponents=opponents,
        workers=args.workers,
        action_timeout=args.action_timeout,
        startup_timeout=args.startup_timeout,
        game_timeout=args.game_timeout,
        output=args.output,
        markdown=args.markdown,
    )


if __name__ == "__main__":
    raise SystemExit(main())
