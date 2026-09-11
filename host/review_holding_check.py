#!/usr/bin/env python3
"""Reduce a review holding to a fail-closed GitHub check state.

The reducer is intentionally independent of the coordination-state producer.
It accepts one holding record and an exact target head SHA. A live review
holding on that exact head reduces to PENDING; an absent, released, expired,
or different-head holding reduces to SUCCESS; malformed evidence is INVALID.

With --publish-check, the same result is mirrored to a GitHub Check Run without
keeping a runner occupied: PENDING -> in_progress, SUCCESS -> completed/success,
INVALID -> completed/failure. A later invocation updates the same check by an
exact external_id derived from (key, head_sha).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SCHEMA = "commons-review-holding/v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CHECK_NAME = "commons/review-holding"


class InputError(ValueError):
    pass


def _exact_int(value, *, name: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise InputError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise InputError(f"{name} must be >= {minimum}")
    return value


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise InputError(f"{name} must be a lowercase 40-hex SHA")
    return value


def _timestamp(value: object, *, name: str) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise InputError(f"{name} must be UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise InputError(f"{name} is not a real UTC timestamp") from exc
    return parsed.replace(tzinfo=dt.timezone.utc)


def _now(value: str | None) -> dt.datetime:
    if value is None:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return _timestamp(value, name="now")


def _load(path: str | None) -> object | None:
    if path is None:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_no_duplicate_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"holding is unreadable JSON: {exc}") from exc


def _no_duplicate_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def evaluate(record: object | None, expected_head_sha: str, *, now: dt.datetime) -> dict:
    expected = _sha(expected_head_sha, name="expected_head_sha")
    if record is None:
        return {
            "schema": "commons-review-holding-check/v1",
            "state": "SUCCESS",
            "reason": "no_holding",
            "expected_head_sha": expected,
            "key": None,
            "holder": None,
            "expires_at": None,
        }
    if not isinstance(record, dict):
        raise InputError("holding must be a JSON object")
    if record.get("schema") != SCHEMA:
        raise InputError(f"holding.schema must equal {SCHEMA}")
    key = record.get("key")
    holder = record.get("holder")
    if not isinstance(key, str) or not key.strip() or len(key) > 240:
        raise InputError("holding.key must be a nonempty string <= 240 chars")
    if not isinstance(holder, str) or not holder.strip() or len(holder) > 160:
        raise InputError("holding.holder must be a nonempty string <= 160 chars")
    head = _sha(record.get("head_sha"), name="holding.head_sha")
    heartbeat = _timestamp(record.get("heartbeat_at"), name="holding.heartbeat_at")
    ttl_s = _exact_int(record.get("ttl_s"), name="holding.ttl_s", minimum=1)
    if ttl_s > 86400:
        raise InputError("holding.ttl_s must be <= 86400")
    if heartbeat > now:
        raise InputError("holding.heartbeat_at cannot be in the future")
    released_raw = record.get("released_at")
    released = None if released_raw is None else _timestamp(released_raw, name="holding.released_at")
    if released is not None and released < heartbeat:
        raise InputError("holding.released_at cannot precede heartbeat_at")
    expires = heartbeat + dt.timedelta(seconds=ttl_s)
    base = {
        "schema": "commons-review-holding-check/v1",
        "expected_head_sha": expected,
        "key": key,
        "holder": holder,
        "holding_head_sha": head,
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if head != expected:
        return {**base, "state": "SUCCESS", "reason": "different_head"}
    if released is not None and released <= now:
        return {**base, "state": "SUCCESS", "reason": "released"}
    if now >= expires:
        return {**base, "state": "SUCCESS", "reason": "expired"}
    remaining = int((expires - now).total_seconds())
    return {**base, "state": "PENDING", "reason": "live_review_holding", "remaining_s": remaining}


def _request(method: str, url: str, token: str, body: object | None = None) -> object:
    data = None if body is None else json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "commons-review-holding-check")
    request.add_header("Authorization", "Bearer " + token)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"GitHub API {method} {url} -> {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API {method} {url} -> {exc}") from exc
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def publish_check(result: dict, *, repo: str, token: str, check_name: str = CHECK_NAME) -> dict:
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
        raise InputError("repo must be owner/name")
    if not token:
        raise InputError("GitHub token is required for --publish-check")
    if not isinstance(check_name, str) or not check_name.strip() or len(check_name) > 100:
        raise InputError("check name must be nonempty and <= 100 chars")
    head = result["expected_head_sha"]
    key = result.get("key") or "none"
    external_id = f"review-holding:{key}:{head}"
    base = f"https://api.github.com/repos/{repo}"
    query = urllib.parse.urlencode({"check_name": check_name, "per_page": 100})
    listing = _request("GET", f"{base}/commits/{head}/check-runs?{query}", token)
    runs = listing.get("check_runs", []) if isinstance(listing, dict) else []
    matches = [r for r in runs if isinstance(r, dict) and r.get("external_id") == external_id]
    target_id = max((r.get("id") for r in matches if type(r.get("id")) is int), default=None)
    state = result["state"]
    if state == "PENDING":
        payload = {
            "name": check_name,
            "head_sha": head,
            "external_id": external_id,
            "status": "in_progress",
            "output": {
                "title": "Review holding active",
                "summary": f"{result['holder']} holds {result['key']} until {result['expires_at']} (UTC).",
            },
        }
    else:
        conclusion = "success" if state == "SUCCESS" else "failure"
        payload = {
            "name": check_name,
            "head_sha": head,
            "external_id": external_id,
            "status": "completed",
            "conclusion": conclusion,
            "completed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output": {
                "title": "Review holding clear" if conclusion == "success" else "Review holding evidence invalid",
                "summary": f"state={state}; reason={result.get('reason', 'invalid')}",
            },
        }
    if target_id is None:
        response = _request("POST", f"{base}/check-runs", token, payload)
        action = "created"
    else:
        update = dict(payload)
        update.pop("head_sha", None)
        response = _request("PATCH", f"{base}/check-runs/{target_id}", token, update)
        action = "updated"
    return {
        "action": action,
        "check_run_id": response.get("id") if isinstance(response, dict) else None,
        "check_name": check_name,
        "external_id": external_id,
        "status": payload["status"],
        "conclusion": payload.get("conclusion"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holding", help="path to one review-holding JSON record; omit for no holding")
    parser.add_argument("--expected-head-sha", required=True)
    parser.add_argument("--now", help="deterministic UTC timestamp for tests/replay")
    parser.add_argument("--publish-check", action="store_true")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--check-name", default=CHECK_NAME)
    args = parser.parse_args(argv)
    try:
        record = _load(args.holding)
        result = evaluate(record, args.expected_head_sha, now=_now(args.now))
    except InputError as exc:
        result = {
            "schema": "commons-review-holding-check/v1",
            "state": "INVALID",
            "reason": str(exc),
            "expected_head_sha": args.expected_head_sha,
        }
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    if args.publish_check:
        try:
            receipt = publish_check(result, repo=args.repo, token=args.token, check_name=args.check_name)
        except (InputError, RuntimeError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"publish failed: {exc}\n")
            return 4
        print(json.dumps(receipt, separators=(",", ":"), sort_keys=True))
    return {"SUCCESS": 0, "PENDING": 3, "INVALID": 2}.get(result.get("state"), 2)


if __name__ == "__main__":
    raise SystemExit(main())
