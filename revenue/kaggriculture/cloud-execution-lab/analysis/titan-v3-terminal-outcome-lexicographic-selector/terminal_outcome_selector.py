#!/usr/bin/env python3
"""Fail-closed terminal outcome selector for TITAN V3.

This module does not model Kaggriculture or generate market plans.  It consumes
terminal-complete, source-bound scenario certificates produced elsewhere and
selects at most one already-generated plan.  Selection is deliberately
conservative:

* no modeled scenario may move to a worse W/T/L class;
* when the W/T/L class is unchanged, neither own cash nor margin may fall;
* own-cash sacrifice is permitted only in a scenario whose W/T/L class improves;
* a unique candidate must lexicographically outrank the incumbent;
* malformed, incomplete, aliased, or ambiguous evidence preserves the incumbent
  or is rejected as a contract error.

The public API is ``select_document(document)``.  The CLI reads strict JSON and
atomically writes a self-sealed canonical JSON report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn, Sequence

INPUT_SCHEMA = "titan.v3.terminal-outcome-selector.input.v1"
REPORT_SCHEMA = "titan.v3.terminal-outcome-selector.report.v1"
POLICY_ID = "titan.v3.terminal-outcome-lexicographic-selector.v1"
MAX_ABS_CASH = (1 << 63) - 1
MAX_PLANS = 256
MAX_SCENARIOS = 4096
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_FIELDS = (
    "main_commit",
    "archive_sha256",
    "source_manifest_sha256",
    "engine_sha256",
    "evaluator_sha256",
    "scenario_model_sha256",
    "scenario_set_sha256",
)


class ContractError(ValueError):
    """Raised when evidence does not satisfy the selector contract."""


def _fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _fail(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _reject_constant(token: str) -> NoReturn:
    _fail(f"non-finite JSON number: {token}")


def strict_loads(text: str) -> Any:
    """Parse JSON while rejecting duplicate keys and non-finite constants."""

    if not isinstance(text, str):
        _fail("JSON input must be text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        _fail(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")


def canonical_bytes(value: Any) -> bytes:
    """Return deterministic strict-JSON bytes with a final newline."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail(f"value is not canonical JSON: {exc}")
    return encoded + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be an object")
    for key in value:
        if not isinstance(key, str):
            _fail(f"{label} has a non-string key")
    return value


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        _fail(f"{label} keys differ: missing={missing}, extra={extra}")


def _text(value: Any, label: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        _fail(f"{label} must be nonempty text of at most {max_length} characters")
    return value


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label, max_length=128)
    if _ID_RE.fullmatch(text) is None:
        _fail(f"{label} is not a canonical identifier")
    return text


def _hex(value: Any, label: str, size: int = 64) -> str:
    text = _text(value, label, max_length=size)
    matcher = _HEX40_RE if size == 40 else _HEX64_RE
    if matcher.fullmatch(text) is None:
        _fail(f"{label} must be lowercase {size}-hex")
    return text


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{label} must be an integer, not bool/float/string")
    if abs(value) > MAX_ABS_CASH:
        _fail(f"{label} exceeds signed-64-bit cash bound")
    return value


def _nonnegative_integer(value: Any, label: str) -> int:
    parsed = _integer(value, label)
    if parsed < 0:
        _fail(f"{label} must be nonnegative")
    return parsed


def _true(value: Any, label: str) -> None:
    if value is not True:
        _fail(f"{label} must be literal true")


@dataclass(frozen=True, order=True)
class Rank:
    """Lexicographic tournament rank. Larger is better."""

    worst_outcome: int
    wins: int
    ties: int
    minimum_margin: int
    aggregate_margin: int
    minimum_own_cash: int
    aggregate_own_cash: int

    def as_dict(self) -> dict[str, int]:
        return {
            "worst_outcome": self.worst_outcome,
            "wins": self.wins,
            "ties": self.ties,
            "minimum_margin": self.minimum_margin,
            "aggregate_margin": self.aggregate_margin,
            "minimum_own_cash": self.minimum_own_cash,
            "aggregate_own_cash": self.aggregate_own_cash,
        }


@dataclass(frozen=True)
class Row:
    scenario_id: str
    preworld_sha256: str
    scenario_sha256: str
    terminal_trace_sha256: str
    own_cash: int
    rival_cash: int

    @property
    def margin(self) -> int:
        return self.own_cash - self.rival_cash

    @property
    def outcome(self) -> int:
        return 1 if self.margin > 0 else (-1 if self.margin < 0 else 0)

    def score_tuple(self) -> tuple[int, int, int, str]:
        return (self.own_cash, self.rival_cash, self.margin, self.terminal_trace_sha256)


@dataclass(frozen=True)
class Plan:
    plan_id: str
    commitment_sha256: str
    rows: tuple[Row, ...]

    @property
    def row_map(self) -> dict[str, Row]:
        return {row.scenario_id: row for row in self.rows}

    @property
    def rank(self) -> Rank:
        outcomes = [row.outcome for row in self.rows]
        margins = [row.margin for row in self.rows]
        own = [row.own_cash for row in self.rows]
        return Rank(
            worst_outcome=min(outcomes),
            wins=sum(value == 1 for value in outcomes),
            ties=sum(value == 0 for value in outcomes),
            minimum_margin=min(margins),
            aggregate_margin=sum(margins),
            minimum_own_cash=min(own),
            aggregate_own_cash=sum(own),
        )


def _parse_source(value: Any) -> dict[str, str]:
    source = _mapping(value, "source")
    _exact_keys(source, _SOURCE_FIELDS, "source")
    parsed: dict[str, str] = {}
    for field in _SOURCE_FIELDS:
        parsed[field] = _hex(source[field], f"source.{field}", 40 if field == "main_commit" else 64)
    return parsed


def _parse_tail_policy(value: Any) -> dict[str, int]:
    policy = _mapping(value, "tail_policy")
    _exact_keys(
        policy,
        ("minimum_own_cash", "maximum_outcome_improvement_sacrifice"),
        "tail_policy",
    )
    return {
        "minimum_own_cash": _integer(policy["minimum_own_cash"], "tail_policy.minimum_own_cash"),
        "maximum_outcome_improvement_sacrifice": _nonnegative_integer(
            policy["maximum_outcome_improvement_sacrifice"],
            "tail_policy.maximum_outcome_improvement_sacrifice",
        ),
    }


def _parse_required_scenarios(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("required_scenarios must be an array")
    if not value or len(value) > MAX_SCENARIOS:
        _fail(f"required_scenarios must contain 1..{MAX_SCENARIOS} entries")
    parsed = [_identifier(item, f"required_scenarios[{index}]") for index, item in enumerate(value)]
    if len(set(parsed)) != len(parsed):
        _fail("required_scenarios contains duplicates")
    return tuple(sorted(parsed))


def _parse_row(value: Any, label: str) -> Row:
    row = _mapping(value, label)
    _exact_keys(
        row,
        (
            "scenario_id",
            "preworld_sha256",
            "scenario_sha256",
            "terminal_trace_sha256",
            "own_cash",
            "rival_cash",
            "terminal_complete",
            "score_equals_terminal_bank",
        ),
        label,
    )
    _true(row["terminal_complete"], f"{label}.terminal_complete")
    _true(row["score_equals_terminal_bank"], f"{label}.score_equals_terminal_bank")
    return Row(
        scenario_id=_identifier(row["scenario_id"], f"{label}.scenario_id"),
        preworld_sha256=_hex(row["preworld_sha256"], f"{label}.preworld_sha256"),
        scenario_sha256=_hex(row["scenario_sha256"], f"{label}.scenario_sha256"),
        terminal_trace_sha256=_hex(row["terminal_trace_sha256"], f"{label}.terminal_trace_sha256"),
        own_cash=_integer(row["own_cash"], f"{label}.own_cash"),
        rival_cash=_integer(row["rival_cash"], f"{label}.rival_cash"),
    )


def _parse_plan(value: Any, index: int, required: tuple[str, ...]) -> Plan:
    label = f"plans[{index}]"
    plan = _mapping(value, label)
    _exact_keys(plan, ("plan_id", "commitment_sha256", "rows"), label)
    rows_value = plan["rows"]
    if not isinstance(rows_value, list):
        _fail(f"{label}.rows must be an array")
    rows = tuple(_parse_row(item, f"{label}.rows[{row_index}]") for row_index, item in enumerate(rows_value))
    ids = [row.scenario_id for row in rows]
    if len(set(ids)) != len(ids):
        _fail(f"{label}.rows contains duplicate scenario ids")
    if set(ids) != set(required):
        _fail(
            f"{label}.rows scenario grid differs: "
            f"missing={sorted(set(required) - set(ids))}, extra={sorted(set(ids) - set(required))}"
        )
    rows = tuple(sorted(rows, key=lambda row: row.scenario_id))
    return Plan(
        plan_id=_identifier(plan["plan_id"], f"{label}.plan_id"),
        commitment_sha256=_hex(plan["commitment_sha256"], f"{label}.commitment_sha256"),
        rows=rows,
    )


def _validate_cross_plan(plans: Sequence[Plan], required: tuple[str, ...]) -> None:
    ids = [plan.plan_id for plan in plans]
    if len(set(ids)) != len(ids):
        _fail("plans contains duplicate plan_id values")

    baseline = plans[0].row_map
    for scenario_id in required:
        expected = (baseline[scenario_id].preworld_sha256, baseline[scenario_id].scenario_sha256)
        for plan in plans[1:]:
            row = plan.row_map[scenario_id]
            actual = (row.preworld_sha256, row.scenario_sha256)
            if actual != expected:
                _fail(f"scenario custody mismatch for {scenario_id!r} in plan {plan.plan_id!r}")

    by_commitment: dict[str, Plan] = {}
    for plan in plans:
        prior = by_commitment.get(plan.commitment_sha256)
        if prior is None:
            by_commitment[plan.commitment_sha256] = plan
            continue
        if tuple(row.score_tuple() for row in prior.rows) != tuple(row.score_tuple() for row in plan.rows):
            _fail(
                "same commitment has contradictory terminal evidence: "
                f"{prior.plan_id!r} vs {plan.plan_id!r}"
            )


def _transition_name(before: int, after: int) -> str:
    names = {-1: "L", 0: "T", 1: "W"}
    return f"{names[before]}->{names[after]}"


def _evaluate_plan(plan: Plan, incumbent: Plan, tail_policy: Mapping[str, int]) -> dict[str, Any]:
    incumbent_rows = incumbent.row_map
    transitions: dict[str, int] = {}
    outcome_regressions: list[str] = []
    same_class_own_regressions: list[str] = []
    same_class_margin_regressions: list[str] = []
    own_cash_floor_violations: list[str] = []
    outcome_improvement_sacrifice_violations: list[str] = []
    strict_scenarios: list[str] = []

    for row in plan.rows:
        before = incumbent_rows[row.scenario_id]
        transition = _transition_name(before.outcome, row.outcome)
        transitions[transition] = transitions.get(transition, 0) + 1
        if row.own_cash < tail_policy["minimum_own_cash"]:
            own_cash_floor_violations.append(row.scenario_id)
        if (
            row.outcome > before.outcome
            and before.own_cash - row.own_cash > tail_policy["maximum_outcome_improvement_sacrifice"]
        ):
            outcome_improvement_sacrifice_violations.append(row.scenario_id)
        if row.outcome < before.outcome:
            outcome_regressions.append(row.scenario_id)
            continue
        if row.outcome == before.outcome:
            if row.own_cash < before.own_cash:
                same_class_own_regressions.append(row.scenario_id)
            if row.margin < before.margin:
                same_class_margin_regressions.append(row.scenario_id)
            if row.own_cash > before.own_cash or row.margin > before.margin:
                strict_scenarios.append(row.scenario_id)
        else:
            strict_scenarios.append(row.scenario_id)

    action_active = plan.commitment_sha256 != incumbent.commitment_sha256
    eligible = (
        action_active
        and not outcome_regressions
        and not same_class_own_regressions
        and not same_class_margin_regressions
        and not own_cash_floor_violations
        and not outcome_improvement_sacrifice_violations
        and bool(strict_scenarios)
    )
    reasons: list[str] = []
    if not action_active:
        reasons.append("COMMITMENT_ALIAS")
    if outcome_regressions:
        reasons.append("OUTCOME_REGRESSION")
    if same_class_own_regressions:
        reasons.append("SAME_CLASS_OWN_REGRESSION")
    if same_class_margin_regressions:
        reasons.append("SAME_CLASS_MARGIN_REGRESSION")
    if own_cash_floor_violations:
        reasons.append("OWN_CASH_FLOOR_VIOLATION")
    if outcome_improvement_sacrifice_violations:
        reasons.append("OUTCOME_IMPROVEMENT_SACRIFICE_CAP_VIOLATION")
    if not strict_scenarios:
        reasons.append("NO_STRICT_IMPROVEMENT")
    if eligible:
        reasons.append("SCENARIO_SAFE")

    return {
        "plan_id": plan.plan_id,
        "commitment_sha256": plan.commitment_sha256,
        "action_active": action_active,
        "eligible": eligible,
        "reasons": reasons,
        "rank": plan.rank.as_dict(),
        "transitions": dict(sorted(transitions.items())),
        "strict_scenarios": sorted(strict_scenarios),
        "outcome_regressions": sorted(outcome_regressions),
        "same_class_own_regressions": sorted(same_class_own_regressions),
        "same_class_margin_regressions": sorted(same_class_margin_regressions),
        "own_cash_floor_violations": sorted(own_cash_floor_violations),
        "outcome_improvement_sacrifice_violations": sorted(outcome_improvement_sacrifice_violations),
    }


def _seal(report: dict[str, Any]) -> dict[str, Any]:
    if "report_sha256" in report:
        _fail("internal report already sealed")
    sealed = dict(report)
    sealed["report_sha256"] = sha256_hex(canonical_bytes(report))
    return sealed


def verify_report_seal(report: Mapping[str, Any]) -> bool:
    """Return True only when a report's self-seal matches canonical bytes."""

    try:
        expected = _hex(report.get("report_sha256"), "report.report_sha256")
        body = dict(report)
        del body["report_sha256"]
        return expected == sha256_hex(canonical_bytes(body))
    except (ContractError, KeyError, TypeError):
        return False


def select_document(document: Any) -> dict[str, Any]:
    """Validate a selector document and return a deterministic sealed report."""

    root = _mapping(document, "document")
    _exact_keys(
        root,
        ("schema", "source", "tail_policy", "required_scenarios", "incumbent_plan_id", "plans"),
        "document",
    )
    if root["schema"] != INPUT_SCHEMA:
        _fail(f"unsupported schema: {root['schema']!r}")
    source = _parse_source(root["source"])
    tail_policy = _parse_tail_policy(root["tail_policy"])
    required = _parse_required_scenarios(root["required_scenarios"])
    incumbent_id = _identifier(root["incumbent_plan_id"], "incumbent_plan_id")

    plans_value = root["plans"]
    if not isinstance(plans_value, list) or not 1 <= len(plans_value) <= MAX_PLANS:
        _fail(f"plans must contain 1..{MAX_PLANS} entries")
    plans = tuple(_parse_plan(value, index, required) for index, value in enumerate(plans_value))
    _validate_cross_plan(plans, required)
    plan_map = {plan.plan_id: plan for plan in plans}
    if incumbent_id not in plan_map:
        _fail("incumbent_plan_id does not name a plan")
    incumbent = plan_map[incumbent_id]

    evaluations = [
        _evaluate_plan(plan, incumbent, tail_policy)
        for plan in sorted(plans, key=lambda item: item.plan_id)
    ]
    evaluation_map = {item["plan_id"]: item for item in evaluations}
    incumbent_eval = evaluation_map[incumbent_id]
    incumbent_eval["eligible"] = True
    incumbent_eval["reasons"] = ["INCUMBENT"]

    eligible_candidates = [
        plan
        for plan in plans
        if plan.plan_id != incumbent_id and evaluation_map[plan.plan_id]["eligible"]
    ]
    # Eligibility itself implies rank > incumbent: outcomes never worsen; an
    # outcome improvement raises the outcome prefix of Rank, while a same-class
    # strict value improvement raises aggregate margin or aggregate own cash.
    selected = incumbent
    status = "PRESERVE_INCUMBENT"
    reason = "NO_ELIGIBLE_IMPROVEMENT"
    if eligible_candidates:
        if any(plan.rank <= incumbent.rank for plan in eligible_candidates):
            _fail("internal invariant: eligible candidate does not outrank incumbent")
        best_rank = max(plan.rank for plan in eligible_candidates)
        leaders = sorted(
            (plan for plan in eligible_candidates if plan.rank == best_rank),
            key=lambda item: item.plan_id,
        )
        if len(leaders) == 1:
            selected = leaders[0]
            status = "SELECT_CANDIDATE"
            reason = "UNIQUE_OUTCOME_SAFE_LEXICOGRAPHIC_IMPROVEMENT"
        else:
            reason = "AMBIGUOUS_BEST_PRESERVE_INCUMBENT"

    aliases: list[list[str]] = []
    by_commitment: dict[str, list[str]] = {}
    for plan in plans:
        by_commitment.setdefault(plan.commitment_sha256, []).append(plan.plan_id)
    for values in by_commitment.values():
        if len(values) > 1:
            aliases.append(sorted(values))

    body: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "policy_id": POLICY_ID,
        "source": source,
        "tail_policy": tail_policy,
        "required_scenarios": list(required),
        "incumbent_plan_id": incumbent_id,
        "selected_plan_id": selected.plan_id,
        "status": status,
        "reason": reason,
        "incumbent_rank": incumbent.rank.as_dict(),
        "selected_rank": selected.rank.as_dict(),
        "behavior_aliases": sorted(aliases),
        "plans": evaluations,
        "claims": {
            "terminal_complete_inputs_required": True,
            "outcome_regression_allowed": False,
            "same_class_own_regression_allowed": False,
            "same_class_margin_regression_allowed": False,
            "cash_sacrifice_only_on_outcome_improvement": True,
            "absolute_own_cash_floor_enforced": True,
            "outcome_improvement_sacrifice_cap_enforced": True,
            "ambiguous_best_preserves_incumbent": True,
            "gameplay_strength_claim": False,
            "promotion_authority": False,
        },
    }
    return _seal(body)


def _read_regular_utf8(path: Path) -> str:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(f"cannot stat input {path}: {exc}")
    if not stat.S_ISREG(metadata.st_mode):
        _fail(f"input must be a regular file, not a symlink/device/directory: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _fail(f"cannot read UTF-8 input {path}: {exc}")


def _paths_alias(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
        if left.exists() and right.exists() and os.path.samefile(left, right):
            return True
    except OSError as exc:
        _fail(f"cannot establish input/output identity: {exc}")
    return False


def _atomic_write(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        try:
            metadata = path.lstat()
        except OSError as exc:
            _fail(f"cannot stat output {path}: {exc}")
        if not stat.S_ISREG(metadata.st_mode):
            _fail(f"output must be absent or a regular file, not a symlink/device/directory: {path}")
    parent = path.parent.resolve(strict=True)
    if not parent.is_dir():
        _fail(f"output parent is not a directory: {parent}")
    target = parent / path.name
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="strict JSON selector input")
    parser.add_argument("output", type=Path, help="canonical sealed report path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if _paths_alias(arguments.input, arguments.output):
            _fail("input and output paths must not alias")
        document = strict_loads(_read_regular_utf8(arguments.input))
        report = select_document(document)
        _atomic_write(arguments.output, canonical_bytes(report))
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"terminal-outcome-selector: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
