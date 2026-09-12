#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Record exact per-step action witnesses for two candidate arms on one world.

This is evidence tooling only. It reuses the pinned generic evaluator without
modifying it, intercepting Actor.act in-process so the actual worker response
used by the official interpreter is also hashed for causal comparison.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import tempfile
import uuid
from typing import Any

SCHEMA = "titan-v5-production-action-divergence/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class WitnessError(ValueError):
    pass


def _encoded(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _read_regular(path: Path) -> bytes:
    path = Path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise WitnessError(f"cannot open ordinary file {path}: {exc}") from exc
    try:
        st = os.fstat(fd)
        if not os.path.isfile(path) or not (st.st_mode & 0o170000) == 0o100000:
            raise WitnessError(f"path is not an ordinary file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(_read_regular(path)).hexdigest()


def _expected_sha(value: str, field: str) -> str:
    if _SHA256_RE.fullmatch(value or "") is None:
        raise WitnessError(f"{field} must be a lowercase SHA256")
    return value


def _verify_file(path: Path, expected: str, field: str) -> dict[str, Any]:
    expected = _expected_sha(expected, field)
    actual = _sha_file(path)
    if actual != expected:
        raise WitnessError(f"{field} mismatch: {actual} != {expected}")
    return {"path": str(Path(path).resolve()), "sha256": actual}


def _spec_path(spec: str) -> Path:
    path_text, sep, callable_name = spec.partition("::")
    if not path_text or (sep and not callable_name):
        raise WitnessError(f"invalid agent spec: {spec!r}")
    path = Path(path_text).resolve(strict=True)
    _read_regular(path)
    return path


def _inspect_spec_dependencies(spec: str) -> dict[str, str]:
    spec_path = _spec_path(spec)
    resolved_spec = spec_path.resolve()
    deps: dict[str, str] = {str(resolved_spec): _sha_file(resolved_spec)}
    try:
        content = spec_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(spec_path))
    except Exception:
        return deps

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value.strip()
            if val and ("/" in val or "\\" in val) and not val.startswith("http"):
                try:
                    candidate = Path(val).resolve()
                    if candidate.is_file():
                        deps[str(candidate)] = _sha_file(candidate)
                        for sibling in candidate.parent.glob("*"):
                            if sibling.is_file() and sibling.suffix in (
                                ".py",
                                ".so",
                                ".json",
                                ".hpp",
                                ".cpp",
                            ):
                                deps[str(sibling.resolve())] = _sha_file(sibling)
                except Exception:
                    pass
    try:
        py_siblings = [p for p in spec_path.parent.glob("*.py") if p.is_file()]
        if len(py_siblings) <= 50:
            for sib in py_siblings:
                deps[str(sib.resolve())] = _sha_file(sib)
    except Exception:
        pass
    return deps


def _verify_actor_custody(spec: str, expected_deps: dict[str, dict[str, str]]) -> None:
    deps = expected_deps.get(spec)
    if deps is None:
        try:
            resolved_str = str(_spec_path(spec).resolve())
            for d in expected_deps.values():
                if resolved_str in d:
                    deps = d
                    break
        except Exception:
            pass
    if deps is None:
        raise WitnessError(f"Actor execution-custody failed: unknown spec {spec}")
    for path_str, expected_sha in deps.items():
        p = Path(path_str)
        if not p.is_file():
            raise WitnessError(
                f"Actor execution-custody violation for {spec}: dependency {p} missing"
            )
        actual_sha = _sha_file(p)
        if actual_sha != expected_sha:
            raise WitnessError(
                f"Actor execution-custody violation for {spec}: "
                f"file {p} drifted (actual {actual_sha} != expected {expected_sha})"
            )



def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        f"_titan_action_witness_{uuid.uuid4().hex}", path
    )
    if spec is None or spec.loader is None:
        raise WitnessError(f"cannot import evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_json(value: Any) -> Any:
    return json.loads(_encoded(value))


def _record_step(
    records: dict[str, list[dict[str, Any]]],
    actor_spec: str,
    observation: Any,
    response: dict[str, Any],
) -> None:
    step = observation.get("step") if isinstance(observation, dict) else None
    if type(step) is not int or step < 0:
        raise WitnessError("recorded observation lacks a nonnegative integer step")
    row: dict[str, Any] = {
        "step": step,
        "observation_sha256": _digest(observation),
        "response_kind": response.get("kind"),
    }
    if response.get("kind") == "action":
        action = response.get("action")
        if type(action) is not dict:
            raise WitnessError("evaluator returned non-object action")
        row["action_sha256"] = _digest(action)
        row["action"] = _copy_json(action)
    records.setdefault(actor_spec, []).append(row)


def _validate_trace(rows: list[dict[str, Any]], label: str) -> None:
    if not rows:
        raise WitnessError(f"{label} trace is empty")
    steps = [row.get("step") for row in rows]
    if any(type(step) is not int or step < 0 for step in steps):
        raise WitnessError(f"{label} trace has invalid steps")
    if steps != list(range(len(rows))):
        raise WitnessError(f"{label} trace steps are not contiguous from zero")
    for row in rows:
        if row.get("response_kind") != "action":
            raise WitnessError(
                f"{label} step {row['step']} is not a completed action response"
            )
        _expected_sha(row.get("observation_sha256", ""), "observation_sha256")
        _expected_sha(row.get("action_sha256", ""), "action_sha256")


def _first_diff(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    field: str,
) -> int | None:
    if len(left) != len(right):
        raise WitnessError("trace lengths differ")
    for lrow, rrow in zip(left, right):
        if lrow["step"] != rrow["step"]:
            raise WitnessError("trace step topology differs")
        if lrow[field] != rrow[field]:
            return lrow["step"]
    return None


def _compact_trace(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain the complete hash-bearing trace without duplicating full actions."""
    return [
        {
            "step": row["step"],
            "observation_sha256": row["observation_sha256"],
            "action_sha256": row["action_sha256"],
        }
        for row in rows
    ]


def _window(
    left_candidate: list[dict[str, Any]],
    right_candidate: list[dict[str, Any]],
    left_opponent: list[dict[str, Any]],
    right_opponent: list[dict[str, Any]],
    center: int | None,
    radius: int,
) -> list[dict[str, Any]]:
    if center is None:
        return []
    start = max(0, center - radius)
    stop = min(len(left_candidate), center + radius + 1)
    rows: list[dict[str, Any]] = []
    for step in range(start, stop):
        rows.append({
            "step": step,
            "left_candidate": copy.deepcopy(left_candidate[step]),
            "right_candidate": copy.deepcopy(right_candidate[step]),
            "left_opponent": copy.deepcopy(left_opponent[step]),
            "right_opponent": copy.deepcopy(right_opponent[step]),
        })
    return rows


def compare_traces(
    left_candidate: list[dict[str, Any]],
    right_candidate: list[dict[str, Any]],
    left_opponent: list[dict[str, Any]],
    right_opponent: list[dict[str, Any]],
    *,
    radius: int = 2,
) -> dict[str, Any]:
    for label, rows in (
        ("left_candidate", left_candidate),
        ("right_candidate", right_candidate),
        ("left_opponent", left_opponent),
        ("right_opponent", right_opponent),
    ):
        _validate_trace(rows, label)
    lengths = {len(rows) for rows in (
        left_candidate, right_candidate, left_opponent, right_opponent
    )}
    if len(lengths) != 1:
        raise WitnessError("candidate/opponent trace lengths differ")
    if type(radius) is not int or radius < 0 or radius > 12:
        raise WitnessError("window radius must be an integer from 0 through 12")

    candidate_action = _first_diff(
        left_candidate, right_candidate, "action_sha256"
    )
    candidate_observation = _first_diff(
        left_candidate, right_candidate, "observation_sha256"
    )
    opponent_action = _first_diff(
        left_opponent, right_opponent, "action_sha256"
    )
    opponent_observation = _first_diff(
        left_opponent, right_opponent, "observation_sha256"
    )
    action_points = [
        step for step in (candidate_action, opponent_action) if step is not None
    ]
    first_any_action = min(action_points) if action_points else None
    causal_candidate_first = (
        candidate_action is not None
        and (opponent_action is None or candidate_action < opponent_action)
        and (
            candidate_observation is None
            or candidate_observation > candidate_action
        )
        and (
            opponent_observation is None
            or opponent_observation > candidate_action
        )
    )
    center = first_any_action
    trace_vectors = {
        "left_candidate": _compact_trace(left_candidate),
        "right_candidate": _compact_trace(right_candidate),
        "left_opponent": _compact_trace(left_opponent),
        "right_opponent": _compact_trace(right_opponent),
    }
    return {
        "steps": next(iter(lengths)),
        "first_candidate_action_divergence_step": candidate_action,
        "first_candidate_observation_divergence_step": candidate_observation,
        "first_opponent_action_divergence_step": opponent_action,
        "first_opponent_observation_divergence_step": opponent_observation,
        "first_any_action_divergence_step": first_any_action,
        "candidate_action_is_first_observed_divergence": causal_candidate_first,
        "all_actions_identical": first_any_action is None,
        "window_radius": radius,
        "witness_window": _window(
            left_candidate,
            right_candidate,
            left_opponent,
            right_opponent,
            center,
            radius,
        ),
        "trace_vectors": trace_vectors,
        "left_candidate_trace_sha256": _digest([
            {k: v for k, v in row.items() if k != "action"}
            for row in left_candidate
        ]),
        "right_candidate_trace_sha256": _digest([
            {k: v for k, v in row.items() if k != "action"}
            for row in right_candidate
        ]),
        "left_opponent_trace_sha256": _digest([
            {k: v for k, v in row.items() if k != "action"}
            for row in left_opponent
        ]),
        "right_opponent_trace_sha256": _digest([
            {k: v for k, v in row.items() if k != "action"}
            for row in right_opponent
        ]),
    }


def _run_arm(
    evaluator: Any,
    engine: Any,
    *,
    candidate_spec: str,
    opponent_spec: str,
    engine_dir: Path,
    loader: Path,
    seed: int,
    candidate_seat: int,
    rng_seed: int,
    action_timeout: float,
    startup_timeout: float,
    game_timeout: float,
    expected_deps: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    base_actor = evaluator.Actor
    records: dict[str, list[dict[str, Any]]] = {}

    class RecordingActor(base_actor):
        def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
            _verify_actor_custody(spec, expected_deps)
            super().__init__(spec, cache, loader, rng_seed, startup_timeout)
            _verify_actor_custody(spec, expected_deps)

        def act(self, observation, configuration, timeout):
            response = base_actor.act(self, observation, configuration, timeout)
            _record_step(records, self.spec, observation, response)
            return response

        def close(self):
            try:
                _verify_actor_custody(self.spec, expected_deps)
            finally:
                super().close()

    evaluator.Actor = RecordingActor
    try:
        specs = (
            [candidate_spec, opponent_spec]
            if candidate_seat == 0
            else [opponent_spec, candidate_spec]
        )
        result = evaluator.play(
            engine,
            specs,
            engine_dir,
            loader,
            seed,
            candidate_seat,
            rng_seed=rng_seed,
            action_timeout=action_timeout,
            startup_timeout=startup_timeout,
            game_timeout=game_timeout,
        )
    finally:
        evaluator.Actor = base_actor
    return result, records


def _finite_positive(value: float, field: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise WitnessError(f"{field} must be a finite positive number")
    return float(value)


def _parse_seats(text: str) -> list[int]:
    try:
        seats = [int(piece) for piece in text.split(",") if piece != ""]
    except ValueError as exc:
        raise WitnessError("seats must be comma-separated 0/1 values") from exc
    if not seats or len(seats) != len(set(seats)) or any(s not in (0, 1) for s in seats):
        raise WitnessError("seats must be a unique nonempty subset of 0,1")
    return seats


def run_witness(args: argparse.Namespace) -> dict[str, Any]:
    evaluator_path = Path(args.evaluator).resolve(strict=True)
    loader_path = Path(args.loader).resolve(strict=True)
    engine_dir = Path(args.engine_dir).resolve(strict=True)
    left_archive = Path(args.left_archive).resolve(strict=True)
    right_archive = Path(args.right_archive).resolve(strict=True)

    evaluator_authority = _verify_file(
        evaluator_path, args.expected_evaluator_sha256, "expected_evaluator_sha256"
    )
    loader_authority = _verify_file(
        loader_path, args.expected_loader_sha256, "expected_loader_sha256"
    )
    left_archive_authority = _verify_file(
        left_archive, args.left_archive_sha256, "left_archive_sha256"
    )
    right_archive_authority = _verify_file(
        right_archive, args.right_archive_sha256, "right_archive_sha256"
    )
    left_spec_path = _spec_path(args.left_candidate)
    right_spec_path = _spec_path(args.right_candidate)
    opponent_spec_path = _spec_path(args.opponent)

    # Bind expected entry SHAs and complete runtime dependency commitments before execution:
    expected_deps: dict[str, dict[str, str]] = {
        args.left_candidate: _inspect_spec_dependencies(args.left_candidate),
        args.right_candidate: _inspect_spec_dependencies(args.right_candidate),
        args.opponent: _inspect_spec_dependencies(args.opponent),
    }
    expected_entry_shas = {
        "left": expected_deps[args.left_candidate][str(left_spec_path.resolve())],
        "right": expected_deps[args.right_candidate][str(right_spec_path.resolve())],
        "opponent": expected_deps[args.opponent][str(opponent_spec_path.resolve())],
    }

    evaluator = _load_module(evaluator_path)
    engine, engine_sha256 = evaluator.get_engine(engine_dir, loader_path)
    if type(engine_sha256) is not dict or not engine_sha256:
        raise WitnessError("evaluator did not return engine SHA256 authority")

    seats = _parse_seats(args.seats)
    action_timeout = _finite_positive(args.action_timeout, "action_timeout")
    startup_timeout = _finite_positive(args.startup_timeout, "startup_timeout")
    game_timeout = _finite_positive(args.game_timeout, "game_timeout")
    if type(args.seed) is not int or args.seed < 0:
        raise WitnessError("seed must be a nonnegative integer")
    if type(args.rng_seed) is not int or args.rng_seed < 0:
        raise WitnessError("rng_seed must be a nonnegative integer")

    rows: list[dict[str, Any]] = []
    for seat in seats:
        left_result, left_records = _run_arm(
            evaluator,
            engine,
            candidate_spec=args.left_candidate,
            opponent_spec=args.opponent,
            engine_dir=engine_dir,
            loader=loader_path,
            seed=args.seed,
            candidate_seat=seat,
            rng_seed=args.rng_seed,
            action_timeout=action_timeout,
            startup_timeout=startup_timeout,
            game_timeout=game_timeout,
            expected_deps=expected_deps,
        )
        right_result, right_records = _run_arm(
            evaluator,
            engine,
            candidate_spec=args.right_candidate,
            opponent_spec=args.opponent,
            engine_dir=engine_dir,
            loader=loader_path,
            seed=args.seed,
            candidate_seat=seat,
            rng_seed=args.rng_seed,
            action_timeout=action_timeout,
            startup_timeout=startup_timeout,
            game_timeout=game_timeout,
            expected_deps=expected_deps,
        )
        if left_result.get("status") != "complete" or right_result.get("status") != "complete":
            raise WitnessError(
                f"seat {seat} did not complete both arms: "
                f"left={left_result.get('status')} right={right_result.get('status')}"
            )
        try:
            left_candidate = left_records[args.left_candidate]
            right_candidate = right_records[args.right_candidate]
            left_opponent = left_records[args.opponent]
            right_opponent = right_records[args.opponent]
        except KeyError as exc:
            raise WitnessError(f"missing recorded actor trace: {exc}") from exc
        comparison = compare_traces(
            left_candidate,
            right_candidate,
            left_opponent,
            right_opponent,
            radius=args.window_radius,
        )
        rows.append({
            "candidate_seat": seat,
            "left_result": left_result,
            "right_result": right_result,
            "comparison": comparison,
        })

    # Re-verify all specs and dependencies before certifying authority:
    for spec in (args.left_candidate, args.right_candidate, args.opponent):
        _verify_actor_custody(spec, expected_deps)

    authority = {
        "evaluator": evaluator_authority,
        "loader": loader_authority,
        "engine_sha256": engine_sha256,
        "left_archive": left_archive_authority,
        "right_archive": right_archive_authority,
        "left_entry_sha256": expected_entry_shas["left"],
        "right_entry_sha256": expected_entry_shas["right"],
        "opponent_entry_sha256": expected_entry_shas["opponent"],
        "left_label": args.left_label,
        "right_label": args.right_label,
        "opponent_label": args.opponent_label,
        "seed": args.seed,
        "rng_seed": args.rng_seed,
        "seats": seats,
        "timeouts": {
            "action": action_timeout,
            "startup": startup_timeout,
            "game": game_timeout,
        },
    }
    report = {
        "schema": SCHEMA,
        "authority": authority,
        "authority_sha256": _digest(authority),
        "rows": rows,
    }
    report["report_sha256"] = _digest(report)
    return report


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--expected-loader-sha256", required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--left-candidate", required=True)
    parser.add_argument("--right-candidate", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--left-label", required=True)
    parser.add_argument("--right-label", required=True)
    parser.add_argument("--opponent-label", required=True)
    parser.add_argument("--left-archive", type=Path, required=True)
    parser.add_argument("--left-archive-sha256", required=True)
    parser.add_argument("--right-archive", type=Path, required=True)
    parser.add_argument("--right-archive-sha256", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--rng-seed", type=int, default=20260912)
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--action-timeout", type=float, default=1.25)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=900.0)
    parser.add_argument("--window-radius", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_witness(args)
        _atomic_write(args.output, report)
    except (WitnessError, OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"action_divergence_witness: {exc}", file=os.sys.stderr)
        return 2
    summary = {
        "authority_sha256": report["authority_sha256"],
        "rows": [
            {
                "candidate_seat": row["candidate_seat"],
                "left_scores": row["left_result"].get("scores"),
                "right_scores": row["right_result"].get("scores"),
                "first_candidate_action_divergence_step": row["comparison"]["first_candidate_action_divergence_step"],
                "first_any_action_divergence_step": row["comparison"]["first_any_action_divergence_step"],
                "candidate_action_is_first_observed_divergence": row["comparison"]["candidate_action_is_first_observed_divergence"],
            }
            for row in report["rows"]
        ],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())