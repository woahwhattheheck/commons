"""Byte-deterministic JSON, CSV, and Markdown evidence export primitives."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Mapping

from charttrace.schema.v1 import (
    GLOBAL_SCOPE_STATEMENT,
    SCHEMA_VERSION,
    to_primitive,
)

from .extraction import AnalysisResult


EXPORT_VERSION = "charttrace.exports.v1.1"


def _payload(result: AnalysisResult) -> Dict[str, Any]:
    return {
        "authorities": to_primitive(result.authorities),
        "chronology": to_primitive(result.chronology),
        "document": result.document,
        "export_version": EXPORT_VERSION,
        "extraction_version": result.extraction_version,
        "facts": to_primitive(result.facts),
        "ignored_document_instruction_count": len(
            result.ignored_document_instructions
        ),
        "leads": to_primitive(result.leads),
        "network_policy": result.network_policy,
        "schema_version": SCHEMA_VERSION,
        "scope_statement": GLOBAL_SCOPE_STATEMENT,
        "source_hash": result.source_hash,
        "source_sha256": result.source_hash,
    }


def export_json(result: AnalysisResult) -> str:
    return (
        json.dumps(
            _payload(result),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    )


def export_json_bytes(result: AnalysisResult) -> bytes:
    return export_json(result).encode("ascii")


def _csv_cell(value: Any) -> str:
    primitive = to_primitive(value)
    if isinstance(primitive, (list, dict)):
        return json.dumps(
            primitive, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
    if primitive is None:
        return ""
    return str(primitive)


def export_csv(result: AnalysisResult) -> str:
    """Export all typed objects using one fixed, deterministic wide schema."""

    fieldnames = [
        "object_type",
        "object_id",
        "title_or_statement",
        "domain",
        "care_phase",
        "event_date",
        "evidence_grade",
        "relevance_grade",
        "document",
        "page",
        "span_or_bbox",
        "source_hash",
        "source_sha256",
        "payload_json",
    ]
    rows: List[Dict[str, str]] = []
    for fact in sorted(result.facts, key=lambda item: item.fact_id):
        rows.append(
            {
                "object_type": fact.object_type.value,
                "object_id": fact.fact_id,
                "title_or_statement": fact.statement,
                "domain": fact.domain,
                "care_phase": fact.care_phase,
                "event_date": fact.event_date or "",
                "evidence_grade": "",
                "relevance_grade": "",
                "document": fact.citation.document,
                "page": str(fact.citation.page),
                "span_or_bbox": _csv_cell(fact.citation.span_or_bbox),
                "source_hash": fact.citation.source_hash,
                "source_sha256": fact.citation.source_sha256,
                "payload_json": _csv_cell(fact),
            }
        )
    for authority in sorted(
        result.authorities, key=lambda item: item.authority_id
    ):
        citation = authority.citation
        rows.append(
            {
                "object_type": authority.object_type.value,
                "object_id": authority.authority_id,
                "title_or_statement": authority.supported_proposition,
                "domain": authority.authority_type,
                "care_phase": "",
                "event_date": authority.effective_from,
                "evidence_grade": "",
                "relevance_grade": "",
                "document": citation.document if citation else "",
                "page": str(citation.page) if citation else "",
                "span_or_bbox": _csv_cell(citation.span_or_bbox) if citation else "",
                "source_hash": citation.source_hash if citation else "",
                "source_sha256": citation.source_sha256 if citation else "",
                "payload_json": _csv_cell(authority),
            }
        )
    for lead in sorted(result.leads, key=lambda item: item.lead_id):
        rows.append(
            {
                "object_type": lead.object_type.value,
                "object_id": lead.lead_id,
                "title_or_statement": lead.neutral_title,
                "domain": lead.domain,
                "care_phase": lead.care_phase,
                "event_date": lead.date_scope,
                "evidence_grade": lead.evidence_grade.value,
                "relevance_grade": lead.relevance_grade.value,
                "document": "",
                "page": "",
                "span_or_bbox": "",
                "source_hash": "",
                "source_sha256": "",
                "payload_json": _csv_cell(lead),
            }
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def export_csv_bytes(result: AnalysisResult) -> bytes:
    return export_csv(result).encode("utf-8")


def _markdown_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _citation_text(citation: Any) -> str:
    location = to_primitive(citation.span_or_bbox)
    location_text = json.dumps(location, sort_keys=True, separators=(",", ":"))
    return (
        f"{citation.document}, page {citation.page}, {location_text}, "
        f"source `{citation.source_hash}`"
    )


def export_markdown(result: AnalysisResult) -> str:
    lines = [
        "# ChartTrace investigative evidence",
        "",
        GLOBAL_SCOPE_STATEMENT,
        "",
        f"- Schema: `{SCHEMA_VERSION}`",
        f"- Export: `{EXPORT_VERSION}`",
        f"- Source: `{result.source_hash}`",
        f"- Network policy: `{result.network_policy}`",
        "",
        "## Chronology",
        "",
    ]
    if not result.chronology:
        lines.append("- No tagged chronology facts were extracted.")
    for event in result.chronology:
        date = event.event_date or "undated"
        lines.append(
            f"- **{_markdown_text(date)} [{event.date_certainty.value}]** "
            f"{_markdown_text(event.statement)} "
            f"({_citation_text(event.citation)})"
        )
    lines.extend(["", "## Investigative leads", ""])
    if not result.leads:
        lines.append("- No tagged investigative leads were extracted.")
    for lead in result.leads:
        lines.extend(
            [
                f"### {_markdown_text(lead.neutral_title)} (`{lead.lead_id}`)",
                "",
                f"- Evidence: `{lead.evidence_grade.value}`",
                f"- Relevance: `{lead.relevance_grade.value}`",
                f"- Observation: {_markdown_text(lead.cited_observation)}",
                f"- Hypothesis: {_markdown_text(lead.hypothesis)}",
                f"- Review question: {_markdown_text(lead.review_question)}",
                "- Supporting facts: "
                + ", ".join(f"`{item}`" for item in lead.supporting_facts),
                "- Counterevidence: "
                + (
                    "; ".join(_markdown_text(item) for item in lead.counterevidence)
                    or "none tagged"
                ),
                "- Alternative explanations: "
                + (
                    "; ".join(
                        _markdown_text(item)
                        for item in lead.alternative_explanations
                    )
                    or "none tagged"
                ),
                "",
            ]
        )
    lines.extend(["## External authorities", ""])
    if not result.authorities:
        lines.append("- No tagged external authorities were extracted.")
    for authority in result.authorities:
        lines.append(
            f"- `{authority.authority_id}` {_markdown_text(authority.issuer)} "
            f"({_markdown_text(authority.jurisdiction)}, "
            f"{_markdown_text(authority.effective_from)}): "
            f"{_markdown_text(authority.supported_proposition)} "
            f"[{authority.review_status.value}]"
        )
    lines.extend(
        [
            "",
            f"Ignored document instruction tags: "
            f"{len(result.ignored_document_instructions)}.",
            "",
        ]
    )
    return "\n".join(lines)


def export_markdown_bytes(result: AnalysisResult) -> bytes:
    return export_markdown(result).encode("utf-8")
