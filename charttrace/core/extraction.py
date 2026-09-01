"""Deterministic, local-only extraction of page-cited synthetic evidence."""

from __future__ import annotations

import hashlib
import json
import re
import socket
import threading
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from charttrace.schema.v1 import (
    AuthorityReviewStatus,
    Citation,
    DateCertainty,
    EvidenceGrade,
    ExternalAuthority,
    InvestigativeLead,
    RecordFact,
    RelevanceGrade,
    ReviewHistoryEntry,
    TextSpan,
)

from .pdf import PDFPage, read_embedded_pdf_text


EXTRACTION_VERSION = "charttrace.extraction.v1.1"
NETWORK_POLICY = "DENY"
MODEL_VERSION = "LOCAL_RULES_ONLY_NO_EXTERNAL_MODEL"
PROMPT_VERSION = "CT_TAGGED_SYNTHETIC_V1"
POLICY_VERSION = "CHARTTRACE_OWNER_AMENDMENT_V1.1"


class ExtractionError(ValueError):
    pass


class NetworkDeniedError(RuntimeError):
    pass


_NETWORK_PATCH_LOCK = threading.RLock()


def _deny_network(*_: object, **__: object) -> None:
    raise NetworkDeniedError("network access is denied during ChartTrace analysis")


class NetworkDeny(AbstractContextManager["NetworkDeny"]):
    """Process-local guard that makes socket connection attempts fail closed."""

    def __init__(self) -> None:
        self._originals: Dict[str, Any] = {}

    def __enter__(self) -> "NetworkDeny":
        _NETWORK_PATCH_LOCK.acquire()
        self._originals = {
            "connect": socket.socket.connect,
            "connect_ex": socket.socket.connect_ex,
            "create_connection": socket.create_connection,
            "getaddrinfo": socket.getaddrinfo,
        }
        socket.socket.connect = _deny_network  # type: ignore[assignment]
        socket.socket.connect_ex = _deny_network  # type: ignore[assignment]
        socket.create_connection = _deny_network  # type: ignore[assignment]
        socket.getaddrinfo = _deny_network  # type: ignore[assignment]
        return self

    def __exit__(self, *_: object) -> None:
        socket.socket.connect = self._originals["connect"]
        socket.socket.connect_ex = self._originals["connect_ex"]
        socket.create_connection = self._originals["create_connection"]
        socket.getaddrinfo = self._originals["getaddrinfo"]
        self._originals = {}
        _NETWORK_PATCH_LOCK.release()


def network_denied() -> NetworkDeny:
    return NetworkDeny()


@dataclass(frozen=True, slots=True)
class ChronologyEvent:
    fact_id: str
    event_date: Optional[str]
    date_certainty: DateCertainty
    statement: str
    citation: Citation


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    document: str
    source_hash: str
    pages: Tuple[PDFPage, ...]
    facts: Tuple[RecordFact, ...]
    leads: Tuple[InvestigativeLead, ...]
    authorities: Tuple[ExternalAuthority, ...]
    chronology: Tuple[ChronologyEvent, ...]
    ignored_document_instructions: Tuple[str, ...]
    extraction_version: str = EXTRACTION_VERSION
    network_policy: str = NETWORK_POLICY


def _split_escaped(value: str, delimiter: str = "|") -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    escaped = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == delimiter:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    parts.append("".join(current))
    return parts


def _tag_payload(line: str) -> Tuple[str, Dict[str, Any]]:
    fields = _split_escaped(line)
    if len(fields) < 2 or fields[0] != "CT":
        raise ExtractionError("not a ChartTrace tagged line")
    tag = fields[1].strip().upper()
    remaining = fields[2:]
    if len(remaining) == 1 and remaining[0].lstrip().startswith("{"):
        try:
            payload = json.loads(remaining[0])
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"invalid {tag} JSON payload") from exc
        if not isinstance(payload, dict):
            raise ExtractionError(f"{tag} payload must be a JSON object")
        return tag, payload
    if remaining and all("=" in item for item in remaining):
        return tag, {
            key.strip(): value.strip()
            for key, value in (item.split("=", 1) for item in remaining)
        }
    positional: Dict[str, Sequence[str]] = {
        "FACT": (
            "fact_id",
            "event_date",
            "date_certainty",
            "domain",
            "care_phase",
            "statement",
        ),
        "CHRONOLOGY": (
            "fact_id",
            "event_date",
            "date_certainty",
            "domain",
            "care_phase",
            "statement",
        ),
        "LEAD": (
            "lead_id",
            "neutral_title",
            "domain",
            "care_phase",
            "cited_observation",
            "hypothesis",
            "review_question",
            "supporting_facts",
        ),
        "AUTHORITY": (
            "authority_id",
            "authority_type",
            "issuer",
            "jurisdiction",
            "effective_from",
            "effective_to",
            "primary_url",
            "pinpoint",
            "retrieval_date",
            "supported_proposition",
        ),
    }
    names = positional.get(tag)
    if names is None:
        return tag, {"text": "|".join(remaining)}
    if len(remaining) > len(names):
        remaining = list(remaining[: len(names) - 1]) + [
            "|".join(remaining[len(names) - 1 :])
        ]
    return tag, dict(zip(names, remaining))


def _required(payload: Mapping[str, Any], name: str, tag: str) -> str:
    value = payload.get(name)
    if value is None or str(value).strip() == "":
        raise ExtractionError(f"{tag} requires {name}")
    return str(value).strip()


def _tuple_value(value: Any) -> Tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(";") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ExtractionError("list fields must be arrays or semicolon-separated text")


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise ExtractionError(f"invalid boolean: {value}")


def _citation(
    document: str,
    page: PDFPage,
    source_hash: str,
    line: str,
    line_start: int,
) -> Citation:
    return Citation(
        document=document,
        page=page.page_number,
        span_or_bbox=TextSpan(
            start=line_start, end=line_start + len(line), quote=line
        ),
        source_hash=source_hash,
    )


def _fact_from_payload(
    payload: Mapping[str, Any], citation: Citation, tag: str
) -> RecordFact:
    event_date = str(payload.get("event_date") or "").strip() or None
    certainty_default = "EXACT" if event_date else "UNDATED"
    try:
        certainty = DateCertainty(
            str(payload.get("date_certainty") or certainty_default).upper()
        )
    except ValueError as exc:
        raise ExtractionError(f"{tag} has invalid date_certainty") from exc
    return RecordFact(
        fact_id=_required(payload, "fact_id", tag),
        statement=_required(payload, "statement", tag),
        citation=citation,
        domain=str(payload.get("domain") or "chronology"),
        care_phase=str(payload.get("care_phase") or "unspecified"),
        event_date=event_date,
        date_certainty=certainty,
    )


def _authority_from_payload(
    payload: Mapping[str, Any], citation: Citation
) -> ExternalAuthority:
    try:
        review_status = AuthorityReviewStatus(
            str(payload.get("review_status") or "context_only").lower()
        )
    except ValueError as exc:
        raise ExtractionError("AUTHORITY has invalid review_status") from exc
    return ExternalAuthority(
        authority_id=_required(payload, "authority_id", "AUTHORITY"),
        authority_type=_required(payload, "authority_type", "AUTHORITY"),
        issuer=_required(payload, "issuer", "AUTHORITY"),
        jurisdiction=_required(payload, "jurisdiction", "AUTHORITY"),
        effective_from=_required(payload, "effective_from", "AUTHORITY"),
        effective_to=str(payload.get("effective_to") or "").strip() or None,
        care_date_match=_bool_value(payload.get("care_date_match"), default=False),
        primary_url=_required(payload, "primary_url", "AUTHORITY"),
        pinpoint=_required(payload, "pinpoint", "AUTHORITY"),
        retrieval_date=_required(payload, "retrieval_date", "AUTHORITY"),
        supported_proposition=_required(
            payload, "supported_proposition", "AUTHORITY"
        ),
        supersession=str(payload.get("supersession") or "").strip() or None,
        review_status=review_status,
        citation=citation,
    )


def _lead_from_payload(payload: Mapping[str, Any]) -> InvestigativeLead:
    try:
        evidence_grade = EvidenceGrade(
            str(payload.get("evidence_grade") or "CLUE").upper()
        )
        relevance_grade = RelevanceGrade(
            str(payload.get("relevance_grade") or "TENUOUS").upper()
        )
    except ValueError as exc:
        raise ExtractionError("LEAD has invalid evidence or relevance grade") from exc
    history_values = payload.get("review_history") or ()
    history: Tuple[ReviewHistoryEntry, ...]
    if history_values:
        if not isinstance(history_values, (list, tuple)) or not all(
            isinstance(item, ReviewHistoryEntry) for item in history_values
        ):
            raise ExtractionError(
                "tagged extraction accepts typed ReviewHistoryEntry values only"
            )
        history = tuple(history_values)
    else:
        history = ()
    return InvestigativeLead(
        lead_id=_required(payload, "lead_id", "LEAD"),
        neutral_title=_required(payload, "neutral_title", "LEAD"),
        domain=str(payload.get("domain") or "unspecified"),
        care_phase=str(payload.get("care_phase") or "unspecified"),
        cited_observation=_required(payload, "cited_observation", "LEAD"),
        hypothesis=_required(payload, "hypothesis", "LEAD"),
        review_question=_required(payload, "review_question", "LEAD"),
        supporting_facts=_tuple_value(payload.get("supporting_facts")),
        counterevidence=_tuple_value(payload.get("counterevidence")),
        conflicts=_tuple_value(payload.get("conflicts")),
        missing_records=_tuple_value(payload.get("missing_records")),
        alternative_explanations=_tuple_value(
            payload.get("alternative_explanations")
        ),
        source_universe_searched=_tuple_value(
            payload.get("source_universe_searched")
        ),
        external_authorities=_tuple_value(payload.get("external_authorities")),
        jurisdiction_scope=str(payload.get("jurisdiction_scope") or "unspecified"),
        date_scope=str(payload.get("date_scope") or "unspecified"),
        evidence_grade=evidence_grade,
        relevance_grade=relevance_grade,
        clinical_plausibility=str(
            payload.get("clinical_plausibility") or "requires clinician review"
        ),
        temporal_linkage=str(
            payload.get("temporal_linkage") or "requires chronology review"
        ),
        peer_version=str(payload.get("peer_version") or EXTRACTION_VERSION),
        model_version=str(payload.get("model_version") or MODEL_VERSION),
        prompt_version=str(payload.get("prompt_version") or PROMPT_VERSION),
        policy_version=str(payload.get("policy_version") or POLICY_VERSION),
        review_history=history,
    )


_DATE_PREFIX_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


def _chronology_key(event: ChronologyEvent) -> Tuple[int, int, int, int, str]:
    if event.event_date is None:
        return (9999, 99, 99, 4, event.fact_id)
    match = _DATE_PREFIX_RE.match(event.event_date)
    if match is None:
        return (9998, 99, 99, 3, event.fact_id)
    year, month, day = match.groups()
    certainty_order = {
        DateCertainty.EXACT: 0,
        DateCertainty.APPROXIMATE: 1,
        DateCertainty.RANGE: 2,
        DateCertainty.UNDATED: 3,
    }
    return (
        int(year),
        int(month or 1),
        int(day or 1),
        certainty_order[event.date_certainty],
        event.fact_id,
    )


def analyze_pdf(
    source: Union[str, Path, bytes, bytearray],
    *,
    document: str,
    expected_source_hash: Optional[str] = None,
) -> AnalysisResult:
    """Extract known synthetic ``CT|...`` tags under a socket network deny."""

    data = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
    source_hash = hashlib.sha256(data).hexdigest()
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise ExtractionError("HOLD_SOURCE_HASH_MISMATCH")

    facts: List[RecordFact] = []
    leads: List[InvestigativeLead] = []
    authorities: List[ExternalAuthority] = []
    ignored_instructions: List[str] = []

    with network_denied():
        pages = read_embedded_pdf_text(data)
        for page in pages:
            offset = 0
            for raw_line in page.text.splitlines(keepends=True):
                line = raw_line.rstrip("\r\n")
                line_start = offset
                offset += len(raw_line)
                if not line.startswith("CT|"):
                    continue
                tag, payload = _tag_payload(line)
                citation = _citation(
                    document, page, source_hash, line, line_start
                )
                if tag in {"FACT", "CHRONOLOGY"}:
                    facts.append(_fact_from_payload(payload, citation, tag))
                elif tag == "AUTHORITY":
                    authorities.append(_authority_from_payload(payload, citation))
                elif tag == "LEAD":
                    leads.append(_lead_from_payload(payload))
                elif tag in {"INSTRUCTION", "PROMPT", "COMMAND"}:
                    ignored_instructions.append(line)
                else:
                    raise ExtractionError(f"unknown synthetic tag: {tag}")

    fact_ids = {fact.fact_id for fact in facts}
    authority_ids = {authority.authority_id for authority in authorities}
    if len(fact_ids) != len(facts):
        raise ExtractionError("duplicate fact_id")
    if len(authority_ids) != len(authorities):
        raise ExtractionError("duplicate authority_id")
    lead_ids = {lead.lead_id for lead in leads}
    if len(lead_ids) != len(leads):
        raise ExtractionError("duplicate lead_id")
    for lead in leads:
        missing_facts = sorted(set(lead.supporting_facts) - fact_ids)
        missing_authorities = sorted(set(lead.external_authorities) - authority_ids)
        if missing_facts:
            raise ExtractionError(
                f"lead {lead.lead_id} has orphan supporting facts: {missing_facts}"
            )
        if missing_authorities:
            raise ExtractionError(
                f"lead {lead.lead_id} has orphan authorities: {missing_authorities}"
            )

    chronology = tuple(
        sorted(
            (
                ChronologyEvent(
                    fact_id=fact.fact_id,
                    event_date=fact.event_date,
                    date_certainty=fact.date_certainty,
                    statement=fact.statement,
                    citation=fact.citation,
                )
                for fact in facts
            ),
            key=_chronology_key,
        )
    )
    return AnalysisResult(
        document=document,
        source_hash=source_hash,
        pages=tuple(pages),
        facts=tuple(sorted(facts, key=lambda item: item.fact_id)),
        leads=tuple(sorted(leads, key=lambda item: item.lead_id)),
        authorities=tuple(
            sorted(authorities, key=lambda item: item.authority_id)
        ),
        chronology=chronology,
        ignored_document_instructions=tuple(ignored_instructions),
    )
