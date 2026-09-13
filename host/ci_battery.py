#!/usr/bin/env python3
"""Run the Commons CI battery on a clean cloud-worker checkout.

The default discovery is shared with tests.yml: root test_*.py, recursive
infra/test_*.py, then root test_*.js. Every selected file runs after failures.
Use --output-dir for portable JSON evidence, or --results for the existing
Actions NUL stream. Dirty worktrees fail closed before any test executes.
No provider API, Docker daemon, or new credentials are needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

try:
    from . import battery_report
except ImportError:
    import battery_report


def discover(root: Path) -> list[tuple[str, str]]:
    python = [p for p in root.glob("test_*.py") if p.is_file() and not p.is_symlink()]
    infra = root / "infra"
    if infra.is_dir() and not infra.is_symlink():
        # os.walk does not descend through directory symlinks, like find.
        for directory, _, files in os.walk(infra, followlinks=False):
            python.extend(Path(directory) / name for name in files
                          if name.startswith("test_") and name.endswith(".py")
                          and (Path(directory) / name).is_file()
                          and not (Path(directory) / name).is_symlink())
    paths = sorted((p.relative_to(root).as_posix() for p in python), key=os.fsencode)
    node = sorted((p.name for p in root.glob("test_*.js") if p.is_file()), key=os.fsencode)
    return [("python3", p) for p in paths] + [("node", p) for p in node]


def record(handle, command: str, path: str, code: str | int) -> None:
    handle.write(b"".join(os.fsencode(str(value)) + b"\0" for value in (command, path, code)))
    handle.flush()


def execute(root: Path, command: str, path: str, timeout: float | None) -> int:
    argv = [sys.executable if command == "python3" else command, "./" + path]
    try:
        process = subprocess.Popen(argv, cwd=root, start_new_session=os.name == "posix")
    except OSError:
        print("could not start test: " + json.dumps(path), file=sys.stderr, flush=True)
        return 127
    try:
        rc = process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait()
        if isinstance(exc, KeyboardInterrupt):
            raise
        print("test timed out: " + json.dumps(path), file=sys.stderr, flush=True)
        return 124
    return min(255, 128 - rc) if rc < 0 else min(255, rc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, help="directory for results.nul and report.json")
    parser.add_argument("--results", type=Path, help="write the existing Actions-compatible raw stream")
    parser.add_argument("--report", type=Path, help="also write checkout-linked JSON")
    parser.add_argument("--test", action="append", default=[], help="select a discovered test path; repeatable")
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0, help="zero-based shard number")
    parser.add_argument("--timeout", type=float, default=0, help="per-file seconds; 0 preserves the unbounded battery")
    parser.add_argument("--list", action="store_true", help="list selected commands without executing")
    args = parser.parse_args(argv)
    if args.output_dir and args.results:
        parser.error("use --output-dir or --results, not both")
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        parser.error("shard index must be between zero and shard count minus one")
    if not math.isfinite(args.timeout) or args.timeout < 0:
        parser.error("timeout must be finite and nonnegative")
    root = args.root.resolve()
    discovered = discover(root)
    requested = list(dict.fromkeys(p[2:] if p.startswith("./") else p for p in args.test))
    missing = sorted(set(requested) - {path for _, path in discovered})
    if missing:
        parser.error("test paths were not discovered: " + json.dumps(missing))
    selected = [row for row in discovered if not requested or row[1] in requested]
    selected = selected[args.shard_index::args.shard_count]
    if args.list:
        print(json.dumps(selected, indent=2))
        return 0
    if args.results:
        results = args.results.resolve()
        report_path = args.report.resolve() if args.report else None
    else:
        output = (args.output_dir or Path(tempfile.mkdtemp(prefix="commons-ci-"))).resolve()
        results = output / "results.nul"
        report_path = args.report.resolve() if args.report else output / "report.json"
    if report_path == results:
        parser.error("report and results must be different files")
    # Never let an output path truncate a selected test before execution.
    inputs = {root / path for _, path in selected}
    if results in inputs or report_path in inputs:
        parser.error("output paths must differ from selected test paths")

    outcome = "success"
    code = 0
    file_hashes = {}
    scope = {"kind": "selected" if requested else "full", "requested": requested,
             "shard_index": args.shard_index, "shard_count": args.shard_count,
             "discovered_files": len(discovered), "planned_files": len(selected)}
    if args.shard_count > 1:
        scope["kind"] = "selected-shard" if requested else "shard"
    dirty = None
    preflight_error = None

    try:
        # Measure checkout state before creating any output inside the repository.
        # Otherwise a clean run using an in-repo output directory can mark itself
        # dirty and weaken the starting-state claim.
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
                             check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True, capture_output=True,
        ).stdout)
        results.parent.mkdir(parents=True, exist_ok=True)
        with results.open("wb") as handle:
            record(handle, "checkout_sha", sha, "")
            if dirty:
                preflight_error = "dirty_worktree"
                outcome, code = "failure", 2
                print("refusing to execute battery from a dirty worktree", file=sys.stderr)
            else:
                for command, path in selected:
                    try:
                        file_hashes[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
                    except OSError:
                        file_hashes[path] = None
                    rc = execute(root, command, path, args.timeout or None)
                    record(handle, command, "./" + path, rc)
                    code = int(bool(code or rc))
                    print(("ok   " if rc == 0 else "FAIL ") + json.dumps(path), flush=True)
                record(handle, "battery_complete", "", code)
                outcome = "failure" if code else "success"
                if not selected:
                    print("no tests matched; no passing battery evidence", file=sys.stderr)
                    code = 1
    except KeyboardInterrupt:
        outcome, code = "cancelled", 130
    except (OSError, subprocess.CalledProcessError):
        print("battery could not read its checkout or write results", file=sys.stderr)
        outcome, code = "failure", 2

    if report_path:
        try:
            raw = results.read_bytes() if results.exists() else None
            report = battery_report.build_report(root, raw, outcome, os.environ)
            report["scope"] = scope
            report["execution"] = {
                "kind": "direct-process",
                "python_version": sys.version.split()[0],
                "worktree_dirty_at_start": dirty,
                "preflight_error": preflight_error,
                "test_file_sha256": file_hashes,
            }
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            print(report["conclusion"] + ": " + str(report_path), flush=True)
            if report["conclusion"] != "PASSED" and code == 0:
                code = 1
        except OSError:
            print("battery report could not read or write its local result files", file=sys.stderr)
            return code or 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
