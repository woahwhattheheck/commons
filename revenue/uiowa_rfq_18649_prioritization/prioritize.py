#!/usr/bin/env python3
"""Transparent recommendation prioritization worksheet (University of Iowa RFQ 18649).

Compares expected effects on quality, security and delivery against implementation
complexity, and produces a ranking in which every weight, every input and every
arithmetic step is visible next to the result.

Design rules this module enforces mechanically
----------------------------------------------
1.  A MISSING ESTIMATE IS NEVER A ZERO.  An absent, null, empty or explicitly
    "UNKNOWN" estimate becomes an `Unknown` sentinel that propagates.  It is not
    coerced to 0 (which would bury the item at the bottom of the list) and not
    coerced to the scale maximum (which would float it to the top).  An item whose
    ranking actually depends on an unknown is removed from the ranked list into a
    separate NEEDS_ESTIMATE bucket, unranked, with the blocking field named.
    An explicit `0` is a real estimate ("we looked, we expect no effect") and stays
    ranked.  `0` and UNKNOWN must never produce the same output; `test_prioritize.py`
    asserts this directly.

2.  WEIGHT-DEPENDENT MATERIALITY.  An unknown in a dimension the active weight
    vector gives zero weight to cannot change this ranking, so the item stays
    ranked -- but the unknown is still reported as `non_material_unknowns`, never
    dropped.  Give that dimension weight and the same item moves into the
    NEEDS_ESTIMATE bucket.  Unknown-ness is a property of the item; being
    *blocked* is a property of the item under a specific weighting.

3.  SENSITIVITY IS COMPUTED, NOT ASSERTED.  `sweep_scenarios` re-ranks under named
    weight vectors and reports which items are pinned and which move.
    `find_crossovers` walks one dimension's weight from 0.0 to 1.0 and reports the
    exact weight at which two items swap order.

4.  TIES STAY LEGIBLE.  Equal scores share a rank (standard competition ranking:
    1, 2, 2, 4).  Every tie group is reported with the inputs that produced it, so
    a reader can see what would separate the members.  Display order inside a tie
    group is by recommendation_id for determinism and carries no priority meaning.

This module is offline and uses the Python standard library only.  It performs no
network access, reads no University data, and produces no maturity score,
compliance verdict, peer percentile or individual performance rating.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------------
# Scales and vocabulary
# --------------------------------------------------------------------------------

#: Benefit dimensions, in the fixed display order used by every output.
DIMENSIONS: Tuple[str, ...] = ("quality", "security", "delivery")

#: Expected-effect scale.  0 is a REAL estimate meaning "assessed, no expected
#: effect".  It is not the same thing as "not estimated" -- see `Unknown`.
EFFECT_MIN = 0
EFFECT_MAX = 5

#: Implementation-complexity scale.  The floor is 1, not 0: "zero effort" is never
#: a real estimate, so a submitted 0 is rejected loudly instead of being accepted
#: as a free win that would divide its way to the top of the list.
COMPLEXITY_MIN = 1
COMPLEXITY_MAX = 5

#: Spellings that all mean "no estimate was supplied".
UNKNOWN_TOKENS = frozenset({"unknown", "", "n/a", "na", "tbd", "none", "null", "?"})

SCORE_PRECISION = 4

RANKED = "RANKED"
NEEDS_ESTIMATE = "NEEDS_ESTIMATE"

#: Literal written into the rank column of tabular output for an unranked item.
#: Deliberately a word, not an empty cell and not 0 -- a blank or a zero in a
#: spreadsheet is exactly how a missing estimate silently becomes a bottom rank.
NOT_RANKED = "NOT_RANKED"


class PrioritizationError(ValueError):
    """Raised for input that cannot be interpreted without guessing.

    Every message names the offending recommendation and field.  The module never
    repairs a malformed estimate by substitution; it refuses and says why.
    """


class _Unknown:
    """Sentinel for 'no estimate supplied'.

    Distinct from 0 by identity and by type.  Arithmetic against it is impossible
    by construction, so an unknown cannot leak into a score through a stray sum.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "UNKNOWN"

    def __bool__(self) -> bool:
        # Guards `if value:` style bugs that would treat UNKNOWN like a truthy 5.
        raise PrioritizationError(
            "UNKNOWN has no truth value; test with `is UNKNOWN` instead"
        )


UNKNOWN = _Unknown()


# --------------------------------------------------------------------------------
# Estimate parsing
# --------------------------------------------------------------------------------


def parse_estimate(raw: Any, *, rec_id: str, field: str, lo: int, hi: int):
    """Return an int within [lo, hi], or UNKNOWN.  Never returns a substituted value.

    Accepts either a bare value (``3``) or the documented estimate object
    (``{"value": 3, "basis": "...", "source": "..."}``) so a worksheet can carry
    the justification next to the number.
    """
    if isinstance(raw, dict):
        if "value" not in raw:
            # An estimate object with a basis but no number is still no estimate.
            return UNKNOWN
        raw = raw["value"]

    if raw is None:
        return UNKNOWN
    if isinstance(raw, str):
        token = raw.strip().lower()
        if token in UNKNOWN_TOKENS:
            return UNKNOWN
        try:
            raw = float(token)
        except ValueError:
            raise PrioritizationError(
                f"{rec_id}: field '{field}' is {raw!r}, which is neither a number on "
                f"the {lo}-{hi} scale nor a recognized unknown marker "
                f"({sorted(t for t in UNKNOWN_TOKENS if t)})"
            )
    if isinstance(raw, bool):
        # bool is an int subclass in Python; True would silently become 1.
        raise PrioritizationError(
            f"{rec_id}: field '{field}' is a boolean; estimates must be numeric "
            f"on the {lo}-{hi} scale or an explicit unknown marker"
        )
    if not isinstance(raw, (int, float)):
        raise PrioritizationError(
            f"{rec_id}: field '{field}' has unusable type {type(raw).__name__}"
        )
    if isinstance(raw, float) and not float(raw).is_integer():
        raise PrioritizationError(
            f"{rec_id}: field '{field}' is {raw}; the scale is whole numbers "
            f"{lo}-{hi}"
        )
    value = int(raw)
    if value < lo or value > hi:
        raise PrioritizationError(
            f"{rec_id}: field '{field}' is {value}, outside the documented "
            f"{lo}-{hi} scale. "
            + (
                "Complexity has no zero: 'no effort' is not a real estimate. Use an "
                "unknown marker if it has not been estimated."
                if field == "complexity" and value < lo
                else "Use an unknown marker if it has not been estimated."
            )
        )
    return value


def _text(raw: Any) -> str:
    """Read an optional free-text field without turning None into "None".

    `str(None)` is the string "None", which is how a JSON `null` becomes a
    four-character value that looks like content. The cross-lane UNKNOWN screen
    in `../uiowa_rfq_18649_unknown_propagation/` caught exactly that in this
    file's own output: a recommendation with `"notes": null` shipped with
    `"notes": "None"`. An absent value is an empty string, not a word.
    """
    if raw is None:
        return ""
    return str(raw).strip()


def _estimate_basis(raw: Any) -> str:
    """Pull the human justification out of an estimate object, if one was given."""
    if isinstance(raw, dict):
        basis = raw.get("basis")
        if isinstance(basis, str) and basis.strip():
            return basis.strip()
    return ""


# --------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------


class Recommendation:
    """One candidate recommendation with its estimates and their justifications."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise PrioritizationError(
                f"recommendation entries must be objects, got "
                f"{type(payload).__name__}"
            )
        rec_id = payload.get("recommendation_id")
        if not isinstance(rec_id, str) or not rec_id.strip():
            raise PrioritizationError(
                "every recommendation needs a non-empty 'recommendation_id'"
            )
        self.recommendation_id = rec_id.strip()
        self.title = _text(payload.get("title"))
        self.group = _text(payload.get("group"))
        self.area = _text(payload.get("area"))

        finding_ids = payload.get("finding_ids", [])
        if isinstance(finding_ids, str):
            finding_ids = [finding_ids]
        if not isinstance(finding_ids, list) or not all(
            isinstance(f, str) for f in finding_ids
        ):
            raise PrioritizationError(
                f"{self.recommendation_id}: 'finding_ids' must be a list of strings"
            )
        #: Traceability back to the finding register.  An empty list is reported as
        #: an untraceable recommendation rather than quietly accepted.
        self.finding_ids: List[str] = [f.strip() for f in finding_ids if f.strip()]

        raw_effects = payload.get("effects", {})
        if raw_effects is None:
            raw_effects = {}
        if not isinstance(raw_effects, dict):
            raise PrioritizationError(
                f"{self.recommendation_id}: 'effects' must be an object keyed by "
                f"{list(DIMENSIONS)}"
            )
        unexpected = sorted(set(raw_effects) - set(DIMENSIONS))
        if unexpected:
            raise PrioritizationError(
                f"{self.recommendation_id}: unrecognized effect dimension(s) "
                f"{unexpected}; the worksheet compares exactly {list(DIMENSIONS)}"
            )

        self.effects: Dict[str, Any] = {}
        self.effect_basis: Dict[str, str] = {}
        for dim in DIMENSIONS:
            raw = raw_effects.get(dim, None)
            self.effects[dim] = parse_estimate(
                raw,
                rec_id=self.recommendation_id,
                field=f"effects.{dim}",
                lo=EFFECT_MIN,
                hi=EFFECT_MAX,
            )
            self.effect_basis[dim] = _estimate_basis(raw)

        raw_complexity = payload.get("complexity", None)
        self.complexity = parse_estimate(
            raw_complexity,
            rec_id=self.recommendation_id,
            field="complexity",
            lo=COMPLEXITY_MIN,
            hi=COMPLEXITY_MAX,
        )
        self.complexity_basis = _estimate_basis(raw_complexity)
        self.notes = _text(payload.get("notes"))

    # -- convenience -------------------------------------------------------------

    @property
    def unknown_fields(self) -> List[str]:
        """Every field on this record with no estimate, regardless of weighting."""
        missing = [f"effects.{d}" for d in DIMENSIONS if self.effects[d] is UNKNOWN]
        if self.complexity is UNKNOWN:
            missing.append("complexity")
        return missing

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "group": self.group,
            "area": self.area,
            "finding_ids": list(self.finding_ids),
            "effects": {
                d: (None if self.effects[d] is UNKNOWN else self.effects[d])
                for d in DIMENSIONS
            },
            "effects_unknown": [
                d for d in DIMENSIONS if self.effects[d] is UNKNOWN
            ],
            "effect_basis": dict(self.effect_basis),
            "complexity": (
                None if self.complexity is UNKNOWN else self.complexity
            ),
            "complexity_unknown": self.complexity is UNKNOWN,
            "complexity_basis": self.complexity_basis,
            "notes": self.notes,
        }


class Weights:
    """A normalized weight vector over the benefit dimensions.

    Normalization is performed and *reported*: `raw` keeps what the operator typed
    and `normalized` is what the arithmetic used, so nobody has to reverse-engineer
    a hidden rescale.
    """

    def __init__(self, raw: Dict[str, Any], name: str = "custom") -> None:
        self.name = name
        if not isinstance(raw, dict):
            raise PrioritizationError("weights must be an object")
        unexpected = sorted(set(raw) - set(DIMENSIONS))
        if unexpected:
            raise PrioritizationError(
                f"weight scenario '{name}': unrecognized dimension(s) {unexpected}"
            )
        values: Dict[str, float] = {}
        for dim in DIMENSIONS:
            v = raw.get(dim, 0)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise PrioritizationError(
                    f"weight scenario '{name}': weight for '{dim}' must be a number"
                )
            if v < 0:
                raise PrioritizationError(
                    f"weight scenario '{name}': weight for '{dim}' is negative"
                )
            values[dim] = float(v)
        total = sum(values.values())
        if total <= 0:
            raise PrioritizationError(
                f"weight scenario '{name}': weights sum to {total}; at least one "
                f"dimension must carry weight"
            )
        self.raw: Dict[str, float] = values
        self.raw_total = total
        self.normalized: Dict[str, float] = {
            d: values[d] / total for d in DIMENSIONS
        }
        self.was_normalized = not math.isclose(total, 1.0, abs_tol=1e-9)

    def weighted_dimensions(self) -> List[str]:
        """Dimensions that can actually move this ranking."""
        return [d for d in DIMENSIONS if self.normalized[d] > 0.0]

    def formula(self) -> str:
        parts = " + ".join(
            f"{self.normalized[d]:.3f}x{d}" for d in DIMENSIONS
        )
        return f"benefit = {parts}; priority_score = benefit / complexity"

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "raw": dict(self.raw),
            "raw_total": round(self.raw_total, 6),
            "normalized": {d: round(self.normalized[d], 6) for d in DIMENSIONS},
            "was_normalized": self.was_normalized,
            "formula": self.formula(),
        }


# --------------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------------


def _round(x: float) -> float:
    return round(x + 0.0, SCORE_PRECISION)


def score_recommendation(rec: Recommendation, weights: Weights) -> Dict[str, Any]:
    """Score one recommendation under one weight vector.

    Returns a record that always carries the full arithmetic (each dimension's
    weight, raw estimate and contribution) whether or not the item ends up ranked.
    An item is ranked only when every dimension carrying weight has an estimate and
    complexity has an estimate.
    """
    blocking: List[str] = []
    non_material: List[str] = []

    for dim in DIMENSIONS:
        if rec.effects[dim] is UNKNOWN:
            if weights.normalized[dim] > 0.0:
                blocking.append(f"effects.{dim}")
            else:
                # Still surfaced: the estimate is missing, it just cannot change
                # *this* ranking.  Weighting it turns this into a blocker.
                non_material.append(f"effects.{dim}")
    if rec.complexity is UNKNOWN:
        blocking.append("complexity")

    contributions: Dict[str, Any] = {}
    for dim in DIMENSIONS:
        value = rec.effects[dim]
        contributions[dim] = {
            "weight": round(weights.normalized[dim], 6),
            "estimate": None if value is UNKNOWN else value,
            "estimate_is_unknown": value is UNKNOWN,
            "contribution": (
                None
                if value is UNKNOWN
                else _round(weights.normalized[dim] * value)
            ),
            "basis": rec.effect_basis[dim],
        }

    record: Dict[str, Any] = {
        "recommendation_id": rec.recommendation_id,
        "title": rec.title,
        "group": rec.group,
        "area": rec.area,
        "finding_ids": list(rec.finding_ids),
        "traceable_to_finding": bool(rec.finding_ids),
        "contributions": contributions,
        "complexity": None if rec.complexity is UNKNOWN else rec.complexity,
        "complexity_basis": rec.complexity_basis,
        "unknown_fields": rec.unknown_fields,
        "blocking_unknowns": blocking,
        "non_material_unknowns": non_material,
        "notes": rec.notes,
    }

    if blocking:
        record["status"] = NEEDS_ESTIMATE
        record["rank"] = None
        record["benefit"] = None
        record["priority_score"] = None
        record["arithmetic"] = (
            "not computed: "
            + ", ".join(blocking)
            + " has no estimate. A missing estimate is not scored as 0."
        )
        bound = _score_bounds(rec, weights)
        record["score_bounds"] = bound
        return record

    # Only dimensions carrying weight are read at all. A zero-weight dimension
    # contributes nothing by definition, so an unestimated value there is never
    # touched -- which is how a non-material UNKNOWN stays out of the sum. The
    # sentinel has no arithmetic, so a regression that reads one here raises a
    # TypeError instead of quietly scoring a missing estimate as 0.
    benefit = 0.0
    terms: List[str] = []
    for dim in DIMENSIONS:
        weight = weights.normalized[dim]
        if weight == 0.0:
            continue
        value = rec.effects[dim]
        if value is UNKNOWN:  # pragma: no cover - unreachable via `blocking`
            raise PrioritizationError(
                f"{rec.recommendation_id}: internal error, tried to score the "
                f"unestimated dimension '{dim}' which carries weight {weight}"
            )
        benefit += weight * value
        terms.append(f"{weight:.3f}x{value}")
    skipped = [d for d in DIMENSIONS if weights.normalized[d] == 0.0]
    score = benefit / rec.complexity
    record["status"] = RANKED
    record["benefit"] = _round(benefit)
    record["priority_score"] = _round(score)
    record["arithmetic"] = (
        f"benefit = {' + '.join(terms)} = {_round(benefit)}; "
        f"score = {_round(benefit)} / {rec.complexity} = {_round(score)}"
        + (f" (zero weight, not read: {', '.join(skipped)})" if skipped else "")
    )
    record["score_bounds"] = None
    return record


def _score_bounds(rec: Recommendation, weights: Weights) -> Dict[str, Any]:
    """Best/worst score an unranked item could take if its unknowns were filled in.

    This is a BOUND, never a score: it is reported to show whether the missing
    estimate is decision-blocking (the item could plausibly land at the top) or
    merely incomplete (it could not reach the top under any admissible value).
    The item stays unranked either way.
    """
    lo_benefit = 0.0
    hi_benefit = 0.0
    for dim in DIMENSIONS:
        w = weights.normalized[dim]
        value = rec.effects[dim]
        if value is UNKNOWN:
            lo_benefit += w * EFFECT_MIN
            hi_benefit += w * EFFECT_MAX
        else:
            lo_benefit += w * value
            hi_benefit += w * value
    if rec.complexity is UNKNOWN:
        lo_complexity, hi_complexity = COMPLEXITY_MAX, COMPLEXITY_MIN
    else:
        lo_complexity = hi_complexity = rec.complexity
    return {
        "basis": (
            "bound, not a score: the unknown estimate is walked across its full "
            f"admissible range (effects {EFFECT_MIN}-{EFFECT_MAX}, complexity "
            f"{COMPLEXITY_MIN}-{COMPLEXITY_MAX})"
        ),
        "score_if_unknowns_lowest": _round(lo_benefit / lo_complexity),
        "score_if_unknowns_highest": _round(hi_benefit / hi_complexity),
    }


# --------------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------------


def _assign_ranks(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Standard competition ranking (1, 2, 2, 4) with explicit tie groups.

    Sorting inside a tie is by recommendation_id purely so output is byte-stable.
    Each record records `tie_group_size` and `display_order_is_not_priority` so a
    reader is never invited to read a within-tie position as a decision.
    """
    ordered = sorted(
        scored,
        key=lambda r: (-r["priority_score"], r["recommendation_id"]),
    )
    rank = 0
    seen = 0
    previous: Optional[float] = None
    for record in ordered:
        seen += 1
        if previous is None or record["priority_score"] != previous:
            rank = seen
            previous = record["priority_score"]
        record["rank"] = rank
    counts: Dict[int, int] = {}
    for record in ordered:
        counts[record["rank"]] = counts.get(record["rank"], 0) + 1
    for record in ordered:
        size = counts[record["rank"]]
        record["tie_group_size"] = size
        record["is_tied"] = size > 1
        record["display_order_is_not_priority"] = size > 1
    return ordered


def _tie_corner_probe(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each dimension, does weighting *only* that dimension break this tie?

    Computed, not guessed: at a corner weighting the benefit collapses to the one
    estimate, so the score is simply ``estimate / complexity``. This turns "the
    tie is an artifact of the weights" from a claim into something a reader can
    check, and it names the weighting that would resolve it.
    """
    probe: List[Dict[str, Any]] = []
    for dim in DIMENSIONS:
        scores: Dict[str, float] = {}
        missing: List[str] = []
        for member in members:
            estimate = member["contributions"][dim]["estimate"]
            if estimate is None:
                missing.append(member["recommendation_id"])
                continue
            scores[member["recommendation_id"]] = _round(
                estimate / member["complexity"]
            )
        if missing:
            probe.append(
                {
                    "dimension": dim,
                    "separates": None,
                    "scores_at_full_weight": scores,
                    "detail": (
                        f"not testable: {', '.join(missing)} has no {dim} "
                        f"estimate, so this weighting would move the item into "
                        f"the needs-estimate bucket rather than rank it"
                    ),
                }
            )
            continue
        separates = len(set(scores.values())) > 1
        probe.append(
            {
                "dimension": dim,
                "separates": separates,
                "scores_at_full_weight": scores,
                "detail": (
                    "separates them: "
                    + ", ".join(f"{k} {v}" for k, v in sorted(scores.items()))
                    if separates
                    else "still tied at this corner"
                ),
            }
        )
    return probe


def _separating_advice(
    corner: List[Dict[str, Any]], separators: List[str]
) -> List[str]:
    """Plain statement of what a reader could actually do about a tie."""
    advice: List[str] = []
    for entry in corner:
        if entry["separates"] is True:
            advice.append(
                f"weight {entry['dimension']} alone and they separate ("
                + ", ".join(
                    f"{k} {v}" for k, v in sorted(entry["scores_at_full_weight"].items())
                )
                + ")"
            )
        elif entry["separates"] is None:
            advice.append(f"{entry['dimension']}: {entry['detail']}")
    if not advice:
        if separators:
            advice.append(
                "no single-dimension weighting separates them; the input "
                "differences cancel at every corner tested, so a tiebreak has to "
                "come from something this worksheet does not carry (sequencing, "
                "owner availability, a dependency)"
            )
        else:
            advice.append(
                "nothing in the current model: these are equivalent on every "
                "scored input, so a tiebreak has to come from something this "
                "worksheet does not carry (sequencing, owner availability, a "
                "dependency)"
            )
    return advice


def _tie_groups(ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Describe each tie so a reader can see what would separate the members."""
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for record in ranked:
        groups.setdefault(record["rank"], []).append(record)
    out: List[Dict[str, Any]] = []
    for rank in sorted(groups):
        members = groups[rank]
        if len(members) < 2:
            continue
        separators: List[str] = []
        for dim in DIMENSIONS:
            values = {m["contributions"][dim]["estimate"] for m in members}
            if len(values) > 1:
                # A ranked item can still carry a None here: an unknown in a
                # zero-weight dimension is non-material, not absent. Sort with a
                # key so None does not blow up the comparison, and print it as
                # UNKNOWN rather than as a number.
                shown = sorted(
                    values, key=lambda v: (v is None, v if v is not None else 0)
                )
                separators.append(
                    f"{dim} estimates differ "
                    f"({[('UNKNOWN' if v is None else v) for v in shown]})"
                )
        complexities = {m["complexity"] for m in members}
        if len(complexities) > 1:
            separators.append(
                f"complexity differs ({sorted(complexities)})"
            )
        corner = _tie_corner_probe(members)
        out.append(
            {
                "rank": rank,
                "members": [m["recommendation_id"] for m in members],
                "shared_priority_score": members[0]["priority_score"],
                "member_inputs": [
                    {
                        "recommendation_id": m["recommendation_id"],
                        "benefit": m["benefit"],
                        "complexity": m["complexity"],
                        "effects": {
                            d: m["contributions"][d]["estimate"]
                            for d in DIMENSIONS
                        },
                    }
                    for m in members
                ],
                "why_tied": (
                    "identical benefit and complexity inputs"
                    if not separators
                    else "different inputs whose differences cancel at these "
                    "weights: " + "; ".join(separators)
                ),
                "corner_probe": corner,
                "what_would_separate_them": _separating_advice(corner, separators),
                "resolution": (
                    "left tied; display order inside the group is by "
                    "recommendation_id and carries no priority meaning"
                ),
            }
        )
    return out


def rank(
    recommendations: Sequence[Recommendation],
    weights: Weights,
) -> Dict[str, Any]:
    """Produce one complete ranking under one weight vector."""
    scored = [score_recommendation(r, weights) for r in recommendations]
    ranked = _assign_ranks([r for r in scored if r["status"] == RANKED])
    needs_estimate = sorted(
        (r for r in scored if r["status"] == NEEDS_ESTIMATE),
        key=lambda r: r["recommendation_id"],
    )

    # Is the missing estimate actually in the way of a decision?  If the item's
    # best possible score would still not reach the top ranked score, filling the
    # estimate in cannot change who goes first.
    top_score = ranked[0]["priority_score"] if ranked else None
    for record in needs_estimate:
        bounds = record["score_bounds"]
        if top_score is None:
            record["estimate_urgency"] = "DECISION_BLOCKING"
            record["estimate_urgency_basis"] = (
                "nothing is rankable, so every missing estimate is in the way"
            )
        elif bounds["score_if_unknowns_highest"] >= top_score:
            record["estimate_urgency"] = "DECISION_BLOCKING"
            record["estimate_urgency_basis"] = (
                f"upper bound {bounds['score_if_unknowns_highest']} reaches or "
                f"exceeds the current top score {top_score}: this item could lead "
                f"the list, so the ranking is not decidable without the estimate"
            )
        else:
            record["estimate_urgency"] = "NOT_DECISION_BLOCKING"
            record["estimate_urgency_basis"] = (
                f"upper bound {bounds['score_if_unknowns_highest']} is below the "
                f"current top score {top_score}: the estimate is still missing and "
                f"the item is still unranked, but filling it in cannot change who "
                f"leads"
            )

    return {
        "weights": weights.to_public_dict(),
        "ranked": ranked,
        "needs_estimate": needs_estimate,
        "tie_groups": _tie_groups(ranked),
        "counts": {
            "total": len(scored),
            "ranked": len(ranked),
            "needs_estimate": len(needs_estimate),
            "decision_blocking_unknowns": sum(
                1
                for r in needs_estimate
                if r["estimate_urgency"] == "DECISION_BLOCKING"
            ),
        },
    }


# --------------------------------------------------------------------------------
# Sensitivity analysis
# --------------------------------------------------------------------------------


def sweep_scenarios(
    recommendations: Sequence[Recommendation],
    scenarios: Sequence[Weights],
) -> Dict[str, Any]:
    """Re-rank under each named weight vector and report what actually moved."""
    if not scenarios:
        raise PrioritizationError("sensitivity analysis needs at least one scenario")
    results = {s.name: rank(recommendations, s) for s in scenarios}

    stability: List[Dict[str, Any]] = []
    for rec in sorted(recommendations, key=lambda r: r.recommendation_id):
        rid = rec.recommendation_id
        positions: Dict[str, Any] = {}
        numeric: List[int] = []
        unranked_in: List[str] = []
        for scenario in scenarios:
            result = results[scenario.name]
            hit = next(
                (r for r in result["ranked"] if r["recommendation_id"] == rid), None
            )
            if hit is None:
                positions[scenario.name] = NOT_RANKED
                unranked_in.append(scenario.name)
            else:
                positions[scenario.name] = hit["rank"]
                numeric.append(hit["rank"])
        if unranked_in and numeric:
            label = "ENTERS_UNKNOWN_BUCKET"
            detail = (
                "ranked under some weightings and unranked under "
                + ", ".join(unranked_in)
                + ": a dimension it never estimated carries weight there"
            )
        elif unranked_in:
            label = "NEVER_RANKED"
            detail = "blocked by a missing estimate under every scenario tested"
        elif len(set(numeric)) == 1:
            label = "PINNED"
            detail = f"rank {numeric[0]} under every scenario tested"
        else:
            label = "MOVES"
            detail = f"rank {min(numeric)} to {max(numeric)} across scenarios"
        stability.append(
            {
                "recommendation_id": rid,
                "title": rec.title,
                "rank_by_scenario": positions,
                "best_rank": min(numeric) if numeric else None,
                "worst_rank": max(numeric) if numeric else None,
                "rank_spread": (max(numeric) - min(numeric)) if numeric else None,
                "stability": label,
                "stability_basis": detail,
            }
        )

    leaders: Dict[str, Any] = {}
    for scenario in scenarios:
        ranked = results[scenario.name]["ranked"]
        leaders[scenario.name] = (
            [r["recommendation_id"] for r in ranked if r["rank"] == 1]
            if ranked
            else []
        )
    distinct_leaders = {tuple(v) for v in leaders.values()}

    return {
        "scenarios": [s.to_public_dict() for s in scenarios],
        "results": results,
        "rank_stability": stability,
        "leader_by_scenario": leaders,
        "top_item_stable": len(distinct_leaders) == 1,
        "interpretation": (
            "the leading recommendation is the same under every weighting tested, "
            "so the top of this list does not depend on the weights"
            if len(distinct_leaders) == 1
            else "the leading recommendation changes with the weights: this ranking "
            "is an argument about priorities, not a measurement, and the weight "
            "vector has to be agreed before the order means anything"
        ),
    }


def find_crossovers(
    recommendations: Sequence[Recommendation],
    dimension: str,
    *,
    steps: int = 100,
    base: Optional[Weights] = None,
) -> Dict[str, Any]:
    """Walk one dimension's weight 0.0 -> 1.0 and report where the order changes.

    The remaining weight is split across the other dimensions in the same
    proportion the base vector gave them, so the sweep isolates one assumption.
    """
    if dimension not in DIMENSIONS:
        raise PrioritizationError(
            f"unknown dimension '{dimension}'; expected one of {list(DIMENSIONS)}"
        )
    if steps < 2:
        raise PrioritizationError("a sweep needs at least 2 steps")
    if base is None:
        base = Weights({d: 1.0 for d in DIMENSIONS}, name="equal")
    others = [d for d in DIMENSIONS if d != dimension]
    other_total = sum(base.normalized[d] for d in others)

    points: List[Dict[str, Any]] = []
    previous_order: Optional[List[str]] = None
    crossovers: List[Dict[str, Any]] = []

    for i in range(steps + 1):
        w = i / steps
        raw = {dimension: w}
        for d in others:
            share = (
                base.normalized[d] / other_total if other_total > 0 else 1.0 / len(others)
            )
            raw[d] = (1.0 - w) * share
        if sum(raw.values()) <= 0:  # pragma: no cover - guarded by w in [0,1]
            continue
        try:
            weights = Weights(raw, name=f"{dimension}={w:.2f}")
        except PrioritizationError:
            continue
        result = rank(recommendations, weights)
        order = [r["recommendation_id"] for r in result["ranked"]]
        points.append(
            {
                "weight": round(w, 6),
                "order": order,
                "unranked": [
                    r["recommendation_id"] for r in result["needs_estimate"]
                ],
            }
        )
        if previous_order is not None and order != previous_order:
            leader_changed = bool(order) and bool(previous_order) and (
                order[0] != previous_order[0]
            )
            entered = [r for r in order if r not in previous_order]
            left = [r for r in previous_order if r not in order]
            crossovers.append(
                {
                    "at_weight": round(w, 6),
                    "dimension": dimension,
                    "order_before": previous_order,
                    "order_after": order,
                    "changed": _describe_order_change(previous_order, order),
                    "leader_changed": leader_changed,
                    "leader_before": previous_order[0] if previous_order else None,
                    "leader_after": order[0] if order else None,
                    "entered_ranked_list": entered,
                    "left_ranked_list": left,
                }
            )
        previous_order = order

    # The two changes a reader actually cares about, pulled out of the noise: the
    # weight at which the top of the list changes hands, and the weights at which
    # a missing estimate starts or stops mattering.
    leader_changes = [c for c in crossovers if c["leader_changed"]]
    materiality_changes = [
        c for c in crossovers if c["entered_ranked_list"] or c["left_ranked_list"]
    ]

    return {
        "dimension": dimension,
        "base_weights": base.to_public_dict(),
        "steps": steps,
        "points": points,
        "crossovers": crossovers,
        "leader_changes": leader_changes,
        "materiality_changes": materiality_changes,
        "reorders": bool(crossovers),
    }


def _describe_order_change(before: List[str], after: List[str]) -> List[str]:
    """Plain-language account of what moved between two orderings."""
    changes: List[str] = []
    before_pos = {rid: i for i, rid in enumerate(before)}
    after_pos = {rid: i for i, rid in enumerate(after)}
    for rid in sorted(set(before) | set(after)):
        if rid not in before_pos:
            changes.append(f"{rid} entered the ranked list")
        elif rid not in after_pos:
            changes.append(f"{rid} left the ranked list (estimate became blocking)")
        elif before_pos[rid] != after_pos[rid]:
            changes.append(
                f"{rid} moved from position {before_pos[rid] + 1} to "
                f"{after_pos[rid] + 1}"
            )
    return changes


# --------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------


def load_recommendations(payload: Any) -> List[Recommendation]:
    """Accept either a bare list or ``{"recommendations": [...]}``."""
    if isinstance(payload, dict):
        payload = payload.get("recommendations", payload.get("items"))
    if not isinstance(payload, list):
        raise PrioritizationError(
            "expected a list of recommendations, or an object with a "
            "'recommendations' list"
        )
    recs = [Recommendation(entry) for entry in payload]
    seen: Dict[str, int] = {}
    for rec in recs:
        seen[rec.recommendation_id] = seen.get(rec.recommendation_id, 0) + 1
    duplicates = sorted(k for k, v in seen.items() if v > 1)
    if duplicates:
        raise PrioritizationError(
            f"duplicate recommendation_id(s): {duplicates}"
        )
    return recs


def load_scenarios(payload: Any) -> List[Weights]:
    """Accept ``{"scenarios": {"name": {...}}}`` or a bare name->weights map."""
    if isinstance(payload, dict) and "scenarios" in payload:
        payload = payload["scenarios"]
    if not isinstance(payload, dict):
        raise PrioritizationError(
            "expected weight scenarios as an object mapping name -> weights"
        )
    scenarios: List[Weights] = []
    for name in payload:
        entry = payload[name]
        if isinstance(entry, dict) and "weights" in entry:
            scenarios.append(Weights(entry["weights"], name=name))
        else:
            scenarios.append(Weights(entry, name=name))
    if not scenarios:
        raise PrioritizationError("no weight scenarios supplied")
    return scenarios


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as exc:
            raise PrioritizationError(f"{path}: not valid JSON ({exc})") from exc


# --------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------

CSV_COLUMNS = [
    "rank",
    "status",
    "recommendation_id",
    "title",
    "group",
    "area",
    "finding_ids",
    "quality_estimate",
    "security_estimate",
    "delivery_estimate",
    "complexity",
    "benefit",
    "priority_score",
    "blocked_by",
    "non_material_unknowns",
    "estimate_urgency",
    "score_bound_low",
    "score_bound_high",
    "tie_group_size",
    "arithmetic",
]


def _cell(value: Any) -> str:
    """Render a value for CSV without ever emitting a bare 0 for 'unknown'."""
    if value is None:
        return "UNKNOWN"
    return str(value)


def to_csv_rows(result: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = [list(CSV_COLUMNS)]
    for record in result["ranked"] + result["needs_estimate"]:
        rows.append(
            [
                str(record["rank"]) if record["rank"] is not None else NOT_RANKED,
                record["status"],
                record["recommendation_id"],
                record["title"],
                record["group"],
                record["area"],
                "|".join(record["finding_ids"]) or "NONE",
                _cell(record["contributions"]["quality"]["estimate"]),
                _cell(record["contributions"]["security"]["estimate"]),
                _cell(record["contributions"]["delivery"]["estimate"]),
                _cell(record["complexity"]),
                _cell(record["benefit"]),
                _cell(record["priority_score"]),
                "|".join(record["blocking_unknowns"]) or "",
                "|".join(record["non_material_unknowns"]) or "",
                record.get("estimate_urgency", ""),
                _cell(
                    (record.get("score_bounds") or {}).get(
                        "score_if_unknowns_lowest"
                    )
                )
                if record.get("score_bounds")
                else "",
                _cell(
                    (record.get("score_bounds") or {}).get(
                        "score_if_unknowns_highest"
                    )
                )
                if record.get("score_bounds")
                else "",
                str(record.get("tie_group_size", "")),
                record["arithmetic"],
            ]
        )
    return rows


def write_csv(result: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(to_csv_rows(result))


def render_markdown(
    result: Dict[str, Any],
    sensitivity: Optional[Dict[str, Any]] = None,
    crossover: Optional[Dict[str, Any]] = None,
    source_label: str = "",
) -> str:
    weights = result["weights"]
    out: List[str] = []
    out.append("# Recommendation prioritization worksheet")
    out.append("")
    out.append(
        "SYNTHETIC / DRAFT. Generated by `prioritize.py`. The recommendation set "
        "below is fiction written to exercise the calculator. It is not a "
        "University of Iowa finding, assessment, score or commitment."
    )
    if source_label:
        out.append("")
        out.append(f"Source recommendation set: `{source_label}`")
    out.append("")
    out.append("## The formula, and the weights it used")
    out.append("")
    out.append("```")
    out.append(weights["formula"])
    out.append("```")
    out.append("")
    out.append("| dimension | weight as entered | weight used |")
    out.append("|---|---:|---:|")
    for dim in DIMENSIONS:
        out.append(
            f"| {dim} | {weights['raw'][dim]:g} | {weights['normalized'][dim]:.3f} |"
        )
    out.append("")
    if weights["was_normalized"]:
        out.append(
            f"Entered weights summed to {weights['raw_total']:g}, so they were "
            f"normalized to 1.0. The normalization is shown above rather than "
            f"applied silently."
        )
    else:
        out.append("Entered weights already summed to 1.0; no rescaling applied.")
    out.append("")
    out.append(
        f"Scales: expected effect {EFFECT_MIN}-{EFFECT_MAX} (0 means *assessed, no "
        f"expected effect*); implementation complexity {COMPLEXITY_MIN}-"
        f"{COMPLEXITY_MAX} (there is no zero -- \"no effort\" is not a real "
        f"estimate). A blank estimate is **UNKNOWN**, which is not 0."
    )
    out.append("")

    out.append("## Ranked")
    out.append("")
    if not result["ranked"]:
        out.append("_Nothing is rankable under this weighting._")
    else:
        out.append(
            "| rank | id | recommendation | Q | S | D | benefit | cplx | score | "
            "arithmetic |"
        )
        out.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---|")
        for r in result["ranked"]:
            tie = " (tied)" if r["is_tied"] else ""
            out.append(
                "| {rank}{tie} | `{rid}` | {title} | {q} | {s} | {d} | {b} | "
                "{c} | **{score}** | {arith} |".format(
                    rank=r["rank"],
                    tie=tie,
                    rid=r["recommendation_id"],
                    title=r["title"],
                    q=_cell(r["contributions"]["quality"]["estimate"]),
                    s=_cell(r["contributions"]["security"]["estimate"]),
                    d=_cell(r["contributions"]["delivery"]["estimate"]),
                    b=r["benefit"],
                    c=r["complexity"],
                    score=r["priority_score"],
                    arith=r["arithmetic"],
                )
            )
    out.append("")

    out.append("## Needs estimate (not ranked, not scored zero)")
    out.append("")
    if not result["needs_estimate"]:
        out.append("_Every recommendation carried the estimates this weighting uses._")
    else:
        out.append(
            "These are held out of the ranking because a value the current weights "
            "depend on was never estimated. They are **not** scored 0 and **not** "
            "placed last; an unestimated item is an open question, not a low "
            "priority."
        )
        out.append("")
        out.append(
            "| id | recommendation | missing | possible score range | urgency | "
            "why that urgency |"
        )
        out.append("|---|---|---|---|---|---|")
        for r in result["needs_estimate"]:
            bounds = r["score_bounds"]
            out.append(
                "| `{rid}` | {title} | {missing} | {lo} - {hi} | **{urg}** | "
                "{basis} |".format(
                    rid=r["recommendation_id"],
                    title=r["title"],
                    missing=", ".join(f"`{f}`" for f in r["blocking_unknowns"]),
                    lo=bounds["score_if_unknowns_lowest"],
                    hi=bounds["score_if_unknowns_highest"],
                    urg=r["estimate_urgency"],
                    basis=r["estimate_urgency_basis"],
                )
            )
        out.append("")
        out.append(
            "The range is a **bound, not a score**: it is what the item could score "
            "if the missing value turned out to sit anywhere in its admissible "
            "range. It exists to answer one question -- does this gap change the "
            "decision, or just the paperwork?"
        )
    out.append("")

    non_material = [
        r for r in result["ranked"] if r["non_material_unknowns"]
    ]
    if non_material:
        out.append("## Ranked, but carrying an unestimated dimension")
        out.append("")
        out.append(
            "These items are missing an estimate in a dimension the current weights "
            "give **zero** weight, so the gap cannot move this ranking. The gap is "
            "still real and is reported here rather than dropped. Give that "
            "dimension any weight and these items move into the needs-estimate "
            "bucket."
        )
        out.append("")
        out.append("| id | rank here | unestimated |")
        out.append("|---|---:|---|")
        for r in non_material:
            out.append(
                f"| `{r['recommendation_id']}` | {r['rank']} | "
                f"{', '.join('`' + f + '`' for f in r['non_material_unknowns'])} |"
            )
        out.append("")

    untraceable = [
        r
        for r in result["ranked"] + result["needs_estimate"]
        if not r["traceable_to_finding"]
    ]
    if untraceable:
        out.append("## Not traceable to a finding")
        out.append("")
        out.append(
            "These recommendations carry no `finding_ids`. They still rank, "
            "because the arithmetic does not depend on provenance -- but a "
            "recommendation that cannot be traced back to a finding is not "
            "defensible in a report, whatever it scores. Treat this as a gap in "
            "the recommendation, not in the calculation."
        )
        out.append("")
        for r in untraceable:
            position = (
                f"rank {r['rank']}" if r["rank"] is not None else "not ranked"
            )
            out.append(f"- `{r['recommendation_id']}` ({position}) -- {r['title']}")
        out.append("")

    out.append("## Ties")
    out.append("")
    if not result["tie_groups"]:
        out.append("_No ties under this weighting._")
    else:
        for group in result["tie_groups"]:
            out.append(
                f"**Rank {group['rank']} is shared** by "
                + ", ".join(f"`{m}`" for m in group["members"])
                + f" at score {group['shared_priority_score']}."
            )
            out.append("")
            out.append("| id | benefit | complexity | Q | S | D |")
            out.append("|---|---:|---:|---:|---:|---:|")
            for member in group["member_inputs"]:
                out.append(
                    "| `{rid}` | {b} | {c} | {q} | {s} | {d} |".format(
                        rid=member["recommendation_id"],
                        b=member["benefit"],
                        c=member["complexity"],
                        q=_cell(member["effects"]["quality"]),
                        s=_cell(member["effects"]["security"]),
                        d=_cell(member["effects"]["delivery"]),
                    )
                )
            out.append("")
            out.append(f"- Why they tie: {group['why_tied']}")
            out.append(
                "- What would separate them: "
                + "; ".join(group["what_would_separate_them"])
            )
            out.append(f"- Resolution: {group['resolution']}")
            out.append("")

    if sensitivity:
        out.append("## Sensitivity to the weights")
        out.append("")
        out.append(sensitivity["interpretation"] + ".")
        out.append("")
        names = [s["name"] for s in sensitivity["scenarios"]]
        out.append("| scenario | " + " | ".join(f"{d} w" for d in DIMENSIONS) + " | leads |")
        out.append("|---|" + "---:|" * len(DIMENSIONS) + "---|")
        for scenario in sensitivity["scenarios"]:
            leaders = sensitivity["leader_by_scenario"][scenario["name"]]
            out.append(
                f"| {scenario['name']} | "
                + " | ".join(
                    f"{scenario['normalized'][d]:.3f}" for d in DIMENSIONS
                )
                + " | "
                + (", ".join(f"`{x}`" for x in leaders) or "_nothing rankable_")
                + " |"
            )
        out.append("")
        out.append("| id | " + " | ".join(names) + " | spread | stability |")
        out.append("|---|" + "---:|" * len(names) + "---:|---|")
        for row in sensitivity["rank_stability"]:
            cells = [str(row["rank_by_scenario"][n]) for n in names]
            out.append(
                f"| `{row['recommendation_id']}` | "
                + " | ".join(cells)
                + f" | {row['rank_spread'] if row['rank_spread'] is not None else '-'}"
                + f" | {row['stability']} |"
            )
        out.append("")

    if crossover:
        out.append(f"## Crossover sweep: `{crossover['dimension']}` weight 0.0 -> 1.0")
        out.append("")
        if not crossover["crossovers"]:
            out.append(
                "_No reordering: sweeping this weight across its full range never "
                "changed the order. The ranking is insensitive to this assumption._"
            )
        else:
            out.append(
                f"{len(crossover['crossovers'])} order change(s) across "
                f"{crossover['steps']} steps. The two that matter:"
            )
            out.append("")
            out.append("**The top of the list changes hands at:**")
            out.append("")
            if crossover["leader_changes"]:
                for point in crossover["leader_changes"]:
                    out.append(
                        f"- `{crossover['dimension']}` weight **"
                        f"{point['at_weight']:.2f}** -- `{point['leader_before']}` "
                        f"gives way to `{point['leader_after']}`"
                    )
            else:
                out.append(
                    "- nowhere: the same recommendation leads across the whole "
                    "sweep"
                )
            out.append("")
            out.append("**A missing estimate starts or stops mattering at:**")
            out.append("")
            if crossover["materiality_changes"]:
                for point in crossover["materiality_changes"]:
                    for rid in point["left_ranked_list"]:
                        out.append(
                            f"- `{crossover['dimension']}` weight **"
                            f"{point['at_weight']:.2f}** -- `{rid}` leaves the "
                            f"ranked list: the dimension it never estimated now "
                            f"carries weight, so it moves to the needs-estimate "
                            f"bucket instead of being scored"
                        )
                    for rid in point["entered_ranked_list"]:
                        out.append(
                            f"- `{crossover['dimension']}` weight **"
                            f"{point['at_weight']:.2f}** -- `{rid}` enters the "
                            f"ranked list: the dimension it never estimated has "
                            f"dropped to zero weight, so the gap can no longer "
                            f"change this order (the gap is still reported)"
                        )
            else:
                out.append(
                    "- nowhere: no item's missing estimate changes materiality "
                    "across this sweep"
                )
            out.append("")
            out.append("<details><summary>All order changes in the sweep</summary>")
            out.append("")
            out.append("| at weight | what changed |")
            out.append("|---:|---|")
            for point in crossover["crossovers"]:
                out.append(
                    f"| {point['at_weight']:.2f} | "
                    + "; ".join(point["changed"])
                    + " |"
                )
            out.append("")
            out.append("</details>")
        out.append("")

    out.append("---")
    out.append("")
    out.append(
        "Produced offline by `prioritize.py` (Python standard library only). The "
        "worksheet ranks *proposed* work against *estimated* effects. It is not a "
        "maturity score, a compliance verdict, a peer comparison or an assessment "
        "of any individual."
    )
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------

DEFAULT_SCENARIOS = {
    "baseline": {"quality": 0.35, "security": 0.40, "delivery": 0.25},
    "security-led": {"quality": 0.20, "security": 0.65, "delivery": 0.15},
    "delivery-led": {"quality": 0.25, "security": 0.15, "delivery": 0.60},
    "quality-led": {"quality": 0.60, "security": 0.25, "delivery": 0.15},
    "equal": {"quality": 1, "security": 1, "delivery": 1},
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prioritize.py",
        description=(
            "Rank recommendations by weighted expected effect over implementation "
            "complexity, keeping every weight, input and step visible. Missing "
            "estimates are held out as UNKNOWN and never scored as zero."
        ),
    )
    parser.add_argument(
        "--recommendations",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures",
            "synthetic-recommendations.json",
        ),
        help="JSON recommendation set (default: the checked-in synthetic set)",
    )
    parser.add_argument(
        "--scenarios",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures",
            "weight-scenarios.json",
        ),
        help="JSON named weight scenarios (default: the checked-in set)",
    )
    parser.add_argument(
        "--weights",
        default="baseline",
        help="scenario name to rank with, or inline 'quality=.3,security=.5,delivery=.2'",
    )
    parser.add_argument(
        "--sweep-dimension",
        default="security",
        choices=list(DIMENSIONS),
        help="dimension to walk 0.0->1.0 for the crossover sweep",
    )
    parser.add_argument("--sweep-steps", type=int, default=100)
    parser.add_argument(
        "--include-sweep-points",
        action="store_true",
        help=(
            "keep every sampled point of the crossover sweep in the JSON. Off by "
            "default: the points are intermediate scaffolding and the crossovers "
            "derived from them are the result. Turn it on to plot the sweep."
        ),
    )
    parser.add_argument("--json-out", help="write the full result as JSON")
    parser.add_argument("--csv-out", help="write the ranked table as CSV")
    parser.add_argument("--markdown-out", help="write the readable worksheet")
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="rank under one weighting only, skipping the scenario sweep",
    )
    return parser


def _parse_inline_weights(text: str) -> Optional[Dict[str, float]]:
    if "=" not in text:
        return None
    values: Dict[str, float] = {}
    for chunk in text.split(","):
        if not chunk.strip():
            continue
        if "=" not in chunk:
            raise PrioritizationError(
                f"inline weights: '{chunk}' is not 'dimension=number'"
            )
        key, _, value = chunk.partition("=")
        key = key.strip()
        try:
            values[key] = float(value)
        except ValueError:
            raise PrioritizationError(
                f"inline weights: '{value.strip()}' is not a number"
            ) from None
    return values


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        recs = load_recommendations(read_json(args.recommendations))
        scenarios = load_scenarios(read_json(args.scenarios))
        inline = _parse_inline_weights(args.weights)
        if inline is not None:
            active = Weights(inline, name="inline")
        else:
            match = [s for s in scenarios if s.name == args.weights]
            if not match:
                raise PrioritizationError(
                    f"no scenario named '{args.weights}'; available: "
                    f"{[s.name for s in scenarios]}"
                )
            active = match[0]

        result = rank(recs, active)
        sensitivity = (
            None if args.no_sensitivity else sweep_scenarios(recs, scenarios)
        )
        crossover = (
            None
            if args.no_sensitivity
            else find_crossovers(
                recs, args.sweep_dimension, steps=args.sweep_steps, base=active
            )
        )
    except PrioritizationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    source_label = os.path.basename(args.recommendations)
    markdown = render_markdown(result, sensitivity, crossover, source_label)

    if args.json_out:
        emitted_crossover = crossover
        if crossover is not None and not args.include_sweep_points:
            emitted_crossover = dict(crossover)
            emitted_crossover["points"] = None
            emitted_crossover["points_omitted"] = (
                f"{len(crossover['points'])} sampled points omitted; rerun with "
                f"--include-sweep-points to keep them. The crossovers below are "
                f"derived from them."
            )
        bundle = {
            "generated_by": "prioritize.py",
            "content_class": "SYNTHETIC_DRAFT_NOT_A_UNIVERSITY_FINDING",
            "source_recommendations": source_label,
            "active_ranking": result,
            "sensitivity": sensitivity,
            "crossover_sweep": emitted_crossover,
        }
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle, indent=2, sort_keys=True)
            handle.write("\n")
    if args.csv_out:
        write_csv(result, args.csv_out)
    if args.markdown_out:
        with open(args.markdown_out, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    if not (args.json_out or args.csv_out or args.markdown_out):
        print(markdown)

    counts = result["counts"]
    print(
        f"[prioritize] weighting '{active.name}': {counts['ranked']} ranked, "
        f"{counts['needs_estimate']} held for missing estimates "
        f"({counts['decision_blocking_unknowns']} decision-blocking) out of "
        f"{counts['total']}.",
        file=sys.stderr,
    )
    if sensitivity:
        print(
            f"[prioritize] sensitivity: top item stable = "
            f"{sensitivity['top_item_stable']}; crossover sweep on "
            f"'{args.sweep_dimension}' found "
            f"{len(crossover['crossovers']) if crossover else 0} reorder(s).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
