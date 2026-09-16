#!/usr/bin/env python3
"""Emit a deterministic synthetic remediation-scope fixture."""
from __future__ import annotations

import json
import sys


def build_manifest() -> dict:
    return {
        "schema": "security-remediation-scope-v1",
        "scope_id": "SYNTHETIC-REMEDIATION-001",
        "as_of": "2026-09-16T12:00:00Z",
        "currency": "USD",
        "source_packet": {
            "packet_id": "SYNTHETIC-QUESTIONNAIRE-001",
            "sha256": "a" * 64,
            "observed_at": "2026-09-15T12:00:00Z",
        },
        "findings": [
            {
                "id": "F.ACCESS",
                "source_status": "PARTIAL",
                "requirement": "Administrative access should have retained MFA evidence.",
                "source_evidence_ids": ["E.ACCESS"],
                "current_state": "Role-based administrative access evidence is retained; MFA evidence is not retained for the reviewed scope.",
                "gap": "Retained MFA configuration and validation evidence is missing.",
                "remediation": {
                    "deliverable": "Implement owner-approved MFA configuration for the bounded administrative surface and retain configuration plus validation evidence.",
                    "acceptance_test": "Owner-reviewed synthetic and staging checks show the bounded administrative paths require a second factor and the retained evidence bytes reproduce the result.",
                    "dependencies": ["Owner supplies approved identity-provider configuration", "Staging administrative surface is available"],
                    "change_control_trigger": "Any additional identity provider, production rollout, or new administrative surface is separately scoped.",
                    "owner_proposed_price_cents": 750000,
                },
            },
            {
                "id": "F.BACKUP",
                "source_status": "HOLD_STALE_EVIDENCE",
                "requirement": "A current restore exercise should be evidenced for the bounded service.",
                "source_evidence_ids": ["E.BACKUP"],
                "current_state": "A prior restore exercise exists but is outside the declared evidence-currentness window.",
                "gap": "No current retained restore exercise evidence is available.",
                "remediation": {
                    "deliverable": "Run one owner-approved non-production restore exercise for the bounded service and retain the procedure, timestamps, result, and artifact digests.",
                    "acceptance_test": "The owner can reproduce the retained non-production restore procedure and verify the resulting artifact digests against the delivery packet.",
                    "dependencies": ["Owner provides approved non-production backup set", "Owner defines recovery target for the exercise"],
                    "change_control_trigger": "Production disaster-recovery execution, new backup products, or broader recovery objectives require a separate change order.",
                    "owner_proposed_price_cents": 1000000,
                },
            },
            {
                "id": "F.LOGGING",
                "source_status": "SUPPORTED",
                "requirement": "Privileged administrative actions should produce retained audit events.",
                "source_evidence_ids": ["E.LOGGING"],
                "current_state": "Current retained evidence supports structured privileged-action audit events for the reviewed scope.",
                "gap": "No remediation gap is asserted.",
                "remediation": None,
            },
        ],
    }


def fixture_bytes() -> bytes:
    return (json.dumps(build_manifest(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


if __name__ == "__main__":
    sys.stdout.buffer.write(fixture_bytes())
