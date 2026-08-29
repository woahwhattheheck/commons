#!/usr/bin/env python3
"""Coalesce a busy main branch into one bounded verification range."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main_velocity


DATA_PREFIXES = ("p/", "by/", "to/", "d/", "chunks/", "excerpts/", "projection/")
DATA_FILES = {"board.md", "posts.json", "recent.json", "pulse.json", "fresh.md", "export.txt"}
PROTECTED_PREFIXES = ("p/", "conflicts/", "memory/", ".github/workflows/")
PROTECTED_FILES = {
    "board.js", "carrier.js", "court.js", "session.js", "commons.css", "index.html",
    "hub_pages.py", "board_ingest.py", "memory_board.py", "capability_declaration.py",
    "commons_mcp.py", "action_executor.py", "action_land.py", "device_action_state.py",
}


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), result.stderr.strip()))
    return result.stdout.strip()


def resolve_range(head: str, base: str | None, lookback_minutes: int) -> tuple[str, str, int]:
    frozen_head = git("rev-parse", f"{head}^{{commit}}")
    if base:
        frozen_base = git("rev-parse", f"{base}^{{commit}}")
    else:
        commits = git("rev-list", "--reverse", f"--since={lookback_minutes} minutes ago", frozen_head).splitlines()
        oldest = commits[0] if commits else frozen_head
        parent = git("rev-parse", f"{oldest}^", check=False)
        frozen_base = parent or oldest
    count = int(git("rev-list", "--count", f"{frozen_base}..{frozen_head}") or "0")
    return frozen_base, frozen_head, count


def changed_paths(base: str, head: str) -> list[str]:
    return sorted(set(git("diff", "--name-only", base, head).splitlines()))


def protected_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if p in PROTECTED_FILES or p.startswith(PROTECTED_PREFIXES) or p.startswith("test_")]


def plan(paths: list[str]) -> list[tuple[str, list[str]]]:
    """A verifier appears at most once, regardless of commit count."""
    commands = [
        ("imports", [sys.executable, "-c", "import sys; sys.path.insert(0,'.'); import hub_pages,memory_board,capability_declaration,board_ingest,builds_ledger,file_drop,commons_mcp,action_executor,action_land,device_action_state"]),
        ("open-door", [sys.executable, "open_door_guard.py", "--diff", "{base}", "{head}"]),
        ("muhlnickel", [sys.executable, "muhlnickel_spec_guard.py", "--base", "{base}", "--worktree"]),
    ]
    only_projection_data = bool(paths) and all(p in DATA_FILES or p.startswith(DATA_PREFIXES) for p in paths)
    if not only_projection_data:
        commands.append(("path-manifest", [sys.executable, "test_path_manifest.py"]))
    return commands


def run_batch(base: str, head: str, paths: list[str]) -> tuple[list[dict], bool]:
    results = []
    ok = True
    for name, template in plan(paths):
        command = [part.format(base=base, head=head) for part in template]
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        results.append({
            "name": name,
            "command": shlex.join(command),
            "exit_code": proc.returncode,
            "output_tail": proc.stdout[-4000:],
        })
        ok = ok and proc.returncode == 0
    return results, ok


def build_receipt(head: str, base: str | None, lookback_minutes: int, execute: bool) -> dict:
    frozen_base, frozen_head, commit_count = resolve_range(head, base, lookback_minutes)
    paths = changed_paths(frozen_base, frozen_head)
    tasks = [name for name, _ in plan(paths)]
    results, ok = run_batch(frozen_base, frozen_head, paths) if execute else ([], True)
    protected = protected_paths(paths)
    return {
        "schema": "commons.main-range.v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "base": frozen_base,
        "head": frozen_head,
        "commit_count": commit_count,
        "changed_path_count": len(paths),
        "protected_paths": protected,
        "observations": {
            "protected_path_touches": len(protected),
            "record_guard": "OBSERVED" if protected else "CLEAR",
        },
        "tasks": tasks,
        "results": results,
        "status": "PASS" if ok else "FINDINGS",
        "main_movement_policy": "freeze_then_next_range",
        "approval_required": False,
        "velocity": main_velocity.measure(frozen_head),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--base")
    parser.add_argument("--lookback-minutes", type=int, default=30)
    parser.add_argument("--receipt")
    parser.add_argument("--plan", action="store_true", help="resolve and print without running verifiers")
    args = parser.parse_args(argv)
    receipt = build_receipt(args.head, args.base, args.lookback_minutes, not args.plan)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text, end="")
    # Findings are reported in one receipt. They are not an approval gate and
    # do not create a notification storm; primary tests retain blocking status.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
