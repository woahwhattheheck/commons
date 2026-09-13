#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile connector-captured Slack/GitHub evidence into a pre-claim decision.

The module is deliberately read-only.  It performs no claim, comment, branch,
merge, transplant, or upstream mutation.  Connector/API acquisition remains
outside this process so no Slack/GitHub credentials need to be copied into a
repository process.  The evaluator fails closed when any required evidence
slice is incomplete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

DECISIONS = {
    "SAFE_TO_BIND_BRANCH",
    "OWNED",
    "ALREADY_ABSORBED",
    "NEEDS_MANUAL_DIFF",
}
PATH_STATES = {"MISSING", "EXACT_BASE", "EXACT_HEAD", "DIVERGED"}

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REF_RE = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([1-9][0-9]*)$")
_GH_REF_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(pull|issues)/([1-9][0-9]*)(?:/)?$"
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_HIT_KEYS = {"id", "url", "channel_id", "ts", "kind", "repo", "number", "overlap_paths"}


class PreclaimInputError(ValueError):
    """Raised when request/evidence cannot support a trustworthy decision."""


def _bounded_string(value: Any, field: str, *, max_len: int = 500) -> str:
    if type(value) is not str:
        raise PreclaimInputError(f"{field} must be a string")
    if not value or len(value) > max_len:
        raise PreclaimInputError(f"{field} must be non-empty and <= {max_len} chars")
    if any(ord(ch) < 32 for ch in value):
        raise PreclaimInputError(f"{field} contains control characters")
    return value


def _repo(value: Any, field: str) -> str:
    value = _bounded_string(value, field, max_len=200)
    if not _REPO_RE.fullmatch(value):
        raise PreclaimInputError(f"{field} must be owner/repo")
    return value


def _upstream_ref(value: Any) -> tuple[str, int, str]:
    value = _bounded_string(value, "upstream_pr_or_issue", max_len=300)
    match = _REF_RE.fullmatch(value)
    kind = "unknown"
    if not match:
        url_match = _GH_REF_RE.fullmatch(value)
        if not url_match:
            raise PreclaimInputError(
                "upstream_pr_or_issue must be owner/repo#N or a canonical GitHub pull/issues URL"
            )
        repo, url_kind, number = url_match.groups()
        kind = "pr" if url_kind == "pull" else "issue"
        return repo, int(number), kind
    return match.group(1), int(match.group(2)), kind


def _path(value: Any, field: str) -> str:
    value = _bounded_string(value, field, max_len=500)
    if value.startswith("/") or "\\" in value:
        raise PreclaimInputError(f"{field} must be a repository-relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PreclaimInputError(f"{field} has an unsafe path component")
    return value


def _unique_strings(values: Any, field: str, *, paths: bool = False, max_items: int = 100) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > max_items:
        raise PreclaimInputError(f"{field} must be a list of at most {max_items} items")
    result: list[str] = []
    seen: set[str] = set()
    for idx, raw in enumerate(values):
        value = _path(raw, f"{field}[{idx}]") if paths else _bounded_string(
            raw, f"{field}[{idx}]", max_len=300
        )
        if value in seen:
            raise PreclaimInputError(f"{field} contains duplicate value: {value}")
        seen.add(value)
        result.append(value)
    return result


def _normalize_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise PreclaimInputError("request must be an object")
    allowed = {
        "owner_fork",
        "upstream_pr_or_issue",
        "stable_id",
        "candidate_paths",
        "semantic_phrases",
    }
    extra = set(request) - allowed
    if extra:
        raise PreclaimInputError(f"request has unknown fields: {sorted(extra)}")
    owner_fork = _repo(request.get("owner_fork"), "owner_fork")
    upstream_repo, upstream_number, upstream_kind = _upstream_ref(
        request.get("upstream_pr_or_issue")
    )
    stable_id = request.get("stable_id")
    if stable_id is not None:
        stable_id = _bounded_string(stable_id, "stable_id", max_len=200)
    candidate_paths = _unique_strings(
        request.get("candidate_paths", []), "candidate_paths", paths=True
    )
    semantic_phrases = _unique_strings(
        request.get("semantic_phrases", []), "semantic_phrases", max_items=20
    )
    return {
        "owner_fork": owner_fork,
        "upstream_repo": upstream_repo,
        "upstream_number": upstream_number,
        "upstream_kind": upstream_kind,
        "canonical_upstream_ref": f"{upstream_repo}#{upstream_number}",
        "stable_id": stable_id,
        "candidate_paths": candidate_paths,
        "semantic_phrases": semantic_phrases,
    }


def _sha(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not _SHA_RE.fullmatch(value):
        raise PreclaimInputError(f"{field} must be null or a lowercase 40-hex blob SHA")
    return value


def _hits(
    slice_: Any, field: str, *, expected_query: str
) -> tuple[bool, list[dict[str, Any]]]:
    if not isinstance(slice_, dict):
        raise PreclaimInputError(f"{field} must be an object")
    if set(slice_) != {"complete", "hits", "query"}:
        raise PreclaimInputError(f"{field} must contain exactly complete, hits, and query")
    query = _bounded_string(slice_.get("query"), f"{field}.query", max_len=500)
    if query != expected_query:
        raise PreclaimInputError(
            f"{field}.query does not match the requested evidence scope"
        )
    complete = slice_.get("complete")
    if type(complete) is not bool:
        raise PreclaimInputError(f"{field}.complete must be boolean")
    hits = slice_.get("hits")
    if not isinstance(hits, list) or len(hits) > 200:
        raise PreclaimInputError(f"{field}.hits must be a list of at most 200 items")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, hit in enumerate(hits):
        if not isinstance(hit, dict):
            raise PreclaimInputError(f"{field}.hits[{idx}] must be an object")
        extra = set(hit) - _ALLOWED_HIT_KEYS
        if extra:
            # In particular, refuse raw Slack message bodies.  The receipt is
            # coordination metadata, not a second copy of workspace content.
            raise PreclaimInputError(
                f"{field}.hits[{idx}] has disallowed fields: {sorted(extra)}"
            )
        hit_id = _bounded_string(hit.get("id"), f"{field}.hits[{idx}].id", max_len=300)
        if hit_id in seen:
            continue
        seen.add(hit_id)
        clean: dict[str, Any] = {"id": hit_id}
        for key in ("url", "channel_id", "ts", "kind", "repo"):
            if key in hit and hit[key] is not None:
                clean[key] = _bounded_string(
                    hit[key], f"{field}.hits[{idx}].{key}", max_len=500
                )
        if "number" in hit and hit["number"] is not None:
            number = hit["number"]
            if type(number) is not int or number <= 0:
                raise PreclaimInputError(f"{field}.hits[{idx}].number must be positive int")
            clean["number"] = number
        if "overlap_paths" in hit:
            clean["overlap_paths"] = _unique_strings(
                hit["overlap_paths"],
                f"{field}.hits[{idx}].overlap_paths",
                paths=True,
            )
        normalized.append(clean)
    return complete, normalized


def _named_slices(
    payload: Any,
    field: str,
    expected_names: Iterable[str],
) -> tuple[bool, dict[str, list[dict[str, Any]]]]:
    if not isinstance(payload, dict):
        raise PreclaimInputError(f"{field} must be an object")
    expected = list(expected_names)
    if set(payload) != set(expected):
        raise PreclaimInputError(
            f"{field} keys must exactly match requested values: {expected}"
        )
    complete = True
    hits: dict[str, list[dict[str, Any]]] = {}
    for name in expected:
        item_complete, item_hits = _hits(
            payload[name], f"{field}[{name!r}]", expected_query=name
        )
        complete = complete and item_complete
        hits[name] = item_hits
    return complete, hits


def _classify_path(raw: Any, path: str) -> tuple[bool, dict[str, Any]]:
    if not isinstance(raw, dict) or set(raw) - {
        "complete",
        "owner_default_sha",
        "upstream_base_sha",
        "upstream_head_sha",
    }:
        raise PreclaimInputError(f"github.paths[{path!r}] has invalid fields")
    complete = raw.get("complete")
    if type(complete) is not bool:
        raise PreclaimInputError(f"github.paths[{path!r}].complete must be boolean")
    owner = _sha(raw.get("owner_default_sha"), f"github.paths[{path!r}].owner_default_sha")
    base = _sha(raw.get("upstream_base_sha"), f"github.paths[{path!r}].upstream_base_sha")
    head = _sha(raw.get("upstream_head_sha"), f"github.paths[{path!r}].upstream_head_sha")

    if owner is not None and head is not None and owner == head:
        state = "EXACT_HEAD"
    elif owner is None:
        state = "MISSING"
    elif owner is not None and base is not None and owner == base:
        state = "EXACT_BASE"
    else:
        state = "DIVERGED"
    return complete, {
        "status": state,
        "owner_default_sha": owner,
        "upstream_base_sha": base,
        "upstream_head_sha": head,
        "complete": complete,
    }


def evaluate_preclaim(request: Any, evidence: Any) -> dict[str, Any]:
    """Return a deterministic read-only custody decision from bounded evidence."""
    req = _normalize_request(request)
    if not isinstance(evidence, dict) or set(evidence) != {"slack", "github"}:
        raise PreclaimInputError("evidence must contain exactly slack and github objects")
    slack = evidence["slack"]
    github = evidence["github"]
    if not isinstance(slack, dict):
        raise PreclaimInputError("slack evidence must be an object")
    if not isinstance(github, dict):
        raise PreclaimInputError("github evidence must be an object")

    expected_slack = {"upstream_ref", "candidate_paths", "semantic_phrases"}
    if req["stable_id"] is not None:
        expected_slack.add("stable_id")
    if set(slack) != expected_slack:
        raise PreclaimInputError(
            f"slack evidence keys must exactly match required slices: {sorted(expected_slack)}"
        )

    complete = True
    slack_hits: dict[str, Any] = {}

    upstream_complete, upstream_hits = _hits(
        slack["upstream_ref"],
        "slack.upstream_ref",
        expected_query=req["canonical_upstream_ref"],
    )
    complete = complete and upstream_complete
    slack_hits["upstream_ref"] = upstream_hits

    if req["stable_id"] is not None:
        stable_complete, stable_hits = _hits(
            slack["stable_id"], "slack.stable_id", expected_query=req["stable_id"]
        )
        complete = complete and stable_complete
        slack_hits["stable_id"] = stable_hits
    else:
        slack_hits["stable_id"] = []

    path_complete, path_hits = _named_slices(
        slack["candidate_paths"], "slack.candidate_paths", req["candidate_paths"]
    )
    phrase_complete, phrase_hits = _named_slices(
        slack["semantic_phrases"], "slack.semantic_phrases", req["semantic_phrases"]
    )
    complete = complete and path_complete and phrase_complete
    slack_hits["candidate_paths"] = path_hits
    slack_hits["semantic_phrases"] = phrase_hits

    if set(github) != {"scope", "owner_open_prs", "paths"}:
        raise PreclaimInputError(
            "github evidence must contain scope, owner_open_prs, and paths"
        )
    scope = github["scope"]
    expected_scope = {
        "owner_fork": req["owner_fork"],
        "upstream_ref": req["canonical_upstream_ref"],
    }
    if scope != expected_scope:
        raise PreclaimInputError(
            "github.scope does not match the requested owner fork and upstream ref"
        )
    prs_complete, owner_pr_hits = _hits(
        github["owner_open_prs"],
        "github.owner_open_prs",
        expected_query=f"owner-fork-open-prs:{req['owner_fork']}",
    )
    complete = complete and prs_complete

    raw_paths = github["paths"]
    if not isinstance(raw_paths, dict) or set(raw_paths) != set(req["candidate_paths"]):
        raise PreclaimInputError("github.paths keys must exactly match candidate_paths")
    path_status: dict[str, dict[str, Any]] = {}
    for path in req["candidate_paths"]:
        path_complete_flag, status = _classify_path(raw_paths[path], path)
        complete = complete and path_complete_flag
        path_status[path] = status

    any_slack_hit = (
        bool(slack_hits["stable_id"])
        or bool(slack_hits["upstream_ref"])
        or any(slack_hits["candidate_paths"].values())
        or any(slack_hits["semantic_phrases"].values())
    )
    any_custody_hit = any_slack_hit or bool(owner_pr_hits)
    states = [row["status"] for row in path_status.values()]
    all_head = bool(states) and all(state == "EXACT_HEAD" for state in states)
    any_head = any(state == "EXACT_HEAD" for state in states)
    any_diverged = any(state == "DIVERGED" for state in states)

    reasons: list[str] = []
    if not complete:
        decision = "NEEDS_MANUAL_DIFF"
        reasons.append("EVIDENCE_INCOMPLETE")
    elif all_head:
        # Main already contains the candidate head byte-for-byte.  This is a
        # stronger branch-binding stop than a stale/open PR or Slack claim.
        decision = "ALREADY_ABSORBED"
        reasons.append("ALL_CANDIDATE_PATHS_EXACT_HEAD")
    elif any_custody_hit:
        decision = "OWNED"
        if slack_hits["stable_id"]:
            reasons.append("SLACK_STABLE_ID_HIT")
        if slack_hits["upstream_ref"]:
            reasons.append("SLACK_UPSTREAM_REF_HIT")
        if any(slack_hits["candidate_paths"].values()):
            reasons.append("SLACK_CANDIDATE_PATH_HIT")
        if any(slack_hits["semantic_phrases"].values()):
            reasons.append("SLACK_SEMANTIC_PHRASE_HIT")
        if owner_pr_hits:
            reasons.append("OWNER_FORK_OPEN_PR_HIT")
    elif any_diverged or any_head:
        decision = "NEEDS_MANUAL_DIFF"
        reasons.append(
            "DIVERGED_CANDIDATE_PATH" if any_diverged else "PARTIAL_HEAD_ABSORPTION"
        )
    else:
        decision = "SAFE_TO_BIND_BRANCH"
        reasons.append("NO_CUSTODY_OR_ABSORPTION_CONFLICT")

    if decision not in DECISIONS:
        raise AssertionError("unreachable decision")
    if any(row["status"] not in PATH_STATES for row in path_status.values()):
        raise AssertionError("unreachable path status")

    receipt_core = {
        "schema": "swarm-preclaim-fence/v1",
        "request": req,
        "evidence_complete": complete,
        "slack_hits": slack_hits,
        "owner_fork_open_pr_hits": owner_pr_hits,
        "path_status": path_status,
        "decision": decision,
        "reasons": reasons,
        "mutations_performed": [],
    }
    canonical = json.dumps(
        receipt_core, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return {
        **receipt_core,
        "receipt_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile connector-captured custody evidence into a read-only branch-binding decision."
    )
    parser.add_argument("--request", required=True, help="request JSON path")
    parser.add_argument("--evidence", required=True, help="normalized read-only evidence JSON path")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate_preclaim(_load_json(args.request), _load_json(args.evidence))
    except (OSError, json.JSONDecodeError, PreclaimInputError) as exc:
        print(json.dumps({"schema": "swarm-preclaim-fence/v1", "decision": "NEEDS_MANUAL_DIFF",
                          "reasons": ["INPUT_INVALID"], "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["decision"] == "SAFE_TO_BIND_BRANCH" else 3


if __name__ == "__main__":
    raise SystemExit(main())
