"""Cancel stale job-watchdog ticks bound to pre-concurrency YAML.

Run 33211112146 on SHA 57d934d10fcfe7b63df057b5af4098df6c1f8ed0 waited
~80 minutes, ticked the stale checkout, then harness_wake.land hit
REBASE_CONFLICT on eight wake_jobs content splits and returned after one
attempt. Cite:
woahwhattheheck/commons:job-watchdog:57d934d10fcfe7b63df057b5af4098df6c1f8ed0:land job state on main only

#5124 composes compatible wake_jobs JSON. #5129 refreshes onto current
main. #5157 cancels redundant main ticks via concurrency, but GitHub
binds workflow YAML to the triggering SHA, so pre-concurrency snapshots
never join that group. Unique leftover: a current-main tick explicitly
cancels other queued/in-progress main ticks, including those snapshots.
Never --force. Fail open so compose+refresh+land still run.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Callable, Sequence

WORKFLOW_FILE = "job-watchdog.yml"
ACTIVE_STATUS = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
SKIP_EVENTS = frozenset({"pull_request"})


def _run_gh(
    args: Sequence[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = ["gh", *args]
    if any(part == "--force" or part.startswith("--force") for part in cmd):
        raise RuntimeError("force-push is forbidden")
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "check": False,
    }
    if env is not None:
        kwargs["env"] = env
    return run(cmd, **kwargs)


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


def select_stale_runs(runs: Sequence[dict[str, Any]], *, self_id: str) -> list[dict[str, Any]]:
    """Pick sibling main ticks that concurrency cannot see."""
    selected: list[dict[str, Any]] = []
    self_s = str(self_id or "")
    seen: set[str] = set()
    for run in runs:
        rid = str(run.get("databaseId") or run.get("id") or "")
        if not rid or rid == self_s or rid in seen:
            continue
        if str(run.get("event") or "") in SKIP_EVENTS:
            continue
        if str(run.get("status") or "") not in ACTIVE_STATUS:
            continue
        seen.add(rid)
        selected.append(run)
    return selected


def cancel_stale(
    *,
    self_id: str | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Cancel other active job-watchdog main ticks. Never --force."""
    run = run or subprocess.run
    env = dict(env or os.environ)
    self_id = str(self_id or env.get("GITHUB_RUN_ID") or "")
    if not self_id:
        return {"ok": True, "state": "NO_SELF_ID", "cancelled": [], "note": "no GITHUB_RUN_ID"}
    if not (env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")):
        return {"ok": True, "state": "NO_TOKEN", "cancelled": [], "note": "no token; fail open"}

    listed = _run_gh(
        [
            "run",
            "list",
            "--workflow",
            WORKFLOW_FILE,
            "--branch",
            "main",
            "--limit",
            "100",
            "--json",
            "databaseId,event,status,headSha",
        ],
        run=run,
        env=env,
    )
    if listed.returncode != 0:
        return {
            "ok": True,
            "state": "LIST_FAILED",
            "cancelled": [],
            "detail": _combined(listed),
            "note": "fail open; compose+refresh+land still run",
        }
    try:
        rows = json.loads(listed.stdout or "[]")
    except ValueError:
        return {
            "ok": True,
            "state": "LIST_UNPARSED",
            "cancelled": [],
            "detail": _combined(listed),
            "note": "fail open; compose+refresh+land still run",
        }
    if not isinstance(rows, list):
        rows = []
    stale = select_stale_runs([row for row in rows if isinstance(row, dict)], self_id=self_id)
    cancelled: list[str] = []
    errors: list[dict[str, str]] = []
    for row in stale:
        rid = str(row.get("databaseId") or row.get("id") or "")
        stopped = _run_gh(["run", "cancel", rid], run=run, env=env)
        if stopped.returncode == 0:
            cancelled.append(rid)
        else:
            errors.append({"id": rid, "detail": _combined(stopped)})
    receipt: dict[str, Any] = {
        "ok": True,
        "state": "CANCELLED" if cancelled else "QUIET",
        "self_id": self_id,
        "cancelled": cancelled,
        "stale_count": len(stale),
    }
    if errors:
        receipt["errors"] = errors
        receipt["note"] = "fail open; compose+refresh+land still run"
    return receipt


def main(argv: list[str] | None = None) -> int:
    del argv
    result = cancel_stale()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
