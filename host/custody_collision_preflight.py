#!/usr/bin/env python3
"""Fail-closed, read-only pre-claim custody collision classifier.

This tool does not take claims or mutate Slack/GitHub. It combines normalized
observations gathered by existing connectors / command-center roads and emits a
single source-backed disposition. Any absence-dependent decision requires the
relevant inventories to be explicitly marked complete.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from host import coordination_state as cs
except ImportError:  # Direct execution as ``python host/custody_collision_preflight.py``.
    import coordination_state as cs  # type: ignore

SCHEMA = "commons-custody-collision-preflight/v1"
VERDICTS = {
    "ALREADY_INTEGRATED",
    "COLLISION",
    "OVERLAP_REVIEW",
    "UNKNOWN_HOLD",
    "SAFE_TO_CLAIM",
}
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SOURCE_KINDS = {"source_take", "source_claim", "owned", "carrier"}
_NEUTRAL_KINDS = {"build_order", "idea", "demand", "release", "handoff"}
_ACTIVE_STATES = {"open", "active", "held", "pending", "draft"}


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA_RE.fullmatch(value))


def _norm_sha(value: Any) -> str | None:
    return value.lower() if _valid_sha(value) else None


def _norm_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().replace("\\", "/")
    if not value or value.startswith("/") or "\x00" in value:
        return None
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    return "/".join(parts)


def _paths(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    out = set()
    for raw in rows:
        path = _norm_path(raw)
        if path:
            out.add(path)
    return out


def _blob_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for raw_path, raw_sha in value.items():
        path = _norm_path(raw_path)
        sha = _norm_sha(raw_sha)
        if path and sha:
            out[path] = sha
    return out


def _pr_identity(value: Any) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    repo = value.get("repo")
    number = value.get("number")
    if not isinstance(repo, str) or repo.count("/") != 1:
        return None
    if type(number) is not int or number <= 0:
        return None
    return repo.lower(), number


def _canonical_operation(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return cs.change_key(value=value.strip())


def _complete(snapshot: dict[str, Any], name: str) -> bool:
    complete = snapshot.get("complete")
    return isinstance(complete, dict) and complete.get(name) is True


def _evidence(kind: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "reason": reason, **extra}


def classify(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Classify one normalized pre-claim snapshot without side effects."""
    if not isinstance(snapshot, dict):
        return _result("UNKNOWN_HOLD", [_evidence("invalid", "snapshot must be an object")])

    operation_key = _canonical_operation(snapshot.get("operation_id"))
    holder = snapshot.get("holder")
    candidate = snapshot.get("candidate")
    if not operation_key or not isinstance(holder, str) or not holder.strip() or not isinstance(candidate, dict):
        return _result(
            "UNKNOWN_HOLD",
            [_evidence("invalid", "operation_id, non-empty holder, and candidate object are required")],
            operation_key=operation_key,
        )
    holder = holder.strip()

    candidate_pr = _pr_identity(candidate.get("upstream_pr"))
    candidate_paths = _paths(candidate.get("paths"))
    donor_blobs = _blob_map(candidate.get("donor_blobs"))
    owner_default = snapshot.get("owner_default") if isinstance(snapshot.get("owner_default"), dict) else {}
    owner_blobs = _blob_map(owner_default.get("blobs"))
    evidence: list[dict[str, Any]] = []

    # Exact positive proof that source is already on the owner default branch.
    if donor_blobs:
        matched = sorted(path for path, sha in donor_blobs.items() if owner_blobs.get(path) == sha)
        if len(matched) == len(donor_blobs):
            evidence.append(_evidence(
                "owner_default_exact_blob",
                "every candidate donor blob is already the owner-default blob",
                paths=matched,
            ))
            return _result("ALREADY_INTEGRATED", evidence, operation_key=operation_key)

    # Slack/message custody evidence. Build orders and handoffs are neutral;
    # only explicit source-custody kinds can establish collision.
    slack_rows = snapshot.get("slack") if isinstance(snapshot.get("slack"), list) else []
    for index, row in enumerate(slack_rows):
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "").strip().lower()
        row_holder = str(row.get("holder") or "").strip()
        row_key = _canonical_operation(row.get("operation_id"))
        row_pr = _pr_identity(row.get("upstream_pr"))
        same_holder = row_holder == holder if row_holder else False
        if kind in _SOURCE_KINDS and not same_holder:
            if row_key and row_key == operation_key:
                evidence.append(_evidence(
                    "slack_exact_operation_custody",
                    "another holder has explicit source custody for the canonical operation",
                    index=index, holder=row_holder or None,
                ))
                return _result("COLLISION", evidence, operation_key=operation_key)
            if candidate_pr and row_pr == candidate_pr:
                evidence.append(_evidence(
                    "slack_exact_upstream_pr_custody",
                    "another holder has explicit source custody for the same upstream PR",
                    index=index, holder=row_holder or None,
                    upstream_pr={"repo": candidate_pr[0], "number": candidate_pr[1]},
                ))
                return _result("COLLISION", evidence, operation_key=operation_key)
        elif kind in _NEUTRAL_KINDS and (row_key == operation_key or (candidate_pr and row_pr == candidate_pr)):
            evidence.append(_evidence(
                "source_neutral_message",
                "matching build-order/handoff evidence is not source custody",
                index=index, message_kind=kind,
            ))

    # Owner-fork carrier census. Exact operation/upstream identity or exact donor
    # blob on an active carrier is collision proof. Path-only overlap is routed
    # for composition review, not mislabeled semantic conflict.
    overlaps: list[dict[str, Any]] = []
    owner_rows = snapshot.get("owner_prs") if isinstance(snapshot.get("owner_prs"), list) else []
    for row in owner_rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("state") or "").strip().lower()
        if state and state not in _ACTIVE_STATES:
            continue
        row_holder = str(row.get("holder") or "").strip()
        if row_holder and row_holder == holder:
            continue
        row_key = _canonical_operation(row.get("operation_id"))
        row_pr = _pr_identity(row.get("upstream_pr"))
        number = row.get("number") if type(row.get("number")) is int else None
        if row_key and row_key == operation_key:
            evidence.append(_evidence(
                "owner_carrier_exact_operation",
                "an active owner-fork carrier matches the canonical operation",
                number=number, holder=row_holder or None,
            ))
            return _result("COLLISION", evidence, operation_key=operation_key)
        if candidate_pr and row_pr == candidate_pr:
            evidence.append(_evidence(
                "owner_carrier_exact_upstream_pr",
                "an active owner-fork carrier matches the same upstream PR",
                number=number, holder=row_holder or None,
            ))
            return _result("COLLISION", evidence, operation_key=operation_key)

        row_blobs = _blob_map(row.get("blobs"))
        exact_blob_paths = sorted(path for path, sha in donor_blobs.items() if row_blobs.get(path) == sha)
        if donor_blobs and exact_blob_paths:
            evidence.append(_evidence(
                "owner_carrier_exact_donor_blob",
                "an active owner-fork carrier already carries a candidate donor blob",
                number=number, paths=exact_blob_paths,
            ))
            return _result("COLLISION", evidence, operation_key=operation_key)

        shared = sorted(candidate_paths & _paths(row.get("paths")))
        if shared:
            overlaps.append({"number": number, "holder": row_holder or None, "paths": shared})

    if overlaps:
        evidence.append(_evidence(
            "owner_carrier_path_overlap",
            "active carrier touches candidate paths; semantic compatibility must be checked",
            carriers=overlaps,
        ))
        return _result("OVERLAP_REVIEW", evidence, operation_key=operation_key)

    required = ("slack", "owner_prs", "owner_default")
    incomplete = [name for name in required if not _complete(snapshot, name)]
    if incomplete:
        evidence.append(_evidence(
            "incomplete_inventory",
            "absence of collision is unproven because required inventories are incomplete",
            inventories=incomplete,
        ))
        return _result("UNKNOWN_HOLD", evidence, operation_key=operation_key)

    if donor_blobs:
        missing = sorted(set(donor_blobs) - set(owner_blobs))
        if missing:
            evidence.append(_evidence(
                "missing_owner_blob",
                "owner-default blob inventory is marked complete but lacks candidate donor paths",
                paths=missing,
            ))
            return _result("UNKNOWN_HOLD", evidence, operation_key=operation_key)

    evidence.append(_evidence(
        "complete_noncollision",
        "complete inventories contain no explicit source custody, active matching carrier, or path overlap",
    ))
    return _result("SAFE_TO_CLAIM", evidence, operation_key=operation_key)


def _result(verdict: str, evidence: list[dict[str, Any]], *, operation_key: str | None = None) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError("unknown verdict")
    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "operation_key": operation_key,
        "evidence": evidence,
        "safety": {
            "mutates_github": False,
            "mutates_slack": False,
            "writes_claims": False,
            "takes_custody": False,
            "safe_to_claim_requires_complete_absence_inventories": True,
        },
    }


def _write_report(report: dict[str, Any], out: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if out is None:
        sys.stdout.write(text)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        body = text.encode("utf-8")
        view = memoryview(body)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="normalized observation snapshot JSON")
    parser.add_argument("--out", type=Path, help="create-exclusive JSON report path")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    report = classify(payload)
    _write_report(report, args.out)
    return 0 if report["verdict"] in {"SAFE_TO_CLAIM", "ALREADY_INTEGRATED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
