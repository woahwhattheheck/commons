"""Fail-closed packet, citation, and worker-output validation (Lane B)."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from charttrace.peers.contracts import (
    ALLOWED_LEAD_KEYS,
    EvidenceGrade,
    FORBIDDEN_PEER_INPUT_KEYS,
    REQUIRED_LEAD_FIELDS,
    RelevanceGrade,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NAMESPACED_ID_RE = re.compile(r"^[a-z][a-z0-9_]*[-:][a-z0-9][a-z0-9._:-]{0,120}$")
NAME_LIKE_ID_RE = re.compile(r"[A-Z][a-z]+[._-][A-Z][a-z]+")
SSN_LIKE_ID_RE = re.compile(r"\d{3}[-_.]\d{2}[-_.]\d{4}")
PHI_TOKEN_RE = re.compile(
    r"(?i)(\b(mrn|ssn|dob|patient|phi)\b|\d{3}-\d{2}-\d{4}|[A-Z][a-z]+\s+[A-Z][a-z]+)"
)
LONG_DIGIT_RE = re.compile(r"\d{8,}")
COMMERCIAL_VALUE_RE = re.compile(
    r"(?i)\b("
    r"destination[_-]?firm|affiliate[_-]?identity|packet[_-]?price|"
    r"compensation|routing[_-]?score|review[_-]?fee|firm_id|"
    r"price"
    r")\b\s*[:=]\s*\S+"
)

ALLOWED_PACKET_KEYS = frozenset(
    {
        "case_id",
        "jurisdiction",
        "care_date_start",
        "care_date_end",
        "excerpts",
        "known_facts",
        "source_universe",
        "grounding_pack_ids",
        "sealed_peer_results",
    }
)
ALLOWED_EXCERPT_KEYS = frozenset(
    {
        "document_id",
        "page",
        "source_sha256",
        "text",
        "care_phase",
        "source_category",
    }
)

COMMERCIAL_STEMS = frozenset(
    {
        "price",
        "firm",
        "affiliate",
        "stripe",
        "payment",
        "payout",
        "compensation",
        "routing",
        "recovery",
        "contingency",
        "destination",
        "reviewfee",
        "casevalue",
        "damagesvalue",
        "successprobability",
        "packetprice",
    }
)


def parse_iso_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def assert_synthetic_id(value: Any, field_name: str, *, packet_id: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a namespaced synthetic identifier")
    if " " in value or PHI_TOKEN_RE.search(value) or NAME_LIKE_ID_RE.search(value) or SSN_LIKE_ID_RE.search(value):
        raise ValueError(f"{field_name} rejects names, MRNs, and PHI-like tokens")
    if packet_id and LONG_DIGIT_RE.search(value):
        raise ValueError(f"{field_name} rejects names, MRNs, and PHI-like tokens")
    if not NAMESPACED_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a namespaced synthetic identifier")
    return value


def assert_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be an exact SHA-256 hex digest")
    return value


def assert_positive_page(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive page number")
    return value


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(key).lower())


def key_is_commercial(key: str) -> bool:
    raw = str(key)
    lowered = raw.lower().replace("-", "_")
    if lowered in FORBIDDEN_PEER_INPUT_KEYS:
        return True
    compact = _normalized_key(raw)
    if any(stem in compact for stem in COMMERCIAL_STEMS):
        return True
    for part in lowered.split("_"):
        if part in FORBIDDEN_PEER_INPUT_KEYS or part in COMMERCIAL_STEMS:
            return True
    return False


def detect_commercial_aliases(payload: Any, path: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(payload, Mapping):
        for k, v in payload.items():
            here = f"{path}.{k}" if path else str(k)
            if key_is_commercial(str(k)):
                found.append(here)
            found.extend(detect_commercial_aliases(v, here))
    elif isinstance(payload, (list, tuple)):
        for i, v in enumerate(payload):
            found.extend(detect_commercial_aliases(v, f"{path}[{i}]"))
    return found


def detect_commercial_values(payload: Any, path: str = "") -> List[str]:
    """Reject commercial semantics in allowlisted string values (not excerpt text)."""
    found: List[str] = []
    if isinstance(payload, Mapping):
        for k, v in payload.items():
            here = f"{path}.{k}" if path else str(k)
            if str(k) == "text" and (path == "excerpts" or path.startswith("excerpts[")):
                continue
            found.extend(detect_commercial_values(v, here))
    elif isinstance(payload, (list, tuple)):
        for i, v in enumerate(payload):
            found.extend(detect_commercial_values(v, f"{path}[{i}]"))
    elif isinstance(payload, str) and COMMERCIAL_VALUE_RE.search(payload):
        found.append(path or "value")
    return found


def assert_packet_allowlist(payload: Mapping[str, Any]) -> None:
    unknown = sorted(set(payload.keys()) - ALLOWED_PACKET_KEYS)
    if unknown:
        raise ValueError(f"unknown packet metadata rejected: {unknown}")
    commercial = detect_commercial_aliases(payload)
    if commercial:
        raise ValueError(f"commercial/routing aliases rejected: {commercial}")
    commercial_values = detect_commercial_values(payload)
    if commercial_values:
        raise ValueError(f"commercial/routing values rejected: {commercial_values}")
    for ex in payload.get("excerpts", []):
        if not isinstance(ex, Mapping):
            raise ValueError("excerpt must be a mapping")
        extra = sorted(set(ex.keys()) - ALLOWED_EXCERPT_KEYS)
        if extra:
            raise ValueError(f"unknown excerpt metadata rejected: {extra}")


def assert_excerpt_contract(excerpt: Mapping[str, Any]) -> None:
    assert_synthetic_id(excerpt.get("document_id"), "document_id", packet_id=True)
    assert_positive_page(excerpt.get("page"), "page")
    assert_sha256(excerpt.get("source_sha256"), "source_sha256")
    text = excerpt.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("excerpt text is required")


def assert_citation_shape(citation: Mapping[str, Any]) -> None:
    if not isinstance(citation, Mapping):
        raise ValueError("citation must be a mapping")
    required = (
        "document_id",
        "page",
        "source_sha256",
        "span_start",
        "span_end",
        "quote",
    )
    missing = [k for k in required if k not in citation]
    if missing:
        raise ValueError(f"citation missing fields: {missing}")
    extra = sorted(set(citation.keys()) - set(required))
    if extra:
        raise ValueError(f"citation unknown fields: {extra}")
    assert_synthetic_id(citation["document_id"], "citation.document_id", packet_id=True)
    assert_positive_page(citation["page"], "citation.page")
    assert_sha256(citation["source_sha256"], "citation.source_sha256")
    start = citation["span_start"]
    end = citation["span_end"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
        raise ValueError("citation span must be a positive half-open range")
    quote = citation["quote"]
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("citation quote is required")
    if len(quote) != end - start:
        raise ValueError("citation quote length must match span")


def resolve_citation_against_excerpts(
    citation: Mapping[str, Any],
    excerpts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    assert_citation_shape(citation)
    matches = [
        ex
        for ex in excerpts
        if str(ex.get("document_id")) == citation["document_id"]
        and int(ex.get("page")) == citation["page"]
        and str(ex.get("source_sha256")) == citation["source_sha256"]
    ]
    if len(matches) != 1:
        raise ValueError("citation does not resolve to exactly one excerpt")
    text = str(matches[0].get("text", ""))
    start = citation["span_start"]
    end = citation["span_end"]
    if end > len(text) or text[start:end] != citation["quote"]:
        raise ValueError("citation quote is not bound to the sliced excerpt span")
    if "[QUARANTINED_INSTRUCTION]" in citation["quote"]:
        raise ValueError("quarantined instruction text cannot be cited as evidence")
    return matches[0]


def _nonempty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string")
    return value


def assert_lead_complete(lead: Mapping[str, Any]) -> None:
    if not isinstance(lead, Mapping):
        raise ValueError("lead must be a mapping")
    missing = sorted(REQUIRED_LEAD_FIELDS - set(lead.keys()))
    if missing:
        raise ValueError(f"lead missing fields: {missing}")
    unknown = sorted(set(lead.keys()) - ALLOWED_LEAD_KEYS)
    if unknown:
        raise ValueError(f"lead unknown fields: {unknown}")
    for name in (
        "lead_id",
        "title",
        "domain",
        "care_phase",
        "cited_observation",
        "hypothesis",
        "review_question",
        "jurisdiction_date_scope",
        "clinical_plausibility",
        "temporal_linkage",
        "temporal_date",
        "peer_version",
        "model_version",
        "prompt_version",
        "policy_version",
    ):
        _nonempty_str(lead.get(name), name)
    assert_synthetic_id(lead["lead_id"], "lead_id")
    parse_iso_date(str(lead["temporal_date"]), "temporal_date")
    try:
        grade = EvidenceGrade(lead.get("evidence_grade"))
    except ValueError as exc:
        raise ValueError("evidence_grade invalid") from exc
    try:
        RelevanceGrade(lead.get("relevance_grade"))
    except ValueError as exc:
        raise ValueError("relevance_grade invalid") from exc
    for seq_name in (
        "supporting_facts",
        "counterevidence",
        "conflicts",
        "missing_records",
        "alternative_explanations",
        "source_universe_searched",
        "external_authorities",
        "review_history",
        "citations",
    ):
        value = lead.get(seq_name)
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{seq_name} must be a sequence")
    universe = [str(x) for x in lead["source_universe_searched"]]
    if not universe or any(not x.strip() for x in universe):
        raise ValueError("source_universe_searched must list labels actually searched")
    citations = list(lead.get("citations") or [])
    for citation in citations:
        assert_citation_shape(citation)
    supporting = list(lead.get("supporting_facts") or [])
    if grade in {EvidenceGrade.SUPPORTED, EvidenceGrade.CORROBORATED, EvidenceGrade.EXPLICIT}:
        if not citations or not supporting:
            raise ValueError("supported leads require typed citations and supporting facts")
    else:
        if not supporting and not list(lead.get("missing_records") or []):
            raise ValueError("CLUE leads require supporting facts or missing_records")
        if supporting and not citations:
            raise ValueError("supporting facts must be bound to typed citations")


def assert_lead_against_packet(lead: Mapping[str, Any], packet: Mapping[str, Any]) -> None:
    assert_lead_complete(lead)
    excerpts = list(packet.get("excerpts") or [])
    resolved: List[Tuple[str, int, str]] = []
    for citation in lead.get("citations") or []:
        ex = resolve_citation_against_excerpts(citation, excerpts)
        resolved.append(
            (str(ex.get("document_id")), int(ex.get("page")), str(ex.get("source_sha256")))
        )
    searched = set(str(x) for x in lead.get("source_universe_searched") or [])
    actual = {
        str(ex.get("source_category") or "clinical_note")
        for ex in excerpts
    }
    if excerpts and searched - actual:
        raise ValueError("source_universe_searched contains labels that were never searched")
    known_authorities = set(packet.get("grounding_pack_ids") or [])
    for aid in lead.get("external_authorities") or []:
        if str(aid) not in known_authorities:
            raise ValueError(f"unknown or inapplicable authority id: {aid}")
    for item in lead.get("counterevidence") or []:
        if not isinstance(item, Mapping):
            raise ValueError("counterevidence items must be typed citations or bound facts")
        if item.get("kind") == "citation":
            cite = item.get("citation")
            if not isinstance(cite, Mapping):
                raise ValueError("counterevidence citation missing")
            resolve_citation_against_excerpts(cite, excerpts)
            key = (cite["document_id"], cite["page"], cite["source_sha256"])
            if key not in resolved:
                raise ValueError("counterevidence must bind to a cited supporting source")
        elif item.get("kind") == "negation":
            quote = str(item.get("of_quote") or "")
            if not any(quote and quote == c.get("quote") for c in lead.get("citations") or []):
                raise ValueError("negation must name a cited supporting quote")
        else:
            raise ValueError("counterevidence must be a bound citation or negation")


def assert_no_injection_evidence(lead: Mapping[str, Any]) -> None:
    blob = " ".join(
        [
            str(lead.get("cited_observation") or ""),
            str(lead.get("hypothesis") or ""),
            " ".join(str(x) for x in lead.get("supporting_facts") or []),
            " ".join(str(c.get("quote") or "") for c in lead.get("citations") or []),
        ]
    ).lower()
    if "ignore previous" in blob or "ignore prior" in blob or "you are now" in blob:
        raise ValueError("injected instruction text cannot become evidence")
    if "quarantined_instruction" in blob:
        raise ValueError("quarantined instruction text cannot become evidence")


def trusted_identity_conflicts(role_id: str, result: Mapping[str, Any]) -> List[str]:
    conflicts: List[str] = []
    claimed_role = result.get("role_id")
    if claimed_role not in (None, role_id):
        conflicts.append("spoofed_role_id")
    if result.get("external_model_calls") not in (None, 0):
        conflicts.append("spoofed_external_model_calls")
    return conflicts
