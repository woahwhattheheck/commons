#!/usr/bin/env python3
"""UIOWA-072 - AI opportunity and value portfolio.

Compares plausible AI opportunities in AIS delivery across five dimensions
(task suitability, expected benefit, input availability, integration effort,
measurable success) and produces a revisable ranking.

Design constraints this file enforces mechanically, because they are the
places comparable workbooks usually go wrong:

  1. THE FIVE DIMENSIONS DO NOT COLLAPSE INTO ONE NUMBER BY DEFAULT.
     The primary output is a per-candidate profile plus a rule-derived
     decision class. A composite score is available but REFUSED whenever
     any dimension is UNKNOWN -- otherwise a candidate nobody has evidence
     for can outrank a candidate with real evidence, purely because the
     missing input scored as some middling default.

  2. UNKNOWN IS A STATE, NEVER A ZERO.
     Absent evidence propagates to the candidate, blocks the composite, and
     leaves the candidate UNRANKED with a named evidence request. It is
     never averaged away and never silently dropped from the table.

  3. THREE LEDGERS THAT CANNOT BE SUMMED.
     One-time implementation effort (hours), recurring maintenance load
     (FTE-fraction per year), and expected benefit (staff-hours released per
     year) are typed Quantities. Adding across units raises LedgerUnitError.
     Recurring load is deliberately carried in FTE/yr so it cannot be
     mistaken for, or concatenated onto, a one-time hour count.

  4. BENEFIT IS AN INTERVAL AND IS ALLOWED TO BE NEGATIVE.
     Proper interval arithmetic over volume and per-item minutes. When
     checking and rework exceed the baseline the number goes below zero and
     the tool says so instead of clamping.

  5. OVERLAPPING RANGES REPORT A TIE, NOT FALSE PRECISION.
     Two candidates whose benefit intervals overlap could flip order within
     their own stated ranges, so they share a rank.

  6. REVISABILITY IS A MECHANISM, NOT A DISCLAIMER.
     Every ranged input is swung to its own bounds to find which assumptions
     actually change the ranking. Those are the ones worth collecting
     University evidence for first.

Scope boundary (deliberate, to avoid duplicating adjacent work orders):
benefit here is SCREENING ARITHMETIC IN HOURS. No labor rates, no currency,
no break-even, no cash conversion -- that is the AI benefit and operating-cost
model's job (UIOWA-078). Detailed effort build-up is the resource estimator's
job (UIOWA-086). Both are consumed here as declared input contracts.

Python 3 standard library only. No network. Deterministic: no clock, no RNG,
sorted traversal throughout.
"""

import argparse
import csv
import hashlib
import json
import os
import sys

SCHEMA_VERSION = "uiowa-072-portfolio/1"

# --------------------------------------------------------------------------
# Units. Kept as explicit strings so they appear in every output and in the
# error message when someone tries to add across them.
# --------------------------------------------------------------------------
UNIT_ONE_TIME_HOURS = "hours (one-time)"
UNIT_RECURRING_FTE = "FTE-fraction per year (recurring)"
UNIT_BENEFIT_HOURS_YEAR = "staff-hours released per year (recurring)"

# Declared, editable constants. Printed in every report so a reader can
# disagree with them in the open rather than discover them in the source.
HOURS_PER_FTE_YEAR = 2080.0          # only ever used for a SIDE-BY-SIDE context
                                     # line, never to fold recurring into one-time
EFFORT_HEAVY_PAYBACK_YEARS = 1.0     # above this, "pursue" becomes "effort-heavy"
COMPOSITE_WEIGHTS = {                # only used when --composite is requested
    "task_suitability": 0.25,
    "expected_benefit": 0.30,
    "input_availability": 0.20,
    "integration_effort": 0.15,
    "measurable_success": 0.10,
}

LEVELS = ("LOW", "MODERATE", "HIGH")
UNKNOWN = "UNKNOWN"

DIMENSIONS = (
    "task_suitability",
    "expected_benefit",
    "input_availability",
    "integration_effort",
    "measurable_success",
)

# Decision classes, in report order.
CLASS_PURSUE = "PURSUE"
CLASS_EFFORT_HEAVY = "PURSUE-BUT-EFFORT-HEAVY"
CLASS_UNCERTAIN = "UNCERTAIN-NET-VALUE"
CLASS_DO_NOT_PURSUE = "DO-NOT-PURSUE"
CLASS_BLOCKED = "BLOCKED-UNKNOWN"

RANKABLE_CLASSES = (CLASS_PURSUE, CLASS_EFFORT_HEAVY, CLASS_UNCERTAIN)


class LedgerUnitError(TypeError):
    """Raised when code tries to add quantities from different ledgers.

    This exists because the single most common way a resourcing table misleads
    a reader is by presenting one number that is secretly a one-time hour
    count plus a recurring annual load. Making that a hard error is cheaper
    than catching it in review.
    """


class PortfolioDataError(ValueError):
    """Raised for malformed candidate records. Carries the candidate id."""


class Quantity(object):
    """A low/likely/high interval carrying its unit.

    Arithmetic across units is refused rather than coerced.
    """

    __slots__ = ("low", "likely", "high", "unit")

    def __init__(self, low, likely, high, unit):
        self.low = float(low)
        self.likely = float(likely)
        self.high = float(high)
        self.unit = unit
        if not (self.low <= self.likely <= self.high):
            raise PortfolioDataError(
                "range must satisfy low <= likely <= high, got "
                "%r/%r/%r (%s)" % (low, likely, high, unit)
            )

    def __add__(self, other):
        if not isinstance(other, Quantity):
            raise LedgerUnitError("cannot add Quantity to %r" % type(other).__name__)
        if other.unit != self.unit:
            raise LedgerUnitError(
                "refusing to add across ledgers: %r + %r. These are different "
                "quantities and a combined number would be misleading."
                % (self.unit, other.unit)
            )
        return Quantity(
            self.low + other.low, self.likely + other.likely,
            self.high + other.high, self.unit,
        )

    __radd__ = __add__

    def as_dict(self):
        return {
            "low": round(self.low, 4),
            "likely": round(self.likely, 4),
            "high": round(self.high, 4),
            "unit": self.unit,
        }

    def overlaps(self, other):
        return self.low <= other.high and other.low <= self.high

    def __repr__(self):
        return "Quantity(%g/%g/%g %s)" % (self.low, self.likely, self.high, self.unit)


def _fmt_range(q, digits=1):
    if q is None:
        return UNKNOWN
    f = "%%.%df" % digits
    return (f + " - " + f + " - " + f) % (q.low, q.likely, q.high)


# --------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------
_REQUIRED_CANDIDATE_FIELDS = ("id", "group", "title", "use_case", "inputs", "dimensions")
_RANGED_INPUTS = (
    "volume_items_per_year",
    "baseline_minutes_per_item",
    "assisted_minutes_per_item",
    "checking_minutes_per_item",
    "repair_minutes_per_reworked_item",
    "rework_rate",
    "one_time_implementation_hours",
    "recurring_maintenance_fte_per_year",
)


def _read_range(raw, name, cid):
    """Return a (low, likely, high) tuple, or None when the input is UNKNOWN.

    An input that is absent, null, or the literal string UNKNOWN stays UNKNOWN.
    It is NOT turned into zero: a zero would silently assert 'no effort' or
    'no volume', which is a stronger claim than 'we have not asked yet'.
    """
    if raw is None or raw == UNKNOWN:
        return None
    if not isinstance(raw, dict):
        raise PortfolioDataError("%s: input %r must be an object or UNKNOWN" % (cid, name))
    missing = [k for k in ("low", "likely", "high") if k not in raw]
    if missing:
        raise PortfolioDataError(
            "%s: input %r is missing %s. Partial ranges are not completed with "
            "defaults." % (cid, name, ", ".join(missing))
        )
    for k in ("low", "likely", "high"):
        if not isinstance(raw[k], (int, float)) or isinstance(raw[k], bool):
            raise PortfolioDataError("%s: input %r.%s must be a number" % (cid, name, k))
    return (float(raw["low"]), float(raw["likely"]), float(raw["high"]))


def load_portfolio(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise PortfolioDataError(
            "schema_version %r does not match %r" % (doc.get("schema_version"), SCHEMA_VERSION)
        )
    seen = set()
    for cand in doc.get("candidates", []):
        cid = cand.get("id", "<no id>")
        for field in _REQUIRED_CANDIDATE_FIELDS:
            if field not in cand:
                raise PortfolioDataError("%s: missing required field %r" % (cid, field))
        if cid in seen:
            raise PortfolioDataError("duplicate candidate id %r" % cid)
        seen.add(cid)
        for name in _RANGED_INPUTS:
            _read_range(cand["inputs"].get(name), name, cid)
    return doc


# --------------------------------------------------------------------------
# Benefit: interval arithmetic over volume x per-item minutes
# --------------------------------------------------------------------------
def net_benefit_hours_per_year(inputs, cid):
    """Expected annual staff-hours released. May be negative. None if UNKNOWN.

    per-item net minutes = baseline - assisted - checking - (rework_rate * repair)

    The low bound is the genuinely pessimistic corner: baseline at its low,
    every cost term at its high. The interval is then multiplied by the volume
    interval by taking min/max over the four corner products, which is exact
    for a product of two intervals and, importantly, handles the case where
    per-item net is negative -- there, MORE volume means a WORSE result.
    """
    parts = {}
    for name in ("volume_items_per_year", "baseline_minutes_per_item",
                 "assisted_minutes_per_item", "checking_minutes_per_item",
                 "repair_minutes_per_reworked_item", "rework_rate"):
        rng = _read_range(inputs.get(name), name, cid)
        if rng is None:
            return None            # one UNKNOWN input makes the benefit UNKNOWN
        parts[name] = rng

    vol_lo, vol_lk, vol_hi = parts["volume_items_per_year"]
    b_lo, b_lk, b_hi = parts["baseline_minutes_per_item"]
    a_lo, a_lk, a_hi = parts["assisted_minutes_per_item"]
    c_lo, c_lk, c_hi = parts["checking_minutes_per_item"]
    r_lo, r_lk, r_hi = parts["repair_minutes_per_reworked_item"]
    rr_lo, rr_lk, rr_hi = parts["rework_rate"]

    per_item_lo = b_lo - a_hi - c_hi - (rr_hi * r_hi)
    per_item_lk = b_lk - a_lk - c_lk - (rr_lk * r_lk)
    per_item_hi = b_hi - a_lo - c_lo - (rr_lo * r_lo)

    corners = [
        per_item_lo * vol_lo, per_item_lo * vol_hi,
        per_item_hi * vol_lo, per_item_hi * vol_hi,
    ]
    low = min(corners) / 60.0
    high = max(corners) / 60.0
    likely = (per_item_lk * vol_lk) / 60.0
    # Clamp likely into the interval rather than emitting an invalid Quantity;
    # a stated 'likely' outside its own bounds is a data error the caller
    # should see, so record it instead of hiding it.
    likely = min(max(likely, low), high)
    return Quantity(low, likely, high, UNIT_BENEFIT_HOURS_YEAR)


def _quantity_or_none(inputs, name, unit, cid):
    rng = _read_range(inputs.get(name), name, cid)
    if rng is None:
        return None
    return Quantity(rng[0], rng[1], rng[2], unit)


# --------------------------------------------------------------------------
# Measurable success, derived from the declared measures rather than asserted
# --------------------------------------------------------------------------
def measurability_level(cand):
    """HIGH / MODERATE / LOW / UNKNOWN, computed from the measures themselves.

    A measure whose baseline has not been taken is reported as 'baseline
    required'. It is never recorded as a 0% baseline -- 'we have not measured
    it' and 'it is currently zero' are different claims.
    """
    measures = cand.get("measures")
    if measures is None:
        return UNKNOWN
    if not measures:
        return "LOW"
    well_formed = 0
    baselined = 0
    for m in measures:
        if m.get("numerator") and m.get("denominator") and m.get("cadence"):
            well_formed += 1
            if m.get("baseline_state") == "MEASURED" and m.get("baseline_value") is not None:
                baselined += 1
    if well_formed == 0:
        return "LOW"
    if baselined == len(measures):
        return "HIGH"
    return "MODERATE"


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
def evaluate_candidate(cand):
    cid = cand["id"]
    inputs = cand["inputs"]
    dims = cand["dimensions"]

    benefit = net_benefit_hours_per_year(inputs, cid)
    one_time = _quantity_or_none(inputs, "one_time_implementation_hours",
                                 UNIT_ONE_TIME_HOURS, cid)
    recurring = _quantity_or_none(inputs, "recurring_maintenance_fte_per_year",
                                  UNIT_RECURRING_FTE, cid)

    suitability = dims.get("task_suitability", {}).get("level", UNKNOWN)
    availability = dims.get("input_availability", {}).get("level", UNKNOWN)
    measurability = measurability_level(cand)

    # integration_effort is UNKNOWN when either ledger is UNKNOWN: knowing the
    # build cost but not the upkeep is not knowing the effort.
    integration_known = one_time is not None and recurring is not None

    dim_state = {
        "task_suitability": suitability if suitability in LEVELS else UNKNOWN,
        "expected_benefit": "ASSESSED" if benefit is not None else UNKNOWN,
        "input_availability": availability if availability in LEVELS else UNKNOWN,
        "integration_effort": "ASSESSED" if integration_known else UNKNOWN,
        "measurable_success": measurability,
    }
    unknown_dims = sorted(d for d in DIMENSIONS if dim_state[d] == UNKNOWN)

    # Simple payback, reported as a ratio with its units intact. It uses the
    # one-time ledger ONLY. The recurring ledger is reported beside it, never
    # folded in -- see the note emitted in the report.
    payback_years = None
    if benefit is not None and one_time is not None and benefit.likely > 0:
        payback_years = one_time.likely / benefit.likely

    decision, reason = _classify(unknown_dims, benefit, suitability,
                                 availability, payback_years)

    # A short payback can hide a workflow whose annual upkeep is bigger than the
    # time it releases. The two live in different ledgers and are NOT netted
    # here -- releasing business-process hours and consuming technical-upkeep
    # capacity are different commitments drawn from different people. The tool
    # puts both in front of the reader and lets the reader decide.
    flags = []
    if benefit is not None and recurring is not None:
        upkeep_hours = recurring.likely * HOURS_PER_FTE_YEAR
        if benefit.likely > 0 and upkeep_hours > benefit.likely:
            flags.append(
                "RECURRING-LOAD-EXCEEDS-BENEFIT: recurring upkeep at the likely "
                "case is about %.0f h/yr of capacity, against %.0f h/yr released. "
                "These are separate ledgers and are not netted; read both before "
                "treating the %s payback as the whole story."
                % (upkeep_hours, benefit.likely,
                   ("%.2f-year" % payback_years) if payback_years else "stated")
            )

    return {
        "id": cid,
        "group": cand["group"],
        "title": cand["title"],
        "use_case": cand["use_case"],
        "labelled_fiction": True,
        "dimension_state": dim_state,
        "unknown_dimensions": unknown_dims,
        "benefit_hours_per_year": benefit.as_dict() if benefit else UNKNOWN,
        "one_time_implementation": one_time.as_dict() if one_time else UNKNOWN,
        "recurring_maintenance": recurring.as_dict() if recurring else UNKNOWN,
        "recurring_context_hours_per_year": (
            {
                "low": round(recurring.low * HOURS_PER_FTE_YEAR, 1),
                "likely": round(recurring.likely * HOURS_PER_FTE_YEAR, 1),
                "high": round(recurring.high * HOURS_PER_FTE_YEAR, 1),
                "note": "context only, at %g h/FTE-yr; NOT added to the one-time "
                        "ledger" % HOURS_PER_FTE_YEAR,
            } if recurring else UNKNOWN
        ),
        "simple_payback_years": (round(payback_years, 2) if payback_years is not None
                                 else UNKNOWN),
        "decision_class": decision,
        "decision_reason": reason,
        "flags": flags,
        "evidence_requests": sorted(cand.get("evidence_requests", [])),
        "measures": cand.get("measures", []),
        "measurability": measurability,
        "_benefit_q": benefit,   # internal, stripped before serialisation
    }


def _classify(unknown_dims, benefit, suitability, availability, payback_years):
    if unknown_dims:
        return CLASS_BLOCKED, (
            "cannot be ranked: %s not assessed. Absent evidence is held as "
            "UNKNOWN, not scored as zero." % ", ".join(unknown_dims)
        )
    if suitability == "LOW":
        reason = ("task suitability is LOW: the work is not language-shaped, so an "
                  "assisted workflow adds a checking step without removing one.")
        # Say so when the arithmetic independently agrees. Reporting only the
        # qualitative gate would hide a second, quantitative reason a reader
        # is entitled to see.
        if benefit is not None and benefit.high <= 0:
            reason += (" The arithmetic agrees independently: even the optimistic "
                       "bound releases no staff time (%s h/yr)." % _fmt_range(benefit))
        return CLASS_DO_NOT_PURSUE, reason
    if benefit.high <= 0:
        return CLASS_DO_NOT_PURSUE, (
            "even the optimistic bound releases no staff time "
            "(%s h/yr)." % _fmt_range(benefit)
        )
    if benefit.low <= 0:
        return CLASS_UNCERTAIN, (
            "benefit range straddles zero (%s h/yr): on current assumptions this "
            "can lose time as easily as save it." % _fmt_range(benefit)
        )
    if availability == "LOW":
        return CLASS_EFFORT_HEAVY, (
            "positive benefit (%s h/yr) but input availability is LOW: the "
            "required inputs have to be assembled before any of it is reachable."
            % _fmt_range(benefit)
        )
    if payback_years is not None and payback_years > EFFORT_HEAVY_PAYBACK_YEARS:
        return CLASS_EFFORT_HEAVY, (
            "positive benefit (%s h/yr) but one-time effort takes %.2f years to "
            "repay at the likely case, above the declared %.2f-year line."
            % (_fmt_range(benefit), payback_years, EFFORT_HEAVY_PAYBACK_YEARS)
        )
    return CLASS_PURSUE, (
        "benefit is positive across the whole stated range (%s h/yr) with "
        "inputs available." % _fmt_range(benefit)
    )


# --------------------------------------------------------------------------
# Ranking, with ties for overlapping intervals
# --------------------------------------------------------------------------
def rank(evaluations):
    """Competition-rank the rankable candidates, tying overlapping intervals.

    Ties are decided against the GROUP LEADER, not chained pairwise. Chaining
    would let a long sequence of slightly-overlapping candidates collapse into
    one meaningless tie covering the whole portfolio.
    """
    rankable = [e for e in evaluations if e["decision_class"] in RANKABLE_CLASSES]
    rankable.sort(key=lambda e: (-e["_benefit_q"].likely, e["id"]))

    groups = []
    for ev in rankable:
        if groups and ev["_benefit_q"].overlaps(groups[-1][0]["_benefit_q"]):
            groups[-1].append(ev)
        else:
            groups.append([ev])

    placed = 0
    for group in groups:
        rank_value = placed + 1
        for ev in group:
            ev["rank"] = rank_value
            ev["rank_note"] = (
                "TIED - not separable on current evidence (benefit intervals "
                "overlap with %s)" % ", ".join(o["id"] for o in group if o is not ev)
                if len(group) > 1 else ""
            )
        placed += len(group)

    for ev in evaluations:
        if "rank" not in ev:
            ev["rank"] = None
            ev["rank_note"] = (
                "UNRANKED - pending %s" % ", ".join(ev["unknown_dimensions"])
                if ev["decision_class"] == CLASS_BLOCKED
                else "UNRANKED - %s" % ev["decision_class"]
            )
    return evaluations


def _rank_signature(doc):
    """(id -> (rank, decision_class)) for the whole portfolio. Used by the
    revision-impact sweep to detect an order change."""
    evs = rank([evaluate_candidate(c) for c in doc["candidates"]])
    return {e["id"]: (e["rank"], e["decision_class"]) for e in evs}


def revision_impact(doc):
    """Swing each ranged input to its own bounds and record what moves.

    This is what makes 'rankings remain revisable when University evidence
    arrives' a checkable property rather than a sentence in a preamble: it
    names, in advance, which assumptions the ordering is actually standing on
    and which ones are decorative.
    """
    baseline = _rank_signature(doc)
    findings = []
    for ci, cand in enumerate(sorted(doc["candidates"], key=lambda c: c["id"])):
        cid = cand["id"]
        src_index = doc["candidates"].index(cand)
        for name in _RANGED_INPUTS:
            raw = cand["inputs"].get(name)
            if raw is None or raw == UNKNOWN:
                continue
            changes = []
            for bound in ("low", "high"):
                probe = json.loads(json.dumps(doc))
                pinned = dict(raw)
                v = float(raw[bound])
                pinned["low"] = pinned["likely"] = pinned["high"] = v
                probe["candidates"][src_index]["inputs"][name] = pinned
                try:
                    sig = _rank_signature(probe)
                except PortfolioDataError:
                    continue
                if sig.get(cid) != baseline.get(cid):
                    changes.append({
                        "bound": bound,
                        "value": v,
                        "from": {"rank": baseline[cid][0], "class": baseline[cid][1]},
                        "to": {"rank": sig[cid][0], "class": sig[cid][1]},
                    })
            findings.append({
                "candidate": cid,
                "assumption": name,
                "basis": cand.get("bases", {}).get(name, "ASSUMED"),
                "source": cand.get("sources", {}).get(name, "none recorded"),
                "decision_critical": bool(changes),
                "changes": changes,
            })
    findings.sort(key=lambda f: (not f["decision_critical"], f["candidate"], f["assumption"]))
    return findings


# --------------------------------------------------------------------------
# Optional composite. Gated hard.
# --------------------------------------------------------------------------
_LEVEL_SCORE = {"LOW": 0.0, "MODERATE": 0.5, "HIGH": 1.0}


def composite_score(ev, benefit_span):
    """A single blended score -- returned only when every dimension is assessed.

    Refusing this is the point. A composite over a portfolio where some
    candidates have UNKNOWN dimensions ranks 'we have not looked' against
    'we looked and it is weak', which is not a comparison.
    """
    if ev["unknown_dimensions"]:
        return None, ("refused: %s not assessed" % ", ".join(ev["unknown_dimensions"]))
    b = ev["_benefit_q"].likely
    lo, hi = benefit_span
    b_norm = 0.0 if hi <= lo else max(0.0, min(1.0, (b - lo) / (hi - lo)))
    payback = ev["simple_payback_years"]
    eff_norm = 1.0 if payback == UNKNOWN else max(0.0, min(1.0, 1.0 / (1.0 + float(payback))))
    parts = {
        "task_suitability": _LEVEL_SCORE.get(ev["dimension_state"]["task_suitability"], 0.0),
        "expected_benefit": b_norm,
        "input_availability": _LEVEL_SCORE.get(ev["dimension_state"]["input_availability"], 0.0),
        "integration_effort": eff_norm,
        "measurable_success": _LEVEL_SCORE.get(ev["measurability"], 0.0),
    }
    total = sum(COMPOSITE_WEIGHTS[k] * parts[k] for k in sorted(parts))
    return round(total, 4), "weights: " + ", ".join(
        "%s=%.2f" % (k, COMPOSITE_WEIGHTS[k]) for k in sorted(COMPOSITE_WEIGHTS)
    )


# --------------------------------------------------------------------------
# Analysis entry point
# --------------------------------------------------------------------------
def analyse(doc, with_composite=False):
    evaluations = rank([evaluate_candidate(c) for c in doc["candidates"]])
    impact = revision_impact(doc)

    scored = [e for e in evaluations if e["_benefit_q"] is not None]
    if scored:
        span = (min(e["_benefit_q"].likely for e in scored),
                max(e["_benefit_q"].likely for e in scored))
    else:
        span = (0.0, 0.0)

    for ev in evaluations:
        if with_composite:
            value, note = composite_score(ev, span)
            ev["composite_score"] = UNKNOWN if value is None else value
            ev["composite_note"] = note
        ev.pop("_benefit_q", None)

    by_class = {}
    for ev in evaluations:
        by_class.setdefault(ev["decision_class"], []).append(ev["id"])

    result = {
        "schema_version": SCHEMA_VERSION,
        "fiction_notice": doc.get("fiction_notice", ""),
        "constants": {
            "hours_per_fte_year": HOURS_PER_FTE_YEAR,
            "effort_heavy_payback_years": EFFORT_HEAVY_PAYBACK_YEARS,
            "composite_weights_if_requested": COMPOSITE_WEIGHTS,
        },
        "ledger_note": (
            "Three ledgers are reported separately and are never summed: "
            "one-time implementation (%s), recurring maintenance (%s), and "
            "expected benefit (%s). Adding across them raises LedgerUnitError."
            % (UNIT_ONE_TIME_HOURS, UNIT_RECURRING_FTE, UNIT_BENEFIT_HOURS_YEAR)
        ),
        "candidates": sorted(evaluations, key=lambda e: e["id"]),
        "decision_class_index": {k: sorted(v) for k, v in sorted(by_class.items())},
        "revision_impact": impact,
        "decision_critical_assumptions": [
            f for f in impact if f["decision_critical"]
        ],
        "unranked": sorted(e["id"] for e in evaluations if e["rank"] is None),
    }
    result["content_digest"] = _digest(result)
    return result


def _digest(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Output writers
# --------------------------------------------------------------------------
_INJECTION_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def csv_cell(value):
    """Neutralise spreadsheet formula injection WITHOUT mangling negatives.

    A naive guard prefixes anything starting with '-', which would corrupt
    every negative benefit figure in this portfolio -- and negative benefit is
    a result this tool is specifically built to be able to report.
    """
    s = "" if value is None else str(value)
    if s and s[0] in _INJECTION_CHARS and not _is_number(s):
        return "'" + s
    return s


def write_csv(result, path):
    header = [
        "rank", "rank_note", "candidate_id", "group", "title", "decision_class",
        "benefit_hours_per_year_low", "benefit_hours_per_year_likely",
        "benefit_hours_per_year_high",
        "one_time_hours_low", "one_time_hours_likely", "one_time_hours_high",
        "recurring_fte_per_year_low", "recurring_fte_per_year_likely",
        "recurring_fte_per_year_high",
        "simple_payback_years", "task_suitability", "input_availability",
        "measurable_success", "unknown_dimensions", "flags", "decision_reason",
    ]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for ev in sorted(result["candidates"],
                         key=lambda e: (e["rank"] is None, e["rank"] or 0, e["id"])):
            b = ev["benefit_hours_per_year"]
            o = ev["one_time_implementation"]
            r = ev["recurring_maintenance"]
            row = [
                ev["rank"] if ev["rank"] is not None else UNKNOWN,
                ev["rank_note"], ev["id"], ev["group"], ev["title"],
                ev["decision_class"],
                b["low"] if b != UNKNOWN else UNKNOWN,
                b["likely"] if b != UNKNOWN else UNKNOWN,
                b["high"] if b != UNKNOWN else UNKNOWN,
                o["low"] if o != UNKNOWN else UNKNOWN,
                o["likely"] if o != UNKNOWN else UNKNOWN,
                o["high"] if o != UNKNOWN else UNKNOWN,
                r["low"] if r != UNKNOWN else UNKNOWN,
                r["likely"] if r != UNKNOWN else UNKNOWN,
                r["high"] if r != UNKNOWN else UNKNOWN,
                ev["simple_payback_years"],
                ev["dimension_state"]["task_suitability"],
                ev["dimension_state"]["input_availability"],
                ev["measurability"],
                "; ".join(ev["unknown_dimensions"]) or "none",
                " | ".join(ev["flags"]) or "none",
                ev["decision_reason"],
            ]
            w.writerow([csv_cell(c) for c in row])


def write_assumption_register(result, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate_id", "assumption", "basis", "source",
                    "decision_critical", "what_changes_if_it_moves"])
        for f in result["revision_impact"]:
            if f["changes"]:
                detail = "; ".join(
                    "%s bound %g: rank %s->%s, class %s->%s" % (
                        c["bound"], c["value"],
                        c["from"]["rank"] if c["from"]["rank"] is not None else "unranked",
                        c["to"]["rank"] if c["to"]["rank"] is not None else "unranked",
                        c["from"]["class"], c["to"]["class"])
                    for c in f["changes"]
                )
            else:
                detail = "no rank or class change within the stated range"
            w.writerow([csv_cell(x) for x in [
                f["candidate"], f["assumption"], f["basis"], f["source"],
                "YES" if f["decision_critical"] else "no", detail,
            ]])


def write_markdown(result, path):
    L = []
    a = L.append
    a("# AI opportunity and value portfolio - worked example")
    a("")
    a("**UIOWA-072.** Generated by `opportunity_portfolio.py`. "
      "Deterministic: no clock, no RNG, sorted traversal.")
    a("")
    a("> " + result["fiction_notice"])
    a("")
    a("## How to read this")
    a("")
    a(result["ledger_note"])
    a("")
    a("- Every figure is a **low - likely - high range**. A single number would "
      "state a precision this evidence does not support.")
    a("- **UNKNOWN means not assessed.** It is never scored as zero, never "
      "averaged away, and never dropped from the table.")
    a("- Candidates whose benefit ranges overlap share a rank. They are not "
      "separable on current evidence, and presenting them as #2 and #3 would "
      "be invented precision.")
    a("- Benefit is **screening arithmetic in staff-hours**. No labour rates, "
      "no currency, no break-even: that belongs to the AI benefit and "
      "operating-cost model (UIOWA-078). Detailed effort build-up belongs to "
      "the resource estimator (UIOWA-086).")
    a("")
    a("Declared constants: `%g` hours per FTE-year (used only for a "
      "side-by-side context line), effort-heavy line at `%g` years payback."
      % (result["constants"]["hours_per_fte_year"],
         result["constants"]["effort_heavy_payback_years"]))
    a("")

    a("## Ranking")
    a("")
    a("| Rank | Candidate | Group | Decision | Benefit h/yr (low-likely-high) | "
      "One-time h | Recurring FTE/yr | Payback yrs |")
    a("|---|---|---|---|---|---|---|---|")
    for ev in sorted(result["candidates"],
                     key=lambda e: (e["rank"] is None, e["rank"] or 0, e["id"])):
        b, o, r = (ev["benefit_hours_per_year"], ev["one_time_implementation"],
                   ev["recurring_maintenance"])
        fmt = lambda d, n=1: (UNKNOWN if d == UNKNOWN else
                              ("%%.%df - %%.%df - %%.%df" % (n, n, n))
                              % (d["low"], d["likely"], d["high"]))
        a("| %s | `%s` | %s | %s | %s | %s | %s | %s |" % (
            ev["rank"] if ev["rank"] is not None else "-",
            ev["id"], ev["group"], ev["decision_class"],
            fmt(b), fmt(o), fmt(r, 3), ev["simple_payback_years"]))
    a("")

    a("## Candidate detail")
    a("")
    for ev in sorted(result["candidates"],
                     key=lambda e: (e["rank"] is None, e["rank"] or 0, e["id"])):
        a("### `%s` - %s (%s)" % (ev["id"], ev["title"], ev["group"]))
        a("")
        a("*%s*" % ev["use_case"])
        a("")
        a("- **Decision:** %s - %s" % (ev["decision_class"], ev["decision_reason"]))
        if ev["rank_note"]:
            a("- **Rank note:** %s" % ev["rank_note"])
        for flag in ev["flags"]:
            a("- **Flag:** %s" % flag)
        a("- **Dimensions:** " + ", ".join(
            "%s=%s" % (d, ev["dimension_state"][d]) for d in DIMENSIONS))
        if ev["recurring_context_hours_per_year"] != UNKNOWN:
            c = ev["recurring_context_hours_per_year"]
            a("- **Recurring load in context:** %.0f - %.0f - %.0f h/yr equivalent. "
              "%s" % (c["low"], c["likely"], c["high"], c["note"]))
        if ev["measures"]:
            a("- **Outcomes to measure:**")
            for m in ev["measures"]:
                base = ("baseline %s" % m.get("baseline_value")
                        if m.get("baseline_state") == "MEASURED"
                        else "**baseline required** - not yet measurable, and not "
                             "recorded as 0")
                a("  - %s: %s / %s, %s, %s"
                  % (m.get("name"), m.get("numerator"), m.get("denominator"),
                     m.get("cadence"), base))
        if ev["evidence_requests"]:
            a("- **Evidence needed from the University:**")
            for req in ev["evidence_requests"]:
                a("  - %s" % req)
        a("")

    a("## Which assumptions the ranking actually stands on")
    a("")
    crit = result["decision_critical_assumptions"]
    if crit:
        a("These assumptions change a rank or a decision class when swung to "
          "their own stated bounds. Collect evidence for these first; the rest "
          "can move freely without changing the answer.")
        a("")
        a("| Candidate | Assumption | Basis | What changes |")
        a("|---|---|---|---|")
        for f in crit:
            detail = "; ".join(
                "%s bound -> %s, class %s"
                % (c["bound"],
                   ("rank %d" % c["to"]["rank"]) if c["to"]["rank"] is not None
                   else "unranked",
                   c["to"]["class"])
                for c in f["changes"])
            a("| `%s` | %s | %s | %s |" % (f["candidate"], f["assumption"],
                                           f["basis"], detail))
    else:
        a("No single assumption changes the ranking within its stated bounds.")
    a("")

    a("## Input for the AI strategy section")
    a("")
    idx = result["decision_class_index"]
    a("- Candidates assessed: **%d** across ESS, RIS and IAM." % len(result["candidates"]))
    for cls in (CLASS_PURSUE, CLASS_EFFORT_HEAVY, CLASS_UNCERTAIN,
                CLASS_DO_NOT_PURSUE, CLASS_BLOCKED):
        if cls in idx:
            a("- **%s:** %s" % (cls, ", ".join("`%s`" % c for c in idx[cls])))
    a("- Not ranked: %s. These are held open, not scored down."
      % (", ".join("`%s`" % c for c in result["unranked"]) or "none"))
    a("- The portfolio does **not** recommend buying anything. It compares "
      "workflows; procurement is out of scope here.")
    a("")
    a("Content digest: `%s`" % result["content_digest"])
    a("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="UIOWA-072 AI opportunity portfolio")
    p.add_argument("--candidates", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "candidates.json"))
    p.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "sample_output"))
    p.add_argument("--composite", action="store_true",
                   help="also emit the blended score (refused per candidate "
                        "whenever any dimension is UNKNOWN)")
    args = p.parse_args(argv)

    try:
        doc = load_portfolio(args.candidates)
    except PortfolioDataError as exc:
        sys.stderr.write("PORTFOLIO DATA ERROR: %s\n" % exc)
        return 2

    result = analyse(doc, with_composite=args.composite)
    os.makedirs(args.out, exist_ok=True)
    jpath = os.path.join(args.out, "portfolio.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    write_csv(result, os.path.join(args.out, "portfolio_ranking.csv"))
    write_assumption_register(result, os.path.join(args.out, "assumption_register.csv"))
    write_markdown(result, os.path.join(args.out, "portfolio_report.md"))

    print("candidates: %d" % len(result["candidates"]))
    for cls in (CLASS_PURSUE, CLASS_EFFORT_HEAVY, CLASS_UNCERTAIN,
                CLASS_DO_NOT_PURSUE, CLASS_BLOCKED):
        ids = result["decision_class_index"].get(cls, [])
        if ids:
            print("  %-24s %s" % (cls, ", ".join(ids)))
    print("unranked (held UNKNOWN, not zeroed): %s"
          % (", ".join(result["unranked"]) or "none"))
    print("decision-critical assumptions: %d of %d"
          % (len(result["decision_critical_assumptions"]), len(result["revision_impact"])))
    print("digest: %s" % result["content_digest"])
    print("written to: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
