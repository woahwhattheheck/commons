"""Compile the leadership executive summary. Run: python3 build_summary.py

Deterministic and offline: same inputs -> byte-identical outputs. Exits non-zero when
a SIGNIFICANT or CRITICAL finding is assertable and no statement cites it, because a
dropped serious finding is the failure this tool exists to make visible.
"""

import json
import os
import sys

import kit_status
from findings import load_findings
from render import (
    render_compile_report,
    render_executive_summary,
    render_traceability_matrix_csv,
)
from summary import compile_summary, load_document

OUT = "out"


def _write(name, text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path, len(text)


def _jsonable(result):
    return {
        "title": result["title"], "source_label": result["source_label"],
        "stats": result["stats"],
        "accepted": {sid: {"text": entry["statement"].text,
                           "cites": list(entry["statement"].cites),
                           "claimed_strength": entry["claimed_strength"],
                           "supported_strength": entry["supported_strength"]}
                     for sid, entry in result["accepted"].items()},
        "rejected": result["rejected"],
        "uncited_findings": [{"finding_id": f.finding_id, "severity": f.severity,
                              "max_strength": f.max_strength,
                              "scope": f.scope_label, "title": f.title}
                             for f in result["uncited_findings"]],
        "unresolved": result["unresolved"],
        "sections": result["sections"],
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    store, rejected_findings, _raw = load_findings(os.path.join("data", "findings.json"))
    document = load_document(os.path.join("data", "draft_statements.json"))
    result = compile_summary(document, store)

    written = [
        _write("executive_summary.md", render_executive_summary(result)),
        _write("traceability_matrix.csv", render_traceability_matrix_csv(result)),
        _write("compile_report.md", render_compile_report(result, rejected_findings)),
        _write("compile_result.json",
               json.dumps({"result": _jsonable(result),
                           "findings_rejected_at_load": rejected_findings},
                          indent=2, sort_keys=True) + "\n"),
    ]

    print("UIOWA-081 executive summary compiled into out/")
    for path, size in written:
        print(f"  {path:<40} {size:>6} bytes")

    stats = result["stats"]
    print(f"\nStatements: {stats['statements_accepted']} accepted, "
          f"{stats['statements_rejected']} rejected, of "
          f"{stats['statements_submitted']} drafted")
    for item in result["rejected"]:
        codes = ", ".join(problem["code"] for problem in item["problems"])
        print(f"  REJECT {item['statement_id']:<6} {codes}")
    if rejected_findings:
        print(f"\nFindings rejected at load: "
              f"{', '.join(f['raw_id'] for f in rejected_findings)}")

    droppable = [f for f in result["uncited_findings"]
                 if f.max_strength != "NOT_ESTABLISHED"]
    serious = [f for f in droppable if f.severity in ("SIGNIFICANT", "CRITICAL")]
    print(f"\nCoverage: {stats['findings_cited']}/{stats['findings_total']} findings "
          f"cited by an accepted statement")
    for finding in result["uncited_findings"]:
        note = ("NOT ASSERTABLE - belongs in open questions"
                if finding.max_strength == "NOT_ESTABLISHED"
                else "ASSERTABLE BUT UNCITED")
        print(f"  {finding.finding_id} ({finding.severity}) {note}")

    if serious:
        print(f"\nFAIL: {len(serious)} assertable "
              f"SIGNIFICANT/CRITICAL finding(s) are missing from the summary: "
              f"{', '.join(f.finding_id for f in serious)}")

    # Signal the result instead of leaving it in stdout. Rejected statements, a
    # dropped serious finding and a malformed finding record all need action.
    # A finding that is NOT_ESTABLISHED is unresolved evidence, not a clean result.
    findings = (len(result["rejected"]) + len(serious) + len(rejected_findings))
    unresolved = sum(1 for finding in store.all()
                     if finding.max_strength == "NOT_ESTABLISHED")
    return kit_status.emit("build_summary", findings=findings,
                           indeterminate=unresolved,
                           note=f"{stats['statements_rejected']} statement(s) rejected, "
                                f"{len(serious)} serious finding(s) missing, "
                                f"{unresolved} not-established finding(s)")


if __name__ == "__main__":
    sys.exit(main())
