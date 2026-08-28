#!/usr/bin/env python3
"""Compile verified Commons execution receipts into persistent skill knowledge."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "experience" / "raw"
WIKI_DIR = ROOT / "experience" / "wiki"
PATTERN_DIR = WIKI_DIR / "patterns"
SCHEMA = "commons-experience/v1"
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ExperienceError(ValueError):
    """Raised when an experience packet violates the public contract."""


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExperienceError(f"{path.relative_to(ROOT)}: {exc}") from exc
        validate_record(record, path)
        record_id = record["id"]
        if record_id in seen:
            raise ExperienceError(f"duplicate experience id: {record_id}")
        seen.add(record_id)
        records.append(record)
    if not records:
        raise ExperienceError("experience/raw must contain at least one packet")
    return records


def validate_record(record: dict[str, Any], path: Path) -> None:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    required = {
        "schema",
        "id",
        "recorded_at",
        "task",
        "outcome",
        "evidence",
        "patterns",
        "skill_impacts",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise ExperienceError(f"{rel}: missing {', '.join(missing)}")
    if record["schema"] != SCHEMA:
        raise ExperienceError(f"{rel}: unsupported schema")
    record_id = record["id"]
    if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
        raise ExperienceError(f"{rel}: invalid id")
    if path.stem != record_id:
        raise ExperienceError(f"{rel}: filename must match id")
    if record["outcome"] not in {"passed", "failed"}:
        raise ExperienceError(f"{rel}: outcome must be passed or failed")
    if not isinstance(record["task"], str) or not record["task"].strip():
        raise ExperienceError(f"{rel}: task must be non-empty")
    evidence = record["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ExperienceError(f"{rel}: evidence must be non-empty")
    for item in evidence:
        if not isinstance(item, dict) or not item.get("kind") or not item.get("value"):
            raise ExperienceError(f"{rel}: malformed evidence")
        if item["kind"] == "commit" and not SHA_RE.fullmatch(item["value"]):
            raise ExperienceError(f"{rel}: commit evidence must be a full SHA")
    patterns = record["patterns"]
    if not isinstance(patterns, list) or not patterns:
        raise ExperienceError(f"{rel}: patterns must be non-empty")
    for pattern in patterns:
        needed = {"id", "kind", "summary", "procedure", "applies_to"}
        if not isinstance(pattern, dict) or needed - pattern.keys():
            raise ExperienceError(f"{rel}: malformed pattern")
        if not ID_RE.fullmatch(pattern["id"]):
            raise ExperienceError(f"{rel}: invalid pattern id")
        if pattern["kind"] not in {"success", "failure"}:
            raise ExperienceError(f"{rel}: pattern kind must be success or failure")
        if not isinstance(pattern["applies_to"], list) or not pattern["applies_to"]:
            raise ExperienceError(f"{rel}: pattern applies_to must be non-empty")
    for impact in record["skill_impacts"]:
        needed = {"skill", "change", "decision", "validation"}
        if not isinstance(impact, dict) or needed - impact.keys():
            raise ExperienceError(f"{rel}: malformed skill impact")
        if impact["decision"] not in {"adopted", "rejected", "observed"}:
            raise ExperienceError(f"{rel}: invalid skill decision")
        validation = impact["validation"]
        if not isinstance(validation, dict) or "result" not in validation:
            raise ExperienceError(f"{rel}: skill impact needs validation result")


def compile_outputs(records: list[dict[str, Any]]) -> dict[Path, str]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "success_count": 0,
            "failure_count": 0,
            "evidence_records": [],
            "applies_to": set(),
            "summaries": [],
            "procedures": [],
        }
    )
    evolution: list[dict[str, Any]] = []
    impacts: list[dict[str, Any]] = []

    for record in records:
        evolution.append(
            {
                "id": record["id"],
                "recorded_at": record["recorded_at"],
                "outcome": record["outcome"],
                "task": record["task"],
                "evidence": record["evidence"],
            }
        )
        for pattern in record["patterns"]:
            item = grouped[pattern["id"]]
            item[f"{pattern['kind']}_count"] += 1
            item["evidence_records"].append(record["id"])
            item["applies_to"].update(pattern["applies_to"])
            if pattern["summary"] not in item["summaries"]:
                item["summaries"].append(pattern["summary"])
            if pattern["procedure"] not in item["procedures"]:
                item["procedures"].append(pattern["procedure"])
        for impact in record["skill_impacts"]:
            impacts.append({"experience_id": record["id"], **impact})

    catalog = {
        "schema": "commons-experience-wiki/v1",
        "source_schema": SCHEMA,
        "record_count": len(records),
        "pattern_count": len(grouped),
        "patterns": [],
    }
    outputs: dict[Path, str] = {}
    for pattern_id in sorted(grouped):
        item = grouped[pattern_id]
        compiled = {
            "id": pattern_id,
            "success_count": item["success_count"],
            "failure_count": item["failure_count"],
            "evidence_records": sorted(item["evidence_records"]),
            "applies_to": sorted(item["applies_to"]),
            "summaries": item["summaries"],
            "procedures": item["procedures"],
        }
        catalog["patterns"].append(compiled)
        lines = [
            f"# {pattern_id}",
            "",
            f"Evidence: {len(compiled['evidence_records'])} verified experience packet(s).",
            f"Success observations: {compiled['success_count']}",
            f"Failure observations: {compiled['failure_count']}",
            "",
            "## Applies to",
            "",
            *[f"- `{name}`" for name in compiled["applies_to"]],
            "",
            "## Compiled knowledge",
            "",
            *[f"- {summary}" for summary in compiled["summaries"]],
            "",
            "## Reusable procedures",
            "",
            *[f"- {procedure}" for procedure in compiled["procedures"]],
            "",
            "## Evidence packets",
            "",
            *[f"- `experience/raw/{record_id}.json`" for record_id in compiled["evidence_records"]],
            "",
        ]
        outputs[PATTERN_DIR / f"{pattern_id}.md"] = "\n".join(lines)

    index_lines = [
        "# Commons Experience Wiki",
        "",
        "This is compiled knowledge, not raw history and not an executable skill.",
        "It is rebuilt deterministically from evidence packets in `experience/raw/`.",
        "",
        f"- Verified experience packets: {len(records)}",
        f"- Compiled patterns: {len(grouped)}",
        f"- Skill-impact entries: {len(impacts)}",
        "",
        "## Pattern catalog",
        "",
        *[
            f"- [{item['id']}](patterns/{item['id']}.md) — "
            f"{item['success_count']} success / {item['failure_count']} failure observations"
            for item in catalog["patterns"]
        ],
        "",
        "The runtime agent reads active skills, not this wiki. Maintainers and skill",
        "proposers use the wiki to make one evidence-backed procedural change at a time.",
        "",
    ]
    outputs[WIKI_DIR / "index.md"] = "\n".join(index_lines)
    outputs[WIKI_DIR / "catalog.json"] = _json(catalog)
    outputs[WIKI_DIR / "evolution-log.jsonl"] = "".join(
        json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n" for item in evolution
    )
    outputs[WIKI_DIR / "skill-impact.json"] = _json(
        {"schema": "commons-skill-impact/v1", "entries": impacts}
    )
    return outputs


def compile_to_disk(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(outputs: dict[Path, str]) -> list[str]:
    drift: list[str] = []
    for path, expected in outputs.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != expected:
            drift.append(str(path.relative_to(ROOT)))
    expected_pattern_paths = {path for path in outputs if path.parent == PATTERN_DIR}
    for path in PATTERN_DIR.glob("*.md"):
        if path not in expected_pattern_paths:
            drift.append(str(path.relative_to(ROOT)))
    return sorted(drift)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compile", "check", "validate"))
    args = parser.parse_args()
    try:
        records = load_records()
        outputs = compile_outputs(records)
        if args.command == "compile":
            compile_to_disk(outputs)
            print(f"COMPILED {len(records)} records {len(outputs)} outputs")
        elif args.command == "check":
            drift = check_outputs(outputs)
            if drift:
                print("DRIFT " + " ".join(drift))
                return 1
            print(f"CURRENT {len(records)} records {len(outputs)} outputs")
        else:
            print(f"VALID {len(records)} records {len(outputs)} outputs")
    except ExperienceError as exc:
        print(f"INVALID {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
