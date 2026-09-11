#!/usr/bin/env python3
"""Normalize Commons build/review receipts into a small, fail-closed JSON schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import PurePosixPath
from typing import Any

SCHEMA_VERSION = "commons-build-receipt/v1"
_REQUIRED = {
    "marker",
    "base",
    "head",
    "paths",
    "tests",
    "hosted",
    "provider_nonclaims",
    "release_state",
}
_ALLOWED = _REQUIRED | {"notes"}
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TEST_STATES = {"PASS", "FAIL", "NOT_RUN", "QUEUED", "PENDING", "CANCELLED"}
_HOSTED_STATES = {
    "NOT_RUN",
    "QUEUED",
    "PENDING",
    "SUCCESS",
    "FAILURE",
    "CANCELLED",
    "ACTION_REQUIRED",
    "MIXED",
}
_RELEASE_STATES = {"ACTIVE", "HOLD", "PUBLISHED", "RELEASED", "MERGED", "SUPERSEDED"}
_CHECKOUT_MODES = {"PR_MERGE_REF", "PR_HEAD_EXPLICIT", "PUSH_DISPATCH_SHA"}


class ReceiptError(ValueError):
    """Raised when a receipt is incomplete or ambiguous."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{field} must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise ReceiptError(f"{field} must be single-line")
    return value.strip()


def _sha(value: Any, field: str) -> str:
    text = _text(value, field).lower()
    if not _SHA_RE.fullmatch(text):
        raise ReceiptError(f"{field} must be a full 40-hex Git SHA")
    return text


def _path(value: Any) -> str:
    text = _text(value, "paths[]")
    if "\\" in text or text.startswith("/") or text.endswith("/"):
        raise ReceiptError(f"unsafe repo-relative path: {text!r}")
    path = PurePosixPath(text)
    canonical = path.as_posix()
    if canonical != text or any(part == ".." for part in path.parts):
        raise ReceiptError(f"unsafe or non-canonical repo-relative path: {text!r}")
    return canonical


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ReceiptError(f"{field} must be a list")
    out = [_text(item, f"{field}[]") for item in value]
    if len(out) != len(set(out)):
        raise ReceiptError(f"{field} contains duplicates")
    return sorted(out)


def _tests(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ReceiptError("tests must be a list")
    out: list[dict[str, str]] = []
    names: set[str] = set()
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise ReceiptError(f"tests[{idx}] must be an object")
        unknown = set(item) - {"name", "status", "command"}
        if unknown:
            raise ReceiptError(f"tests[{idx}] unknown keys: {sorted(unknown)}")
        name = _text(item.get("name"), f"tests[{idx}].name")
        if name in names:
            raise ReceiptError(f"duplicate test name: {name}")
        names.add(name)
        status = _text(item.get("status"), f"tests[{idx}].status").upper()
        if status not in _TEST_STATES:
            raise ReceiptError(f"tests[{idx}].status invalid: {status}")
        row = {"name": name, "status": status}
        if "command" in item:
            row["command"] = _text(item["command"], f"tests[{idx}].command")
        out.append(row)
    return sorted(out, key=lambda row: row["name"])


def _hosted(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReceiptError("hosted must be an object")
    unknown = set(value) - {"state", "runs"}
    if unknown:
        raise ReceiptError(f"hosted unknown keys: {sorted(unknown)}")
    state = _text(value.get("state"), "hosted.state").upper()
    if state not in _HOSTED_STATES:
        raise ReceiptError(f"hosted.state invalid: {state}")

    runs = value.get("runs", [])
    if not isinstance(runs, list):
        raise ReceiptError("hosted.runs must be a list")
    if state == "NOT_RUN" and runs:
        raise ReceiptError("NOT_RUN hosted state cannot carry runs")
    if state != "NOT_RUN" and not runs:
        raise ReceiptError(f"{state} hosted state requires at least one run")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    allowed = {
        "run_id",
        "event",
        "run_head_sha",
        "executed_checkout_sha",
        "checkout_mode",
    }
    for idx, item in enumerate(runs):
        if not isinstance(item, dict):
            raise ReceiptError(f"hosted.runs[{idx}] must be an object")
        unknown_run = set(item) - allowed
        missing_run = allowed - set(item)
        if missing_run:
            raise ReceiptError(
                f"hosted.runs[{idx}] missing keys: {sorted(missing_run)}"
            )
        if unknown_run:
            raise ReceiptError(
                f"hosted.runs[{idx}] unknown keys: {sorted(unknown_run)}"
            )

        run_id = item["run_id"]
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
            raise ReceiptError(
                f"hosted.runs[{idx}].run_id must be a positive integer"
            )
        if run_id in seen_ids:
            raise ReceiptError(f"duplicate hosted run_id: {run_id}")
        seen_ids.add(run_id)

        event = _text(item["event"], f"hosted.runs[{idx}].event")
        run_head_sha = _sha(
            item["run_head_sha"], f"hosted.runs[{idx}].run_head_sha"
        )
        executed = item["executed_checkout_sha"]
        if executed is not None:
            executed = _sha(
                executed, f"hosted.runs[{idx}].executed_checkout_sha"
            )
        mode = _text(
            item["checkout_mode"], f"hosted.runs[{idx}].checkout_mode"
        ).upper()
        if mode not in _CHECKOUT_MODES:
            raise ReceiptError(
                f"hosted.runs[{idx}].checkout_mode invalid: {mode}"
            )

        normalized.append(
            {
                "run_id": run_id,
                "event": event,
                "run_head_sha": run_head_sha,
                "executed_checkout_sha": executed,
                "checkout_mode": mode,
            }
        )
    return {"state": state, "runs": sorted(normalized, key=lambda row: row["run_id"])}


def normalize_receipt(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ReceiptError("receipt must be a JSON object")
    missing = _REQUIRED - set(payload)
    unknown = set(payload) - _ALLOWED
    if missing:
        raise ReceiptError(f"missing keys: {sorted(missing)}")
    if unknown:
        raise ReceiptError(f"unknown keys: {sorted(unknown)}")

    marker = _text(payload["marker"], "marker")
    base = _sha(payload["base"], "base")
    head = _sha(payload["head"], "head")

    raw_paths = payload["paths"]
    if not isinstance(raw_paths, list):
        raise ReceiptError("paths must be a list")
    paths = [_path(item) for item in raw_paths]
    if len(paths) != len(set(paths)):
        raise ReceiptError("paths contains duplicates")

    release_state = _text(payload["release_state"], "release_state").upper()
    if release_state not in _RELEASE_STATES:
        raise ReceiptError(f"release_state invalid: {release_state}")

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "marker": marker,
        "base": base,
        "head": head,
        "paths": sorted(paths),
        "tests": _tests(payload["tests"]),
        "hosted": _hosted(payload["hosted"]),
        "provider_nonclaims": _string_list(
            payload["provider_nonclaims"], "provider_nonclaims"
        ),
        "release_state": release_state,
    }
    if "notes" in payload:
        receipt["notes"] = _text(payload["notes"], "notes")
    return receipt


def canonical_json(payload: Any) -> str:
    return json.dumps(
        normalize_receipt(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="receipt JSON file, or '-' for stdin",
    )
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            payload = json.load(sys.stdin)
        else:
            with open(args.input, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        sys.stdout.write(canonical_json(payload) + "\n")
        return 0
    except (OSError, json.JSONDecodeError, ReceiptError) as exc:
        print(f"build-receipt: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
