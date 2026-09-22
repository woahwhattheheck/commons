#!/usr/bin/env python3
"""Run a repo's GitHub Actions checks inside the current cloud session.

Private-repo Actions minutes bill the owner's card, so hosted jobs there are
switched off (they skip unless the repo variable HOSTED_CI is "on"). Sessions
run the same checks in their own container instead, before pushing:

    curl -fsSL https://raw.githubusercontent.com/woahwhattheheck/commons/main/tools/sandbox_ci.py | python3 -

Run it from the repo root. It reads .github/workflows/*.yml, picks the
workflows whose push/pull_request path filters match the files this branch
changed, and runs each job's `run:` steps once with the session's own tools.
`uses:` steps (checkout, setup-python, ...) are skipped because the checkout
and toolchain already exist here. Matrix jobs run once, with the first value
of each matrix axis. The result is a markdown table to paste into the PR.

Options:
  --base REF      diff base (default: merge-base with origin's default branch)
  --list          show the selected workflows and exit
  --all           run every push/pull_request workflow, ignoring path filters
  --workflow F    run only this workflow file (repeatable)
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import yaml
except ImportError:
    sys.exit("sandbox_ci: needs PyYAML (pip install pyyaml)")

CHECK_EVENTS = ("pull_request", "push")
EXPR = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")


def git(*args):
    return subprocess.run(("git",) + args, capture_output=True, text=True).stdout.strip()


def default_base():
    head = git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    for ref in filter(None, (head, "origin/main", "origin/master")):
        base = git("merge-base", "HEAD", ref)
        if base:
            return base
    return "HEAD"


def changed_files(base):
    files = set()
    for args in (("diff", "--name-only", base, "HEAD"),
                 ("diff", "--name-only", "HEAD"),
                 ("ls-files", "--others", "--exclude-standard")):
        files.update(line for line in git(*args).splitlines() if line)
    return sorted(files)


def glob_match(path, pattern):
    """GitHub path-filter glob: ** crosses directories, * does not."""
    rx, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            rx, i = rx + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            rx, i = rx + ".*", i + 2
        elif pattern[i] == "*":
            rx, i = rx + "[^/]*", i + 1
        elif pattern[i] == "?":
            rx, i = rx + "[^/]", i + 1
        else:
            rx, i = rx + re.escape(pattern[i]), i + 1
    return re.fullmatch(rx, path) is not None


def filter_hits(files, spec):
    """True if an event's paths/paths-ignore filter admits any changed file."""
    if not isinstance(spec, dict):
        return True
    if "paths" in spec:
        hits = False
        for f in files:
            keep = False
            for pat in spec["paths"] or []:
                neg = pat.startswith("!")
                if glob_match(f, pat[1:] if neg else pat):
                    keep = not neg
            hits = hits or keep
        return hits
    if "paths-ignore" in spec:
        ignore = spec["paths-ignore"] or []
        return any(not any(glob_match(f, p) for p in ignore) for f in files)
    return True


def triggers(doc):
    on = doc.get(True, doc.get("on")) or {}
    if isinstance(on, str):
        on = {on: None}
    if isinstance(on, list):
        on = {k: None for k in on}
    return on


def selected(doc, files, run_all):
    on = triggers(doc)
    events = [e for e in CHECK_EVENTS if e in on]
    if not events:
        return False
    return run_all or any(filter_hits(files, on[e]) for e in events)


def axis_first(value):
    """First value of a matrix axis, including `${{ fromJSON(... '[..]') }}` axes.

    For the `cond && '[a]' || '[b]'` idiom the last list is the push/PR branch.
    """
    if isinstance(value, list):
        return value[0] if value else None
    for literal in reversed(re.findall(r"'(\[.*?\])'", str(value))):
        try:
            items = json.loads(literal)
        except ValueError:
            continue
        if items:
            return items[0]
    return None


def first_matrix(job):
    matrix = ((job.get("strategy") or {}).get("matrix")) or {}
    if not isinstance(matrix, dict):
        return {}
    values = {}
    for k, v in matrix.items():
        if k in ("include", "exclude"):
            continue
        first = axis_first(v)
        if first is not None:
            values[k] = first
    for extra in matrix.get("include") or []:
        if isinstance(extra, dict):
            for k, v in extra.items():
                values.setdefault(k, v)
    return values


def expand(text, matrix):
    def sub(m):
        expr = m.group(1)
        if expr.startswith("matrix."):
            return str(matrix.get(expr[7:], ""))
        if expr == "github.workspace":
            return os.getcwd()
        if expr in ("runner.temp",):
            return os.environ.get("TMPDIR", "/tmp")
        if expr in ("runner.os",):
            return "Linux"
        return ""
    return EXPR.sub(sub, str(text))


def pick_python(job, matrix):
    """Interpreter for the job: the setup-python version if installed, else the newest."""
    wanted = ""
    for step in job.get("steps") or []:
        if "setup-python" in str(step.get("uses", "")):
            wanted = expand((step.get("with") or {}).get("python-version", ""), matrix)
    match = re.match(r"(\d+\.\d+)", str(wanted).strip())
    if match and shutil.which("python" + match.group(1)):
        return shutil.which("python" + match.group(1))
    for minor in range(20, 7, -1):
        found = shutil.which(f"python3.{minor}")
        if found:
            return found
    return shutil.which("python3")


def python_shim(interpreter):
    shim = tempfile.mkdtemp(prefix="sandbox_ci_")
    for name in ("python", "python3"):
        os.symlink(interpreter, os.path.join(shim, name))
    return shim


def run_job(job, wf_env, matrix):
    shim = python_shim(pick_python(job, matrix))
    try:
        return run_steps(job, wf_env, matrix, shim)
    finally:
        shutil.rmtree(shim, ignore_errors=True)


def run_steps(job, wf_env, matrix, shim):
    env = dict(os.environ, CI="true", GITHUB_ACTIONS="", GITHUB_WORKSPACE=os.getcwd(),
               PATH=shim + os.pathsep + os.environ.get("PATH", ""))
    for scope in (wf_env or {}, job.get("env") or {}):
        env.update({k: expand(v, matrix) for k, v in scope.items()})
    defaults = ((job.get("defaults") or {}).get("run")) or {}
    for step in job.get("steps") or []:
        if "run" not in step:
            continue
        step_env = dict(env)
        step_env.update({k: expand(v, matrix) for k, v in (step.get("env") or {}).items()})
        cwd = step.get("working-directory") or defaults.get("working-directory") or "."
        shell = step.get("shell") or defaults.get("shell") or "bash"
        script = expand(step["run"], matrix)
        cmd = ["bash", "-eo", "pipefail", "-c", script] if shell.startswith("bash") or shell == "sh" \
            else [shell.split()[0], "-c", script]
        label = step.get("name") or script.splitlines()[0][:80]
        print(f"  $ {label}", flush=True)
        proc = subprocess.run(cmd, cwd=expand(cwd, matrix), env=step_env)
        if proc.returncode != 0:
            return f"fail: {label}"
    return "pass"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workflow", action="append", default=[])
    args = ap.parse_args()

    wf_dir = os.path.join(".github", "workflows")
    if not os.path.isdir(wf_dir):
        sys.exit("sandbox_ci: run from a repo root with .github/workflows")
    files = changed_files(args.base or default_base())
    picked = []
    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        if args.workflow and not any(fnmatch.fnmatch(name, w) for w in args.workflow):
            continue
        with open(os.path.join(wf_dir, name), encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        if args.workflow or selected(doc, files, args.all):
            picked.append((name, doc))

    print(f"sandbox_ci: {len(files)} changed file(s), {len(picked)} workflow(s) selected")
    if args.list or not picked:
        for name, _ in picked:
            print(f"  {name}")
        return 0

    rows, failed = [], 0
    for name, doc in picked:
        for job_id, job in (doc.get("jobs") or {}).items():
            if "uses" in job:
                rows.append((name, job_id, "skipped: reusable workflow", 0))
                continue
            print(f"== {name} / {job_id}", flush=True)
            start = time.time()
            result = run_job(job, doc.get("env"), first_matrix(job))
            failed += result != "pass"
            rows.append((name, job_id, result, time.time() - start))

    print("\n| Workflow | Job | Result | Seconds |\n|---|---|---|---|")
    for name, job_id, result, secs in rows:
        print(f"| {name} | {job_id} | {result} | {secs:.0f} |")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
