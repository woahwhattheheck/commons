#!/usr/bin/env python3
"""Outcome-first promotion classifier for paired TITAN panels.

The gate is deliberately evidence-only.  It does not run agents or games; it
consumes a normalized, source-bound paired report and distinguishes rating
signal from cash-only polish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "titan.rating-gate.input.v1"
RESULT_SCHEMA = "titan.rating-gate.result.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OUTCOME_POINTS2 = {"W": 2, "T": 1, "L": 0}
REQUIRED_EXPERIMENT_FIELDS = (
    "control_id",
    "candidate_id",
    "engine_sha256",
    "evaluator_sha256",
    "opponent_manifest_sha256",
    "grid_id",
)


class GateError(ValueError):
    """Raised when evidence is structurally invalid or causally unbound."""


class DuplicateKeyError(GateError):
    """Raised when JSON contains duplicate object keys."""


def _reject_constant(value: str) -> None:
    raise GateError(f"non-finite JSON number is forbidden: {value}")


def _no_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def loads_strict(raw: bytes) -> Any:
    """Parse UTF-8 JSON while rejecting duplicate keys and NaN/Infinity."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError(f"input is not UTF-8: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_duplicate_pairs,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
        )
    except DuplicateKeyError:
        raise
    except (json.JSONDecodeError, GateError) as exc:
        raise GateError(f"invalid JSON: {exc}") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GateError(f"{where} must be an object")
    return value


def _require_list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError(f"{where} must be an array")
    return value


def _require_nonempty_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{where} must be a non-empty string")
    return value


def _require_digest(value: Any, where: str) -> str:
    text = _require_nonempty_text(value, where).lower()
    if not HEX64.fullmatch(text):
        raise GateError(f"{where} must be a lowercase 64-hex SHA-256")
    return text


def _require_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateError(f"{where} must be an integer")
    return value


def _decimal(value: Any, where: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise GateError(f"{where} must be a finite number")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise GateError(f"{where} must be a finite number") from exc
    if not result.is_finite():
        raise GateError(f"{where} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Mapping):
        return {
            str(k): _jsonable(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


@dataclass(frozen=True)
class Arm:
    own_score: Decimal
    rival_score: Decimal
    tested_action_sha256: str
    action_count: int

    @property
    def outcome(self) -> str:
        if self.own_score > self.rival_score:
            return "W"
        if self.own_score < self.rival_score:
            return "L"
        return "T"

    @property
    def margin(self) -> Decimal:
        return self.own_score - self.rival_score


@dataclass(frozen=True)
class Pair:
    opponent: str
    seed: str
    seat: int
    control: Arm
    candidate: Arm

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.opponent, self.seed, self.seat)


def _parse_arm(value: Any, where: str, expected_action_count: int) -> Arm:
    obj = _require_mapping(value, where)
    state = _require_nonempty_text(obj.get("state"), f"{where}.state")
    phase = _require_nonempty_text(obj.get("phase"), f"{where}.phase")
    if state != "complete":
        raise GateError(f"{where}.state must be 'complete', got {state!r}")
    if phase != "finalize":
        raise GateError(f"{where}.phase must be 'finalize', got {phase!r}")

    action_count = _require_int(obj.get("action_count"), f"{where}.action_count")
    if action_count != expected_action_count:
        raise GateError(
            f"{where}.action_count must be {expected_action_count}, got {action_count}"
        )

    return Arm(
        own_score=_decimal(obj.get("own_score"), f"{where}.own_score"),
        rival_score=_decimal(obj.get("rival_score"), f"{where}.rival_score"),
        tested_action_sha256=_require_digest(
            obj.get("tested_action_sha256"), f"{where}.tested_action_sha256"
        ),
        action_count=action_count,
    )


def _seed_text(value: Any, where: str) -> str:
    if isinstance(value, bool) or value is None:
        raise GateError(f"{where} must be a string or integer")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value
    raise GateError(f"{where} must be a non-empty string or integer")


def _parse_pairs(document: Mapping[str, Any], expected_action_count: int) -> list[Pair]:
    rows = _require_list(document.get("pairs"), "pairs")
    if not rows:
        raise GateError("pairs must contain at least one paired cell")

    parsed: list[Pair] = []
    seen: set[tuple[str, str, int]] = set()
    for index, raw_pair in enumerate(rows):
        where = f"pairs[{index}]"
        obj = _require_mapping(raw_pair, where)
        opponent = _require_nonempty_text(obj.get("opponent"), f"{where}.opponent")
        seed = _seed_text(obj.get("seed"), f"{where}.seed")
        seat = _require_int(obj.get("seat"), f"{where}.seat")
        if seat not in (0, 1):
            raise GateError(f"{where}.seat must be 0 or 1")
        pair = Pair(
            opponent=opponent,
            seed=seed,
            seat=seat,
            control=_parse_arm(
                obj.get("control"), f"{where}.control", expected_action_count
            ),
            candidate=_parse_arm(
                obj.get("candidate"), f"{where}.candidate", expected_action_count
            ),
        )
        if pair.key in seen:
            raise GateError(
                "duplicate paired cell: "
                f"opponent={opponent!r}, seed={seed!r}, seat={seat}"
            )
        seen.add(pair.key)
        parsed.append(pair)
    return parsed


def _validate_experiment(document: Mapping[str, Any]) -> dict[str, str]:
    schema = _require_nonempty_text(document.get("schema"), "schema")
    if schema != SCHEMA:
        raise GateError(f"schema must be {SCHEMA!r}, got {schema!r}")

    experiment = _require_mapping(document.get("experiment"), "experiment")
    out: dict[str, str] = {}
    for field in REQUIRED_EXPERIMENT_FIELDS:
        value = experiment.get(field)
        if field.endswith("_sha256"):
            out[field] = _require_digest(value, f"experiment.{field}")
        else:
            out[field] = _require_nonempty_text(value, f"experiment.{field}")
    if out["control_id"] == out["candidate_id"]:
        raise GateError("experiment.control_id and candidate_id must differ")
    return out


def _sign_test_one_sided(positive: int, negative: int) -> Fraction:
    """Exact P[X >= positive] for X~Binomial(positive+negative, 1/2)."""

    n = positive + negative
    if n == 0:
        return Fraction(1, 1)
    numerator = sum(math.comb(n, k) for k in range(positive, n + 1))
    return Fraction(numerator, 2**n)


def _mean(total: Decimal, count: int) -> Decimal:
    return total / Decimal(count)


def classify_document(
    document: Mapping[str, Any],
    *,
    input_sha256: str,
    expected_action_count: int = 719,
) -> dict[str, Any]:
    """Validate and classify one normalized paired-panel document."""

    if expected_action_count <= 0:
        raise GateError("expected_action_count must be positive")
    experiment = _validate_experiment(document)
    pairs = _parse_pairs(document, expected_action_count)

    transitions: Counter[str] = Counter()
    stratum: dict[tuple[str, int], dict[str, Any]] = defaultdict(
        lambda: {
            "cells": 0,
            "half_point_delta": 0,
            "own_delta": Decimal(0),
            "rival_delta": Decimal(0),
            "margin_delta": Decimal(0),
            "positive_outcome_cells": 0,
            "negative_outcome_cells": 0,
        }
    )

    normalized_pairs: list[dict[str, Any]] = []
    action_changed_cells = 0
    neutral_action_changed_cells = 0
    score_changed_cells = 0
    positive_outcome_cells = 0
    negative_outcome_cells = 0
    positive_own_cells = 0
    negative_own_cells = 0
    new_losses = 0
    lost_wins = 0
    own_total = Decimal(0)
    rival_total = Decimal(0)
    margin_total = Decimal(0)
    half_point_total = 0

    for pair in pairs:
        control_outcome = pair.control.outcome
        candidate_outcome = pair.candidate.outcome
        transition = f"{control_outcome}->{candidate_outcome}"
        transitions[transition] += 1

        action_changed = (
            pair.control.tested_action_sha256
            != pair.candidate.tested_action_sha256
        )
        score_changed = (
            pair.control.own_score != pair.candidate.own_score
            or pair.control.rival_score != pair.candidate.rival_score
        )
        if score_changed and not action_changed:
            raise GateError(
                "candidate-action identity cannot own a score change for cell "
                f"{pair.key!r}"
            )

        own_delta = pair.candidate.own_score - pair.control.own_score
        rival_delta = pair.candidate.rival_score - pair.control.rival_score
        margin_delta = pair.candidate.margin - pair.control.margin
        half_point_delta = (
            OUTCOME_POINTS2[candidate_outcome]
            - OUTCOME_POINTS2[control_outcome]
        )

        action_changed_cells += int(action_changed)
        neutral_action_changed_cells += int(action_changed and not score_changed)
        score_changed_cells += int(score_changed)
        positive_outcome_cells += int(half_point_delta > 0)
        negative_outcome_cells += int(half_point_delta < 0)
        positive_own_cells += int(own_delta > 0)
        negative_own_cells += int(own_delta < 0)
        new_losses += int(control_outcome != "L" and candidate_outcome == "L")
        lost_wins += int(control_outcome == "W" and candidate_outcome != "W")
        own_total += own_delta
        rival_total += rival_delta
        margin_total += margin_delta
        half_point_total += half_point_delta

        bucket = stratum[(pair.opponent, pair.seat)]
        bucket["cells"] += 1
        bucket["half_point_delta"] += half_point_delta
        bucket["own_delta"] += own_delta
        bucket["rival_delta"] += rival_delta
        bucket["margin_delta"] += margin_delta
        bucket["positive_outcome_cells"] += int(half_point_delta > 0)
        bucket["negative_outcome_cells"] += int(half_point_delta < 0)

        normalized_pairs.append(
            {
                "opponent": pair.opponent,
                "seed": pair.seed,
                "seat": pair.seat,
                "control": {
                    "own_score": pair.control.own_score,
                    "rival_score": pair.control.rival_score,
                    "tested_action_sha256": pair.control.tested_action_sha256,
                    "action_count": pair.control.action_count,
                    "outcome": control_outcome,
                },
                "candidate": {
                    "own_score": pair.candidate.own_score,
                    "rival_score": pair.candidate.rival_score,
                    "tested_action_sha256": pair.candidate.tested_action_sha256,
                    "action_count": pair.candidate.action_count,
                    "outcome": candidate_outcome,
                },
                "action_changed": action_changed,
                "score_changed": score_changed,
                "half_point_delta": half_point_delta,
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": margin_delta,
                "transition": transition,
            }
        )

    normalized_pairs.sort(
        key=lambda row: (row["opponent"], row["seed"], row["seat"])
    )
    normalized = {
        "schema": SCHEMA,
        "experiment": experiment,
        "pairs": normalized_pairs,
    }
    normalized_sha256 = _sha256(canonical_bytes(normalized))

    strata_rows: list[dict[str, Any]] = []
    for (opponent, seat), bucket in sorted(stratum.items()):
        cells = int(bucket["cells"])
        strata_rows.append(
            {
                "opponent": opponent,
                "seat": seat,
                "cells": cells,
                "win_point_delta": Fraction(int(bucket["half_point_delta"]), 2),
                "own_delta_sum": bucket["own_delta"],
                "own_delta_mean": _mean(bucket["own_delta"], cells),
                "rival_delta_sum": bucket["rival_delta"],
                "margin_delta_sum": bucket["margin_delta"],
                "margin_delta_mean": _mean(bucket["margin_delta"], cells),
                "positive_outcome_cells": bucket["positive_outcome_cells"],
                "negative_outcome_cells": bucket["negative_outcome_cells"],
            }
        )

    negative_winpoint_strata = sum(
        int(row["win_point_delta"] < 0) for row in strata_rows
    )
    negative_own_strata = sum(
        int(row["own_delta_sum"] < 0) for row in strata_rows
    )
    negative_margin_strata = sum(
        int(row["margin_delta_sum"] < 0) for row in strata_rows
    )

    if action_changed_cells == 0:
        verdict = "NO_SIGNAL"
        reason = "candidate returned the same tested-seat action stream in every cell"
    elif (
        half_point_total > 0
        and negative_outcome_cells == 0
        and new_losses == 0
        and lost_wins == 0
        and negative_winpoint_strata == 0
    ):
        verdict = "RATING_ADVANCE_SCREEN"
        reason = (
            "paired terminal win points improved with no adverse outcome cell or "
            "opponent-by-seat stratum"
        )
    elif negative_outcome_cells > 0 or new_losses > 0 or lost_wins > 0:
        verdict = "REJECT"
        reason = "at least one paired cell moved to a worse terminal outcome"
    elif half_point_total < 0 or negative_winpoint_strata > 0:
        verdict = "REJECT"
        reason = (
            "terminal win points regress globally or in an opponent-by-seat stratum"
        )
    elif half_point_total == 0 and positive_outcome_cells > 0:
        verdict = "MORE_EVIDENCE"
        reason = "positive outcome movement is offset elsewhere"
    elif (
        half_point_total == 0
        and positive_outcome_cells == 0
        and own_total > 0
        and margin_total >= 0
        and negative_own_cells == 0
        and negative_own_strata == 0
        and negative_margin_strata == 0
    ):
        verdict = "POLISH_ONLY"
        reason = "cash improved safely but every terminal W/T/L outcome stayed unchanged"
    else:
        verdict = "MORE_EVIDENCE"
        reason = (
            "evidence is action-active but does not satisfy rating or safe-polish gates"
        )

    sign_p = _sign_test_one_sided(
        positive_outcome_cells, negative_outcome_cells
    )
    changed_outcomes = positive_outcome_cells + negative_outcome_cells
    evidence_strength = "SPARSE"
    if verdict == "RATING_ADVANCE_SCREEN" and sign_p <= Fraction(1, 20):
        represented_positive_opponents = {
            row["opponent"]
            for row in strata_rows
            if row["positive_outcome_cells"] > 0
        }
        represented_positive_seats = {
            row["seat"]
            for row in strata_rows
            if row["positive_outcome_cells"] > 0
        }
        if (
            len(represented_positive_opponents) >= 2
            and represented_positive_seats == {0, 1}
        ):
            evidence_strength = "BROAD_PAIRED_SIGNAL"
        else:
            evidence_strength = "CONCENTRATED_PAIRED_SIGNAL"

    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "verdict": verdict,
        "reason": reason,
        "evidence_strength": evidence_strength,
        "input_sha256": input_sha256,
        "normalized_sha256": normalized_sha256,
        "experiment": experiment,
        "counts": {
            "paired_cells": len(pairs),
            "action_changed_cells": action_changed_cells,
            "neutral_action_changed_cells": neutral_action_changed_cells,
            "score_changed_cells": score_changed_cells,
            "outcome_changed_cells": changed_outcomes,
            "positive_outcome_cells": positive_outcome_cells,
            "negative_outcome_cells": negative_outcome_cells,
            "positive_own_cells": positive_own_cells,
            "negative_own_cells": negative_own_cells,
            "new_losses": new_losses,
            "lost_wins": lost_wins,
            "negative_winpoint_strata": negative_winpoint_strata,
            "negative_own_strata": negative_own_strata,
            "negative_margin_strata": negative_margin_strata,
        },
        "totals": {
            "win_point_delta": Fraction(half_point_total, 2),
            "win_point_delta_mean": Fraction(
                half_point_total, 2 * len(pairs)
            ),
            "own_delta_sum": own_total,
            "own_delta_mean": _mean(own_total, len(pairs)),
            "rival_delta_sum": rival_total,
            "rival_delta_mean": _mean(rival_total, len(pairs)),
            "margin_delta_sum": margin_total,
            "margin_delta_mean": _mean(margin_total, len(pairs)),
        },
        "transitions": dict(sorted(transitions.items())),
        "paired_sign_test": {
            "positive": positive_outcome_cells,
            "negative": negative_outcome_cells,
            "ties_excluded": len(pairs) - changed_outcomes,
            "one_sided_p_exact": sign_p,
        },
        "strata": strata_rows,
    }
    result["receipt_sha256"] = _sha256(canonical_bytes(result))
    return _jsonable(result)


def classify_bytes(
    raw: bytes, *, expected_action_count: int = 719
) -> dict[str, Any]:
    document = _require_mapping(loads_strict(raw), "document")
    return classify_document(
        document,
        input_sha256=_sha256(raw),
        expected_action_count=expected_action_count,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="normalized paired-panel JSON")
    parser.add_argument("--output", type=Path, help="write canonical result JSON")
    parser.add_argument(
        "--expected-action-count",
        type=int,
        default=719,
        help="exact tested-seat action count per completed game (default: 719)",
    )
    parser.add_argument(
        "--require-verdict",
        action="append",
        choices=(
            "RATING_ADVANCE_SCREEN",
            "POLISH_ONLY",
            "MORE_EVIDENCE",
            "NO_SIGNAL",
            "REJECT",
        ),
        help="exit 3 unless the verdict is one of the supplied values",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        raw = args.report.read_bytes()
        result = classify_bytes(
            raw, expected_action_count=args.expected_action_count
        )
    except (OSError, GateError) as exc:
        error = {
            "schema": RESULT_SCHEMA,
            "verdict": "INVALID",
            "reason": str(exc),
        }
        payload = canonical_bytes(error)
        if args.output:
            args.output.write_bytes(payload)
        else:
            sys.stdout.buffer.write(payload)
        return 2

    payload = canonical_bytes(result)
    if args.output:
        args.output.write_bytes(payload)
    else:
        sys.stdout.buffer.write(payload)

    if (
        args.require_verdict
        and result["verdict"] not in set(args.require_verdict)
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
