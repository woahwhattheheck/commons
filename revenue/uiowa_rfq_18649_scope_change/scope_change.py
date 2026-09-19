#!/usr/bin/env python3
"""Scope-change impact calculator (University of Iowa RFQ 18649, work order 133).

Extends the baseline cost and staffing model in
``../uiowa_rfq_18649_workshare/COMMERCIAL.md`` and ``ACCEPTANCE_EXHIBIT.md`` with
separately priced changes, and computes incremental effort, dependencies,
schedule effect and a proposed fee from assumptions that are printed next to the
answer rather than buried in a rate card.

The distinctions this file exists to keep
-----------------------------------------
1.  **A defect cure is not added work.** Section 7 of the acceptance exhibit is
    explicit: "A small correction to a TJLabs-authored artifact that fails an
    agreed acceptance criterion is not treated as a new scope item merely because
    it occurs during acceptance review." So a request grounded in a failed
    acceptance criterion is dispositioned `NO_CHARGE_CURE`: **fee zero, hours
    still reported.** Reporting zero hours would hide work that really costs
    time; charging for it would bill the buyer for our own nonconformance. Both
    are refused.

2.  **Some requests cannot be quoted at any price.** The RFQ's controlling scope
    boundary (specific product/vendor recommendations; legal, audit,
    certification, insurance or regulatory opinions) is not a change-control
    item. The exhibit: "It cannot be added merely because the prime asks for it;
    only a formal controlling-solicitation amendment could reopen that question."
    Those are `NOT_QUOTABLE` and never receive a fee, however much effort they
    would take.

3.  **A missing estimate is not zero.** An unestimated work item makes its
    request `NEEDS_INPUT`, with the gap named. It is never quoted at zero hours
    or zero dollars.

4.  **The baseline does not move.** Changes are separate line items. The $24,000
    base and its 40/40/20 milestone split are reported unchanged by every
    scenario; a test asserts it.

5.  **Everything here is a proposed estimate.** No output of this file is an
    offer, an authorization, a commitment, an invoice or recognized revenue.

Money is handled in **integer cents** throughout. Floating-point dollars in a
quotation worksheet are a defect, not a rounding preference.

Offline, Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------

#: A real change: work outside the bounded package, separately authorized.
CHANGE_QUOTE = "CHANGE_QUOTE"

#: Correcting a genuine nonconformance in a TJLabs-authored deliverable.
#: Costs hours. Costs the buyer nothing.
NO_CHARGE_CURE = "NO_CHARGE_CURE"

#: Outside the controlling solicitation's scope boundary. No price exists.
NOT_QUOTABLE = "NOT_QUOTABLE"

#: Cannot be estimated yet, because a required input is missing.
NEEDS_INPUT = "NEEDS_INPUT"

DISPOSITIONS = (CHANGE_QUOTE, NO_CHARGE_CURE, NOT_QUOTABLE, NEEDS_INPUT)

#: The grounds a request can be raised on. The disposition follows from this,
#: not from how the request is worded or who is asking.
BASIS_ADDED_SCOPE = "added_scope"
BASIS_DELIVERABLE_DEFECT = "deliverable_defect"
BASIS_EXCLUDED_BY_SOLICITATION = "excluded_by_solicitation"
BASES = (
    BASIS_ADDED_SCOPE,
    BASIS_DELIVERABLE_DEFECT,
    BASIS_EXCLUDED_BY_SOLICITATION,
)

UNKNOWN_TOKENS = frozenset({"unknown", "", "n/a", "na", "tbd", "none", "null", "?"})

STATUS_BANNER = "PROPOSED_ESTIMATE_NOT_A_COMMITMENT"


class ScopeChangeError(ValueError):
    """Input that cannot be interpreted without guessing. Names the request."""


class _Unknown:
    """Sentinel for 'not estimated'. Has no arithmetic, so it cannot become 0."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "UNKNOWN"

    def __bool__(self) -> bool:
        raise ScopeChangeError(
            "UNKNOWN has no truth value; test with `is UNKNOWN` instead"
        )


UNKNOWN = _Unknown()


# --------------------------------------------------------------------------------
# Money: integer cents, never floats
# --------------------------------------------------------------------------------


def dollars_to_cents(value: Any, *, field: str) -> int:
    """Parse a dollar amount into integer cents without going through float.

    A quotation that drifts by a cent because of binary floating point is a
    defect in a commercial document, so the string is split on the decimal point
    and handled as integers.
    """
    if isinstance(value, bool):
        raise ScopeChangeError(f"{field}: boolean is not a money amount")
    if isinstance(value, int):
        return value * 100
    if isinstance(value, float):
        raise ScopeChangeError(
            f"{field}: {value!r} was supplied as a float. Money must be an int "
            f"(whole dollars) or a decimal string such as \"187.50\", so the "
            f"amount cannot drift in binary floating point."
        )
    if not isinstance(value, str):
        raise ScopeChangeError(f"{field}: unusable money type {type(value).__name__}")
    text = value.strip().replace("$", "").replace(",", "")
    if not text:
        raise ScopeChangeError(f"{field}: empty money amount")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if text.count(".") > 1 or not text.replace(".", "").isdigit():
        raise ScopeChangeError(f"{field}: {value!r} is not a money amount")
    if "." in text:
        whole, frac = text.split(".")
        if len(frac) > 2:
            raise ScopeChangeError(
                f"{field}: {value!r} has sub-cent precision; quote to the cent"
            )
        frac = (frac + "00")[:2]
    else:
        whole, frac = text, "00"
    cents = int(whole or "0") * 100 + int(frac)
    return -cents if negative else cents


def cents_to_dollars(cents: Optional[int]) -> str:
    """Render cents as a plain dollar string. UNKNOWN never becomes $0.00."""
    if cents is None:
        return "UNKNOWN"
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"


def parse_hours(raw: Any, *, request_id: str, field: str):
    """Hours as a number, or UNKNOWN. Never a substituted value."""
    if isinstance(raw, dict):
        if "hours" not in raw:
            return UNKNOWN
        raw = raw["hours"]
    if raw is None:
        return UNKNOWN
    if isinstance(raw, str):
        token = raw.strip().lower()
        if token in UNKNOWN_TOKENS:
            return UNKNOWN
        try:
            raw = float(token)
        except ValueError:
            raise ScopeChangeError(
                f"{request_id}: {field} is {raw!r}, neither a number of hours nor "
                f"a recognized unknown marker"
            ) from None
    if isinstance(raw, bool):
        raise ScopeChangeError(f"{request_id}: {field} is a boolean, not hours")
    if not isinstance(raw, (int, float)):
        raise ScopeChangeError(
            f"{request_id}: {field} has unusable type {type(raw).__name__}"
        )
    if raw < 0:
        raise ScopeChangeError(f"{request_id}: {field} is negative ({raw})")
    return float(raw)


# --------------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------------


class Baseline:
    """The engagement as already proposed, plus the modelling assumptions.

    The commercial figures are quoted from the repository's existing
    ``COMMERCIAL.md`` / ``ACCEPTANCE_EXHIBIT.md``. The effort figures are
    **assumptions** this calculator needs in order to convert hours into money,
    and each one is labelled and sourced so it can be replaced with a real number
    in one edit.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ScopeChangeError("baseline must be an object")

        commercial = payload.get("commercial", {})
        self.base_fee_cents = dollars_to_cents(
            commercial.get("base_workshare_fee", 0), field="base_workshare_fee"
        )
        self.optional_readout_cents = dollars_to_cents(
            commercial.get("optional_readout_fee", 0), field="optional_readout_fee"
        )
        self.currency = str(commercial.get("currency", "USD"))
        self.travel_treatment = str(commercial.get("travel_treatment", ""))
        self.source = str(commercial.get("source", ""))

        self.milestones: List[Dict[str, Any]] = []
        for entry in commercial.get("milestones", []):
            amount = dollars_to_cents(
                entry["amount"], field=f"milestone {entry.get('name')}"
            )
            self.milestones.append(
                {
                    "name": entry["name"],
                    "share": entry["share"],
                    "amount_cents": amount,
                    "trigger": entry.get("trigger", ""),
                }
            )
        total = sum(m["amount_cents"] for m in self.milestones)
        if self.milestones and total != self.base_fee_cents:
            raise ScopeChangeError(
                f"milestone amounts total {cents_to_dollars(total)} but the base "
                f"workshare fee is {cents_to_dollars(self.base_fee_cents)}; the "
                f"baseline must reconcile before anything is quoted against it"
            )

        self.roles: Dict[str, Dict[str, Any]] = {}
        for name, entry in payload.get("roles", {}).items():
            self.roles[name] = {
                "name": name,
                "rate_cents_per_hour": dollars_to_cents(
                    entry["loaded_rate_per_hour"], field=f"role {name} rate"
                ),
                "basis": entry.get("basis", ""),
                "status": entry.get("status", "ASSUMED"),
            }
        if not self.roles:
            raise ScopeChangeError("baseline needs at least one role with a rate")

        effort = payload.get("effort_model", {})
        self.base_package_hours = effort.get("base_package_hours")
        self.coordination_overhead_pct = float(
            effort.get("coordination_overhead_pct", 0)
        )
        if self.coordination_overhead_pct < 0:
            raise ScopeChangeError("coordination overhead cannot be negative")

        schedule = payload.get("schedule", {})
        self.baseline_weeks = schedule.get("baseline_duration_weeks", "")
        self.schedule_basis = schedule.get("basis", "")

        self.assumptions: List[Dict[str, Any]] = list(payload.get("assumptions", []))
        self.scope_boundary: List[str] = list(payload.get("excluded_by_solicitation", []))

    # -- derived -----------------------------------------------------------------

    def implied_blended_rate_cents(self) -> Optional[int]:
        """What the base fee implies per hour, if base hours were assumed.

        Reported so a reader can sanity-check the role rates against the fixed
        base fee instead of taking the rate card on faith.
        """
        if not self.base_package_hours:
            return None
        return round(self.base_fee_cents / float(self.base_package_hours))

    def role(self, name: str, *, request_id: str) -> Dict[str, Any]:
        if name not in self.roles:
            raise ScopeChangeError(
                f"{request_id}: unknown role {name!r}; baseline defines "
                f"{sorted(self.roles)}"
            )
        return self.roles[name]

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "currency": self.currency,
            "base_workshare_fee": cents_to_dollars(self.base_fee_cents),
            "base_workshare_fee_cents": self.base_fee_cents,
            "optional_readout_fee": cents_to_dollars(self.optional_readout_cents),
            "travel_treatment": self.travel_treatment,
            "milestones": [
                {
                    "name": m["name"],
                    "share": m["share"],
                    "amount": cents_to_dollars(m["amount_cents"]),
                    "trigger": m["trigger"],
                }
                for m in self.milestones
            ],
            "roles": {
                name: {
                    "loaded_rate_per_hour": cents_to_dollars(
                        r["rate_cents_per_hour"]
                    ),
                    "status": r["status"],
                    "basis": r["basis"],
                }
                for name, r in sorted(self.roles.items())
            },
            "effort_model": {
                "base_package_hours": self.base_package_hours,
                "base_package_hours_status": "ASSUMED",
                "implied_blended_rate_per_hour": cents_to_dollars(
                    self.implied_blended_rate_cents()
                ),
                "coordination_overhead_pct": self.coordination_overhead_pct,
            },
            "schedule": {
                "baseline_duration_weeks": self.baseline_weeks,
                "basis": self.schedule_basis,
            },
            "assumptions": self.assumptions,
            "excluded_by_solicitation": self.scope_boundary,
        }


# --------------------------------------------------------------------------------
# Change requests
# --------------------------------------------------------------------------------


class ChangeRequest:
    """One request from the prime, with its grounds and its work breakdown."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ScopeChangeError("change requests must be objects")
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            raise ScopeChangeError("every change request needs a 'request_id'")
        self.request_id = request_id.strip()
        self.title = str(payload.get("title", "")).strip()
        self.requested_by = str(payload.get("requested_by", "")).strip()
        self.summary = str(payload.get("summary", "")).strip()

        basis = payload.get("basis")
        if basis not in BASES:
            raise ScopeChangeError(
                f"{self.request_id}: 'basis' must be one of {list(BASES)}, got "
                f"{basis!r}. The disposition follows from the grounds, so the "
                f"grounds cannot be left to inference."
            )
        self.basis = basis

        #: Cited when basis is deliverable_defect: which agreed acceptance
        #: criterion the delivered artifact failed. Without one, a defect claim
        #: is unsubstantiated and is not silently converted into either a free
        #: cure or a billable change.
        self.failed_criterion = str(payload.get("failed_criterion", "")).strip()

        #: Cited when basis is excluded_by_solicitation.
        self.exclusion_reference = str(payload.get("exclusion_reference", "")).strip()

        self.work_items: List[Dict[str, Any]] = []
        for index, item in enumerate(payload.get("work_items", [])):
            if not isinstance(item, dict):
                raise ScopeChangeError(
                    f"{self.request_id}: work_items[{index}] must be an object"
                )
            self.work_items.append(
                {
                    "task": str(item.get("task", "")).strip(),
                    "role": str(item.get("role", "")).strip(),
                    "hours": parse_hours(
                        item.get("hours"),
                        request_id=self.request_id,
                        field=f"work_items[{index}].hours",
                    ),
                    "hours_basis": str(item.get("hours_basis", "")).strip(),
                }
            )

        self.dependencies: List[str] = [
            str(d) for d in payload.get("dependencies", [])
        ]
        schedule = payload.get("schedule_effect", {})
        self.calendar_days_added = schedule.get("calendar_days_added")
        self.on_critical_path = bool(schedule.get("on_critical_path", False))
        self.schedule_note = str(schedule.get("note", "")).strip()

        #: Costs that exist but that this carrier cannot commit (travel is the
        #: standing example). Reported, never folded into the fee.
        self.non_committable: List[Dict[str, Any]] = list(
            payload.get("non_committable_costs", [])
        )

        #: A pre-existing separately-authorized price, where the exhibit already
        #: names one (the $4,000 optional readout). Where a published price
        #: exists it GOVERNS, and the computed labour becomes a cross-check --
        #: deriving a second, different number for the same thing is how a
        #: proposal ends up contradicting itself across documents.
        self.published_price_ref = str(payload.get("published_price_ref", "")).strip()
        raw_published = payload.get("published_price")
        self.published_price_cents = (
            None
            if raw_published is None
            else dollars_to_cents(
                raw_published, field=f"{self.request_id}.published_price"
            )
        )
        self.notes = str(payload.get("notes", "")).strip()


# --------------------------------------------------------------------------------
# Quoting
# --------------------------------------------------------------------------------


def _price_work_items(
    request: ChangeRequest, baseline: Baseline
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Cost each work item. Returns (lines, unestimated task names).

    An unestimated item produces a line with UNKNOWN hours and UNKNOWN cost. It
    is never priced at zero, and its presence is what makes the request
    NEEDS_INPUT.
    """
    lines: List[Dict[str, Any]] = []
    unestimated: List[str] = []
    for item in request.work_items:
        role = baseline.role(item["role"], request_id=request.request_id)
        hours = item["hours"]
        if hours is UNKNOWN:
            unestimated.append(item["task"] or item["role"])
            lines.append(
                {
                    "task": item["task"],
                    "role": item["role"],
                    "hours": None,
                    "rate_per_hour": cents_to_dollars(role["rate_cents_per_hour"]),
                    "cost_cents": None,
                    "cost": "UNKNOWN",
                    "hours_basis": item["hours_basis"],
                    "arithmetic": (
                        "not computed: hours not estimated. Not priced at zero."
                    ),
                }
            )
            continue
        cost_cents = round(hours * role["rate_cents_per_hour"])
        lines.append(
            {
                "task": item["task"],
                "role": item["role"],
                "hours": hours,
                "rate_per_hour": cents_to_dollars(role["rate_cents_per_hour"]),
                "cost_cents": cost_cents,
                "cost": cents_to_dollars(cost_cents),
                "hours_basis": item["hours_basis"],
                "arithmetic": (
                    f"{hours:g} h x "
                    f"{cents_to_dollars(role['rate_cents_per_hour'])}/h = "
                    f"{cents_to_dollars(cost_cents)}"
                ),
            }
        )
    return lines, unestimated


def quote(request: ChangeRequest, baseline: Baseline) -> Dict[str, Any]:
    """Disposition and price one request.

    The order of the checks is the policy. Exclusion is tested before effort,
    because an excluded request has no price no matter how small the effort.
    Defect grounds are tested before effort is converted to money, because the
    conversion is exactly what must not happen for a cure.
    """
    lines, unestimated = _price_work_items(request, baseline)
    known_hours = sum(
        line["hours"] for line in lines if line["hours"] is not None
    )
    record: Dict[str, Any] = {
        "request_id": request.request_id,
        "title": request.title,
        "requested_by": request.requested_by,
        "summary": request.summary,
        "basis": request.basis,
        "work_items": lines,
        "hours_estimated": round(known_hours, 4),
        "hours_unestimated_tasks": unestimated,
        "dependencies": list(request.dependencies),
        "schedule_effect": {
            "calendar_days_added": request.calendar_days_added,
            "on_critical_path": request.on_critical_path,
            "note": request.schedule_note,
            "basis": (
                "relative to kickoff; the prime owns the integrated schedule and "
                "any University-facing dates"
            ),
        },
        "non_committable_costs": [
            {
                "item": entry.get("item", ""),
                "reason": entry.get("reason", ""),
                "excluded_from_fee": True,
            }
            for entry in request.non_committable
        ],
        "notes": request.notes,
        "status": STATUS_BANNER,
    }

    # 1. Outside the controlling solicitation's boundary -> no price exists.
    if request.basis == BASIS_EXCLUDED_BY_SOLICITATION:
        record["disposition"] = NOT_QUOTABLE
        record["fee_cents"] = None
        record["fee"] = "NOT QUOTED"
        record["fee_basis"] = (
            "No fee is calculated. This request is outside the controlling "
            "solicitation's scope boundary, which is not a change-control item. "
            "It cannot be added because the prime asks for it; only a formal "
            "controlling-solicitation amendment could reopen the question. "
            f"Effort of roughly {round(known_hours, 2)} h is shown so the "
            "request is not dismissed as trivial, but it is not for sale at any "
            "price."
        )
        record["exclusion_reference"] = request.exclusion_reference
        record["reconciles"] = True
        return record

    # 2. Correcting our own nonconformance -> real hours, zero fee.
    if request.basis == BASIS_DELIVERABLE_DEFECT:
        if not request.failed_criterion:
            record["disposition"] = NEEDS_INPUT
            record["fee_cents"] = None
            record["fee"] = "UNKNOWN"
            record["fee_basis"] = (
                "A defect claim needs the agreed acceptance criterion the "
                "delivered artifact failed. Without it this is neither a "
                "substantiated cure nor an agreed change, and it is not resolved "
                "by guessing in either direction."
            )
            record["missing_inputs"] = ["failed_criterion"]
            record["reconciles"] = True
            return record
        record["disposition"] = NO_CHARGE_CURE
        record["fee_cents"] = 0
        record["fee"] = cents_to_dollars(0)
        record["failed_criterion"] = request.failed_criterion
        record["fee_basis"] = (
            f"No charge. This corrects a TJLabs-authored artifact that failed the "
            f"agreed acceptance criterion \"{request.failed_criterion}\". Per the "
            f"acceptance exhibit, a correction of genuine nonconformance is not a "
            f"new scope item merely because it occurs during acceptance review. "
            f"The {round(known_hours, 2)} h below is real work at TJLabs' cost; it "
            f"is reported rather than zeroed so the effort stays visible, and it "
            f"is not billed."
        )
        record["internal_cost_cents"] = sum(
            line["cost_cents"] for line in lines if line["cost_cents"] is not None
        )
        record["internal_cost"] = cents_to_dollars(record["internal_cost_cents"])
        record["internal_cost_note"] = (
            "TJLabs' own cost of the cure, shown for internal effort tracking. "
            "It is not a charge, not an invoice line, and not part of any total "
            "presented to the buyer."
        )
        record["reconciles"] = True
        # A cure must never contribute to a buyer-facing total.
        if unestimated:
            record["hours_unestimated_tasks"] = unestimated
            record["cure_effort_partially_unknown"] = True
        return record

    # 3. Added scope with no work breakdown at all. An empty breakdown is not a
    # free change -- it is a change nobody has estimated yet. Quoting $0.00 here
    # would be the same "absence becomes zero" error this file exists to prevent,
    # just moved up a level from the line item to the request.
    if not request.work_items:
        record["disposition"] = NEEDS_INPUT
        record["fee_cents"] = None
        record["fee"] = "UNKNOWN"
        record["fee_basis"] = (
            "Not quoted: this request has no work breakdown. No breakdown means "
            "the change has not been estimated, which is not the same as a change "
            "that costs nothing."
        )
        record["missing_inputs"] = ["work_items"]
        record["reconciles"] = True
        return record

    # 4. Added scope, but a line needed to price it is missing.
    if unestimated:
        record["disposition"] = NEEDS_INPUT
        record["fee_cents"] = None
        record["fee"] = "UNKNOWN"
        record["fee_basis"] = (
            "Not quoted: "
            + ", ".join(unestimated)
            + " has no hours estimate. An unestimated task is an open question, "
            "not zero effort, and quoting around it would understate the change."
        )
        record["missing_inputs"] = [f"work_items hours: {t}" for t in unestimated]
        record["reconciles"] = True
        return record

    # 5. A real, priceable change.
    subtotal_cents = sum(
        line["cost_cents"] for line in lines if line["cost_cents"] is not None
    )
    overhead_cents = round(
        subtotal_cents * baseline.coordination_overhead_pct / 100.0
    )
    fee_cents = subtotal_cents + overhead_cents
    record["disposition"] = CHANGE_QUOTE
    record["labour_subtotal_cents"] = subtotal_cents
    record["labour_subtotal"] = cents_to_dollars(subtotal_cents)
    record["coordination_overhead_pct"] = baseline.coordination_overhead_pct
    record["coordination_overhead_cents"] = overhead_cents
    record["coordination_overhead"] = cents_to_dollars(overhead_cents)
    record["computed_fee_cents"] = fee_cents
    record["computed_fee"] = cents_to_dollars(fee_cents)

    if request.published_price_cents is not None:
        # An already-published price governs. The computed labour stays visible
        # as a cross-check, and any gap is stated rather than quietly resolved in
        # whichever direction flatters the total.
        delta = fee_cents - request.published_price_cents
        record["fee_cents"] = request.published_price_cents
        record["fee"] = cents_to_dollars(request.published_price_cents)
        record["price_source"] = "PUBLISHED"
        record["published_price_ref"] = request.published_price_ref
        record["computed_vs_published_delta_cents"] = delta
        record["computed_vs_published_delta"] = cents_to_dollars(delta)
        record["fee_basis"] = (
            f"{cents_to_dollars(request.published_price_cents)} — the price "
            f"already published for this item ({request.published_price_ref}). "
            f"That figure governs. Bottom-up from {round(known_hours, 2)} h at "
            f"the baseline role rates the same work computes to "
            f"{cents_to_dollars(fee_cents)}, a difference of "
            f"{cents_to_dollars(delta)}; the published price is not re-derived, "
            f"because a second number for the same item is how a proposal starts "
            f"contradicting itself across documents. The gap is shown so the "
            f"published figure can be revisited deliberately if it is wrong."
        )
        record["reconciles"] = True
        record["reconciliation"] = (
            f"published {cents_to_dollars(request.published_price_cents)} "
            f"governs; computed line items "
            f"{cents_to_dollars(subtotal_cents)} + overhead "
            f"{cents_to_dollars(overhead_cents)} = {cents_to_dollars(fee_cents)} "
            f"(cross-check only)"
        )
        return record

    record["fee_cents"] = fee_cents
    record["fee"] = cents_to_dollars(fee_cents)
    record["price_source"] = "COMPUTED"
    record["fee_basis"] = (
        f"{round(known_hours, 2)} h of added work priced at the baseline role "
        f"rates, plus {baseline.coordination_overhead_pct:g}% coordination "
        f"overhead. Proposed estimate against the assumptions printed with this "
        f"worksheet; not an offer and not an authorization."
    )

    # Reconciliation: the parts must equal the whole, to the cent.
    recomputed = (
        sum(line["cost_cents"] for line in lines if line["cost_cents"] is not None)
        + overhead_cents
    )
    record["reconciles"] = recomputed == fee_cents
    record["reconciliation"] = (
        f"line items {cents_to_dollars(subtotal_cents)} + overhead "
        f"{cents_to_dollars(overhead_cents)} = {cents_to_dollars(fee_cents)}"
    )
    return record


# --------------------------------------------------------------------------------
# Portfolio
# --------------------------------------------------------------------------------


def evaluate(
    requests: Sequence[ChangeRequest], baseline: Baseline
) -> Dict[str, Any]:
    """Quote every request and reconcile the whole worksheet."""
    quotes = [quote(r, baseline) for r in requests]

    quoted = [q for q in quotes if q["disposition"] == CHANGE_QUOTE]
    cures = [q for q in quotes if q["disposition"] == NO_CHARGE_CURE]
    refused = [q for q in quotes if q["disposition"] == NOT_QUOTABLE]
    blocked = [q for q in quotes if q["disposition"] == NEEDS_INPUT]

    change_total_cents = sum(q["fee_cents"] for q in quoted)

    # The baseline is restated, not recomputed: no scenario may move it.
    totals = {
        "baseline_base_fee": cents_to_dollars(baseline.base_fee_cents),
        "baseline_base_fee_cents": baseline.base_fee_cents,
        "baseline_unchanged": True,
        "quoted_changes": cents_to_dollars(change_total_cents),
        "quoted_changes_cents": change_total_cents,
        "combined_if_all_authorized": cents_to_dollars(
            baseline.base_fee_cents + change_total_cents
        ),
        "combined_note": (
            "Arithmetic only. Authorizing every change at once is not proposed, "
            "and this figure is not an offer."
        ),
        "no_charge_cure_count": len(cures),
        "no_charge_cure_fee": cents_to_dollars(0),
        "no_charge_cure_hours": round(
            sum(q["hours_estimated"] for q in cures), 2
        ),
        "not_quotable_count": len(refused),
        "needs_input_count": len(blocked),
    }

    hours = {
        "quoted_change_hours": round(
            sum(q["hours_estimated"] for q in quoted), 2
        ),
        "no_charge_cure_hours": totals["no_charge_cure_hours"],
        "unestimated_tasks": sorted(
            t for q in quotes for t in q["hours_unestimated_tasks"]
        ),
    }

    # Every dispositioned request lands in exactly one bucket.
    bucket_total = len(quoted) + len(cures) + len(refused) + len(blocked)

    return {
        "status": STATUS_BANNER,
        "content_class": "SYNTHETIC_DRAFT_NOT_A_COMMITMENT",
        "baseline": baseline.to_public_dict(),
        "quotes": quotes,
        "totals": totals,
        "hours": hours,
        "integrity": {
            "requests_in": len(requests),
            "requests_dispositioned": bucket_total,
            "all_requests_dispositioned": bucket_total == len(requests),
            "all_quotes_reconcile": all(q["reconciles"] for q in quotes),
            "cures_are_all_zero_fee": all(q["fee_cents"] == 0 for q in cures),
            "refusals_carry_no_fee": all(
                q["fee_cents"] is None for q in refused
            ),
            "blocked_carry_no_fee": all(q["fee_cents"] is None for q in blocked),
        },
    }


# --------------------------------------------------------------------------------
# Assumption sensitivity
# --------------------------------------------------------------------------------


def sweep_assumption(
    requests: Sequence[ChangeRequest],
    baseline_payload: Dict[str, Any],
    *,
    role: str,
    multipliers: Sequence[float],
) -> Dict[str, Any]:
    """Re-quote with one role's rate scaled, to show what the assumption is worth.

    A quotation worksheet whose numbers move when an assumption moves is honest
    about being an estimate. One whose numbers look fixed is pretending.
    """
    rows: List[Dict[str, Any]] = []
    for multiplier in multipliers:
        payload = json.loads(json.dumps(baseline_payload))  # deep copy
        if role not in payload.get("roles", {}):
            raise ScopeChangeError(f"no role {role!r} in the baseline")
        original = dollars_to_cents(
            payload["roles"][role]["loaded_rate_per_hour"], field="rate"
        )
        scaled = round(original * multiplier)
        payload["roles"][role]["loaded_rate_per_hour"] = (
            f"{scaled // 100}.{scaled % 100:02d}"
        )
        result = evaluate(requests, Baseline(payload))
        rows.append(
            {
                "multiplier": multiplier,
                "rate_per_hour": cents_to_dollars(scaled),
                "quoted_changes": result["totals"]["quoted_changes"],
                "quoted_changes_cents": result["totals"]["quoted_changes_cents"],
                "no_charge_cure_fee": result["totals"]["no_charge_cure_fee"],
                "not_quotable_count": result["totals"]["not_quotable_count"],
            }
        )
    cure_fees = {row["no_charge_cure_fee"] for row in rows}
    return {
        "role": role,
        "rows": rows,
        "changes_move": len({r["quoted_changes_cents"] for r in rows}) > 1,
        "cures_stay_zero": cure_fees == {cents_to_dollars(0)},
        "interpretation": (
            "The quoted change total moves with the rate assumption, as an "
            "estimate should. The no-charge cure total does not move, because it "
            "is zero by policy rather than by arithmetic -- there is no rate at "
            "which correcting our own nonconformance becomes billable."
        ),
    }


# --------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------


def load_requests(payload: Any) -> List[ChangeRequest]:
    if isinstance(payload, dict):
        payload = payload.get("change_requests", payload.get("requests"))
    if not isinstance(payload, list):
        raise ScopeChangeError(
            "expected a list of change requests, or an object with a "
            "'change_requests' list"
        )
    requests = [ChangeRequest(entry) for entry in payload]
    seen: Dict[str, int] = {}
    for request in requests:
        seen[request.request_id] = seen.get(request.request_id, 0) + 1
    duplicates = sorted(k for k, v in seen.items() if v > 1)
    if duplicates:
        raise ScopeChangeError(f"duplicate request_id(s): {duplicates}")
    return requests


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as exc:
            raise ScopeChangeError(f"{path}: not valid JSON ({exc})") from exc


# --------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------

CSV_COLUMNS = [
    "request_id",
    "title",
    "basis",
    "disposition",
    "hours_estimated",
    "fee",
    "fee_is_zero_by_policy",
    "calendar_days_added",
    "on_critical_path",
    "dependencies",
    "missing_inputs",
    "non_committable_costs",
    "fee_basis",
]


def to_csv_rows(result: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = [list(CSV_COLUMNS)]
    for q in result["quotes"]:
        rows.append(
            [
                q["request_id"],
                q["title"],
                q["basis"],
                q["disposition"],
                # Hours are real even when the fee is zero or absent. A blank
                # here would erase the effort a cure actually costs.
                str(q["hours_estimated"]),
                q["fee"],
                "YES" if q["disposition"] == NO_CHARGE_CURE else "NO",
                (
                    "UNKNOWN"
                    if q["schedule_effect"]["calendar_days_added"] is None
                    else str(q["schedule_effect"]["calendar_days_added"])
                ),
                "YES" if q["schedule_effect"]["on_critical_path"] else "NO",
                "|".join(q["dependencies"]) or "NONE",
                "|".join(q.get("missing_inputs", [])) or "",
                "|".join(c["item"] for c in q["non_committable_costs"]) or "",
                q["fee_basis"],
            ]
        )
    return rows


def write_csv(result: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(to_csv_rows(result))


DISPOSITION_HEADINGS = {
    CHANGE_QUOTE: "Separately priced changes",
    NO_CHARGE_CURE: "No-charge corrections (not added work)",
    NOT_QUOTABLE: "Not quotable at any price",
    NEEDS_INPUT: "Cannot be quoted yet",
}


def render_markdown(
    result: Dict[str, Any], sensitivity: Optional[Dict[str, Any]] = None
) -> str:
    baseline = result["baseline"]
    out: List[str] = []
    out.append("# Scope-change impact worksheet")
    out.append("")
    out.append(
        "**PROPOSED ESTIMATES, NOT COMMITMENTS.** Nothing in this worksheet is an "
        "offer, an authorization, a contract, an invoice or recognized revenue. "
        "The change requests below are SYNTHETIC illustrations written to "
        "exercise the calculator; they are not requests anyone has made."
    )
    out.append("")

    out.append("## Baseline this is measured against")
    out.append("")
    out.append(f"Source: `{baseline['source']}`")
    out.append("")
    out.append(
        f"- Base workshare: **{baseline['base_workshare_fee']}** fixed "
        f"({baseline['currency']})"
    )
    out.append(
        f"- Optional final-readout support: {baseline['optional_readout_fee']}, "
        f"only when separately authorized"
    )
    out.append(f"- Travel: {baseline['travel_treatment']}")
    out.append(
        f"- Duration: {baseline['schedule']['baseline_duration_weeks']} "
        f"({baseline['schedule']['basis']})"
    )
    out.append("")
    out.append("| milestone | share | amount | trigger |")
    out.append("|---|---:|---:|---|")
    for m in baseline["milestones"]:
        out.append(f"| {m['name']} | {m['share']} | {m['amount']} | {m['trigger']} |")
    out.append("")
    out.append(
        "**The baseline does not move.** Every change below is a separate line "
        "item. No scenario re-bills the base workshare or alters the milestone "
        "split."
    )
    out.append("")

    out.append("## The assumptions doing the work")
    out.append("")
    out.append(
        "These convert hours into money. They are assumptions, not quoted terms, "
        "and the whole worksheet moves when they change."
    )
    out.append("")
    out.append("| role | loaded rate / h | status | basis |")
    out.append("|---|---:|---|---|")
    for name, role in baseline["roles"].items():
        out.append(
            f"| {name} | {role['loaded_rate_per_hour']} | {role['status']} | "
            f"{role['basis']} |"
        )
    out.append("")
    effort = baseline["effort_model"]
    out.append(
        f"- Base package modelled at **{effort['base_package_hours']} h** "
        f"({effort['base_package_hours_status']}), which implies a blended "
        f"**{effort['implied_blended_rate_per_hour']}/h** against the fixed "
        f"{baseline['base_workshare_fee']} base. The role rates above should "
        f"stay consistent with that; if they drift, one of the two is wrong."
    )
    out.append(
        f"- Coordination overhead on changes: "
        f"**{effort['coordination_overhead_pct']:g}%**"
    )
    out.append("")
    for assumption in baseline["assumptions"]:
        out.append(f"- {assumption}")
    out.append("")

    for disposition in (CHANGE_QUOTE, NO_CHARGE_CURE, NOT_QUOTABLE, NEEDS_INPUT):
        group = [q for q in result["quotes"] if q["disposition"] == disposition]
        if not group:
            continue
        out.append(f"## {DISPOSITION_HEADINGS[disposition]}")
        out.append("")
        for q in group:
            out.append(f"### `{q['request_id']}` — {q['title']}")
            out.append("")
            out.append(f"*Requested by:* {q['requested_by']}")
            out.append("")
            out.append(q["summary"])
            out.append("")
            if q["work_items"]:
                out.append("| task | role | hours | rate | cost |")
                out.append("|---|---|---:|---:|---:|")
                for line in q["work_items"]:
                    out.append(
                        "| {task} | {role} | {hours} | {rate} | {cost} |".format(
                            task=line["task"],
                            role=line["role"],
                            hours=(
                                "UNKNOWN"
                                if line["hours"] is None
                                else f"{line['hours']:g}"
                            ),
                            rate=line["rate_per_hour"],
                            cost=line["cost"],
                        )
                    )
                out.append("")
            out.append(f"- **Hours:** {q['hours_estimated']:g}")
            if disposition == CHANGE_QUOTE:
                out.append(
                    f"- **Reconciliation:** {q['reconciliation']}"
                )
                out.append(f"- **Proposed fee:** **{q['fee']}**")
            elif disposition == NO_CHARGE_CURE:
                out.append(f"- **Charge to the buyer: {q['fee']}**")
                out.append(
                    f"- TJLabs' own cost of the cure: {q['internal_cost']} "
                    f"({q['internal_cost_note']})"
                )
            else:
                out.append(f"- **Fee:** {q['fee']}")
            out.append(f"- **Why:** {q['fee_basis']}")
            if q["dependencies"]:
                out.append(
                    "- **Depends on:** " + "; ".join(q["dependencies"])
                )
            schedule = q["schedule_effect"]
            days = schedule["calendar_days_added"]
            out.append(
                "- **Schedule:** "
                + (
                    "not estimated (UNKNOWN)"
                    if days is None
                    else f"+{days} calendar days"
                )
                + (
                    ", on the critical path"
                    if schedule["on_critical_path"]
                    else ", runs in parallel with baseline work"
                )
                + (f". {schedule['note']}" if schedule["note"] else "")
            )
            for cost in q["non_committable_costs"]:
                out.append(
                    f"- **Excluded from the fee:** {cost['item']} — "
                    f"{cost['reason']}"
                )
            if q.get("missing_inputs"):
                out.append(
                    "- **Missing before this can be quoted:** "
                    + ", ".join(f"`{m}`" for m in q["missing_inputs"])
                )
            out.append("")

    totals = result["totals"]
    out.append("## Reconciliation")
    out.append("")
    out.append("| | |")
    out.append("|---|---:|")
    out.append(f"| Baseline workshare (unchanged) | {totals['baseline_base_fee']} |")
    out.append(f"| Separately priced changes | {totals['quoted_changes']} |")
    out.append(
        f"| No-charge corrections ({totals['no_charge_cure_count']}, "
        f"{totals['no_charge_cure_hours']:g} h) | {totals['no_charge_cure_fee']} |"
    )
    out.append(f"| Not quotable | {totals['not_quotable_count']} request(s) |")
    out.append(f"| Cannot be quoted yet | {totals['needs_input_count']} request(s) |")
    out.append(
        f"| **If every quoted change were authorized** | "
        f"**{totals['combined_if_all_authorized']}** |"
    )
    out.append("")
    out.append(totals["combined_note"])
    out.append("")
    out.append(
        f"Hours: {result['hours']['quoted_change_hours']:g} h of quoted change "
        f"work, plus {result['hours']['no_charge_cure_hours']:g} h of corrections "
        f"that are **not** billed. The correction hours are shown because they "
        f"are real effort; they are worth "
        f"{totals['no_charge_cure_fee']} to the buyer."
    )
    out.append("")

    if sensitivity:
        out.append("## What the rate assumption is worth")
        out.append("")
        out.append(
            f"Scaling the `{sensitivity['role']}` loaded rate and re-quoting "
            f"everything:"
        )
        out.append("")
        out.append("| rate multiplier | rate / h | quoted changes | no-charge cures |")
        out.append("|---:|---:|---:|---:|")
        for row in sensitivity["rows"]:
            out.append(
                f"| x{row['multiplier']:g} | {row['rate_per_hour']} | "
                f"{row['quoted_changes']} | {row['no_charge_cure_fee']} |"
            )
        out.append("")
        out.append(sensitivity["interpretation"])
        out.append("")

    integrity = result["integrity"]
    out.append("## Self-checks")
    out.append("")
    for key, value in sorted(integrity.items()):
        out.append(f"- `{key}`: {value}")
    out.append("")
    out.append("---")
    out.append("")
    out.append(
        "Produced offline by `scope_change.py` (Python standard library only). "
        "Amounts are computed in integer cents. Every figure is a proposed "
        "estimate against the stated assumptions; none is an offer, an "
        "authorization, a commitment, an invoice or recognized revenue."
    )
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        prog="scope_change.py",
        description=(
            "Price scope changes against the proposed baseline, keeping a "
            "no-charge defect correction distinguishable from added work."
        ),
    )
    parser.add_argument(
        "--baseline", default=os.path.join(here, "fixtures", "baseline.json")
    )
    parser.add_argument(
        "--requests",
        default=os.path.join(here, "fixtures", "change_requests.json"),
    )
    parser.add_argument("--json-out")
    parser.add_argument("--csv-out")
    parser.add_argument("--markdown-out")
    parser.add_argument(
        "--sweep-role",
        default="assessment_engineer",
        help="role whose loaded rate is scaled for the assumption sweep",
    )
    parser.add_argument("--no-sensitivity", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        baseline_payload = read_json(args.baseline)
        baseline = Baseline(baseline_payload)
        requests = load_requests(read_json(args.requests))
        result = evaluate(requests, baseline)
        sensitivity = (
            None
            if args.no_sensitivity
            else sweep_assumption(
                requests,
                baseline_payload,
                role=args.sweep_role,
                multipliers=(0.8, 1.0, 1.25),
            )
        )
    except ScopeChangeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(result, sensitivity)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(
                {"result": result, "assumption_sensitivity": sensitivity},
                handle,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
    if args.csv_out:
        write_csv(result, args.csv_out)
    if args.markdown_out:
        with open(args.markdown_out, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    if not (args.json_out or args.csv_out or args.markdown_out):
        print(markdown)

    totals = result["totals"]
    print(
        f"[scope] {totals['not_quotable_count']} not quotable, "
        f"{totals['no_charge_cure_count']} no-charge cure(s) at "
        f"{totals['no_charge_cure_fee']} covering "
        f"{totals['no_charge_cure_hours']:g} h, "
        f"{totals['needs_input_count']} awaiting input, "
        f"{totals['quoted_changes']} of quoted change against an unchanged "
        f"{totals['baseline_base_fee']} base.",
        file=sys.stderr,
    )
    if not result["integrity"]["all_quotes_reconcile"]:
        print("[scope] RECONCILIATION FAILURE", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
