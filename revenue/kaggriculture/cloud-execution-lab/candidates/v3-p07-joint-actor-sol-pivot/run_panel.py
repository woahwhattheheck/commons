# SPDX-License-Identifier: Apache-2.0
"""Action-bound all-step census for the exact P07 pair-atomic candidate."""
from __future__ import annotations

from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v3-l02-ledger-tranche"
RUNNER = SOURCE / "run_panel.py"
EXPECTED_ACTION_COUNT = 719
EXPECTED_EPISODE_STEPS = 720


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "_p07_paired_panel_source", RUNNER
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load paired panel source: {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _replace_once(text: str, needle: str, replacement: str, label: str) -> str:
    if text.count(needle) != 1:
        raise RuntimeError(f"evaluator {label} seam changed")
    return text.replace(needle, replacement, 1)


def instrument_candidate_actions(path: Path) -> None:
    """Hash each candidate-seat action immediately before interpretation."""
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "actors, trace = [], hashlib.sha256()",
        "actors, trace, candidate_actions = [], hashlib.sha256(), hashlib.sha256()",
        "digest initialization",
    )
    text = _replace_once(
        text,
        '"failure": None, "steps": 0, "episode_steps": cfg.episodeSteps, "daily_bank": []}',
        '"failure": None, "steps": 0, "episode_steps": cfg.episodeSteps, "daily_bank": [],\n'
        '              "candidate_action_count": 0, "candidate_action_sha256": None}',
        "result schema",
    )
    text = _replace_once(
        text,
        '                actions.append(response["action"])\n            for seat in range(2):',
        '                actions.append(response["action"])\n'
        '            candidate_actions.update(encoded({"step": step, "action": actions[candidate_seat]}))\n'
        '            result["candidate_action_count"] += 1\n'
        '            for seat in range(2):',
        "pre-interpreter action",
    )
    text = _replace_once(
        text,
        '        else:\n            result["trace_sha256"] = trace.hexdigest()\n        if finalization_errors:',
        '        else:\n            result["trace_sha256"] = trace.hexdigest()\n'
        '        result["candidate_action_sha256"] = candidate_actions.hexdigest()\n'
        '        if finalization_errors:',
        "digest finalization",
    )
    path.write_text(text, encoding="utf-8")


def add_p07_environment(path: Path) -> None:
    """Forward only the source path and append-only P07 trace into workers."""
    text = path.read_text(encoding="utf-8")
    seam = '''        if os.environ.get("TITAN_L02_PYTHONPATH"):
            env["PYTHONPATH"] = os.environ["TITAN_L02_PYTHONPATH"]'''
    replacement = seam + '''
        if os.environ.get("TITAN_P07_LOG"):
            env["TITAN_P07_LOG"] = os.environ["TITAN_P07_LOG"]'''
    path.write_text(_replace_once(text, seam, replacement, "P07 environment"), encoding="utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _key(row: Mapping[str, Any]) -> tuple[str, int, int]:
    return (
        str(row["opponent"]),
        int(row["seed"]),
        int(row["candidate_seat"]),
    )


def _validate_action_receipt(
    game: Mapping[str, Any], key: tuple[str, int, int], arm: str
) -> None:
    if _key(game) != key:
        raise ValueError(f"{arm} key mismatch for {key}")
    if int(game.get("episode_steps", -1)) != EXPECTED_EPISODE_STEPS:
        raise ValueError(f"{arm} episode length mismatch for {key}")
    if int(game.get("steps", -1)) != EXPECTED_ACTION_COUNT:
        raise ValueError(f"{arm} completed-step mismatch for {key}")
    if int(game.get("candidate_action_count", -1)) != EXPECTED_ACTION_COUNT:
        raise ValueError(f"{arm} action count mismatch for {key}")
    if not _is_sha256(game.get("candidate_action_sha256")):
        raise ValueError(f"{arm} candidate action digest missing for {key}")


def bind_candidate_actions(
    rows: Sequence[Mapping[str, Any]],
    baseline: Mapping[tuple[str, int, int], Mapping[str, Any]],
    candidate: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach exact pre-interpreter action drift to each paired score row."""
    if set(baseline) != set(candidate):
        raise ValueError("baseline/candidate cell sets differ")
    if len(rows) != len(baseline):
        raise ValueError("paired row cardinality mismatch")
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for raw in rows:
        key = _key(raw)
        if key in seen or key not in baseline:
            raise ValueError(f"invalid or duplicate paired row: {key}")
        seen.add(key)
        base, cand = baseline[key], candidate[key]
        _validate_action_receipt(base, key, "baseline")
        _validate_action_receipt(cand, key, "candidate")
        row = dict(raw)
        row["baseline_candidate_action_sha256"] = base["candidate_action_sha256"]
        row["candidate_candidate_action_sha256"] = cand["candidate_action_sha256"]
        row["candidate_action_count"] = cand["candidate_action_count"]
        row["candidate_action_changed"] = (
            base["candidate_action_sha256"] != cand["candidate_action_sha256"]
        )
        output.append(row)
    if seen != set(baseline):
        raise ValueError("paired grid incomplete after action binding")
    return output


def _read_trace(path: Path) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    proposals = commits = repairs = malformed = 0
    rows = 0
    first_commits: list[dict[str, Any]] = []
    if not path.is_file():
        return {
            "path": str(path),
            "rows": 0,
            "proposal_activations": 0,
            "committed_activations": 0,
            "atomic_repairs": 0,
            "malformed_lines": 0,
            "reason_counts": {},
            "first_commits": [],
        }
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(record, dict):
            malformed += 1
            continue
        if record.get("phase") == "proposal":
            reasons[str(record.get("reason"))] += 1
            if record.get("changed") is True:
                proposals += 1
        if record.get("phase") == "finish":
            repairs += int(record.get("atomic_repair") is True)
            if record.get("committed") is True:
                commits += 1
                if len(first_commits) < 12:
                    first_commits.append(record)
    return {
        "path": str(path),
        "rows": rows,
        "proposal_activations": proposals,
        "committed_activations": commits,
        "atomic_repairs": repairs,
        "malformed_lines": malformed,
        "reason_counts": dict(sorted(reasons.items())),
        "first_commits": first_commits,
    }


def _mean_groups(
    rows: Sequence[Mapping[str, Any]], fields: Sequence[str]
) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        name = "/".join(str(row[field]) for field in fields)
        groups.setdefault(name, []).append(float(row["own_delta"]))
    return {
        name: statistics.fmean(values) for name, values in sorted(groups.items())
    }


def strict_verdict(
    global_summary: Mapping[str, Any],
    per_opponent: Mapping[str, Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    """Separate executable activation from playing-strength promotion."""
    score_changed = [
        row
        for row in rows
        if float(row.get("own_delta", 0.0)) != 0.0
        or float(row.get("margin_delta", 0.0)) != 0.0
    ]
    action_changed = [
        row for row in rows if row.get("candidate_action_changed") is True
    ]
    strata = _mean_groups(rows, ("opponent", "candidate_seat")) if rows else {}
    structural = {
        "complete_nonempty_grid": bool(rows),
        "candidate_action_receipts_complete": bool(rows)
        and all(
            int(row.get("candidate_action_count", -1)) == EXPECTED_ACTION_COUNT
            and _is_sha256(row.get("candidate_candidate_action_sha256"))
            for row in rows
        ),
        "trace_well_formed": int(trace.get("malformed_lines", 0)) == 0,
        "proposal_activated": int(trace.get("proposal_activations", 0)) > 0,
        "pair_committed": int(trace.get("committed_activations", 0)) > 0,
        "pre_interpreter_action_changed": bool(action_changed),
        "every_score_change_action_bound": all(
            row.get("candidate_action_changed") is True for row in score_changed
        ),
        "no_half_commit_observed": int(trace.get("atomic_repairs", 0)) == 0,
    }
    strength = {
        "positive_mean_own_cash": float(
            global_summary.get("mean_own_delta", 0.0)
        )
        > 0.0,
        "positive_mean_margin": float(
            global_summary.get("mean_margin_delta", 0.0)
        )
        > 0.0,
        "no_opponent_seat_mean_own_regression": bool(strata)
        and all(value >= 0.0 for value in strata.values()),
        "all_opponents_reported": set(per_opponent)
        == {str(row["opponent"]) for row in rows},
    }
    if not all(structural.values()):
        decision = "REJECT_DORMANT_OR_UNBOUND"
    elif all(strength.values()):
        decision = "ADVANCE_TO_DISJOINT_HOLDOUT"
    else:
        decision = "ACTIVE_BUT_REJECT_PLAYING_STRENGTH"
    return {
        "decision": decision,
        "structural_checks": structural,
        "strength_checks": strength,
        "per_opponent_seat_mean_own_delta": strata,
        "candidate_action_changed_cells": len(action_changed),
        "score_changed_cells": len(score_changed),
        "p07_trace": dict(trace),
        "scope": (
            "source-bound development census; no canonical promotion, "
            "Kaggle upload, or leaderboard claim"
        ),
    }


def _output_from_argv(argv: Sequence[str]) -> Path:
    for index, value in enumerate(argv):
        if value == "--output" and index + 1 < len(argv):
            return Path(argv[index + 1]).resolve()
    raise ValueError("--output is required")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    output_path = _output_from_argv(args)
    trace_path = output_path.with_name("P07-TRACE.jsonl")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.unlink(missing_ok=True)
    os.environ["TITAN_P07_LOG"] = str(trace_path)

    runner = _load_runner()
    original_dependency_receipt = runner.dependency_receipt
    original_markdown = runner.markdown
    original_patch_evaluator = runner.patch_evaluator
    original_pair_games = runner.pair_games
    original_summarize = runner.summarize
    paired_rows: list[dict[str, Any]] = []

    def agent_spec(variant: str) -> str:
        path = runner.LAB / "main.py" if variant == "baseline" else HERE / "candidate.py"
        return str(path.resolve()) + "::agent"

    def patch_evaluator(source: Path, target: Path) -> None:
        original_patch_evaluator(source, target)
        add_p07_environment(target)
        instrument_candidate_actions(target)

    def pair_games(baseline, candidate):
        rows = bind_candidate_actions(
            original_pair_games(baseline, candidate), baseline, candidate
        )
        paired_rows[:] = rows
        return rows

    def summarize(rows):
        summary = original_summarize(rows)
        summary["candidate_action_changed_cells"] = sum(
            row.get("candidate_action_changed") is True for row in rows
        )
        summary["score_changed_cells"] = sum(
            float(row.get("own_delta", 0.0)) != 0.0
            or float(row.get("margin_delta", 0.0)) != 0.0
            for row in rows
        )
        return summary

    def verdict(global_summary, per_opponent):
        return strict_verdict(
            global_summary, per_opponent, paired_rows, _read_trace(trace_path)
        )

    def dependency_receipt(head: str, *, evaluator=None):
        saved_here = runner.HERE
        runner.HERE = SOURCE
        try:
            receipt = original_dependency_receipt(head, evaluator=evaluator)
        finally:
            runner.HERE = saved_here
        receipt["sha256"]["candidate"] = runner.sha256_file(HERE / "candidate.py")
        receipt["sha256"].pop("overlay", None)
        receipt["sha256"]["p07_atomic"] = runner.sha256_file(HERE / "p07_atomic.py")
        receipt["sha256"]["joint_assignment"] = runner.sha256_file(
            runner.LAB / "joint_assignment.py"
        )
        receipt["sha256"]["spatial_tempo"] = runner.sha256_file(
            runner.LAB / "spatial_tempo.py"
        )
        receipt["sha256"]["panel_adapter"] = runner.sha256_file(HERE / "run_panel.py")
        receipt["sha256"]["panel_source"] = runner.sha256_file(RUNNER)
        receipt["candidate_bundle"] = runner.tree_sha256(HERE)
        receipt["ablation"] = {
            "operation": "TITAN-V3-P07-JOINT-ACTOR-INTEGRATION-20260910-01",
            "key": "p07_joint_actor",
            "default_enabled_in_canonical": False,
            "candidate_enabled": True,
            "authority": "joint_assignment.propose_pair_swap",
            "publication": "both current actions and both continuation streams or neither",
            "trace": str(trace_path),
        }
        return receipt

    def markdown(report):
        text = original_markdown(report)
        text = text.replace(
            "# TITAN L02 ledger-coherent tranche — development panel",
            "# TITAN P07 exact pair-atomic joint actors — development census",
            1,
        )
        verdict_data = report.get("verdict") or {}
        trace = verdict_data.get("p07_trace") or {}
        appendix = [
            "",
            "## P07 all-step activation census",
            "",
            f"- proposal activations: `{trace.get('proposal_activations', 0)}`",
            f"- committed pair activations: `{trace.get('committed_activations', 0)}`",
            f"- atomic repairs: `{trace.get('atomic_repairs', 0)}`",
            f"- candidate-action changed cells: `{verdict_data.get('candidate_action_changed_cells', 0)}`",
            f"- decision: **{verdict_data.get('decision', 'UNKNOWN')}**",
            "",
            "The trace records every candidate step, not only hour 23. "
            "This is a development screen, not a hosted-rating or submission claim.",
            "",
        ]
        return text + "\n".join(appendix)

    runner._agent_spec = agent_spec
    runner.patch_evaluator = patch_evaluator
    runner.pair_games = pair_games
    runner.summarize = summarize
    runner.verdict = verdict
    runner.dependency_receipt = dependency_receipt
    runner.markdown = markdown
    try:
        return int(runner.main(args))
    finally:
        os.environ.pop("TITAN_P07_LOG", None)


if __name__ == "__main__":
    raise SystemExit(main())
