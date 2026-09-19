#!/usr/bin/env python3
"""Find checks that have stopped checking, across every landed lane.

The defect class: an integrity check whose expected value is written by the
same run that verifies it. A manifest that rewrites its own sha256 to match
whatever the suite just produced is a hash that can never fail -- it reports
PASS whether or not the artefact drifted. Nothing shows up red, which is
exactly why these survive.

This is the cross-lane version of the rule the traceability bundle next door
enforces on itself: recording an expected value is a DELIBERATE act, never a
side effect of running the check (see README, "Nothing self-heals").

Method, in descending order of confidence:

  1. BEHAVIOURAL (high confidence). Copy a lane to a scratch directory, hash
     every file, run the lane's own test suite there, hash everything again.
     Any tracked file the suite rewrote is non-hermetic. If a rewritten file
     also carried digest-shaped values and those values CHANGED, the check is
     self-sealing.
  2. STATIC (advisory). Flag source that writes a computed digest back into a
     file it also reads as the expected value. A static hit is a place to
     look, not a verdict.

Nothing in the repository is modified: every lane is copied first and the copy
is what runs. Python 3 standard library only, no network.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules"}
DIGEST_RE = re.compile(r"\b[0-9a-f]{32,64}\b")
STATIC_PATTERNS = [
    (re.compile(r"\[[\"']sha256[\"']\]\s*=", re.I), "assigns into a sha256 field"),
    (re.compile(r"[\"']sha256[\"']\s*:\s*(hashlib|_?(sha|digest|file_sha))", re.I),
     "builds a manifest entry from a freshly computed digest"),
]


def snapshot(root):
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, "rb") as f:
                    body = f.read()
            except OSError:
                continue
            out[os.path.relpath(full, root)] = (hashlib.sha256(body).hexdigest(), body)
    return out


def digests_in(body):
    return set(DIGEST_RE.findall(body.decode("utf-8", "replace")))


def run_suite(workdir, test_files, timeout):
    """Run the lane's own tests in the copy. A crash is a result, not an abort."""
    mods = [os.path.splitext(os.path.basename(t))[0] for t in test_files]
    try:
        p = subprocess.run([sys.executable, "-m", "unittest"] + mods,
                           cwd=workdir, capture_output=True, text=True, timeout=timeout)
        tail = (p.stderr or p.stdout).strip().splitlines()
        return {"ran": True, "returncode": p.returncode,
                "summary": tail[-1] if tail else "", "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"ran": True, "returncode": None, "summary": "TIMEOUT", "timed_out": True}
    except Exception as exc:
        return {"ran": False, "returncode": None, "summary": str(exc), "timed_out": False}


def static_scan(root):
    hits = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for pat, why in STATIC_PATTERNS:
                    if pat.search(line):
                        hits.append({"file": os.path.relpath(full, root), "line": i,
                                     "why": why, "text": line.strip()[:120]})
                        break
    return hits


def _restore(scratch, pristine, changed):
    """Put the tree back so the next lane starts from clean bytes."""
    for rel in changed:
        src, dst = os.path.join(pristine, rel), os.path.join(scratch, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        elif os.path.exists(dst):
            os.remove(dst)


def audit_lane(scratch, pristine, lane_name, timeout):
    """Audit one lane inside a shared copy of the whole tree.

    Why a shared tree and not a lone directory: the first version of this tool
    copied each lane on its own, and reported uiowa_rfq_18649_acceptance_map as
    TESTS_NOT_GREEN with six failures. It was a false positive of my own
    making -- that suite reads ACCEPTANCE_EXHIBIT.md from a SIBLING lane, and
    isolating the lane deleted the file it was pointing at. A checker that
    manufactures failures is the same defect class as one that manufactures
    passes, so the isolation model had to change rather than the verdict.
    """
    lane = os.path.join(scratch, lane_name)
    groups = {}
    for dirpath, dirnames, files in os.walk(lane):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        # Tests under fixtures/ are DATA, not this lane's suite. The operator
        # handoff kit ships a minikit whose README says outright: "Status:
        # production ready. All checks green. That claim is false and is here
        # on purpose: the verifier must contradict a README that asserts a
        # component works." Reporting that fixture's intended failure as a
        # defect would be the tool inventing a finding.
        if "fixtures" in os.path.relpath(dirpath, lane).split(os.sep):
            continue
        for fn in sorted(files):
            if fn.startswith("test_") and fn.endswith(".py"):
                groups.setdefault(dirpath, []).append(os.path.join(dirpath, fn))
    result = {"lane": lane_name, "tests": sorted(os.path.basename(f)
                                                 for g in groups.values() for f in g),
              "mutated": [], "foreign_writes": [], "self_sealing": [],
              "static_hits": static_scan(lane), "suite": None, "verdict": "NO_TESTS"}
    if not groups:
        if result["static_hits"]:
            result["verdict"] = "NO_TESTS_STATIC_HIT"
        return result

    before = snapshot(scratch)
    summaries, worst = [], 0
    for workdir in sorted(groups):
        out = run_suite(workdir, groups[workdir], timeout)
        summaries.append("%s: %s" % (os.path.relpath(workdir, scratch), out["summary"]))
        if out["returncode"]:
            worst = out["returncode"]
        if out["timed_out"]:
            worst = worst or 99
    result["suite"] = {"summary": " | ".join(summaries), "returncode": worst}
    after = snapshot(scratch)

    changed = []
    lane_prefix = lane_name + os.sep
    for rel in sorted(set(before) | set(after)):
        b, a = before.get(rel), after.get(rel)
        if b is not None and a is not None and b[0] == a[0]:
            continue
        changed.append(rel)
        change = "created" if b is None else ("deleted" if a is None else "rewritten")
        entry = {"file": rel, "change": change}
        if change == "rewritten":
            moved = digests_in(a[1]) - digests_in(b[1])
            if moved and digests_in(b[1]):
                # The file carried digest values and they changed: running the
                # check rewrote its own expected value.
                entry["digests_changed"] = sorted(moved)[:3]
                result["self_sealing"].append(entry)
        if not rel.startswith(lane_prefix):
            result["foreign_writes"].append(entry)
        result["mutated"].append(entry)

    _restore(scratch, pristine, changed)

    if result["self_sealing"]:
        result["verdict"] = "SELF_SEALING"
    elif result["foreign_writes"]:
        result["verdict"] = "WRITES_OUTSIDE_LANE"
    elif result["mutated"]:
        result["verdict"] = "NON_HERMETIC"
    elif worst == 0:
        result["verdict"] = "CLEAN"
    else:
        result["verdict"] = "TESTS_NOT_GREEN"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="directory holding the lanes")
    ap.add_argument("--prefix", default="uiowa_rfq_18649_")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--only", help="audit a single lane by directory name")
    args = ap.parse_args(argv)

    names = sorted(d for d in os.listdir(args.root)
                   if d.startswith(args.prefix)
                   and os.path.isdir(os.path.join(args.root, d)))
    tmp = tempfile.mkdtemp(prefix="lane-audit-")
    try:
        # Two copies: one the suites run in, one pristine to restore from. The
        # repository itself is never touched.
        scratch, pristine = os.path.join(tmp, "run"), os.path.join(tmp, "pristine")
        for dest in (scratch, pristine):
            os.makedirs(dest)
            for n in names:
                shutil.copytree(os.path.join(args.root, n), os.path.join(dest, n))
        targets = [args.only] if args.only else names
        results = [audit_lane(scratch, pristine, n, args.timeout) for n in targets]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if args.format == "json":
        print(json.dumps(results, indent=2, sort_keys=True))
        return 1 if any(r["verdict"] == "SELF_SEALING" for r in results) else 0

    order = {"SELF_SEALING": 0, "WRITES_OUTSIDE_LANE": 1, "NON_HERMETIC": 2,
             "TESTS_NOT_GREEN": 3, "NO_TESTS_STATIC_HIT": 4, "CLEAN": 5, "NO_TESTS": 6}
    print("audited %d lane(s) under %s\n" % (len(results), args.root))
    for r in sorted(results, key=lambda r: (order.get(r["verdict"], 9), r["lane"])):
        if r["verdict"] in ("CLEAN", "NO_TESTS"):
            continue
        print("%-22s %s" % (r["verdict"], r["lane"]))
        if r["suite"]:
            print("    suite: %s" % r["suite"]["summary"])
        for m in r["mutated"][:6]:
            extra = ""
            if "digests_changed" in m:
                extra = "   <- DIGEST REWRITTEN: %s..." % m["digests_changed"][0][:16]
            print("    %-10s %s%s" % (m["change"], m["file"], extra))
        if len(r["mutated"]) > 6:
            print("    ... and %d more" % (len(r["mutated"]) - 6))
        print()
    untested = sorted(r["lane"] for r in results if r["verdict"] == "NO_TESTS")
    if untested:
        print("NO_TESTS -- these lanes have no runnable suite, so nothing here")
        print("was verified behaviourally. That is a coverage gap, not a pass:")
        for lane in untested:
            print("    %s" % lane)
        print()
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("summary: " + "  ".join("%s=%d" % (k, counts[k]) for k in sorted(counts)))
    return 1 if counts.get("SELF_SEALING") else 0


if __name__ == "__main__":
    raise SystemExit(main())
