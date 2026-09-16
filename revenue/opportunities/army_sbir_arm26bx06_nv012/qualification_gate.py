#!/usr/bin/env python3
"""Fail-closed opportunity qualification for Army SBIR ARM26BX06-NV012.

The gate is intentionally unable to submit, contact, register, certify, or sign.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from decision_program import ValidationError, canonical_bytes, digest

SCHEMA = "commons.army-sbir-qualification/v1"
REQUIRED_FACTS = (
    "official_topic_source_bound",
    "controlling_dsip_package_retrieved",
    "sbir_small_business_eligibility_evidenced",
    "ownership_control_requirements_evidenced",
    "sam_uei_requirements_satisfied",
    "dsip_account_ready",
    "topic_deadline_evidenced_from_controlling_package",
    "phase1_demo_one_ready",
    "phase1_demo_two_ready",
    "commercialization_evidence_ready",
    "owner_submission_approval",
)


def _load(path: Path) -> Any:
    def hook(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValidationError(f"duplicate key {k!r}")
            out[k] = v
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook)


def evaluate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or set(raw) != {"schema_version", "topic", "facts", "evidence_refs"}:
        raise ValidationError("qualification document shape mismatch")
    if raw["schema_version"] != SCHEMA or raw["topic"] != "ARM26BX06-NV012":
        raise ValidationError("qualification identity mismatch")
    facts = raw["facts"]
    refs = raw["evidence_refs"]
    if type(facts) is not dict or set(facts) != set(REQUIRED_FACTS):
        raise ValidationError("facts must contain the exact required gate keys")
    if type(refs) is not dict:
        raise ValidationError("evidence_refs must be an object")
    hold, no_go = [], []
    for key in REQUIRED_FACTS:
        value = facts[key]
        if value not in (True, False, None):
            raise ValidationError(f"{key} must be true, false, or null")
        if value is None:
            hold.append(key)
        elif value is False:
            if key in {"sbir_small_business_eligibility_evidenced", "ownership_control_requirements_evidenced"} and refs.get(key) == "EXPLICIT_INELIGIBILITY":
                no_go.append(key)
            else:
                hold.append(key)
        elif not refs.get(key):
            hold.append(key + ":MISSING_EVIDENCE_REF")
    if no_go:
        disposition = "NO_GO"
    elif hold:
        disposition = "HOLD"
    else:
        disposition = "READY_FOR_OWNER_SUBMISSION_DECISION"
    result = {
        "schema_version": "commons.army-sbir-qualification-result/v1",
        "topic": raw["topic"],
        "disposition": disposition,
        "hold_reasons": sorted(hold),
        "no_go_reasons": sorted(no_go),
        "external_contact_authorized": False,
        "portal_mutation_authorized": False,
        "proposal_submission_authorized": False,
        "signature_authorized": False,
        "recognized_revenue": False,
        "input_digest": digest(raw),
    }
    result["result_digest"] = digest(result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qualification", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = _load(args.qualification)
        sys.stdout.buffer.write(canonical_bytes(evaluate(raw)))
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
