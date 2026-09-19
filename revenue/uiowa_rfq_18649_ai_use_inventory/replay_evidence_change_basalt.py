#!/usr/bin/env python3
"""Replay a fictional evidence change through the existing UIOWA-071 engine.

This is a fixed worked example, not another classifier. It captures the four
engine source files and the supplied synthetic fixture once, then executes those
captured copies in one isolated temporary-directory interpreter. No network,
external records, live repository writes or output-directory replacement occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ENGINE_FILES = ("inventory.py", "schema.py", "interview_guide.py", "__init__.py")
FIXTURE = "fixtures/synthetic_ai_use.json"
TARGET = "AIU-SYN-003"
FIXTURE_BLOB = "42347c91fd9b6b3ce3e600487bd9a3d4632a83c9"

# This child imports only the captured engine; it contains no classification rule.
CHILD = r'''
import copy, json, pathlib, sys
import inventory, interview_guide
fixture = pathlib.Path("fixtures/synthetic_ai_use.json")
records, label = inventory.load(fixture)
if len([r for r in records if r.get("entry_id") == "AIU-SYN-003"]) != 1:
    raise ValueError("worked example requires exactly one AIU-SYN-003 record")
source = next(r for r in records if r["entry_id"] == "AIU-SYN-003")
locator = "synthetic://uiowa-rfq18649/AIU-SYN-003/release-note-example"
changes = [
    ("baseline", {}),
    ("locator_only", {"evidence_refs": [locator]}),
    ("named_output", {"evidence_refs": [locator], "outputs": ["Fictional release-note document SYN-003"]}),
    ("explicit_standalone", {"evidence_refs": [locator], "outputs": ["Fictional release-note document SYN-003"], "integrations": []}),
    ("workflow_recorded", {"evidence_refs": [locator], "outputs": ["Fictional release-note document SYN-003"], "integrations": ["Fictional release-note publication workflow"]}),
    ("benefit_example", {"evidence_refs": [locator], "outputs": ["Fictional release-note document SYN-003"], "integrations": ["Fictional release-note publication workflow"], "observed_benefits": [{"claim": source["observed_benefits"][0]["claim"], "example_ref": "synthetic://uiowa-rfq18649/AIU-SYN-003/before-after-example"}]}),
    ("still_declared_planned", {"evidence_refs": [locator], "outputs": ["Fictional release-note document SYN-003"], "integrations": ["Fictional release-note publication workflow"], "observed_benefits": [{"claim": source["observed_benefits"][0]["claim"], "example_ref": "synthetic://uiowa-rfq18649/AIU-SYN-003/before-after-example"}], "declared_status": "PLANNED"}),
]
out = []
for name, delta in changes:
    revised = copy.deepcopy(records)
    next(r for r in revised if r["entry_id"] == "AIU-SYN-003").update(copy.deepcopy(delta))
    result = inventory.build(revised, source_label=label)
    row = next(r for r in result.entries if r["entry_id"] == "AIU-SYN-003")
    out.append({"scenario": name, "changes_from_baseline": delta, "input_record": next(r for r in revised if r["entry_id"] == "AIU-SYN-003"), "target_entry": row, "counts": result.counts(), "coverage": result.coverage(), "total_gaps": len(result.gaps()), "follow_up_probes": interview_guide.probes_for(row), "validation_issues": result.issues})
print(json.dumps({"synthetic": True, "notice": "All records and modifications are fictional. No University inputs or findings.", "target": "AIU-SYN-003", "source_label": label, "optimize": sys.flags.optimize, "scenarios": out}, sort_keys=True))
'''


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def run_replay(source_dir: Path = HERE) -> dict:
    """Capture source/fixture once, execute those bytes, retain the same identities."""
    paths = (*ENGINE_FILES, FIXTURE)
    captured = {name: (source_dir / name).read_bytes() for name in paths}
    if git_blob(captured[FIXTURE]) != FIXTURE_BLOB:
        raise ValueError("this fixed fictional replay requires the original synthetic fixture; do not relabel other records as synthetic")
    with tempfile.TemporaryDirectory(prefix="uiowa071-evidence-replay-") as temp:
        root = Path(temp)
        for name, data in captured.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        env = dict(os.environ, PYTHONPATH="", PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, *(["-O"] * sys.flags.optimize), "-S", "-c", CHILD]
        process = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                 text=True, encoding="utf-8", timeout=60)
        if process.returncode != 0:
            raise RuntimeError("captured engine replay failed: " + process.stderr.strip())
        # Detect writes into the captured inputs; all scenario edits belong in memory.
        for name, data in captured.items():
            if (root / name).read_bytes() != data:
                raise RuntimeError("engine changed captured input: " + name)
    result = json.loads(process.stdout)
    if result.get("optimize") != sys.flags.optimize:
        raise RuntimeError("child interpreter optimization did not match the caller")
    result["source_blobs"] = {name: git_blob(data) for name, data in captured.items()}
    result["runner_sha256"] = hashlib.sha256(CHILD.encode("utf-8")).hexdigest()
    result["execution_scope"] = "Captured original engine API in a temporary cloud process; not hosted CI or source verification of the fictional locators."
    return result


def render_markdown(result: dict) -> str:
    lines = ["# What changes an AI-use claim?", "", result["notice"], "",
             "The original engine was executed for each variant. These are input interpretations, not verified adoption.", "",
             "| Variant | Engine classification | Target gaps | Whole-collection gaps |",
             "| --- | --- | ---: | ---: |"]
    for case in result["scenarios"]:
        entry = case["target_entry"]
        lines.append(f"| {case['scenario']} | {entry['classification']} | {len(entry['gaps'])} | {case['total_gaps']} |")
    lines += ["", "A named output can receive ACTIVE_USE while integration remains UNKNOWN. Explicit NONE_REPORTED changes that result; neither state proves approval or benefit.", "",
              "Supplying a benefit example locator does not verify the locator or establish quantified time savings. A PLANNED declaration remains PLANNED_USE even with contradictory outputs.", "",
              "## Exact inputs, reasons and next questions", ""]
    for case in result["scenarios"]:
        entry = case["target_entry"]
        lines += ["### " + case["scenario"], "", "Changes from the unchanged baseline:", "", "```json", json.dumps(case["changes_from_baseline"], indent=2, sort_keys=True), "```", "",
                  "Engine reasons: " + ("; ".join(entry["classification_reasons"]) or "No classification reason was emitted."), "",
                  "Remaining gap codes: " + ", ".join(g["gap"] for g in entry["gaps"]), "",
                  "Actual follow-up probes: " + "; ".join(q["id"] + ": " + q["text"] for q in case["follow_up_probes"]), ""]
    lines += ["## Captured source objects", "", "```json", json.dumps(result["source_blobs"], indent=2, sort_keys=True), "```", "", result["execution_scope"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    try:
        result = run_replay()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
