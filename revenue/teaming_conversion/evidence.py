from __future__ import annotations

from datetime import datetime
from typing import Any

from .common import _dedupe_or_conflict


def _duplicate_id_blockers(rows: list[dict[str, Any]], id_key: str, label: str) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        row_id = str(row[id_key])
        if row_id in seen:
            duplicates.append(f"{label}_duplicate_id:{row_id}")
        else:
            seen.add(row_id)
    return duplicates


def evaluate_evidence(
    parsed: dict[str, Any], parsed_policy: dict[str, Any], now: datetime
) -> dict[str, Any]:
    blockers: list[str] = []
    opportunity = parsed["opportunity"]
    future_skew = parsed_policy["max_future_skew_seconds"]
    source_checked_at = opportunity["source_checked_at"]

    for rows, id_key, label in (
        (parsed["observations"], "observation_id", "observation"),
        (parsed["assets"], "asset_id", "asset"),
        (parsed["release_records"], "release_id", "release"),
        (parsed["qualification_gates"], "gate_id", "gate"),
        (parsed["commitments"], "commitment_id", "commitment"),
    ):
        blockers.extend(_duplicate_id_blockers(rows, id_key, label))

    if (source_checked_at - now).total_seconds() > future_skew:
        blockers.append("opportunity_source_from_future")
    elif (now - source_checked_at).total_seconds() > parsed_policy["max_source_age_seconds"]:
        blockers.append("opportunity_source_stale")

    observations, conflicts = _dedupe_or_conflict(
        parsed["observations"], id_key="observation_id", extra_unique_key="message_id", label="observation"
    )
    blockers.extend(conflicts)
    for obs in observations:
        if obs["thread_id"] != opportunity["thread_id"]:
            blockers.append(f"cross_thread_observation:{obs['observation_id']}")
        if (obs["received_at"] - now).total_seconds() > future_skew:
            blockers.append(f"future_observation:{obs['observation_id']}")

    obs_by_id = {obs["observation_id"]: obs for obs in observations}
    for obs in observations:
        predecessor_id = obs["supersedes_observation_id"]
        if predecessor_id is None:
            continue
        predecessor = obs_by_id.get(predecessor_id)
        if predecessor is None:
            blockers.append(f"unknown_superseded_observation:{obs['observation_id']}")
        elif predecessor["received_at"] >= obs["received_at"]:
            blockers.append(f"invalid_supersession_chronology:{obs['observation_id']}")

    current: dict[str, Any] | None = None
    if observations:
        ordered = sorted(observations, key=lambda row: (row["received_at"], row["observation_id"]))
        latest_time = ordered[-1]["received_at"]
        latest = [row for row in ordered if row["received_at"] == latest_time]
        if len(latest) != 1:
            blockers.append("ambiguous_latest_observation")
        else:
            current = latest[0]
            if (now - current["received_at"]).total_seconds() > parsed_policy["max_reply_age_seconds"]:
                blockers.append("current_observation_stale")

    def normalize(rows: list[dict[str, Any]], id_key: str, label: str) -> list[dict[str, Any]]:
        unique, row_conflicts = _dedupe_or_conflict(
            rows, id_key=id_key, extra_unique_key=None, label=label
        )
        blockers.extend(row_conflicts)
        return unique

    assets = normalize(parsed["assets"], "asset_id", "asset")
    releases = normalize(parsed["release_records"], "release_id", "release")
    gates = normalize(parsed["qualification_gates"], "gate_id", "gate")
    commitments = normalize(parsed["commitments"], "commitment_id", "commitment")

    for release in releases:
        if (release["approved_at"] - now).total_seconds() > future_skew:
            blockers.append(f"future_release_record:{release['release_id']}")

    return {
        "blockers": sorted(set(blockers)),
        "opportunity": opportunity,
        "current": current,
        "assets": assets,
        "releases": releases,
        "gates": gates,
        "commitments": commitments,
    }
