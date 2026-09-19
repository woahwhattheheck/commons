#!/usr/bin/env python3
"""Run nine fictional file-delivery scenarios against a captured assessor.

All inputs and outputs live in temporary directories. The assessor argument is
read once and never modified. This exercises the existing CLI, not a second
assessment engine. A nonzero exit keeps the failed cases in the printed report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any

FIXTURE = {
    "label": "FICTIONAL output-preservation rehearsal; not University findings",
    "as_of": "2026-09-19",
    "datasets": [{
        "dataset_id": "SYN-OUTPUT", "service": "ESS", "data_origin": "synthetic",
        "required_boundary_cases": ["empty", "unicode-\u00e9"],
        "covered_boundary_cases": [], "last_refreshed": "2026-09-20",
        "refresh_cadence_days": 30, "cleanup_required": True,
        "cleanup_last_verified": "2026-09-20",
    }],
}
CASES = (
    "new-json", "new-markdown", "replace-distinct-report", "same-path",
    "source-symlink", "source-hardlink", "distinct-symlink",
    "missing-parent", "unicode-write-error",
)
REFUSALS = set(CASES[3:])
PRIOR = b"previous complete fictional report\n"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def run_case(source: bytes, name: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="uiowa047-replay-") as temporary:
        root = Path(temporary)
        script = root / "test_data_assessor.py"
        script.write_bytes(source)
        payload = json.loads(json.dumps(FIXTURE))
        if name == "unicode-write-error":
            payload["datasets"][0]["owner_role"] = "\ud800"
        original = (json.dumps(payload, sort_keys=True) + "\n").encode()
        catalog = root / "catalog.json"
        catalog.write_bytes(original)
        output = root / "report.json"
        previous = None
        previous_path = None
        if name == "same-path":
            output = catalog
        elif name == "source-symlink":
            output.symlink_to(catalog)
        elif name == "source-hardlink":
            os.link(catalog, output)
        elif name == "distinct-symlink":
            previous_path = root / "previous.json"
            previous_path.write_bytes(PRIOR)
            previous = PRIOR
            output.symlink_to(previous_path)
        elif name == "missing-parent":
            output = root / "absent" / "report.json"
        elif name in {"replace-distinct-report", "unicode-write-error"}:
            output.write_bytes(PRIOR)
            output.chmod(0o640)
            previous, previous_path = PRIOR, output
        fmt = "markdown" if name in {"new-markdown", "unicode-write-error"} else "json"
        mode = [] if not sys.flags.optimize else ["-" + "O" * sys.flags.optimize]
        command = [sys.executable, *mode, "-B", str(script), str(catalog), "--format", fmt]
        result = subprocess.run(command + ["--output", str(output)], capture_output=True, timeout=15)
        diagnostic = result.stderr.decode("utf-8", errors="replace").replace(str(root), "<work>")
        # Normalize only ephemeral staging basenames, not error meaning.
        diagnostic = re.sub(r"\.uiowa047-[A-Za-z0-9_]+\.tmp", ".uiowa047-<temporary>.tmp", diagnostic)
        error_lines = [line for line in diagnostic.splitlines() if ": error:" in line]
        row = {
            "case": name,
            "expected_exit": 2 if name in REFUSALS else 0,
            "actual_exit": result.returncode,
            "input_preserved": catalog.read_bytes() == original,
            "assessor_preserved": script.read_bytes() == source,
            "no_staging_leftovers": not any(root.glob(".uiowa047-*.tmp")),
            "stdout_empty": result.stdout == b"",
            "diagnostic": error_lines[-1] if error_lines else ("Traceback" if "Traceback" in diagnostic else ""),
            "previous_report_preserved": None,
            "report_matches_stdout": None,
            "evidence_states_retained": None,
            "existing_mode_retained": None,
        }
        passed = (row["actual_exit"] == row["expected_exit"] and row["input_preserved"]
                  and row["assessor_preserved"] and row["no_staging_leftovers"] and row["stdout_empty"])
        if name in REFUSALS:
            passed = passed and ": error: cannot write report:" in diagnostic and "Traceback" not in diagnostic
            if previous_path is not None:
                row["previous_report_preserved"] = previous_path.read_bytes() == previous
                passed = passed and row["previous_report_preserved"]
            if name == "missing-parent":
                passed = passed and not output.exists()
        else:
            reference = subprocess.run(command, capture_output=True, timeout=15)
            row["report_matches_stdout"] = (reference.returncode == 0 and output.read_bytes() == reference.stdout)
            passed = passed and row["report_matches_stdout"]
            if fmt == "json" and reference.returncode == 0:
                report = json.loads(reference.stdout)
                states = {item["check_id"]: item["state"] for item in report["datasets"][0]["checks"]}
                row["evidence_states_retained"] = (
                    report["dataset_count"] == 1 and states["refresh_freshness"] == "UNKNOWN"
                    and states["cleanup"] == "UNKNOWN" and states["representativeness"] == "OBSERVED_GAP"
                )
                passed = passed and row["evidence_states_retained"]
            if name == "replace-distinct-report":
                row["existing_mode_retained"] = stat.S_IMODE(output.stat().st_mode) == 0o640
                passed = passed and row["existing_mode_retained"]
        row["passed"] = bool(passed)
        return row


def rehearse(source: bytes) -> dict[str, Any]:
    results = [run_case(source, name) for name in CASES]
    return {
        "schema": "uiowa047-output-preservation-replay-v1",
        "label": "FICTIONAL CLI delivery behavior; not University findings",
        "subject_git_blob": git_blob(source),
        "subject_bytes": len(source),
        "cases": results,
        "passed": sum(row["passed"] for row in results),
        "total": len(results),
        "all_passed": all(row["passed"] for row in results),
        "scope": "Existing local filesystem and interpreter only; no hosted CI, Windows or main-integration claim.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessor", type=Path, default=Path(__file__).with_name("test_data_assessor.py"))
    parser.add_argument("--expected-source-blob", help="Optional exact Git blob to verify before execution")
    args = parser.parse_args(argv)
    try:
        source = args.assessor.read_bytes()
        if args.expected_source_blob is not None and git_blob(source) != args.expected_source_blob:
            raise ValueError("assessor bytes do not match --expected-source-blob")
        report = rehearse(source)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
