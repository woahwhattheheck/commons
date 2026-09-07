#!/usr/bin/env python3
"""Turn the battery's NUL-delimited exit records into checkout-linked JSON.

This reads local git objects only. It never parses test stdout, contacts GitHub,
reruns tests, or changes their outcome. Counts describe executed files, not test
cases. A source blob identifies the file in the recorded starting checkout; it
is not an assertion that a test left the working tree unchanged.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from collections.abc import Mapping

SCHEMA = "commons-battery-report-v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")


def parse_results(raw: bytes | None) -> tuple[str, list[dict], bool, list[str]]:
    """Read command/path/exit triples, retaining completed records after a stop."""
    problems: list[str] = []
    records: list[dict] = []
    sha = ""
    marker: int | None = None
    if raw is None:
        return sha, records, False, ["result stream is missing"]
    fields = raw.split(b"\0")
    if fields[-1] == b"":
        fields.pop()
    else:
        problems.append("unterminated result stream")
    if len(fields) % 3:
        problems.append("partial result record")
    for index in range(0, len(fields) - len(fields) % 3, 3):
        command, path, code = (field.decode("utf-8", "surrogateescape") for field in fields[index:index + 3])
        if marker is not None:
            problems.append("records follow completion marker")
        if command == "checkout_sha":
            if index != 0 or sha or not HEX40.fullmatch(path) or code:
                problems.append("invalid checkout record")
            else:
                sha = path
            continue
        if command == "battery_complete":
            if path or code not in ("0", "1"):
                problems.append("invalid completion record")
            else:
                marker = int(code)
            continue
        if command not in ("python3", "node"):
            problems.append("unknown result command")
            continue
        if not re.fullmatch(r"[0-9]{1,3}", code) or int(code) > 255:
            problems.append("invalid exit code")
            continue
        normalized = PurePosixPath(path)
        if not path or normalized.is_absolute() or ".." in normalized.parts or str(normalized) == ".":
            problems.append("invalid repository-relative test path")
            continue
        records.append({"path": str(normalized), "command": [command, path], "exit_code": int(code)})
    if not sha:
        problems.append("checkout record is missing")
    if marker is None:
        problems.append("completion marker is missing")
    elif marker != int(any(row["exit_code"] != 0 for row in records)):
        problems.append("completion marker disagrees with recorded exits")
    return sha, records, not problems, problems


def source_blobs(root: Path, sha: str) -> dict[str, str]:
    """Resolve paths on the recorded commit, even when a test moved HEAD."""
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", sha + "^{commit}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if commit != sha:
        raise ValueError("recorded object is not a commit")
    tree = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", sha],
        check=True, capture_output=True,
    ).stdout
    blobs = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        _mode, kind, blob = metadata.split()
        if kind == b"blob":
            blobs[path.decode("utf-8", "surrogateescape")] = blob.decode("ascii")
    return blobs


def build_report(root: Path, raw: bytes | None, outcome: str, environ: Mapping[str, str]) -> dict:
    sha, records, complete, problems = parse_results(raw)
    blobs: dict[str, str] = {}
    if sha:
        try:
            blobs = source_blobs(root, sha)
        except (OSError, subprocess.CalledProcessError, ValueError):
            problems.append("recorded checkout commit is unavailable")
            complete = False
    for row in records:
        row["source_blob_sha"] = blobs.get(row["path"])
        row["source_in_checkout_commit"] = row["source_blob_sha"] is not None
    failed = sum(row["exit_code"] != 0 for row in records)
    if outcome in ("cancelled", "skipped"):
        problems.append("battery step was " + outcome)
        complete = False
    elif outcome == "success" and failed:
        problems.append("step outcome disagrees with recorded exits")
        complete = False
    if not complete:
        conclusion = "INCOMPLETE"
    elif failed:
        conclusion = "FAILED"
    elif outcome == "failure":
        conclusion = "HARNESS_FAILED"
    elif not records:
        conclusion = "NO_TESTS"
    else:
        conclusion = "PASSED"
    return {
        "schema": SCHEMA,
        "repository": environ.get("GITHUB_REPOSITORY", ""),
        "run_id": environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": environ.get("GITHUB_RUN_ATTEMPT", ""),
        "job_name": environ.get("GITHUB_JOB", ""),
        "workflow_name": environ.get("GITHUB_WORKFLOW", ""),
        "workflow_ref": environ.get("GITHUB_WORKFLOW_REF", ""),
        "workflow_sha": environ.get("GITHUB_WORKFLOW_SHA", ""),
        "event_name": environ.get("GITHUB_EVENT_NAME", ""),
        "event_sha": environ.get("GITHUB_SHA", ""),
        "checkout_sha": sha,
        "workflow_outcome": outcome,
        "complete": complete,
        "conclusion": conclusion,
        "counts": {
            "completed_files": len(records),
            "passed_files": len(records) - failed,
            "failed_files": failed,
            "unresolved_source_files": sum(not row["source_in_checkout_commit"] for row in records),
        },
        "results": records,
        "problems": problems,
    }


def summary(report: dict) -> str:
    counts = report["counts"]
    lines = [
        "## Battery source-linked results",
        "",
        "**%s** — %d completed files, %d failed files. These are file counts, not test-case counts."
        % (report["conclusion"], counts["completed_files"], counts["failed_files"]),
        "",
        "Recorded starting checkout: `%s`." % (report["checkout_sha"] or "UNAVAILABLE"),
        "Source blobs refer to that commit, not to a later moving main or uncommitted working-tree bytes.",
        "",
    ]
    failures = [row for row in report["results"] if row["exit_code"] != 0]
    if failures:
        lines += ["| Test file | Exit | Source blob |", "| --- | --- | --- |"]
        for row in failures:
            path = html.escape(json.dumps(row["path"], ensure_ascii=True)).replace("|", "&#124;")
            lines.append("| <code>%s</code> | %d | `%s` |" % (
                path, row["exit_code"], row["source_blob_sha"] or "NOT_IN_CHECKOUT_COMMIT"))
    if counts["unresolved_source_files"]:
        lines += ["", "%d executed file(s) were not resolved to this checkout commit; see the JSON artifact."
                  % counts["unresolved_source_files"]]
    if report["problems"]:
        lines += ["", "Report diagnostics: " + "; ".join(report["problems"]) + "."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--outcome", choices=("success", "failure", "cancelled", "skipped", "unknown"), default="unknown")
    args = parser.parse_args(argv)
    try:
        try:
            raw = args.results.read_bytes()
        except FileNotFoundError:
            raw = None
        report = build_report(args.root, raw, args.outcome, os.environ)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as handle:
                handle.write(summary(report))
    except OSError:
        print("battery report could not read or write its local result files", file=sys.stderr)
        return 1
    # The battery's original exit code controls CI. Reporting a red is not a
    # second test execution, nor may it turn the failed battery step green.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
