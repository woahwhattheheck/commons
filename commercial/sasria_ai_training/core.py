"""Fail-closed readiness compiler for Sasria RFP2026/22 teaming evidence.

The compiler records evidence supplied by a prospective qualified prime.  It does
not certify South African procurement eligibility, training accreditation,
client references, buyer scores, partnership, submission, award, or payment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "tjlabs.sasria_ai_training_readiness.v1"

REQUIRED_RETURNABLES = (
    "sbd_1_invitation_to_bid",
    "sbd_4_disclosure_declaration",
    "sbd_6_1_specific_goals",
    "annexure_a_confidentiality_nda",
    "annexure_b_bid_conditions_details",
    "annexure_c_shareholder_information",
    "annexure_d_experience_project_team",
    "csd_report",
    "bbbee_certificate_or_affidavit",
    "technical_proposal",
    "financial_proposal",
)

RECOGNIZED_FRAMEWORKS = frozenset(
    {
        "ISO/IEC 42001",
        "NIST AI RMF",
        "Gartner AI Governance Playbook",
    }
)

ROLE_GROUPS = (
    "executives_and_senior_management",
    "specialists_and_general_employees",
    "ai_navigators",
    "ai_project_team",
    "technical_team",
    "business_process_owners",
)

TECHNICAL_SCORE_CAPS = {
    "company_profile": 20,
    "project_proposal_and_training_methodology": 40,
    "training_personnel": 10,
    "key_personnel_cvs": 10,
    "reference_letters": 20,
}
TECHNICAL_PASS_SCORE = 70


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted({value.strip() for value in values if isinstance(value, str) and value.strip()})


@dataclass(frozen=True)
class EvidenceRef:
    label: str
    locator: str
    note: str = ""

    def valid(self) -> bool:
        return _nonempty(self.label) and _nonempty(self.locator)

    def as_dict(self) -> dict[str, str]:
        return {
            "label": self.label.strip(),
            "locator": self.locator.strip(),
            "note": self.note.strip(),
        }


@dataclass(frozen=True)
class PrimeCandidate:
    legal_name: str
    company_profile_ref: EvidenceRef | None
    returnables: Mapping[str, bool]
    framework_alignment: tuple[str, ...] = ()
    framework_evidence: tuple[EvidenceRef, ...] = ()
    training_body_accreditation_ref: EvidenceRef | None = None
    recognized_certification_capability_ref: EvidenceRef | None = None
    platform_access_12_months_ref: EvidenceRef | None = None
    regulated_environment_training_ref: EvidenceRef | None = None
    financial_services_training_ref: EvidenceRef | None = None
    facilitator_refs: tuple[EvidenceRef, ...] = ()
    reference_letter_refs: tuple[EvidenceRef, ...] = ()
    ai_trainings_last_3y: int | None = None

    def mandatory_gate(self) -> dict[str, Any]:
        blockers: list[str] = []
        warnings: list[str] = []

        if not _nonempty(self.legal_name):
            blockers.append("missing_legal_name")
        if self.company_profile_ref is None or not self.company_profile_ref.valid():
            blockers.append("missing_company_profile_evidence")

        missing_returnables = sorted(
            name for name in REQUIRED_RETURNABLES if self.returnables.get(name) is not True
        )
        if missing_returnables:
            blockers.append("missing_required_returnables")

        frameworks = _sorted_unique(self.framework_alignment)
        recognized = sorted(set(frameworks) & RECOGNIZED_FRAMEWORKS)
        if not recognized:
            blockers.append("missing_recognized_ai_governance_framework_alignment")
        valid_framework_refs = [ref for ref in self.framework_evidence if ref.valid()]
        if not valid_framework_refs:
            blockers.append("missing_framework_alignment_evidence")

        for field_name, ref in (
            ("training_body_accreditation", self.training_body_accreditation_ref),
            ("recognized_certification_capability", self.recognized_certification_capability_ref),
            ("post_training_platform_access_12_months", self.platform_access_12_months_ref),
        ):
            if ref is None or not ref.valid():
                blockers.append(f"missing_{field_name}_evidence")

        if self.ai_trainings_last_3y is None:
            warnings.append("ai_training_count_not_evidenced")
        elif isinstance(self.ai_trainings_last_3y, bool) or not isinstance(self.ai_trainings_last_3y, int) or self.ai_trainings_last_3y < 0:
            blockers.append("invalid_ai_training_count")
        elif self.ai_trainings_last_3y < 5:
            warnings.append("company_profile_may_not_reach_max_training_history_score")

        if self.regulated_environment_training_ref is None or not self.regulated_environment_training_ref.valid():
            warnings.append("regulated_environment_training_evidence_missing")
        if self.financial_services_training_ref is None or not self.financial_services_training_ref.valid():
            warnings.append("financial_services_training_evidence_missing")
        if not [ref for ref in self.facilitator_refs if ref.valid()]:
            warnings.append("facilitator_evidence_missing")
        if not [ref for ref in self.reference_letter_refs if ref.valid()]:
            warnings.append("reference_letters_missing")

        blockers.sort()
        warnings.sort()
        return {
            "status": "PRIME_MANDATORY_READY" if not blockers else "HOLD",
            "blockers": blockers,
            "warnings": warnings,
            "missing_returnables": missing_returnables,
            "recognized_frameworks": recognized,
            "valid_framework_evidence_count": len(valid_framework_refs),
            "valid_facilitator_evidence_count": len([ref for ref in self.facilitator_refs if ref.valid()]),
            "valid_reference_letter_count": len([ref for ref in self.reference_letter_refs if ref.valid()]),
            "ai_trainings_last_3y": self.ai_trainings_last_3y,
        }


@dataclass(frozen=True)
class BuyerTechnicalScore:
    """Scores copied from a grounded buyer-rubric review, never self-inferred."""

    scores: Mapping[str, int]
    evidence_refs: tuple[EvidenceRef, ...] = ()

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        normalized: dict[str, int] = {}
        missing = sorted(set(TECHNICAL_SCORE_CAPS) - set(self.scores))
        extra = sorted(set(self.scores) - set(TECHNICAL_SCORE_CAPS))
        if missing:
            blockers.append("missing_technical_score_categories")
        if extra:
            blockers.append("unknown_technical_score_categories")

        for category, cap in TECHNICAL_SCORE_CAPS.items():
            if category not in self.scores:
                continue
            value = self.scores[category]
            if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= cap):
                blockers.append(f"invalid_score:{category}")
            else:
                normalized[category] = value

        evidence = [ref.as_dict() for ref in self.evidence_refs if ref.valid()]
        if not evidence:
            blockers.append("missing_score_evidence")

        total = sum(normalized.values()) if len(normalized) == len(TECHNICAL_SCORE_CAPS) else None
        if total is not None and total < TECHNICAL_PASS_SCORE:
            blockers.append("technical_score_below_70")

        blockers = sorted(set(blockers))
        return {
            "status": "TECHNICAL_THRESHOLD_READY" if not blockers else "HOLD",
            "blockers": blockers,
            "scores": {key: normalized[key] for key in sorted(normalized)},
            "score_caps": dict(sorted(TECHNICAL_SCORE_CAPS.items())),
            "total": total,
            "pass_threshold": TECHNICAL_PASS_SCORE,
            "evidence_refs": evidence,
            "scoring_boundary": "Values must come from a grounded buyer-rubric review; this compiler does not award points.",
        }


@dataclass(frozen=True)
class TrainingPathway:
    role_group: str
    learning_outcomes: tuple[str, ...]
    delivery_modes: tuple[str, ...]
    evaluation_methods: tuple[str, ...]
    artefacts: tuple[str, ...]

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        if self.role_group not in ROLE_GROUPS:
            blockers.append("unknown_role_group")
        outcomes = _sorted_unique(self.learning_outcomes)
        modes = _sorted_unique(self.delivery_modes)
        evaluations = _sorted_unique(self.evaluation_methods)
        artefacts = _sorted_unique(self.artefacts)
        if not outcomes:
            blockers.append("missing_learning_outcomes")
        if not modes:
            blockers.append("missing_delivery_modes")
        if not evaluations:
            blockers.append("missing_evaluation_methods")
        if not artefacts:
            blockers.append("missing_training_artefacts")
        return {
            "role_group": self.role_group,
            "status": "READY" if not blockers else "HOLD",
            "blockers": sorted(blockers),
            "learning_outcomes": outcomes,
            "delivery_modes": modes,
            "evaluation_methods": evaluations,
            "artefacts": artefacts,
        }


@dataclass(frozen=True)
class PaidWorkshare:
    owner: str
    deliverables: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    exclusions: tuple[str, ...]
    commercial_state: str = "PAID_SCOPE_TO_BE_AGREED"

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        if not _nonempty(self.owner):
            blockers.append("missing_workshare_owner")
        deliverables = _sorted_unique(self.deliverables)
        acceptance = _sorted_unique(self.acceptance_criteria)
        exclusions = _sorted_unique(self.exclusions)
        if not deliverables:
            blockers.append("missing_workshare_deliverables")
        if not acceptance:
            blockers.append("missing_workshare_acceptance_criteria")
        if not exclusions:
            blockers.append("missing_workshare_exclusions")
        if self.commercial_state != "PAID_SCOPE_TO_BE_AGREED":
            blockers.append("unsupported_commercial_state")
        return {
            "status": "WORKSHARE_READY" if not blockers else "HOLD",
            "blockers": sorted(blockers),
            "owner": self.owner.strip(),
            "deliverables": deliverables,
            "acceptance_criteria": acceptance,
            "exclusions": exclusions,
            "commercial_state": self.commercial_state,
        }


@dataclass(frozen=True)
class SubmissionAuthority:
    portal_account_confirmed: bool = False
    authorized_signatory_confirmed: bool = False
    prime_approved_submission: bool = False

    def result(self) -> dict[str, Any]:
        missing = []
        if not self.portal_account_confirmed:
            missing.append("portal_account_not_confirmed")
        if not self.authorized_signatory_confirmed:
            missing.append("authorized_signatory_not_confirmed")
        if not self.prime_approved_submission:
            missing.append("prime_submission_approval_not_confirmed")
        return {
            "status": "SUBMISSION_AUTHORITY_READY" if not missing else "HOLD",
            "blockers": missing,
        }


def compile_readiness_pack(
    *,
    prime: PrimeCandidate,
    technical_score: BuyerTechnicalScore,
    pathways: Sequence[TrainingPathway],
    workshare: PaidWorkshare,
    submission_authority: SubmissionAuthority | None = None,
) -> dict[str, Any]:
    prime_result = prime.mandatory_gate()
    score_result = technical_score.result()
    pathway_rows = sorted((pathway.result() for pathway in pathways), key=lambda row: row["role_group"])
    represented_roles = {row["role_group"] for row in pathway_rows if row["role_group"] in ROLE_GROUPS}
    missing_roles = sorted(set(ROLE_GROUPS) - represented_roles)
    duplicate_roles = sorted(
        role
        for role in represented_roles
        if sum(row["role_group"] == role for row in pathway_rows) > 1
    )
    workshare_result = workshare.result()
    authority_result = (submission_authority or SubmissionAuthority()).result()

    blockers: list[str] = []
    if prime_result["status"] != "PRIME_MANDATORY_READY":
        blockers.append("prime_mandatory_gate")
    if score_result["status"] != "TECHNICAL_THRESHOLD_READY":
        blockers.append("technical_score_gate")
    if missing_roles:
        blockers.append("missing_role_pathways")
    if duplicate_roles:
        blockers.append("duplicate_role_pathways")
    if any(row["status"] != "READY" for row in pathway_rows):
        blockers.append("pathway_content_gate")
    if workshare_result["status"] != "WORKSHARE_READY":
        blockers.append("paid_workshare_gate")

    response_status = "RESPONSE_ASSEMBLY_READY" if not blockers else "HOLD"
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "opportunity": {
            "buyer": "Sasria SOC Ltd",
            "solicitation": "RFP2026/22",
            "closing": "2026-09-17T12:00:00+02:00",
            "submission_route": "Sasria Online Tender Portal",
        },
        "prime_gate": prime_result,
        "technical_score": score_result,
        "training_pathways": pathway_rows,
        "missing_role_pathways": missing_roles,
        "duplicate_role_pathways": duplicate_roles,
        "paid_workshare": workshare_result,
        "response_status": response_status,
        "response_blockers": sorted(set(blockers)),
        "submission_authority": authority_result,
        "submission_status": "SUBMISSION_READY" if response_status == "RESPONSE_ASSEMBLY_READY" and authority_result["status"] == "SUBMISSION_AUTHORITY_READY" else "HOLD",
        "claims_boundary": (
            "Records supplied evidence only. It does not certify CSD/B-BBEE status, accreditation, certification authority, "
            "client references, buyer scoring, legal/procurement compliance, partnership, portal registration, submission, award, payment, or revenue."
        ),
    }
    payload["receipt_sha256"] = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return payload


def render_markdown(pack: Mapping[str, Any]) -> str:
    lines = [
        "# Sasria RFP2026/22 readiness pack",
        "",
        f"- Response assembly: **{pack['response_status']}**",
        f"- Submission: **{pack['submission_status']}**",
        f"- Prime mandatory gate: **{pack['prime_gate']['status']}**",
        f"- Technical threshold gate: **{pack['technical_score']['status']}**",
        f"- Paid workshare: **{pack['paid_workshare']['status']}**",
        f"- Receipt SHA-256: `{pack['receipt_sha256']}`",
        "",
        "## Response blockers",
    ]
    blockers = pack.get("response_blockers") or []
    lines.extend([f"- `{item}`" for item in blockers] or ["- none"])
    lines.extend(["", "## Prime blockers"])
    prime_blockers = pack["prime_gate"].get("blockers") or []
    lines.extend([f"- `{item}`" for item in prime_blockers] or ["- none"])
    lines.extend(["", "## Prime warnings"])
    warnings = pack["prime_gate"].get("warnings") or []
    lines.extend([f"- `{item}`" for item in warnings] or ["- none"])
    lines.extend(["", "## Role pathways"])
    for row in pack.get("training_pathways", []):
        lines.append(f"- `{row['role_group']}` — **{row['status']}**")
    lines.extend(["", "## Submission authority"])
    for item in pack["submission_authority"].get("blockers", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Claims boundary", str(pack["claims_boundary"]), ""])
    return "\n".join(lines)
