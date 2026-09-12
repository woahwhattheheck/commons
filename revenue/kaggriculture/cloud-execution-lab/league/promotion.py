# SPDX-License-Identifier: Apache-2.0
"""Order-invariant, fail-closed matched-cell promotion gate for TITAN leagues."""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from promotion_audit import audit_promotion
from promotion_model import (
    FIELD_SCHEMA,
    SCHEMA,
    CellKey,
    PromotionData,
    PromotionPolicy,
    _name,
    expected_keys_from_plan,
)


def audit_field(
    rows: Sequence[Mapping[str, Any]], reference: str, *, challengers: Iterable[str] | None = None,
    expected_keys: set[CellKey] | None = None,
    policy: PromotionPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select canonical unless a challenger safely dominates on the matched grid."""
    reference = _name(reference, "reference")
    present = {_name(row.get("contestant"), f"row {index} contestant") for index, row in enumerate(rows)}
    if reference not in present:
        raise PromotionData(f"reference {reference!r} is absent")
    challengers = sorted(set(challengers) if challengers is not None else present - {reference})
    if not challengers or reference in challengers or set(challengers) - present:
        raise PromotionData("challenger set is empty, contains reference, or is absent from evidence")
    audits = [
        audit_promotion(rows, reference, name, expected_keys=expected_keys, policy=policy)
        for name in challengers
    ]
    eligible = [audit for audit in audits if audit["eligible"]]
    eligible.sort(key=lambda audit: (
        -audit["metrics"]["mean_own_cash_delta"],
        -audit["metrics"]["mean_margin_delta"],
        -audit["metrics"]["min_own_cash_delta"],
        audit["challenger"],
    ))
    selected = eligible[0]["challenger"] if eligible else reference
    return {
        "schema": FIELD_SCHEMA, "reference": reference, "selected": selected,
        "promotion": selected != reference, "audits": audits,
    }


def _audit_markdown(audit: Mapping[str, Any]) -> list[str]:
    coverage, metrics = audit["coverage"], audit.get("metrics")
    lines = [
        f"## {audit['challenger']} vs {audit['reference']}", "",
        f"- Verdict: **{audit['verdict']}**",
        f"- Coverage: {coverage['paired_cells']}/{coverage['expected_cells']} paired; exact={coverage['complete']}",
    ]
    if metrics:
        worst = metrics["worst_own_cash_cell"]
        lines += [
            f"- Mean own-cash delta: {metrics['mean_own_cash_delta']:+.3f}",
            f"- Mean margin delta: {metrics['mean_margin_delta']:+.3f}",
            f"- Cells: +{metrics['positive_cells']} / ={metrics['tie_cells']} / -{metrics['negative_cells']}",
            f"- Worst own-cash cell: {worst['own_cash_delta']:+.3f} at {worst['opponent']} / seed {worst['seed']} / seat {worst['candidate_seat']}",
        ]
    if audit["reasons"]:
        lines.append("- Rejection reasons: " + ", ".join(reason["kind"] for reason in audit["reasons"]))
    return [*lines, ""]


def promotion_to_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact review receipt."""
    if report.get("schema") == FIELD_SCHEMA:
        lines = [
            "# Paired promotion verdict", "",
            f"- Reference: `{report['reference']}`", f"- Selected: `{report['selected']}`",
            f"- Promotion: `{'YES' if report['promotion'] else 'NO'}`", "",
        ]
        for audit in report["audits"]:
            lines.extend(_audit_markdown(audit))
        return "\n".join(lines).rstrip() + "\n"
    if report.get("schema") == SCHEMA:
        return "\n".join(["# Paired promotion verdict", "", *_audit_markdown(report)]).rstrip() + "\n"
    raise PromotionData(f"unsupported report schema: {report.get('schema')!r}")


def _load(path: str, *, jsonl: bool = False) -> Any:
    try:
        text = Path(path).read_text()
        if not jsonl:
            return json.loads(text)
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not rows or not all(isinstance(row, dict) for row in rows):
            raise PromotionData(f"{path}: JSONL must contain object rows")
        return rows
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionData(f"cannot load {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--challenger", action="append")
    parser.add_argument("--policy")
    parser.add_argument("--json-out")
    parser.add_argument("--markdown-out")
    args = parser.parse_args(argv)
    plan = _load(args.plan)
    if not isinstance(plan, dict):
        raise PromotionData("plan must be a JSON object")
    policy = _load(args.policy) if args.policy else None
    if policy is not None and not isinstance(policy, dict):
        raise PromotionData("policy must be a JSON object")
    report = audit_field(
        _load(args.games, jsonl=True), args.reference,
        challengers=args.challenger, expected_keys=expected_keys_from_plan(plan), policy=policy,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    markdown = promotion_to_markdown(report)
    if args.json_out:
        Path(args.json_out).write_text(rendered)
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown)
    print(rendered, end="")
    return 0 if report["promotion"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
