#!/usr/bin/env python3
"""Validate and report UIOWA-087 recommendation-linked outcome measures.

The tool reports directional measurement evidence. It never attributes causality,
combines adoption and outcome into an effectiveness score, or rates individuals.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


MEASURE_CLASSES = {"adoption", "outcome"}
DIRECTIONS = {"higher_better", "lower_better", "context_only"}
PERIOD_ROLES = {"baseline", "followup"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    key: str = ""


@dataclass(frozen=True)
class Comparison:
    measure_id: str
    recommendation_id: str
    assessment_area: str
    measure_class: str
    measure_name: str
    baseline_rate_pct: float | None
    followup_rate_pct: float | None
    absolute_change_pp: float | None
    comparability: str
    directional_signal: str
    baseline_evidence: str
    followup_evidence: str
    collection_effort_minutes: int | None
    interpretation_limit: str


def read_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_nonnegative_int(raw: str, *, field: str, key: str, findings: list[Finding]) -> int | None:
    text = (raw or "").strip()
    if not text:
        findings.append(Finding("ERROR", "MISSING_COUNT", f"{field} is missing", key))
        return None
    try:
        value = int(text)
    except ValueError:
        findings.append(Finding("ERROR", "INVALID_COUNT", f"{field} must be an integer", key))
        return None
    if value < 0:
        findings.append(Finding("ERROR", "NEGATIVE_COUNT", f"{field} must be nonnegative", key))
        return None
    return value


def parse_effort(raw: str, key: str, findings: list[Finding]) -> int | None:
    text = (raw or "").strip()
    if not text:
        findings.append(Finding("WARNING", "EFFORT_UNKNOWN", "Collection effort is not estimated", key))
        return None
    try:
        value = int(text)
    except ValueError:
        findings.append(Finding("ERROR", "INVALID_EFFORT", "Collection effort must be an integer minute estimate", key))
        return None
    if value < 0:
        findings.append(Finding("ERROR", "INVALID_EFFORT", "Collection effort cannot be negative", key))
        return None
    return value


def unique_by(rows: list[dict[str, str]], key_name: str, findings: list[Finding]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows, start=2):
        key = (row.get(key_name) or "").strip()
        if not key:
            findings.append(Finding("ERROR", "MISSING_ID", f"{key_name} missing at CSV line {index}"))
            continue
        if key in result:
            findings.append(Finding("ERROR", "DUPLICATE_ID", f"Duplicate {key_name}: {key}", key))
            continue
        result[key] = row
    return result


def required(row: dict[str, str], fields: tuple[str, ...], key: str, findings: list[Finding]) -> None:
    for field in fields:
        if not (row.get(field) or "").strip():
            findings.append(Finding("ERROR", "MISSING_FIELD", f"{field} is required", key))


def validate_and_compare(
    recommendations: list[dict[str, str]],
    register: list[dict[str, str]],
    observations: list[dict[str, str]],
) -> tuple[list[Finding], list[Comparison]]:
    findings: list[Finding] = []
    recs = unique_by(recommendations, "recommendation_id", findings)
    measures = unique_by(register, "measure_id", findings)

    for rec_id, row in recs.items():
        required(row, ("assessment_area", "title", "intended_change"), rec_id, findings)

    for measure_id, row in measures.items():
        required(
            row,
            (
                "recommendation_id",
                "assessment_area",
                "measure_class",
                "measure_name",
                "numerator_definition",
                "denominator_definition",
                "unit",
                "direction",
                "evidence_source",
                "collection_cadence",
                "interpretation_limit",
            ),
            measure_id,
            findings,
        )
        rec_id = (row.get("recommendation_id") or "").strip()
        if rec_id and rec_id not in recs:
            findings.append(Finding("ERROR", "BROKEN_RECOMMENDATION_LINK", f"Unknown recommendation {rec_id}", measure_id))
        cls = (row.get("measure_class") or "").strip()
        if cls and cls not in MEASURE_CLASSES:
            findings.append(Finding("ERROR", "INVALID_MEASURE_CLASS", f"Expected one of {sorted(MEASURE_CLASSES)}", measure_id))
        direction = (row.get("direction") or "").strip()
        if direction and direction not in DIRECTIONS:
            findings.append(Finding("ERROR", "INVALID_DIRECTION", f"Expected one of {sorted(DIRECTIONS)}", measure_id))
        parse_effort(row.get("estimated_minutes_per_cycle", ""), measure_id, findings)

    grouped: dict[str, dict[str, dict[str, str]]] = {}
    seen_period_keys: set[tuple[str, str]] = set()
    for line_number, row in enumerate(observations, start=2):
        measure_id = (row.get("measure_id") or "").strip()
        role = (row.get("period_role") or "").strip()
        key = f"{measure_id}:{role or '?'}"
        required(
            row,
            ("measure_id", "period_id", "period_role", "numerator", "denominator", "population_definition", "evidence_locator"),
            key,
            findings,
        )
        if measure_id not in measures:
            findings.append(Finding("ERROR", "UNKNOWN_MEASURE", f"Observation references unknown measure {measure_id}", key))
            continue
        if role not in PERIOD_ROLES:
            findings.append(Finding("ERROR", "INVALID_PERIOD_ROLE", f"Expected baseline or followup at line {line_number}", key))
            continue
        period_key = (measure_id, role)
        if period_key in seen_period_keys:
            findings.append(Finding("ERROR", "DUPLICATE_PERIOD_ROLE", f"Duplicate {role} row for {measure_id}", key))
            continue
        seen_period_keys.add(period_key)
        grouped.setdefault(measure_id, {})[role] = row

    comparisons: list[Comparison] = []
    for measure_id, measure in measures.items():
        pair = grouped.get(measure_id, {})
        baseline = pair.get("baseline")
        followup = pair.get("followup")

        if baseline is None:
            findings.append(Finding("WARNING", "BASELINE_MISSING", "No baseline observation", measure_id))
        if followup is None:
            findings.append(Finding("WARNING", "FOLLOWUP_MISSING", "No follow-up observation", measure_id))

        b_rate = f_rate = change = None
        comparability = "INSUFFICIENT_DATA"
        signal = "INSUFFICIENT_DATA"
        b_evidence = (baseline or {}).get("evidence_locator", "")
        f_evidence = (followup or {}).get("evidence_locator", "")

        if baseline is not None and followup is not None:
            b_num = parse_nonnegative_int(baseline.get("numerator", ""), field="baseline numerator", key=measure_id, findings=findings)
            b_den = parse_nonnegative_int(baseline.get("denominator", ""), field="baseline denominator", key=measure_id, findings=findings)
            f_num = parse_nonnegative_int(followup.get("numerator", ""), field="followup numerator", key=measure_id, findings=findings)
            f_den = parse_nonnegative_int(followup.get("denominator", ""), field="followup denominator", key=measure_id, findings=findings)

            if b_den == 0:
                findings.append(Finding("ERROR", "ZERO_DENOMINATOR", "Baseline denominator cannot be zero", measure_id))
            if f_den == 0:
                findings.append(Finding("ERROR", "ZERO_DENOMINATOR", "Follow-up denominator cannot be zero", measure_id))
            if b_num is not None and b_den not in (None, 0) and b_num > b_den:
                findings.append(Finding("ERROR", "NUMERATOR_EXCEEDS_DENOMINATOR", "Baseline numerator exceeds denominator", measure_id))
            if f_num is not None and f_den not in (None, 0) and f_num > f_den:
                findings.append(Finding("ERROR", "NUMERATOR_EXCEEDS_DENOMINATOR", "Follow-up numerator exceeds denominator", measure_id))

            same_population = (
                (baseline.get("population_definition") or "").strip()
                == (followup.get("population_definition") or "").strip()
            )
            if not same_population:
                comparability = "NOT_COMPARABLE"
                findings.append(
                    Finding(
                        "WARNING",
                        "POPULATION_CHANGED",
                        "Baseline and follow-up population definitions differ; direct rate comparison is suppressed",
                        measure_id,
                    )
                )
            elif None not in (b_num, b_den, f_num, f_den) and b_den and f_den and b_num <= b_den and f_num <= f_den:
                comparability = "COMPARABLE"
                b_rate = 100.0 * b_num / b_den
                f_rate = 100.0 * f_num / f_den
                change = f_rate - b_rate
                direction = (measure.get("direction") or "").strip()
                if math.isclose(b_rate, f_rate, rel_tol=0.0, abs_tol=1e-12):
                    signal = "UNCHANGED"
                elif direction == "higher_better":
                    signal = "FAVORABLE_DIRECTION" if f_rate > b_rate else "UNFAVORABLE_DIRECTION"
                elif direction == "lower_better":
                    signal = "FAVORABLE_DIRECTION" if f_rate < b_rate else "UNFAVORABLE_DIRECTION"
                else:
                    signal = "CONTEXT_ONLY"

        comparisons.append(
            Comparison(
                measure_id=measure_id,
                recommendation_id=(measure.get("recommendation_id") or "").strip(),
                assessment_area=(measure.get("assessment_area") or "").strip(),
                measure_class=(measure.get("measure_class") or "").strip(),
                measure_name=(measure.get("measure_name") or "").strip(),
                baseline_rate_pct=b_rate,
                followup_rate_pct=f_rate,
                absolute_change_pp=change,
                comparability=comparability,
                directional_signal=signal,
                baseline_evidence=b_evidence,
                followup_evidence=f_evidence,
                collection_effort_minutes=parse_effort(
                    measure.get("estimated_minutes_per_cycle", ""),
                    measure_id,
                    [],
                ),
                interpretation_limit=(measure.get("interpretation_limit") or "").strip(),
            )
        )

    by_rec: dict[str, set[str]] = {}
    for measure in measures.values():
        by_rec.setdefault((measure.get("recommendation_id") or "").strip(), set()).add(
            (measure.get("measure_class") or "").strip()
        )
    for rec_id in recs:
        classes = by_rec.get(rec_id, set())
        if "adoption" not in classes:
            findings.append(Finding("WARNING", "ADOPTION_MEASURE_MISSING", "Recommendation has no adoption measure", rec_id))
        if "outcome" not in classes:
            findings.append(Finding("WARNING", "OUTCOME_MEASURE_MISSING", "Recommendation has no operational outcome measure", rec_id))

    return findings, comparisons


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}%"


def _fmt_pp(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f} pp"


def render_markdown(
    recommendations: list[dict[str, str]],
    comparisons: list[Comparison],
    findings: list[Finding],
) -> str:
    rec_map = {row["recommendation_id"]: row for row in recommendations if row.get("recommendation_id")}
    out = [
        "# Synthetic improvement outcome-measurement report",
        "",
        "> Directional measurement evidence only. This report does not establish causality, release approval, maturity, compliance, or individual performance.",
        "",
    ]

    grouped: dict[str, list[Comparison]] = {}
    for comparison in comparisons:
        grouped.setdefault(comparison.recommendation_id, []).append(comparison)

    for rec_id, rows in grouped.items():
        rec = rec_map.get(rec_id, {})
        out.extend(
            [
                f"## {rec_id} — {rec.get('title', 'Unknown recommendation')}",
                "",
                f"**Intended change:** {rec.get('intended_change', '')}",
                "",
                "| Class | Measure | Baseline | Follow-up | Change | Comparability | Directional signal | Effort/cycle |",
                "| --- | --- | ---: | ---: | ---: | --- | --- | ---: |",
            ]
        )
        for row in sorted(rows, key=lambda r: (r.measure_class, r.measure_id)):
            effort = "—" if row.collection_effort_minutes is None else f"{row.collection_effort_minutes} min"
            out.append(
                f"| {row.measure_class} | {row.measure_id}: {row.measure_name} | "
                f"{_fmt(row.baseline_rate_pct)} | {_fmt(row.followup_rate_pct)} | "
                f"{_fmt_pp(row.absolute_change_pp)} | {row.comparability} | "
                f"{row.directional_signal} | {effort} |"
            )
        out.extend(["", "### Interpretation limits", ""])
        for row in sorted(rows, key=lambda r: r.measure_id):
            out.append(f"- **{row.measure_id}:** {row.interpretation_limit}")
        out.append("")

    out.extend(["## Validation findings", ""])
    if findings:
        for finding in findings:
            key = f" [{finding.key}]" if finding.key else ""
            out.append(f"- **{finding.level} {finding.code}**{key}: {finding.message}")
    else:
        out.append("- No structural or comparability findings.")

    out.extend(
        [
            "",
            "## Reading rule",
            "",
            "Adoption and outcome rows are intentionally not averaged into a single effectiveness score. "
            "Favorable movement in both classes is useful evidence for follow-up discussion, but still does not establish that the recommendation caused the outcome change.",
            "",
        ]
    )
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "report"):
        p = sub.add_parser(command)
        p.add_argument("--recommendations", required=True)
        p.add_argument("--register", required=True)
        p.add_argument("--measurements", required=True)
        if command == "validate":
            p.add_argument("--json", action="store_true", dest="json_output")
        else:
            p.add_argument("-o", "--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    recs = read_csv(args.recommendations)
    register = read_csv(args.register)
    observations = read_csv(args.measurements)
    findings, comparisons = validate_and_compare(recs, register, observations)

    if args.command == "validate":
        if args.json_output:
            print(
                json.dumps(
                    {
                        "findings": [asdict(f) for f in findings],
                        "comparisons": [asdict(c) for c in comparisons],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            for finding in findings:
                key = f" [{finding.key}]" if finding.key else ""
                print(f"{finding.level} {finding.code}{key}: {finding.message}")
            print(f"comparisons={len(comparisons)} errors={sum(f.level == 'ERROR' for f in findings)}")
    else:
        report = render_markdown(recs, comparisons, findings)
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
        else:
            print(report)

    return 2 if any(f.level == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
