#!/usr/bin/env python3
"""UIOWA-105 component adapters.

Three adapters, each mapping one upstream component's output onto the shared
work-item shape the recommendation register can join against:

  adapt_resource_estimates  <- the resource-estimation kit  (UIOWA-086 contract)
  adapt_economics           <- the AI benefit / operating-cost model (UIOWA-078
                               contract)
  adapt_opportunity_portfolio <- the AI opportunity and value portfolio
                               (UIOWA-072, ALREADY ON main -- this one is proven
                               against a real landed file, not against a fixture
                               of my own invention)

Two notes on what these deliberately do NOT do.

FIRST, they do not compute economics or effort. They transport it. An adapter
that applied a labour rate, or that derived an effort figure the upstream kit
never stated, would be inventing the answer it was asked to carry. Ranges,
bases and source record ids survive the mapping intact.

SECOND, they do not invent the crosswalk between a component's own identifiers
and recommendation ids. The opportunity portfolio names candidates
(OPP-ESS-01); the register names recommendations (REC-SYN-ESS-DEP-001). Nothing
in either file states the correspondence, so it is supplied explicitly as a
human-asserted crosswalk and anything unmapped is REPORTED as unmapped rather
than dropped. Guessing the join is how two components silently disagree.
"""

from ledgers import (
    ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH, RECURRING_CASH,
    RELEASED_CAPACITY, UNKNOWN, Amount, AdapterError, read_amount,
)

RESOURCE_SCHEMA = "uiowa-086-resource-estimate/1"
ECONOMICS_SCHEMA = "uiowa-078-economics/1"
PORTFOLIO_SCHEMA = "uiowa-072-portfolio/1"


def _work_item(wid, label, rec_ids, component, record_id, amounts,
               roles=None, notes="", unmapped_reason=""):
    return {
        "work_item_id": wid,
        "label": label,
        "recommendation_ids": sorted(set(rec_ids)),
        "source_component": component,
        "source_record_id": record_id,
        "amounts": amounts,
        "specialist_roles": roles or [],
        "notes": notes,
        "unmapped_reason": unmapped_reason,
    }


def _require(doc, key, expected, what):
    got = doc.get(key)
    if got != expected:
        raise AdapterError("%s: %s is %r, expected %r" % (what, key, got, expected))


# --------------------------------------------------------------------------
# UIOWA-086 contract: resource and adoption estimates
# --------------------------------------------------------------------------
def adapt_resource_estimates(doc):
    """Resource-estimation kit -> work items.

    Contract (see CONTRACTS.md). Carries one-time implementation effort,
    recurring staff load, and the specialist roles the work needs. Cash is NOT
    read here even if present: cash belongs to the economics adapter, and two
    adapters both claiming the same money is one of the double counts this
    component exists to prevent.
    """
    _require(doc, "schema_version", RESOURCE_SCHEMA, "resource estimates")
    items = []
    seen = set()
    for raw in doc.get("work_items", []):
        wid = raw.get("work_item_id")
        if not wid:
            raise AdapterError("resource estimates: a work item has no work_item_id")
        if wid in seen:
            raise AdapterError("resource estimates: duplicate work_item_id %r" % wid)
        seen.add(wid)
        rec_ids = raw.get("recommendation_ids") or []
        amounts = {
            ONE_TIME_EFFORT: read_amount(
                raw.get("one_time_effort_hours"), ONE_TIME_EFFORT,
                "uiowa-086-resource-estimate", wid, "one_time_effort_hours"),
            RECURRING_EFFORT: read_amount(
                raw.get("recurring_effort_fte_per_year"), RECURRING_EFFORT,
                "uiowa-086-resource-estimate", wid, "recurring_effort_fte_per_year"),
        }
        roles = []
        for role in raw.get("specialist_roles", []):
            roles.append({
                "role": role.get("role", "UNSTATED"),
                "one_time_hours": read_amount(
                    role.get("one_time_hours"), ONE_TIME_EFFORT,
                    "uiowa-086-resource-estimate", wid,
                    "specialist_roles.one_time_hours"),
            })
        items.append(_work_item(
            wid, raw.get("label", ""), rec_ids, "uiowa-086-resource-estimate",
            wid, amounts, roles, raw.get("notes", ""),
            unmapped_reason="" if rec_ids else
            "the resource estimate names no recommendation_ids"))
    return items


# --------------------------------------------------------------------------
# UIOWA-078 contract: benefit and operating cost
# --------------------------------------------------------------------------
def adapt_economics(doc):
    """AI benefit / operating-cost model -> work items.

    Carries one-time cash, recurring cash and released staff capacity. Effort
    hours are NOT read here for the same reason cash is not read above.

    An economics entry may name a `work_item_id` that the resource kit also
    reported. That is not a conflict -- it is the join. The two adapters fill
    different ledgers of the SAME work item, and the integrator merges them
    rather than creating a second item and doubling the programme.
    """
    _require(doc, "schema_version", ECONOMICS_SCHEMA, "economics")
    currency = doc.get("currency")
    if not currency:
        raise AdapterError(
            "economics: no currency declared. A cash figure without its unit "
            "is not a fact that can be carried into a report table.")
    items = []
    seen = set()
    for raw in doc.get("entries", []):
        eid = raw.get("entry_id")
        if not eid:
            raise AdapterError("economics: an entry has no entry_id")
        if eid in seen:
            raise AdapterError("economics: duplicate entry_id %r" % eid)
        seen.add(eid)
        # An entry may attach to shared work; if it does not, it stands alone.
        wid = raw.get("work_item_id") or eid
        rec_ids = raw.get("recommendation_ids") or []
        amounts = {
            ONE_TIME_CASH: read_amount(raw.get("one_time_cash"), ONE_TIME_CASH,
                                       "uiowa-078-economics", eid, "one_time_cash"),
            RECURRING_CASH: read_amount(raw.get("recurring_cash_per_year"),
                                        RECURRING_CASH, "uiowa-078-economics",
                                        eid, "recurring_cash_per_year"),
            RELEASED_CAPACITY: read_amount(
                raw.get("released_capacity_hours_per_year"), RELEASED_CAPACITY,
                "uiowa-078-economics", eid, "released_capacity_hours_per_year"),
        }
        notes = raw.get("notes", "")
        assumptions = raw.get("assumptions") or []
        if assumptions:
            notes = (notes + " | " if notes else "") + "; ".join(assumptions)
        items.append(_work_item(
            wid, raw.get("label", ""), rec_ids, "uiowa-078-economics", eid,
            amounts, None, notes,
            unmapped_reason="" if rec_ids else
            "the economics entry names no recommendation_ids"))
    return items, currency


# --------------------------------------------------------------------------
# UIOWA-072: the opportunity portfolio, already on main
# --------------------------------------------------------------------------
def adapt_opportunity_portfolio(doc, crosswalk):
    """Opportunity portfolio -> work items, via an explicit crosswalk.

    `crosswalk` maps candidate id -> {"recommendation_ids": [...],
    "work_item_id": "...", "asserted_by": "..."}. It is supplied rather than
    inferred: nothing in either file states the correspondence, and a matcher
    that guessed it from title similarity would be manufacturing traceability.

    A candidate the crosswalk does not cover is emitted with an empty
    recommendation list and an `unmapped_reason`, so it appears in the report
    as unmapped instead of vanishing.

    A candidate the portfolio itself left UNKNOWN stays UNKNOWN through the
    mapping. It is not resolved here and it is not zeroed.
    """
    _require(doc, "schema_version", PORTFOLIO_SCHEMA, "opportunity portfolio")
    items = []
    for cand in sorted(doc.get("candidates", []), key=lambda c: c["id"]):
        cid = cand["id"]
        entry = crosswalk.get(cid, {})
        rec_ids = entry.get("recommendation_ids") or []
        wid = entry.get("work_item_id") or ("WI-FROM-%s" % cid)

        def pull(key, ledger, field):
            value = cand.get(key)
            if value == UNKNOWN or value is None:
                return UNKNOWN
            return Amount(value["low"], value["likely"], value["high"], ledger,
                          basis=("carried from the opportunity portfolio; "
                                 "decision class %s" % cand.get("decision_class")),
                          source_component="uiowa-072-portfolio",
                          source_record_id=cid)

        amounts = {
            ONE_TIME_EFFORT: pull("one_time_implementation", ONE_TIME_EFFORT,
                                  "one_time_implementation"),
            RECURRING_EFFORT: pull("recurring_maintenance", RECURRING_EFFORT,
                                   "recurring_maintenance"),
            RELEASED_CAPACITY: pull("benefit_hours_per_year", RELEASED_CAPACITY,
                                    "benefit_hours_per_year"),
        }
        notes = cand.get("decision_reason", "")
        for flag in cand.get("flags", []):
            notes += " | FLAG: " + flag
        reason = ""
        if not rec_ids:
            reason = ("no crosswalk entry: this candidate is not yet tied to a "
                      "recommendation, and the join is not guessed from the title")
        items.append(_work_item(
            wid, cand.get("title", ""), rec_ids, "uiowa-072-portfolio", cid,
            amounts, None, notes.strip(), unmapped_reason=reason))
    return items
