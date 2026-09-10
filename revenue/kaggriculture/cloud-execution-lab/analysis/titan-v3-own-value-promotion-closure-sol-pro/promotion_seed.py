# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from promotion_core import *

SPEND_KEYS = {
    "operation",
    "hypothesis",
    "head",
    "source_pr",
    "run_id",
    "run_attempt",
    "event_name",
    "policy_sha256",
    "seeds",
    "status",
    "reuse_forbidden",
}


def validate_spend_entry(entry: Mapping[str, Any], label: str = "spend entry") -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        raise PromotionClosureError(f"{label} must be an object")
    require_keys(entry, SPEND_KEYS, label)
    operation = nonempty_string(entry["operation"], f"{label}.operation")
    hypothesis = nonempty_string(entry["hypothesis"], f"{label}.hypothesis")
    head = sha40(entry["head"], f"{label}.head")
    source_pr = true_int(entry["source_pr"], f"{label}.source_pr", minimum=1)
    run_id = true_int(entry["run_id"], f"{label}.run_id", minimum=1)
    run_attempt = true_int(entry["run_attempt"], f"{label}.run_attempt", minimum=1)
    if run_attempt != 1:
        raise PromotionClosureError(f"{label} is not immutable attempt 1")
    event_name = nonempty_string(entry["event_name"], f"{label}.event_name")
    if event_name != "pull_request":
        raise PromotionClosureError(f"{label} must originate from pull_request")
    policy_sha = sha64(entry["policy_sha256"], f"{label}.policy_sha256")
    raw_seeds = entry["seeds"]
    if not isinstance(raw_seeds, list) or not raw_seeds:
        raise PromotionClosureError(f"{label}.seeds must be a nonempty list")
    seeds = [true_int(seed, f"{label}.seed", minimum=0) for seed in raw_seeds]
    if len(seeds) != len(set(seeds)):
        raise PromotionClosureError(f"{label}.seeds contains duplicates")
    status = nonempty_string(entry["status"], f"{label}.status")
    if status not in {"reserved", "spent"}:
        raise PromotionClosureError(f"{label}.status must be reserved or spent")
    if entry["reuse_forbidden"] is not True:
        raise PromotionClosureError(f"{label}.reuse_forbidden must be true")
    return {
        "operation": operation,
        "hypothesis": hypothesis,
        "head": head,
        "source_pr": source_pr,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "event_name": event_name,
        "policy_sha256": policy_sha,
        "seeds": seeds,
        "status": status,
        "reuse_forbidden": True,
    }


def validate_seed_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(ledger, Mapping):
        raise PromotionClosureError("seed ledger must be an object")
    require_keys(ledger, {"schema_version", "entries"}, "seed ledger")
    if ledger["schema_version"] != LEDGER_SCHEMA:
        raise PromotionClosureError("unsupported seed ledger schema")
    entries = ledger["entries"]
    if not isinstance(entries, list):
        raise PromotionClosureError("seed ledger entries must be a list")
    normalized: list[dict[str, Any]] = []
    operations: set[str] = set()
    run_ids: set[int] = set()
    used_seeds: dict[int, str] = {}
    for index, raw in enumerate(entries):
        entry = validate_spend_entry(raw, f"seed ledger entry {index}")
        if entry["operation"] in operations:
            raise PromotionClosureError("seed ledger repeats an operation")
        if entry["run_id"] in run_ids:
            raise PromotionClosureError("seed ledger repeats a run id")
        for seed in entry["seeds"]:
            if seed in used_seeds:
                raise PromotionClosureError(
                    f"seed {seed} reused by {used_seeds[seed]!r} and {entry['operation']!r}"
                )
            used_seeds[seed] = entry["operation"]
        operations.add(entry["operation"])
        run_ids.add(entry["run_id"])
        normalized.append(entry)
    return {"schema_version": LEDGER_SCHEMA, "entries": normalized}


def validate_append_only(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    before = validate_seed_ledger(previous)
    after = validate_seed_ledger(current)
    old_entries = before["entries"]
    new_entries = after["entries"]
    if len(new_entries) != len(old_entries) + 1:
        raise PromotionClosureError("append-only update must add exactly one entry")
    if new_entries[: len(old_entries)] != old_entries:
        raise PromotionClosureError("append-only update changed prior seed custody")
    return after


def assert_fresh_spend(ledger: Mapping[str, Any], raw_entry: Mapping[str, Any]) -> dict[str, Any]:
    prior = validate_seed_ledger(ledger)
    entry = validate_spend_entry(raw_entry)
    for old in prior["entries"]:
        if old["operation"] == entry["operation"]:
            raise PromotionClosureError("operation was already spent or reserved")
        overlap = sorted(set(old["seeds"]) & set(entry["seeds"]))
        if overlap:
            raise PromotionClosureError(
                f"future spend reuses prior seeds from {old['operation']}: {overlap}"
            )
    return entry


def validate_run_environment(env: Mapping[str, str], *, expected_head: str) -> dict[str, Any]:
    expected_head = sha40(expected_head, "expected head")
    event_name = env.get("GITHUB_EVENT_NAME")
    if event_name != "pull_request":
        raise PromotionClosureError("game workflow must be pull_request-only")
    if env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise PromotionClosureError("game workflow must be immutable run attempt 1")
    actual_head = env.get("CHECKED_OUT_HEAD")
    if actual_head != expected_head:
        raise PromotionClosureError(
            f"checked-out game head mismatch: expected {expected_head}, got {actual_head!r}"
        )
    run_id_text = env.get("GITHUB_RUN_ID", "")
    if not run_id_text.isdigit() or int(run_id_text) <= 0:
        raise PromotionClosureError("GITHUB_RUN_ID must be a positive integer")
    return {
        "event_name": event_name,
        "run_attempt": 1,
        "head": expected_head,
        "run_id": int(run_id_text),
    }


