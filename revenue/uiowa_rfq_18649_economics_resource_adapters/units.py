#!/usr/bin/env python3
"""UIOWA-105D - unit vocabulary resolution for the resourcing ledgers.

A scan of 62 landed lanes found four different spellings in use for quantities
that the final report has to present side by side:

    FTE-fraction per year (recurring staff load)   this lane
    staff-hours per month                          uiowa_rfq_18649_readout_deck
    person_hours_per_month                         uiowa_rfq_18649_adoption_readiness
    staff-hours available ... per phase window     uiowa_rfq_18649_capacity_feasibility
    effort_hours                                   uiowa_rfq_18649_unknown_propagation
    person_hours                                   uiowa_rfq_18649_adoption_readiness
    hours                                          several

THE RULE THIS MODULE ENFORCES: a unit is resolved only when BOTH its measure
and its period are stated lexically. "person_hours_per_month" and "staff-hours
per month" are the same quantity -- person/staff and underscore/hyphen are
spelling, not meaning. But a bare "staff-hours" does NOT resolve to one-time.

That last point is the whole reason this file exists. capacity_feasibility's
item effort IS one-time, but you only know that from its `meta`, not from the
string "staff-hours". Reading a bare hours unit as one-time is an inference,
and an inference made here would silently turn somebody's monthly figure into
a one-off cost. So an unstated period yields UNRESOLVED, and a caller has to
go and look rather than be handed a confident wrong answer.

Python 3 standard library only. Deterministic. No I/O.
"""

import re

# Verdicts
EQUIVALENT = "EQUIVALENT"        # same measure, same period
CONVERTIBLE = "CONVERTIBLE"      # different measure, a declared constant relates them
DIFFERENT = "DIFFERENT"          # not the same quantity
UNRESOLVED = "UNRESOLVED"        # cannot be decided from the strings alone

# Measures
M_HOURS = "staff-hours"
M_FTE = "FTE-fraction"
M_CURRENCY = "currency"
M_ITEMS = "items"
M_UNRESOLVED = "UNRESOLVED-MEASURE"

# Periods
P_ONE_TIME = "one-time"
P_MONTH = "per month"
P_YEAR = "per year"
P_PHASE_WINDOW = "per phase window"
P_UNSTATED = "UNSTATED-PERIOD"

# Spelling variants that carry no difference in meaning. person/staff and
# hyphen/underscore/space are orthography; they are normalised, not inferred.
_W = r'(?<![A-Za-z0-9])'      # start: not preceded by an alphanumeric
_E = r'(?![A-Za-z0-9])'       # end:   not followed by an alphanumeric
_MEASURE_PATTERNS = (
    (M_FTE, re.compile(_W + r'fte' + _E, re.I)),
    (M_HOURS, re.compile(_W + r'(staff|person|people|man)[\s_-]*hours?' + _E, re.I)),
    (M_HOURS, re.compile(_W + r'hours?' + _E, re.I)),
    (M_CURRENCY, re.compile(_W + r'(currency|usd|eur|gbp|cash|dollars?|cents?)' + _E, re.I)),
    (M_ITEMS, re.compile(_W + r'items?' + _E, re.I)),
)

# A period is only taken when it is written down.
_PERIOD_PATTERNS = (
    (P_PHASE_WINDOW, re.compile(r'per[\s_-]*phase[\s_-]*window', re.I)),
    (P_MONTH, re.compile(r'(per[\s_-]*month|monthly|/\s*month|p/?m\b)', re.I)),
    (P_YEAR, re.compile(r'(per[\s_-]*year|annual(?:ly)?|/\s*year|p/?a\b|per[\s_-]*annum)', re.I)),
    (P_ONE_TIME, re.compile(r'(one[\s_-]*time|onetime|upfront|up[\s_-]front)', re.I)),
)

# Measures a declared constant can convert between. Nothing is converted here;
# this only records that a conversion EXISTS and needs a stated constant.
_CONVERTIBLE_PAIRS = {
    frozenset((M_FTE, M_HOURS)): "hours per FTE-year",
}


def parse_unit(raw):
    """Break a unit string into measure and period. Never guesses a period."""
    text = "" if raw is None else str(raw)
    measure = M_UNRESOLVED
    for name, pattern in _MEASURE_PATTERNS:
        if pattern.search(text):
            measure = name
            break
    period = P_UNSTATED
    for name, pattern in _PERIOD_PATTERNS:
        if pattern.search(text):
            period = name
            break
    return {
        "raw": text,
        "measure": measure,
        "period": period,
        "resolved": measure != M_UNRESOLVED and period != P_UNSTATED,
        "note": ("" if period != P_UNSTATED else
                 "the period is not written in the unit string. It is NOT read "
                 "as one-time: a bare hours unit can be a monthly or annual "
                 "figure, and assuming otherwise turns a recurring commitment "
                 "into a one-off cost."),
    }


def units_equivalent(a, b, hours_per_fte_year=None):
    """Compare two unit strings. Returns (verdict, detail).

    EQUIVALENT only when both sides resolve and match. An unstated period on
    either side is UNRESOLVED, never EQUIVALENT and never DIFFERENT -- the
    strings genuinely do not say.
    """
    pa, pb = parse_unit(a), parse_unit(b)
    if pa["measure"] == M_UNRESOLVED or pb["measure"] == M_UNRESOLVED:
        return UNRESOLVED, ("the measure is not identifiable in %r or %r"
                            % (pa["raw"], pb["raw"]))
    if pa["period"] == P_UNSTATED or pb["period"] == P_UNSTATED:
        unstated = pa["raw"] if pa["period"] == P_UNSTATED else pb["raw"]
        return UNRESOLVED, (
            "%r does not state a period, so it cannot be matched against %r "
            "from the strings alone. Check the component's own metadata; do "
            "not read it as one-time."
            % (unstated, pb["raw"] if unstated == pa["raw"] else pa["raw"]))
    if pa["measure"] == pb["measure"]:
        if pa["period"] == pb["period"]:
            return EQUIVALENT, ("both are %s %s; the spellings %r and %r differ "
                                "but the quantity does not"
                                % (pa["measure"], pa["period"], pa["raw"], pb["raw"]))
        return DIFFERENT, ("same measure (%s) but different periods (%s vs %s)"
                           % (pa["measure"], pa["period"], pb["period"]))
    pair = frozenset((pa["measure"], pb["measure"]))
    if pair in _CONVERTIBLE_PAIRS:
        constant = _CONVERTIBLE_PAIRS[pair]
        if hours_per_fte_year is None:
            return CONVERTIBLE, (
                "%s and %s are related by a declared %s, which has not been "
                "supplied. No conversion is performed and no agreement is "
                "claimed." % (pa["measure"], pb["measure"], constant))
        return CONVERTIBLE, ("%s and %s relate through %s = %g"
                             % (pa["measure"], pb["measure"], constant,
                                hours_per_fte_year))
    return DIFFERENT, ("%s and %s are not the same quantity"
                       % (pa["measure"], pb["measure"]))


def resolve_vocabulary(observed):
    """Group observed unit strings by the quantity they denote.

    `observed` maps a component name to the unit strings it uses. Strings that
    resolve are grouped under 'measure period'. Strings that do not resolve are
    listed separately with the component that has to be asked -- they are not
    bucketed by guess.
    """
    groups, unresolved, out_of_scope = {}, [], []
    for component in sorted(observed):
        for raw in sorted(set(observed[component])):
            parsed = parse_unit(raw)
            if parsed["measure"] == M_UNRESOLVED:
                # No resourcing measure in the string at all: this is a measure
                # denominator or a free-text label, not a unit this module
                # governs. Counted, not listed as an unresolved unit.
                out_of_scope.append({"component": component, "unit": raw})
                continue
            if not parsed["resolved"]:
                unresolved.append({"component": component, "unit": raw,
                                   "measure": parsed["measure"],
                                   "period": parsed["period"],
                                   "note": parsed["note"]})
                continue
            key = "%s %s" % (parsed["measure"], parsed["period"])
            entry = groups.setdefault(key, {"quantity": key, "spellings": set(),
                                            "components": set()})
            entry["spellings"].add(raw)
            entry["components"].add(component)
    return {
        "quantities": [
            {"quantity": g["quantity"],
             "spellings": sorted(g["spellings"]),
             "components": sorted(g["components"]),
             "spelling_count": len(g["spellings"])}
            for g in sorted(groups.values(), key=lambda g: g["quantity"])],
        "unresolved": sorted(unresolved, key=lambda u: (u["component"], u["unit"])),
        "out_of_scope_count": len(out_of_scope),
        "out_of_scope": sorted(out_of_scope,
                               key=lambda u: (u["component"], u["unit"])),
        "verdict": (
            "%d quantities observed under %d spellings; %d resourcing unit "
            "strings name a measure but no period and are listed rather than "
            "guessed; %d strings carry no resourcing measure and are out of "
            "scope for this module."
            % (len(groups), sum(len(g["spellings"]) for g in groups.values()),
               len(unresolved), len(out_of_scope))),
    }


def render_vocabulary(resolved):
    L = ["## Unit vocabulary across landed lanes", "", resolved["verdict"], ""]
    if resolved["quantities"]:
        L += ["| Quantity | Spellings in use | Components |", "|---|---|---|"]
        for q in resolved["quantities"]:
            L.append("| `%s` | %s | %s |"
                     % (q["quantity"],
                        ", ".join("`%s`" % s for s in q["spellings"]),
                        ", ".join(q["components"])))
        L.append("")
    if resolved["unresolved"]:
        L += ["### Unit strings that do not state a period", "",
              "These are not read as one-time. Each needs its own component's "
              "metadata, or an answer from the seat that owns it.", "",
              "| Component | Unit | Measure | Period |", "|---|---|---|---|"]
        for u in resolved["unresolved"]:
            L.append("| %s | `%s` | %s | %s |"
                     % (u["component"], u["unit"], u["measure"], u["period"]))
        L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Scan the landed lanes for unit strings actually in use
# --------------------------------------------------------------------------
_UNIT_KEYS = ("unit", "units", "effort_unit", "measure_unit")


def observed_units_in_tree(revenue_dir, prefix="uiowa_rfq_18649_"):
    """Collect every unit string declared in landed lanes' JSON files.

    Reads only; writes nothing. Returns {component: sorted unit strings}.
    """
    import json
    import os

    observed = {}
    if not revenue_dir or not os.path.isdir(revenue_dir):
        return observed
    for lane in sorted(os.listdir(revenue_dir)):
        if not lane.startswith(prefix):
            continue
        found = set()
        for root, _, files in os.walk(os.path.join(revenue_dir, lane)):
            for name in sorted(files):
                if not name.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(root, name), encoding="utf-8") as fh:
                        doc = json.load(fh)
                except Exception:
                    continue

                def walk(node, depth=0):
                    if depth > 8:
                        return
                    if isinstance(node, dict):
                        for key, value in node.items():
                            if key in _UNIT_KEYS and isinstance(value, str) and value:
                                found.add(value)
                            walk(value, depth + 1)
                    elif isinstance(node, list):
                        for value in node[:200]:
                            walk(value, depth + 1)

                walk(doc)
        if found:
            observed[lane] = sorted(found)
    return observed


def main(argv=None):
    import argparse
    import json
    import os

    import integrate

    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description="UIOWA-105D unit vocabulary")
    p.add_argument("--revenue-dir", default=os.path.normpath(os.path.join(here, "..")))
    p.add_argument("--out", default=os.path.join(here, "sample_output"))
    args = p.parse_args(argv)

    observed = observed_units_in_tree(args.revenue_dir)
    # This lane's own ledger units belong in the comparison.
    from ledgers import ALL_LEDGERS
    observed["uiowa_rfq_18649_economics_resource_adapters"] = sorted(ALL_LEDGERS)
    resolved = resolve_vocabulary(observed)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "unit_vocabulary.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"schema_version": "uiowa-105d-units/1",
                   "observed": observed, "resolved": resolved},
                  fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(args.out, "unit_vocabulary.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# Unit vocabulary report (UIOWA-105D)\n\n"
                 "> Read-only scan of landed lanes. No lane is modified.\n\n")
        fh.write(render_vocabulary(resolved))
        fh.write("\n")

    print("components declaring units: %d" % len(observed))
    print(resolved["verdict"])
    for q in resolved["quantities"]:
        if q["spelling_count"] > 1:
            print("  %-28s %d spellings: %s"
                  % (q["quantity"], q["spelling_count"], ", ".join(q["spellings"])))
    for u in resolved["unresolved"]:
        print("  UNRESOLVED %-42s %r" % (u["component"], u["unit"]))
    print("written to: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
