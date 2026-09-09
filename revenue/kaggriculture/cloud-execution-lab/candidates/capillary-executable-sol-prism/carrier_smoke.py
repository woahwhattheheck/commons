# SPDX-License-Identifier: Apache-2.0
"""Prove the Capillary private-arena carrier in stripped fresh processes.

This is not a score panel.  It proves that the exact candidate constructs and
initializes without repository ``PYTHONPATH``, then returns every requested
action through the pinned process-isolated evaluator in both seats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
CANDIDATE = HERE / "candidate.py"
EVALUATOR = KAG / "cloud-eval" / "evaluate.py"
LOADER = KAG / "20260907-offline-agent" / "evaluate.py"
ENGINE = LAB / "reference" / "engine"

EXPECTED_ARCHIVE_SHA256 = "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86"
EXPECTED_RUNTIME_FILES = 109
EXPECTED_EVALUATOR_GIT_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_LOADER_GIT_BLOB = "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5"
EXPECTED_OVERLAY_BLOBS = {
    "jit_seed_staging.py": "e1cf2485ab869cf3c6f5eec455b0a25f6aeaa505",
    "jit_seed_order_rail.py": "f5d2c3775bc527ef7f950a850eac8036bd71e865",
    "titan_capillary.py": "afbfb0859d7a3219d2f3e5c4178d72c128f31911",
    "capillary_main.py": "e545a65d99f81f7982ee70fd4c336b78ad957afc",
}
SEED = 2611092201
EPISODE_STEPS = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def minimal_environment(home: Path) -> dict[str, str]:
    """Match the evaluator's intentionally stripped worker environment."""
    return {
        "PATH": os.defpath,
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def completed(command: list[str], *, cwd: Path, env: dict[str, str], timeout: float):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "isolated command failed "
            f"(rc={result.returncode}):\n"
            f"stdout tail:\n{result.stdout[-6000:]}\n"
            f"stderr tail:\n{result.stderr[-6000:]}"
        )
    return result


def fresh_private_runtime_smoke() -> dict[str, Any]:
    """Construct and initialize the real candidate under ``python -I``."""
    probe = r'''
import importlib.util
import json
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve(strict=True)
sys.path.insert(0, str(path.parent))
name = "_sol_prism_fresh_process_candidate"
spec = importlib.util.spec_from_file_location(name, path)
if spec is None or spec.loader is None:
    raise RuntimeError("candidate spec unavailable")
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)

arena = module._ARENA_ROOT.resolve()
config = json.loads((arena / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
canonical = module._ENTRY._canonical_module()
instance = canonical._new_instance(arena, dict(config))
instance._initialize()

import frozen_selected
import jit_seed_order_rail
import jit_seed_staging
import observed_clone
import scheduler
import titan_capillary
import titan_runtime

def inside(value):
    origin = Path(value).resolve()
    try:
        origin.relative_to(arena)
        return True
    except ValueError:
        return False

compile_report = dict(instance._capillary_compile_report)
detach_report = dict(instance._capillary_route_detach_report)
payload = {
    "mro": [kind.__name__ for kind in type(instance).__mro__[:3]],
    "compile_certified": compile_report.get("certified"),
    "compile_changed": compile_report.get("changed"),
    "compile_reason": compile_report.get("reason"),
    "route_detached": detach_report.get("detached"),
    "route_detach_reason": detach_report.get("reason"),
    "spatial_owns_controller_routes": (
        instance.spatial is not None
        and instance.spatial._crop_routes is instance.controller.R
    ),
    "archive_sha256": module._ARENA_RECEIPT.get("archive_sha256"),
    "runtime_files": module._ARENA_RECEIPT.get("runtime_files"),
    "archive_members": module._ARENA_RECEIPT.get("archive_members"),
    "overlay_git_blobs": {
        name: row.get("git_blob")
        for name, row in (module._ARENA_RECEIPT.get("overlays") or {}).items()
    },
    "origins_inside_private_arena": {
        "entry": inside(module._ENTRY.__file__),
        "canonical_main": inside(canonical.__file__),
        "frozen_selected": inside(frozen_selected.__file__),
        "scheduler": inside(scheduler.__file__),
        "observed_clone": inside(observed_clone.__file__),
        "titan_runtime": inside(titan_runtime.__file__),
        "titan_capillary": inside(titan_capillary.__file__),
        "jit_seed_staging": inside(jit_seed_staging.__file__),
        "jit_seed_order_rail": inside(jit_seed_order_rail.__file__),
    },
    "ambient_lab_on_sys_path": str(module.LAB.resolve()) in sys.path,
}
print(json.dumps(payload, sort_keys=True, allow_nan=False))
'''
    with tempfile.TemporaryDirectory(prefix="sol-prism-capillary-init-") as raw:
        home = Path(raw).resolve()
        result = completed(
            [sys.executable, "-I", "-B", "-c", probe, str(CANDIDATE.resolve())],
            cwd=home,
            env=minimal_environment(home),
            timeout=60,
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(
            f"fresh-process probe emitted {len(lines)} nonempty lines"
        )
    try:
        receipt = json.loads(lines[0])
    except ValueError as exc:
        raise RuntimeError("fresh-process probe did not emit strict JSON") from exc

    if receipt.get("mro") != [
        "FinalPressureAgent",
        "CapillaryTitanAgent",
        "TitanAgent",
    ]:
        raise RuntimeError(f"candidate MRO drift: {receipt.get('mro')!r}")
    if (
        receipt.get("compile_certified") is not True
        or receipt.get("compile_changed") is not True
        or receipt.get("compile_reason") != "staged"
    ):
        raise RuntimeError(f"Capillary compiler did not activate: {receipt}")
    if (
        receipt.get("route_detached") is not True
        or receipt.get("route_detach_reason") != "private_route_bank_bound"
        or receipt.get("spatial_owns_controller_routes") is not True
    ):
        raise RuntimeError(f"Capillary route ownership failed: {receipt}")
    if receipt.get("archive_sha256") != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("fresh-process archive identity mismatch")
    if receipt.get("runtime_files") != EXPECTED_RUNTIME_FILES:
        raise RuntimeError("fresh-process runtime cardinality mismatch")
    if receipt.get("archive_members") != EXPECTED_RUNTIME_FILES + 1:
        raise RuntimeError("fresh-process archive-member cardinality mismatch")
    if receipt.get("overlay_git_blobs") != EXPECTED_OVERLAY_BLOBS:
        raise RuntimeError("fresh-process Capillary overlay identity mismatch")
    origins = receipt.get("origins_inside_private_arena")
    if not isinstance(origins, dict) or not origins or set(origins.values()) != {True}:
        raise RuntimeError(f"runtime import escaped private arena: {origins}")
    if receipt.get("ambient_lab_on_sys_path") is not False:
        raise RuntimeError("candidate depended on mutable repository lab sys.path")
    return receipt


def evaluator_first_actions_smoke() -> dict[str, Any]:
    """Run the exact repository evaluator through real actions in both seats."""
    if git_blob_sha1(EVALUATOR) != EXPECTED_EVALUATOR_GIT_BLOB:
        raise RuntimeError("pinned evaluator source drift")
    if git_blob_sha1(LOADER) != EXPECTED_LOADER_GIT_BLOB:
        raise RuntimeError("pinned evaluator loader drift")

    with tempfile.TemporaryDirectory(prefix="sol-prism-capillary-evaluator-") as raw:
        home = Path(raw).resolve()
        output = home / "EVALUATOR-SMOKE.json"
        result = completed(
            [
                sys.executable,
                "-B",
                str(EVALUATOR.resolve()),
                "--engine-dir",
                str(ENGINE.resolve()),
                "--loader",
                str(LOADER.resolve()),
                "--candidate",
                str(CANDIDATE.resolve()) + "::agent",
                "--opponent",
                "starter=official_starter",
                "--seeds",
                str(SEED),
                "--rng-seed",
                "20260909",
                "--action-timeout",
                "1.0",
                "--startup-timeout",
                "15",
                "--game-timeout",
                "60",
                "--episode-steps",
                str(EPISODE_STEPS),
                "--output",
                str(output),
            ],
            cwd=home,
            env=minimal_environment(home),
            timeout=180,
        )
        if not output.is_file():
            raise RuntimeError("pinned evaluator produced no final report")
        try:
            report = json.loads(output.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise RuntimeError("pinned evaluator report is not strict JSON") from exc

    progress = report.get("progress") or {}
    games = report.get("games")
    if report.get("schema_version") != 1 or progress.get("state") != "complete":
        raise RuntimeError("pinned evaluator did not close a complete report")
    if report.get("candidate", {}).get("sha256") != sha256_file(CANDIDATE):
        raise RuntimeError("evaluator candidate entry digest mismatch")
    if report.get("evaluator_sha256") != sha256_file(EVALUATOR):
        raise RuntimeError("evaluator self digest mismatch")
    if report.get("loader_sha256") != sha256_file(LOADER):
        raise RuntimeError("evaluator loader digest mismatch")
    if not isinstance(games, list) or len(games) != 2:
        raise RuntimeError("expected one seed in both candidate seats")

    normalized_games: list[dict[str, Any]] = []
    seen_seats: set[int] = set()
    for game in games:
        seat = game.get("candidate_seat")
        if type(seat) is not int or seat not in (0, 1) or seat in seen_seats:
            raise RuntimeError(f"invalid or duplicate candidate seat: {seat!r}")
        seen_seats.add(seat)
        scores = game.get("scores")
        if (
            game.get("opponent") != "starter"
            or game.get("seed") != SEED
            or game.get("status") != "complete"
            or game.get("failure") is not None
            or type(game.get("steps")) is not int
            or game["steps"] != EPISODE_STEPS - 1
            or not isinstance(scores, list)
            or len(scores) != 2
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in scores
            )
        ):
            raise RuntimeError(f"invalid evaluator smoke game for seat {seat}: {game}")
        actors = game.get("actors")
        if not isinstance(actors, list) or len(actors) != 2:
            raise RuntimeError("evaluator actor custody missing")
        candidate_actor = actors[seat]
        calls = candidate_actor.get("calls") if isinstance(candidate_actor, dict) else None
        if type(calls) is not int or calls != game["steps"] or calls <= 0:
            raise RuntimeError(
                f"candidate did not return every requested action in seat {seat}: {calls!r}"
            )
        normalized_games.append(
            {
                "candidate_seat": seat,
                "status": game["status"],
                "steps": game["steps"],
                "candidate_actor_calls": calls,
                "candidate_actor_exit_code": candidate_actor.get("exit_code"),
                "scores": scores,
            }
        )
    if seen_seats != {0, 1}:
        raise RuntimeError("both candidate seats were not exercised")
    normalized_games.sort(key=lambda row: row["candidate_seat"])
    return {
        "candidate_entry_sha256": report["candidate"]["sha256"],
        "evaluator_sha256": report["evaluator_sha256"],
        "loader_sha256": report["loader_sha256"],
        "engine_sha256": report.get("engine_sha256"),
        "seed": SEED,
        "episode_steps": EPISODE_STEPS,
        "games": normalized_games,
        "stdout_summary_present": "SUMMARY " in result.stdout,
    }


def run() -> dict[str, Any]:
    for path in (CANDIDATE, EVALUATOR, LOADER, ENGINE / "kaggriculture.py"):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"carrier-smoke dependency is not a regular file: {path}")
    return {
        "schema_version": 1,
        "operation": "titan-capillary-executable-carrier-20260909-sol-prism-01",
        "scope": "private executable carrier and first actions only; no score claim",
        "fresh_private_runtime": fresh_private_runtime_smoke(),
        "pinned_evaluator": evaluator_first_actions_smoke(),
        "decision": "PASS",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    result = run()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
