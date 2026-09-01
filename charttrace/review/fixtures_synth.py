"""Synthetic non-PHI fixtures for ChartTrace Lane D tests."""

from __future__ import annotations

from typing import Any, Dict, List


def _hash(n: int) -> str:
    return f"{n:064x}"


def base_sources() -> List[Dict[str, Any]]:
    return [
        {
            "source_id": "src-001",
            "sha256": _hash(1),
            "pages": 12,
            "filename": "synthetic_note_a.pdf",
            "ocr": {"status": "ok", "confidence": 0.95},
        },
        {
            "source_id": "src-002",
            "sha256": _hash(2),
            "pages": 8,
            "filename": "synthetic_lab_b.pdf",
            "ocr": {"status": "ok", "confidence": 0.91},
        },
    ]


def clean_lead(**overrides: Any) -> Dict[str, Any]:
    lead: Dict[str, Any] = {
        "lead_id": "L-clean-1",
        "title": "Abnormal lab without documented callback in supplied cardiology notes",
        "domain": "communication",
        "band": "primary",
        "evidence_grade": "SUPPORTED",
        "relevance_grade": "MATERIAL_IF_CONFIRMED",
        "cited_observation": "potassium 6.1 flagged critical on 2020-03-01",
        "hypothesis": "Possible closed-loop communication gap worth counsel review",
        "review_question": "What documentation exists for critical-result notification?",
        "citations": [
            {
                "text": "potassium 6.1 flagged critical on 2020-03-01 lab report page 2",
                "page": 2,
                "source_id": "src-002",
            }
        ],
        "counterevidence": [
            "Callback note timed 2020-03-01 14:02 appears in nursing addendum"
        ],
        "alternative_explanations": ["Callback documented in unsupplied phone log"],
        "missing_records": ["Outpatient phone triage log 2020-03-01"],
        "flags": [],
        "grounded": True,
        "jurisdiction": "US-MT",
        "care_year": 2020,
        "authority": {
            "jurisdiction": "US-MT",
            "effective_from_year": 2015,
            "effective_to_year": 2025,
            "citation": "42 CFR 493.1291 (context_only)",
        },
    }
    lead.update(overrides)
    return lead


def weak_grounded_lead(**overrides: Any) -> Dict[str, Any]:
    lead = clean_lead(
        lead_id="L-weak-1",
        band="weak",
        evidence_grade="CLUE",
        relevance_grade="TENUOUS",
        title="Unusual unit notation on single flowsheet row",
        cited_observation="glucose recorded as 180 mgm/dL",
        hypothesis="Possible unit transcription oddity; may be benign",
        citations=[
            {
                "text": "glucose recorded as 180 mgm/dL on flowsheet row 4",
                "page": 4,
                "source_id": "src-001",
            }
        ],
        counterevidence=["Adjacent rows use mg/dL consistently"],
        alternative_explanations=["OCR artifact on unit suffix"],
    )
    lead.update(overrides)
    return lead


def base_packet(**overrides: Any) -> Dict[str, Any]:
    packet: Dict[str, Any] = {
        "case_id": "SYN-CASE-001",
        "sources": base_sources(),
        "discovery": {
            "peer_runs": [
                {"peer_id": "chronology", "inputs": {"case_id": "SYN-CASE-001"}},
                {"peer_id": "communication", "inputs": {"case_id": "SYN-CASE-001"}},
            ]
        },
        "leads": [clean_lead(), weak_grounded_lead()],
        "counterevidence": [],
        "missing_record_requests": [],
        "chronology": [{"date": "2020-03-01", "event": "critical lab flagged"}],
        "citation_index": [{"lead_id": "L-clean-1", "source_id": "src-002", "page": 2}],
        "recipient": {
            "recipient_id": "firm-synth-001",
            "authorization_state": "TRANSFER_AUTHORIZED",
        },
        "release": {
            "named_human_reviewer": "Reviewer-Synthetic-A",
            "state": "HUMAN_RELEASE_REVIEW",
            "auto_released": False,
        },
        "format": {"broken_table": False, "accessibility": {"missing_alt_text": False}},
        "adversarial": {"attacks": []},
        "contains_phi_marker": False,
    }
    packet.update(overrides)
    return packet
