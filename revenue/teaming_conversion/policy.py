from __future__ import annotations

from typing import Any

from .common import (
    RELEASE_CLASSES, ControlError, _reject_unknown, _require_dict, _require_enum,
    _require_list, _require_ref, _require_sha256,
)
from .parse import _parse_policy


def _parse_asset_rule(raw: Any, index: int) -> dict[str, Any]:
    label = f"policy.asset_rules[{index}]"
    obj = _require_dict(raw, label)
    allowed = {"asset_id", "asset_version", "asset_sha256", "release_class", "projection_sha256"}
    _reject_unknown(obj, allowed, label)
    return {
        "asset_id": _require_ref(obj.get("asset_id"), f"{label}.asset_id"),
        "asset_version": _require_ref(obj.get("asset_version"), f"{label}.asset_version"),
        "asset_sha256": _require_sha256(obj.get("asset_sha256"), f"{label}.asset_sha256"),
        "release_class": _require_enum(obj.get("release_class"), f"{label}.release_class", RELEASE_CLASSES),
        "projection_sha256": _require_sha256(obj.get("projection_sha256"), f"{label}.projection_sha256"),
    }


def parse_policy_with_asset_rules(raw: dict[str, Any]) -> dict[str, Any]:
    obj = _require_dict(raw, "policy")
    allowed = {
        "schema_version", "max_reply_age_seconds", "max_source_age_seconds",
        "max_future_skew_seconds", "required_asset_ids", "required_clear_gate_ids", "asset_rules",
    }
    _reject_unknown(obj, allowed, "policy")
    rules = [
        _parse_asset_rule(value, index)
        for index, value in enumerate(_require_list(obj.get("asset_rules", []), "policy.asset_rules"))
    ]
    seen: set[str] = set()
    for rule in rules:
        if rule["asset_id"] in seen:
            raise ControlError(f"policy.asset_rules contains duplicate asset_id {rule['asset_id']!r}")
        seen.add(rule["asset_id"])
    base = dict(obj)
    base.pop("asset_rules", None)
    parsed = _parse_policy(base)
    parsed["asset_rules"] = rules
    return parsed
