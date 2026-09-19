#!/usr/bin/env python3
"""Render an exercised, source-bound synthetic release/recovery walkthrough."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STAGES = (
    ("09:05", "Failure detected; no completed recovery attempt."),
    ("09:16", "Rollback failed; process health alone did not restore behavior."),
    ("09:26", "Configuration now agrees; verification is still outstanding."),
    ("09:27", "Technical health passes; business verification is still outstanding."),
    ("09:32", "Both recorded verification scopes now support the historical endpoint."),
    ("10:00", "Same historical interval; this is not a fresh service-health check."),
)
BOUNDARY = (
    "SYNTHETIC REHEARSAL, not University evidence. Each row is computed by the "
    "existing three components, not filled from expected answers. UNKNOWN is not "
    "zero. A supported historical recovery interval does not establish current "
    "service health, causality, authenticity, a readiness grade or a live action."
)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_case():
    path = HERE / "case.py"
    raw = path.read_bytes()
    spec = importlib.util.spec_from_file_location("uiowa109_walkthrough_case", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module, git_blob(raw)


def build():
    case, source_blob = load_case()
    stages = []
    scenarios = []
    for time, interpretation in STAGES:
        ledger = case.fixture()
        ledger["as_of"] = "2026-09-18T" + time + ":00Z"
        stages.append({"as_of": ledger["as_of"], "interpretation": interpretation,
                       "ledger": ledger, "report": case.run(ledger)})
    for name in case.SCENARIOS:
        ledger = case.fixture(name)
        scenarios.append({"name": name, "ledger": ledger, "report": case.run(ledger)})
    bindings = stages[0]["report"]["component_bindings"]
    if any(row["report"]["component_bindings"] != bindings for row in stages + scenarios):
        raise ValueError("component sources changed during the walkthrough; rerun from one source version")
    return {"schema_version": "uiowa109-walkthrough/v1", "synthetic": True,
            "limitation": BOUNDARY, "case_source_git_blob": source_blob,
            "component_bindings": bindings, "stages": stages, "scenarios": scenarios}


def cell(value):
    if value is None:
        return "UNKNOWN"
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(
        "|", "&#124;").replace("`", "&#96;").replace("\r", " ").replace("\n", " ")


def markdown(packet):
    lines = ["# Release/recovery: an exercised operator walkthrough", "", packet["limitation"], "",
             "## Watch the evidence arrive", "",
             "All times below are UTC on the fictional event date, September 18, 2026.", "",
             "| As of | Environment then | Historical release-linked minutes | Endpoint records | Interpretation |",
             "|---|---|---:|---|---|"]
    for row in packet["stages"]:
        s = row["report"]["summary"]
        lines.append("| " + " | ".join(cell(v) for v in (
            row["as_of"][11:16], s["environment_at_as_of"], s["release_linked_recovery_minutes"],
            ", ".join(s["verified_source_event_ids"]) or "NONE", row["interpretation"])) + " |")
    lines += ["", "## Change one piece of evidence", "",
              "| Scenario | Provenance | Environment at as-of | Native historical minutes | Release-linked historical minutes |",
              "|---|---|---|---:|---:|"]
    for row in packet["scenarios"]:
        s = row["report"]["summary"]
        lines.append("| " + " | ".join(cell(v) for v in (
            row["name"], s["provenance_status"], s["environment_at_as_of"],
            s["native_detection_to_verified_minutes"], s["release_linked_recovery_minutes"])) + " |")
    lines += ["", "## Questions to walk through", "",
              "At 09:26, why is configuration agreement insufficient? The environment output",
              "records equal settings, not successful business behavior. At 09:27, name the",
              "still-missing scope. At 09:32, follow E_HEALTH and E_BEHAVIOR through the",
              "native recovery input and output before using the 27-minute interval.", "",
              "Then compare missing_deployment: native arithmetic still gives 27 minutes,",
              "but the release-linked value is UNKNOWN because that chain lacks a deployment.", "",
              "An attempt that starts before as_of but finishes after it is excluded by this",
              "v1 completion-event model. An earlier supported interval may remain in the",
              "historical report. Do not describe that result as current service health or",
              "as evidence that the in-flight intervention succeeded.", "",
              "## Exact loaded source bindings", "",
              "Case source Git blob: `" + packet["case_source_git_blob"] + "`.", "",
              "| Component | Loaded Git blob | Compared with tested baseline |", "|---|---|---|"]
    for name, binding in sorted(packet["component_bindings"].items()):
        lines.append("| " + " | ".join(cell(v) for v in
                     (name, binding["git_blob"], binding["version_binding"])) + " |")
    lines += ["", "## Reproduce", "", "From the repository root:", "", "```sh",
              "python revenue/uiowa_rfq_18649_release_recovery_case/walkthrough.py --output NEW_DIRECTORY",
              "python -m unittest discover -s revenue/uiowa_rfq_18649_release_recovery_case -v",
              "python -O -m unittest discover -s revenue/uiowa_rfq_18649_release_recovery_case -v", "```", "",
              "Choose a new directory. walkthrough.json retains every editable input ledger",
              "and actual native input/output report behind these tables. Re-run any retained",
              "ledger through case.py --ledger; keep future and excluded records visible.", "",
              "Original integration and fixtures: ZZ-COPPERFIN-R7. Independent source-binding",
              "repair, execution review and walkthrough: ZZ-PETREL-82M. Native component",
              "authors retain their original attribution. Local runs are not GitHub CI."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="create a new directory; never overwrite")
    args = parser.parse_args(argv)
    try:
        packet = build()
        rendered = markdown(packet)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=False)
            (args.output / "walkthrough.json").write_text(
                json.dumps(packet, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            (args.output / "walkthrough.md").write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError, OverflowError, SyntaxError, ImportError) as exc:
        print("release-recovery-walkthrough: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
