from __future__ import annotations

import json

from .engine import REQUIRED_GATES, evaluate

AS_OF = "2026-09-14T03:15:00Z"


def fixture() -> dict:
    packet = {
        "schema": "commons.mmsd-ai-governance/v1",
        "opportunity_id": "MMSD-COMPREHENSIVE-AI-POLICY-2026",
        "buyer": "Madison Metropolitan Sewerage District",
        "sources": [
            {
                "source_id": "buyer-page-cache-20260911",
                "doc_kind": "BUYER_PAGE",
                "generation": "2026-09-11",
                "authority": "BUYER_PAGE_CACHE",
                "source_ref": "madsewer.org:contracting-center/comprehensive-artificial-intelligence-ai-use-and-governance-policy-request-for-proposal",
                "content_sha256": None,
                "captured_at": "2026-09-14T02:55:00Z",
                "current": False,
                "fetch_state": "INDEXED_ONLY",
                "supersedes": None,
            },
            {
                "source_id": "buyer-page-probe-20260914",
                "doc_kind": "BUYER_PAGE",
                "generation": "2026-09-14",
                "authority": "OFFICIAL_BUYER_PAGE",
                "source_ref": "madsewer.org:contracting-center/comprehensive-artificial-intelligence-ai-use-and-governance-policy-request-for-proposal",
                "content_sha256": None,
                "captured_at": "2026-09-14T03:00:00Z",
                "current": True,
                "fetch_state": "NOT_FOUND",
                "supersedes": "buyer-page-cache-20260911",
            },
            {
                "source_id": "contracting-center-live-20260914",
                "doc_kind": "BUYER_PAGE",
                "generation": "2026-09-14",
                "authority": "OFFICIAL_BUYER_PAGE",
                "source_ref": "madsewer.org:contracting-center",
                "content_sha256": None,
                "captured_at": "2026-09-14T03:12:00Z",
                "current": True,
                "fetch_state": "AVAILABLE",
                "supersedes": None,
            },
            {
                "source_id": "publicbidsearch-index-20260914",
                "doc_kind": "RFP",
                "generation": "2026-09-14",
                "authority": "SECONDARY_INDEX",
                "source_ref": "publicbidsearch.com:madison-metropolitan-sewerage-district-ai-governance",
                "content_sha256": None,
                "captured_at": "2026-09-14T03:01:00Z",
                "current": True,
                "fetch_state": "INDEXED_ONLY",
                "supersedes": None,
            },
        ],
        "source_set_complete": False,
        "addenda_checked": False,
        "qa_checked": False,
        "deadlines": {
            "questions_due": "2026-09-28T21:00:00Z",
            "proposal_due": "2026-10-16T21:00:00Z",
            "proposal_due_source_id": "buyer-page-cache-20260911",
        },
        "gates": [],
        "partner": {
            "candidate_id": None,
            "confirmed": False,
            "commercial_workshare_agreed": False,
            "evidence_refs": [],
        },
        "outreach": {"state": "NOT_CONTACTED", "provider_receipt_id": None},
        "budget": {
            "math_valid": False,
            "owner_approved": False,
            "pricing_structure_known": False,
            "total_cents": 0,
        },
        "owner_release": False,
    }
    for route in ("PRIME", "TEAM"):
        for gate_id in REQUIRED_GATES:
            packet["gates"].append(
                {
                    "gate_id": gate_id,
                    "route": route,
                    "state": "HOLD" if route == "PRIME" else "PARTNER_CURABLE",
                    "evidence_refs": [],
                }
            )
    return packet


def main() -> int:
    output = evaluate(fixture(), AS_OF)
    assert output["disposition"] == "SOURCE_REFRESH_REQUIRED"
    assert not output["source_posture"]["official_submission_bytes_complete"]
    assert "buyer-page-probe-20260914" in output["source_posture"]["current_unavailable_source_ids"]
    assert output["outreach"]["state"] == "NOT_CONTACTED"
    assert not any(output["authority"].values())
    print(
        json.dumps(
            {
                "disposition": output["disposition"],
                "proposal_due": output["deadlines"]["proposal_due"],
                "proposal_due_authoritative": output["deadlines"]["proposal_due_authoritative"],
                "unavailable": output["source_posture"]["current_unavailable_source_ids"],
                "receipt_sha256": output["receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
