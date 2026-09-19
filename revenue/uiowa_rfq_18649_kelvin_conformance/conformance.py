#!/usr/bin/env python3
"""Run this seat's projected rows through the evidence register's OWN validator.

Run:
    python3 conformance.py --revenue-root .. --outdir out

Exit codes: 0 conformant · 1 rejected or undeclared divergence ·
2 bad input · 3 could not verify (a sibling lane is absent).

The point is that the claim "these lanes join to the register" is settled by
executing the register's validator, not by matching field names. A sibling
that is absent produces SKIPPED with a stated reason -- never a pass.

This module reads sibling lanes and writes only into its own output
directory. It does not modify any other lane.
"""

import argparse
import csv
import json
import os
import subprocess
import sys

import project

VALIDATOR_REL = os.path.join(
    "uiowa_rfq_18649_workshare", "methodology", "validate_23_evidence_register.py"
)

# Source values that mean "this is not evidenced". None of them may project to
# a SUPPORTING state -- that would make the projection more favourable than
# the record it came from.
UNSUPPORTED_SOURCE_VALUES = {
    "inventory": ("PLANNED_USE", "UNSUPPORTED_CLAIM", "UNKNOWN"),
    "continuity": ("ASSUMED", "UNKNOWN"),
    "transition": ("NO_EVIDENCE",),
}

MAPPINGS = {
    "inventory": project.INVENTORY_STATE,
    "continuity": project.ASSUMPTION_STATE,
    "transition": project.TRANSITION_STATE,
}


def load_declared(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def undeclared_collapses(declared):
    """Every pair of distinct source values landing on the same register
    target must be covered by a declared divergence."""
    covered = set()
    for d in declared["declared"]:
        target = tuple(d["register_target"])
        for value in d["source_values"]:
            covered.add((value, target))

    problems = []
    for table_name, table in sorted(MAPPINGS.items()):
        by_target = {}
        for source_value, target in sorted(table.items()):
            by_target.setdefault(tuple(target), []).append(source_value)
        for target, values in sorted(by_target.items()):
            if len(values) < 2:
                continue
            for value in values:
                if (value, target) not in covered:
                    problems.append({
                        "table": table_name,
                        "source_value": value,
                        "register_target": list(target),
                        "shares_target_with": [v for v in values if v != value],
                        "detail": "collapses onto a shared register state with no declared divergence",
                    })
    return problems


def favourability_problems():
    """A projection must never read stronger than its source."""
    problems = []
    for table_name, table in sorted(MAPPINGS.items()):
        for source_value in UNSUPPORTED_SOURCE_VALUES[table_name]:
            state, confidence = table[source_value]
            if state == "SUPPORTING" or confidence in ("HIGH", "MODERATE"):
                problems.append({
                    "table": table_name,
                    "source_value": source_value,
                    "register_target": [state, confidence],
                    "detail": "an unevidenced source value projects to a supporting register state",
                })
    return problems


def write_register_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=project.REGISTER_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def run_validator(validator_path, csv_path):
    proc = subprocess.run(
        [sys.executable, validator_path, csv_path],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def render_markdown(result):
    lines = []
    lines.append("# Conformance: seat lanes projected into the UIOWA-023 register")
    lines.append("")
    lines.append("The claim that lanes 071, 107 and 108 join to the evidence register was")
    lines.append("made by matching field names and id shapes. This settles it by running")
    lines.append("the register's own validator over the projected rows.")
    lines.append("")
    lines.append("All source records are fictional rehearsal records. The projection")
    lines.append("carries that forward and does not launder them into evidence.")
    lines.append("")
    lines.append("## Result: `%s`" % result["status"])
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | ---: |")
    lines.append("| Rows projected | %d |" % result["rows"])
    lines.append("| Rows skipped | %d |" % len(result["skipped"]))
    lines.append("| Sibling lanes absent | %d |" % len(result["absent"]))
    lines.append("| Declared divergences | %d |" % result["declared_count"])
    lines.append("| Undeclared divergences | %d |" % len(result["undeclared"]))
    lines.append("")
    lines.append("### Validator output, verbatim")
    lines.append("")
    lines.append("```")
    lines.append("$ python3 %s %s" % (result["validator"], result["csv"]))
    lines.append("exit=%s" % result["validator_exit"])
    if result["validator_stdout"]:
        lines.append(result["validator_stdout"])
    if result["validator_stderr"]:
        lines.append(result["validator_stderr"])
    lines.append("```")
    lines.append("")
    lines.append("### Rows by register state")
    lines.append("")
    lines.append("| Order | evidence_state | confidence | Rows |")
    lines.append("| --- | --- | --- | ---: |")
    for key in sorted(result["by_state"]):
        order, state, confidence = key.split("|")
        lines.append("| %s | %s | %s | %d |" % (order, state, confidence, result["by_state"][key]))
    lines.append("")
    lines.append("## Declared divergences")
    lines.append("")
    for d in result["declared"]:
        lines.append("**%s** (%s) — `%s` → `%s`"
                     % (d["id"], d["order"], "`, `".join(d["source_values"]),
                        " / ".join(d["register_target"])))
        lines.append("")
        lines.append("- %s" % d["why"])
        lines.append("- Preserved as: %s" % d["preserved_as"])
        lines.append("- Direction: %s" % d["direction"])
        lines.append("")
    lines.append("## Distinctions that survived the projection")
    lines.append("")
    for s in result["survivals"]:
        lines.append("- **%s** (%s) — %s" % (s["id"], s["order"], s["why"]))
    lines.append("")
    if result["undeclared"]:
        lines.append("## Undeclared divergences")
        lines.append("")
        for u in result["undeclared"]:
            lines.append("- `%s` %s → %s (shares with %s): %s"
                         % (u["table"], u["source_value"], u["register_target"],
                            ", ".join(u["shares_target_with"]), u["detail"]))
        lines.append("")
    if result["skipped"]:
        lines.append("## Rows skipped")
        lines.append("")
        for s in result["skipped"]:
            lines.append("- `%s` (%s): %s" % (s["id"], s.get("order", "?"), s["reason"]))
        lines.append("")
    if result["absent"]:
        lines.append("## Sibling lanes absent — NOT VERIFIED")
        lines.append("")
        for a in result["absent"]:
            lines.append("- `%s` (%s): %s" % (a["lane"], a["order"], a["reason"]))
        lines.append("")
    lines.append("## Limits")
    lines.append("")
    lines.append("- A passing validator run proves the rows are structurally admissible")
    lines.append("  to the register. It does not prove the mapping is the one the")
    lines.append("  assessment team would choose.")
    lines.append("- Only the register is exercised here. The UIOWA-091 collection")
    lines.append("  validator is not run, so compatibility with that collection remains")
    lines.append("  asserted rather than demonstrated.")
    lines.append("")
    return "\n".join(lines)


def build(revenue_root, declared_path):
    declared = load_declared(declared_path)
    rows, skipped, absent = project.project_all(revenue_root)
    undeclared = undeclared_collapses(declared) + favourability_problems()

    by_state = {}
    for row in rows:
        key = "%s|%s|%s" % (row.get("_order", "?"), row["evidence_state"], row["confidence"])
        by_state[key] = by_state.get(key, 0) + 1

    return {
        "rows": len(rows),
        "row_data": rows,
        "skipped": skipped,
        "absent": absent,
        "undeclared": undeclared,
        "declared": declared["declared"],
        "declared_count": len(declared["declared"]),
        "survivals": declared["verified_survivals"],
        "by_state": by_state,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Run projected rows through the register validator.")
    p.add_argument("--revenue-root", required=True)
    p.add_argument("--outdir", default="out")
    p.add_argument("--print", dest="do_print", action="store_true")
    args = p.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    declared_path = os.path.join(here, "divergences.json")
    if not os.path.isdir(args.revenue_root):
        sys.stderr.write("error: not a directory: %s\n" % args.revenue_root)
        return 2

    result = build(args.revenue_root, declared_path)

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "projected_register.csv")
    write_register_csv(result["row_data"], csv_path)

    validator = os.path.join(args.revenue_root, VALIDATOR_REL)
    if not os.path.exists(validator):
        result.update({"status": "SKIPPED_VALIDATOR_ABSENT", "validator": VALIDATOR_REL,
                       "csv": csv_path, "validator_exit": "n/a",
                       "validator_stdout": "", "validator_stderr":
                       "the register validator is not present; conformance is NOT verified"})
        exit_code = 3
    else:
        code, out, err = run_validator(validator, csv_path)
        result.update({"validator": os.path.relpath(validator, args.revenue_root),
                       "csv": csv_path, "validator_exit": code,
                       "validator_stdout": out, "validator_stderr": err})
        if code != 0:
            result["status"] = "REJECTED_BY_REGISTER"
            exit_code = 1
        elif result["undeclared"]:
            result["status"] = "UNDECLARED_DIVERGENCE"
            exit_code = 1
        elif result["absent"]:
            result["status"] = "PARTIAL_SIBLING_ABSENT"
            exit_code = 3
        else:
            result["status"] = "CONFORMANT"
            exit_code = 0

    report = render_markdown(result)
    with open(os.path.join(args.outdir, "conformance.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    payload = dict(result)
    payload.pop("row_data", None)
    with open(os.path.join(args.outdir, "conformance.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)

    if args.do_print:
        sys.stdout.write(report)
    sys.stderr.write("status=%s rows=%d skipped=%d absent=%d undeclared=%d validator_exit=%s\n"
                     % (result["status"], result["rows"], len(result["skipped"]),
                        len(result["absent"]), len(result["undeclared"]),
                        result["validator_exit"]))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
