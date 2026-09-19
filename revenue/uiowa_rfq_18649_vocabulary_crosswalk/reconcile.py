#!/usr/bin/env python3
"""Reconcile the group and assessment-area vocabularies used across the RFQ-18649 lanes.

Why: 41 files in the tree carry an assessment-area column and they do not agree on what
the four areas are called. That is not hypothetical - a UIOWA-130 check that said
"deployment" where a lane says "deployment_operations" manufactured a 3-cell gap in
another seat's work before it was caught.

What this does NOT do, deliberately: it does not fuzzy-match, edit-distance, stem, or
prefix-match anything. Every mapping is declared in crosswalk.json by a human-readable
basis. A term that is not declared comes back UNMAPPED and is reported. Guessing is how
two lanes that measure different things end up silently joined.

Strictly READ-ONLY against every other lane: it parses files and writes only into --out.

    python3 reconcile.py --revenue-root .. --out output

Exit codes: 0 always for a completed scan - unresolved vocabulary is a finding to report,
not a failure of this tool. 2 if the crosswalk or tree could not be read.
"""
import argparse
import csv
import io
import json
import os
import sys

import scan_vocabulary as SV

BANNER = ("VOCABULARY RECONCILIATION over synthetic RFQ-18649 fixtures. Terms are "
          "reported as observed; mappings are declared, never guessed. Nothing here is "
          "a University of Iowa finding, and no lane is scored, ranked or certified.")

# This package's own outputs copy terms out of other lanes. Counting them would report
# one lane's vocabulary twice and inflate how widespread a term looks.
DEFAULT_SKIP = ("uiowa_rfq_18649_vocabulary_crosswalk",)
SKIP_PATH_PARTS = ("sample_packet",)

MULTI_SEPARATORS = SV.MULTI_SEPARATORS

RESOLVED_KINDS = ("EXACT_VARIANT", "DECLARED_JUDGMENT", "SCOPE_VALUE",
                  "GRANULARITY_MISMATCH")
UNRESOLVED_KINDS = ("COMPOUND", "CROSS_SLOT_PACKED", "SCOPE_VALUE_AREA", "AMBIGUOUS",
                    "UNRESOLVED_CONCEPT", "UNMAPPED")


def classify(term, slot, crosswalk):
    """Map one observed term. Returns a record; never returns a guess."""
    declared = crosswalk[slot].get(term)
    if declared:
        return {
            "term": term, "slot": slot, "canonical": declared.get("canonical"),
            "kind": declared["kind"], "basis": declared["basis"],
            "question": declared.get("question", ""),
        }
    if ":" in term:
        halves = [h.strip() for h in term.split(":") if h.strip()]
        if len(halves) == 2:
            a = crosswalk["group"].get(halves[0]), crosswalk["area"].get(halves[1])
            if all(d and d.get("canonical") for d in a):
                return {
                    "term": term, "slot": slot, "canonical": None,
                    "kind": "CROSS_SLOT_PACKED",
                    "basis": (f"packs a group ({halves[0]}) and an area ({halves[1]}) "
                              "into one field; both halves are declared terms in "
                              "different slots. Not split - splitting changes the row's "
                              "cardinality, and the packed value is a different thing "
                              "from either half."),
                    "question": ("Should a packed group:area value be joined as a "
                                 "group, as an area, or as a composite key?"),
                    "parts": halves,
                }
    if any(sep in term for sep in MULTI_SEPARATORS):
        parts = [p.strip() for p in term.replace(";", "|").split("|") if p.strip()]
        mapped, unmapped = [], []
        for part in parts:
            d = crosswalk[slot].get(part)
            (mapped if d and d.get("canonical") else unmapped).append(part)
        return {
            "term": term, "slot": slot, "canonical": None, "kind": "COMPOUND",
            "basis": ("one cell naming several terms at once; parts "
                      f"{sorted(mapped) or 'none'} are declared, "
                      f"{sorted(unmapped) or 'none'} are not. The cell is NOT split into "
                      "independent rows - splitting would assume the separator means "
                      "'and' and would double-count the row."),
            "question": "Should a cell naming several areas count once, or once per area?",
            "parts": parts,
        }
    return {
        "term": term, "slot": slot, "canonical": None, "kind": "UNMAPPED",
        "basis": "not declared in crosswalk.json; this package does not guess",
        "question": f"Which canonical {slot} does {term!r} denote, if any?",
    }


def reconcile(root, crosswalk, skip_lanes=DEFAULT_SKIP):
    observations = [
        o for o in SV.scan(root, skip_lanes=skip_lanes)
        if not any(part in o["file"] for part in SKIP_PATH_PARTS)
    ]
    grouped = SV.terms_by_slot(observations)
    records = []
    for slot in ("group", "area"):
        for term, entry in sorted(grouped[slot].items()):
            rec = classify(term, slot, crosswalk)
            rec.update({"rows": entry["rows"], "lanes": entry["lanes"],
                        "files": entry["files"], "columns": entry["columns"]})
            records.append(rec)

    tally = {}
    for r in records:
        tally[r["kind"]] = tally.get(r["kind"], 0) + 1

    # Collisions: distinct canonical values whose observed terms share a leading word.
    # Reported so a reader can see WHY a naive join is unsafe, never used to map.
    collisions = []
    by_slot = {}
    for r in records:
        by_slot.setdefault(r["slot"], []).append(r)
    for slot, recs in sorted(by_slot.items()):
        buckets = {}
        for r in recs:
            head = r["term"].lower().replace("-", "_").split("_")[0].split(" ")[0]
            buckets.setdefault(head, []).append(r)
        for head, members in sorted(buckets.items()):
            canon = {m["canonical"] for m in members}
            if len(members) > 1 and len(canon) > 1:
                collisions.append({
                    "slot": slot, "shared_prefix": head,
                    "terms": sorted(m["term"] for m in members),
                    "distinct_canonical": sorted(str(c) for c in canon),
                    "why_it_matters": ("these terms begin with the same word but do not "
                                       "all resolve to the same canonical value, so a "
                                       "join on the raw column would merge rows that "
                                       "this crosswalk keeps separate"),
                })
    notes = [n for n in (slash_taxonomy_note(records),) if n]
    key_collisions = key_name_collisions(observations)
    return {
        "_banner": BANNER,
        "canonical": crosswalk["canonical"],
        "patterns": notes,
        "kinds": crosswalk["kinds"],
        "counts": {
            "observations": len(observations),
            "distinct_terms": len(records),
            "files_scanned": len({o["file"] for o in observations}),
            "lanes_scanned": len({o["lane"] for o in observations}),
            "resolved": sum(1 for r in records if r["kind"] in RESOLVED_KINDS),
            "needing_a_decision": sum(1 for r in records if r["kind"] in UNRESOLVED_KINDS),
            "by_kind": tally,
        },
        "terms": records,
        "collisions": collisions,
        "key_name_collisions": key_collisions,
        "observations": observations,
    }


def key_name_collisions(observations):
    """Report key/column names that carry disjoint value sets in different lanes.

    Found when the scan was extended to JSON: the key `dimension` holds
    ai_readiness/deployment/security/software in one lane and delivery/quality/security
    in another, where the second set is scoring dimensions, not assessment areas. A
    column name is therefore not a reliable indicator of what a column holds, which is
    why this package matches header names exactly and still reports the overlap.
    """
    by_key = {}
    for o in observations:
        by_key.setdefault(o["column"].strip().lower(), {}).setdefault(
            o["lane"], set()).add(o["term"])
    out = []
    for key, lanes in sorted(by_key.items()):
        if len(lanes) < 2:
            continue
        disjoint = []
        names = sorted(lanes)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if not (lanes[a] & lanes[b]):
                    disjoint.append((a, b))
        if disjoint:
            out.append({
                "key": key,
                "lane_pairs_with_no_shared_value": [list(p) for p in disjoint[:8]],
                "values_by_lane": {ln: sorted(v) for ln, v in sorted(lanes.items())},
                "finding": (f"the key {key!r} carries value sets with no overlap between "
                            "at least two lanes, so the key name alone does not "
                            "establish what the column holds"),
            })
    return out


def slash_taxonomy_note(records):
    """Report slash-joined prose terms WITHOUT splitting them.

    One lane writes its area column as prose joined by " / ". The separator does not
    mean the same thing twice in the same column: in "Deployment / operations" the
    slash joins two words of ONE concept, while in "Access / IAM / software delivery"
    it appears to join distinct concepts. Splitting on it would be a guess, and it
    would invent an "Access" area and destroy the "Deployment and operations" one.
    So these stay UNMAPPED and the pattern is reported instead.
    """
    hits = [r for r in records if " / " in r["term"]]
    if not hits:
        return None
    return {
        "pattern": "slash_joined_prose_terms",
        "term_count": len(hits),
        "row_count": sum(r["rows"] for r in hits),
        "lanes": sorted({lane for r in hits for lane in r["lanes"]}),
        "terms": sorted(r["term"] for r in hits),
        "finding": ("These terms use a different taxonomy, not a different spelling of "
                    "the same one. They name concepts outside the four assessment areas "
                    "entirely - data classification, records handling, accessibility, "
                    "procurement, governance - so no canonical assessment area applies."),
        "why_not_split": ('" / " does not carry one meaning in this column. In '
                          '"Deployment / operations" it joins two words of a single '
                          'concept; in "Access / IAM / software delivery" it appears to '
                          'join separate concepts. Splitting on it would invent an '
                          '"Access" area and destroy "Deployment and operations". This '
                          "package does not split on an ambiguous separator."),
        "question": ("Is this column the four-area assessment taxonomy under other "
                     "names, or a separate policy-topic taxonomy that should not be "
                     "joined to it at all?"),
    }


def _csv(fieldnames, rows):
    buf = io.StringIO(newline="")
    buf.write("# " + BANNER + "\n")
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("; ".join(map(str, v)) if isinstance(v, list) else
                        ("" if v is None else v)) for k, v in r.items()})
    return buf.getvalue()


def render(report):
    L, a = [], None
    a = L.append
    a("# RFQ-18649 group and assessment-area vocabulary reconciliation")
    a("")
    a("> **" + BANNER + "**")
    a("")
    c = report["counts"]
    a(f"{c['observations']} observations across {c['files_scanned']} files in "
      f"{c['lanes_scanned']} lanes. **{c['distinct_terms']} distinct terms**: "
      f"{c['resolved']} resolve to a canonical value, **{c['needing_a_decision']} need "
      f"a decision from the lane that uses them.**")
    a("")
    a("## 1. Why this matters")
    a("")
    a("A check written against one lane's spelling silently mis-compares another's. "
      "This is not hypothetical: a UIOWA-130 check that said `deployment` where a lane "
      "says `deployment_operations` reported that lane as covering 9 of 12 cells when "
      "it covers all 12. The check manufactured a gap in another seat's work.")
    a("")
    a("## 2. Terms needing a decision")
    a("")
    a("These are **not** mapped. Each names the lane that must answer.")
    a("")
    a("| Term | Slot | Kind | Rows | Lanes | Question |")
    a("| --- | --- | --- | --- | --- | --- |")
    for r in report["terms"]:
        if r["kind"] in UNRESOLVED_KINDS:
            a(f"| `{r['term']}` | {r['slot']} | **{r['kind']}** | {r['rows']} | "
              f"{', '.join(r['lanes'])} | {r['question']} |")
    a("")
    a("## 3. Declared mappings")
    a("")
    a("`EXACT_VARIANT` is mechanical — same words, different case or separator — and can "
      "be accepted without argument. `DECLARED_JUDGMENT` is this package's reading and "
      "a reviewer may reject it; the original term is retained either way.")
    a("")
    a("| Term | Slot | → | Kind | Rows | Basis |")
    a("| --- | --- | --- | --- | --- | --- |")
    for r in report["terms"]:
        if r["kind"] in RESOLVED_KINDS:
            a(f"| `{r['term']}` | {r['slot']} | `{r['canonical']}` | {r['kind']} | "
              f"{r['rows']} | {r['basis']} |")
    a("")
    a("## 4. Terms that resemble each other but do not resolve together")
    a("")
    if report["collisions"]:
        for col in report["collisions"]:
            a(f"- **`{col['shared_prefix']}…`** ({col['slot']}): "
              f"{', '.join('`' + t + '`' for t in col['terms'])} → "
              f"{', '.join('`' + c + '`' for c in col['distinct_canonical'])}. "
              f"{col['why_it_matters']}.")
    else:
        a("None observed.")
    a("")
    for note in report.get("patterns", []):
        a(f"## 4b. Pattern: {note['pattern'].replace('_', ' ')}")
        a("")
        a(f"**{note['term_count']} terms / {note['row_count']} rows**, all in "
          f"{', '.join('`' + l + '`' for l in note['lanes'])}.")
        a("")
        a(note["finding"])
        a("")
        a(f"**Not split.** {note['why_not_split']}")
        a("")
        a(f"*Question for that lane:* {note['question']}")
        a("")
    if report.get("key_name_collisions"):
        a("## 4c. Key names that do not mean one thing")
        a("")
        for kc in report["key_name_collisions"]:
            a(f"- **`{kc['key']}`** — {kc['finding']}.")
            for lane, vals in sorted(kc["values_by_lane"].items()):
                a(f"    - `{lane}`: {', '.join('`' + v + '`' for v in vals[:8])}")
        a("")
    a("## 5. What this package will not do")
    a("")
    a("- **No fuzzy matching of any kind.** An undeclared term is `UNMAPPED`, never "
      "assigned to the nearest-looking canonical value.")
    a("- **`operational_reliability` is not mapped to `DEP`.** Reliability in operation "
      "is an outcome; deployment and operations is a practice area. Equating them would "
      "fabricate agreement between lanes that may be measuring different things.")
    a("- **Compound cells are not split.** Splitting `ai_readiness|security` into two "
      "rows assumes the separator means \"and\" and double-counts the row.")
    a("- **No lane is scored, ranked, corrected or certified.** No file outside this "
      "package's own output directory is written.")
    a("")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--revenue-root", default="..")
    p.add_argument("--crosswalk", default="crosswalk.json")
    p.add_argument("--out", default="output")
    args = p.parse_args(argv)
    try:
        with open(args.crosswalk, encoding="utf-8") as fh:
            crosswalk = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"CROSSWALK UNREADABLE: {exc}", file=sys.stderr)
        return 2
    if not os.path.isdir(args.revenue_root):
        print(f"TREE NOT FOUND: {args.revenue_root}", file=sys.stderr)
        return 2

    report = reconcile(args.revenue_root, crosswalk)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "vocabulary_report.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    with open(os.path.join(args.out, "term_crosswalk.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(_csv(["slot", "term", "canonical", "kind", "rows", "lanes", "basis",
                       "question"], report["terms"]))
    with open(os.path.join(args.out, "needs_a_decision.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(_csv(["slot", "term", "kind", "rows", "lanes", "files", "question"],
                      [r for r in report["terms"] if r["kind"] in UNRESOLVED_KINDS]))
    with open(os.path.join(args.out, "observations.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(_csv(["slot", "term", "lane", "file", "column", "rows", "compound"],
                      report["observations"]))
    with open(os.path.join(args.out, "VOCABULARY_REPORT.md"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(render(report))

    print(BANNER)
    print("")
    print(f"scanned        {c['files_scanned'] if (c := report['counts']) else 0} files "
          f"in {c['lanes_scanned']} lanes, {c['observations']} observations")
    print(f"distinct terms {c['distinct_terms']}")
    for kind in RESOLVED_KINDS + UNRESOLVED_KINDS:
        if c["by_kind"].get(kind):
            print(f"  {kind:<22} {c['by_kind'][kind]}")
    print(f"resolved       {c['resolved']}")
    print(f"need a decision {c['needing_a_decision']}")
    print(f"collisions     {len(report['collisions'])} term group(s) that resemble each "
          f"other but do not resolve together")
    for note in report.get("patterns", []):
        print(f"pattern        {note['pattern']}: {note['term_count']} terms / "
              f"{note['row_count']} rows in {', '.join(note['lanes'])}")
    print(f"key collisions {len(report.get('key_name_collisions', []))} key name(s) "
          f"carrying disjoint value sets across lanes")
    print(f"written to     {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
