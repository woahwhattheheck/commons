#!/usr/bin/env python3
"""Stop a private repo's CI workflows from auto-running on billed GitHub runners.

Adds this condition to every job of every check workflow (a workflow whose only
triggers are push, pull_request, workflow_dispatch or merge_group):

    if: ${{ (vars.HOSTED_CI == 'on' || github.event_name == 'workflow_dispatch') && (<existing if>) }}

Skipped jobs use no Actions minutes. The "Run workflow" button still runs the
job, and setting the repo variable HOSTED_CI=on turns automatic runs back on.
Workflows with other triggers (schedule, issues, issue_comment, ...) are left
alone. Checks run in the session instead: tools/sandbox_ci.py.

    python3 hosted_ci_gate.py [REPO_ROOT]           # apply
    python3 hosted_ci_gate.py --check [REPO_ROOT]   # exit 1 if any check job is ungated

Idempotent. Each edited file is re-parsed and must equal the original except
for the job `if:` values.
"""

import os
import re
import sys

import yaml

GATE = "vars.HOSTED_CI == 'on' || github.event_name == 'workflow_dispatch'"
CHECK_ONLY = {"push", "pull_request", "workflow_dispatch", "merge_group"}
JOB = re.compile(r"^  (?![\s#])([^:]+):\s*(#.*)?$")
IF_LINE = re.compile(r"^    if:\s*(.*?)\s*$")


def triggers(doc):
    on = doc.get(True, doc.get("on")) or {}
    if isinstance(on, str):
        return {on}
    return set(on)


def unwrap(expr):
    expr = expr.strip()
    if len(expr) >= 2 and expr[0] == expr[-1] and expr[0] in "'\"":
        expr = expr[1:-1]
    m = re.fullmatch(r"\$\{\{\s*(.*?)\s*\}\}", expr, re.S)
    return m.group(1) if m else expr


def gate_text(text):
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", l))
    except StopIteration:
        return text
    out, i = lines[:start + 1], start + 1
    while i < len(lines):
        line = lines[i]
        if line and not line[0].isspace() and not line.startswith("#"):
            out.extend(lines[i:])
            break
        out.append(line)
        i += 1
        if not JOB.match(line):
            continue
        body = []
        while i < len(lines):
            nxt = lines[i]
            if JOB.match(nxt) or (nxt and not nxt[0].isspace() and not nxt.startswith("#")):
                break
            body.append(nxt)
            i += 1
        out.extend(gate_job(body))
    return "\n".join(out)


def gate_job(body):
    for n, line in enumerate(body):
        m = IF_LINE.match(line)
        if not m:
            continue
        value, end = m.group(1), n + 1
        if value in ("", ">", ">-", "|", "|-"):
            while end < len(body) and (body[end].startswith("      ") or not body[end].strip()):
                end += 1
            value = " ".join(l.strip() for l in body[n + 1:end] if l.strip())
        existing = unwrap(value)
        if "vars.HOSTED_CI" in existing:
            return body
        merged = f"    if: ${{{{ ({GATE}) && ({existing}) }}}}"
        return body[:n] + [merged] + body[end:]
    if any("vars.HOSTED_CI" in l for l in body):
        return body
    return [f"    if: ${{{{ {GATE} }}}}"] + body


def strip_ifs(doc):
    for job in (doc.get("jobs") or {}).values():
        if isinstance(job, dict):
            job.pop("if", None)
    return doc


def ungated_jobs(doc):
    return [name for name, job in (doc.get("jobs") or {}).items()
            if "vars.HOSTED_CI" not in str((job or {}).get("if", ""))]


def main(argv):
    check = "--check" in argv
    args = [a for a in argv if a != "--check"]
    wf_dir = os.path.join(args[0] if args else ".", ".github", "workflows")
    changed, missing = 0, []
    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        path = os.path.join(wf_dir, name)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        doc = yaml.safe_load(text) or {}
        if not triggers(doc) or not triggers(doc) <= CHECK_ONLY:
            continue
        if check:
            missing += [f"{name}:{job}" for job in ungated_jobs(doc)]
            continue
        new = gate_text(text)
        if new == text:
            continue
        new_doc = yaml.safe_load(new)
        if ungated_jobs(new_doc) or strip_ifs(new_doc) != strip_ifs(yaml.safe_load(text)):
            sys.exit(f"hosted_ci_gate: refusing to write {name}; edit did not round-trip")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
        changed += 1
    if check:
        for item in missing:
            print(f"ungated: {item}")
        return 1 if missing else 0
    print(f"hosted_ci_gate: gated {changed} workflow file(s) in {wf_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
