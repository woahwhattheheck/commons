from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "gate_ledger.json"
TEXT_FILES = sorted(p for p in ROOT.glob("*.md") if p.is_file())

_REQUIRED_HOLD_GATES = {
    "organization_portal_account",
    "pi_eligibility",
    "named_key_team",
    "water_domain_and_cv_qualification",
    "wrf_request_amount",
    "minimum_contribution",
    "budget_workbook_and_narrative",
    "w9",
    "financial_statements",
    "financial_grant_management_capabilities",
    "certifications_assurances",
}

# Public proposal paths must not acquire obvious tax/private-contact values.
_FORBIDDEN_PATTERNS = {
    "ssn_like": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "ein_like": re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"),
    "private_w9_field": re.compile(r"\b(?:taxpayer identification number|TIN)\s*[:=]\s*\d", re.I),
}


class ValidationError(ValueError):
    pass


def _load_ledger() -> dict:
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid gate ledger: {exc}") from exc
    if type(data) is not dict:
        raise ValidationError("gate ledger root must be an object")
    return data


def _validate_ledger(data: dict) -> None:
    expected_top = {
        "schema",
        "operation",
        "deadline",
        "published_max_wrf_usd",
        "minimum_contribution_fraction_of_request",
        "technical_drafting",
        "portal_submission",
        "gates",
        "authority",
    }
    if set(data) != expected_top:
        raise ValidationError("gate ledger top-level schema drift")
    if data["schema"] != "wrf-5417-submission-gates/v1":
        raise ValidationError("unexpected gate-ledger schema")
    if data["operation"] != "WRF-5417-CAMERA-AI-PROPOSAL-ZTHK6P8-20260913":
        raise ValidationError("operation id drift")
    if data["deadline"] != "2026-09-14T15:00:00-06:00":
        raise ValidationError("deadline drift")
    if type(data["published_max_wrf_usd"]) is not int or data["published_max_wrf_usd"] != 300000:
        raise ValidationError("published WRF maximum drift")
    if type(data["minimum_contribution_fraction_of_request"]) is not float or data[
        "minimum_contribution_fraction_of_request"
    ] != 0.33:
        raise ValidationError("minimum contribution fraction drift")
    if data["technical_drafting"] != "GO":
        raise ValidationError("technical drafting state unexpectedly changed")
    if data["portal_submission"] != "HOLD":
        raise ValidationError("portal submission may not be greened by repository editing")

    gates = data["gates"]
    if type(gates) is not list:
        raise ValidationError("gates must be a list")
    by_id = {}
    for gate in gates:
        if type(gate) is not dict or set(gate) != {"id", "state", "required", "reason"}:
            raise ValidationError("malformed gate row")
        if type(gate["id"]) is not str or gate["id"] in by_id:
            raise ValidationError("duplicate/malformed gate id")
        if type(gate["state"]) is not str or type(gate["required"]) is not bool or type(gate["reason"]) is not str:
            raise ValidationError(f"malformed gate values: {gate.get('id')}")
        by_id[gate["id"]] = gate
    missing = _REQUIRED_HOLD_GATES - set(by_id)
    if missing:
        raise ValidationError(f"missing required owner/evidence gates: {sorted(missing)}")
    for gate_id in _REQUIRED_HOLD_GATES:
        state = by_id[gate_id]["state"]
        if state in {"READY", "VERIFIED", "PASS", "SUBMITTED", "COMPLETE"}:
            raise ValidationError(f"repository cannot self-green external gate {gate_id}: {state}")

    authority = data["authority"]
    if type(authority) is not dict or not authority:
        raise ValidationError("authority must be a non-empty object")
    for name, value in authority.items():
        if type(value) is not bool or value is not False:
            raise ValidationError(f"repository may not assert external authority: {name}={value!r}")


def _validate_public_text(paths: Iterable[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for name, pattern in _FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                raise ValidationError(f"possible private identifier ({name}) in {path.name}")


def validate() -> None:
    data = _load_ledger()
    _validate_ledger(data)
    _validate_public_text(TEXT_FILES)


def main() -> int:
    try:
        validate()
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print("WRF_5417_PROPOSAL_GATES_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
