#!/usr/bin/env python3
"""UIOWA-137 - Evidence-backed technical capability appendix.

A capability appendix is a marketing document by default. Its natural failure
mode is a claim nobody can check: "robust traceability tooling", "enterprise
grade evidence organization". Those read well and prove nothing.

This generator makes the document physically unable to print an unbacked
claim. A claim is rendered as a capability only when ALL of the following
bind:

  1. every artifact file it cites exists on disk
  2. a run of its demonstration command was actually observed and recorded
  3. that run exited zero and produced non-empty output
  4. the file digests recorded at observation still match the files now
     (so a claim silently demotes if the artifact changes underneath it)
  5. the demonstration command invokes a file the claim itself cites
  6. the claim's own wording passes a language check

Fail any one and the claim does not appear in the appendix body. It drops to
a separate "Not demonstrated" section with the specific missing element
named. There is no code path that prints a capability with a hole in it.

The language check rejects rather than softens. A claim containing
"enterprise-grade", "seamlessly", "robust" or "guaranteed" is refused: if the
sentence cannot survive without the adjective, the adjective was doing the
work. It also refuses certification, compliance and guarantee language
outright, which is a claim class this engagement does not make.

"Two pages" is enforced arithmetic, not an aspiration. The generator holds a
word budget and reports the exact overage. It never truncates a claim to make
the document fit -- an appendix that quietly drops its last capability is
worse than one that says it is 140 words over.

Two subcommands, deliberately separated:

    record   executes each claim's demonstration command and writes down what
             actually happened, including file digests. This is the only part
             that runs anything.
    build    renders the appendix from the register plus the recorded
             observations. It executes nothing and reads no clock, so its
             output is reproducible.

Python 3 standard library only. No network.

    python3 capability_appendix.py record --observed-on 2026-09-19
    python3 capability_appendix.py build --outdir out
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_REGISTER = os.path.join(HERE, "capabilities.json")
DEFAULT_OBSERVATIONS = os.path.join(HERE, "observed_runs.json")

# --------------------------------------------------------------------------
# The language check
# --------------------------------------------------------------------------

# Words that assert quality without offering anything to check. A claim that
# needs one of these is not yet a claim.
MARKETING_TERMS = [
    "enterprise-grade", "enterprise grade", "best-in-class", "best in class",
    "industry-leading", "industry leading", "world-class", "world class",
    "state-of-the-art", "cutting-edge", "cutting edge", "next-generation",
    "turnkey", "seamless", "seamlessly", "frictionless", "effortless",
    "robust", "scalable", "unparalleled", "revolutionary", "revolutionize",
    "synergy", "synergies", "holistic", "game-changing", "powerful",
    "comprehensive", "sophisticated", "blazing",
]

# Intensifiers standing in for a number.
UNQUANTIFIED_TERMS = [
    "significantly", "dramatically", "substantially", "vastly", "massively",
    "drastically", "exponentially",
]

# Claims this engagement does not make at all.
PROHIBITED_TERMS = [
    "certified", "certification", "compliant", "compliance-ready",
    "audit-proof", "accredited", "guarantee", "guaranteed", "guarantees",
    "eliminates risk", "fully secure", "industry standard compliant",
]

LANGUAGE_CHECKS = (
    ("marketing language", MARKETING_TERMS),
    ("unquantified intensifier", UNQUANTIFIED_TERMS),
    ("prohibited certification or guarantee language", PROHIBITED_TERMS),
)


def language_violations(text):
    """Return [(category, term)] for every banned term in the text.

    Word-boundary matched so 'scalable' fires but 'descale' does not, and
    'compliant' fires but 'complaint' does not.
    """
    found = []
    lowered = text.lower()
    for category, terms in LANGUAGE_CHECKS:
        for term in terms:
            pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append((category, term))
    return found


# --------------------------------------------------------------------------
# Recording: the only part that executes anything
# --------------------------------------------------------------------------

def digest_file(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def command_targets(command):
    """Files a demonstration command invokes.

    Handles a direct script (`python3 validate_trace.py`) and a module
    (`python3 -m unittest test_closeout` -> test_closeout.py). Used to check
    that the instruction points at something the claim actually owns.
    """
    tokens = command.split()
    targets = set()
    for i, token in enumerate(tokens):
        if token.endswith(".py"):
            targets.add(os.path.basename(token))
        elif token == "-m" and i + 1 < len(tokens):
            module = tokens[i + 1]
            if module not in ("unittest", "pytest", "pip", "json.tool"):
                targets.add(module.split(".")[-1] + ".py")
    # `-m unittest <module>`: the module is the trailing argument.
    if "-m" in tokens and "unittest" in tokens:
        for token in tokens[tokens.index("unittest") + 1:]:
            if not token.startswith("-"):
                targets.add(token.split(".")[-1] + ".py")
    return sorted(targets)


def record_runs(register, base, observed_on, timeout=300):
    """Execute each claim's demonstration command and write down what
    happened. Honest by construction: a failing command is recorded as
    failing, not skipped."""
    observations = []
    for claim in register["claims"]:
        demo = claim.get("demonstration") or {}
        command = demo.get("command") or ""
        cwd = os.path.join(base, demo.get("cwd") or "")
        entry = {
            "claim_id": claim["claim_id"],
            "observed_on": observed_on,
            "cwd": demo.get("cwd"),
            "command": command,
        }

        if not command or command.startswith("("):
            entry["status"] = "not_run"
            entry["reason"] = "no executable demonstration command declared"
            observations.append(entry)
            continue
        if not os.path.isdir(cwd):
            entry["status"] = "not_run"
            entry["reason"] = "declared working directory does not exist: %s" % cwd
            observations.append(entry)
            continue

        try:
            proc = subprocess.run(command.split(), cwd=cwd, timeout=timeout,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = proc.stdout.decode("utf-8", "replace").strip()
            entry["status"] = "ran"
            entry["exit_code"] = proc.returncode
            entry["output_verbatim"] = output
        except (OSError, subprocess.TimeoutExpired) as exc:
            entry["status"] = "not_run"
            entry["reason"] = "command could not be executed: %s" % exc
            observations.append(entry)
            continue

        digests = {}
        for rel in claim.get("artifact_paths") or []:
            full = os.path.join(base, rel)
            digests[rel] = digest_file(full) if os.path.isfile(full) else None
        entry["file_digests"] = digests
        observations.append(entry)

    return {
        "note": ("Produced by `capability_appendix.py record`. Each entry is "
                 "what this seat actually observed when it executed the "
                 "command, including failures. Digests pin the exact bytes "
                 "that were executed."),
        "observed_on": observed_on,
        "observations": observations,
    }


# --------------------------------------------------------------------------
# Binding: build executes nothing
# --------------------------------------------------------------------------

def bind_claim(claim, observation, base):
    """Decide whether a claim may be printed as a capability.

    Returns (demonstrated: bool, blockers: [str], detail: dict). Every blocker
    names the specific missing element, because "not demonstrated" without a
    reason is just a different kind of unbacked statement.
    """
    blockers = []
    detail = {}

    paths = claim.get("artifact_paths") or []
    if not paths:
        blockers.append("the claim cites no artifact files")
    missing = [p for p in paths if not os.path.isfile(os.path.join(base, p))]
    if missing:
        blockers.append("artifact file(s) not found: %s" % ", ".join(missing))
    detail["artifact_count"] = len(paths)
    detail["missing_artifacts"] = missing

    violations = language_violations(
        "%s %s" % (claim.get("statement", ""), claim.get("business_use", "")))
    if violations:
        blockers.append("wording rejected (%s)" % "; ".join(
            "%s: '%s'" % (cat, term) for cat, term in violations))
    detail["language_violations"] = ["%s:%s" % (c, t) for c, t in violations]

    demo = claim.get("demonstration") or {}
    command = demo.get("command") or ""
    targets = command_targets(command)
    owned = {os.path.basename(p) for p in paths}
    orphan = [t for t in targets if t not in owned]
    if command and not command.startswith("(") and orphan:
        blockers.append(
            "demonstration command invokes %s, which the claim does not cite"
            % ", ".join(orphan))
    detail["command_targets"] = targets

    if observation is None:
        blockers.append("no observed run recorded for this claim")
        return False, blockers, detail

    detail["observed_on"] = observation.get("observed_on")
    if observation.get("status") != "ran":
        blockers.append("demonstration was not run: %s"
                        % observation.get("reason", "reason not recorded"))
        return False, blockers, detail

    detail["exit_code"] = observation.get("exit_code")
    detail["output_verbatim"] = observation.get("output_verbatim", "")
    if observation.get("exit_code") != 0:
        blockers.append("demonstration exited %s" % observation.get("exit_code"))
    if not (observation.get("output_verbatim") or "").strip():
        blockers.append("demonstration produced no output to show")

    drifted = []
    absent = []
    for rel, recorded in (observation.get("file_digests") or {}).items():
        full = os.path.join(base, rel)
        if not os.path.isfile(full):
            absent.append(rel)
            continue
        if recorded is None:
            absent.append(rel)
            continue
        if digest_file(full) != recorded:
            drifted.append(rel)
    if drifted:
        blockers.append(
            "artifact changed since it was demonstrated: %s. The recorded run "
            "no longer describes these bytes." % ", ".join(sorted(drifted)))
    if absent:
        blockers.append("digest recorded for missing file(s): %s"
                        % ", ".join(sorted(absent)))
    detail["drifted"] = sorted(drifted)

    return (not blockers), blockers, detail


def evaluate(register, observations, base):
    obs_by_claim = {o["claim_id"]: o for o in observations.get("observations", [])}
    demonstrated = []
    not_demonstrated = []
    for claim in register["claims"]:
        ok, blockers, detail = bind_claim(claim, obs_by_claim.get(claim["claim_id"]),
                                          base)
        record = dict(claim)
        record["bind_detail"] = detail
        record["blockers"] = blockers
        record["demonstrated"] = ok
        (demonstrated if ok else not_demonstrated).append(record)
    return demonstrated, not_demonstrated


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def count_words(text):
    return len([t for t in text.split() if t.strip()])


def run_summary(output):
    """One line a reader can check against the evidence index.

    Prefers the informative line over the terse one: a unittest run whose last
    line is "OK" is reported with its test count, because "OK" alone tells a
    reviewer nothing about how much was actually exercised.
    """
    lines = [ln.strip() for ln in (output or "").splitlines() if ln.strip()]
    if not lines:
        return ""
    last = lines[-1]
    for line in reversed(lines):
        match = re.match(r"^(Ran \d+ tests? in [\d.]+s)$", line)
        if match:
            return "%s - %s" % (match.group(1), last)
    return last


def render_appendix(register, demonstrated, not_demonstrated):
    """The two-page body. Verbatim outputs and digests live in the separate
    evidence index so the appendix itself stays readable."""
    out = []
    out.append("# Technical capability appendix")
    out.append("")
    out.append("Every capability below is bound to working files in this "
               "repository and to a run of those files that was executed and "
               "recorded. A claim that could not be bound is not described "
               "here as a capability; it is listed at the end with the reason. "
               "Exact file digests and verbatim run output are in the "
               "accompanying evidence index.")
    out.append("")

    areas = []
    for claim in demonstrated:
        if claim["capability_area"] not in areas:
            areas.append(claim["capability_area"])

    for area in areas:
        out.append("## %s" % area.capitalize())
        out.append("")
        for claim in [c for c in demonstrated if c["capability_area"] == area]:
            detail = claim["bind_detail"]
            summary = run_summary(detail.get("output_verbatim"))
            out.append("**%s.** %s" % (claim["claim_id"], claim["statement"]))
            out.append("")
            out.append("*Why it matters:* %s" % claim["business_use"])
            out.append("")
            out.append("*Demonstrated by:* `%s` (%d file%s). Run `%s` from that "
                       "directory; observed %s, result `%s`."
                       % (claim["artifact_dir"], detail["artifact_count"],
                          "" if detail["artifact_count"] == 1 else "s",
                          claim["demonstration"]["command"],
                          detail.get("observed_on", "date not recorded"),
                          summary))
            out.append("")

    if not_demonstrated:
        out.append("## Not demonstrated")
        out.append("")
        out.append("These were proposed as capabilities and are not claimed as "
                   "such, because the binding below is missing. They are listed "
                   "rather than removed so the omission is visible.")
        out.append("")
        for claim in not_demonstrated:
            out.append("- **%s** (%s) - %s" % (
                claim["claim_id"], claim["capability_area"],
                "; ".join(claim["blockers"])))
        out.append("")

    out.append("## How to check this appendix")
    out.append("")
    out.append("Run `python3 capability_appendix.py record --observed-on "
               "<date>` to re-execute every demonstration, then `python3 "
               "capability_appendix.py build`. If an artifact has changed "
               "since it was demonstrated, its claim moves itself into the "
               "Not demonstrated list.")
    return "\n".join(out)


def render_evidence_index(register, demonstrated, not_demonstrated):
    out = []
    out.append("# Capability appendix - evidence index")
    out.append("")
    out.append("Verbatim output and file digests behind each capability in the "
               "appendix. Digests are of the exact bytes that were executed.")
    out.append("")
    for claim in demonstrated + not_demonstrated:
        detail = claim["bind_detail"]
        out.append("## %s - %s" % (claim["claim_id"], claim["capability_area"]))
        out.append("")
        out.append("**Status:** %s" % ("DEMONSTRATED" if claim["demonstrated"]
                                       else "NOT DEMONSTRATED"))
        if claim["blockers"]:
            out.append("")
            for blocker in claim["blockers"]:
                out.append("- Blocker: %s" % blocker)
        out.append("")
        out.append("**Contributing seat:** %s" % claim.get("contributing_seat",
                                                           "not recorded"))
        out.append("")
        out.append("**Reported commit:** `%s` - %s" % (
            claim.get("reported_commit", "not recorded"),
            claim.get("reported_commit_status", "status not recorded")))
        out.append("")
        out.append("**Working directory:** `%s`" % claim["demonstration"]["cwd"])
        out.append("")
        out.append("**Command:** `%s`" % claim["demonstration"]["command"])
        if detail.get("output_verbatim"):
            out.append("")
            out.append("**Observed output (verbatim, exit %s, %s):**"
                       % (detail.get("exit_code"),
                          detail.get("observed_on", "date not recorded")))
            out.append("")
            out.append("```")
            out.append(detail["output_verbatim"])
            out.append("```")
        out.append("")
        out.append("**Artifact digests:**")
        out.append("")
        out.append("| File | Digest at demonstration |")
        out.append("|---|---|")
        for path in claim.get("artifact_paths") or []:
            recorded = (claim.get("_digests") or {}).get(path)
            out.append("| `%s` | %s |" % (path, recorded or "not recorded"))
        out.append("")
    return "\n".join(out)


CSV_COLUMNS = ["claim_id", "capability_area", "demonstrated", "artifact_dir",
               "artifact_count", "command", "observed_on", "exit_code",
               "blockers"]


def write_csv(demonstrated, not_demonstrated, path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for claim in demonstrated + not_demonstrated:
            detail = claim["bind_detail"]
            writer.writerow([
                claim["claim_id"],
                claim["capability_area"],
                "yes" if claim["demonstrated"] else "no",
                claim["artifact_dir"],
                detail.get("artifact_count", "UNKNOWN"),
                claim["demonstration"]["command"],
                detail.get("observed_on") or "UNKNOWN",
                detail.get("exit_code") if detail.get("exit_code") is not None
                else "UNKNOWN",
                "; ".join(claim["blockers"]) if claim["blockers"] else "none",
            ])
    return path


def budget_check(register, text):
    budget = register.get("page_budget") or {}
    pages = budget.get("pages", 2)
    per_page = budget.get("words_per_page", 500)
    allowed = pages * per_page
    words = count_words(text)
    return {
        "pages_allowed": pages,
        "words_per_page": per_page,
        "words_allowed": allowed,
        "words_used": words,
        "over_by": max(0, words - allowed),
        "within_budget": words <= allowed,
        "estimated_pages": round(words / float(per_page), 2),
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (IOError, OSError) as exc:
        raise SystemExit("error: cannot read %s (%s): %s" % (what, path, exc))
    except ValueError as exc:
        raise SystemExit("error: %s is not valid JSON (%s): %s" % (what, path, exc))


def cmd_record(args):
    register = load_json(args.register, "claim register")
    result = record_runs(register, args.base, args.observed_on)
    with open(args.observations, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    ran = sum(1 for o in result["observations"] if o.get("status") == "ran")
    clean = sum(1 for o in result["observations"] if o.get("exit_code") == 0)
    print("recorded %d claim(s): %d executed, %d exited zero"
          % (len(result["observations"]), ran, clean))
    for obs in result["observations"]:
        if obs.get("status") != "ran":
            print("  %s not run: %s" % (obs["claim_id"], obs.get("reason")))
        else:
            print("  %s exit=%s" % (obs["claim_id"], obs["exit_code"]))
    print("wrote %s" % args.observations)
    return 0


def cmd_build(args):
    register = load_json(args.register, "claim register")
    if os.path.isfile(args.observations):
        observations = load_json(args.observations, "observations")
    else:
        observations = {"observations": []}
        print("note: no observations file at %s; every claim will be "
              "unbacked" % args.observations, file=sys.stderr)

    demonstrated, not_demonstrated = evaluate(register, observations, args.base)

    obs_by_claim = {o["claim_id"]: o for o in observations.get("observations", [])}
    for claim in demonstrated + not_demonstrated:
        obs = obs_by_claim.get(claim["claim_id"]) or {}
        claim["_digests"] = obs.get("file_digests") or {}

    appendix = render_appendix(register, demonstrated, not_demonstrated)
    budget = budget_check(register, appendix)

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    md_path = os.path.join(args.outdir, "capability_appendix.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(appendix)
        handle.write("\n")
    idx_path = os.path.join(args.outdir, "capability_evidence_index.md")
    with open(idx_path, "w", encoding="utf-8") as handle:
        handle.write(render_evidence_index(register, demonstrated, not_demonstrated))
        handle.write("\n")
    csv_path = write_csv(demonstrated, not_demonstrated,
                         os.path.join(args.outdir, "capability_claims.csv"))
    json_path = os.path.join(args.outdir, "capability_appendix.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump({
            "prepared_by_seat": register.get("prepared_by_seat"),
            "budget": budget,
            "demonstrated": demonstrated,
            "not_demonstrated": not_demonstrated,
        }, handle, indent=2, default=str)
        handle.write("\n")

    if not args.quiet:
        print("claims: %d demonstrated, %d not demonstrated"
              % (len(demonstrated), len(not_demonstrated)))
        for claim in not_demonstrated:
            print("  %s blocked: %s" % (claim["claim_id"],
                                        "; ".join(claim["blockers"])))
        print("budget: %d words used of %d allowed (%s pages at %d words/page)%s"
              % (budget["words_used"], budget["words_allowed"],
                 budget["estimated_pages"], budget["words_per_page"],
                 "" if budget["within_budget"]
                 else " -- OVER BY %d WORDS" % budget["over_by"]))
        for path in (md_path, idx_path, csv_path, json_path):
            print("wrote %s" % path)
    # Over budget is a real failure of the deliverable, so say so in the exit
    # code rather than shipping a document that does not fit its own spec.
    return 0 if budget["within_budget"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build an evidence-backed capability appendix in which no "
                    "claim can be printed without a recorded demonstration.")
    parser.add_argument("--register", default=DEFAULT_REGISTER)
    parser.add_argument("--observations", default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help="repository root that artifact paths resolve against")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record", help="execute and record each demonstration")
    rec.add_argument("--observed-on", required=True,
                     help="the date to record (YYYY-MM-DD). Required so the "
                          "output does not depend on the wall clock.")
    rec.set_defaults(func=cmd_record)

    bld = sub.add_parser("build", help="render the appendix; executes nothing")
    bld.add_argument("--outdir", default=os.path.join(HERE, "out"))
    bld.add_argument("--quiet", action="store_true")
    bld.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
