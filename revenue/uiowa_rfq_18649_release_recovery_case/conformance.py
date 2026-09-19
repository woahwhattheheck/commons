#!/usr/bin/env python3
"""Execute the REAL sibling components on this kit's projections and compare.

WHY THIS EXISTS
---------------
UIOWA-109 landed asserting that its projections matched UIOWA-057's and
UIOWA-068's *field names*. They did. The semantics did not, and nobody noticed,
because matching a field list is not running a tool:

    UIOWA-068 measures RTO to BUSINESS-FUNCTION verification.
    This kit measured it to TECHNICAL RESTORE COMPLETION.

On the same events that is 65 minutes versus 50 minutes, and reporting the
technical number as RTO is exactly the conflation UIOWA-068 exists to prevent.
A kit whose whole job is detecting cross-component disagreement was carrying one
with the component it claimed to consume.

So this harness does the thing that would have caught it: it imports the sibling
modules from their real files, runs them on the projections, and compares the
outputs field by field. Nothing is mocked and no expected value is hard-coded --
the sibling's live behaviour is the expectation.

WHAT COUNTS AS A FAILURE
------------------------
* a numeric field that disagrees                      -> always a failure
* a status this kit reports as STRONGER than the      -> always a failure
  sibling's ("looser": claiming more than the
  component this kit defers to)
* a status this kit reports as WEAKER, where the      -> failure unless DECLARED
  difference is not in DECLARED_DIVERGENCES
* the sibling rejects a case this kit called AGREED   -> always a failure (a miss)

Being stricter than a sibling is allowed, because a conservative reading never
manufactures a claim. It still has to be written down. Being looser is never
allowed.

Offline, standard library only, reads the sibling lanes and writes nothing to
them. If a sibling lane is not present the harness reports NOT_RUN and exits 3 --
a skip that cannot be mistaken for a pass.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
import release_recovery_case as rrc  # noqa: E402  (path-relative by design)

PROVENANCE_LANE = os.path.join(HERE, os.pardir, "uiowa_rfq_18649_release_provenance")
RECOVERY_LANE = os.path.join(HERE, os.pardir, "uiowa_rfq_18649_recovery_evidence")

EXIT_CONFORMS, EXIT_DIVERGED, EXIT_ERROR, EXIT_NOT_RUN = 0, 1, 2, 3

# How strong a claim each status word makes. A comparison is only meaningful
# between words on the same ladder.
STRENGTH = {
    "EVIDENCED": 2, "NOT_APPLICABLE": 2, "DEMONSTRATED": 2,
    "PARTIAL": 1, "INCONSISTENT": 1,
    "UNKNOWN": 0, "NOT_EVIDENCED": 0, "NOT_DEMONSTRATED": 0,
}

# Fields compared numerically. These must agree exactly -- this is the class the
# RTO defect belonged to.
NUMERIC_FIELDS = ("observed_rpo_minutes", "observed_rto_minutes")

# Target comparisons are not a strength ladder -- a target is met or it is not,
# and "UNKNOWN" is a third distinct answer. These must match EXACTLY; treating
# them as a ladder would let a disagreement pass as "stricter".
EXACT_RESULT_FIELDS = ("rpo_result", "rto_result")

# Fields compared on the strength ladder.
STATUS_FIELDS = ("backup_status", "restoration_status",
                 "dependency_verification", "business_verification")

# A weaker status than the sibling's is permitted ONLY for these fields, only
# for the stated reason. Anything else is an undeclared divergence.
DECLARED_DIVERGENCES = {
    "backup_status":
        "UIOWA-068 treats any non-empty evidence id as evidenced. This kit also "
        "requires the id to RESOLVE in the shared evidence register and not to be "
        "interview-only (UIOWA-057's rule that interview evidence without artifact "
        "corroboration stays UNKNOWN). Stricter only: this kit may report PARTIAL "
        "where UIOWA-068 reports EVIDENCED, never the reverse.",
    "business_verification":
        "Same rule applied to the business-function verification source: the cited "
        "evidence must resolve and must not be interview-only. Stricter only.",
    "restoration_status":
        "Follows from the two above: a claim this kit holds down for want of usable "
        "evidence cannot then raise the restoration ladder. Stricter only.",
    "dependency_verification":
        "Same rule applied to each dependency verification source. Stricter only.",
}


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def siblings_available():
    return (os.path.isfile(os.path.join(PROVENANCE_LANE, "provenance.py"))
            and os.path.isfile(os.path.join(RECOVERY_LANE, "assess_recovery.py")))


def load_siblings():
    """Import the sibling tools from their real files. Nothing is vendored."""
    return (_load_module("_sibling_provenance",
                         os.path.join(PROVENANCE_LANE, "provenance.py")),
            _load_module("_sibling_recovery",
                         os.path.join(RECOVERY_LANE, "assess_recovery.py")))


def _num(value):
    return None if value is None else float(value)


def compare_recovery(mine, theirs, case_id):
    """Field-by-field comparison of this kit's recovery view against UIOWA-068's."""
    rows, problems = [], []
    theirs_by_id = {s["service_id"]: s for s in theirs["services"]}
    for svc in mine["recovery"]["services"]:
        sid = svc["service_id"]
        other = theirs_by_id.get(sid)
        if other is None:
            problems.append({
                "code": "SERVICE_MISSING_FROM_SIBLING", "case": case_id, "service": sid,
                "detail": f"{sid} is absent from the sibling's output entirely"})
            continue
        for field in NUMERIC_FIELDS:
            a, b = _num(svc.get(field)), _num(other.get(field))
            agree = a == b
            rows.append({"case": case_id, "service": sid, "field": field,
                         "mine": svc.get(field), "sibling": other.get(field),
                         "verdict": "AGREES" if agree else "NUMERIC_DISAGREEMENT"})
            if not agree:
                problems.append({
                    "code": "NUMERIC_DISAGREEMENT", "case": case_id, "service": sid,
                    "field": field,
                    "detail": f"this kit computes {svc.get(field)!r}, UIOWA-068 computes "
                              f"{other.get(field)!r} from the same records"})
        for field in EXACT_RESULT_FIELDS:
            a, b = svc.get(field), other.get(field)
            agree = a == b
            rows.append({"case": case_id, "service": sid, "field": field,
                         "mine": a, "sibling": b,
                         "verdict": "AGREES" if agree else "RESULT_DISAGREEMENT"})
            if not agree:
                problems.append({
                    "code": "RESULT_DISAGREEMENT", "case": case_id, "service": sid,
                    "field": field,
                    "detail": f"this kit reports {a!r} against the target, UIOWA-068 "
                              f"reports {b!r} from the same records"})
        for field in STATUS_FIELDS:
            a, b = svc.get(field), other.get(field)
            if a == b:
                rows.append({"case": case_id, "service": sid, "field": field,
                             "mine": a, "sibling": b, "verdict": "AGREES"})
                continue
            sa, sb = STRENGTH.get(a), STRENGTH.get(b)
            if sa is None or sb is None:
                verdict = "UNCOMPARABLE_VOCABULARY"
                problems.append({
                    "code": verdict, "case": case_id, "service": sid, "field": field,
                    "detail": f"{a!r} and {b!r} are not both on the strength ladder; the "
                              f"two kits are using different vocabularies for this field"})
            elif sa > sb:
                verdict = "LOOSER_THAN_SIBLING"
                problems.append({
                    "code": verdict, "case": case_id, "service": sid, "field": field,
                    "detail": f"this kit claims {a!r}, which is a STRONGER claim than "
                              f"UIOWA-068's {b!r}. Claiming more than the component this "
                              f"kit defers to is never permitted"})
            elif field in DECLARED_DIVERGENCES:
                verdict = "STRICTER_DECLARED"
            else:
                verdict = "UNDECLARED_DIVERGENCE"
                problems.append({
                    "code": verdict, "case": case_id, "service": sid, "field": field,
                    "detail": f"this kit reports {a!r} where UIOWA-068 reports {b!r}; the "
                              f"difference is conservative but is not declared in "
                              f"DECLARED_DIVERGENCES"})
            rows.append({"case": case_id, "service": sid, "field": field,
                         "mine": a, "sibling": b, "verdict": verdict})
    return rows, problems


def compare_provenance(mine, theirs, case_id):
    """This kit's chain verdict against UIOWA-057's own status."""
    rows, problems = [], []
    their_status = theirs.get("status")
    mine_linked = mine["provenance"]["linked"]
    mine_contradiction = any(
        f["class"] == "contradiction" and f["component"] == "provenance"
        for f in mine["findings"])
    rows.append({"case": case_id, "service": "-", "field": "provenance.status",
                 "mine": ("LINKED" if mine_linked else "NOT_LINKED")
                         + ("+CONTRADICTION" if mine_contradiction else ""),
                 "sibling": their_status,
                 "verdict": "AGREES"})
    if their_status == "CONTRADICTORY_RECORDS" and not mine_contradiction:
        rows[-1]["verdict"] = "MISSED_BY_THIS_KIT"
        problems.append({
            "code": "MISSED_BY_THIS_KIT", "case": case_id, "service": "-",
            "field": "provenance.status",
            "detail": "UIOWA-057 reports CONTRADICTORY_RECORDS on this packet and this "
                      "kit reports no provenance contradiction"})
    if mine_contradiction and their_status == "LINKED_RECORDS":
        rows[-1]["verdict"] = "LOOSER_THAN_SIBLING"
        problems.append({
            "code": "CONTRADICTS_A_LINKED_PACKET", "case": case_id, "service": "-",
            "field": "provenance.status",
            "detail": "this kit reports a provenance contradiction on a packet "
                      "UIOWA-057 reports as fully linked"})
    return rows, problems


def run_case(path, prov_mod, rec_mod):
    """Assess one case with this kit, then run both siblings on its projections."""
    case = rrc.load_case(path)
    report = rrc.assess(case)
    case_id = report["case_id"]
    rows, problems = [], []

    packet = rrc.project_provenance(case)
    try:
        their_prov = prov_mod.inspect(packet)
    except Exception as exc:  # the sibling validates; a rejection is information
        their_prov = None
        rows.append({"case": case_id, "service": "-", "field": "provenance.status",
                     "mine": report["status"], "sibling": f"REJECTED: {exc}",
                     "verdict": "SIBLING_REJECTED"})
        if report["status"] == "AGREED":
            problems.append({
                "code": "MISSED_BY_THIS_KIT", "case": case_id, "service": "-",
                "field": "provenance", "detail":
                    f"UIOWA-057 rejects this packet ({exc}) but this kit returned AGREED"})
    if their_prov is not None:
        r, p = compare_provenance(report, their_prov, case_id)
        rows += r
        problems += p

    records = rrc.project_recovery(case)
    try:
        their_rec = rec_mod.assess(records)
    except Exception as exc:
        rows.append({"case": case_id, "service": "-", "field": "recovery",
                     "mine": report["status"], "sibling": f"REJECTED: {exc}",
                     "verdict": "SIBLING_REJECTED"})
        if report["status"] == "AGREED":
            problems.append({
                "code": "MISSED_BY_THIS_KIT", "case": case_id, "service": "-",
                "field": "recovery", "detail":
                    f"UIOWA-068 rejects these records ({exc}) but this kit returned "
                    f"AGREED"})
    else:
        r, p = compare_recovery(report, their_rec, case_id)
        rows += r
        problems += p
    return rows, problems


def default_cases():
    cases = [os.path.join(HERE, "case.json")]
    fixtures = os.path.join(HERE, "fixtures")
    if os.path.isdir(fixtures):
        cases += [os.path.join(fixtures, n) for n in sorted(os.listdir(fixtures))
                  if n.endswith(".json")]
    return cases


def run(paths=None):
    if not siblings_available():
        return {"status": "NOT_RUN", "reason":
                "a sibling lane is not present next to this one "
                "(uiowa_rfq_18649_release_provenance / uiowa_rfq_18649_recovery_evidence); "
                "conformance cannot be established from here and is NOT assumed",
                "comparisons": [], "problems": [], "summary": {}}
    prov_mod, rec_mod = load_siblings()
    rows, problems = [], []
    for path in (paths or default_cases()):
        r, p = run_case(path, prov_mod, rec_mod)
        rows += r
        problems += p
    verdicts = {}
    for row in rows:
        verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
    return {
        "status": "DIVERGED" if problems else "CONFORMS",
        "comparisons": rows, "problems": problems,
        "summary": {"comparisons": len(rows), "problems": len(problems),
                    "verdicts": dict(sorted(verdicts.items())),
                    "declared_divergence_fields": sorted(DECLARED_DIVERGENCES)},
        "boundary": {
            "siblings_executed": True,
            "expected_values_hard_coded": False,
            "stricter_than_sibling_is_allowed": True,
            "looser_than_sibling_is_allowed": False,
        },
    }


def render(result):
    out = [f"# Sibling conformance — {result['status']}", ""]
    if result["status"] == "NOT_RUN":
        out += [result["reason"], ""]
        return "\n".join(out)
    s = result["summary"]
    out += [f"{s['comparisons']} field comparisons against the live sibling tools · "
            f"{s['problems']} problem(s)", "",
            "| Verdict | Count |", "|---|---|"]
    for verdict, count in s["verdicts"].items():
        out.append(f"| `{verdict}` | {count} |")
    out += ["", "Declared divergences (this kit is stricter, never looser): "
            + ", ".join(f"`{f}`" for f in s["declared_divergence_fields"]), ""]
    if result["problems"]:
        out += ["## Problems", "", "| Code | Case | Service | Field | Detail |",
                "|---|---|---|---|---|"]
        for p in result["problems"]:
            out.append(f"| `{p['code']}` | {p['case']} | {p.get('service','-')} | "
                       f"{p.get('field','-')} | {p['detail']} |")
    else:
        out.append("_No numeric disagreement, no looser claim, no undeclared "
                   "divergence and no sibling rejection this kit missed._")
    out.append("")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("cases", nargs="*", help="case files (default: case.json + fixtures/)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--json-output")
    args = parser.parse_args(argv)
    try:
        result = run(args.cases or None)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)
            fh.write("\n")
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render(result))
    if result["status"] == "NOT_RUN":
        return EXIT_NOT_RUN
    return EXIT_DIVERGED if result["problems"] else EXIT_CONFORMS


if __name__ == "__main__":
    sys.exit(main())
