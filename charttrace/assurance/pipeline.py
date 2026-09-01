"""PDF-only adapters shaped like Lane B excerpts and Lane D candidates.

The hidden oracle is used only to *select* seeded leads after pages are
parsed from bytes. Callers that want a system-under-test packet should
pass PDF bytes in, not oracle objects.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from charttrace.assurance.pdf_parse import extract_page_texts, pdf_page_count
from charttrace.assurance.thresholds import ASSURANCE_VERSION
from charttrace.fixtures.oracle import (
    CASE_ID,
    INJECTION_TEXT,
    MODEL_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    SyntheticOracle,
    build_oracle,
)


def parse_document_bytes(content: bytes) -> tuple[str, ...]:
    pages = extract_page_texts(content)
    if pdf_page_count(content) != len(pages):
        raise ValueError("independent parser page count drifted")
    return pages


def peer_excerpts_from_pdfs(
    documents: Iterable[Any],
) -> list[dict[str, Any]]:
    """Lane B RecordExcerpt-shaped rows. No price, firm, or destination keys."""

    excerpts: list[dict[str, Any]] = []
    for document in documents:
        pages = parse_document_bytes(document.content)
        digest = hashlib.sha256(document.content).hexdigest()
        if digest != document.sha256:
            raise ValueError(f"sha mismatch for {document.artifact_id}")
        for index, text in enumerate(pages, start=1):
            excerpts.append(
                {
                    "document_id": document.artifact_id,
                    "page": index,
                    "source_sha256": digest,
                    "text": text,
                    "care_phase": "unspecified",
                    "source_category": "clinical_note",
                }
            )
    return excerpts


def _citation_from_parsed(
    document: Any,
    page_text: str,
    needle: str,
    page: int,
) -> dict[str, Any] | None:
    start = page_text.find(needle)
    if start < 0:
        return None
    return {
        "document_id": document.artifact_id,
        "canonical_id": document.canonical_id,
        "page": page,
        "source_sha256": document.sha256,
        "span_start": start,
        "span_end": start + len(needle),
        "text": page_text[start : start + len(needle)],
    }


def gold_packet_from_pdfs(oracle: SyntheticOracle | None = None):
    """Build a release packet from parsed PDF bytes, not stored page strings."""

    from charttrace.assurance.evaluate import ReviewPacket, SurfacedLead

    oracle = oracle or build_oracle()
    parsed: dict[str, tuple[str, ...]] = {}
    by_canonical: dict[str, Any] = {}
    for document in oracle.documents:
        pages = parse_document_bytes(document.content)
        parsed[document.artifact_id] = pages
        by_canonical.setdefault(document.canonical_id, document)

    def cite(fact_id: str) -> dict[str, Any]:
        fact = oracle.fact_map()[fact_id]
        document = by_canonical[fact.document_id]
        page_text = parsed[document.artifact_id][fact.page - 1]
        citation = _citation_from_parsed(document, page_text, fact.text, fact.page)
        if citation is None:
            raise ValueError(f"parsed PDF missing fact {fact_id}")
        return citation

    surfaced: list[Any] = []
    for lead in oracle.leads:
        if lead.band == "obvious":
            disposition = "PRIMARY"
        elif lead.band == "subtle":
            disposition = "SECONDARY"
        else:
            disposition = "WEAK_APPENDIX"
        citations = tuple(cite(fact_id) for fact_id in lead.supporting_fact_ids)
        counter = tuple(
            oracle.fact_map()[fact_id].text for fact_id in lead.counterevidence_fact_ids
        )
        surfaced.append(
            SurfacedLead(
                lead_id=lead.lead_id,
                disposition=disposition,
                supporting_citations=citations,
                text=lead.title,
                counterevidence=counter,
                alternatives=lead.alternative_explanations,
            )
        )
    for trail in oracle.false_trails:
        citations = tuple(cite(fact_id) for fact_id in trail.supporting_fact_ids)
        surfaced.append(
            SurfacedLead(
                lead_id=trail.trail_id,
                disposition="FALSE_TRAIL",
                supporting_citations=citations,
                text=trail.attractive_error,
                counterevidence=("seeded attractive error is not a supported conclusion",),
                alternatives=("copy-forward, mislabel, or template leftover",),
            )
        )
    injection_seen = any(
        INJECTION_TEXT in page
        for pages in parsed.values()
        for page in pages
    )
    if not injection_seen:
        raise ValueError("injected PDF page was not recovered by the parser")
    return ReviewPacket(
        packet_id="syn-gold-packet-01",
        oracle_version=oracle.version,
        assurance_version=ASSURANCE_VERSION,
        model_version=MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        policy_version=POLICY_VERSION,
        leads=tuple(surfaced),
    )


def review_candidates_from_packet(packet: Any) -> list[dict[str, Any]]:
    """Lane D LeadCandidate-shaped rows derived from a scored packet."""

    rows = []
    for item in packet.leads:
        clauses = [
            {
                "clause_id": f"{item.lead_id}:c{index}",
                "text": item.text,
                "citations": list(item.supporting_citations),
            }
            for index, _ in enumerate(item.supporting_citations, start=1)
        ]
        rows.append(
            {
                "lead_id": item.lead_id,
                "title": item.text,
                "band": "weak" if item.disposition == "WEAK_APPENDIX" else "obvious",
                "clauses": clauses,
                "counterevidence": list(item.counterevidence),
                "alternatives": list(item.alternatives),
                "weak_grounded": item.disposition == "WEAK_APPENDIX" and bool(item.text.strip()),
            }
        )
    return rows


def try_lane_b_d_adapters(excerpts: list[Mapping[str, Any]]) -> dict[str, str]:
    """Use live B/D modules when present; otherwise report adapter-unavailable."""

    status = {"peers": "unavailable", "review": "unavailable"}
    try:
        from charttrace.peers.packet import packet_from_mapping  # type: ignore

        packet_from_mapping(
            {
                "case_id": CASE_ID,
                "jurisdiction": "US-federal-context",
                "care_date_start": "2020-01-01",
                "care_date_end": "2020-12-31",
                "excerpts": excerpts,
            }
        )
        status["peers"] = "bound"
    except Exception:
        status["peers"] = "unavailable"
    try:
        from charttrace.review.models import SourceUniverse  # type: ignore

        SourceUniverse(case_id=CASE_ID, documents={})
        status["review"] = "bound"
    except Exception:
        status["review"] = "unavailable"
    return status
