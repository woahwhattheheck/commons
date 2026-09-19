#!/usr/bin/env python3
"""Run one lane's test suite in THIS process and report its peak memory.

Invoked as a subprocess, one fresh interpreter per lane. That matters:
``resource.getrusage(RUSAGE_SELF).ru_maxrss`` is a high-water mark that never
falls, so measuring several lanes in one process would report a running maximum
and silently attribute the heaviest lane's peak to every lane after it. A fresh
process per lane is what makes the number belong to that lane.

Prints one JSON object on stdout. Everything else -- test output, warnings,
whatever the suite prints -- is kept off stdout so the parent can parse it.

Usage:  python3 mem_probe.py <lane-dir>
        python3 mem_probe.py --baseline      # interpreter cost with no suite

Python 3 standard library only.
"""
from __future__ import annotations

import io
import json
import os
import resource
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


def peak_rss_bytes() -> int:
    """Peak RSS of this process.

    ``ru_maxrss`` is kilobytes on Linux and bytes on macOS. Normalising to bytes
    here rather than at the reporting end keeps the unit question in one place.
    """
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw * 1024 if sys.platform.startswith("linux") else raw


def run_suite(lane: Path) -> dict:
    """Discover and run the lane's tests, capturing everything."""
    lane = Path(lane).resolve()
    test_files = sorted(lane.glob("test_*.py")) + sorted(lane.glob("*_test.py"))
    if not test_files:
        return {
            "status": "NO_TESTS",
            "tests_run": "UNKNOWN",
            "note": "No test_*.py in this lane. Peak memory for this lane is UNKNOWN -- "
                    "nothing was executed, which is not the same as using no memory.",
        }

    # The lane's modules import each other by bare name, so it has to be on the
    # path and be the working directory.
    sys.path.insert(0, str(lane))
    os.chdir(lane)

    buf_out, buf_err = io.StringIO(), io.StringIO()
    started = time.perf_counter()
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            loader = unittest.TestLoader()
            suite = loader.discover(str(lane), pattern="test_*.py", top_level_dir=str(lane))
            runner = unittest.TextTestRunner(stream=buf_err, verbosity=0)
            result = runner.run(suite)
    except Exception as exc:  # a suite that cannot even be collected
        return {
            "status": "ERROR",
            "tests_run": "UNKNOWN",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": time.perf_counter() - started,
            "note": "Suite could not be run. Memory figure covers only what happened before "
                    "the failure and must not be read as this lane's cost.",
        }

    elapsed = time.perf_counter() - started

    # A module that fails to IMPORT does not raise out of discover(); unittest
    # substitutes a `_FailedTest` placeholder that shows up as an ordinary
    # error. Left alone, such a lane reports a small, tidy memory figure that
    # represents the interpreter failing to load a file -- not the lane's cost.
    # That is the exact "looks cheap because it never ran" result this whole
    # lane exists to prevent, so it gets its own status and its figure withheld.
    load_failures = [str(test) for test, _ in result.errors
                     if type(test).__name__ == "_FailedTest"]
    if load_failures:
        return {
            "status": "COLLECTION_ERROR",
            "tests_run": result.testsRun,
            "load_failures": load_failures,
            "elapsed_seconds": elapsed,
            "note": "One or more test modules could not be imported, so the lane's code was "
                    "not fully exercised. Memory UNKNOWN -- the observed peak reflects a "
                    "failed import, not this lane's cost.",
        }

    return {
        "status": "OK" if result.wasSuccessful() else "TESTS_FAILED",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "elapsed_seconds": elapsed,
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--baseline":
        # What a bare interpreter costs, so the per-lane figures can be read
        # against something instead of looking alarming on their own.
        payload = {"lane": "<baseline>", "status": "BASELINE", "tests_run": 0,
                   "peak_rss_bytes": peak_rss_bytes()}
        print(json.dumps(payload, sort_keys=True))
        return 0

    if len(argv) != 1:
        print(json.dumps({"status": "ERROR", "error": "usage: mem_probe.py <lane-dir>"}))
        return 2

    lane = Path(argv[0])
    if not lane.is_dir():
        print(json.dumps({"lane": str(lane), "status": "ERROR",
                          "error": f"not a directory: {lane}", "tests_run": "UNKNOWN"}))
        return 2

    name = lane.resolve().name
    outcome = run_suite(lane)
    outcome["lane"] = name
    # Read the high-water mark AFTER the suite, which is the whole point.
    outcome["peak_rss_bytes"] = peak_rss_bytes()
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
