#!/usr/bin/env python3
"""Role-gated execute wrap into landed Autopsy fulfillment.py.

Gates on tool `autopsy_fulfillment` and calls landed
`revenue/agent_failure_autopsy/fulfillment.py` helpers (`next_business_day`,
`validate_bundle`) — import-only; do not remint fulfillment.py.

`run_deadline` returns delivery_due_at.
`run_sla_status` compares as_of vs due → OPEN|MISSED (WEDGE leftover after #8982).
"""

from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from roles import RoleError

_TOOL_NAME = "autopsy_fulfillment"
_TOOL_ENTRY = "python3 revenue/agent_failure_autopsy/fulfillment.py"
_FULFILL_REL = "revenue/agent_failure_autopsy/fulfillment.py"
_EXAMPLES_REL = "revenue/agent_failure_autopsy/examples"

_ROOT = Path(__file__).resolve().parents[2]


def require_autopsy_fulfillment_tool(role: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse unless the role tools the landed Autopsy fulfillment entry."""
    if not isinstance(role, Mapping):
        raise RoleError("role must be an object")
    for tool in role.get("tools") or []:
        if not isinstance(tool, Mapping):
            continue
        if tool.get("name") != _TOOL_NAME:
            continue
        entry = str(tool.get("entry") or "").strip()
        if entry != _TOOL_ENTRY and not entry.endswith(
            "/agent_failure_autopsy/fulfillment.py"
        ):
            raise RoleError(
                f"{_TOOL_NAME} entry must be {_TOOL_ENTRY}; got {entry!r}"
            )
        return dict(tool)
    raise RoleError(
        f"role lacks tool {_TOOL_NAME} → {_TOOL_ENTRY}; "
        "refusing autopsy fulfill execute (not an Autopsy fulfillment role)"
    )


def _load_fulfillment_module() -> Any:
    path = _ROOT / _FULFILL_REL
    if not path.is_file():
        raise RoleError(f"landed fulfillment missing on disk: {_FULFILL_REL}")
    spec = importlib.util.spec_from_file_location(
        "commons_autopsy_fulfillment_landed", path
    )
    if spec is None or spec.loader is None:
        raise RoleError(f"failed to load {_FULFILL_REL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_aware(stamp: str, label: str) -> datetime:
    text = str(stamp or "").strip()
    if not text:
        raise RoleError(f"{label} must be a nonempty string")
    if not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", text):
        raise RoleError(f"{label} must be an offset-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RoleError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise RoleError(f"{label} must carry a UTC offset")
    return parsed


def run_deadline(
    role: Mapping[str, Any],
    *,
    usable_evidence_at: str,
) -> dict[str, str]:
    """Compute delivery_due_at via landed fulfillment.next_business_day."""
    require_autopsy_fulfillment_tool(role)
    stamp = str(usable_evidence_at or "").strip()
    if not stamp:
        raise RoleError("usable_evidence_at must be a nonempty string")
    mod = _load_fulfillment_module()
    try:
        due = mod.next_business_day(stamp)
    except Exception as exc:  # noqa: BLE001 — map landed errors
        raise RoleError(str(exc)) from exc
    return {
        "usable_evidence_at": stamp,
        "delivery_due_at": due,
    }


def run_sla_status(
    role: Mapping[str, Any],
    *,
    usable_evidence_at: str,
    as_of: str,
) -> dict[str, Any]:
    """OPEN|MISSED Autopsy SLA card vs as_of.

    Reuses run_deadline calendar path; does not remint fulfillment.py.
    within_one_business_day matches Autopsy report rule: as_of <= delivery_due_at.
    """
    base = run_deadline(role, usable_evidence_at=usable_evidence_at)
    as_of_stamp = str(as_of or "").strip()
    as_of_dt = _parse_aware(as_of_stamp, "as_of")
    due_dt = _parse_aware(str(base["delivery_due_at"]), "delivery_due_at")
    within = as_of_dt <= due_dt
    out: dict[str, Any] = {
        **base,
        "as_of": as_of_stamp,
        "within_one_business_day": within,
        "sla_status": "OPEN" if within else "MISSED",
    }
    blob = json.dumps(out)
    for forbidden in ("sk_", "rk_", "whsec_", "prod_", "price_", "plink_"):
        if forbidden in blob:
            raise RoleError(f"sla card leaked forbidden token prefix {forbidden}")
    return out


def run_validate(
    role: Mapping[str, Any],
    *,
    intake: str | Path | None = None,
    report: str | Path | None = None,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate intake+report via landed fulfillment.validate_bundle.

    Defaults to checked-in examples/ (SYNTHETIC_EXAMPLE hermetic path).
    """
    require_autopsy_fulfillment_tool(role)
    examples = _ROOT / _EXAMPLES_REL
    intake_path = Path(intake) if intake is not None else examples / "intake.json"
    report_path = Path(report) if report is not None else examples / "report.json"
    root = Path(evidence_root) if evidence_root is not None else examples
    mod = _load_fulfillment_module()
    try:
        intake_obj = mod.load_json(intake_path)
        report_obj = mod.load_json(report_path)
        result = mod.validate_bundle(intake_obj, report_obj, root)
    except Exception as exc:  # noqa: BLE001 — map landed errors
        raise RoleError(str(exc)) from exc
    if not isinstance(result, dict):
        raise RoleError("fulfillment.validate_bundle must return an object")
    # Never surface secrets from validate output.
    blob = json.dumps(result)
    for forbidden in ("sk_", "rk_", "whsec_", "token", "password"):
        if forbidden in blob.lower() and forbidden in ("sk_", "rk_", "whsec_"):
            raise RoleError(f"validate result leaked forbidden prefix {forbidden}")
    return result
