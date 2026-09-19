#!/usr/bin/env python3
"""Transparent recommendation prioritization for UIOWA-084.

Scores are synthetic planning inputs, not University findings.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

DIMENSIONS = ("quality", "security", "delivery")
REQUIRED_INPUT_COLUMNS = (
    "id", "title", "quality", "security", "delivery", "complexity",
    "confidence", "owner_role", "dependencies", "assumptions",
)
SCORE_MIN = 0.0
SCORE_MAX = 5.0


def _parse_optional_number(value: str) -> Optional[float]:
    text = (value or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"not a number: {value!r}") from exc


def _validate_range(name: str, value: Optional[float], lo: float, hi: float) -> None:
    if value is not None and not (lo <= value <= hi):
        raise ValueError(f"{name} must be between {lo} and {hi}; got {value}")


def validate_weights(config: dict) -> None:
    if "profiles" not in config or not isinstance(config["profiles"], dict) or not config["profiles"]:
        raise ValueError("weights config must contain a non-empty 'profiles' object")
    epsilon = float(config.get("tie_epsilon", 0.0))
    if epsilon < 0:
        raise ValueError("tie_epsilon must be >= 0")
    for profile_name, weights in config["profiles"].items():
        missing = [d for d in (*DIMENSIONS, "complexity") if d not in weights]
        if missing:
            raise ValueError(f"profile {profile_name!r} is missing weights: {', '.join(missing)}")
        benefit_sum = sum(float(weights[d]) for d in DIMENSIONS)
        if abs(benefit_sum - 1.0) > 1e-9:
            raise ValueError(
                f"profile {profile_name!r} benefit weights must sum to 1.0; got {benefit_sum}"
            )
        for d in DIMENSIONS:
            if float(weights[d]) < 0:
                raise ValueError(f"profile {profile_name!r} weight {d} must be >= 0")
        if float(weights["complexity"]) < 0:
            raise ValueError(f"profile {profile_name!r} complexity weight must be >= 0")


def load_weights(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        config = json.load(fh)
    validate_weights(config)
    return config


def load_recommendations(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("recommendation CSV has no header")
        missing_cols = [c for c in REQUIRED_INPUT_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            raise ValueError("recommendation CSV missing columns: " + ", ".join(missing_cols))
        records: List[dict] = []
        seen: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            rec_id = (row["id"] or "").strip()
            title = (row["title"] or "").strip()
            if not rec_id:
                raise ValueError(f"line {line_no}: id is required")
            if rec_id in seen:
                raise ValueError(f"line {line_no}: duplicate id {rec_id!r}")
            seen.add(rec_id)
            if not title:
                raise ValueError(f"line {line_no}: title is required")
            parsed = dict(row)
            parsed["id"] = rec_id
            parsed["title"] = title
            for name in (*DIMENSIONS, "complexity"):
                parsed[name] = _parse_optional_number(row[name])
                _validate_range(name, parsed[name], SCORE_MIN, SCORE_MAX)
            parsed["confidence"] = _parse_optional_number(row["confidence"])
            _validate_range("confidence", parsed["confidence"], 0.0, 1.0)
            records.append(parsed)
    return records


def score_record(record: dict, weights: dict) -> dict:
    missing = [name for name in (*DIMENSIONS, "complexity") if record.get(name) is None]
    if missing:
        return {
            **record,
            "status": "HOLD_MISSING_ESTIMATE",
            "missing_estimates": ";".join(missing),
            "benefit_score": None,
            "priority_score": None,
        }
    benefit = sum(float(weights[d]) * float(record[d]) for d in DIMENSIONS)
    complexity_penalty = float(weights["complexity"]) * float(record["complexity"])
    score = benefit - complexity_penalty
    return {
        **record,
        "status": "RANKED",
        "missing_estimates": "",
        "benefit_score": benefit,
        "priority_score": score,
    }


def rank_profile(records: Sequence[dict], profile_name: str, weights: dict, tie_epsilon: float) -> List[dict]:
    scored = [score_record(r, weights) for r in records]
    eligible = [r for r in scored if r["status"] == "RANKED"]
    held = [r for r in scored if r["status"] != "RANKED"]
    eligible.sort(key=lambda r: (-float(r["priority_score"]), r["id"]))
    held.sort(key=lambda r: r["id"])

    ranked: List[dict] = []
    i = 0
    tie_group_counter = 0
    while i < len(eligible):
        anchor = eligible[i]
        group = [anchor]
        j = i + 1
        while j < len(eligible):
            if abs(float(eligible[j]["priority_score"]) - float(anchor["priority_score"])) <= tie_epsilon:
                group.append(eligible[j])
                j += 1
            else:
                break
        rank = i + 1
        tie_group_counter += 1
        tie_id = f"T{tie_group_counter:02d}" if len(group) > 1 else ""
        if len(group) > 1:
            low = min(float(x["priority_score"]) for x in group)
            high = max(float(x["priority_score"]) for x in group)
            tie_reason = (
                f"{len(group)} recommendations within tie_epsilon={tie_epsilon:.4f}; "
                f"score span={high-low:.4f}"
            )
        else:
            tie_reason = ""
        for rec in group:
            ranked.append({
                **rec,
                "profile": profile_name,
                "rank": rank,
                "tie_group": tie_id,
                "tie_reason": tie_reason,
            })
        i = j

    for rec in held:
        ranked.append({
            **rec,
            "profile": profile_name,
            "rank": "",
            "tie_group": "",
            "tie_reason": "",
        })
    return ranked


def _fmt(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_profile_csv(path: Path, rows: Sequence[dict]) -> None:
    fields = [
        "profile", "rank", "tie_group", "id", "title", "status",
        "priority_score", "benefit_score", "quality", "security", "delivery",
        "complexity", "confidence", "missing_estimates", "tie_reason",
        "owner_role", "dependencies", "assumptions",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in fields})


def build_sensitivity(all_profiles: Dict[str, Sequence[dict]]) -> List[dict]:
    ids = sorted({r["id"] for rows in all_profiles.values() for r in rows})
    lookup = {
        (profile, row["id"]): row
        for profile, rows in all_profiles.items()
        for row in rows
    }
    out: List[dict] = []
    profiles = list(all_profiles.keys())
    for rec_id in ids:
        first = lookup[(profiles[0], rec_id)]
        ranked_ranks = [
            int(lookup[(p, rec_id)]["rank"])
            for p in profiles
            if lookup[(p, rec_id)]["rank"] != ""
        ]
        row = {
            "id": rec_id,
            "title": first["title"],
            "status": (
                "RANKED_ALL_PROFILES"
                if len(ranked_ranks) == len(profiles)
                else "HOLD_MISSING_ESTIMATE"
            ),
            "best_rank": min(ranked_ranks) if ranked_ranks else "",
            "worst_rank": max(ranked_ranks) if ranked_ranks else "",
            "rank_span": (max(ranked_ranks) - min(ranked_ranks)) if ranked_ranks else "",
        }
        for p in profiles:
            item = lookup[(p, rec_id)]
            row[f"{p}_rank"] = item["rank"]
            row[f"{p}_score"] = item["priority_score"]
            row[f"{p}_tie_group"] = item["tie_group"]
        out.append(row)
    return out


def write_sensitivity_csv(path: Path, rows: Sequence[dict], profiles: Sequence[str]) -> None:
    fields = ["id", "title", "status", "best_rank", "worst_rank", "rank_span"]
    for p in profiles:
        fields.extend([f"{p}_rank", f"{p}_score", f"{p}_tie_group"])
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in fields})


def render_report(config: dict, all_profiles: Dict[str, Sequence[dict]], sensitivity: Sequence[dict]) -> str:
    profiles = list(all_profiles.keys())
    lines: List[str] = []
    lines.append("# Recommendation prioritization sensitivity report")
    lines.append("")
    lines.append("**Synthetic planning output — not a University of Iowa finding or decision.**")
    lines.append("")
    lines.append("## Formula")
    lines.append("")
    lines.append("For a complete recommendation under each profile:")
    lines.append("")
    lines.append("`benefit = quality*w_q + security*w_s + delivery*w_d`")
    lines.append("")
    lines.append("`priority = benefit - complexity*w_complexity`")
    lines.append("")
    lines.append(
        "Quality, security, delivery, and complexity are explicit 0–5 planning estimates. "
        "Missing required estimates produce `HOLD_MISSING_ESTIMATE`; they are never converted to zero."
    )
    lines.append("")
    lines.append(f"Tie epsilon: `{float(config.get('tie_epsilon', 0.0)):.4f}`.")
    lines.append("")
    lines.append("## Weight profiles")
    lines.append("")
    lines.append("| Profile | Quality | Security | Delivery | Complexity penalty |")
    lines.append("|---|---:|---:|---:|---:|")
    for p in profiles:
        w = config["profiles"][p]
        lines.append(
            f"| {p} | {float(w['quality']):.2f} | {float(w['security']):.2f} | "
            f"{float(w['delivery']):.2f} | {float(w['complexity']):.2f} |"
        )
    lines.append("")
    lines.append("## Rankings by profile")
    lines.append("")
    for p in profiles:
        lines.append(f"### {p}")
        lines.append("")
        lines.append("| Rank | ID | Recommendation | Score | Status | Tie |")
        lines.append("|---:|---|---|---:|---|---|")
        for r in all_profiles[p]:
            rank = r["rank"] if r["rank"] != "" else "—"
            score = _fmt(r["priority_score"]) or "—"
            tie = r["tie_group"] or ""
            lines.append(f"| {rank} | {r['id']} | {r['title']} | {score} | {r['status']} | {tie} |")
        lines.append("")
    lines.append("## Sensitivity summary")
    lines.append("")
    lines.append("| ID | Recommendation | Best rank | Worst rank | Rank span | Status |")
    lines.append("|---|---|---:|---:|---:|---|")
    for r in sorted(
        sensitivity,
        key=lambda x: (999999 if x["best_rank"] == "" else int(x["best_rank"]), x["id"]),
    ):
        lines.append(
            f"| {r['id']} | {r['title']} | {r['best_rank'] or '—'} | "
            f"{r['worst_rank'] or '—'} | {r['rank_span'] if r['rank_span'] != '' else '—'} | "
            f"{r['status']} |"
        )
    lines.append("")
    lines.append("## Interpretation guardrails")
    lines.append("")
    lines.append("- Rankings expose assumptions; they do not replace evidence, judgment, or accountable University decisions.")
    lines.append("- A high score means high priority under the selected synthetic assumptions, not proven impact.")
    lines.append("- Confidence is reported but not silently multiplied into the score; teams may change the formula explicitly if desired.")
    lines.append("- Tied recommendations intentionally retain the same rank when scores fall within the configured epsilon.")
    lines.append("- Recommendations with missing required estimates remain on hold and visible in every output.")
    lines.append("")
    return "\n".join(lines)


def run(input_csv: Path, weights_path: Path, out_dir: Path) -> Dict[str, Sequence[dict]]:
    config = load_weights(weights_path)
    records = load_recommendations(input_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    epsilon = float(config.get("tie_epsilon", 0.0))

    all_profiles: Dict[str, Sequence[dict]] = {}
    for profile_name, weights in config["profiles"].items():
        rows = rank_profile(records, profile_name, weights, epsilon)
        all_profiles[profile_name] = rows
        write_profile_csv(out_dir / f"ranking_{profile_name}.csv", rows)

    sensitivity = build_sensitivity(all_profiles)
    write_sensitivity_csv(out_dir / "sensitivity.csv", sensitivity, list(all_profiles.keys()))
    (out_dir / "report.md").write_text(render_report(config, all_profiles, sensitivity), encoding="utf-8")
    return all_profiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank recommendations with transparent assumptions.")
    parser.add_argument("recommendations", type=Path, help="Input recommendation CSV")
    parser.add_argument("weights", type=Path, help="JSON weight-profile config")
    parser.add_argument("--out-dir", type=Path, default=Path("out"), help="Output directory")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    run(args.recommendations, args.weights, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
