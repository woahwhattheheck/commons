#!/usr/bin/env python3
"""OPS-RUN-SWEEP - does the delivery kit actually run?

Dozens of component lanes land onto one branch from more than one build swarm.
Every pass count published alongside them was produced by the seat that wrote
the code, in that seat's own session. Nobody has executed the whole tree
together on the integrated branch.

This sweeps it and reports three things SEPARATELY, because they are three
different claims:

    does it run          the suite was invoked and exited zero
    did it assert        the suite actually executed a test
    whose work is here   whether one lane directory holds one write history
                         or several

The guardrail that matters: **a suite that runs zero tests is never counted as
a pass.** `python3 -m unittest some_module` with no TestCase in it prints
"Ran 0 tests" and exits zero, so any naive sweep records it green. That is a
file being counted, not a test. It gets its own state, EMPTY, and it is
excluded from the pass rate rather than inflating it.

The second guardrail: **a lane with no test suite is UNKNOWN, not a failure.**
Several lanes are document deliverables, and one ships a standalone validator
instead of a unittest suite. Scoring those as failures would be inventing a
defect. They are categorised and left out of the pass denominator.

The third: **nothing here repairs anything.** The sweep reads and executes. It
never writes into a lane it did not create.

Python 3 standard library only. No network. Lane classification is
deterministic; wall-clock durations are recorded as observations and are
explicitly not part of the reproducible result.

    python3 run_sweep.py --root /path/to/repo --observed-on 2026-09-19
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys

# --------------------------------------------------------------------------
# Suite outcomes
# --------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"
EMPTY = "EMPTY"          # ran, exited zero, asserted nothing
TIMEOUT = "TIMEOUT"

# Lane categories. A lane with no unittest suite is not a failing lane.
TESTED = "TESTED"
EXECUTABLE_NO_SUITE = "EXECUTABLE_NO_SUITE"
DOCUMENTS_ONLY = "DOCUMENTS_ONLY"

RAN_RE = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s$", re.MULTILINE)
SEAT_RE = re.compile(r"\b(OP5-[A-Z0-9]+|ZZ-[A-Za-z0-9-]+|ZCCW-[A-Za-z0-9]+|"
                     r"ANVIL-[A-Za-z0-9]+|KESTREL-[A-Za-z0-9]+|LOOM-[A-Za-z0-9]+|"
                     r"IBIS-[A-Za-z0-9]+|PEREGRINE-[A-Za-z0-9]+)\b")

# Seat tokens that are references to the fleet in general rather than a claim
# of authorship. Matching these would make every lane look multi-seat.
SEAT_NOISE = {"ZZ-", "OP5-"}

# unittest turns a module that will not import into a synthetic failing test
# (`unittest.loader._FailedTest`), so it reports "Ran 1 test ... FAILED". That
# looks identical to a real assertion failure in a summary, and it is not the
# same finding: one says a test is wrong, the other says the module never
# loaded. This marker is how the two are told apart.
LOADER_FAILURE_MARKERS = (
    "unittest.loader._FailedTest",
    "Failed to import test module",
)


def parse_unittest_output(text):
    """Pull the test count out of a unittest run.

    Returns (count, status_line). A run with no 'Ran N tests' line means the
    module never got as far as running anything, which is an ERROR, not zero
    tests that happened to pass.
    """
    match = None
    for match in RAN_RE.finditer(text or ""):
        pass
    count = int(match.group(1)) if match else None
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    status = lines[-1] if lines else ""
    return count, status


def classify(exit_code, count, status, timed_out, output=""):
    if timed_out:
        return TIMEOUT
    if any(marker in (output or "") for marker in LOADER_FAILURE_MARKERS):
        # The module did not load. Reported as ERROR even though unittest
        # dressed it up as a failing test.
        return ERROR
    if count is None:
        # Never reached the runner at all: a crash, or output this parser
        # does not recognise. Also not a test that ran and failed.
        return ERROR
    if exit_code != 0 or status.startswith("FAILED"):
        return FAIL
    if count == 0:
        return EMPTY
    return PASS


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def discover_suites(lane_dir):
    """Every unittest entry point in a lane.

    Looks at the lane root AND a `tests/` subdirectory, because a lane whose
    root-level `test_*.py` holds no TestCase while the real suite sits in
    `tests/` is precisely the case a one-file-per-lane sweep gets wrong.
    """
    suites = []
    for name in sorted(os.listdir(lane_dir)):
        if not name.endswith(".py"):
            continue
        if name.startswith("test_") or name.endswith("_test.py"):
            suites.append({"kind": "module", "module": name[:-3], "path": name})
    tests_dir = os.path.join(lane_dir, "tests")
    if os.path.isdir(tests_dir):
        has_tests = any(n.startswith("test_") and n.endswith(".py")
                        for n in os.listdir(tests_dir))
        if has_tests:
            suites.append({"kind": "discover", "module": "tests", "path": "tests/"})
    return suites


def lane_category(lane_dir, suites):
    if suites:
        return TESTED
    for root, dirs, files in os.walk(lane_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if any(f.endswith(".py") for f in files):
            return EXECUTABLE_NO_SUITE
    return DOCUMENTS_ONLY


def seats_named_in(lane_dir):
    """Seats named inside a lane's own documentation and source.

    Evidence-based and deliberately conservative: it reports the seat tokens
    that actually appear in the lane's text. Two distinct seats naming
    themselves inside one directory is worth a reviewer's attention; it is not
    by itself a defect, and this never guesses at authorship.
    """
    seats = set()
    readmes = []
    root_readmes = []
    for root, dirs, files in os.walk(lane_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(files):
            if name.lower().startswith("readme") and name.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, name), lane_dir)
                readmes.append(rel)
                # Two READMEs at the lane ROOT means two write histories in one
                # directory. Nested ones are almost always fixture content, so
                # counting those would make every kit with a sample tree look
                # like a collision.
                if os.path.dirname(rel) == "":
                    root_readmes.append(rel)
            if not (name.endswith(".md") or name.endswith(".py")):
                continue
            try:
                with open(os.path.join(root, name), encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
            except (IOError, OSError):
                continue
            for token in SEAT_RE.findall(text):
                if token not in SEAT_NOISE:
                    seats.add(token)
    return sorted(seats), sorted(readmes), sorted(root_readmes)


def has_declared_prerequisites(lane_dir):
    for name in ("requirements.txt", "pyproject.toml", "Pipfile"):
        if os.path.isfile(os.path.join(lane_dir, name)):
            return name
    return None


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------

def run_suite(lane_dir, suite, timeout):
    if suite["kind"] == "discover":
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    else:
        command = [sys.executable, "-m", "unittest", suite["module"]]
    timed_out = False
    try:
        proc = subprocess.run(command, cwd=lane_dir, timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.stdout.decode("utf-8", "replace")
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.output or b"").decode("utf-8", "replace")
        exit_code = None
        timed_out = True
    except OSError as exc:
        return {
            "suite": suite["path"], "command": " ".join(command),
            "outcome": ERROR, "exit_code": None, "tests_run": None,
            "status_line": "could not execute: %s" % exc, "tail": "",
        }

    count, status = parse_unittest_output(output)
    outcome = classify(exit_code, count, status, timed_out, output)
    note = ""
    if outcome == ERROR and count:
        # unittest counts its own `_FailedTest` placeholder as a test. Nothing
        # of the module's own actually ran, so counting it would inflate the
        # executed-test total with a test that does not exist.
        note = ("module did not load; unittest's synthetic placeholder test "
                "is not counted as executed")
        count = 0
    tail = "\n".join([ln for ln in output.splitlines() if ln.strip()][-12:])
    return {
        "suite": suite["path"],
        "command": " ".join(command),
        "outcome": outcome,
        "exit_code": exit_code,
        "tests_run": count,
        "status_line": status,
        "note": note,
        "tail": tail if outcome != PASS else "",
    }


def sweep(root, pattern, timeout, observed_on):
    revenue = os.path.join(root, "revenue")
    base = revenue if os.path.isdir(revenue) else root
    lanes = []
    prefix = pattern.rstrip("*")
    for name in sorted(os.listdir(base)):
        lane_dir = os.path.join(base, name)
        if not os.path.isdir(lane_dir) or not name.startswith(prefix):
            continue
        suites = discover_suites(lane_dir)
        category = lane_category(lane_dir, suites)
        seats, readmes, root_readmes = seats_named_in(lane_dir)
        results = [run_suite(lane_dir, s, timeout) for s in suites]
        outcomes = [r["outcome"] for r in results]

        if category != TESTED:
            lane_outcome = "NO_SUITE"
        elif FAIL in outcomes or ERROR in outcomes or TIMEOUT in outcomes:
            lane_outcome = FAIL
        elif PASS in outcomes:
            # A lane with a real suite plus an empty module still passes, but
            # the empty module is reported so it can be removed or filled.
            lane_outcome = PASS
        else:
            lane_outcome = EMPTY

        lanes.append({
            "lane": name,
            "category": category,
            "lane_outcome": lane_outcome,
            "suite_count": len(suites),
            "tests_run_total": sum(r["tests_run"] or 0 for r in results),
            "suites": results,
            "seats_named": seats,
            "multi_seat": len(seats) > 1,
            "readme_files": readmes,
            "root_readme_files": root_readmes,
            "shared_directory_signal": len(root_readmes) > 1,
            "prerequisites_file": has_declared_prerequisites(lane_dir),
        })
    return {
        "observed_on": observed_on,
        "root": base,
        "pattern": pattern,
        "lanes": lanes,
        "summary": summarise(lanes),
        "note": ("Durations are observations of one machine at one moment and "
                 "are not part of the reproducible result. Lane classification "
                 "is deterministic given the same tree."),
    }


def summarise(lanes):
    tested = [l for l in lanes if l["category"] == TESTED]
    empty_suites = []
    for lane in lanes:
        for suite in lane["suites"]:
            if suite["outcome"] == EMPTY:
                empty_suites.append("%s::%s" % (lane["lane"], suite["suite"]))
    return {
        "lanes_seen": len(lanes),
        "lanes_with_a_suite": len(tested),
        "lanes_passing": sum(1 for l in tested if l["lane_outcome"] == PASS),
        "lanes_failing": sum(1 for l in tested if l["lane_outcome"] == FAIL),
        "lanes_asserting_nothing": sum(1 for l in tested
                                       if l["lane_outcome"] == EMPTY),
        "lanes_without_a_suite": sum(1 for l in lanes
                                     if l["category"] == EXECUTABLE_NO_SUITE),
        "lanes_documents_only": sum(1 for l in lanes
                                    if l["category"] == DOCUMENTS_ONLY),
        "tests_executed": sum(l["tests_run_total"] for l in lanes),
        "empty_suites": sorted(empty_suites),
        "multi_seat_lanes": sorted(l["lane"] for l in lanes if l["multi_seat"]),
        "shared_directory_lanes": sorted(l["lane"] for l in lanes
                                         if l["shared_directory_signal"]),
        "lanes_with_prerequisites": sorted(
            l["lane"] for l in lanes if l["prerequisites_file"]),
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

CSV_COLUMNS = ["lane", "category", "lane_outcome", "suite_count",
               "tests_run_total", "empty_suites", "failing_suites",
               "seats_named", "prerequisites_file"]

UNKNOWN = "UNKNOWN"


def _cell(value):
    if value is None:
        return UNKNOWN
    if isinstance(value, list):
        return "; ".join(str(v) for v in value) if value else "none"
    text = str(value)
    if text[:1] in ("=", "+", "@") or (text[:1] == "-" and not text[1:2].isdigit()):
        return "'" + text
    return text


def write_csv(report, path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for lane in report["lanes"]:
            empties = [s["suite"] for s in lane["suites"] if s["outcome"] == EMPTY]
            failing = [s["suite"] for s in lane["suites"]
                       if s["outcome"] in (FAIL, ERROR, TIMEOUT)]
            writer.writerow([
                _cell(lane["lane"]), _cell(lane["category"]),
                _cell(lane["lane_outcome"]), _cell(lane["suite_count"]),
                _cell(lane["tests_run_total"]), _cell(empties), _cell(failing),
                _cell(lane["seats_named"]), _cell(lane["prerequisites_file"]),
            ])
    return path


def render_report(report):
    s = report["summary"]
    out = []
    out.append("# Delivery-kit run sweep")
    out.append("")
    out.append("Executed on **%s** against `%s`. Every figure below is an "
               "observation of running the code, not a count reported by the "
               "seat that wrote it." % (report["observed_on"], report["root"]))
    out.append("")
    out.append("## Three claims, kept apart")
    out.append("")
    out.append("- **Does it run** - the suite was invoked and exited zero.")
    out.append("- **Did it assert** - the suite actually executed a test. A "
               "module with no test case prints `Ran 0 tests` and exits zero, "
               "so it passes any naive sweep. Here it is `EMPTY` and is "
               "excluded from the pass rate.")
    out.append("- **Whose work is here** - how many seats are named inside one "
               "lane directory.")
    out.append("")
    out.append("A lane with no test suite is `NO_SUITE`, not a failure. Some "
               "lanes are document deliverables and one ships a standalone "
               "validator; scoring those as broken would be inventing a defect.")
    out.append("")
    out.append("## Position")
    out.append("")
    out.append("| Measure | Count |")
    out.append("|---|---|")
    out.append("| Lanes seen | %d |" % s["lanes_seen"])
    out.append("| Lanes with a unittest suite | %d |" % s["lanes_with_a_suite"])
    out.append("| ... passing | %d |" % s["lanes_passing"])
    out.append("| ... failing | %d |" % s["lanes_failing"])
    out.append("| ... asserting nothing | %d |" % s["lanes_asserting_nothing"])
    out.append("| Lanes with code but no suite | %d |" % s["lanes_without_a_suite"])
    out.append("| Lanes that are documents only | %d |" % s["lanes_documents_only"])
    out.append("| **Tests actually executed** | **%d** |" % s["tests_executed"])
    out.append("")

    failing = [l for l in report["lanes"] if l["lane_outcome"] == FAIL]
    out.append("## Lanes that do not run clean")
    out.append("")
    if not failing:
        out.append("None. Every lane with a suite ran and asserted something.")
    for lane in failing:
        out.append("### `%s`" % lane["lane"])
        out.append("")
        for suite in lane["suites"]:
            if suite["outcome"] == PASS:
                continue
            out.append("- `%s` -> **%s** (exit %s, %s tests) - %s" % (
                suite["suite"], suite["outcome"],
                suite["exit_code"] if suite["exit_code"] is not None else UNKNOWN,
                suite["tests_run"] if suite["tests_run"] is not None else UNKNOWN,
                suite["status_line"]))
            if suite["tail"]:
                out.append("")
                out.append("```")
                out.append(suite["tail"])
                out.append("```")
        out.append("")

    out.append("## Suites that assert nothing")
    out.append("")
    if not s["empty_suites"]:
        out.append("None.")
    else:
        out.append("These exit zero and would be counted green by a sweep that "
                   "trusts the exit code. They are not counted here.")
        out.append("")
        for item in s["empty_suites"]:
            out.append("- `%s`" % item)
    out.append("")

    out.append("## Lanes holding more than one write history")
    out.append("")
    out.append("The strong signal is **more than one README at the lane root**. "
               "That means two build efforts wrote into the same directory. "
               "READMEs nested inside `fixtures/` are sample content and are "
               "not counted, otherwise every kit shipping an example tree would "
               "look like a collision.")
    out.append("")
    if not s["shared_directory_lanes"]:
        out.append("None.")
    else:
        for lane_name in s["shared_directory_lanes"]:
            lane = [l for l in report["lanes"] if l["lane"] == lane_name][0]
            out.append("- `%s` - %d root-level README files (%s); names %s" % (
                lane_name, len(lane["root_readme_files"]),
                ", ".join(lane["root_readme_files"]),
                ", ".join(lane["seats_named"])))
    out.append("")
    out.append("### Lanes that merely name another seat")
    out.append("")
    out.append("Not a defect. A lane citing another seat's component, consuming "
               "its contract, or crediting a handoff lands here. Listed so the "
               "strong signal above is not confused with ordinary "
               "cross-referencing.")
    out.append("")
    weak = [n for n in s["multi_seat_lanes"] if n not in s["shared_directory_lanes"]]
    if not weak:
        out.append("None.")
    for lane_name in weak:
        lane = [l for l in report["lanes"] if l["lane"] == lane_name][0]
        out.append("- `%s` - names %s" % (lane_name, ", ".join(lane["seats_named"])))
    out.append("")

    out.append("## Lanes with declared prerequisites")
    out.append("")
    if not s["lanes_with_prerequisites"]:
        out.append("None. Every lane runs on the standard library alone.")
    else:
        out.append("These declare third-party dependencies. A reviewer who "
                   "clones and runs without installing them gets errors, so a "
                   "delivery kit needs to say so up front.")
        out.append("")
        for lane_name in s["lanes_with_prerequisites"]:
            lane = [l for l in report["lanes"] if l["lane"] == lane_name][0]
            out.append("- `%s` (`%s`)" % (lane_name, lane["prerequisites_file"]))
    out.append("")

    out.append("## What this sweep does not claim")
    out.append("")
    out.append("A passing suite means the suite passed. It is not a statement "
               "that the component is correct, complete, or fit for the "
               "engagement, and it is not a maturity rating of any lane or any "
               "seat. Nothing here was repaired: this reads and executes only.")
    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Execute every component lane's test suite on the "
                    "integrated tree and report what actually happened.")
    parser.add_argument("--root", default="/home/user/commons",
                        help="repository root (or a directory of lanes)")
    parser.add_argument("--pattern", default="uiowa_rfq_18649_",
                        help="lane directory name prefix")
    parser.add_argument("--outdir", default="out")
    parser.add_argument("--timeout", type=int, default=180,
                        help="seconds per suite before it is recorded TIMEOUT")
    parser.add_argument("--observed-on", required=True,
                        help="the date to record (YYYY-MM-DD). Required so the "
                             "output does not depend on the wall clock.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        sys.stderr.write("error: root %s does not exist\n" % args.root)
        return 2

    report = sweep(args.root, args.pattern, args.timeout, args.observed_on)

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    json_path = os.path.join(args.outdir, "run_sweep.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    csv_path = write_csv(report, os.path.join(args.outdir, "run_sweep.csv"))
    md_path = os.path.join(args.outdir, "run_sweep_report.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(report))
        handle.write("\n")

    s = report["summary"]
    if not args.quiet:
        print("lanes seen %d | with suite %d | passing %d | failing %d | "
              "asserting nothing %d" % (
                  s["lanes_seen"], s["lanes_with_a_suite"], s["lanes_passing"],
                  s["lanes_failing"], s["lanes_asserting_nothing"]))
        print("no suite: %d code-only, %d documents-only"
              % (s["lanes_without_a_suite"], s["lanes_documents_only"]))
        print("tests actually executed: %d" % s["tests_executed"])
        for lane in report["lanes"]:
            if lane["lane_outcome"] == FAIL:
                print("  FAIL %s" % lane["lane"])
        for item in s["empty_suites"]:
            print("  EMPTY %s" % item)
        for lane_name in s["shared_directory_lanes"]:
            print("  SHARED-DIRECTORY %s" % lane_name)
        for lane_name in s["multi_seat_lanes"]:
            if lane_name not in s["shared_directory_lanes"]:
                print("  cross-reference only: %s" % lane_name)
        for path in (json_path, csv_path, md_path):
            print("wrote %s" % path)
    # A failing lane is a real finding, and the exit code says so.
    return 1 if s["lanes_failing"] else 0


if __name__ == "__main__":
    sys.exit(main())
