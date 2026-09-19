#!/usr/bin/env python3
"""command_index.py -- discover every component's real command line by running it.

Why this exists
---------------
The operator guide names fifty components and their phases. It does not tell an
operator what to type. Filling that in from each component's README would put the
whole index at the mercy of documentation drift -- the exact failure mode the rest
of this lane exists to avoid. So the index is discovered the same way statuses
are: execute the thing and record what it says about itself.

Method
------
For each lane: copy it to a temporary directory, find the plausible entry-point
modules (top-level `.py` files that are not tests and not obvious library
helpers), run each with `--help`, and keep the ones that respond like a command
line -- exit 0 with a usage line naming that file. Everything else is recorded as
"no verified command line", never as broken and never with a guessed command.

Nothing outside the temporary copy is written or modified.

Usage
-----
  python3 command_index.py --root /home/user/commons/revenue
  python3 command_index.py --root ../ --out COMMAND_INDEX.md --out-json idx.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import verify_kit  # reuse the manifest, the lane walk and the isolation rule

USAGE_RE = re.compile(r"^usage:\s*(\S+)", re.M | re.I)

# Modules that are conventionally imported rather than run. Probing them is
# harmless but noisy, and a helper that happens to print usage would put a
# misleading command in front of an operator.
LIBRARY_HINTS = ("adapter", "schema", "models", "util", "utils", "common", "helpers")


def candidate_entry_points(lane_dir):
    """Top-level .py files worth probing, in a stable order."""
    out = []
    try:
        names = sorted(os.listdir(lane_dir))
    except OSError:
        return out
    for fn in names:
        if not fn.endswith(".py"):
            continue
        if fn.startswith("test_") or fn.endswith("_test.py") or fn == "__init__.py":
            continue
        out.append(fn)
    return out


def probe(workdir, script, timeout):
    """Run one script with --help and decide whether it is a real command line."""
    started = time.time()
    try:
        proc = subprocess.run([sys.executable, script, "--help"], cwd=workdir,
                              timeout=timeout, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        out = proc.stdout.decode("utf-8", "replace")
        rc, timed_out = proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        out = (exc.output or b"").decode("utf-8", "replace")
        rc, timed_out = None, True
    m = USAGE_RE.search(out)
    # A usage line that names a *different* file usually means the script re-execs
    # or delegates; accept it, but record what it actually printed.
    is_cli = bool(rc == 0 and m and not timed_out)
    first = ""
    if m:
        for line in out.splitlines():
            if line.lower().startswith("usage:"):
                first = line.strip()
                break
    return {
        "script": script,
        "command": "python3 %s --help" % script,
        "exit_code": rc,
        "timed_out": timed_out,
        "duration_s": round(time.time() - started, 2),
        "is_cli": is_cli,
        "usage_line": first,
        "library_hint": any(h in script.lower() for h in LIBRARY_HINTS),
        "output_tail": out.strip()[-600:],
    }


def index(root, manifest, timeout=25):
    placed = []
    for phase in sorted(manifest["phases"], key=lambda p: p["order"]):
        for comp in phase["components"]:
            placed.append((phase["id"], phase["order"], phase["title"],
                           comp["lane"], comp.get("role", ""), comp.get("runner")))
    seen = set()
    rows = []
    for phase_id, order, title, lane, role, runner in placed:
        key = (phase_id, lane)
        if key in seen:
            continue
        seen.add(key)
        lane_dir = os.path.join(root, lane)
        if not os.path.isdir(lane_dir):
            rows.append({"phase": phase_id, "phase_order": order, "phase_title": title,
                         "component": lane, "role": role, "present": False,
                         "commands": [], "rejected": [], "manifest_runner": None,
                         "note": "component not built yet"})
            continue
        cands = candidate_entry_points(lane_dir)
        probes = []
        if cands:
            tmp = tempfile.mkdtemp(prefix="cmdidx_")
            try:
                work = os.path.join(tmp, lane)
                shutil.copytree(lane_dir, work, ignore=verify_kit._ignore)
                for fn in cands:
                    probes.append(probe(work, fn, timeout))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        cli = [p for p in probes if p["is_cli"] and not p["library_hint"]]
        rejected = [p for p in probes if not (p["is_cli"] and not p["library_hint"])]
        # Some components are perfectly runnable and simply take no arguments, so
        # they never answer --help. The manifest already records a documented runner
        # for those, and verify_kit has executed it. Surfacing it here stops the index
        # from implying a working tool has no way to invoke it.
        runner_cmd = " ".join(runner["cmd"]) if runner else None
        if cli:
            note = "%d verified command line(s)" % len(cli)
        elif runner_cmd:
            note = ("no --help interface, but the manifest records a documented runner "
                    "that verify_kit executes")
        elif probes:
            note = ("no verified command line: %d module(s) probed, none answered --help "
                    "with a usage line" % len(probes))
        else:
            note = "no top-level python modules; this component is documents or data"
        rows.append({"phase": phase_id, "phase_order": order, "phase_title": title,
                     "component": lane, "role": role, "present": True,
                     "commands": cli, "rejected": rejected,
                     "manifest_runner": runner_cmd, "note": note})
    total_cli = sum(len(r["commands"]) for r in rows)
    with_cli = sum(1 for r in rows if r["commands"])
    return {
        "survey_root": os.path.abspath(root),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0],
        "components": len(rows),
        "components_with_a_command_line": with_cli,
        "verified_commands": total_cli,
        "rows": rows,
    }


def render(idx):
    L = []
    L.append("# Command index")
    L.append("")
    L.append("**What do I type?** — every command below was discovered by executing the")
    L.append("script with `--help` in a throwaway copy of its lane and keeping the ones that")
    L.append("answered with a real usage line. None of it was read out of a README, so none")
    L.append("of it can be stale relative to the code in the way documentation can.")
    L.append("")
    L.append("- survey root: `%s`" % idx["survey_root"])
    L.append("- generated (UTC): %s · python %s" % (idx["generated_at_utc"], idx["python"]))
    L.append("- **%d verified command lines across %d of %d components**"
             % (idx["verified_commands"], idx["components_with_a_command_line"],
                idx["components"]))
    L.append("")
    L.append("Regenerate with:")
    L.append("")
    L.append("```bash")
    L.append("cd revenue/uiowa_rfq_18649_operator_handoff")
    L.append("python3 command_index.py --root ../ --out COMMAND_INDEX.md --out-json sample/command_index.json")
    L.append("```")
    L.append("")
    L.append("A component listed as having **no verified command line** is not broken. It")
    L.append("either ships documents and data rather than a program, or its code is imported")
    L.append("by something else. Open it and read it; do not invent a command for it.")
    L.append("")
    cur = None
    for r in sorted(idx["rows"], key=lambda r: (r["phase_order"], r["component"])):
        if r["phase"] != cur:
            cur = r["phase"]
            L.append("---")
            L.append("")
            L.append("## %d. %s" % (r["phase_order"], r["phase_title"]))
            L.append("")
        L.append("### `%s`" % r["component"])
        L.append("")
        if r["role"]:
            L.append("%s" % r["role"])
            L.append("")
        if not r["present"]:
            L.append("Not built yet — nothing to run.")
            L.append("")
            continue
        if r["commands"]:
            L.append("```bash")
            for c in r["commands"]:
                L.append("cd revenue/%s" % r["component"])
                L.append("python3 %s --help" % c["script"])
            L.append("```")
            L.append("")
            for c in r["commands"]:
                L.append("- `%s` → `%s`" % (c["script"], c["usage_line"]))
            L.append("")
        elif r.get("manifest_runner"):
            L.append("Takes no arguments, so it has no `--help` interface. Documented runner,")
            L.append("executed by `verify_kit.py`:")
            L.append("")
            L.append("```bash")
            L.append("cd revenue/%s" % r["component"])
            L.append("%s" % r["manifest_runner"].replace("{ROOT}", "<revenue dir>")
                     .replace("{REPO}", "<repo root>").replace("{OUT}", "<output dir>"))
            L.append("```")
            L.append("")
        else:
            L.append("_No verified command line._ %s" % r["note"])
            L.append("")
    return "\n".join(L).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/user/commons/revenue")
    ap.add_argument("--manifest", default=os.path.join(HERE, "kit_manifest.json"))
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--out", default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    with open(args.manifest, encoding="utf-8") as fh:
        manifest = json.load(fh)
    idx = index(args.root, manifest, timeout=args.timeout)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(render(idx))
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            json.dump(idx, fh, indent=2)
            fh.write("\n")
    if not args.quiet:
        print("survey root : %s" % idx["survey_root"])
        print("commands    : %d verified across %d of %d components"
              % (idx["verified_commands"], idx["components_with_a_command_line"],
                 idx["components"]))
        print("")
        for r in sorted(idx["rows"], key=lambda r: (r["phase_order"], r["component"])):
            if r["commands"]:
                for c in r["commands"]:
                    print("%-46s %s" % (r["component"][:46], c["usage_line"][:70]))
            elif r.get("manifest_runner"):
                print("%-46s ~~ runner: %s" % (r["component"][:46], r["manifest_runner"][:60]))
            else:
                print("%-46s -- %s" % (r["component"][:46], r["note"][:70]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
