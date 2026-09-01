"""Assemble ordered export packets from review output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from charttrace.export.language import sanitize_export_text
from charttrace.review.pipeline import PACKET_SECTION_ORDER, ReviewResult


@dataclass
class ExportPacket:
    sections: Dict[str, List[Dict[str, Any]]]
    source_manifest: List[Dict[str, Any]]
    citation_index: List[Dict[str, Any]]
    grounding_versions: Dict[str, str]
    peer_review_release_manifest: Dict[str, Any]
    recipient_id: str
    release_version: str
    schema_version: str = "charttrace.export.v1"
    json_rows: List[Dict[str, Any]] = field(default_factory=list)
    csv_rows: List[List[str]] = field(default_factory=list)
    weak_appendix: List[Dict[str, Any]] = field(default_factory=list)
    reviewed_tables: List[Dict[str, Any]] = field(default_factory=list)
    quarantine_internal: List[Dict[str, Any]] = field(default_factory=list)

    def section_order(self) -> Tuple[str, ...]:
        return PACKET_SECTION_ORDER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipient_id": self.recipient_id,
            "release_version": self.release_version,
            "section_order": list(PACKET_SECTION_ORDER),
            "sections": self.sections,
            "weak_appendix": self.weak_appendix,
            "source_manifest": self.source_manifest,
            "citation_index": self.citation_index,
            "grounding_versions": self.grounding_versions,
            "peer_review_release_manifest": self.peer_review_release_manifest,
            "json_rows": self.json_rows,
            "csv_rows": self.csv_rows,
            "reviewed_tables": self.reviewed_tables,
            "quarantine_internal_count": len(self.quarantine_internal),
        }


def _scrub_item(item: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(item)
    for key in (
        "title",
        "hypothesis",
        "cited_observation",
        "review_question",
        "text",
        "summary",
        "clause",
    ):
        if key in out and isinstance(out[key], str):
            scrubbed, _ = sanitize_export_text(out[key])
            out[key] = scrubbed
    for banned in ("malpractice_score", "case_value", "actionability", "negligence_flag"):
        out.pop(banned, None)
    if out.get("legal_relevance") and not out.get("counsel_filled"):
        out.pop("legal_relevance", None)
    if out.get("legal_viability") and not out.get("counsel_filled"):
        out.pop("legal_viability", None)
    return out


def assemble_export_packet(
    review: ReviewResult,
    *,
    sources: Sequence[Dict[str, Any]],
    recipient_id: str,
    release_version: str,
    citation_index: Optional[Sequence[Dict[str, Any]]] = None,
    peer_manifest: Optional[Dict[str, Any]] = None,
    reviewed_pdf_meta: Optional[Dict[str, Any]] = None,
    quarantine_items: Optional[Sequence[Dict[str, Any]]] = None,
) -> ExportPacket:
    if review.release_blocked:
        raise ValueError("Cannot assemble export packet while release is blocked")
    if not recipient_id:
        raise ValueError("recipient_id required")

    sections: Dict[str, List[Dict[str, Any]]] = {}
    for key in PACKET_SECTION_ORDER:
        scrubbed: List[Dict[str, Any]] = []
        for x in review.packet_sections.get(key, []):
            if isinstance(x, dict):
                scrubbed.append(_scrub_item(dict(x)))
            else:
                scrubbed.append(_scrub_item({"text": str(x)}))
        sections[key] = scrubbed

    weak = list(sections.get("weak_lead_appendix") or [])
    json_rows: List[Dict[str, Any]] = []
    csv_rows: List[List[str]] = [
        ["lead_id", "band", "title", "evidence_grade", "relevance_grade"]
    ]
    for band, key in (
        ("primary", "strongest_grounded_patterns"),
        ("secondary", "secondary_findings"),
        ("weak", "weak_lead_appendix"),
    ):
        for item in sections[key]:
            json_rows.append(
                {
                    "lead_id": item.get("lead_id"),
                    "band": band,
                    "title": item.get("title"),
                    "evidence_grade": item.get("evidence_grade"),
                    "relevance_grade": item.get("relevance_grade"),
                }
            )
            csv_rows.append(
                [
                    str(item.get("lead_id") or ""),
                    band,
                    str(item.get("title") or ""),
                    str(item.get("evidence_grade") or ""),
                    str(item.get("relevance_grade") or ""),
                ]
            )

    source_manifest = []
    for src in sources:
        source_manifest.append(
            {
                "source_id": src.get("source_id") or src.get("id"),
                "sha256": src.get("sha256") or src.get("hash"),
                "pages": src.get("pages"),
                "filename": src.get("filename") or src.get("name"),
            }
        )

    tables: List[Dict[str, Any]] = []
    if reviewed_pdf_meta:
        tables.append({"kind": "pdf_meta", **dict(reviewed_pdf_meta)})
    tables.append({"kind": "lead_table", "rows": json_rows})

    return ExportPacket(
        sections=sections,
        source_manifest=source_manifest,
        citation_index=list(citation_index or []),
        grounding_versions={
            "review": review.grounding_version,
            "export": "charttrace.export.v1",
            "schema": review.schema_version,
        },
        peer_review_release_manifest=dict(peer_manifest or {}),
        recipient_id=recipient_id,
        release_version=release_version,
        json_rows=json_rows,
        csv_rows=csv_rows,
        weak_appendix=weak,
        reviewed_tables=tables,
        quarantine_internal=list(quarantine_items or []),
    )
