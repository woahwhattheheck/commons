#!/usr/bin/env python3
"""Fail-closed procurement readiness gate.

This never submits a proposal. It only declares READY when every user-supplied factual
and authorization gate is explicitly true and no expired-inquiry exception is needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TRUE = (
    "latest_official_rfp_and_addenda_rechecked",
    "proposal_entity_and_signatory_confirmed",
    "firm_contact_information_verified",
    "key_personnel_and_qualifications_verified",
    "previous_dashboard_examples_verified",
    "final_scope_and_platform_approved",
    "five_year_cost_and_hourly_rates_approved",
    "schedule_commitments_approved",
    "accessibility_compliance_plan_verified",
    "hosting_and_handover_position_approved",
    "confidentiality_marking_reviewed",
    "submission_pdf_rendered_and_checked",
    "submission_recipient_and_subject_reverified",
    "receipt_confirmation_plan_owned",
)


def evaluate(doc: dict) -> tuple[bool, list[str]]:
    missing = [name for name in REQUIRED_TRUE if doc.get(name) is not True]
    if doc.get("p37_or_rfp_exception_needed") is True:
        missing.append(
            "p37_or_rfp_exception_needed=true: inquiry period ended 2026-09-04; do not assume an unraised exception is available"
        )
    if doc.get("buyer_contact_outside_authorized_poc_attempted") is True:
        missing.append("buyer_contact_outside_authorized_poc_attempted=true: communication restriction risk")
    return (not missing, missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    doc = json.loads(args.state.read_text(encoding="utf-8"))
    ok, missing = evaluate(doc)
    if ok:
        print("READY: all explicit procurement gates passed; this is not a submission receipt")
        return 0
    print("BLOCKED")
    for item in missing:
        print(f"- {item}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
