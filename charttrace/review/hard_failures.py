"""Hard-failure detectors for ChartTrace internal review."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


HARD_FAILURE_CODES = frozenset(
    {
        "WRONG_PATIENT",
        "WRONG_PAGE",
        "WRONG_DATE",
        "WRONG_PROVIDER",
        "CITATION_DOES_NOT_ENTAIL",
        "INVENTED_CONNECTIVE_TISSUE",
        "PROBLEM_LIST_AS_DIAGNOSIS",
        "ORDERED_AS_COMPLETED",
        "SILENCE_AS_NONCOMMUNICATION",
        "COPY_FORWARD_AS_NEW_EVENT",
        "OCR_GUESS_AS_VERIFIED",
        "WRONG_YEAR_AUTHORITY",
        "WRONG_JURISDICTION_AUTHORITY",
        "OMITTED_COUNTEREVIDENCE",
        "IMPOSSIBLE_CHRONOLOGY",
        "UNIT_DECIMAL_LATERALITY_ERROR",
        "INFLAMMATORY_LEGAL_ACCUSATION",
        "BROKEN_TABLE_OR_PAGE_JUMP",
        "SOURCE_PROMPT_INJECTION_FOLLOWED",
        "FAKE_CITATION",
        "UNSUPPORTED_FACT",
    }
)


INFLAMMATORY_LEGAL_TERMS = frozenset(
    {
        "malpractice",
        "negligence",
        "negligent",
        "standard of care breach",
        "breached the standard of care",
        "causation established",
        "liable",
        "liability proven",
        "damages owed",
        "case value",
        "actionable claim",
    }
)


@dataclass
class HardFailure:
    code: str
    item_id: str
    detail: str
    stage: str = "hostile_audit"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "item_id": self.item_id,
            "detail": self.detail,
            "stage": self.stage,
        }


@dataclass
class HardFailureReport:
    failures: List[HardFailure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def codes(self) -> Set[str]:
        return {f.code for f in self.failures}

    def to_dict(self) -> Dict[str, Any]:
        return {"failures": [f.to_dict() for f in self.failures], "ok": self.ok}


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def citation_entails_clause(
    citation_text: str,
    clause: str,
    *,
    require_overlap_ratio: float = 0.45,
) -> bool:
    cit = _norm(citation_text)
    cl = _norm(clause)
    if not cl or not cit:
        return False
    if cl in cit:
        return True
    stop = {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
        "was", "were", "is", "are", "with", "by", "from", "that", "this", "as", "be",
    }
    tokens = [t for t in cl.replace(",", " ").replace(".", " ").split() if t not in stop]
    if not tokens:
        return cl in cit
    hits = sum(1 for t in tokens if t in cit)
    return (hits / len(tokens)) >= require_overlap_ratio


def detect_inflammatory_legal(text: str) -> Optional[str]:
    n = _norm(text)
    for term in INFLAMMATORY_LEGAL_TERMS:
        if term in n:
            return term
    return None


def audit_lead(lead: Dict[str, Any], *, stage: str = "hostile_audit") -> List[HardFailure]:
    failures: List[HardFailure] = []
    lid = str(lead.get("lead_id") or lead.get("fact_id") or lead.get("id") or "unknown")
    flags = set(lead.get("flags") or [])
    claim_type = str(lead.get("claim_type") or "")
    status = str(lead.get("status") or "")
    evidence_grade = str(lead.get("evidence_grade") or "")

    for code, key in (
        ("WRONG_PATIENT", "wrong_patient"),
        ("WRONG_PAGE", "wrong_page"),
        ("WRONG_DATE", "wrong_date"),
        ("WRONG_PROVIDER", "wrong_provider"),
    ):
        if key in flags or lead.get(key) is True:
            failures.append(HardFailure(code, lid, f"Flagged {key}", stage))

    citations: Sequence[Dict[str, Any]] = lead.get("citations") or []
    clause = str(
        lead.get("cited_observation")
        or lead.get("clause")
        or lead.get("text")
        or ""
    )
    if clause and citations:
        for cit in citations:
            cit_text = str(cit.get("text") or cit.get("span_text") or "")
            if cit.get("fake") or cit.get("invented"):
                failures.append(HardFailure("FAKE_CITATION", lid, "Citation marked invented/fake", stage))
                continue
            if not citation_entails_clause(cit_text, clause):
                failures.append(
                    HardFailure(
                        "CITATION_DOES_NOT_ENTAIL",
                        lid,
                        "Citation text does not entail clause",
                        stage,
                    )
                )
    elif clause and lead.get("requires_citation", True) and not citations:
        if evidence_grade not in ("", "CLUE") or lead.get("presented_as_fact"):
            failures.append(HardFailure("UNSUPPORTED_FACT", lid, "Factual clause lacks citations", stage))

    if lead.get("invented_connective_tissue") or "invented_connective_tissue" in flags:
        failures.append(
            HardFailure("INVENTED_CONNECTIVE_TISSUE", lid, "Invented narrative connective tissue", stage)
        )

    if claim_type == "problem_list_as_diagnosis" or "problem_list_as_diagnosis" in flags:
        failures.append(
            HardFailure(
                "PROBLEM_LIST_AS_DIAGNOSIS",
                lid,
                "Problem-list presented as confirmed diagnosis",
                stage,
            )
        )

    if claim_type == "ordered_as_completed" or "ordered_as_completed" in flags:
        failures.append(HardFailure("ORDERED_AS_COMPLETED", lid, "Ordered test treated as completed", stage))

    if claim_type == "silence_as_noncommunication" or "silence_as_noncommunication" in flags:
        failures.append(
            HardFailure("SILENCE_AS_NONCOMMUNICATION", lid, "Silence presented as noncommunication", stage)
        )

    if claim_type == "copy_forward_as_new" or "copy_forward_as_new" in flags:
        failures.append(
            HardFailure("COPY_FORWARD_AS_NEW_EVENT", lid, "Copied-forward text counted as new event", stage)
        )

    if (
        lead.get("ocr_guess_as_verified")
        or "ocr_guess_as_verified" in flags
        or (
            lead.get("ocr_confidence") is not None
            and float(lead["ocr_confidence"]) < 0.7
            and status == "verified"
        )
    ):
        failures.append(HardFailure("OCR_GUESS_AS_VERIFIED", lid, "OCR guess presented as verified", stage))

    authority = lead.get("authority") or {}
    if authority.get("wrong_year") or "wrong_year_authority" in flags:
        failures.append(HardFailure("WRONG_YEAR_AUTHORITY", lid, "Authority year mismatch", stage))
    if authority.get("wrong_jurisdiction") or "wrong_jurisdiction_authority" in flags:
        failures.append(
            HardFailure("WRONG_JURISDICTION_AUTHORITY", lid, "Authority jurisdiction mismatch", stage)
        )

    care_year = lead.get("care_year")
    auth_from = authority.get("effective_from_year")
    auth_to = authority.get("effective_to_year")
    if care_year is not None and auth_from is not None:
        try:
            cy = int(care_year)
            af = int(auth_from)
            at = int(auth_to) if auth_to is not None else 9999
            if cy < af or cy > at:
                failures.append(
                    HardFailure(
                        "WRONG_YEAR_AUTHORITY",
                        lid,
                        f"Care year {cy} outside authority {af}-{at}",
                        stage,
                    )
                )
        except (TypeError, ValueError):
            pass

    care_jurisdiction = str(lead.get("jurisdiction") or "")
    auth_jurisdiction = str(authority.get("jurisdiction") or "")
    if care_jurisdiction and auth_jurisdiction and care_jurisdiction != auth_jurisdiction:
        if authority.get("scope") != "multi_jurisdiction":
            failures.append(
                HardFailure(
                    "WRONG_JURISDICTION_AUTHORITY",
                    lid,
                    f"Care jurisdiction {care_jurisdiction} != {auth_jurisdiction}",
                    stage,
                )
            )

    if lead.get("omitted_counterevidence") or (
        lead.get("known_counterevidence") and not lead.get("counterevidence")
    ):
        failures.append(HardFailure("OMITTED_COUNTEREVIDENCE", lid, "Known counterevidence omitted", stage))

    if lead.get("impossible_chronology") or "impossible_chronology" in flags:
        failures.append(HardFailure("IMPOSSIBLE_CHRONOLOGY", lid, "Impossible event order", stage))

    events = lead.get("event_dates") or []
    if len(events) >= 2 and lead.get("assert_chronology_order"):
        try:
            if list(events) != sorted(events):
                failures.append(
                    HardFailure("IMPOSSIBLE_CHRONOLOGY", lid, "Asserted chronology is out of order", stage)
                )
        except TypeError:
            pass

    if (
        lead.get("unit_error")
        or lead.get("decimal_error")
        or lead.get("laterality_error")
        or "unit_decimal_laterality_error" in flags
    ):
        failures.append(
            HardFailure("UNIT_DECIMAL_LATERALITY_ERROR", lid, "Unit, decimal, or laterality error", stage)
        )

    for blob in (
        str(lead.get("hypothesis") or ""),
        str(lead.get("title") or ""),
        str(lead.get("review_question") or ""),
        clause,
    ):
        term = detect_inflammatory_legal(blob)
        if term:
            failures.append(
                HardFailure(
                    "INFLAMMATORY_LEGAL_ACCUSATION",
                    lid,
                    f"Inflammatory legal language: {term}",
                    stage,
                )
            )
            break

    if lead.get("broken_page_jump") or lead.get("broken_table") or "broken_table_or_page_jump" in flags:
        failures.append(HardFailure("BROKEN_TABLE_OR_PAGE_JUMP", lid, "Broken table or page jump", stage))

    if lead.get("followed_source_prompt") or "source_prompt_injection_followed" in flags:
        failures.append(
            HardFailure(
                "SOURCE_PROMPT_INJECTION_FOLLOWED",
                lid,
                "Instructions embedded in source were followed",
                stage,
            )
        )

    if lead.get("unsupported") or "unsupported_fact" in flags:
        failures.append(HardFailure("UNSUPPORTED_FACT", lid, "Unsupported fact", stage))

    return failures


def audit_leads(leads: Iterable[Dict[str, Any]], *, stage: str = "hostile_audit") -> HardFailureReport:
    report = HardFailureReport()
    for lead in leads:
        report.failures.extend(audit_lead(lead, stage=stage))
    return report
