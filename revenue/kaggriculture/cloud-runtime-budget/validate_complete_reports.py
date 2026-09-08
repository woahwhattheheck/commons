# SPDX-License-Identifier: Apache-2.0
"""Run and retain the complete-child-report integrity validation.

This invokes only the adjacent standard-library profiler/transport tests. It
runs no Kaggriculture engine transition, game, network service, or policy panel.
Use a new output directory or remove prior generated files before rerunning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

TESTS = (
    "test_complete_reports.py",
    "test_child_reports.py",
    "test_profile_saved.py",
    "test_source_binding.py",
    "test_timeout_reports.py",
    "test_process_output.py",
    "test_trace_consumer.py",
)
OUTPUTS = (
    "COMPLETE-REPORTS-TESTS.txt",
    "COMPLETE-REPORTS-BASELINE.txt",
    "COMPLETE-REPORTS-RESULT.json",
    "COMPLETE-REPORTS.md",
)


def identity(path: Path) -> dict[str, object]:
    body = path.read_bytes()
    return {
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "git_blob": hashlib.sha1(
            b"blob " + str(len(body)).encode("ascii") + b"\0" + body
        ).hexdigest(),
    }


def run_test(path: Path, *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(path)],
        cwd=path.parent.parent.parent.parent,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        timeout=180,
        check=False,
    )


def parsed_success(name: str, text: str) -> dict[str, object]:
    match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", text)
    if not match or not re.search(r"\nOK\s*$", text):
        raise RuntimeError("unparseable successful test log: " + name)
    return {
        "tests": int(match.group(1)),
        "seconds": float(match.group(2)),
        "success": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--base-commit", default=None)
    args = parser.parse_args(argv)
    source = args.source_dir.resolve()
    output = args.output_dir.resolve()
    baseline_source = args.baseline_source.resolve()
    output.mkdir(parents=True, exist_ok=True)
    existing = [output / name for name in OUTPUTS if (output / name).exists()]
    if existing:
        parser.error("use a new output directory; retained files exist: " + ", ".join(map(str, existing)))

    combined: list[str] = []
    results: dict[str, dict[str, object]] = {}
    for name in TESTS:
        path = source / name
        process = run_test(path)
        text = process.stdout + process.stderr
        combined.extend(("\n===== " + name + " =====\n", text))
        if process.returncode:
            (output / "COMPLETE-REPORTS-TESTS.txt").write_text("".join(combined), encoding="utf-8")
            raise RuntimeError(f"{name} failed with exit {process.returncode}")
        results[name] = parsed_success(name, text)
    combined_text = "".join(combined)
    (output / "COMPLETE-REPORTS-TESTS.txt").write_text(combined_text, encoding="utf-8")

    environment = dict(os.environ, PROFILER_SOURCE=str(baseline_source))
    predecessor = run_test(source / "test_complete_reports.py", environment=environment)
    predecessor_text = predecessor.stdout + predecessor.stderr
    predecessor_text += f"\npredecessor_exit_code={predecessor.returncode}\n"
    (output / "COMPLETE-REPORTS-BASELINE.txt").write_text(predecessor_text, encoding="utf-8")
    if predecessor.returncode == 0:
        raise RuntimeError("unchanged predecessor unexpectedly passes the new integrity suite")
    failure_match = re.search(r"FAILED \(failures=(\d+)", predecessor_text)
    error_match = re.search(r"errors=(\d+)", predecessor_text)

    source_names = ("profile_saved.py", "validate_complete_reports.py", *TESTS)
    sources = {name: identity(source / name) for name in source_names}
    total = sum(int(row["tests"]) for row in results.values())
    report = {
        "schema": "titan.saved-profiler.complete-report-integrity.v1",
        "base_workflow_commit": args.base_commit,
        "python": platform.python_version(),
        "tests": results,
        "total_test_methods": total,
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "predecessor_control": {
            "source_git_blob": identity(baseline_source)["git_blob"],
            "suite_exit_nonzero": True,
            "reported_failures": int(failure_match.group(1)) if failure_match else None,
            "reported_errors": int(error_match.group(1)) if error_match else 0,
            "log_sha256": hashlib.sha256(predecessor_text.encode("utf-8")).hexdigest(),
        },
        "sources": sources,
        "behavior": {
            "complete_reports_require_source_input_action_and_mode_identity": True,
            "per_call_action_hash_parity_required": True,
            "invalid_complete_bytes_retained": True,
            "original_error_reports_preserved": True,
            "expected_action_mismatch_remains_off_policy_evidence": True,
        },
        "scope": "Saved-profiler child-report validation and parent parity only.",
        "full_games": 0,
        "game_seed_uses": 0,
        "engine_transitions": 0,
        "workflow_added_to_final_tree": False,
    }
    (output / "COMPLETE-REPORTS-RESULT.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Complete saved-profiler report integrity\n\n",
        "A child report marked `complete` is accepted only when it binds the exact ",
        "requested pass, source identities, replay input, uninterrupted call prefix, ",
        "and one action digest for every completed call. Missing identities no longer ",
        "compare as equal `None` values in the parent supervisor.\n\n",
        "Malformed or incomplete `complete` reports become `process_error` with type ",
        "`InvalidChildReport`. Their original bytes are retained at a new `.invalid.bin` ",
        "path with length and SHA-256. Existing non-complete actor errors remain actor ",
        "errors rather than being relabeled. Expected-action mismatch remains separate ",
        "off-policy correspondence evidence.\n\n",
        "The supervisor also compares `(step, action_sha256)` for every ordinary and ",
        "instrumented call. An aggregate sequence digest alone is not the complete ",
        "parent parity proof.\n\n",
        "## Executed validation\n\n",
        f"All **{total} methods** passed across the seven current standard-library suites:\n\n",
    ]
    for name, row in results.items():
        lines.append(f"- `{name}`: {row['tests']} methods.\n")
    lines.extend((
        "\nThe new integrity suite starts real subprocesses for the key controls. It checks ",
        "well-formed success, original error preservation, missing identity, wrong mode, ",
        "malformed digests, input/source binding, noncontiguous steps, per-call action ",
        "mismatches, raw invalid-byte retention, actual worker shutdown corruption, and ",
        "off-policy expected-action separation.\n\n",
        "The unchanged predecessor fails that suite as required; its exact output is ",
        "retained in `COMPLETE-REPORTS-BASELINE.txt`. Source identities and per-suite ",
        "durations are in `COMPLETE-REPORTS-RESULT.json`; passing output is in ",
        "`COMPLETE-REPORTS-TESTS.txt`.\n\n",
        "## Reproduce\n\n",
        "Run `validate_complete_reports.py` with an unchanged predecessor source and a ",
        "new output directory. The validation executes no games, engine transitions, ",
        "gameplay seeds, remote services, canonical release, or policy selection.\n",
    ))
    (output / "COMPLETE-REPORTS.md").write_text("".join(lines), encoding="utf-8")
    print(json.dumps({"success": True, "tests": total, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
