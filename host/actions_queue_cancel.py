#!/usr/bin/env python3
"""Cancel only GitHub Actions runs whose queued heads are provably stale.

This is the privileged companion to :mod:`host.actions_queue_triage`.  The
triager stays read-only.  This command is dry-run by default; ``--execute`` is
required before it sends a cancellation request.

Safety contract:

* only classifications already named by ``CANDIDATE_CLASSES`` are eligible;
* every candidate run is fetched again by id before action;
* complete branch and open-PR inventories are fetched twice per candidate;
* the second inventory refresh happens immediately before the final run read;
* the run is fetched one final time immediately before the POST;
* any moved head, non-queued status, inventory/read error, or reclassification
  to a keep/unknown state fails closed without a POST;
* ``--max-cancels`` bounds the number of cancellation POSTs in one invocation;
* the JSON receipt records dry-run / accepted / held outcomes without secrets.

Typical dry run::

    python -m host.actions_queue_cancel --repo woahwhattheheck/commons

Execute a bounded drain after inspecting the dry-run receipt::

    python -m host.actions_queue_cancel --repo woahwhattheheck/commons \
      --execute --max-cancels 25 --out /tmp/actions-cancel-receipt.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from host.actions_queue_triage import (
        CANDIDATE_CLASSES,
        GitHub,
        GitHubError,
        _discover_token,
        classify_run,
        make_snapshot,
    )
except ModuleNotFoundError:  # direct ``python host/actions_queue_cancel.py``
    from actions_queue_triage import (  # type: ignore[no-redef]
        CANDIDATE_CLASSES,
        GitHub,
        GitHubError,
        _discover_token,
        classify_run,
        make_snapshot,
    )

SCHEMA = "commons-actions-queue-cancel/v1"
DEFAULT_REPO = "woahwhattheheck/commons"


class CancelGitHub(GitHub):
    """GitHub reader plus the single mutation this command is allowed to make."""

    def cancel_run(self, run_id: int) -> int:
        if type(run_id) is not int or run_id <= 0:
            raise ValueError("run_id must be a positive integer")
        path = f"/repos/{self.repo}/actions/runs/{run_id}/cancel"
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=b"",
            method="POST",
        )
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "commons-actions-queue-cancel")
        if self.token:
            request.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                # GitHub documents 202 Accepted for a successful cancellation.
                response.read()
                return int(response.status)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise GitHubError(f"POST {path} -> HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"POST {path} -> {exc}") from exc


def _fresh_snapshot(github: GitHub, repo: str):
    branches = github.paged(f"/repos/{repo}/branches")
    open_prs = github.paged(f"/repos/{repo}/pulls?state=open")
    return make_snapshot(branches, open_prs)


def _run_id(run: dict[str, Any]) -> int | None:
    value = run.get("id")
    return value if type(value) is int and value > 0 else None


def _head_sha(run: dict[str, Any]) -> str | None:
    value = run.get("head_sha")
    if not isinstance(value, str) or len(value) != 40:
        return None
    if not all(ch in "0123456789abcdefABCDEF" for ch in value):
        return None
    return value.lower()


def _parse_created_at(run: dict[str, Any]) -> dt.datetime | None:
    value = run.get("created_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _candidate_age_seconds(run: dict[str, Any], now: dt.datetime) -> float | None:
    created = _parse_created_at(run)
    if created is None:
        return None
    return (now - created).total_seconds()


def _sorted_candidates(
    runs: list[dict[str, Any]], repo: str, snapshot
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for run in runs:
        classification = classify_run(run, snapshot, repo)
        if classification.get("cancel_candidate") is True:
            rows.append((run, classification))

    def key(item: tuple[dict[str, Any], dict[str, Any]]):
        run, _ = item
        created = _parse_created_at(run)
        stamp = created.timestamp() if created is not None else float("inf")
        return (stamp, _run_id(run) or 2**63)

    rows.sort(key=key)
    return rows


def drain_stale_runs(
    github: GitHub,
    repo: str,
    *,
    cap: int = 1000,
    max_cancels: int = 25,
    min_age_seconds: int = 60,
    execute: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Return a deterministic cancellation receipt; mutate only when execute=True."""
    if cap <= 0:
        raise ValueError("cap must be positive")
    if max_cancels <= 0:
        raise ValueError("max_cancels must be positive")
    if min_age_seconds < 0:
        raise ValueError("min_age_seconds must be non-negative")
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)

    runs, total = github.queued_runs(cap)
    initial_snapshot = _fresh_snapshot(github, repo)
    candidates = _sorted_candidates(runs, repo, initial_snapshot)

    results: list[dict[str, Any]] = []
    posts_attempted = 0
    accepted = 0
    holds = 0

    for original, initial_class in candidates:
        run_id = _run_id(original)
        initial_sha = _head_sha(original)
        base = {
            "run_id": run_id,
            "head_sha": initial_sha,
            "initial_classification": initial_class.get("classification"),
        }
        if run_id is None or initial_sha is None:
            holds += 1
            results.append({**base, "outcome": "HOLD_INVALID_INITIAL_RUN"})
            continue

        age = _candidate_age_seconds(original, now)
        if age is None:
            holds += 1
            results.append({**base, "outcome": "HOLD_INVALID_CREATED_AT"})
            continue
        if age < min_age_seconds:
            results.append(
                {
                    **base,
                    "age_seconds": round(age, 3),
                    "outcome": "KEEP_TOO_NEW",
                }
            )
            continue

        if posts_attempted >= max_cancels:
            results.append({**base, "outcome": "KEEP_BATCH_LIMIT"})
            continue

        try:
            live = github.get(f"/repos/{repo}/actions/runs/{run_id}")
            if not isinstance(live, dict):
                raise GitHubError("run re-read returned non-object")
            if live.get("status") != "queued":
                results.append(
                    {
                        **base,
                        "live_status": live.get("status"),
                        "outcome": "KEEP_NOT_QUEUED",
                    }
                )
                continue
            if _head_sha(live) != initial_sha:
                holds += 1
                results.append({**base, "outcome": "HOLD_HEAD_MOVED"})
                continue

            live_snapshot = _fresh_snapshot(github, repo)
            live_class = classify_run(live, live_snapshot, repo)
            live_label = live_class.get("classification")
            if not (
                live_class.get("cancel_candidate") is True
                and live_label in CANDIDATE_CLASSES
            ):
                results.append(
                    {
                        **base,
                        "live_classification": live_label,
                        "outcome": "KEEP_RECLASSIFIED",
                    }
                )
                continue

            # Refresh complete PR/branch authority one more time immediately
            # before the final run read. This narrows a reopened-PR / moved-ref
            # race without making the inventory the final read and thereby
            # widening the window in which a queued run could start executing.
            final_snapshot = _fresh_snapshot(github, repo)
            final_class = classify_run(live, final_snapshot, repo)
            final_label = final_class.get("classification")
            if not (
                final_class.get("cancel_candidate") is True
                and final_label in CANDIDATE_CLASSES
            ):
                results.append(
                    {
                        **base,
                        "live_classification": live_label,
                        "final_classification": final_label,
                        "outcome": "KEEP_RECLASSIFIED_FINAL",
                    }
                )
                continue

            # Final exact-run re-read immediately before any mutation. A run
            # that started, completed, or otherwise changed while inventories
            # were being refreshed is preserved.
            final_run = github.get(f"/repos/{repo}/actions/runs/{run_id}")
            if not isinstance(final_run, dict):
                raise GitHubError("final run re-read returned non-object")
            if final_run.get("status") != "queued":
                results.append(
                    {
                        **base,
                        "live_classification": live_label,
                        "final_classification": final_label,
                        "final_status": final_run.get("status"),
                        "outcome": "KEEP_NOT_QUEUED_FINAL",
                    }
                )
                continue
            if _head_sha(final_run) != initial_sha:
                holds += 1
                results.append(
                    {
                        **base,
                        "live_classification": live_label,
                        "final_classification": final_label,
                        "outcome": "HOLD_HEAD_MOVED_FINAL",
                    }
                )
                continue

            if not execute:
                results.append(
                    {
                        **base,
                        "live_classification": live_label,
                        "final_classification": final_label,
                        "outcome": "WOULD_CANCEL",
                    }
                )
                continue

            posts_attempted += 1
            cancel = getattr(github, "cancel_run", None)
            if not callable(cancel):
                raise GitHubError("GitHub client has no cancel_run mutation")
            status = cancel(run_id)
            if status != 202:
                raise GitHubError(f"cancel returned unexpected HTTP {status}")
            accepted += 1
            results.append(
                {
                    **base,
                    "live_classification": live_label,
                    "final_classification": final_label,
                    "cancel_http_status": status,
                    "outcome": "CANCEL_ACCEPTED",
                }
            )
        except (GitHubError, OSError, ValueError) as exc:
            holds += 1
            results.append(
                {
                    **base,
                    "outcome": "ERROR_HOLD",
                    "error": str(exc)[:300],
                }
            )

    return {
        "schema": SCHEMA,
        "observed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "mode": "execute" if execute else "dry_run",
        "queued_total_reported": total,
        "queued_runs_observed": len(runs),
        "queued_inventory_complete": isinstance(total, int) and total <= len(runs),
        "initial_cancel_candidates": len(candidates),
        "max_cancels": max_cancels,
        "min_age_seconds": min_age_seconds,
        "cancel_posts_attempted": posts_attempted,
        "cancel_accepted": accepted,
        "holds": holds,
        "safety": {
            "mutates_github": execute,
            "dry_run_default": True,
            "requires_live_reclassification": True,
            "requires_final_inventory_reread": True,
            "requires_final_run_reread": True,
            "candidate_classes": sorted(CANDIDATE_CLASSES),
        },
        "results": results,
    }


def _write_receipt(receipt: dict[str, Any], out: Path | None) -> None:
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if out is None:
        sys.stdout.write(text)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        body = text.encode("utf-8")
        view = memoryview(body)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--cap", type=int, default=1000)
    parser.add_argument("--max-cancels", type=int, default=25)
    parser.add_argument("--min-age-seconds", type=int, default=60)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out", type=Path, help="create-exclusive JSON receipt path")
    args = parser.parse_args(argv)

    if args.cap <= 0:
        parser.error("--cap must be positive")
    if args.max_cancels <= 0:
        parser.error("--max-cancels must be positive")
    if args.min_age_seconds < 0:
        parser.error("--min-age-seconds must be non-negative")

    token = _discover_token()
    if args.execute and not token:
        parser.error("--execute requires an available GitHub token")

    github = CancelGitHub(args.repo, token)
    try:
        receipt = drain_stale_runs(
            github,
            args.repo,
            cap=args.cap,
            max_cancels=args.max_cancels,
            min_age_seconds=args.min_age_seconds,
            execute=args.execute,
        )
        _write_receipt(receipt, args.out)
    except (GitHubError, OSError, ValueError) as exc:
        parser.exit(2, f"actions_queue_cancel: {exc}\n")

    return 2 if receipt["holds"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
