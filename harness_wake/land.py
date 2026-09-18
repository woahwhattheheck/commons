"""Land wake_jobs state onto moving main. Never force-push."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

COMMIT_MESSAGE = "jobs: watchdog tick (no model)"
MAX_ATTEMPTS = 5
WAKE_JOBS = "wake_jobs"
REMOTE_REF = "HEAD:main"
TERMINAL_STATUS = frozenset({"DONE", "CANCELLED", "EXHAUSTED"})
MAX_INT_KEYS = ("attempt_count", "tokens_used", "no_progress_count")
LAST_TICK_COUNT_KEYS = (
    "wake_count",
    "stop_count",
    "backoff_count",
    "invoke_model_count",
)

RACE_MARKERS = (
    "failed to push some refs",
    "fetch first",
    "[rejected]",
    "non-fast-forward",
    "updates were rejected because the remote contains work",
)


def _run_git(
    args: Sequence[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
    cwd: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    if any(part == "--force" or part.startswith("--force") for part in cmd):
        raise RuntimeError("force-push is forbidden")
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "capture_output": True,
        "text": True,
        "check": False,
    }
    if env is not None:
        kwargs["env"] = env
    return run(cmd, **kwargs)


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


def is_push_race(result: subprocess.CompletedProcess[str]) -> bool:
    if result.returncode == 0:
        return False
    blob = _combined(result).lower()
    return any(marker in blob for marker in RACE_MARKERS)


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _unique_rows(rows: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for row in rows:
        key = json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _freshness(job: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(job.get("updated_at") or job.get("ts") or ""),
        str(job.get("created_at") or ""),
        _as_int(job.get("attempt_count")),
    )


def _order(left: dict[str, Any], right: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return (left, right) if _freshness(left) >= _freshness(right) else (right, left)


def compose_last_tick(ours: dict[str, Any], theirs: dict[str, Any]) -> dict[str, Any]:
    winner, loser = _order(ours, theirs)
    composed = json.loads(json.dumps(winner))
    ids: list[Any] = []
    seen: set[str] = set()
    for ident in list(winner.get("wake_job_ids") or []) + list(loser.get("wake_job_ids") or []):
        key = str(ident)
        if key in seen:
            continue
        seen.add(key)
        ids.append(ident)
    composed["wake_job_ids"] = ids
    for key in LAST_TICK_COUNT_KEYS:
        composed[key] = max(_as_int(ours.get(key)), _as_int(theirs.get(key)))
    return composed


def _compose_checkpoint(winner: Any, loser: Any) -> Any:
    if winner == loser or not isinstance(winner, dict):
        return winner
    composed = json.loads(json.dumps(winner))
    if not isinstance(loser, dict):
        return composed
    win_exec = winner.get("execution") if isinstance(winner.get("execution"), dict) else {}
    lose_exec = loser.get("execution") if isinstance(loser.get("execution"), dict) else {}
    if win_exec or lose_exec:
        execution = dict(win_exec)
        execution["blockers"] = _unique_rows(
            list(win_exec.get("blockers") or []) + list(lose_exec.get("blockers") or [])
        )
        execution["failed_executors"] = _unique_rows(
            list(win_exec.get("failed_executors") or [])
            + list(lose_exec.get("failed_executors") or [])
        )
        composed["execution"] = execution
    return composed


def compose_wake_job(ours: dict[str, Any], theirs: dict[str, Any]) -> dict[str, Any] | None:
    """Union append-only receipts; keep the fresher snapshot for the rest."""
    if ours == theirs:
        return ours
    our_id = ours.get("job_id")
    their_id = theirs.get("job_id")
    if our_id and their_id and our_id != their_id:
        return None
    if "wake_job_ids" in ours or "wake_job_ids" in theirs:
        return compose_last_tick(ours, theirs)

    ours_term = ours.get("status") in TERMINAL_STATUS
    theirs_term = theirs.get("status") in TERMINAL_STATUS
    if ours_term and theirs_term and ours.get("status") != theirs.get("status"):
        return None

    winner, loser = _order(ours, theirs)
    if ours_term or theirs_term:
        winner = ours if ours_term else theirs
        loser = theirs if ours_term else ours

    composed = json.loads(json.dumps(winner))
    composed["event_receipts"] = _unique_rows(
        list(winner.get("event_receipts") or []) + list(loser.get("event_receipts") or [])
    )
    for key in MAX_INT_KEYS:
        composed[key] = max(_as_int(ours.get(key)), _as_int(theirs.get(key)))
    composed["checkpoint"] = _compose_checkpoint(
        winner.get("checkpoint"), loser.get("checkpoint")
    )
    if our_id or their_id:
        composed["job_id"] = our_id or their_id
    return composed


def compose_wake_json(ours_text: str, theirs_text: str) -> str | None:
    """Compose two wake_jobs JSON snapshots. None means a real semantic split."""
    try:
        ours = json.loads(ours_text)
        theirs = json.loads(theirs_text)
    except ValueError:
        return None
    if not isinstance(ours, dict) or not isinstance(theirs, dict):
        return None
    composed = compose_wake_job(ours, theirs)
    if composed is None:
        return None
    return _dump(composed)


def _show_stage(
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
    cwd: str,
    stage: int,
    path: str,
) -> str | None:
    shown = _run_git(["show", ":%d:%s" % (stage, path)], run=run, cwd=cwd)
    if shown.returncode != 0:
        return None
    return shown.stdout or ""


def resolve_wake_jobs_rebase(
    *,
    cwd: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    """Compose compatible wake_jobs JSON during rebase. Never --force."""
    listed = _run_git(
        ["diff", "--name-only", "--diff-filter=U"],
        run=run,
        cwd=cwd,
    )
    if listed.returncode != 0:
        return {"ok": False, "reason": "UNMERGED_LIST_FAILED", "detail": _combined(listed)}
    paths = [row.strip() for row in (listed.stdout or "").splitlines() if row.strip()]
    if not paths:
        return {"ok": False, "reason": "NO_UNMERGED"}
    for path in paths:
        if not path.startswith(WAKE_JOBS + "/") or not path.endswith(".json"):
            return {"ok": False, "reason": "NON_JOB_PATH", "path": path}
        ours = _show_stage(run=run, cwd=cwd, stage=2, path=path)
        theirs = _show_stage(run=run, cwd=cwd, stage=3, path=path)
        if ours is None or theirs is None:
            return {"ok": False, "reason": "MISSING_STAGE", "path": path}
        composed = compose_wake_json(ours, theirs)
        if composed is None:
            return {"ok": False, "reason": "SEMANTIC_DISAGREE", "path": path}
        dest = Path(cwd) / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(composed, encoding="utf-8")
        added = _run_git(["add", "--", path], run=run, cwd=cwd)
        if added.returncode != 0:
            return {"ok": False, "reason": "ADD_FAILED", "path": path, "detail": _combined(added)}
    env = os.environ.copy()
    env["GIT_EDITOR"] = "true"
    env["GIT_SEQUENCE_EDITOR"] = "true"
    continued = _run_git(["rebase", "--continue"], run=run, cwd=cwd, env=env)
    if continued.returncode == 0:
        return {"ok": True, "state": "COMPOSED", "paths": paths}
    blob = _combined(continued).lower()
    if "nothing to commit" in blob or "no changes" in blob:
        skipped = _run_git(["rebase", "--skip"], run=run, cwd=cwd)
        if skipped.returncode == 0:
            return {"ok": True, "state": "ALREADY_ON_HEAD", "paths": paths}
        return {"ok": False, "reason": "SKIP_FAILED", "detail": _combined(skipped)}
    return {"ok": False, "reason": "CONTINUE_FAILED", "detail": _combined(continued)}


def land(
    *,
    cwd: str = ".",
    attempts: int = MAX_ATTEMPTS,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleep: Callable[[float], Any] | None = None,
) -> dict[str, Any]:
    """Commit wake_jobs and retry push+rebase while main moves under us."""
    run = run or subprocess.run
    sleep = sleep or time.sleep

    added = _run_git(["add", WAKE_JOBS], run=run, cwd=cwd)
    if added.returncode != 0:
        return {"ok": False, "state": "GIT_ADD_FAILED", "detail": _combined(added)}

    staged = _run_git(["diff", "--cached", "--quiet"], run=run, cwd=cwd)
    if staged.returncode == 0:
        return {"ok": True, "state": "QUIET", "note": "quiet"}

    committed = _run_git(["commit", "-m", COMMIT_MESSAGE], run=run, cwd=cwd)
    if committed.returncode != 0:
        return {"ok": False, "state": "COMMIT_FAILED", "detail": _combined(committed)}

    last_push: subprocess.CompletedProcess[str] | None = None
    last_resolve: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        pushed = _run_git(["push", "origin", REMOTE_REF], run=run, cwd=cwd)
        last_push = pushed
        if pushed.returncode == 0:
            receipt = {"ok": True, "state": "LANDED", "attempts": attempt}
            if last_resolve is not None:
                receipt["resolve"] = last_resolve
            return receipt
        if not is_push_race(pushed):
            return {
                "ok": False,
                "state": "PUSH_FAILED",
                "detail": _combined(pushed),
                "attempts": attempt,
            }
        fetched = _run_git(["fetch", "origin", "main"], run=run, cwd=cwd)
        if fetched.returncode != 0:
            return {
                "ok": False,
                "state": "FETCH_FAILED",
                "detail": _combined(fetched),
                "attempts": attempt,
            }
        rebased = _run_git(["rebase", "origin/main"], run=run, cwd=cwd)
        if rebased.returncode != 0:
            resolved = resolve_wake_jobs_rebase(cwd=cwd, run=run)
            last_resolve = resolved
            if resolved.get("ok"):
                if attempt < attempts:
                    sleep(attempt * 3)
                continue
            _run_git(["rebase", "--abort"], run=run, cwd=cwd)
            return {
                "ok": False,
                "state": "REBASE_CONFLICT",
                "detail": _combined(rebased),
                "attempts": attempt,
                "resolve": resolved,
            }
        if attempt < attempts:
            sleep(attempt * 3)
    return {
        "ok": False,
        "state": "PUSH_RACE",
        "note": "push failed after %s attempts" % attempts,
        "detail": _combined(last_push) if last_push is not None else "",
        "attempts": attempts,
    }


def main(argv: list[str] | None = None) -> int:
    del argv
    result = land()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
