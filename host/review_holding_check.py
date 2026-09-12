#!/usr/bin/env python3
"""Reduce a review holding to a fail-closed GitHub check state.

The reducer is intentionally independent of the coordination-state producer.
It accepts one holding record, an exact target head SHA, and a monotonic
per-head observation generation. A live review holding on that exact head
reduces to PENDING; an absent, released, expired, or different-head holding
reduces to SUCCESS; malformed evidence is INVALID.

With --publish-check, each newer generation creates an immutable Check Run and
supersedes older in-progress generations only after the newer run exists.
Stale generations are ignored, so out-of-order claim/release delivery cannot
clear or resurrect a newer review-holding state.
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
GENERATION_RE = re.compile(r"^(0|[1-9][0-9]*)$")
MAX_GENERATION = 9_223_372_036_854_775_807
CHECK_NAME = "commons/review-holding"


class InputError(ValueError):
    pass


def _exact_int(value, *, name: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise InputError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise InputError(f"{name} must be >= {minimum}")
    return value


def _generation(value: object, *, name: str = "generation") -> int:
    value = _exact_int(value, name=name, minimum=0)
    if value > MAX_GENERATION:
        raise InputError(f"{name} must be <= {MAX_GENERATION}")
    return value


def _generation_text(value: object, *, name: str = "generation") -> int:
    if not isinstance(value, str) or GENERATION_RE.fullmatch(value) is None:
        raise InputError(f"{name} must be a canonical nonnegative integer string")
    return _generation(int(value), name=name)


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


def evaluate(
    record: object | None,
    expected_head_sha: str,
    *,
    now: dt.datetime,
    generation: int,
) -> dict:
    expected = _sha(expected_head_sha, name="expected_head_sha")
    generation = _generation(generation)
    if record is None:
        return {
            "schema": "commons-review-holding-check/v1",
            "state": "SUCCESS",
            "reason": "no_holding",
            "expected_head_sha": expected,
            "generation": generation,
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
        "generation": generation,
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


def _external_id(head: str, generation: int) -> str:
    return f"review-holding:{head}:g{generation}"


def _external_generation(value: object, *, head: str) -> int | None:
    if not isinstance(value, str):
        return None
    prefix = f"review-holding:{head}:g"
    if not value.startswith(prefix):
        return None
    suffix = value[len(prefix):]
    try:
        return _generation_text(suffix, name="check external generation")
    except InputError:
        return None


def _list_check_runs(*, base: str, head: str, check_name: str, token: str) -> list[dict]:
    collected: list[dict] = []
    for page in range(1, 101):
        query = urllib.parse.urlencode(
            {"check_name": check_name, "per_page": 100, "page": page}
        )
        listing = _request(
            "GET",
            f"{base}/commits/{head}/check-runs?{query}",
            token,
        )
        if not isinstance(listing, dict):
            raise RuntimeError("GitHub check-run listing is not an object")
        runs = listing.get("check_runs")
        if not isinstance(runs, list):
            raise RuntimeError("GitHub check-run listing lacks check_runs array")
        collected.extend(run for run in runs if isinstance(run, dict))
        total = listing.get("total_count")
        if type(total) is int and total >= 0 and len(collected) >= total:
            return collected
        if len(runs) < 100:
            return collected
    raise RuntimeError("GitHub check-run listing exceeded 100 pages")


def _published_state(run: dict) -> str:
    status = run.get("status")
    if status == "in_progress":
        return "PENDING"
    if status == "completed":
        conclusion = run.get("conclusion")
        if conclusion == "success":
            return "SUCCESS"
        if conclusion == "failure":
            return "INVALID"
    raise RuntimeError(
        f"existing review-holding check has unsupported status/conclusion: "
        f"{status!r}/{run.get('conclusion')!r}"
    )


def _payload(result: dict, *, check_name: str, external_id: str) -> dict:
    head = result["expected_head_sha"]
    generation = result["generation"]
    state = result["state"]
    if state == "PENDING":
        return {
            "name": check_name,
            "head_sha": head,
            "external_id": external_id,
            "status": "in_progress",
            "output": {
                "title": "Review holding active",
                "summary": (
                    f"generation={generation}; {result['holder']} holds "
                    f"{result['key']} until {result['expires_at']} (UTC)."
                ),
            },
        }
    conclusion = "success" if state == "SUCCESS" else "failure"
    return {
        "name": check_name,
        "head_sha": head,
        "external_id": external_id,
        "status": "completed",
        "conclusion": conclusion,
        "completed_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output": {
            "title": (
                "Review holding clear"
                if conclusion == "success"
                else "Review holding evidence invalid"
            ),
            "summary": (
                f"generation={generation}; state={state}; "
                f"reason={result.get('reason', 'invalid')}"
            ),
        },
    }


def _supersede_older_pending(
    family: list[tuple[int, dict]],
    *,
    generation: int,
    newer_check_id: int | None,
    base: str,
    token: str,
) -> None:
    completed_at = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    for old_generation, run in family:
        if old_generation >= generation or run.get("status") != "in_progress":
            continue
        run_id = run.get("id")
        if type(run_id) is not int:
            raise RuntimeError("older in-progress review-holding check lacks exact integer id")
        update = {
            "status": "completed",
            "conclusion": "success",
            "completed_at": completed_at,
            "output": {
                "title": "Review holding observation superseded",
                "summary": (
                    f"generation={old_generation} superseded by newer "
                    f"generation={generation}"
                    + (
                        f" (check_run_id={newer_check_id})."
                        if newer_check_id is not None
                        else "."
                    )
                ),
            },
        }
        _request("PATCH", f"{base}/check-runs/{run_id}", token, update)


def publish_check(result: dict, *, repo: str, token: str, check_name: str = CHECK_NAME) -> dict:
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
        raise InputError("repo must be owner/name")
    if not token:
        raise InputError("GitHub token is required for --publish-check")
    if not isinstance(check_name, str) or not check_name.strip() or len(check_name) > 100:
        raise InputError("check name must be nonempty and <= 100 chars")

    head = _sha(result.get("expected_head_sha"), name="result.expected_head_sha")
    generation = _generation(result.get("generation"), name="result.generation")
    state = result.get("state")
    if state not in {"PENDING", "SUCCESS", "INVALID"}:
        raise InputError("result.state must be PENDING, SUCCESS, or INVALID")

    base = f"https://api.github.com/repos/{repo}"
    runs = _list_check_runs(base=base, head=head, check_name=check_name, token=token)
    family: list[tuple[int, dict]] = []
    for run in runs:
        observed_generation = _external_generation(run.get("external_id"), head=head)
        if observed_generation is not None:
            family.append((observed_generation, run))

    max_generation = max((item[0] for item in family), default=None)
    if max_generation is not None and generation < max_generation:
        authoritative = max(
            (run for gen, run in family if gen == max_generation),
            key=lambda run: run.get("id") if type(run.get("id")) is int else -1,
        )
        return {
            "action": "ignored_stale",
            "check_run_id": authoritative.get("id"),
            "check_name": check_name,
            "external_id": authoritative.get("external_id"),
            "generation": generation,
            "authoritative_generation": max_generation,
            "status": authoritative.get("status"),
            "conclusion": authoritative.get("conclusion"),
        }

    external_id = _external_id(head, generation)
    same_generation = [run for gen, run in family if gen == generation]
    if same_generation:
        target = max(
            same_generation,
            key=lambda run: run.get("id") if type(run.get("id")) is int else -1,
        )
        published_state = _published_state(target)
        if published_state != state:
            raise RuntimeError(
                f"generation conflict for {generation}: "
                f"published={published_state} incoming={state}"
            )
        _supersede_older_pending(
            family,
            generation=generation,
            newer_check_id=target.get("id") if type(target.get("id")) is int else None,
            base=base,
            token=token,
        )
        return {
            "action": "unchanged",
            "check_run_id": target.get("id"),
            "check_name": check_name,
            "external_id": external_id,
            "generation": generation,
            "authoritative_generation": generation,
            "status": target.get("status"),
            "conclusion": target.get("conclusion"),
        }

    payload = _payload(result, check_name=check_name, external_id=external_id)
    response = _request("POST", f"{base}/check-runs", token, payload)
    new_id = response.get("id") if isinstance(response, dict) else None
    if type(new_id) is not int:
        raise RuntimeError("GitHub check-run create response lacks exact integer id")

    _supersede_older_pending(
        family,
        generation=generation,
        newer_check_id=new_id,
        base=base,
        token=token,
    )
    return {
        "action": "created",
        "check_run_id": new_id,
        "check_name": check_name,
        "external_id": external_id,
        "generation": generation,
        "authoritative_generation": generation,
        "status": payload["status"],
        "conclusion": payload.get("conclusion"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holding", help="path to one review-holding JSON record; omit for no holding")
    parser.add_argument("--expected-head-sha", required=True)
    parser.add_argument("--generation", required=True, help="monotonic per-head observation generation")
    parser.add_argument("--now", help="deterministic UTC timestamp for tests/replay")
    parser.add_argument("--publish-check", action="store_true")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--check-name", default=CHECK_NAME)
    args = parser.parse_args(argv)

    generation = None
    try:
        generation = _generation_text(args.generation)
        record = _load(args.holding)
        result = evaluate(
            record,
            args.expected_head_sha,
            now=_now(args.now),
            generation=generation,
        )
    except InputError as exc:
        result = {
            "schema": "commons-review-holding-check/v1",
            "state": "INVALID",
            "reason": str(exc),
            "expected_head_sha": args.expected_head_sha,
            "generation": generation,
        }
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))

    if args.publish_check:
        if generation is None:
            sys.stderr.write("publish failed: invalid observation generation\n")
            return 4
        try:
            receipt = publish_check(result, repo=args.repo, token=args.token, check_name=args.check_name)
        except (InputError, RuntimeError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"publish failed: {exc}\n")
            return 4
        print(json.dumps(receipt, separators=(",", ":"), sort_keys=True))
    return {"SUCCESS": 0, "PENDING": 3, "INVALID": 2}.get(result.get("state"), 2)


if __name__ == "__main__":
    raise SystemExit(main())
