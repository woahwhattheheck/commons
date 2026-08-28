"""Land wake_jobs state onto moving main. Never force-push."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

COMMIT_MESSAGE = "jobs: watchdog tick (no model)"
MAX_ATTEMPTS = 5
WAKE_JOBS = "wake_jobs"
REMOTE_REF = "HEAD:main"

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
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    if any(part == "--force" or part.startswith("--force") for part in cmd):
        raise RuntimeError("force-push is forbidden")
    return run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


def is_push_race(result: subprocess.CompletedProcess[str]) -> bool:
    if result.returncode == 0:
        return False
    blob = _combined(result).lower()
    return any(marker in blob for marker in RACE_MARKERS)


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
    for attempt in range(1, attempts + 1):
        pushed = _run_git(["push", "origin", REMOTE_REF], run=run, cwd=cwd)
        last_push = pushed
        if pushed.returncode == 0:
            return {"ok": True, "state": "LANDED", "attempts": attempt}
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
            _run_git(["rebase", "--abort"], run=run, cwd=cwd)
            return {
                "ok": False,
                "state": "REBASE_CONFLICT",
                "detail": _combined(rebased),
                "attempts": attempt,
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
