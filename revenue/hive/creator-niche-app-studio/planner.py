from __future__ import annotations

import math
from typing import Any

from core_common import (
    HEX_COLOR_RE,
    TIERS,
    LimitError,
    ValidationError,
    _exact_keys,
    _identifier,
    _integer,
    _text,
)

def validate_workspace(payload: Any) -> dict[str, Any]:
    payload = _exact_keys(
        payload,
        "workspace",
        {"workspace_id", "brand_name", "audience_name", "tagline", "accent_color", "tier"},
        {"workspace_id", "brand_name", "audience_name", "tagline", "accent_color", "tier"},
    )
    tier = _text(payload["tier"], "tier", max_len=20).lower()
    if tier not in TIERS:
        raise ValidationError("tier must be starter or studio")
    accent = _text(payload["accent_color"], "accent_color", max_len=7)
    if not HEX_COLOR_RE.fullmatch(accent):
        raise ValidationError("accent_color must be #RRGGBB")
    return {
        "workspace_id": _identifier(payload["workspace_id"], "workspace_id"),
        "brand_name": _text(payload["brand_name"], "brand_name", max_len=80),
        "audience_name": _text(payload["audience_name"], "audience_name", max_len=120),
        "tagline": _text(payload["tagline"], "tagline", max_len=160),
        "accent_color": accent.lower(),
        "tier": tier,
    }


def validate_item(item: Any, index: int) -> dict[str, Any]:
    item = _exact_keys(
        item,
        f"items[{index}]",
        {
            "item_id",
            "name",
            "mode",
            "unit_label",
            "on_hand_units",
            "reserve_units",
            "units_per_pack",
            "estimated_pack_cost_cents",
            "per_attendee_per_session",
            "shared_target_units",
        },
        {"item_id", "name", "mode", "unit_label", "on_hand_units", "reserve_units", "units_per_pack"},
    )
    mode = _text(item["mode"], f"items[{index}].mode", max_len=40).upper()
    if mode not in {"PER_ATTENDEE_CONSUMABLE", "SHARED_REUSABLE"}:
        raise ValidationError(f"items[{index}].mode is unsupported")
    cost = item.get("estimated_pack_cost_cents")
    if cost is not None:
        cost = _integer(cost, f"items[{index}].estimated_pack_cost_cents", maximum=100_000_000)
    normalized = {
        "item_id": _identifier(item["item_id"], f"items[{index}].item_id"),
        "name": _text(item["name"], f"items[{index}].name", max_len=100),
        "mode": mode,
        "unit_label": _text(item["unit_label"], f"items[{index}].unit_label", max_len=30),
        "on_hand_units": _integer(item["on_hand_units"], f"items[{index}].on_hand_units"),
        "reserve_units": _integer(item["reserve_units"], f"items[{index}].reserve_units"),
        "units_per_pack": _integer(item["units_per_pack"], f"items[{index}].units_per_pack", minimum=1),
        "estimated_pack_cost_cents": cost,
        "per_attendee_per_session": None,
        "shared_target_units": None,
    }
    if mode == "PER_ATTENDEE_CONSUMABLE":
        if "per_attendee_per_session" not in item:
            raise ValidationError(f"items[{index}].per_attendee_per_session is required")
        if item.get("shared_target_units") is not None:
            raise ValidationError(f"items[{index}].shared_target_units must be omitted for consumables")
        normalized["per_attendee_per_session"] = _integer(
            item["per_attendee_per_session"],
            f"items[{index}].per_attendee_per_session",
            minimum=1,
            maximum=10_000,
        )
    else:
        if "shared_target_units" not in item:
            raise ValidationError(f"items[{index}].shared_target_units is required")
        if item.get("per_attendee_per_session") is not None:
            raise ValidationError(f"items[{index}].per_attendee_per_session must be omitted for reusable items")
        normalized["shared_target_units"] = _integer(
            item["shared_target_units"], f"items[{index}].shared_target_units", minimum=1
        )
    return normalized


def validate_plan(payload: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    payload = _exact_keys(
        payload,
        "plan",
        {"plan_id", "title", "rostered_count", "expected_attendees", "sessions", "items"},
        {"plan_id", "title", "rostered_count", "expected_attendees", "sessions", "items"},
    )
    rostered = _integer(payload["rostered_count"], "rostered_count", minimum=1)
    expected = _integer(payload["expected_attendees"], "expected_attendees", minimum=1)
    if expected > rostered:
        raise ValidationError("expected_attendees cannot exceed rostered_count")
    tier = TIERS[workspace["tier"]]
    if expected > tier["max_expected_attendees"]:
        raise LimitError(
            "expected attendees exceed tier limit",
            details={"tier": workspace["tier"], "limit": tier["max_expected_attendees"]},
        )
    if not isinstance(payload["items"], list) or not payload["items"]:
        raise ValidationError("items must be a non-empty array")
    if len(payload["items"]) > tier["max_items"]:
        raise LimitError("item count exceeds tier limit", details={"limit": tier["max_items"]})
    items = [validate_item(item, i) for i, item in enumerate(payload["items"])]
    ids = [item["item_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValidationError("item_id values must be unique")
    return {
        "plan_id": _identifier(payload["plan_id"], "plan_id"),
        "title": _text(payload["title"], "title", max_len=120),
        "rostered_count": rostered,
        "expected_attendees": expected,
        "sessions": _integer(payload["sessions"], "sessions", minimum=1, maximum=365),
        "items": items,
    }


def derive_plan(plan: dict[str, Any]) -> dict[str, Any]:
    derived_items: list[dict[str, Any]] = []
    total_estimated_cents = 0
    known_cost = True
    for item in plan["items"]:
        if item["mode"] == "PER_ATTENDEE_CONSUMABLE":
            operational_required = (
                plan["expected_attendees"] * plan["sessions"] * item["per_attendee_per_session"]
            )
            rostered_reference = plan["rostered_count"] * plan["sessions"] * item["per_attendee_per_session"]
            attendance_sensitive = True
        else:
            operational_required = item["shared_target_units"]
            rostered_reference = item["shared_target_units"]
            attendance_sensitive = False
        target_with_reserve = operational_required + item["reserve_units"]
        units_short = max(0, target_with_reserve - item["on_hand_units"])
        packs_to_acquire = math.ceil(units_short / item["units_per_pack"]) if units_short else 0
        acquired_units = packs_to_acquire * item["units_per_pack"]
        projected_remaining = item["on_hand_units"] + acquired_units - operational_required
        estimated_cost_cents = None
        if item["estimated_pack_cost_cents"] is not None:
            estimated_cost_cents = packs_to_acquire * item["estimated_pack_cost_cents"]
            total_estimated_cents += estimated_cost_cents
        else:
            known_cost = False
        derived_items.append(
            {
                **item,
                "operational_required_units": operational_required,
                "rostered_reference_units": rostered_reference,
                "attendance_delta_units": rostered_reference - operational_required,
                "attendance_sensitive": attendance_sensitive,
                "target_with_reserve_units": target_with_reserve,
                "units_short": units_short,
                "packs_to_acquire": packs_to_acquire,
                "acquired_units": acquired_units,
                "projected_remaining_units": projected_remaining,
                "estimated_acquisition_cost_cents": estimated_cost_cents,
            }
        )
    return {
        **plan,
        "items": derived_items,
        "total_estimated_acquisition_cost_cents": total_estimated_cents if known_cost else None,
        "cost_estimate_complete": known_cost,
        "planning_note": (
            "Expected attendance drives only per-attendee consumables. "
            "Rostered headcount remains a reference; shared/reusable targets are never multiplied by attendance."
        ),
    }
