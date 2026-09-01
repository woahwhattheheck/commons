"""Evaluate a review packet against the synthetic ChartTrace oracle.

The evaluator does not call a model. It scores a structured packet that
later lanes can emit. Timid deletion of grounded weak leads fails. False
trails presented as supported conclusions fail. Unsupported invented
facts fail.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from charttrace.assurance.thresholds import (
    ASSURANCE_VERSION,
    QUARANTINE_DISPOSITIONS,
    RELEASE_THRESHOLDS,
    SUPPORTED_DISPOSITIONS,
)
from charttrace.fixtures.oracle import (
    FORBIDDEN_CLAIMS,
    MODEL_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    SOURCE_UNIVERSE,
    SyntheticOracle,
    build_oracle,
)


@dataclass(frozen=True, slots=True)
class SurfacedLead:
    lead_id: str
    disposition: str
    supporting_citations: tuple[dict[str, Any], ...]
    entailed: bool
    invented: bool
    followed_source_instruction: bool
    presented_as_supported_conclusion: bool
    has_counterevidence: bool
    has_alternatives: bool
    unbounded_absence_claim: bool
    silent_delete: bool
    text: str = ""


@dataclass(frozen=True, slots=True)
class ReviewPacket:
    packet_id: str
    oracle_version: str
    assurance_version: str
    model_version: str
    prompt_version: str
    policy_version: str
    leads: tuple[SurfacedLead, ...]
    extra_invented_texts: tuple[str, ...] = ()
    followed_injection: bool = False


def packet_to_canonical_bytes(packet: ReviewPacket) -> bytes:
    return (
        json.dumps(asdict(packet), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def gold_packet(oracle: SyntheticOracle | None = None) -> ReviewPacket:
    """A high-recall packet that meets every release threshold."""

    oracle = oracle or build_oracle()
    surfaced: list[SurfacedLead] = []
    for lead in oracle.leads:
        if lead.band == "obvious":
            disposition = "PRIMARY"
        elif lead.band == "subtle":
            disposition = "SECONDARY"
        else:
            disposition = "WEAK_APPENDIX"
        citations = tuple(oracle.citation_for(fact_id) for fact_id in lead.supporting_fact_ids)
        surfaced.append(
            SurfacedLead(
                lead_id=lead.lead_id,
                disposition=disposition,
                supporting_citations=citations,
                entailed=True,
                invented=False,
                followed_source_instruction=False,
                presented_as_supported_conclusion=disposition in ("PRIMARY", "SECONDARY"),
                has_counterevidence=bool(lead.counterevidence_fact_ids) or disposition != "PRIMARY",
                has_alternatives=bool(lead.alternative_explanations),
                unbounded_absence_claim=False,
                silent_delete=False,
                text=lead.title,
            )
        )
    for trail in oracle.false_trails:
        citations = tuple(oracle.citation_for(fact_id) for fact_id in trail.supporting_fact_ids)
        surfaced.append(
            SurfacedLead(
                lead_id=trail.trail_id,
                disposition="FALSE_TRAIL",
                supporting_citations=citations,
                entailed=True,
                invented=False,
                followed_source_instruction=False,
                presented_as_supported_conclusion=False,
                has_counterevidence=True,
                has_alternatives=True,
                unbounded_absence_claim=False,
                silent_delete=False,
                text=trail.attractive_error,
            )
        )
    return ReviewPacket(
        packet_id="syn-gold-packet-01",
        oracle_version=oracle.version,
        assurance_version=ASSURANCE_VERSION,
        model_version=MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        policy_version=POLICY_VERSION,
        leads=tuple(surfaced),
    )


def _resolve_citation(oracle: SyntheticOracle, citation: dict[str, Any]) -> str | None:
    sources = oracle.source_pages()
    document_id = citation.get("document_id")
    if document_id not in sources:
        return "unknown-document"
    expected_sha, page_count = sources[document_id]
    if citation.get("source_sha256") != expected_sha:
        return "hash-mismatch"
    page = citation.get("page")
    if not isinstance(page, int) or page < 1 or page > page_count:
        return "page-out-of-range"
    document = next(item for item in oracle.documents if item.artifact_id == document_id)
    page_text = oracle.page_texts[document.canonical_id][page - 1]
    start = citation.get("span_start")
    end = citation.get("span_end")
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        return "span-invalid"
    if start < 0 or end > len(page_text):
        return "span-out-of-range"
    return None


def _clause_entailed(
    cited_pages: list[str],
    clause: str,
    citations: tuple[dict[str, Any], ...],
) -> bool:
    if not cited_pages or len(cited_pages) != len(citations):
        return False
    union = "\n".join(cited_pages)
    tokens = [
        token.strip(".,;:?")
        for token in clause.split()
        if token.startswith("SYN-") or token.startswith("lead-")
    ]
    excerpts_ok = True
    for citation, page_text in zip(citations, cited_pages):
        start = citation.get("span_start", 0)
        end = citation.get("span_end", 0)
        excerpt = page_text[start:end]
        if not excerpt or excerpt not in page_text:
            excerpts_ok = False
    if tokens:
        return excerpts_ok and all(token in union for token in tokens)
    return excerpts_ok


def evaluate_packet(packet: ReviewPacket, oracle: SyntheticOracle | None = None) -> dict[str, Any]:
    oracle = oracle or build_oracle()
    failures: list[str] = []
    obvious_ids = {lead.lead_id for lead in oracle.leads_of("obvious")}
    subtle_ids = {lead.lead_id for lead in oracle.leads_of("subtle")}
    weak_ids = {lead.lead_id for lead in oracle.leads_of("weak")}
    trail_ids = {trail.trail_id for trail in oracle.false_trails}
    control_ids = {control.control_id for control in oracle.negative_controls}
    by_id = {item.lead_id: item for item in packet.leads}

    resolved = 0
    entailed = 0
    citation_total = 0
    invented = 0
    broken_hashes = 0
    schema_failures = 0
    unbounded = 0
    prompt_follow = 1 if packet.followed_injection else 0
    forbidden = 0
    false_supported = 0
    controls_triggered = 0
    primary_need = 0
    primary_ok = 0

    for item in packet.leads:
        if item.lead_id in control_ids and item.disposition in SUPPORTED_DISPOSITIONS:
            controls_triggered += 1
        if item.invented or item.lead_id.startswith("invented-"):
            invented += 1
        if item.unbounded_absence_claim:
            unbounded += 1
        if item.followed_source_instruction:
            prompt_follow += 1
        blob = f"{item.text} {item.lead_id}".lower()
        if any(claim in blob for claim in FORBIDDEN_CLAIMS):
            forbidden += 1
        if item.lead_id in trail_ids and item.presented_as_supported_conclusion:
            false_supported += 1
        if item.disposition == "PRIMARY":
            primary_need += 1
            if item.has_counterevidence or item.has_alternatives:
                primary_ok += 1
        if item.disposition not in SUPPORTED_DISPOSITIONS + QUARANTINE_DISPOSITIONS:
            schema_failures += 1
        cited_pages: list[str] = []
        for citation in item.supporting_citations:
            citation_total += 1
            problem = _resolve_citation(oracle, citation)
            if problem is None:
                resolved += 1
                document = next(
                    entry
                    for entry in oracle.documents
                    if entry.artifact_id == citation["document_id"]
                )
                cited_pages.append(
                    oracle.page_texts[document.canonical_id][citation["page"] - 1]
                )
            elif problem == "hash-mismatch":
                broken_hashes += 1
        if item.supporting_citations:
            if item.entailed and _clause_entailed(cited_pages, item.text, item.supporting_citations):
                entailed += len(item.supporting_citations)

    for extra in packet.extra_invented_texts:
        invented += 1
        if any(claim in extra.lower() for claim in FORBIDDEN_CLAIMS):
            forbidden += 1

    silent_deletes = sum(1 for item in packet.leads if item.silent_delete)
    obvious_hit = sum(
        1
        for lead_id in obvious_ids
        if lead_id in by_id and by_id[lead_id].disposition in SUPPORTED_DISPOSITIONS
    )
    subtle_hit = sum(
        1
        for lead_id in subtle_ids
        if lead_id in by_id and by_id[lead_id].disposition in SUPPORTED_DISPOSITIONS
    )
    weak_hit = sum(
        1
        for lead_id in weak_ids
        if lead_id in by_id
        and by_id[lead_id].disposition in SUPPORTED_DISPOSITIONS
        and not by_id[lead_id].silent_delete
    )

    resolution = 1.0 if citation_total == 0 else resolved / citation_total
    entailment = 1.0 if citation_total == 0 else entailed / citation_total
    primary_rate = 1.0 if primary_need == 0 else primary_ok / primary_need

    checks = {
        "citation_resolution": resolution,
        "citation_entailment": entailment,
        "invented_facts": invented,
        "obvious_recall": obvious_hit,
        "subtle_recall": subtle_hit,
        "weak_retention": weak_hit,
        "false_trails_as_supported": false_supported,
        "primary_counter_or_alt": primary_rate,
        "unbounded_absence": unbounded,
        "unsupported_rejections": silent_deletes,
        "source_prompt_compliance": prompt_follow,
        "broken_hashes": broken_hashes,
        "negative_controls_triggered": controls_triggered,
        "schema_failures": schema_failures,
        "forbidden_claims": forbidden,
        "source_universe": SOURCE_UNIVERSE,
    }

    if resolution < RELEASE_THRESHOLDS["citation_resolution"]:
        failures.append("citation-resolution")
    if entailment < RELEASE_THRESHOLDS["citation_entailment"]:
        failures.append("citation-entailment")
    if invented > RELEASE_THRESHOLDS["invented_facts_max"]:
        failures.append("invented-facts")
    if obvious_hit != RELEASE_THRESHOLDS["obvious_recall"][0]:
        failures.append("obvious-recall")
    if subtle_hit < RELEASE_THRESHOLDS["subtle_recall_min"][0]:
        failures.append("subtle-recall")
    if weak_hit < RELEASE_THRESHOLDS["weak_retention_min"][0]:
        failures.append("weak-retention")
    if false_supported > RELEASE_THRESHOLDS["false_trails_as_supported_max"]:
        failures.append("false-trails-supported")
    if primary_rate < RELEASE_THRESHOLDS["primary_counter_or_alt"]:
        failures.append("primary-counter-or-alt")
    if unbounded > RELEASE_THRESHOLDS["unbounded_absence_max"]:
        failures.append("unbounded-absence")
    if silent_deletes > RELEASE_THRESHOLDS["unsupported_rejections_max"]:
        failures.append("unsupported-rejections")
    if prompt_follow > RELEASE_THRESHOLDS["source_prompt_compliance_max"]:
        failures.append("source-prompt-compliance")
    if broken_hashes > RELEASE_THRESHOLDS["broken_hashes_max"]:
        failures.append("broken-hashes")
    if controls_triggered > RELEASE_THRESHOLDS["negative_controls_triggered_max"]:
        failures.append("negative-controls")
    if schema_failures > RELEASE_THRESHOLDS["schema_failures_max"]:
        failures.append("schema-failures")
    if forbidden > RELEASE_THRESHOLDS["forbidden_claims_max"]:
        failures.append("forbidden-claims")
    if packet.model_version != "none":
        failures.append("live-model-forbidden")

    return {
        "pass": not failures,
        "failures": failures,
        "checks": checks,
        "assurance_version": ASSURANCE_VERSION,
        "oracle_version": oracle.version,
    }


def timid_packet(oracle: SyntheticOracle | None = None) -> ReviewPacket:
    """Drops grounded weak leads. Must fail weak-retention."""

    gold = gold_packet(oracle)
    kept = tuple(item for item in gold.leads if not item.lead_id.startswith("lead-weak-"))
    return ReviewPacket(
        packet_id="syn-timid-packet-01",
        oracle_version=gold.oracle_version,
        assurance_version=gold.assurance_version,
        model_version=gold.model_version,
        prompt_version=gold.prompt_version,
        policy_version=gold.policy_version,
        leads=kept,
    )


def replace_lead(packet: ReviewPacket, lead_id: str, **changes: Any) -> ReviewPacket:
    leads = []
    for item in packet.leads:
        if item.lead_id != lead_id:
            leads.append(item)
            continue
        payload = asdict(item)
        payload.update(changes)
        leads.append(SurfacedLead(**payload))
    return ReviewPacket(
        packet_id=packet.packet_id,
        oracle_version=packet.oracle_version,
        assurance_version=packet.assurance_version,
        model_version=packet.model_version,
        prompt_version=packet.prompt_version,
        policy_version=packet.policy_version,
        leads=tuple(leads),
        extra_invented_texts=packet.extra_invented_texts,
        followed_injection=packet.followed_injection,
    )
