#!/usr/bin/env python3
"""Cross-lane reproducibility audit.

Many lanes in this tree advertise some version of "deterministic - a second
operator gets identical bytes". This runs that claim.

Why running a generator twice is not a test of it
-------------------------------------------------
Python randomises string hashing per process, so a program that iterates a
`set` and writes the result emits one order in my process and a different order
in yours - while re-running inside a single process is byte-identical every
time. So each documented command is run TWICE, in SEPARATE PROCESSES, with
different `PYTHONHASHSEED`, from two throwaway copies at two different absolute
paths. The whole resulting tree is then byte-compared. That covers three real
classes at once: hash-order leakage, embedded timestamps, embedded paths.

Safety
------
Nothing ever runs against the tree itself. Each command runs inside a private
copy in a temporary directory. This is a direct consequence of the finding that
a number of lanes contain destructive-capable calls (`shutil.rmtree`,
`subprocess`): pointing an audit harness at the live tree is the obvious
implementation and the wrong one. A documented command whose output target is
an absolute path outside the copy is SKIPPED and reported - both runs would
write to the same destination and compare equal for the wrong reason.

Where the commands come from
----------------------------
From each lane's own README, out of fenced code blocks. The audit does not
invent invocations. A documented command that does not run is itself a finding.

Verdicts
--------
REPRODUCIBLE  every artifact byte-identical across seeds and paths
VARIES        at least one artifact differed; the differing files are named and
              a probable cause is classified
FAILED        the documented command exited non-zero
TIMEOUT       the documented command did not finish
SKIPPED       not safe or not meaningful to run (absolute target, server, tests)
UNKNOWN       no runnable documented command was found - NOT a pass

Python 3 standard library only. No network. Deterministic ordering of output.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

REPRODUCIBLE = "REPRODUCIBLE"
VARIES = "VARIES"
FAILED = "FAILED"
TIMEOUT = "TIMEOUT"
SKIPPED = "SKIPPED"
UNKNOWN = "UNKNOWN"

# Worst-first: a lane's verdict is the worst verdict among its commands.
VERDICT_RANK = {VARIES: 0, FAILED: 1, TIMEOUT: 2, UNKNOWN: 3, SKIPPED: 4,
                REPRODUCIBLE: 5}

DEFAULT_TIMEOUT = 90
SEED_A, SEED_B = "0", "1"

# Commands we refuse to run, with the reason recorded rather than hidden.
REFUSE_PATTERNS = (
    (re.compile(r"-m\s+unittest|\bpytest\b"), "test suite, not an artifact command"),
    (re.compile(r"\bserver\.py\b|--serve\b|--port\b"), "starts a server"),
    (re.compile(r"\bpip\b|\bvenv\b|\bcurl\b|\bwget\b|\bgit\b"), "environment or network command"),
    (re.compile(r"[<>|;]|&&"), "uses shell redirection or chaining, which this "
                               "audit does not run through a shell"),
)

CLOCK_HINT = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}|\d{2}:\d{2}:\d{2}|"
    r"\b\d{10}(\.\d+)?\b")

# A measured duration. The trailing \b in the first version of this pattern
# could never match scientific notation - in `5.290003173286095e-07` the digits
# run straight into `e`, so `\d+\.\d{3,}\b` fails everywhere and a real
# duration difference was reported as `unclassified`.
DURATION_HINT = re.compile(
    r"\d+\.\d{3,}(e[+-]?\d+)?|"
    r"\b\d+(\.\d+)?\s*(ms|msec|sec|secs|seconds)\b|"
    r"[\"\']?[a-z_]*(seconds|duration|elapsed|_ms|_s)[\"\']?\s*[:=]")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root):
    """Relative path -> sha256 for every file under root."""
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith(".pyc"):
                continue
            path = os.path.join(base, name)
            try:
                out[os.path.relpath(path, root)] = sha256_file(path)
            except OSError:
                continue
    return out


# --------------------------------------------------------------------------
# Command discovery - from the lane's own README, never invented
# --------------------------------------------------------------------------

FENCE = re.compile(r"```[a-zA-Z0-9]*\n(.*?)```", re.S)
COMMAND = re.compile(r"^\s*(?:\$\s+)?(python3?\s+\S[^\n]*)$", re.M)


def documented_commands(readme_text):
    """Extract `python ...` commands from fenced blocks, in order, deduped.

    Trailing `# explanatory comments` are stripped; a line continuation is
    joined so multi-line invocations survive.
    """
    found = []
    for block in FENCE.findall(readme_text or ""):
        joined = re.sub(r"\\\n\s*", " ", block)
        for match in COMMAND.finditer(joined):
            command = match.group(1)
            command = re.sub(r"\s+#.*$", "", command).strip()
            # Joining a line continuation leaves a double space; normalise so
            # the same command written across two lines dedupes against the
            # one-line form.
            command = re.sub(r"[ \t]+", " ", command)
            if command and command not in found:
                found.append(command)
    return found


def classify_command(command, lane_root):
    """Return (runnable, reason). A refusal is reported, never silently dropped."""
    for pattern, reason in REFUSE_PATTERNS:
        if pattern.search(command):
            return False, reason
    try:
        parts = shlex.split(command)
    except ValueError:
        return False, "command could not be parsed"
    if len(parts) < 2:
        return False, "no script named"
    script = parts[1]
    if script == "-m":
        return False, "module invocation, target not resolvable from the README"
    if not os.path.exists(os.path.join(lane_root, script)):
        return False, "script '%s' is not in this lane" % script
    return True, ""


def references_outside_lane(command):
    """True when a command reaches above its own directory. Such a command is
    still run, but the result is labelled: this audit copies each lane in
    isolation, so a sibling lane it expects will not be there."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    return any(part == ".." or part.startswith("../") or "/../" in part
               or part.endswith("/..") for part in parts[2:])


def redirect_absolute_paths(parts, copy_root):
    """Rewrite absolute path arguments into a private directory inside the copy.

    A README that writes to `/tmp/report.json` is perfectly reasonable for an
    operator and useless to this audit: both runs would write to the SAME
    destination and compare equal for the wrong reason. Redirecting makes the
    command comparable instead of unrunnable, and every substitution is
    recorded in the result."""
    sandbox = os.path.join(copy_root, "_audit_redirect")
    rewritten = list(parts)
    notes = []
    for index in range(2, len(rewritten)):
        token = rewritten[index]
        flag, sep, value = token.partition("=")
        target = value if (sep and value.startswith("/")) else (
            token if token.startswith("/") else None)
        if target is None:
            continue
        replacement = os.path.join(sandbox, os.path.basename(target.rstrip("/")) or "out")
        rewritten[index] = (flag + sep + replacement) if sep else replacement
        notes.append({"original": target, "redirected_to": "_audit_redirect/%s"
                      % os.path.basename(replacement)})
    if notes:
        os.makedirs(sandbox, exist_ok=True)
    return rewritten, notes


# --------------------------------------------------------------------------
# Difference classification
# --------------------------------------------------------------------------

def path_markers(path):
    """Every form of a run directory that can end up inside an artifact.

    The first version of this compared only against the lane copy root
    (`<workroot>/lane`), while real output embeds the workroot itself or just
    its basename - so `absolute_path_like` was missed and the file fell through
    to a weaker class.
    """
    markers = []
    while path and path not in ("/", ""):
        markers.append(path)
        markers.append(os.path.basename(path))
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return [m for m in markers if m and len(m) > 3]


def classify_difference(text_a, text_b, path_a, path_b):
    """Causes for two differing artifacts, as a sorted list.

    A list rather than one label: a file can be both path-derived and
    clock-derived, and reporting only the first found loses the other.

    Ordering is checked first - an identical multiset of lines in a different
    order is the hash-seed signature, and it is the class a same-process
    double-run can never see.
    """
    if text_a is None or text_b is None:
        return ["binary_or_unreadable"]
    lines_a, lines_b = text_a.splitlines(), text_b.splitlines()
    if lines_a != lines_b and sorted(lines_a) == sorted(lines_b):
        return ["ordering_like"]

    causes = set()
    differing = [(x, y) for x, y in zip(lines_a, lines_b) if x != y]
    sample = " ".join(x + " " + y for x, y in differing[:40])
    haystack = sample or (text_a + " " + text_b)

    for marker in path_markers(path_a) + path_markers(path_b):
        if marker in haystack:
            causes.add("absolute_path_like")
            break
    if CLOCK_HINT.search(haystack):
        causes.add("timestamp_like")
    if DURATION_HINT.search(haystack):
        causes.add("duration_like")
    if len(lines_a) != len(lines_b):
        causes.add("length_differs")
    return sorted(causes) or ["unclassified"]


def sample_differences(text_a, text_b, limit=3):
    """The actual differing line pairs, truncated.

    `unclassified` must never be the end of the story: whatever the classifier
    concludes, the reader gets the bytes that differed.
    """
    if text_a is None or text_b is None:
        return []
    pairs = [(x, y) for x, y in zip(text_a.splitlines(), text_b.splitlines())
             if x != y]
    return [{"first_run": x.strip()[:200], "second_run": y.strip()[:200]}
            for x, y in pairs[:limit]]


def probable_owner(command, detail, redirects):
    """Who owns a FAILED result. Publishing 17 failures as 17 lane defects
    would be false: several are limits of this harness, not of the lane."""
    text = str(detail)
    if "_audit_redirect" in text:
        return ("harness", "an absolute path in the documented command was "
                           "redirected into the copy and the command expected "
                           "the original shape; re-run it by hand to judge")
    if references_outside_lane(command):
        return ("harness", "the command reads above its own lane and this audit "
                           "copies each lane in isolation")
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return ("environment", "a dependency is not installed in this container")
    if redirects:
        return ("harness", "absolute paths were redirected; the failure may be "
                           "a consequence of that")
    return ("lane", "the command as documented did not run here")


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


# --------------------------------------------------------------------------
# Running one command twice
# --------------------------------------------------------------------------

def run_command_twice(lane_path, command, timeout=DEFAULT_TIMEOUT):
    parts_command = command
    parts = shlex.split(command)
    parts[0] = sys.executable
    results = []
    # Deliberately different path lengths: an absolute path baked into output
    # shows up as a difference rather than cancelling out.
    prefixes = ("ra_a_", "repro_audit_second_operator_working_copy_b_")
    dirs = []
    try:
        for prefix, seed in zip(prefixes, (SEED_A, SEED_B)):
            workroot = tempfile.mkdtemp(prefix=prefix)
            dirs.append(workroot)
            copy_root = os.path.join(workroot, "lane")
            shutil.copytree(lane_path, copy_root,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            invocation, redirects = redirect_absolute_paths(parts, copy_root)
            before = snapshot(copy_root)
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
            try:
                proc = subprocess.run(invocation, cwd=copy_root, env=env, text=True,
                                      capture_output=True, timeout=timeout)
                status, code, err = "ran", proc.returncode, (proc.stderr or "")
            except subprocess.TimeoutExpired:
                status, code, err = "timeout", None, ""
            except OSError as exc:
                status, code, err = "oserror", None, str(exc)
            results.append({"root": copy_root, "before": before,
                            "after": snapshot(copy_root), "status": status,
                            "returncode": code, "stderr": err,
                            "redirects": redirects})

        left, right = results
        if left["status"] == "timeout" or right["status"] == "timeout":
            return {"verdict": TIMEOUT, "detail": "did not finish within %ds" % timeout}
        # A non-zero exit is NOT automatically a failure. A checker that exits 1
        # because it found problems is behaving correctly, and its artifacts are
        # still worth byte-comparing. What is never acceptable is the two runs
        # disagreeing about the exit code.
        if left["returncode"] != right["returncode"]:
            return {"verdict": VARIES,
                    "detail": "exit code differed between runs: %s then %s"
                              % (left["returncode"], right["returncode"]),
                    "causes": {"<exit code>": ["nondeterministic_exit"]},
                    "differing_files": []}

        touched = sorted(set(k for k in left["after"]
                             if left["before"].get(k) != left["after"][k]))
        matches_committed = not touched
        keys = sorted(set(left["after"]) | set(right["after"]))
        only_a = sorted(k for k in keys if k not in right["after"])
        only_b = sorted(k for k in keys if k not in left["after"])
        differing = sorted(k for k in keys
                           if k in left["after"] and k in right["after"]
                           and left["after"][k] != right["after"][k])

        if not (only_a or only_b or differing):
            stderr_tail = (left["stderr"] or "").strip().splitlines()
            genuinely_failed = left["returncode"] and (
                bool(stderr_tail) or left["returncode"] >= 2)
            if genuinely_failed and not touched:
                detail = ("the documented command exited %s and wrote nothing "
                          "new: %s" % (left["returncode"],
                                       stderr_tail[-1] if stderr_tail
                                       else "no stderr"))
                owner, why = probable_owner(parts_command, detail, left["redirects"])
                return {"verdict": FAILED, "returncode": left["returncode"],
                        "redirects": left["redirects"], "probable_owner": owner,
                        "owner_reason": why, "detail": detail}
            return {"verdict": REPRODUCIBLE,
                    "exit_is_a_finding_signal": bool(left["returncode"]),
                    "artifacts_written": len(touched),
                    "matches_committed_artifacts": matches_committed,
                    "exit_code": left["returncode"],
                    "redirects": left["redirects"],
                    "files_compared": len(keys)}

        causes = {}
        samples = {}
        for name in differing[:10]:
            text_left = read_text(os.path.join(left["root"], name))
            text_right = read_text(os.path.join(right["root"], name))
            causes[name] = classify_difference(text_left, text_right,
                                               left["root"], right["root"])
            samples[name] = sample_differences(text_left, text_right)
        return {"verdict": VARIES, "differing_files": differing,
                "only_in_first_run": only_a, "only_in_second_run": only_b,
                "causes": causes, "sample_differences": samples,
                "files_compared": len(keys),
                "exit_code": left["returncode"],
                "redirects": left["redirects"],
                "matches_committed_artifacts": matches_committed}
    finally:
        for workroot in dirs:
            shutil.rmtree(workroot, ignore_errors=True)


# --------------------------------------------------------------------------
# Auditing a lane and a tree
# --------------------------------------------------------------------------

def audit_lane(lane_path, timeout=DEFAULT_TIMEOUT):
    lane = os.path.basename(lane_path.rstrip(os.sep))
    readme = os.path.join(lane_path, "README.md")
    record = {"lane": lane, "commands": [], "verdict": UNKNOWN, "note": ""}
    if not os.path.exists(readme):
        record["note"] = ("no README.md, so no documented command to run; "
                          "not assessed")
        return record
    commands = documented_commands(read_text(readme) or "")
    if not commands:
        record["note"] = ("README documents no runnable command; not assessed. "
                          "This is not a pass.")
        return record
    for command in commands:
        runnable, reason = classify_command(command, lane_path)
        if not runnable:
            record["commands"].append({"command": command, "verdict": SKIPPED,
                                       "detail": reason})
            continue
        outcome = run_command_twice(lane_path, command, timeout)
        outcome["command"] = command
        if references_outside_lane(command):
            outcome["references_outside_lane"] = True
            outcome["isolation_note"] = (
                "This command reads above its own directory. Each lane is "
                "copied in isolation, so a sibling lane it expects is not "
                "present; read this result as an isolated run.")
        record["commands"].append(outcome)
    verdicts = [c["verdict"] for c in record["commands"]]
    real = [v for v in verdicts if v != SKIPPED]
    if not real:
        record["verdict"] = UNKNOWN
        record["note"] = ("every documented command was skipped; not assessed. "
                          "This is not a pass.")
    else:
        record["verdict"] = sorted(real, key=lambda v: VERDICT_RANK[v])[0]
    return record


def audit_tree(tree, pattern="uiowa_rfq_18649_*", timeout=DEFAULT_TIMEOUT,
               limit=None, skip=()):
    lanes = sorted(name for name in os.listdir(tree)
                   if fnmatch.fnmatch(name, pattern)
                   and os.path.isdir(os.path.join(tree, name))
                   and name not in skip)
    if limit:
        lanes = lanes[:limit]
    records = [audit_lane(os.path.join(tree, lane), timeout) for lane in lanes]
    counts = {}
    for record in records:
        counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
    return {
        "artifact": "cross-lane reproducibility audit",
        "method": (
            "Each command documented in a lane's own README is run twice, in "
            "separate processes, with PYTHONHASHSEED=%s and %s, on two private "
            "copies at two different absolute paths. The full resulting trees "
            "are byte-compared. Nothing runs against the tree itself."
            % (SEED_A, SEED_B)),
        "unknown_notice": (
            "UNKNOWN means no documented command could be run. It is not a "
            "pass, and it is not a finding against the lane."),
        "pattern": pattern,
        "lanes": records,
        "counts": counts,
        "lanes_audited": len(records),
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def render_text(result):
    owners = {}
    for record in result["lanes"]:
        for command in record["commands"]:
            if command["verdict"] == FAILED:
                key = command.get("probable_owner", "?")
                owners[key] = owners.get(key, 0) + 1
    lines = ["lanes=%d  %s" % (result["lanes_audited"],
                               "  ".join("%s=%d" % (k, result["counts"][k])
                                         for k in sorted(result["counts"])))]
    if owners:
        lines.append("failed-command owners: %s"
                     % "  ".join("%s=%d" % (k, owners[k]) for k in sorted(owners)))
    for record in result["lanes"]:
        extra = ""
        if record["verdict"] == REPRODUCIBLE:
            best = [c for c in record["commands"] if c["verdict"] == REPRODUCIBLE][0]
            extra = "%d files compared" % best.get("files_compared", 0)
            if best.get("matches_committed_artifacts"):
                extra += ", committed artifacts still match"
        elif record["verdict"] == VARIES:
            bad = [c for c in record["commands"] if c["verdict"] == VARIES][0]
            causes = sorted({c for v in bad.get("causes", {}).values() for c in v})
            extra = "%d file(s) differ (%s)" % (len(bad.get("differing_files", [])),
                                                ", ".join(causes) or "unclassified")
        elif record["verdict"] in (FAILED, TIMEOUT):
            bad = [c for c in record["commands"] if c["verdict"] == record["verdict"]][0]
            extra = "[%s] %s" % (bad.get("probable_owner", "?"),
                                 str(bad.get("detail", ""))[:96])
        else:
            extra = record["note"]
        lines.append("  %-13s %-42s %s" % (record["verdict"], record["lane"], extra))
    return "\n".join(lines) + "\n"


def render_markdown(result):
    lines = ["# Cross-lane reproducibility audit", "",
             "> %s" % result["method"], "",
             "> **Reading UNKNOWN.** %s" % result["unknown_notice"], "",
             "| verdict | count |", "|---|---|"]
    for key in sorted(result["counts"]):
        lines.append("| `%s` | %d |" % (key, result["counts"][key]))
    lines += ["", "| lane | verdict | detail |", "|---|---|---|"]
    for record in result["lanes"]:
        detail = record["note"]
        for command in record["commands"]:
            if command["verdict"] == record["verdict"]:
                detail = command.get("detail", "")
                if command["verdict"] == VARIES:
                    detail = "differs: %s (%s)" % (
                        ", ".join("`%s`" % f for f in command["differing_files"][:4]),
                        ", ".join(sorted({c for v in command.get("causes", {}).values()
                                          for c in v})))
                elif command["verdict"] == REPRODUCIBLE:
                    detail = "%d files byte-identical" % command.get("files_compared", 0)
                    if command.get("matches_committed_artifacts"):
                        detail += "; committed artifacts still match the code"
                break
        lines.append("| `%s` | **%s** | %s |" % (record["lane"], record["verdict"],
                                                 str(detail).replace("|", "\\|")[:220]))
    lines += ["", "## Commands run", ""]
    for record in result["lanes"]:
        if not record["commands"]:
            continue
        lines.append("**`%s`**" % record["lane"])
        lines.append("")
        for command in record["commands"]:
            lines.append("- `%s` → %s%s"
                         % (command["command"], command["verdict"],
                            (" — " + str(command.get("detail", "")))
                            if command.get("detail") else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tree", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    parser.add_argument("--pattern", default="uiowa_rfq_18649_*")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip", nargs="*", default=[])
    parser.add_argument("--out", default=None,
                        help="Directory for audit.json and audit.md.")
    args = parser.parse_args(argv)

    result = audit_tree(args.tree, args.pattern, args.timeout, args.limit,
                        set(args.skip))
    sys.stdout.write(render_text(result))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "audit.json"), "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        with open(os.path.join(args.out, "audit.md"), "w", encoding="utf-8") as handle:
            handle.write(render_markdown(result))
        print("wrote %s/audit.json and audit.md" % args.out)
    return 1 if result["counts"].get(VARIES) else 0


if __name__ == "__main__":
    sys.exit(main())
