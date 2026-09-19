#!/usr/bin/env python3
"""UIOWA-105C - ledger bridge between the resourcing ledgers and the
roadmap-feasibility / readout-deck shapes already on the branch.

Found by scanning every landed lane for numeric resourcing fields (52 lanes,
21 files). Three seams, all reproducible from files on the branch:

  1. THE ROADMAP LANE HAS NO RECURRING LEDGER.
     capacity_feasibility declares its capacity as "staff-hours available to
     this programme per phase window" and carries item effort as one-time
     staff-hours per role. There is no recurring field anywhere in that lane,
     yet its own effort_source names UIOWA-086 and UIOWA-072 as the upstreams --
     both of which emit a recurring ledger. Wire those in naively and an annual
     commitment lands inside a 90-day capacity window. This module supplies
     that input contract and REFUSES to write recurring load into a one-time
     field, rather than leaving the seam unguarded.

  2. TWO LANDED LANES STATE RECURRING LOAD IN INCOMPATIBLE UNITS.
     The readout deck uses "staff-hours per month"; this lane uses
     FTE-fraction per year. They reconcile only through an hours-per-FTE-year
     constant. Conversion here is explicit, declared, and REFUSED when the
     constant is not stated -- so two components can be shown to agree, or
     shown to differ, instead of being incomparable.

  3. THREE RECOMMENDATION-ID CONVENTIONS, IN TWO ISLANDS.
     REC-SYN-* (prioritization, and this lane's join); R-001 (readout deck and
     capacity feasibility); OPP-*/WI-* (opportunity portfolio, work items).
     This module REPORTS the split. It does not bridge it: asserting that
     R-001 is REC-SYN-IAM-DEP-001 would be manufacturing traceability, which
     is the one thing the crosswalk rule forbids.

This module does not modify, and does not need to modify, any other lane.
Python 3 standard library only. Deterministic.
"""

import json
import os

from ledgers import (
    ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH, RECURRING_CASH,
    RELEASED_CAPACITY, UNKNOWN, Amount, AdapterError, LedgerUnitError,
)

# Unit vocabularies observed in landed lanes, and what this lane calls them.
ROADMAP_EFFORT_UNIT = "staff-hours"                 # capacity_feasibility
DECK_RECURRING_UNIT = "staff-hours per month"       # readout_deck
DECK_ONE_TIME_UNIT = "staff-hours"                  # readout_deck

# Identifier conventions seen on the branch. Reported, never auto-joined.
ID_CONVENTIONS = {
    "REC-SYN-*": ["uiowa_rfq_18649_prioritization",
                  "uiowa_rfq_18649_economics_resource_adapters"],
    "R-NNN": ["uiowa_rfq_18649_readout_deck",
              "uiowa_rfq_18649_capacity_feasibility"],
    "OPP-* / WI-*": ["uiowa_rfq_18649_ai_opportunity_portfolio",
                     "uiowa_rfq_18649_economics_resource_adapters"],
}


class BridgeRefusal(LedgerUnitError):
    """Raised when a conversion would state a quantity as something it is not.

    A subclass of LedgerUnitError on purpose: refusing to put an annual load
    into a one-time field is the same rule as refusing to add across ledgers,
    applied at a component boundary instead of inside an expression.
    """


# --------------------------------------------------------------------------
# Recurring-unit conversion, only ever with a declared constant
# --------------------------------------------------------------------------
def fte_year_to_hours_month(amount, hours_per_fte_year):
    """FTE-fraction per year -> staff-hours per month, the readout deck's unit.

    `hours_per_fte_year` must be supplied by the caller. There is no default:
    a silent default is how two components end up 'agreeing' on a number
    neither of them chose.
    """
    _require_constant(hours_per_fte_year)
    _require_ledger(amount, RECURRING_EFFORT)
    factor = hours_per_fte_year / 12.0
    return {
        # 6 places, not 4: an FTE fraction is small enough that 4 loses the
        # round trip, and a figure that cannot survive being converted back is
        # not a figure two components can be checked against each other with.
        "low": round(amount.low * factor, 6),
        "likely": round(amount.likely * factor, 6),
        "high": round(amount.high * factor, 6),
        "unit": DECK_RECURRING_UNIT,
        "converted_from": RECURRING_EFFORT,
        "conversion": "x %g hours per FTE-year / 12 months" % hours_per_fte_year,
        "basis": amount.basis,
        "source_record_id": amount.source_record_id,
    }


def hours_month_to_fte_year(value_low, value_likely, value_high,
                            hours_per_fte_year, source_record_id="",
                            basis=""):
    """staff-hours per month -> FTE-fraction per year, this lane's unit.

    The inverse of the above, so a deck figure and a ledger figure can be put
    side by side and shown to agree or shown to differ.
    """
    _require_constant(hours_per_fte_year)
    factor = 12.0 / hours_per_fte_year
    return Amount(value_low * factor, value_likely * factor, value_high * factor,
                  RECURRING_EFFORT,
                  basis=(basis + " | " if basis else "")
                        + "converted from %s at %g hours per FTE-year"
                          % (DECK_RECURRING_UNIT, hours_per_fte_year),
                  source_component="uiowa-088-readout-deck",
                  source_record_id=source_record_id)


def _require_constant(hours_per_fte_year):
    if hours_per_fte_year is None:
        raise BridgeRefusal(
            "refusing to convert between %r and %r without a declared "
            "hours-per-FTE-year constant. Without it the two units are not "
            "comparable, and inventing one would make two components appear "
            "to agree on a number neither chose."
            % (RECURRING_EFFORT, DECK_RECURRING_UNIT))
    if not isinstance(hours_per_fte_year, (int, float)) or hours_per_fte_year <= 0:
        raise BridgeRefusal("hours-per-FTE-year must be a positive number, got %r"
                            % (hours_per_fte_year,))


def _require_ledger(amount, ledger):
    if not isinstance(amount, Amount):
        raise BridgeRefusal("expected an Amount, got %r" % type(amount).__name__)
    if amount.ledger != ledger:
        raise BridgeRefusal("expected an amount in %r, got %r" % (ledger, amount.ledger))


def recurring_figures_agree(ledger_amount, deck_hours_per_month,
                            hours_per_fte_year, tolerance=0.02):
    """Do a ledger figure and a deck figure describe the same load?

    Returns (verdict, detail). Verdict is AGREE, DIFFER, or UNKNOWN. This is
    the check that seam 2 currently has no way to perform.
    """
    if ledger_amount == UNKNOWN or deck_hours_per_month in (None, UNKNOWN):
        return UNKNOWN, ("one side is not assessed; agreement cannot be "
                         "established and is not assumed")
    converted = fte_year_to_hours_month(ledger_amount, hours_per_fte_year)
    got = converted["likely"]
    if abs(got - float(deck_hours_per_month)) <= max(tolerance * max(abs(got), 1e-9),
                                                     tolerance):
        return "AGREE", ("ledger %g FTE/yr = %g %s, deck states %g"
                         % (ledger_amount.likely, got, DECK_RECURRING_UNIT,
                            float(deck_hours_per_month)))
    return "DIFFER", ("ledger %g FTE/yr = %g %s, but the deck states %g. One of "
                      "them is wrong and the report and the deck will not agree."
                      % (ledger_amount.likely, got, DECK_RECURRING_UNIT,
                         float(deck_hours_per_month)))


# --------------------------------------------------------------------------
# Emitting the roadmap lane's declared input contract
# --------------------------------------------------------------------------
def to_roadmap_effort(amount, role_split=None):
    """One-time effort -> the roadmap lane's per-role `effort` object.

    Refuses anything that is not the one-time ledger. That refusal is the
    whole point: the roadmap lane has no recurring field, so a recurring load
    written here would be silently consumed as one-time capacity inside a
    phase window.
    """
    if amount == UNKNOWN:
        return UNKNOWN
    if not isinstance(amount, Amount):
        raise BridgeRefusal("expected an Amount, got %r" % type(amount).__name__)
    if amount.ledger != ONE_TIME_EFFORT:
        raise BridgeRefusal(
            "refusing to write %r into the roadmap lane's %r field. That lane "
            "carries no recurring ledger, so this value would be consumed as "
            "one-time capacity inside a phase window -- an annual commitment "
            "charged once. Report it separately instead."
            % (amount.ledger, ROADMAP_EFFORT_UNIT))
    if not role_split:
        return {"UNASSIGNED-ROLE": {"low": round(amount.low, 4),
                                    "likely": round(amount.likely, 4),
                                    "high": round(amount.high, 4)}}
    out = {}
    for role in sorted(role_split):
        share = role_split[role]
        out[role] = {"low": round(amount.low * share, 4),
                     "likely": round(amount.likely * share, 4),
                     "high": round(amount.high * share, 4)}
    return out


def roadmap_items_from_integration(result, phase_by_recommendation=None):
    """Build roadmap-lane items from a UIOWA-105 integration result.

    Only the one-time ledger crosses. Recurring load is returned in a SEPARATE
    structure that the roadmap lane has no field for, so it is visible to a
    human instead of being quietly folded into capacity.
    """
    items, recurring_sidecar, unestimated = [], [], []
    for entry in result["recommendations"]:
        rid = entry["recommendation_id"]
        one_time = entry["ledgers"][ONE_TIME_EFFORT]
        recurring = entry["ledgers"][RECURRING_EFFORT]
        if one_time["state"] == UNKNOWN:
            unestimated.append({
                "rec": rid,
                "reason": one_time.get("note") or "no one-time estimate supplied",
                "handling": "the roadmap must treat this as UNESTIMATED. It is "
                            "not zero capacity consumed, and it is not a free item.",
            })
        else:
            items.append({
                "id": "RM-FROM-%s" % rid,
                "rec": rid,
                "title": entry["title"],
                "proposed_phase": (phase_by_recommendation or {}).get(rid, UNKNOWN),
                "prerequisites": [],
                "owner_role": "UNASSIGNED-ROLE",
                "effort": {"UNASSIGNED-ROLE": {
                    "low": one_time["low"], "likely": one_time["likely"],
                    "high": one_time["high"]}},
                "effort_complete": one_time["complete"],
                "effort_note": one_time["note"],
            })
        if recurring["state"] != UNKNOWN:
            recurring_sidecar.append({
                "rec": rid,
                "recurring_effort_fte_per_year": {
                    "low": recurring["low"], "likely": recurring["likely"],
                    "high": recurring["high"]},
                "why_it_is_not_in_effort": (
                    "the roadmap lane carries no recurring ledger; placing this "
                    "in `effort` would charge an annual commitment once, inside "
                    "one phase window"),
            })
    return {
        "meta": {
            "emitted_by": "uiowa-105c-ledger-bridge",
            "effort_unit": ROADMAP_EFFORT_UNIT,
            "effort_ledger": ONE_TIME_EFFORT,
            "fiction_notice": "Derived from synthetic component output. Not a "
                              "University of Iowa finding or plan.",
            "no_individuals_notice": "Effort is stated per ROLE only. No named "
                                     "individual, no date, no personal "
                                     "availability commitment.",
            "recurring_ledger_warning": (
                "The receiving lane has no recurring field. Recurring load is "
                "returned in `recurring_not_representable`, NOT in `items[].effort`."),
        },
        "items": sorted(items, key=lambda i: i["id"]),
        "recurring_not_representable": sorted(recurring_sidecar,
                                              key=lambda r: r["rec"]),
        "unestimated": sorted(unestimated, key=lambda u: u["rec"]),
    }


# --------------------------------------------------------------------------
# Identifier islands: reported, never auto-joined
# --------------------------------------------------------------------------
def identifier_islands(observed):
    """Group observed recommendation ids by convention and report the split.

    `observed` maps a component name to the ids it uses. The return value names
    which components can currently be joined and which cannot. No mapping is
    invented: two conventions are reported as UNJOINED until somebody asserts
    the correspondence.
    """
    def convention(rid):
        if rid.startswith("REC-SYN-"):
            return "REC-SYN-*"
        if rid.startswith("OPP-") or rid.startswith("WI-"):
            return "OPP-* / WI-*"
        if len(rid) > 2 and rid[0] == "R" and rid[1] == "-":
            return "R-NNN"
        return "OTHER"

    islands = {}
    for component in sorted(observed):
        for rid in sorted(set(observed[component])):
            islands.setdefault(convention(rid), {"components": set(), "examples": set()})
            islands[convention(rid)]["components"].add(component)
            islands[convention(rid)]["examples"].add(rid)
    out = []
    for name in sorted(islands):
        out.append({
            "convention": name,
            "components": sorted(islands[name]["components"]),
            "examples": sorted(islands[name]["examples"])[:3],
        })
    joinable = len(out) <= 1
    return {
        "islands": out,
        "joinable": joinable,
        "verdict": ("all observed components share one identifier convention"
                    if joinable else
                    "%d identifier conventions observed; components in different "
                    "islands CANNOT be joined without a human-asserted "
                    "correspondence. This module reports the split rather than "
                    "inventing the mapping." % len(out)),
    }


def render(bridge, agreement=None, islands=None):
    L = ["# Ledger bridge report (UIOWA-105C)", "",
         "> Derived from synthetic component output. Not a University of Iowa "
         "finding or plan.", "",
         "## One-time effort crossing to the roadmap lane", ""]
    L.append("Unit: `%s`. Ledger: `%s`." % (ROADMAP_EFFORT_UNIT, ONE_TIME_EFFORT))
    L.append("")
    L.append("| Item | Recommendation | Effort (low-likely-high) | Complete |")
    L.append("|---|---|---|---|")
    for item in bridge["items"]:
        e = item["effort"]["UNASSIGNED-ROLE"]
        L.append("| `%s` | `%s` | %.2f - %.2f - %.2f | %s |"
                 % (item["id"], item["rec"], e["low"], e["likely"], e["high"],
                    "yes" if item["effort_complete"] else "FLOOR ONLY"))
    L.append("")
    L.append("## Recurring load the receiving lane cannot represent")
    L.append("")
    L.append(bridge["meta"]["recurring_ledger_warning"])
    L.append("")
    if bridge["recurring_not_representable"]:
        L.append("| Recommendation | Recurring (FTE/yr) |")
        L.append("|---|---|")
        for r in bridge["recurring_not_representable"]:
            a = r["recurring_effort_fte_per_year"]
            L.append("| `%s` | %.3f - %.3f - %.3f |"
                     % (r["rec"], a["low"], a["likely"], a["high"]))
    else:
        L.append("None assessed.")
    L.append("")
    if bridge["unestimated"]:
        L.append("## Unestimated — the roadmap must not treat these as free")
        L.append("")
        for u in bridge["unestimated"]:
            L.append("- `%s`: %s" % (u["rec"], u["handling"]))
        L.append("")
    if agreement:
        L.append("## Recurring-unit agreement check")
        L.append("")
        for row in agreement:
            L.append("- `%s`: **%s** — %s" % (row["id"], row["verdict"], row["detail"]))
        L.append("")
    if islands:
        L.append("## Identifier islands")
        L.append("")
        L.append(islands["verdict"])
        L.append("")
        L.append("| Convention | Components | Examples |")
        L.append("|---|---|---|")
        for row in islands["islands"]:
            L.append("| `%s` | %s | %s |"
                     % (row["convention"], ", ".join(row["components"]),
                        ", ".join("`%s`" % e for e in row["examples"])))
        L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# CLI: run the bridge against the components actually on the branch
# --------------------------------------------------------------------------
HOURS_PER_FTE_YEAR = 2080.0   # declared, editable, and printed in every output


def deck_recurring_in_fte_year(report_doc, hours_per_fte_year=HOURS_PER_FTE_YEAR):
    """Restate every readout-deck recurring figure in this lane's unit.

    Useful on its own: until this existed, a deck figure in staff-hours per
    month and a ledger figure in FTE-fraction per year could not be compared
    at all. UNKNOWN stays UNKNOWN -- it is not converted to zero.
    """
    rows = []
    for entry in report_doc.get("resource_implications", []):
        measure = (entry.get("measures") or {}).get("recurring_effort") or {}
        value = measure.get("value")
        if value in (None, UNKNOWN):
            rows.append({"id": entry.get("id"), "rec": entry.get("rec"),
                         "stated": UNKNOWN, "unit": measure.get("unit", UNKNOWN),
                         "fte_per_year": UNKNOWN,
                         "basis": measure.get("basis", "")})
            continue
        converted = hours_month_to_fte_year(value, value, value,
                                            hours_per_fte_year,
                                            source_record_id=entry.get("id", ""),
                                            basis=measure.get("basis", ""))
        rows.append({"id": entry.get("id"), "rec": entry.get("rec"),
                     "stated": value, "unit": measure.get("unit"),
                     "fte_per_year": round(converted.likely, 5),
                     "basis": measure.get("basis", "")})
    return sorted(rows, key=lambda r: str(r["id"]))


def main(argv=None):
    import argparse
    import integrate

    p = argparse.ArgumentParser(description="UIOWA-105C ledger bridge")
    here = os.path.dirname(os.path.abspath(__file__))
    deck = integrate.find_component("uiowa_rfq_18649_readout_deck")
    prio = integrate.find_component("uiowa_rfq_18649_prioritization")
    port = integrate.find_component("uiowa_rfq_18649_ai_opportunity_portfolio")
    p.add_argument("--deck-report", default=(
        os.path.join(deck, "data", "example-report.json") if deck else ""))
    p.add_argument("--hours-per-fte-year", type=float, default=HOURS_PER_FTE_YEAR)
    p.add_argument("--out", default=os.path.join(here, "sample_output"))
    args = p.parse_args(argv)

    result = integrate.build(
        os.path.join(prio, "fixtures", "synthetic-recommendations.json"),
        os.path.join(here, "fixtures", "resource_estimates.contract.json"),
        os.path.join(here, "fixtures", "economics.contract.json"),
        os.path.join(port, "sample_output", "portfolio.json") if port else "",
        os.path.join(here, "fixtures", "crosswalk.json"))

    bridge = roadmap_items_from_integration(result)

    observed = {
        "uiowa_rfq_18649_prioritization":
            [e["recommendation_id"] for e in result["recommendations"]],
        "uiowa_rfq_18649_economics_resource_adapters":
            [i["work_item_id"] for i in result["work_items"]],
    }
    deck_rows = []
    if args.deck_report and os.path.exists(args.deck_report):
        with open(args.deck_report, encoding="utf-8") as fh:
            deck_doc = json.load(fh)
        deck_rows = deck_recurring_in_fte_year(deck_doc, args.hours_per_fte_year)
        observed["uiowa_rfq_18649_readout_deck"] = [
            r["rec"] for r in deck_rows if r.get("rec")]

    islands = identifier_islands(observed)
    agreement = [{
        "id": row["id"],
        "verdict": UNKNOWN,
        "detail": ("deck states %s %s = %s FTE/yr, but no asserted "
                   "correspondence links `%s` to any recommendation in this "
                   "lane's register, so agreement cannot be established and is "
                   "not assumed"
                   % (row["stated"], row["unit"], row["fte_per_year"], row["rec"]))
        if row["stated"] != UNKNOWN else
        ("the deck records this as not assessed; it stays UNKNOWN and is not "
         "converted to zero"),
    } for row in deck_rows]

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "schema_version": "uiowa-105c-bridge/1",
        "hours_per_fte_year": args.hours_per_fte_year,
        "roadmap_input": bridge,
        "deck_recurring_restated": deck_rows,
        "identifier_islands": islands,
    }
    with open(os.path.join(args.out, "bridge.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(args.out, "bridge_report.md"), "w", encoding="utf-8") as fh:
        fh.write(render(bridge, agreement, islands))

    print("roadmap items emitted        : %d" % len(bridge["items"]))
    print("recurring NOT representable  : %d (returned separately, not in effort)"
          % len(bridge["recurring_not_representable"]))
    print("unestimated (never free)     : %s"
          % (", ".join(u["rec"] for u in bridge["unestimated"]) or "none"))
    print("deck recurring figures restated: %d" % len(deck_rows))
    for row in deck_rows:
        print("  %-8s %s %s -> %s FTE/yr"
              % (row["id"], row["stated"], row["unit"], row["fte_per_year"]))
    print("identifier islands           : %d" % len(islands["islands"]))
    print("  %s" % islands["verdict"])
    print("written to: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
