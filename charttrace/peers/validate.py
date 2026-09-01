"""Fail-closed packet, citation, and worker-output validation (Lane B)."""

from __future__ import annotations

from datetime import date
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from charttrace.peers.contracts import (
    ALLOWED_LEAD_KEYS,
    EvidenceGrade,
    FORBIDDEN_PEER_INPUT_KEYS,
    REQUIRED_LEAD_FIELDS,
    RelevanceGrade,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NAMESPACED_ID_RE = re.compile(r"^[a-z][a-z0-9_]*[-:][a-z0-9][a-z0-9.:-]{0,120}$")
NAME_LIKE_ID_RE = re.compile(r"[A-Z][a-z]+[._-][A-Z][a-z]+")
SSN_LIKE_ID_RE = re.compile(r"\d{3}[-_.]\d{2}[-_.]\d{4}")
MRN_SEGMENT_RE = re.compile(r"^mrn\d+$")
DIGIT_SEGMENT_RE = re.compile(r"^\d+$")
PHI_TOKEN_RE = re.compile(
    r"(?i)(\b(mrn|ssn|dob|patient|phi)\b|\d{3}-\d{2}-\d{4}|[A-Z][a-z]+\s+[A-Z][a-z]+)"
)
LONG_DIGIT_RE = re.compile(r"\d{8,}")
ZERO_WIDTH_CHARS = (
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",
    "\u00ad",
)
NAME_DENYLIST = frozenset(
    {
        "jane",
        "john",
        "doe",
        "smith",
        "patient",
        "mrn",
        "ssn",
        "dob",
        "phi",
        "mary",
        "robert",
    }
)
CARE_PHASES = frozenset(
    {
        "unspecified",
        "acute_care",
        "perioperative",
        "documentation",
        "review",
        "continuity",
        "medication",
        "diagnostics",
        "differential",
        "authority",
        "sequelae",
        "communication",
        "outpatient",
        "inpatient",
    }
)
SOURCE_CATEGORIES = frozenset(
    {
        "clinical_note",
        "progress_note",
        "progress_notes",
        "operative_note",
        "lab_report",
        "imaging",
        "other_record",
        "supplied_record_excerpts",
    }
)
KNOWN_FACT_RE = re.compile(r"^fact:[a-z0-9][a-z0-9:-]{0,80}$")
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


def canonicalize_identifier(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value)
    for mark in ZERO_WIDTH_CHARS:
        folded = folded.replace(mark, "")
    folded = (
        folded.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("．", ".")
        .replace("。", ".")
        .replace("：", ":")
        .replace("_", "_")
    )
    return folded


def _id_segments(value: str) -> List[str]:
    return [part for part in re.split(r"[-:._]+", value.lower()) if part]


def _namespace_remainder(value: str) -> str:
    matched = re.match(r"^[a-z][a-z0-9_]*[-:](.*)$", value)
    return matched.group(1) if matched else value


def _opaque_id_rejected(value: str, *, packet_id: bool) -> bool:
    if " " in value or ".." in value:
        return True
    remainder = _namespace_remainder(value)
    if "_" in remainder:
        return True
    if PHI_TOKEN_RE.search(value) or NAME_LIKE_ID_RE.search(value) or SSN_LIKE_ID_RE.search(value):
        return True
    if packet_id and LONG_DIGIT_RE.search(value):
        return True
    segments = _id_segments(value)
    if any(seg in NAME_DENYLIST for seg in segments):
        return True
    if any(MRN_SEGMENT_RE.fullmatch(seg) for seg in segments):
        return True
    if sum(1 for seg in segments if DIGIT_SEGMENT_RE.fullmatch(seg) and len(seg) >= 2) >= 2:
        return True
    return False


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
    canon = canonicalize_identifier(value)
    if canon != value or any(ord(ch) > 127 for ch in value):
        raise ValueError(f"{field_name} rejects names, MRNs, and PHI-like tokens")
    if _opaque_id_rejected(value, packet_id=packet_id):
        raise ValueError(f"{field_name} rejects names, MRNs, and PHI-like tokens")
    if not NAMESPACED_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a namespaced synthetic identifier")
    return value


def assert_care_phase(value: Any, field_name: str = "care_phase") -> str:
    if not isinstance(value, str) or value not in CARE_PHASES:
        raise ValueError(f"{field_name} must be an enumerated care phase")
    return value


def assert_source_category(value: Any, field_name: str = "source_category") -> str:
    if not isinstance(value, str) or value not in SOURCE_CATEGORIES:
        raise ValueError(f"{field_name} must be an enumerated source category")
    return value


def assert_known_fact_token(value: Any) -> str:
    if not isinstance(value, str) or not KNOWN_FACT_RE.fullmatch(value):
        raise ValueError("known_facts must be opaque fact tokens")
    if COMMERCIAL_VALUE_RE.search(value):
        raise ValueError("known_facts rejects commercial/medical free text")
    return value


def assert_raw_packet_types(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("packet must be a mapping")
    for key in ("case_id", "jurisdiction", "care_date_start", "care_date_end"):
        if key in payload and not isinstance(payload[key], str):
            raise ValueError(f"{key} must be a string before coercion")
    excerpts = payload.get("excerpts", [])
    if excerpts is None:
        excerpts = []
    if not isinstance(excerpts, list):
        raise ValueError("excerpts must be a list")
    for ex in excerpts:
        if not isinstance(ex, Mapping):
            raise ValueError("excerpt must be a mapping")
        if "document_id" in ex and not isinstance(ex["document_id"], str):
            raise ValueError("document_id must be a string before coercion")
        if "page" in ex and (isinstance(ex["page"], bool) or not isinstance(ex["page"], int)):
            raise ValueError("page must be an int before coercion")
        if "text" in ex and not isinstance(ex["text"], str):
            raise ValueError("excerpt text must be a string")
        if any(isinstance(v, Mapping) for v in ex.values()):
            raise ValueError("nested excerpt metadata rejected")
        if "care_phase" in ex:
            assert_care_phase(ex["care_phase"])
        if "source_category" in ex:
            assert_source_category(ex["source_category"])
    facts = payload.get("known_facts", [])
    if facts is None:
        facts = []
    if not isinstance(facts, list):
        raise ValueError("known_facts must be a list")
    for item in facts:
        if isinstance(item, Mapping):
            raise ValueError("nested known_facts rejected")
        assert_known_fact_token(item)
    universe = payload.get("source_universe", [])
    if universe is None:
        universe = []
    if not isinstance(universe, list):
        raise ValueError("source_universe must be a list")
    for item in universe:
        assert_source_category(item, "source_universe")
    packs = payload.get("grounding_pack_ids", [])
    if packs is None:
        packs = []
    if not isinstance(packs, list):
        raise ValueError("grounding_pack_ids must be a list")
    for item in packs:
        if not isinstance(item, str) or not item:
            raise ValueError("grounding_pack_ids must be strings")
    if "sealed_peer_results" in payload:
        raise ValueError("caller-supplied sealed_peer_results rejected")


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
    assert_raw_packet_types(payload)
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
    if "care_phase" in excerpt:
        assert_care_phase(excerpt["care_phase"])
    if "source_category" in excerpt:
        assert_source_category(excerpt["source_category"])


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
    assert_care_phase(lead.get("care_phase"))
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
    from charttrace.peers.sanitize import deobfuscate

    blob = " ".join(
        [
            str(lead.get("cited_observation") or ""),
            str(lead.get("hypothesis") or ""),
            " ".join(str(x) for x in lead.get("supporting_facts") or []),
            " ".join(str(c.get("quote") or "") for c in lead.get("citations") or []),
        ]
    ).lower()
    blob = deobfuscate(blob)
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
