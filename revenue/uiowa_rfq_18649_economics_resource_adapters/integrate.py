#!/usr/bin/env python3
"""UIOWA-105 - join economics and resource estimates to recommendations.

Merges adapted work items onto the recommendation register and produces two
views that deliberately do NOT agree:

  * the PER-RECOMMENDATION view answers "what does this one recommendation
    cost", and therefore shows shared work under every recommendation that
    needs it;
  * the PORTFOLIO ROLL-UP answers "what does the programme cost", and therefore
    counts each work item exactly once.

The difference between them is reported as an explicit line rather than
quietly reconciled, because a reader who adds up the per-recommendation column
and gets a bigger number than the roll-up is entitled to know why. That is the
"same work is not counted twice" requirement: not a deduplication that hides
the shared work, but an accounting that shows it in both places correctly.

Python 3 standard library only. No network. Deterministic.
"""

import argparse
import csv
import hashlib
import json
import os
import sys

from ledgers import (
    ALL_LEDGERS, ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH,
    RECURRING_CASH, RELEASED_CAPACITY, UNKNOWN, Amount, AdapterError,
    LedgerUnitError,
)
import adapters

SCHEMA_VERSION = "uiowa-105-integration/1"
HERE = os.path.dirname(os.path.abspath(__file__))


def find_component(name):
    """Locate a sibling component lane.

    After landing, this lane sits next to the others under revenue/, so the
    sibling path resolves with no configuration. UIOWA_REPO_ROOT is the hatch
    for running from a staging directory before that is true.
    """
    sibling = os.path.normpath(os.path.join(HERE, "..", name))
    if os.path.isdir(sibling):
        return sibling
    root = os.environ.get("UIOWA_REPO_ROOT")
    if root:
        candidate = os.path.join(root, name)
        if os.path.isdir(candidate):
            return candidate
    return None


# --------------------------------------------------------------------------
# Merging: two components may fill different ledgers of the same work item
# --------------------------------------------------------------------------
def merge_work_items(*item_lists):
    """Merge by work_item_id. Returns (items, conflicts).

    The resource kit supplies effort; the economics kit supplies cash and
    released capacity. When both name the same work_item_id they are describing
    ONE piece of work from two angles, so they merge -- creating a second item
    would double the programme.

    When both supply the SAME ledger for the same work item, that is a real
    disagreement between two components. It is reported, and the ledger is held
    at UNKNOWN. Silently preferring one source would make the conflict
    invisible, which is worse than the conflict.
    """
    merged = {}
    order = []
    conflicts = []
    for items in item_lists:
        for item in items:
            wid = item["work_item_id"]
            if wid not in merged:
                merged[wid] = {
                    "work_item_id": wid,
                    "label": item["label"],
                    "recommendation_ids": list(item["recommendation_ids"]),
                    "source_components": [item["source_component"]],
                    "source_record_ids": [item["source_record_id"]],
                    "amounts": dict(item["amounts"]),
                    "specialist_roles": list(item["specialist_roles"]),
                    "notes": item["notes"],
                    "unmapped_reason": item["unmapped_reason"],
                }
                order.append(wid)
                continue
            tgt = merged[wid]
            tgt["label"] = tgt["label"] or item["label"]
            tgt["recommendation_ids"] = sorted(
                set(tgt["recommendation_ids"]) | set(item["recommendation_ids"]))
            tgt["source_components"].append(item["source_component"])
            tgt["source_record_ids"].append(item["source_record_id"])
            tgt["specialist_roles"].extend(item["specialist_roles"])
            if item["notes"]:
                tgt["notes"] = (tgt["notes"] + " | " if tgt["notes"] else "") + item["notes"]
            for ledger, amount in item["amounts"].items():
                existing = tgt["amounts"].get(ledger, UNKNOWN)
                if amount == UNKNOWN:
                    continue
                if existing == UNKNOWN:
                    tgt["amounts"][ledger] = amount
                    continue
                if (existing.low, existing.likely, existing.high) == \
                        (amount.low, amount.likely, amount.high):
                    # Two components independently reporting the same range is
                    # corroboration, not a conflict. Keep the first and record
                    # the second source so the agreement is visible.
                    continue
                conflicts.append({
                    "work_item_id": wid,
                    "ledger": ledger,
                    "sources": sorted([existing.source_component,
                                       amount.source_component]),
                    "values": sorted([
                        "%s: %g/%g/%g" % (existing.source_record_id, existing.low,
                                          existing.likely, existing.high),
                        "%s: %g/%g/%g" % (amount.source_record_id, amount.low,
                                          amount.likely, amount.high),
                    ]),
                    "resolution": "held at UNKNOWN pending a human decision; "
                                  "neither source is silently preferred",
                })
                tgt["amounts"][ledger] = UNKNOWN
            # Once mapped, the item is mapped.
            if tgt["recommendation_ids"]:
                tgt["unmapped_reason"] = ""
    conflicts.sort(key=lambda c: (c["work_item_id"], c["ledger"]))
    return [merged[w] for w in order], conflicts


# --------------------------------------------------------------------------
# Totals that refuse to treat UNKNOWN as zero
# --------------------------------------------------------------------------
def total(items, ledger):
    """Sum one ledger across items, keeping UNKNOWN contributors visible.

    A total built from three known amounts and one UNKNOWN is NOT the sum of
    the three -- it is a floor with a named gap. Reporting it as a complete
    figure would understate the programme by exactly the part nobody estimated.
    """
    known, unknown = [], []
    for item in items:
        amount = item["amounts"].get(ledger, UNKNOWN)
        if amount == UNKNOWN:
            unknown.append(item["work_item_id"])
        else:
            known.append(amount)
    if not known:
        return {
            "ledger": ledger, "state": UNKNOWN,
            "low": UNKNOWN, "likely": UNKNOWN, "high": UNKNOWN,
            "contributors": [], "unknown_contributors": sorted(unknown),
            "complete": False,
            "note": "no contributor supplied this ledger; not reported as zero",
        }
    acc = known[0]
    for amount in known[1:]:
        acc = acc + amount            # LedgerUnitError if units ever diverge
    return {
        "ledger": ledger,
        "state": "PARTIAL" if unknown else "COMPLETE",
        "low": round(acc.low, 4), "likely": round(acc.likely, 4),
        "high": round(acc.high, 4),
        "contributors": sorted(a.source_record_id for a in known),
        "unknown_contributors": sorted(unknown),
        "complete": not unknown,
        "note": ("floor only: %d contributor(s) supplied no estimate and are "
                 "NOT counted as zero" % len(unknown)) if unknown else "",
    }


def _delta(per_rec_sum, rollup):
    """The double-count line: per-recommendation sum minus the roll-up."""
    if per_rec_sum["state"] == UNKNOWN or rollup["state"] == UNKNOWN:
        return UNKNOWN
    return {
        "low": round(per_rec_sum["low"] - rollup["low"], 4),
        "likely": round(per_rec_sum["likely"] - rollup["likely"], 4),
        "high": round(per_rec_sum["high"] - rollup["high"], 4),
    }


# --------------------------------------------------------------------------
# Integration
# --------------------------------------------------------------------------
def _serialise_item(item):
    """JSON-safe view of a merged work item, with every Amount expanded so the
    original range, basis and source record id stay visible in the output."""
    out = {}
    for key, value in item.items():
        if key == "amounts":
            out[key] = {lg: (a if a == UNKNOWN else a.as_dict())
                        for lg, a in value.items()}
        elif key == "specialist_roles":
            out[key] = [
                {"role": r["role"],
                 "one_time_hours": (r["one_time_hours"]
                                    if r["one_time_hours"] == UNKNOWN
                                    else r["one_time_hours"].as_dict())}
                for r in value]
        else:
            out[key] = value
    return out


def integrate(register, work_items, conflicts, currency):
    recs = register.get("recommendations", [])
    if not recs:
        raise AdapterError("recommendation register contains no recommendations")
    known_rec_ids = {r["recommendation_id"] for r in recs}

    dangling = sorted({
        rid for item in work_items for rid in item["recommendation_ids"]
        if rid not in known_rec_ids
    })

    # A reference to a recommendation that does not exist must not make a work
    # item look shared, and must not inflate the per-recommendation sum: no row
    # in the table ever charges it. Dangling ids are reported separately, so
    # they are visible without being counted. (Found by reading the first real
    # run: WI-RIS-WINDOW-DOC-001 appeared under "shared work" on the strength of
    # a recommendation id that is not in the register.)
    for item in work_items:
        item["known_recommendation_ids"] = [
            r for r in item["recommendation_ids"] if r in known_rec_ids]

    per_rec = []
    for rec in sorted(recs, key=lambda r: r["recommendation_id"]):
        rid = rec["recommendation_id"]
        mine = [i for i in work_items if rid in i["known_recommendation_ids"]]
        shared = [i["work_item_id"] for i in mine
                  if len(i["known_recommendation_ids"]) > 1]
        entry = {
            "recommendation_id": rid,
            "title": rec.get("title", ""),
            "group": rec.get("group", ""),
            "area": rec.get("area", ""),
            "work_item_ids": sorted(i["work_item_id"] for i in mine),
            "shared_work_item_ids": sorted(shared),
            "ledgers": {ledger: total(mine, ledger) for ledger in ALL_LEDGERS},
        }
        if not mine:
            entry["resourcing_state"] = "NO_RESOURCING_DATA"
            entry["resourcing_note"] = (
                "no resource or economics record names this recommendation. "
                "It is not costed, which is not the same as costing nothing.")
        else:
            incomplete = [l for l in ALL_LEDGERS
                          if not entry["ledgers"][l]["complete"]]
            entry["resourcing_state"] = "PARTIAL" if incomplete else "COMPLETE"
            entry["resourcing_note"] = (
                "ledgers without a complete estimate: %s" % ", ".join(incomplete)
                if incomplete else "")
        per_rec.append(entry)

    mapped = [i for i in work_items if i["known_recommendation_ids"]]
    unmapped = [i for i in work_items if not i["known_recommendation_ids"]]

    rollup, per_rec_sum, double_counted = {}, {}, {}
    for ledger in ALL_LEDGERS:
        rollup[ledger] = total(mapped, ledger)
        # The per-recommendation sum counts a shared item once per
        # recommendation. That is correct for that view and wrong for the
        # programme, which is the whole point of showing both.
        expanded = []
        for item in mapped:
            for _ in item["known_recommendation_ids"]:
                expanded.append(item)
        per_rec_sum[ledger] = total(expanded, ledger)
        double_counted[ledger] = _delta(per_rec_sum[ledger], rollup[ledger])

    shared_items = sorted(
        ({"work_item_id": i["work_item_id"], "label": i["label"],
          "recommendation_ids": i["recommendation_ids"]}
         for i in mapped if len(i["known_recommendation_ids"]) > 1),
        key=lambda d: d["work_item_id"])

    result = {
        "schema_version": SCHEMA_VERSION,
        "currency": currency,
        "ledger_rule": (
            "Five ledgers are reported separately and are never summed across: "
            + "; ".join(ALL_LEDGERS)
            + ". Adding across any two raises LedgerUnitError."),
        "double_count_rule": (
            "Shared work appears under every recommendation that needs it in "
            "the per-recommendation view, and exactly once in the portfolio "
            "roll-up. The difference is published below as "
            "shared_work_not_double_counted."),
        "recommendations": per_rec,
        "work_items": [_serialise_item(i)
                       for i in sorted(work_items, key=lambda i: i["work_item_id"])],
        "portfolio_rollup": rollup,
        "sum_of_per_recommendation": per_rec_sum,
        "shared_work_not_double_counted": double_counted,
        "shared_work_items": shared_items,
        "unmapped_work_items": sorted(
            ({"work_item_id": i["work_item_id"], "label": i["label"],
              "source_components": i["source_components"],
              "reason": i["unmapped_reason"] or
                       ("every recommendation id it names is absent from the "
                        "register: %s" % ", ".join(i["recommendation_ids"]))}
             for i in unmapped),
            key=lambda d: d["work_item_id"]),
        "dangling_recommendation_ids": dangling,
        "component_conflicts": conflicts,
        "recommendations_without_resourcing": sorted(
            e["recommendation_id"] for e in per_rec
            if e["resourcing_state"] == "NO_RESOURCING_DATA"),
    }
    result["content_digest"] = _digest(result)
    return result


def _digest(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------
_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def csv_cell(value):
    """Neutralise formula injection without mangling negative numbers.

    Released capacity is allowed to be negative (a workflow that costs more
    than it saves), so a guard that prefixed everything starting with '-'
    would corrupt real results.
    """
    s = "" if value is None else str(value)
    if s and s[0] in _TRIGGERS and not _is_number(s):
        return "'" + s
    return s


_SHORT = {
    ONE_TIME_EFFORT: "one_time_effort_hours",
    RECURRING_EFFORT: "recurring_effort_fte_yr",
    ONE_TIME_CASH: "one_time_cash",
    RECURRING_CASH: "recurring_cash_yr",
    RELEASED_CAPACITY: "released_capacity_hours_yr",
}


def write_resourcing_table(result, path):
    header = ["recommendation_id", "title", "group", "area", "resourcing_state",
              "work_item_ids", "shared_work_item_ids"]
    for ledger in ALL_LEDGERS:
        short = _SHORT[ledger]
        header += ["%s_low" % short, "%s_likely" % short, "%s_high" % short,
                   "%s_state" % short, "%s_unknown_contributors" % short]
    header.append("resourcing_note")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for entry in result["recommendations"]:
            row = [entry["recommendation_id"], entry["title"], entry["group"],
                   entry["area"], entry["resourcing_state"],
                   "; ".join(entry["work_item_ids"]) or "none",
                   "; ".join(entry["shared_work_item_ids"]) or "none"]
            for ledger in ALL_LEDGERS:
                t = entry["ledgers"][ledger]
                row += [t["low"], t["likely"], t["high"], t["state"],
                        "; ".join(t["unknown_contributors"]) or "none"]
            row.append(entry["resourcing_note"])
            w.writerow([csv_cell(c) for c in row])


def write_rollup(result, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ledger", "view", "low", "likely", "high", "state", "note"])
        for ledger in ALL_LEDGERS:
            for view, key in (("portfolio_rollup (each work item once)", "portfolio_rollup"),
                              ("sum_of_per_recommendation (shared work repeated)",
                               "sum_of_per_recommendation")):
                t = result[key][ledger]
                w.writerow([csv_cell(x) for x in [
                    ledger, view, t["low"], t["likely"], t["high"], t["state"],
                    t["note"]]])
            d = result["shared_work_not_double_counted"][ledger]
            if d == UNKNOWN:
                w.writerow([csv_cell(x) for x in [
                    ledger, "shared_work_not_double_counted", UNKNOWN, UNKNOWN,
                    UNKNOWN, UNKNOWN,
                    "cannot be stated while either view is UNKNOWN"]])
            else:
                w.writerow([csv_cell(x) for x in [
                    ledger, "shared_work_not_double_counted", d["low"],
                    d["likely"], d["high"], "DERIVED",
                    "amount the per-recommendation view repeats because work "
                    "is shared; removed from the programme total"]])


def write_report(result, path):
    L = []
    a = L.append
    a("# Resourcing and economics joined to the recommendation register")
    a("")
    a("**UIOWA-105.** Generated by `integrate.py`. Deterministic; no clock, no RNG.")
    a("")
    a("> Every figure below originates in a synthetic fixture or in a synthetic "
      "component output. None of it is a University of Iowa finding.")
    a("")
    a("## The two views disagree on purpose")
    a("")
    a(result["double_count_rule"])
    a("")
    a(result["ledger_rule"])
    a("")
    a("Currency for all cash ledgers: **%s** (declared by the economics "
      "component; this lane does not convert or infer it)." % result["currency"])
    a("")

    a("## Portfolio roll-up versus the per-recommendation sum")
    a("")
    a("| Ledger | Roll-up (once each) | Per-recommendation sum | Repeated by sharing |")
    a("|---|---|---|---|")
    for ledger in ALL_LEDGERS:
        r = result["portfolio_rollup"][ledger]
        s = result["sum_of_per_recommendation"][ledger]
        d = result["shared_work_not_double_counted"][ledger]
        fmt = lambda t: (UNKNOWN if t["state"] == UNKNOWN
                         else "%.2f - %.2f - %.2f%s" % (t["low"], t["likely"],
                                                        t["high"],
                                                        "" if t["complete"] else " *(floor)*"))
        dd = (UNKNOWN if d == UNKNOWN
              else "%.2f - %.2f - %.2f" % (d["low"], d["likely"], d["high"]))
        a("| %s | %s | %s | %s |" % (ledger, fmt(r), fmt(s), dd))
    a("")
    a("A *(floor)* marker means at least one contributor supplied no estimate. "
      "Those contributors are named in the JSON and are **not** counted as zero.")
    a("")

    if result["shared_work_items"]:
        a("### Work shared by more than one recommendation")
        a("")
        for item in result["shared_work_items"]:
            a("- `%s` %s — needed by %s. Counted once in the roll-up, shown "
              "under each recommendation."
              % (item["work_item_id"], item["label"],
                 ", ".join("`%s`" % r for r in item["recommendation_ids"])))
        a("")

    a("## Per recommendation")
    a("")
    a("| Recommendation | State | One-time effort (h) | Recurring (FTE/yr) | "
      "One-time cash | Recurring cash/yr | Released capacity (h/yr) |")
    a("|---|---|---|---|---|---|---|")
    for entry in result["recommendations"]:
        cells = []
        for ledger in ALL_LEDGERS:
            t = entry["ledgers"][ledger]
            cells.append(UNKNOWN if t["state"] == UNKNOWN
                         else "%.2f - %.2f - %.2f%s" % (t["low"], t["likely"],
                                                        t["high"],
                                                        "" if t["complete"] else " (floor)"))
        a("| `%s` | %s | %s |" % (entry["recommendation_id"],
                                  entry["resourcing_state"], " | ".join(cells)))
    a("")

    if result["recommendations_without_resourcing"]:
        a("**Not costed at all:** %s. No resource or economics record names "
          "these. Not costed is not the same as costing nothing, and they are "
          "listed rather than shown as zero."
          % ", ".join("`%s`" % r for r in result["recommendations_without_resourcing"]))
        a("")
    if result["unmapped_work_items"]:
        a("**Work items not tied to any recommendation** (carried, not dropped):")
        for item in result["unmapped_work_items"]:
            a("- `%s` %s — %s" % (item["work_item_id"], item["label"], item["reason"]))
        a("")
    if result["dangling_recommendation_ids"]:
        a("**Referenced recommendation ids that are not in the register:** %s. "
          "These are reported rather than created."
          % ", ".join("`%s`" % r for r in result["dangling_recommendation_ids"]))
        a("")
    if result["component_conflicts"]:
        a("**Component conflicts** — two components supplied the same ledger "
          "for the same work item:")
        for c in result["component_conflicts"]:
            a("- `%s` / %s: %s. %s" % (c["work_item_id"], c["ledger"],
                                       " vs ".join(c["values"]), c["resolution"]))
        a("")

    a("Content digest: `%s`" % result["content_digest"])
    a("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _load(path, what):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise AdapterError("%s not found at %s" % (what, path))
    except json.JSONDecodeError as exc:
        raise AdapterError("%s at %s is not valid JSON: %s" % (what, path, exc))


def build(register_path, resource_path, economics_path, portfolio_path,
          crosswalk_path):
    register = _load(register_path, "recommendation register")
    resource_items = adapters.adapt_resource_estimates(
        _load(resource_path, "resource estimates"))
    econ_items, currency = adapters.adapt_economics(
        _load(economics_path, "economics"))
    portfolio_items = []
    if portfolio_path and os.path.exists(portfolio_path):
        crosswalk = _load(crosswalk_path, "crosswalk").get("candidates", {})
        portfolio_items = adapters.adapt_opportunity_portfolio(
            _load(portfolio_path, "opportunity portfolio"), crosswalk)
    merged, conflicts = merge_work_items(resource_items, econ_items, portfolio_items)
    return integrate(register, merged, conflicts, currency)


def main(argv=None):
    p = argparse.ArgumentParser(description="UIOWA-105 resourcing integration")
    prio = find_component("uiowa_rfq_18649_prioritization")
    port = find_component("uiowa_rfq_18649_ai_opportunity_portfolio")
    p.add_argument("--register", default=(
        os.path.join(prio, "fixtures", "synthetic-recommendations.json")
        if prio else os.path.join(HERE, "fixtures", "register.fallback.json")))
    p.add_argument("--resource-estimates",
                   default=os.path.join(HERE, "fixtures", "resource_estimates.contract.json"))
    p.add_argument("--economics",
                   default=os.path.join(HERE, "fixtures", "economics.contract.json"))
    p.add_argument("--portfolio", default=(
        os.path.join(port, "sample_output", "portfolio.json") if port else ""))
    p.add_argument("--crosswalk", default=os.path.join(HERE, "fixtures", "crosswalk.json"))
    p.add_argument("--out", default=os.path.join(HERE, "sample_output"))
    args = p.parse_args(argv)

    try:
        result = build(args.register, args.resource_estimates, args.economics,
                       args.portfolio, args.crosswalk)
    except (AdapterError, LedgerUnitError) as exc:
        sys.stderr.write("INTEGRATION ERROR: %s\n" % exc)
        return 2

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "integrated.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    write_resourcing_table(result, os.path.join(args.out, "resourcing_table.csv"))
    write_rollup(result, os.path.join(args.out, "portfolio_rollup.csv"))
    write_report(result, os.path.join(args.out, "integration_report.md"))

    print("recommendations: %d" % len(result["recommendations"]))
    print("work items: %d (shared by >1 recommendation: %d)"
          % (len(result["work_items"]), len(result["shared_work_items"])))
    print("not costed at all: %s"
          % (", ".join(result["recommendations_without_resourcing"]) or "none"))
    print("unmapped work items: %s"
          % (", ".join(i["work_item_id"] for i in result["unmapped_work_items"]) or "none"))
    print("component conflicts: %d" % len(result["component_conflicts"]))
    for ledger in ALL_LEDGERS:
        d = result["shared_work_not_double_counted"][ledger]
        r = result["portfolio_rollup"][ledger]
        if d != UNKNOWN and d["likely"]:
            print("  %-48s rollup likely %.2f, per-rec sum repeats %.2f"
                  % (ledger, r["likely"], d["likely"]))
    print("portfolio used: %s" % (args.portfolio or "NOT RESOLVED"))
    print("digest: %s" % result["content_digest"])
    print("written to: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
