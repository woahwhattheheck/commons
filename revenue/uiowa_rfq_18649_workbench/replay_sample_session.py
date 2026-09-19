#!/usr/bin/env python3
"""Re-run the sample-session tests and retain a real Chromium rehearsal.

No model, network or compiler is invoked. Output is create-only. Test failures,
empty suites, skips and changed source bytes cannot yield a PASS receipt.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
ASSETS = ("app.js", "index.html", "handoff.js", "handoff_import.js", "style.css",
          "test_sample_session.py", "replay_sample_session.py")
RESULT_MARKER = "UIOWA_SAMPLE_TEST_RESULT="


def digest(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()}


def write_new(path: Path, data: bytes) -> None:
    """Never replace a prior file, including a symlink or a broken symlink."""
    with path.open("xb") as stream:
        stream.write(data)


def make_output(path: Path) -> Path:
    # Require the parent to exist: no recursive directory construction or cleanup.
    # mkdir(exist_ok=False) refuses existing directories and symbolic links.
    path.mkdir(exist_ok=False)
    return path


def test_child() -> int:
    import test_sample_session
    test_sample_session.ROOT = ROOT
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_sample_session.SampleSessionTests)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stderr).run(suite)
    record = {"run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped),
              "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses),
              "optimization": sys.flags.optimize}
    print(RESULT_MARKER + json.dumps(record, sort_keys=True))
    return 0 if result.wasSuccessful() and record["run"] > 0 and not any(
        record[key] for key in ("skipped", "expected_failures", "unexpected_successes")) else 1


def checked_result(output: str, returncode: int, optimization: int) -> dict:
    rows = [line[len(RESULT_MARKER):] for line in output.splitlines()
            if line.startswith(RESULT_MARKER)]
    if returncode != 0 or len(rows) != 1:
        raise RuntimeError("Browser test subprocess failed or did not produce one result.")
    result = json.loads(rows[0])
    expected = {"run", "failures", "errors", "skipped", "expected_failures",
                "unexpected_successes", "optimization"}
    if not isinstance(result, dict) or set(result) != expected:
        raise RuntimeError("Malformed browser test result.")
    if any(type(value) is not int or value < 0 for value in result.values()):
        raise RuntimeError("Browser test result contains invalid counts.")
    if result["run"] < 1 or result["optimization"] != optimization:
        raise RuntimeError("Empty suite or incorrect Python optimization mode.")
    if any(result[key] for key in expected - {"run", "optimization"}):
        raise RuntimeError("A browser test failed, errored, skipped or expected failure.")
    return result


def run_tests(out: Path, optimization: int) -> dict:
    command = [sys.executable, "-O" if optimization else "-B", str(Path(__file__).resolve()),
               "--test-child"]
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    env.pop("UIOWA_UI_ROOT", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                             text=True, encoding="utf-8", timeout=180, check=False)
    name = "optimized-tests.txt" if optimization else "normal-tests.txt"
    write_new(out / name, (process.stderr + process.stdout).encode("utf-8"))
    return checked_result(process.stdout, process.returncode, optimization)


def capture(out: Path) -> dict:
    import test_sample_session
    test_sample_session.ROOT = ROOT
    case_type = test_sample_session.SampleSessionTests
    case_type.setUpClass()
    case = case_type(methodName="test_two_consecutive_edit_reset_runs_are_identical")
    try:
        case.setUp()
        case.load()
        initial = case.snapshot()
        clean = case.export("clean.json").read_bytes()
        write_new(out / "clean_handoff.json", clean)
        case.edit("SYNTHETIC REHEARSAL: request the fictional security evidence, not a University finding.")
        edited_path = case.export("edited.json")
        edited = edited_path.read_bytes()
        write_new(out / "edited_handoff.json", edited)
        for cycle in (1, 2):
            case.page.locator("#demoResetBtn").click()
            case.assertEqual(case.snapshot(), initial)
            case.assertEqual(case.export(f"reset-{cycle}.json").read_bytes(), clean)
            case.assertEqual(edited_path.read_bytes(), edited)
            if cycle == 1:
                case.edit("SECOND SYNTHETIC REHEARSAL EDIT")
        case.page.set_viewport_size({"width": 1280, "height": 960})
        case.page.evaluate("window.scrollTo(0, 0)")
        write_new(out / "sample-reset.png", case.page.screenshot(full_page=True))
        case.page.locator("#demoExitBtn").click()
        case.assertIsNone(case.page.evaluate("state.report"))
        case.assertEqual((out / "edited_handoff.json").read_bytes(), edited)
        case.tearDown()
        return {"browser_version": case.browser.version, "repeated_cycles": 2,
                "clean_exports_identical": True, "edited_download_preserved": True,
                "leave_returned_to_empty": True}
    finally:
        case.doCleanups()
        case_type.tearDownClass()


def replay(out: Path) -> dict:
    out = make_output(out)
    before = {name: digest(ROOT / name) for name in ASSETS}
    try:
        normal = run_tests(out, 0)
        optimized = run_tests(out, 1)
        if normal["run"] != optimized["run"]:
            raise RuntimeError("Normal and optimized runs collected different test counts.")
        observed = capture(out)
        after = {name: digest(ROOT / name) for name in ASSETS}
        if before != after:
            raise RuntimeError("Source changed while the replay was running; no PASS is issued.")
        receipt = {"schema": "uiowa-125-synthetic-replay/v1", "result": "PASS",
                   "classification": "SYNTHETIC_UI_ONLY_NOT_COMPILER_OUTPUT",
                   "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                   "tests_normal": normal, "tests_optimized": optimized,
                   "demonstration": observed, "source_files": before,
                   "outputs": {path.name: digest(path) for path in sorted(out.iterdir())},
                   "limits": ["Actual Chromium with repository UI bytes; transport test responses are synthetic.",
                              "This run is not server/compiler execution or GitHub Actions authority.",
                              "Sample/prior work exists only in tab memory; export before closing or reloading."]}
        write_new(out / "run_receipt.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
        return receipt
    except Exception as error:
        failure = {"result": "FAIL", "error_type": type(error).__name__, "error": str(error),
                   "classification": "SYNTHETIC_REPLAY_FAILURE_NOT_A_PASS"}
        write_new(out / "failure.json", (json.dumps(failure, indent=2) + "\n").encode("utf-8"))
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="New output directory; parent must exist. Existing paths are refused.")
    parser.add_argument("--test-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.test_child:
        return test_child()
    if args.out is None:
        parser.error("--out is required")
    try:
        receipt = replay(args.out)
    except Exception as error:
        print(f"REPLAY FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"SYNTHETIC REPLAY PASS: {receipt['tests_normal']['run']} normal + "
          f"{receipt['tests_optimized']['run']} optimized tests; two byte-identical resets. "
          f"Outputs: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
