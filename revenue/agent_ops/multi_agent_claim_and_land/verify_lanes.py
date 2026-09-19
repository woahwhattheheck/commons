#!/usr/bin/env python3
"""Independent re-verification of what a swarm says it landed.

An agent reporting its own test results is the weakest link in a multi-agent
build. Not because agents lie, but because a stale or fabricated pass corrupts
the board every *other* agent reads to decide what to do next -- one phantom
"complete" and the rest of the fleet starts planning against fiction.

So: don't read the receipt, re-run the suite. This walks the landed lanes,
executes each one's tests in a subprocess from the lane's own directory, and
reports what actually happened. It is deliberately vendor-blind -- it verifies
every lane it finds, regardless of which swarm produced it.

Usage:
    python3 verify_lanes.py <repo-root> [--glob revenue/uiowa_rfq_18649_*]
                                        [--timeout 180] [--json out.json]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

TEST_GLOBS = ("test_*.py", "*_test.py", "tests/test_*.py")


def find_lanes(root, pattern):
    return sorted(d for d in glob.glob(os.path.join(root, pattern)) if os.path.isdir(d))


def find_tests(lane):
    found = []
    for g in TEST_GLOBS:
        found.extend(sorted(glob.glob(os.path.join(lane, g))))
    # Deduplicate while preserving order; a lane can match two globs.
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def dirty_paths(repo, lane):
    """Tracked files under `lane` that differ from HEAD, per git."""
    rel = os.path.relpath(lane, repo)
    p = subprocess.run(f"git status --porcelain -- '{rel}'", cwd=repo,
                       shell=True, capture_output=True, text=True)
    return sorted(
        line[3:].strip() for line in p.stdout.splitlines() if line[3:].strip()
    )


def restore(repo, paths):
    if not paths:
        return
    subprocess.run("git checkout -- " + " ".join(f"'{p}'" for p in paths),
                   cwd=repo, shell=True, capture_output=True, text=True)


def run_tests(lane, timeout, repo=None):
    """Run a lane's tests from inside the lane, so its relative paths resolve.

    Tests run IN PLACE rather than in a copy, because several lanes bind to
    repo-relative paths and would fail spuriously somewhere else. The cost is
    that a non-hermetic suite -- one that writes into its own tracked fixtures
    -- leaves the working tree dirty. Verifying something must not modify it,
    so we snapshot what git considers dirty before and after, restore anything
    the run touched, and report the lane as non-hermetic. That turns a
    recurring cleanup chore into a measured property of the lane.
    """
    tests = find_tests(lane)
    if not tests:
        return {"status": "NO-TESTS", "detail": "no test_*.py in lane", "tests": 0}

    before = dirty_paths(repo, lane) if repo else []

    total, failures, skipped, details = 0, 0, 0, []
    for t in tests:
        started = time.perf_counter()
        # Run by path RELATIVE TO THE LANE, not basename: a lane with its tests
        # in tests/ would otherwise be invoked as a file that isn't there, and
        # the harness would report a false failure against someone's landed
        # work. Publishing a phantom failure is exactly as corrupting as
        # publishing a phantom pass.
        rel = os.path.relpath(t, lane)
        try:
            p = subprocess.run(
                [sys.executable, rel],
                cwd=lane, capture_output=True, text=True, timeout=timeout,
            )
            out = (p.stderr or "") + (p.stdout or "")
            # unittest writes its summary to stderr; parse the count it reports
            # rather than counting our own test files.
            n = 0
            for line in out.splitlines():
                if line.startswith("Ran ") and " test" in line:
                    try:
                        n = int(line.split()[1])
                    except (IndexError, ValueError):
                        n = 0
            total += n
            ok = p.returncode == 0
            # A file named test_*.py is not necessarily a test module -- e.g.
            # a "test data assessor" CLI matches the glob and then exits with
            # an argparse usage error. That is the harness picking the wrong
            # file, not the lane failing, so it must not be counted as a
            # failure. The tell is: unittest never reported "Ran N tests".
            not_a_test = (not ok) and n == 0 and (
                "usage:" in out or "the following arguments are required" in out
            )
            if not_a_test:
                skipped += 1
            elif not ok:
                failures += 1
            details.append({
                "file": rel,
                "not_a_test": not_a_test,
                "ok": ok,
                "ran": n,
                "seconds": round(time.perf_counter() - started, 3),
                "tail": out.strip().splitlines()[-1] if out.strip() else "",
            })
        except subprocess.TimeoutExpired:
            failures += 1
            details.append({"file": rel, "not_a_test": False, "ok": False,
                            "ran": 0, "seconds": timeout,
                            "tail": f"TIMEOUT after {timeout}s"})
        except Exception as e:  # a lane that cannot even start is a real result
            failures += 1
            details.append({"file": rel, "not_a_test": False, "ok": False,
                            "ran": 0, "seconds": 0, "tail": f"ERROR {e}"})

    wrote = []
    if repo:
        after = dirty_paths(repo, lane)
        wrote = [p for p in after if p not in before]
        restore(repo, wrote)

    if failures == 0 and total == 0 and skipped:
        # Every glob hit was a non-test file; the lane genuinely has no suite.
        return {"status": "NO-TESTS", "detail": "matched files are not test modules",
                "tests": 0, "skipped": skipped, "files": details,
                "non_hermetic": wrote}
    return {
        "status": "PASS" if failures == 0 else "FAIL",
        "tests": total,
        "skipped": skipped,
        "files": details,
        "non_hermetic": wrote,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--glob", default="revenue/uiowa_rfq_18649_*")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--json")
    args = ap.parse_args()

    lanes = find_lanes(args.root, args.glob)
    # Whole-run snapshot. Per-lane restore is not sufficient on its own:
    # several lanes here execute OTHER lanes' commands as part of their own
    # verification (a capability appendix that runs each claim's demonstration,
    # a command index that executes what it indexes). So lane B's run can
    # re-dirty lane A after A was already restored. Snapshot once at the start
    # and sweep once at the end.
    run_before = dirty_paths(args.root, args.root)
    results, passed, failed, untested, total_tests = [], 0, 0, 0, 0

    for lane in lanes:
        name = os.path.basename(lane)
        r = run_tests(lane, args.timeout, repo=args.root)
        r["lane"] = name
        results.append(r)
        total_tests += r.get("tests", 0)
        if r["status"] == "PASS":
            passed += 1
        elif r["status"] == "FAIL":
            failed += 1
        else:
            untested += 1
        print(f"{r['status']:<9} {name:<52} {r.get('tests', 0):>4} tests")
        for d in r.get("files", []):
            if not d["ok"] and not d.get("not_a_test"):
                print(f"          └─ {d['file']}: {d['tail']}")
            elif d.get("not_a_test"):
                print(f"          └─ {d['file']}: skipped, not a test module")
        if r.get("non_hermetic"):
            print(f"          └─ NON-HERMETIC: run modified "
                  f"{len(r['non_hermetic'])} tracked file(s), restored: "
                  + ", ".join(os.path.basename(p) for p in r["non_hermetic"]))

    print("-" * 78)
    nonherm = [r["lane"] for r in results if r.get("non_hermetic")]
    print(f"lanes={len(lanes)}  pass={passed}  fail={failed}  no-tests={untested}  "
          f"tests-executed={total_tests}  non-hermetic={len(nonherm)}")
    if nonherm:
        print("non-hermetic lanes (wrote into tracked files; restored): "
              + " ".join(nonherm))

    # Final sweep: anything dirty now that was clean when we started belongs to
    # this run, not to the working tree, and must not survive verification.
    leftover = [p for p in dirty_paths(args.root, args.root) if p not in run_before]
    if leftover:
        restore(args.root, leftover)
        still = [p for p in dirty_paths(args.root, args.root) if p not in run_before]
        print(f"run-level sweep: restored {len(leftover)} file(s) left dirty by "
              f"cross-lane execution" + (f"; {len(still)} could NOT be restored: "
              + " ".join(still) if still else ""))

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"lanes": len(lanes), "pass": passed, "fail": failed,
                       "no_tests": untested, "tests_executed": total_tests,
                       "results": results}, f, indent=2)
        print(f"wrote {args.json}")

    # A lane with no tests is a finding, not a failure -- it is reported, but
    # only an actual failing suite sets a nonzero exit.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
