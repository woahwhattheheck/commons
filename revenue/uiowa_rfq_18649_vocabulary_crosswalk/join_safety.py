#!/usr/bin/env python3
"""Answer the question the crosswalk exists to serve: can these two files be joined?

A reconciliation report tells you the vocabularies disagree. It does not tell you
whether YOUR join is affected. This does: give it two CSVs and it reports, per slot,
the terms each side uses, which pair up through the declared crosswalk, and exactly
which rows would be lost or mis-joined if you joined on the raw column.

The verdict is one of:

  SAFE              every term on both sides resolves, and the resolved sets match.
                    A raw join still needs normalising, but nothing is ambiguous.
  NORMALISE_FIRST   every term resolves, but the two sides spell them differently.
                    A raw join silently drops rows; join on the canonical value.
  UNSAFE            at least one term involved does not resolve. Joining would guess.
  NOT_COMPARABLE    a slot is missing from one side entirely.

UNSAFE is not a failure of this tool. It is the finding: the terms needing a decision
are named, with the rows at stake, so somebody can answer them.

Strictly READ-ONLY. Python 3 standard library only.

    python3 join_safety.py --left A.csv --right B.csv --revenue-root ..
"""
import argparse
import json
import os
import sys

import reconcile as R
import scan_vocabulary as SV

SAFE, NORMALISE, UNSAFE, NOT_COMPARABLE = (
    "SAFE", "NORMALISE_FIRST", "UNSAFE", "NOT_COMPARABLE")


def _terms_in(path, slot):
    """Observed terms and row counts for one slot in one CSV."""
    try:
        rows = SV._read_rows(path)
    except OSError:
        return None
    if not rows:
        return None
    wanted = SV.GROUP_COLUMNS if slot == "group" else SV.AREA_COLUMNS
    found = {}
    for column in rows[0].keys():
        if column is None or column.strip().lower() not in wanted:
            continue
        for row in rows:
            raw = (row.get(column) or "").strip()
            if not raw or len(raw) > SV.MAX_TERM_LEN or SV._is_placeholder(raw):
                continue
            found[raw] = found.get(raw, 0) + 1
    return found or None


def assess_slot(left_terms, right_terms, slot, crosswalk):
    if left_terms is None or right_terms is None:
        return {
            "slot": slot, "verdict": NOT_COMPARABLE,
            "detail": (f"no {slot} column found on "
                       + " and ".join(s for s, t in (("the left file", left_terms),
                                                     ("the right file", right_terms))
                                      if t is None)),
            "unresolved": [], "left_only": [], "right_only": [], "rows_at_risk": 0,
        }
    left_map = {t: R.classify(t, slot, crosswalk) for t in left_terms}
    right_map = {t: R.classify(t, slot, crosswalk) for t in right_terms}

    unresolved = []
    for side, mapping, counts in (("left", left_map, left_terms),
                                  ("right", right_map, right_terms)):
        for term, rec in sorted(mapping.items()):
            if rec["canonical"] is None:
                unresolved.append({
                    "side": side, "term": term, "kind": rec["kind"],
                    "rows": counts[term], "question": rec["question"],
                })

    left_canon = {r["canonical"] for r in left_map.values() if r["canonical"]}
    right_canon = {r["canonical"] for r in right_map.values() if r["canonical"]}
    # Rows whose raw spelling has no exact counterpart on the other side. These are
    # precisely the rows a naive join on the raw column loses without saying so.
    spelling_mismatch = 0
    for term, n in left_terms.items():
        if term not in right_terms and left_map[term]["canonical"] in right_canon:
            spelling_mismatch += n
    for term, n in right_terms.items():
        if term not in left_terms and right_map[term]["canonical"] in left_canon:
            spelling_mismatch += n

    if unresolved:
        verdict = UNSAFE
        detail = (f"{len(unresolved)} term(s) covering "
                  f"{sum(u['rows'] for u in unresolved)} row(s) do not resolve; "
                  "joining would require guessing what they mean")
    elif spelling_mismatch:
        verdict = NORMALISE
        detail = (f"every term resolves, but {spelling_mismatch} row(s) are spelled "
                  "differently on the two sides; a join on the raw column drops them "
                  "silently. Join on the canonical value instead")
    elif left_canon != right_canon:
        verdict = SAFE
        detail = ("all terms resolve and spellings agree; the two sides cover "
                  f"different canonical values ({sorted(left_canon ^ right_canon)}), "
                  "which is a coverage difference, not a vocabulary problem")
    else:
        verdict = SAFE
        detail = "all terms resolve and both sides use the same spellings"

    return {
        "slot": slot, "verdict": verdict, "detail": detail,
        "unresolved": unresolved,
        "left_terms": sorted(left_terms), "right_terms": sorted(right_terms),
        "left_only": sorted(set(left_terms) - set(right_terms)),
        "right_only": sorted(set(right_terms) - set(left_terms)),
        "rows_at_risk": (sum(u["rows"] for u in unresolved) if unresolved
                         else spelling_mismatch),
    }


WORST_FIRST = (UNSAFE, NOT_COMPARABLE, NORMALISE, SAFE)


def assess(left_path, right_path, crosswalk):
    slots = [assess_slot(_terms_in(left_path, s), _terms_in(right_path, s), s, crosswalk)
             for s in ("group", "area")]
    overall = next(v for v in WORST_FIRST if any(s["verdict"] == v for s in slots))
    return {
        "_banner": R.BANNER,
        "left": left_path, "right": right_path,
        "overall_verdict": overall,
        "slots": slots,
        "rows_at_risk": sum(s["rows_at_risk"] for s in slots),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--left", required=True)
    p.add_argument("--right", required=True)
    p.add_argument("--revenue-root", default="..")
    p.add_argument("--crosswalk", default="crosswalk.json")
    p.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = p.parse_args(argv)
    try:
        with open(args.crosswalk, encoding="utf-8") as fh:
            crosswalk = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"CROSSWALK UNREADABLE: {exc}", file=sys.stderr)
        return 2

    def resolve(path):
        return path if os.path.isfile(path) else os.path.join(args.revenue_root, path)

    left, right = resolve(args.left), resolve(args.right)
    for path in (left, right):
        if not os.path.isfile(path):
            print(f"FILE NOT FOUND: {path}", file=sys.stderr)
            return 2

    report = assess(left, right, crosswalk)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(R.BANNER)
    print("")
    print(f"left   {args.left}")
    print(f"right  {args.right}")
    print("")
    print(f"VERDICT: {report['overall_verdict']}   ({report['rows_at_risk']} row(s) at risk)")
    print("")
    for slot in report["slots"]:
        print(f"  {slot['slot']:<6} {slot['verdict']}")
        print(f"         {slot['detail']}")
        if slot.get("left_only"):
            print(f"         only on the left:  {slot['left_only']}")
        if slot.get("right_only"):
            print(f"         only on the right: {slot['right_only']}")
        for u in slot["unresolved"]:
            print(f"         [{u['kind']}] {u['side']} {u['term']!r} "
                  f"({u['rows']} rows) - {u['question']}")
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
