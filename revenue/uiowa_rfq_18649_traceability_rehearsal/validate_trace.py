#!/usr/bin/env python3
"""Structural link check for the synthetic UIOWA-093 bundle."""

import csv
import sys
from pathlib import Path


def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split_ids(value):
    return {x.strip() for x in (value or "").replace(",", ";").split(";") if x.strip()}


def main(root):
    evidence = load(root / "evidence.csv")
    findings = load(root / "findings.csv")
    recommendations = load(root / "recommendations.csv")
    trace = load(root / "trace-map.csv")

    eids = {r["evidence_id"] for r in evidence}
    fids = {r["finding_id"] for r in findings}
    rids = {r["recommendation_id"] for r in recommendations}
    sids = {r["statement_id"] for r in trace}
    errors = []

    for row in findings:
        if not split_ids(row["evidence_ids"]) <= eids:
            errors.append(row["finding_id"] + " has a broken evidence link")

    for row in recommendations:
        if not split_ids(row["linked_findings"]) <= fids:
            errors.append(row["recommendation_id"] + " has a broken finding link")

    for row in trace:
        if not split_ids(row["finding_ids"]) <= fids:
            errors.append(row["statement_id"] + " has a broken finding link")
        if not split_ids(row["recommendation_ids"]) <= rids:
            errors.append(row["statement_id"] + " has a broken recommendation link")
        if not split_ids(row["evidence_ids"]) <= eids:
            errors.append(row["statement_id"] + " has a broken evidence link")

    report = (root / "executive-summary.md").read_text(encoding="utf-8")
    report += (root / "final-report.md").read_text(encoding="utf-8")
    for sid in sids:
        if sid not in report:
            errors.append(sid + " is absent from report text")

    if errors:
        print("\n".join(errors))
        return 1

    print(f"evidence={len(evidence)} findings={len(findings)} recommendations={len(recommendations)} statements={len(trace)}")
    print("trace validation: PASS")
    return 0


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    raise SystemExit(main(folder))
