#!/usr/bin/env python3
"""OPS-ONE-RUNNER - is the delivery kit safe to execute as a single job?

A per-lane sweep that runs each component in its own subprocess with its own
working directory proves every lane works ALONE. That is a different claim
from the kit working as one CI job, and the difference is where integration
defects live.

Four independent hazards, reported separately because they have different
causes and different fixes:

  cwd_independence   does a lane's suite behave the same when the working
                     directory is the repository root instead of the lane?
  module_collisions  do two lanes ship a top-level module with the same name?
  crosstalk          when two such lanes share one Python process, does the
                     second lane's import silently resolve to the first
                     lane's file?
  state_leakage      does a lane's test run write outside its own directory?

Crosstalk is the one that has no error message. Python caches by module name,
not by path, so the second lane asks for its own module and receives another
lane's. Every lane is correct in isolation; the kit is wrong the moment two of
them share an interpreter.

Guardrails:

  * A lane with no test suite is UNKNOWN, not a failure. Document lanes and
    lanes shipping a standalone validator are categorised and excluded from
    every denominator rather than scored as broken.
  * Nothing is repaired. This reads, executes and reports. The proposed fixes
    are a list; no file outside this lane is written.
  * A hazard that does not fire is published as a clean result, not omitted.
    A disproved hypothesis is a finding.

Python 3 standard library only. No network. Classification is deterministic;
the observation date is supplied rather than read from the clock.

    python3 one_runner.py --root /path/to/repo --observed-on 2026-09-19
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

UNKNOWN = "UNKNOWN"
PASS = "PASS"
FAIL = "FAIL"
NO_SUITE = "NO_SUITE"

IGNORED_DIRS = {"__pycache__", ".git", ".pytest_cache"}


# --------------------------------------------------------------------------
# Lane discovery
# --------------------------------------------------------------------------

def find_lanes(root, prefix):
    revenue = os.path.join(root, "revenue")
    base = revenue if os.path.isdir(revenue) else root
    lanes = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if os.path.isdir(path) and name.startswith(prefix):
            lanes.append((name, path))
    return base, lanes


def has_suite(lane_dir):
    for name in os.listdir(lane_dir):
        if name.endswith(".py") and (name.startswith("test_")
                                     or name.endswith("_test.py")):
            return True
    tests = os.path.join(lane_dir, "tests")
    if os.path.isdir(tests):
        return any(n.startswith("test_") and n.endswith(".py")
                   for n in os.listdir(tests))
    return False


def top_level_modules(lane_dir):
    """Modules a lane puts on sys.path when its directory is added.

    Only the lane root matters: that is the directory a runner adds. Files in
    subpackages are reached by a dotted name and do not collide the same way.
    """
    out = []
    for name in sorted(os.listdir(lane_dir)):
        if not name.endswith(".py"):
            continue
        stem = name[:-3]
        if stem.startswith("test_") or stem.endswith("_test"):
            continue
        out.append(stem)
    return out


# --------------------------------------------------------------------------
# Hazard 1 - working-directory independence
# --------------------------------------------------------------------------

def run_discover(cwd, start, timeout):
    command = [sys.executable, "-m", "unittest", "discover", "-s", start,
               "-t", start]
    try:
        proc = subprocess.run(command, cwd=cwd, timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return proc.returncode, proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    except OSError as exc:
        return "ERROR", str(exc)


def check_cwd_independence(base, lanes, timeout):
    """Run each suite from the lane and again from the repository root.

    A lane that opens `fixtures/x.json` relative to the process working
    directory passes the first and fails the second. Comparing the two is the
    only way to tell, because the first run alone always looks fine.
    """
    results = []
    for name, path in lanes:
        if not has_suite(path):
            results.append({"lane": name, "status": NO_SUITE,
                            "from_lane": UNKNOWN, "from_root": UNKNOWN,
                            "detail": "no test suite; not assessed"})
            continue
        from_lane, _out_a = run_discover(path, ".", timeout)
        from_root, out_b = run_discover(base, path, timeout)
        same = from_lane == from_root
        results.append({
            "lane": name,
            "status": PASS if same else FAIL,
            "from_lane": from_lane,
            "from_root": from_root,
            "detail": ("same outcome from both working directories" if same
                       else "outcome changed with the working directory; the "
                            "suite depends on where it is run from"),
            "tail": "" if same else "\n".join(
                [ln for ln in out_b.splitlines() if ln.strip()][-10:]),
        })
    return results


# --------------------------------------------------------------------------
# Hazard 2 - module-name collisions
# --------------------------------------------------------------------------

def check_module_collisions(lanes):
    owners = {}
    for name, path in lanes:
        for module in top_level_modules(path):
            owners.setdefault(module, []).append(name)
    collisions = []
    for module in sorted(owners):
        holders = sorted(owners[module])
        if len(holders) > 1:
            collisions.append({"module": module, "lanes": holders,
                               "lane_count": len(holders)})
    return {
        "distinct_modules": len(owners),
        "collisions": collisions,
        "collision_count": len(collisions),
    }


# --------------------------------------------------------------------------
# Hazard 3 - same-process crosstalk
# --------------------------------------------------------------------------

CROSSTALK_PROBE = r"""
import importlib, json, os, sys
lanes = json.loads(sys.argv[1])
module = sys.argv[2]
seen = []
for lane in lanes:
    sys.path.insert(0, os.path.abspath(lane))
    try:
        mod = importlib.import_module(module)
        seen.append({"asked_from": lane, "resolved_to": getattr(mod, "__file__", None)})
    except Exception as exc:
        seen.append({"asked_from": lane, "error": "%s: %s" % (type(exc).__name__, exc)})
print(json.dumps(seen))
"""


def check_crosstalk(base, collisions, timeout):
    """Demonstrate the shadowing rather than assert it.

    Each collision is exercised in a fresh subprocess: add lane A, import the
    module, then add lane B and import the same name again. Python returns the
    cached module, so B receives A's file. The result records which lanes were
    shadowed and by what.
    """
    demos = []
    for collision in collisions:
        module = collision["module"]
        lane_paths = [os.path.join(base, l) for l in collision["lanes"]]
        try:
            proc = subprocess.run(
                [sys.executable, "-c", CROSSTALK_PROBE,
                 json.dumps(lane_paths), module],
                cwd=base, timeout=timeout,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            raw = proc.stdout.decode("utf-8", "replace").strip()
            observations = json.loads(raw.splitlines()[-1]) if raw else []
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
            demos.append({"module": module, "lanes": collision["lanes"],
                          "shadowed": UNKNOWN,
                          "detail": "probe could not run: %s" % exc})
            continue

        winner = None
        shadowed = []
        for obs in observations:
            resolved = obs.get("resolved_to")
            if resolved is None:
                continue
            if winner is None:
                winner = resolved
            elif os.path.abspath(resolved) == os.path.abspath(winner):
                shadowed.append(os.path.basename(obs["asked_from"]))
        demos.append({
            "module": module,
            "lanes": collision["lanes"],
            "resolved_to": os.path.relpath(winner, base) if winner else UNKNOWN,
            "shadowed": shadowed,
            "observations": observations,
            "detail": ("%d lane(s) asked for their own `%s` and received "
                       "another lane's file, with no error raised."
                       % (len(shadowed), module)) if shadowed else
                      ("no shadowing observed for `%s`" % module),
        })
    return demos


# --------------------------------------------------------------------------
# Hazard 4 - state leakage
# --------------------------------------------------------------------------

def tree_signature(base, skip_dir=None):
    """(path -> size, mtime_ns) for everything under base except an excluded
    directory and caches. Stat rather than content hash: this only needs to
    detect that a write happened."""
    signature = {}
    skip = os.path.abspath(skip_dir) if skip_dir else None
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        if skip and os.path.abspath(root).startswith(skip):
            continue
        for name in files:
            full = os.path.join(root, name)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            signature[os.path.relpath(full, base)] = (stat.st_size,
                                                      stat.st_mtime_ns)
    return signature


def check_state_leakage(base, lanes, timeout):
    """Does a lane's test run write outside its own directory?

    Measured on an ISOLATED COPY, never on the live tree. The first version of
    this check watched the real repository around each run and reported two
    lanes as leaking. They were not: other seats were landing work into the
    same tree while the check was running, and the whole of two unrelated
    lanes appeared inside one measurement window. Any before/after watch of a
    directory that other writers share will attribute their writes to whatever
    happened to be running.

    So each lane is copied into a temp root that nothing else touches, given a
    sibling directory to write into if it wants to, and run there. A write
    anywhere in that root outside the lane's own copy is a genuine leak.
    """
    results = []
    for name, path in lanes:
        if not has_suite(path):
            results.append({"lane": name, "status": NO_SUITE,
                            "created": [], "modified": [], "removed": [],
                            "detail": "no test suite; not assessed",
                            "method": "isolated copy"})
            continue
        tmp = tempfile.mkdtemp(prefix="one_runner_")
        try:
            revenue = os.path.join(tmp, "revenue")
            lane_copy = os.path.join(revenue, name)
            shutil.copytree(path, lane_copy,
                            ignore=shutil.ignore_patterns(*IGNORED_DIRS))
            # A neighbour with a file in it, so a lane reaching sideways with a
            # relative path has somewhere real to land rather than erroring.
            neighbour = os.path.join(revenue, "uiowa_rfq_18649_zz_neighbour")
            os.makedirs(neighbour)
            with open(os.path.join(neighbour, "marker.txt"), "w") as handle:
                handle.write("marker\n")

            before = tree_signature(tmp, skip_dir=lane_copy)
            run_discover(lane_copy, ".", timeout)
            after = tree_signature(tmp, skip_dir=lane_copy)

            created = sorted(set(after) - set(before))
            removed = sorted(set(before) - set(after))
            modified = sorted(k for k in set(before) & set(after)
                              if before[k] != after[k])
            leaked = bool(created or removed or modified)
            results.append({
                "lane": name,
                "status": FAIL if leaked else PASS,
                "created": created, "removed": removed, "modified": modified,
                "detail": ("wrote outside its own directory" if leaked
                           else "wrote nothing outside its own directory"),
                "method": "isolated copy",
            })
        except (OSError, shutil.Error) as exc:
            results.append({"lane": name, "status": UNKNOWN,
                            "created": [], "modified": [], "removed": [],
                            "detail": "could not be isolated: %s" % exc,
                            "method": "isolated copy"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return results


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def analyse(root, prefix, timeout, observed_on, skip_leakage=False):
    base, lanes = find_lanes(root, prefix)
    cwd = check_cwd_independence(base, lanes, timeout)
    modules = check_module_collisions(lanes)
    crosstalk = check_crosstalk(base, modules["collisions"], timeout)
    leakage = ([] if skip_leakage
               else check_state_leakage(base, lanes, timeout))

    assessed = [r for r in cwd if r["status"] != NO_SUITE]
    leak_assessed = [r for r in leakage if r["status"] != NO_SUITE]
    shadowed_lanes = sorted({lane for demo in crosstalk
                             for lane in (demo.get("shadowed") or [])
                             if isinstance(demo.get("shadowed"), list)})

    summary = {
        "lanes_seen": len(lanes),
        "lanes_assessed": len(assessed),
        "lanes_without_a_suite": len(lanes) - len(assessed),
        "cwd_dependent_lanes": sorted(r["lane"] for r in assessed
                                      if r["status"] == FAIL),
        "distinct_top_level_modules": modules["distinct_modules"],
        "module_collisions": modules["collision_count"],
        "colliding_modules": [c["module"] for c in modules["collisions"]],
        "shadowed_lanes": shadowed_lanes,
        "leaking_lanes": sorted(r["lane"] for r in leak_assessed
                                if r["status"] == FAIL),
        "leakage_method": "isolated copy per lane; the live tree is never watched",
        "leakage_assessed": len(leak_assessed),
    }
    summary["single_process_safe"] = (
        not summary["module_collisions"] and not summary["leaking_lanes"])
    summary["cwd_safe"] = not summary["cwd_dependent_lanes"]

    return {
        "observed_on": observed_on,
        "root": base,
        "summary": summary,
        "cwd_independence": cwd,
        "modules": modules,
        "crosstalk": crosstalk,
        "state_leakage": leakage,
        "proposed_fixes": propose_fixes(modules["collisions"]),
        "note": ("A lane with no test suite is not assessed and is excluded "
                 "from every denominator. Nothing here was repaired."),
    }


def propose_fixes(collisions):
    """A list, not an edit. Each collision names the lanes that would have to
    agree on a rename; which one keeps the plain name is the lane owners' call
    and is deliberately not decided here."""
    fixes = []
    for collision in collisions:
        module = collision["module"]
        fixes.append({
            "module": module,
            "lanes": collision["lanes"],
            "options": [
                "rename the module in all but one lane, e.g. `%s_%s.py`"
                % (lane.replace("uiowa_rfq_18649_", ""), module)
                for lane in collision["lanes"]
            ],
            "alternative": ("or give each lane a package directory so the "
                            "module is reached as `<lane>.%s`" % module),
            "owner_decision": ("which lane keeps the plain name is for the "
                               "lane owners; this tool does not choose"),
        })
    return fixes


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

CSV_COLUMNS = ["lane", "cwd_independence", "from_lane_exit", "from_root_exit",
               "state_leakage", "files_written_outside_lane",
               "top_level_modules", "colliding_modules"]


def _cell(value):
    if value is None:
        return UNKNOWN
    if isinstance(value, list):
        return "; ".join(str(v) for v in value) if value else "none"
    text = str(value)
    if text[:1] in ("=", "+", "@") or (text[:1] == "-" and not text[1:2].isdigit()):
        return "'" + text
    return text


def write_csv(report, base, path):
    leak_by_lane = {r["lane"]: r for r in report["state_leakage"]}
    colliding = {}
    for collision in report["modules"]["collisions"]:
        for lane in collision["lanes"]:
            colliding.setdefault(lane, []).append(collision["module"])
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for row in report["cwd_independence"]:
            lane = row["lane"]
            leak = leak_by_lane.get(lane, {})
            written = (leak.get("created", []) + leak.get("modified", [])
                       + leak.get("removed", []))
            modules = top_level_modules(os.path.join(base, lane)) \
                if os.path.isdir(os.path.join(base, lane)) else []
            writer.writerow([
                _cell(lane), _cell(row["status"]), _cell(row["from_lane"]),
                _cell(row["from_root"]), _cell(leak.get("status", UNKNOWN)),
                _cell(written), _cell(modules),
                _cell(colliding.get(lane, [])),
            ])
    return path


def render_report(report):
    s = report["summary"]
    out = []
    out.append("# Single-runner readiness")
    out.append("")
    out.append("Observed **%s** against `%s`. Four hazards that a per-lane "
               "sweep cannot see, because a sweep gives every lane its own "
               "process and its own working directory."
               % (report["observed_on"], report["root"]))
    out.append("")
    out.append("| Hazard | Result |")
    out.append("|---|---|")
    out.append("| Working-directory independence | %s |" % (
        "clean across %d assessed lanes" % s["lanes_assessed"] if s["cwd_safe"]
        else "%d lane(s) depend on the working directory"
             % len(s["cwd_dependent_lanes"])))
    out.append("| Module-name collisions | %s |" % (
        "none across %d module names" % s["distinct_top_level_modules"]
        if not s["module_collisions"]
        else "%d name(s) shared by more than one lane: %s"
             % (s["module_collisions"], ", ".join(
                 "`%s`" % m for m in s["colliding_modules"]))))
    out.append("| Same-process crosstalk | %s |" % (
        "no shadowing observed" if not s["shadowed_lanes"]
        else "%d lane(s) silently receive another lane's module"
             % len(s["shadowed_lanes"])))
    out.append("| State leakage | %s |" % (
        "no lane wrote outside itself (%d assessed)" % s["leakage_assessed"]
        if not s["leaking_lanes"]
        else "%d lane(s) wrote outside their own directory"
             % len(s["leaking_lanes"])))
    out.append("")
    out.append("**Working-directory safe:** %s. **Single-process safe:** %s."
               % ("yes" if s["cwd_safe"] else "no",
                  "yes" if s["single_process_safe"] else "no"))
    out.append("")

    out.append("## Working-directory independence")
    out.append("")
    out.append("Every suite was run twice: once with the working directory at "
               "the lane, once at the repository root. A lane that opens a "
               "fixture by a path relative to the process working directory "
               "passes the first and fails the second, and the first run alone "
               "always looks fine.")
    out.append("")
    if s["cwd_safe"]:
        out.append("**No lane differed.** %d lanes assessed, %d not assessed "
                   "(no test suite). This is a verified property, not an "
                   "assumption." % (s["lanes_assessed"],
                                    s["lanes_without_a_suite"]))
    else:
        for row in report["cwd_independence"]:
            if row["status"] != FAIL:
                continue
            out.append("- `%s` - exit %s from the lane, exit %s from the root."
                       % (row["lane"], row["from_lane"], row["from_root"]))
            if row.get("tail"):
                out.append("")
                out.append("```")
                out.append(row["tail"])
                out.append("```")
    out.append("")

    out.append("## Module-name collisions")
    out.append("")
    out.append("%d distinct top-level module names across %d lanes. Test "
               "modules are excluded: a runner imports them by their own name "
               "and they are not what another lane imports."
               % (s["distinct_top_level_modules"], s["lanes_seen"]))
    out.append("")
    if not report["modules"]["collisions"]:
        out.append("No name is shared by more than one lane.")
    else:
        out.append("| Module | Lanes |")
        out.append("|---|---|")
        for collision in report["modules"]["collisions"]:
            out.append("| `%s.py` | %s |" % (
                collision["module"],
                ", ".join("`%s`" % l for l in collision["lanes"])))
    out.append("")

    out.append("## Same-process crosstalk")
    out.append("")
    out.append("Demonstrated, not argued. For each collision a fresh process "
               "adds one lane, imports the module, then adds the next lane and "
               "imports the same name. Python caches by name, so the second "
               "request returns the first lane's module object.")
    out.append("")
    if not report["crosstalk"]:
        out.append("Nothing to demonstrate: no colliding module names.")
    for demo in report["crosstalk"]:
        out.append("### `%s`" % demo["module"])
        out.append("")
        out.append("%s" % demo["detail"])
        out.append("")
        for obs in demo.get("observations", []):
            lane = os.path.basename(obs.get("asked_from", ""))
            if "error" in obs:
                out.append("- `%s` asked for `%s` - %s"
                           % (lane, demo["module"], obs["error"]))
            else:
                out.append("- `%s` asked for `%s` - received `%s`"
                           % (lane, demo["module"],
                              os.path.basename(
                                  os.path.dirname(obs["resolved_to"] or ""))
                              + "/" + os.path.basename(obs["resolved_to"] or "")))
        out.append("")

    out.append("## State leakage")
    out.append("")
    out.append("Measured on an isolated copy of each lane, never on the live "
               "tree. An earlier version of this check watched the real "
               "repository around each run and reported two lanes as leaking; "
               "they were not. Other seats were landing work into the same "
               "tree while it ran, and a before/after watch of a directory "
               "that other writers share attributes their writes to whatever "
               "happened to be running. `__pycache__` is excluded as a side "
               "effect of executing Python.")
    out.append("")
    if not report["state_leakage"]:
        out.append("Not assessed in this run.")
    elif not s["leaking_lanes"]:
        out.append("No lane wrote, modified or removed a file outside its own "
                   "directory during its test run. %d lanes assessed."
                   % s["leakage_assessed"])
    else:
        for row in report["state_leakage"]:
            if row["status"] != FAIL:
                continue
            out.append("- `%s` - created %s, modified %s, removed %s" % (
                row["lane"], row["created"] or "none",
                row["modified"] or "none", row["removed"] or "none"))
    out.append("")

    out.append("## Proposed fixes")
    out.append("")
    if not report["proposed_fixes"]:
        out.append("None needed.")
    else:
        out.append("A list, not an edit. Nothing outside this lane was "
                   "modified, and which lane keeps the plain module name is "
                   "the lane owners' decision.")
        out.append("")
        for fix in report["proposed_fixes"]:
            out.append("- `%s.py` in %s: rename in all but one, or give each "
                       "lane a package directory so it is reached as "
                       "`<lane>.%s`." % (
                           fix["module"],
                           ", ".join("`%s`" % l for l in fix["lanes"]),
                           fix["module"]))
    out.append("")

    out.append("## What this does not claim")
    out.append("")
    out.append("A clean result here means these four hazards were not "
               "observed. It is not a statement that any component is correct, "
               "and it is not a rating of any lane or any seat. Lanes without "
               "a test suite were not assessed and are not counted as either "
               "safe or unsafe.")
    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check whether the component lanes are safe to execute "
                    "as a single job.")
    parser.add_argument("--root", default="/home/user/commons")
    parser.add_argument("--pattern", default="uiowa_rfq_18649_")
    parser.add_argument("--outdir", default="out")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--observed-on", required=True,
                        help="the date to record (YYYY-MM-DD). Required so the "
                             "output does not depend on the wall clock.")
    parser.add_argument("--skip-leakage", action="store_true",
                        help="skip the state-leakage pass (the slow one)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        sys.stderr.write("error: root %s does not exist\n" % args.root)
        return 2

    base, _lanes = find_lanes(args.root, args.pattern)
    report = analyse(args.root, args.pattern, args.timeout, args.observed_on,
                     args.skip_leakage)

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    json_path = os.path.join(args.outdir, "one_runner.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    csv_path = write_csv(report, base, os.path.join(args.outdir, "one_runner.csv"))
    md_path = os.path.join(args.outdir, "one_runner_report.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(report))
        handle.write("\n")

    s = report["summary"]
    if not args.quiet:
        print("lanes %d | assessed %d | no suite %d"
              % (s["lanes_seen"], s["lanes_assessed"],
                 s["lanes_without_a_suite"]))
        print("cwd-dependent lanes: %d %s"
              % (len(s["cwd_dependent_lanes"]), s["cwd_dependent_lanes"] or ""))
        print("module names: %d distinct | %d collide %s"
              % (s["distinct_top_level_modules"], s["module_collisions"],
                 s["colliding_modules"] or ""))
        print("lanes shadowed in one process: %d %s"
              % (len(s["shadowed_lanes"]), s["shadowed_lanes"] or ""))
        print("lanes writing outside themselves: %d %s"
              % (len(s["leaking_lanes"]), s["leaking_lanes"] or ""))
        print("cwd_safe=%s single_process_safe=%s"
              % (s["cwd_safe"], s["single_process_safe"]))
        for path in (json_path, csv_path, md_path):
            print("wrote %s" % path)
    return 0 if (s["cwd_safe"] and s["single_process_safe"]) else 1


if __name__ == "__main__":
    sys.exit(main())
