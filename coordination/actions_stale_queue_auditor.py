#!/usr/bin/env python3
"""Deterministic read-only auditor for stale queued GitHub Actions runs.

This module never calls GitHub and never cancels, reruns, merges, or mutates refs.
It classifies a retained provenance snapshot only. A privileged operator must
perform a fresh live reread before any cancellation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRODUCT = "ActionsStaleQueueAuditor"
VERSION = "1"
INPUT_SCHEMA = "actions-stale-queue-audit.input.v1"
REPORT_SCHEMA = "actions-stale-queue-audit.report.v1"

MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_JSON_BYTES = 1_048_576
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 20_000
MAX_RUNS = 2_000
MAX_PULL_REQUESTS_PER_RUN = 256

HEX40 = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")

INPUT_KEYS = {"schema", "repository", "default_branch", "observed_at", "runs"}
RUN_KEYS = {
    "run_id", "workflow", "event", "status", "head_branch", "head_sha", "provenance",
}
PROVENANCE_KEYS = {"complete", "sources", "pull_requests"}
PR_KEYS = {"number", "state", "current_head_sha"}

REPORT_KEYS = {
    "schema", "product", "version", "repository", "default_branch", "observed_at",
    "input_digest", "authority", "retained_input", "rows", "counts", "report_receipt",
}
ROW_KEYS = {
    "run_id", "workflow", "head_branch", "head_sha", "decision", "reasons",
    "associated_pr_numbers", "requires_live_reread",
}
AUTHORITY_KEYS = {
    "cancel_run_authorized", "rerun_authorized", "merge_authorized",
    "ref_mutation_authorized", "provider_mutation_authorized", "outbound_authorized",
    "payment_authorized", "revenue_recognition_authorized",
}

# Capture semantic provenance policy into function defaults. These immutable public
# views may be rebound by a caller, but that does not widen this import generation.
_REQUIRED_PROVENANCE_SOURCES_LITERAL = frozenset(
    {"RUN_DIRECT", "BRANCH_QUERY", "COMMIT_QUERY"}
)
_ALLOWED_PROVENANCE_SOURCES_LITERAL = _REQUIRED_PROVENANCE_SOURCES_LITERAL
REQUIRED_PROVENANCE_SOURCES = _REQUIRED_PROVENANCE_SOURCES_LITERAL
ALLOWED_PROVENANCE_SOURCES = _ALLOWED_PROVENANCE_SOURCES_LITERAL


class AuditError(ValueError):
    """Stable fail-closed boundary for invalid audit input or report."""


def _exact_keys(
    value: Any, expected: set[str] | frozenset[str], label: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuditError(f"{label} must be an exact object")
    keys = set(value)
    expected_set = set(expected)
    if keys != expected_set:
        raise AuditError(
            f"{label} schema mismatch missing={sorted(expected_set - keys)} "
            f"unknown={sorted(keys - expected_set)}"
        )
    return dict(value)


def _exact_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise AuditError(f"{label} must be an exact boolean")
    return value


def _exact_int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_SAFE_INTEGER,
) -> int:
    if type(value) is not int:
        raise AuditError(f"{label} must be an exact integer")
    if not minimum <= value <= maximum:
        raise AuditError(f"{label} outside {minimum}..{maximum}")
    return value


def _bounded_string(value: Any, label: str, *, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise AuditError(f"{label} must be a nonempty string <= {maximum} chars")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise AuditError(f"{label} contains control characters")
    return value


def _sha(value: Any, label: str) -> str:
    value = _bounded_string(value, label, maximum=40)
    if not HEX40.fullmatch(value):
        raise AuditError(f"{label} must be lowercase 40-hex commit SHA")
    return value


def _utc(value: Any, label: str) -> str:
    value = _bounded_string(value, label, maximum=32)
    if not value.endswith("Z"):
        raise AuditError(f"{label} must use canonical UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AuditError(f"{label} must be canonical UTC seconds") from exc
    canonical = (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed) or canonical != value:
        raise AuditError(f"{label} must be canonical UTC seconds")
    return value


def _json_string_serialized_size(value: str, *, remaining: int) -> int:
    """Exact UTF-8 byte size for this encoder, before serializer entry."""
    if type(value) is not str:
        raise AuditError("JSON string must be an exact string")
    if len(value) + 2 > remaining:
        raise AuditError(f"canonical JSON exceeds {MAX_JSON_BYTES} bytes")
    total = 2
    for ch in value:
        code = ord(ch)
        if 0xD800 <= code <= 0xDFFF:
            raise AuditError("JSON string contains surrogate code point")
        if ch == '"' or ch == "\\":
            step = 2
        elif code in {0x08, 0x09, 0x0A, 0x0C, 0x0D}:
            step = 2
        elif code < 0x20:
            step = 6
        elif code <= 0x7F:
            step = 1
        elif code <= 0x7FF:
            step = 2
        elif code <= 0xFFFF:
            step = 3
        else:
            step = 4
        total += step
        if total > remaining:
            raise AuditError(f"canonical JSON exceeds {MAX_JSON_BYTES} bytes")
    return total


def _freeze_plain_json(value: Any) -> Any:
    """Detach exact JSON and charge every node/canonical byte before dumps.

    Repeated aliases are charged once per serialized occurrence. Dict keys count
    as work nodes. Immediate container cardinality is rejected before children
    are touched, and over-budget direct objects fail before json.dumps is called.
    """
    nodes = [0]
    bytes_used = [0]

    def charge(amount: int) -> None:
        if type(amount) is not int or amount < 0:
            raise AuditError("invalid canonical JSON work charge")
        if amount > MAX_JSON_BYTES - bytes_used[0]:
            raise AuditError(f"canonical JSON exceeds {MAX_JSON_BYTES} bytes")
        bytes_used[0] += amount

    def take_node() -> None:
        nodes[0] += 1
        if nodes[0] > MAX_JSON_NODES:
            raise AuditError(f"JSON node count exceeds {MAX_JSON_NODES}")

    def string_cost(item: str) -> int:
        return _json_string_serialized_size(
            item, remaining=MAX_JSON_BYTES - bytes_used[0]
        )

    def freeze(item: Any, depth: int) -> Any:
        if depth > MAX_JSON_DEPTH:
            raise AuditError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        take_node()
        if item is None:
            charge(4)
            return None
        if type(item) is bool:
            charge(4 if item else 5)
            return item
        if type(item) is int:
            checked = _exact_int(
                item,
                "JSON integer",
                minimum=-MAX_SAFE_INTEGER,
                maximum=MAX_SAFE_INTEGER,
            )
            charge(len(str(checked)))
            return checked
        if type(item) is str:
            charge(string_cost(item))
            return item
        if type(item) is list:
            remaining_nodes = MAX_JSON_NODES - nodes[0]
            if len(item) > remaining_nodes:
                raise AuditError("JSON container exceeds remaining node budget")
            charge(2 + max(0, len(item) - 1))
            return [freeze(child, depth + 1) for child in item]
        if type(item) is dict:
            remaining_nodes = MAX_JSON_NODES - nodes[0]
            if len(item) * 2 > remaining_nodes:
                raise AuditError("JSON object exceeds remaining node budget")
            charge(2 + max(0, len(item) - 1) + len(item))
            out: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise AuditError("JSON object keys must be exact strings")
                take_node()
                charge(string_cost(key))
                out[key] = freeze(child, depth + 1)
            return out
        raise AuditError(f"unsupported JSON value type: {type(item).__name__}")

    return freeze(value, 0)


def _parse_int_token(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if not digits or len(digits) > 16:
        raise AuditError("JSON integer token exceeds safe integer digit bound")
    try:
        value = int(token)
    except ValueError as exc:
        raise AuditError("invalid JSON integer token") from exc
    if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
        raise AuditError("JSON integer outside safe integer range")
    return value


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AuditError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: str) -> Any:
    if type(raw) is not str:
        raise AuditError("JSON input must be text")
    try:
        raw_size = len(raw.encode("utf-8", "strict"))
    except UnicodeError as exc:
        raise AuditError("JSON input is not valid Unicode text") from exc
    if raw_size > MAX_JSON_BYTES:
        raise AuditError(f"raw JSON exceeds {MAX_JSON_BYTES} bytes")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_pairs_no_dupes,
            parse_int=_parse_int_token,
            parse_float=lambda token: (_ for _ in ()).throw(
                AuditError(f"floating point JSON forbidden: {token}")
            ),
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"non-finite JSON forbidden: {token}")
            ),
        )
    except AuditError:
        raise
    except (
        json.JSONDecodeError, TypeError, ValueError, OverflowError,
        RecursionError, UnicodeError,
    ) as exc:
        raise AuditError(f"invalid JSON: {exc}") from exc
    return _freeze_plain_json(value)


def canonical_json(value: Any) -> bytes:
    frozen = _freeze_plain_json(value)
    try:
        return json.dumps(
            frozen,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise AuditError(f"cannot canonicalize JSON: {exc}") from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_pr(value: Any) -> dict[str, Any]:
    row = _exact_keys(value, PR_KEYS, "pull request")
    number = _exact_int(row["number"], "pull request number", minimum=1)
    state = _bounded_string(row["state"], "pull request state", maximum=6)
    if state not in {"OPEN", "CLOSED"}:
        raise AuditError("pull request state must be OPEN or CLOSED")
    return {
        "number": number,
        "state": state,
        "current_head_sha": _sha(row["current_head_sha"], "current_head_sha"),
    }


def _normalize_run(
    value: Any,
    *,
    _allowed_sources: frozenset[str] = _ALLOWED_PROVENANCE_SOURCES_LITERAL,
) -> dict[str, Any]:
    row = _exact_keys(value, RUN_KEYS, "run")
    run_id = _exact_int(row["run_id"], "run_id", minimum=1)
    workflow = _bounded_string(row["workflow"], "workflow", maximum=256)
    event = _bounded_string(row["event"], "event", maximum=64)
    status = _bounded_string(row["status"], "status", maximum=32)
    head_branch = _bounded_string(row["head_branch"], "head_branch", maximum=256)
    head_sha = _sha(row["head_sha"], "head_sha")

    provenance = _exact_keys(row["provenance"], PROVENANCE_KEYS, "provenance")
    complete = _exact_bool(provenance["complete"], "provenance.complete")
    sources_raw = provenance["sources"]
    if type(sources_raw) is not list:
        raise AuditError("provenance.sources must be a list")
    if len(sources_raw) > len(_allowed_sources):
        raise AuditError("too many provenance sources")
    sources: list[str] = []
    for source_value in sources_raw:
        source = _bounded_string(source_value, "provenance source", maximum=32)
        if source not in _allowed_sources:
            raise AuditError(f"unknown provenance source: {source}")
        if source in sources:
            raise AuditError(f"duplicate provenance source: {source}")
        sources.append(source)
    sources.sort()

    prs_raw = provenance["pull_requests"]
    if type(prs_raw) is not list:
        raise AuditError("provenance.pull_requests must be a list")
    if len(prs_raw) > MAX_PULL_REQUESTS_PER_RUN:
        raise AuditError("too many associated pull requests")
    prs = [_normalize_pr(item) for item in prs_raw]
    by_number: dict[int, dict[str, Any]] = {}
    for pr in prs:
        prior = by_number.get(pr["number"])
        if prior is not None:
            if canonical_json(prior) != canonical_json(pr):
                raise AuditError(
                    f"pull request {pr['number']} has conflicting retained provenance"
                )
            raise AuditError(f"duplicate pull request {pr['number']}")
        by_number[pr["number"]] = pr

    return {
        "run_id": run_id,
        "workflow": workflow,
        "event": event,
        "status": status,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "provenance": {
            "complete": complete,
            "sources": sources,
            "pull_requests": [by_number[number] for number in sorted(by_number)],
        },
    }


def normalize_packet(packet: Any) -> dict[str, Any]:
    frozen = _freeze_plain_json(packet)
    row = _exact_keys(frozen, INPUT_KEYS, "audit packet")
    if row["schema"] != INPUT_SCHEMA:
        raise AuditError("wrong audit input schema")
    repository = _bounded_string(row["repository"], "repository", maximum=201)
    if not REPO.fullmatch(repository):
        raise AuditError("repository must be owner/name")
    default_branch = _bounded_string(
        row["default_branch"], "default_branch", maximum=256
    )
    observed_at = _utc(row["observed_at"], "observed_at")

    runs_raw = row["runs"]
    if type(runs_raw) is not list:
        raise AuditError("runs must be a list")
    if len(runs_raw) > MAX_RUNS:
        raise AuditError(f"runs exceeds {MAX_RUNS}")
    runs = [_normalize_run(item) for item in runs_raw]
    by_id: dict[int, dict[str, Any]] = {}
    for run in runs:
        if run["run_id"] in by_id:
            raise AuditError(f"duplicate run_id: {run['run_id']}")
        by_id[run["run_id"]] = run
    return {
        "schema": INPUT_SCHEMA,
        "repository": repository,
        "default_branch": default_branch,
        "observed_at": observed_at,
        "runs": [by_id[run_id] for run_id in sorted(by_id)],
    }


def _classify(
    run: dict[str, Any],
    default_branch: str,
    *,
    _required_sources: frozenset[str] = _REQUIRED_PROVENANCE_SOURCES_LITERAL,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if run["status"] != "queued":
        reasons.append("RUN_NOT_QUEUED")
    if run["event"] != "pull_request":
        reasons.append("EVENT_NOT_PULL_REQUEST")
    if run["head_branch"] == default_branch:
        reasons.append("DEFAULT_BRANCH")

    provenance = run["provenance"]
    if not provenance["complete"]:
        reasons.append("PROVENANCE_INCOMPLETE")
    if set(provenance["sources"]) != set(_required_sources):
        reasons.append("PROVENANCE_SOURCES_INCOMPLETE")
    prs = provenance["pull_requests"]
    if not prs:
        reasons.append("PROVENANCE_EMPTY")
    if any(
        pr["state"] == "OPEN" and pr["current_head_sha"] == run["head_sha"]
        for pr in prs
    ):
        reasons.append("OPEN_PR_CURRENT_HEAD")

    if reasons:
        return "HOLD", sorted(set(reasons))
    return "SAFE_TO_CANCEL", ["ALL_ASSOCIATED_PRS_CLOSED_OR_STALE"]


def build_report(packet: Any) -> dict[str, Any]:
    retained = normalize_packet(packet)
    rows: list[dict[str, Any]] = []
    for run in retained["runs"]:
        decision, reasons = _classify(run, retained["default_branch"])
        rows.append(
            {
                "run_id": run["run_id"],
                "workflow": run["workflow"],
                "head_branch": run["head_branch"],
                "head_sha": run["head_sha"],
                "decision": decision,
                "reasons": reasons,
                "associated_pr_numbers": [
                    pr["number"] for pr in run["provenance"]["pull_requests"]
                ],
                "requires_live_reread": True,
            }
        )

    counts = {
        "HOLD": sum(row["decision"] == "HOLD" for row in rows),
        "SAFE_TO_CANCEL": sum(row["decision"] == "SAFE_TO_CANCEL" for row in rows),
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "product": PRODUCT,
        "version": VERSION,
        "repository": retained["repository"],
        "default_branch": retained["default_branch"],
        "observed_at": retained["observed_at"],
        "input_digest": sha256_hex(canonical_json(retained)),
        "authority": {
            "cancel_run_authorized": False,
            "rerun_authorized": False,
            "merge_authorized": False,
            "ref_mutation_authorized": False,
            "provider_mutation_authorized": False,
            "outbound_authorized": False,
            "payment_authorized": False,
            "revenue_recognition_authorized": False,
        },
        "retained_input": retained,
        "rows": rows,
        "counts": counts,
    }
    report["report_receipt"] = sha256_hex(canonical_json(report))
    return report


def verify_report(report: Any) -> bool:
    frozen = _freeze_plain_json(report)
    row = _exact_keys(frozen, REPORT_KEYS, "audit report")
    if (
        row["schema"] != REPORT_SCHEMA
        or row["product"] != PRODUCT
        or row["version"] != VERSION
    ):
        raise AuditError("wrong report schema/product/version")

    if type(row["authority"]) is not dict or set(row["authority"]) != AUTHORITY_KEYS:
        raise AuditError("authority schema mismatch")
    for name in sorted(AUTHORITY_KEYS):
        value = row["authority"][name]
        if type(value) is not bool or value is not False:
            raise AuditError(f"authority {name} must be literal false")

    retained = normalize_packet(row["retained_input"])
    if row["repository"] != retained["repository"]:
        raise AuditError("repository binding mismatch")
    if row["default_branch"] != retained["default_branch"]:
        raise AuditError("default branch binding mismatch")
    if row["observed_at"] != retained["observed_at"]:
        raise AuditError("observation binding mismatch")
    if row["input_digest"] != sha256_hex(canonical_json(retained)):
        raise AuditError("input digest mismatch")

    supplied = row["report_receipt"]
    if type(supplied) is not str or len(supplied) != 64 or any(
        ch not in "0123456789abcdef" for ch in supplied
    ):
        raise AuditError("report_receipt must be lowercase SHA-256 hex")
    unsigned = dict(row)
    unsigned.pop("report_receipt")
    if sha256_hex(canonical_json(unsigned)) != supplied:
        raise AuditError("report receipt mismatch")

    if type(row["rows"]) is not list:
        raise AuditError("rows must be a list")
    for item in row["rows"]:
        checked = _exact_keys(item, ROW_KEYS, "audit row")
        _exact_int(checked["run_id"], "audit row run_id", minimum=1)
        _bounded_string(checked["workflow"], "audit row workflow", maximum=256)
        _bounded_string(checked["head_branch"], "audit row head_branch", maximum=256)
        _sha(checked["head_sha"], "audit row head_sha")
        if checked["decision"] not in {"SAFE_TO_CANCEL", "HOLD"}:
            raise AuditError("unknown audit decision")
        if type(checked["reasons"]) is not list or not checked["reasons"]:
            raise AuditError("audit reasons must be a nonempty list")
        for reason in checked["reasons"]:
            _bounded_string(reason, "audit reason", maximum=64)
        if type(checked["associated_pr_numbers"]) is not list:
            raise AuditError("associated_pr_numbers must be a list")
        for number in checked["associated_pr_numbers"]:
            _exact_int(number, "associated PR number", minimum=1)
        if _exact_bool(checked["requires_live_reread"], "requires_live_reread") is not True:
            raise AuditError("requires_live_reread must be literal true")

    counts = _exact_keys(row["counts"], {"HOLD", "SAFE_TO_CANCEL"}, "counts")
    _exact_int(counts["HOLD"], "counts.HOLD")
    _exact_int(counts["SAFE_TO_CANCEL"], "counts.SAFE_TO_CANCEL")

    rebuilt = build_report(retained)
    if canonical_json(rebuilt) != canonical_json(row):
        raise AuditError("semantic recompile mismatch")
    return True


def _read_json(path: str) -> Any:
    if path == "-":
        raw = sys.stdin.read(MAX_JSON_BYTES + 1)
    else:
        with Path(path).open("rb") as handle:
            data = handle.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise AuditError(f"raw JSON exceeds {MAX_JSON_BYTES} bytes")
        try:
            raw = data.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise AuditError("JSON file must be strict UTF-8") from exc
    return loads_strict(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile", help="compile retained audit input")
    compile_cmd.add_argument("input", help="input JSON file or - for stdin")
    verify_cmd = sub.add_parser("verify", help="verify an audit report")
    verify_cmd.add_argument("report", help="report JSON file or - for stdin")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            report = build_report(_read_json(args.input))
            sys.stdout.buffer.write(canonical_json(report) + b"\n")
            return 0
        verify_report(_read_json(args.report))
        sys.stdout.write('{"valid":true}\n')
        return 0
    except (AuditError, OSError, UnicodeError) as exc:
        sys.stderr.write(f"AUDIT_ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
