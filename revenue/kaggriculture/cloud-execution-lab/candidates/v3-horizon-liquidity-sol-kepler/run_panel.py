# SPDX-License-Identifier: Apache-2.0
"""Run the carry ablation with candidate-returned-action activation custody."""
from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v3-l02-ledger-tranche"
RUNNER = SOURCE / "run_panel.py"

ACTION_DIGEST_SCHEMA = 1
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTION_COUNT = 719
EVALUATOR_SOURCE_GIT_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"

_INIT_SEAM = "    actors, trace = [], hashlib.sha256()\n"
_ACTION_SEAM = '                actions.append(response["action"])\n'
_FINALIZE_SEAM = (
    '        result["driver_cpu_seconds"] = time.process_time() - initial_cpu\n'
)

_INIT_PATCH = _INIT_SEAM + (
    "    candidate_action_trace = hashlib.sha256()\n"
    "    candidate_action_count = 0\n"
)
_ACTION_PATCH = _ACTION_SEAM + (
    "                if seat == candidate_seat:\n"
    "                    candidate_action_payload = encoded({\n"
    '                        "schema_version": 1, "step": step,\n'
    '                        "action": response["action"],\n'
    "                    })\n"
    "                    candidate_action_trace.update(\n"
    '                        len(candidate_action_payload).to_bytes(8, "big")\n'
    "                    )\n"
    "                    candidate_action_trace.update(candidate_action_payload)\n"
    "                    candidate_action_count += 1\n"
)
_FINALIZE_PATCH = _FINALIZE_SEAM + (
    '        result["candidate_action_digest_schema"] = 1\n'
    '        result["candidate_action_sha256"] = candidate_action_trace.hexdigest()\n'
    '        result["candidate_action_count"] = candidate_action_count\n'
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("_sol_kepler_paired_panel", RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"candidate-action evaluator seam {label} count {count}; expected 1")
    return text.replace(old, new, 1)


def patch_candidate_action_evaluator(path: Path) -> dict[str, Any]:
    """Hash only the tested seat's returned actions before interpretation.

    The inherited evaluator's ``trace_sha256`` is deliberately retained as a
    whole-game diagnostic, but it covers both agents, both banks, and final
    observations. It cannot establish that this candidate returned a different
    action. The added length-delimited digest is parent-observed immediately
    after the tested worker response and before ``engine.interpreter``.
    """
    path = Path(path)
    before = path.read_bytes()
    text = before.decode("utf-8")
    text = _replace_once(text, _INIT_SEAM, _INIT_PATCH, "init")
    text = _replace_once(text, _ACTION_SEAM, _ACTION_PATCH, "action")
    text = _replace_once(text, _FINALIZE_SEAM, _FINALIZE_PATCH, "finalize")
    after = text.encode("utf-8")
    if after == before:
        raise RuntimeError("candidate-action evaluator patch was a no-op")
    path.write_bytes(after)
    return {
        "schema_version": ACTION_DIGEST_SCHEMA,
        "measure": "candidate-seat pre-interpreter returned-action digest",
        "source_git_blob": EVALUATOR_SOURCE_GIT_BLOB,
        "before_sha256": _sha256_bytes(before),
        "after_sha256": _sha256_bytes(after),
        "seams": {"init": 1, "action": 1, "finalize": 1},
        "length_prefix_bytes": 8,
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
        "expected_candidate_actions": EXPECTED_ACTION_COUNT,
        "whole_trace_is_diagnostic_only": True,
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        return len(bytes.fromhex(value)) == 32
    except ValueError:
        return False


def candidate_action_evidence_errors(
    game: Mapping[str, Any], key: tuple[str, int, int]
) -> list[str]:
    """Validate exact complete-game action evidence for one accepted cell."""
    errors: list[str] = []
    if type(game.get("candidate_seat")) is not int or game.get("candidate_seat") not in (0, 1):
        errors.append(f"nonliteral candidate seat {key}")
    if type(game.get("seed")) is not int:
        errors.append(f"nonliteral seed {key}")
    if game.get("candidate_action_digest_schema") != ACTION_DIGEST_SCHEMA:
        errors.append(f"candidate action digest schema mismatch {key}")
    if not _is_sha256(game.get("candidate_action_sha256")):
        errors.append(f"missing candidate action digest {key}")

    count = game.get("candidate_action_count")
    steps = game.get("steps")
    episode_steps = game.get("episode_steps")
    if type(count) is not int:
        errors.append(f"nonliteral candidate action count {key}")
    if type(steps) is not int:
        errors.append(f"nonliteral completed step count {key}")
    if type(episode_steps) is not int:
        errors.append(f"nonliteral episode step count {key}")
    if type(count) is int and type(steps) is int and count != steps:
        errors.append(f"candidate action/step mismatch {key}: {count} != {steps}")
    if episode_steps != EXPECTED_EPISODE_STEPS or steps != EXPECTED_ACTION_COUNT:
        errors.append(
            f"official lifecycle mismatch {key}: episode={episode_steps}, actions={steps}"
        )

    actors = game.get("actors")
    if not isinstance(actors, list) or len(actors) != 2:
        errors.append(f"missing two actor receipts {key}")
    elif type(count) is int:
        for seat, actor in enumerate(actors):
            calls = actor.get("calls") if isinstance(actor, Mapping) else None
            if type(calls) is not int or calls != count:
                errors.append(
                    f"actor call count mismatch {key} seat={seat}: {calls} != {count}"
                )
    return errors


def add_candidate_action_gate(
    games: Mapping[tuple[str, int, int], Mapping[str, Any]],
    gate: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(gate.get("errors") or [])
    for key, game in sorted(games.items()):
        errors.extend(candidate_action_evidence_errors(game, key))
    updated = dict(gate)
    updated.update(
        valid=not errors,
        errors=errors,
        candidate_action_digest_schema=ACTION_DIGEST_SCHEMA,
        candidate_action_evidence_cells=len(games),
        expected_episode_steps=EXPECTED_EPISODE_STEPS,
        expected_candidate_actions=EXPECTED_ACTION_COUNT,
    )
    return updated


def pair_with_candidate_actions(
    original_pair: Callable[..., list[dict[str, Any]]],
    baseline: Mapping[tuple[str, int, int], Mapping[str, Any]],
    candidate: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = original_pair(baseline, candidate)
    for row in rows:
        key = (
            str(row["opponent"]),
            int(row["seed"]),
            int(row["candidate_seat"]),
        )
        base = baseline[key]
        cand = candidate[key]
        row["candidate_action_changed"] = (
            base["candidate_action_sha256"] != cand["candidate_action_sha256"]
        )
        row["baseline_candidate_action_sha256"] = base["candidate_action_sha256"]
        row["candidate_candidate_action_sha256"] = cand["candidate_action_sha256"]
        row["candidate_action_count"] = cand["candidate_action_count"]
    return rows


def summarize_with_candidate_actions(
    original_summarize: Callable[..., dict[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summary = dict(original_summarize(rows))
    changed = sum(bool(row.get("candidate_action_changed")) for row in rows)
    summary["candidate_action_changed_cells"] = changed
    summary["candidate_action_unchanged_cells"] = len(rows) - changed
    return summary


def verdict_with_candidate_actions(
    original_verdict: Callable[..., dict[str, Any]],
    global_summary: Mapping[str, Any],
    per_opponent: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    inherited = dict(original_verdict(global_summary, per_opponent))
    inherited_checks = dict(inherited.get("checks") or {})
    inherited_checks.pop("behavior_activated", None)
    inherited_checks.pop("four_of_six_nonnegative_strata", None)
    checks = {
        "candidate_returned_action_activated": int(
            global_summary.get("candidate_action_changed_cells", 0)
        )
        > 0,
        **inherited_checks,
        "all_four_opponent_strata_nonnegative": (
            len(per_opponent) == 4
            and all(
                float(row.get("mean_own_delta", -math.inf)) >= 0
                for row in per_opponent.values()
            )
        ),
    }
    inherited.update(
        decision="ADVANCE" if all(checks.values()) else "REJECT",
        checks=checks,
        activation_measure="candidate-seat pre-interpreter returned-action digest",
        whole_trace_role="diagnostic only",
    )
    return inherited


def _replace_report_line(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"panel markdown seam count {text.count(old)}; expected 1")
    return text.replace(old, new, 1)


def main(argv=None) -> int:
    runner = _load_runner()
    original_patch_evaluator = runner.patch_evaluator
    original_collect_games = runner.collect_games
    original_pair_games = runner.pair_games
    original_summarize = runner.summarize
    original_verdict = runner.verdict
    original_dependency_receipt = runner.dependency_receipt
    original_markdown = runner.markdown
    original_failure_markdown = runner.failure_markdown
    action_patch_receipt: dict[str, Any] | None = None

    def agent_spec(variant: str) -> str:
        path = runner.LAB / "main.py" if variant == "baseline" else HERE / "candidate.py"
        return str(path.resolve()) + "::agent"

    def patch_evaluator(source: Path, target: Path) -> None:
        nonlocal action_patch_receipt
        original_patch_evaluator(source, target)
        action_patch_receipt = patch_candidate_action_evaluator(target)

    def collect_games(*args, **kwargs):
        games, gate = original_collect_games(*args, **kwargs)
        return games, add_candidate_action_gate(games, gate)

    def pair_games(baseline, candidate):
        return pair_with_candidate_actions(original_pair_games, baseline, candidate)

    def summarize(rows):
        return summarize_with_candidate_actions(original_summarize, rows)

    def verdict(global_summary, per_opponent):
        return verdict_with_candidate_actions(
            original_verdict, global_summary, per_opponent
        )

    def dependency_receipt(head: str, *, evaluator=None):
        if action_patch_receipt is None:
            raise RuntimeError("candidate-action evaluator patch receipt missing")
        saved_here = runner.HERE
        runner.HERE = SOURCE
        try:
            receipt = original_dependency_receipt(head, evaluator=evaluator)
        finally:
            runner.HERE = saved_here
        if receipt["sha256"]["evaluator"] != action_patch_receipt["after_sha256"]:
            raise RuntimeError("patched evaluator digest detached from dependency receipt")
        receipt["sha256"]["candidate"] = runner.sha256_file(HERE / "candidate.py")
        receipt["sha256"].pop("overlay", None)
        receipt["sha256"]["liquidity_haircut"] = runner.sha256_file(
            HERE / "liquidity_haircut.py"
        )
        receipt["sha256"]["selected_sell_core"] = runner.sha256_file(
            runner.LAB / "selected_sell_core.py"
        )
        receipt["sha256"]["source_audit"] = runner.sha256_file(HERE / "audit_change.py")
        receipt["sha256"]["panel_wrapper"] = runner.sha256_file(HERE / "run_panel.py")
        receipt["candidate_bundle"] = runner.tree_sha256(HERE)
        receipt["ablation"] = {
            "operation": "titan-v3-horizon-liquidity-20260909-sol-kepler-01",
            "factor": 0.95,
            "target": "selected_sell_core.MarketPath.score",
            "only_runtime_change": "selected optimizer carry contribution 1.0 -> 0.95",
            "canonical_files_modified": False,
        }
        receipt["activation_custody"] = dict(action_patch_receipt)
        return receipt

    def markdown(report):
        text = original_markdown(report)
        text = _replace_report_line(
            text,
            "# TITAN L02 ledger-coherent tranche — development panel",
            "# TITAN V3 horizon-liquidity ablation — development panel",
        )
        summary = report["summary"]
        old = (
            f"Cells: {summary['cells']}; "
            f"trace-changed: {summary['trace_changed_cells']}"
        )
        new = (
            f"Cells: {summary['cells']}; candidate-action-changed: "
            f"{summary['candidate_action_changed_cells']}; whole-trace-changed: "
            f"{summary['trace_changed_cells']}"
        )
        return _replace_report_line(text, old, new)

    def failure_markdown(payload):
        text = original_failure_markdown(payload)
        return _replace_report_line(
            text,
            "# TITAN L02 ledger-coherent tranche — development panel",
            "# TITAN V3 horizon-liquidity ablation — development panel",
        )

    runner._agent_spec = agent_spec
    runner.patch_evaluator = patch_evaluator
    runner.collect_games = collect_games
    runner.pair_games = pair_games
    runner.summarize = summarize
    runner.verdict = verdict
    runner.dependency_receipt = dependency_receipt
    runner.markdown = markdown
    runner.failure_markdown = failure_markdown
    return int(runner.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
