from __future__ import annotations

from datetime import datetime
from typing import Any

from .common import digest_object


def asset_projection_sha256(asset: dict[str, Any]) -> str:
    return digest_object({
        "asset_id": asset["asset_id"],
        "title": asset["title"],
        "version": asset["version"],
        "sha256": asset["sha256"],
        "release_class": asset["release_class"],
        "safe_snippets": list(asset["safe_snippets"]),
    })


def asset_policy_matches(asset: dict[str, Any], rule: dict[str, Any]) -> bool:
    return (
        rule["asset_version"] == asset["version"]
        and rule["asset_sha256"] == asset["sha256"]
        and rule["release_class"] == asset["release_class"]
        and rule["projection_sha256"] == asset_projection_sha256(asset)
    )


def _project(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": asset["asset_id"],
        "title": asset["title"],
        "version": asset["version"],
        "sha256": asset["sha256"],
        "release_class": asset["release_class"],
        "safe_snippets": list(asset["safe_snippets"]),
    }


def _has_owner_release(
    asset: dict[str, Any], releases: list[dict[str, Any]], now: datetime, future_skew: int
) -> bool:
    return any(
        row["asset_id"] == asset["asset_id"]
        and row["asset_version"] == asset["version"]
        and row["asset_sha256"] == asset["sha256"]
        and (row["approved_at"] - now).total_seconds() <= future_skew
        for row in releases
    )


def evaluate_assets(
    parsed: dict[str, Any],
    parsed_policy: dict[str, Any],
    assets: list[dict[str, Any]],
    releases: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    blockers: list[str] = []
    asset_blockers: list[str] = []
    safe_assets: list[dict[str, Any]] = []
    future_skew = parsed_policy["max_future_skew_seconds"]
    asset_by_id = {row["asset_id"]: row for row in assets}
    rule_by_id = {row["asset_id"]: row for row in parsed_policy["asset_rules"]}

    for asset in assets:
        rule = rule_by_id.get(asset["asset_id"])
        if rule is None:
            if asset["release_class"] != "INTERNAL_ONLY":
                blockers.append(f"asset_release_policy_missing:{asset['asset_id']}")
            continue
        if not asset_policy_matches(asset, rule):
            blockers.append(f"asset_release_policy_mismatch:{asset['asset_id']}")

    required: list[str] = []
    seen: set[str] = set()
    for asset in assets:
        if asset["required_for_followup"] and asset["asset_id"] not in seen:
            seen.add(asset["asset_id"])
            required.append(asset["asset_id"])
    for asset_id in parsed_policy["required_asset_ids"] + parsed["requested_asset_ids"]:
        if asset_id not in seen:
            seen.add(asset_id)
            required.append(asset_id)

    for asset_id in sorted(required):
        asset = asset_by_id.get(asset_id)
        if asset is None:
            asset_blockers.append(f"required_asset_missing:{asset_id}")
            continue
        rule = rule_by_id.get(asset_id)
        if rule is None:
            blockers.append(f"required_asset_release_policy_missing:{asset_id}")
            continue
        if not asset_policy_matches(asset, rule):
            continue
        if asset["prep_state"] != "READY":
            asset_blockers.append(f"required_asset_not_ready:{asset_id}")
            continue
        if asset["release_class"] == "INTERNAL_ONLY":
            asset_blockers.append(f"required_asset_internal_only:{asset_id}")
            continue
        if asset["release_class"] == "OWNER_APPROVAL_REQUIRED" and not _has_owner_release(
            asset, releases, now, future_skew
        ):
            asset_blockers.append(f"required_asset_owner_release_missing:{asset_id}")
            continue
        safe_assets.append(_project(asset))

    projected = {row["asset_id"] for row in safe_assets}
    for asset in sorted(assets, key=lambda row: row["asset_id"]):
        if asset["asset_id"] in projected or asset["prep_state"] != "READY":
            continue
        rule = rule_by_id.get(asset["asset_id"])
        if rule is None or not asset_policy_matches(asset, rule):
            continue
        if asset["release_class"] in {"PROSPECT_SAFE_SUMMARY", "PROSPECT_SAFE_PUBLIC_REFERENCE"}:
            safe_assets.append(_project(asset))
        elif asset["release_class"] == "OWNER_APPROVAL_REQUIRED" and _has_owner_release(
            asset, releases, now, future_skew
        ):
            safe_assets.append(_project(asset))

    return {
        "blockers": sorted(set(blockers)),
        "asset_blockers": sorted(set(asset_blockers)),
        "safe_assets": sorted(safe_assets, key=lambda row: row["asset_id"]),
    }
