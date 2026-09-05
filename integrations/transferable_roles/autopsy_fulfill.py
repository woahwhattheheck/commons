#!/usr/bin/env python3
"""Role-gated execute wrap into landed Autopsy fulfillment.py.

Gates on tool `autopsy_fulfillment` and calls landed
`revenue/agent_failure_autopsy/fulfillment.py` helpers (`next_business_day`,
`validate_bundle`) — import-only; do not remint fulfillment.py.
"""

from __future__ import annotations

import importlib.util
import json
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
