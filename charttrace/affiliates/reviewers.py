"""ChartTrace Affiliate Reviewer Subsystem (Lane E).

Implements audited reviewer QA tiers, structured fee calculation, and conflict guards.

CRITICAL INVARIANTS:
1. Review fee formula:
   review_fee = page_band_rate × established_QA_tier × approved_SLA_multiplier
2. Reviewer never earns more for:
   - higher current-packet score
   - more "bad conduct" or severity
   - case acceptance or referral
   - retainer signing
   - settlement or recovery amount
3. Reviewer firm != recipient firm on one matter (strict conflict separation).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class ReviewerQATier(str, Enum):
    """Rolling QA tier established strictly from historical audited work."""
    PROVISIONAL = "PROVISIONAL"    # 1.0x baseline
    ESTABLISHED = "ESTABLISHED"    # 1.15x
    SENIOR_AUDITED = "SENIOR_AUDITED" # 1.30x
    MASTER_AUDITED = "MASTER_AUDITED" # 1.50x


QA_TIER_MULTIPLIERS: Dict[ReviewerQATier, float] = {
    ReviewerQATier.PROVISIONAL: 1.0,
    ReviewerQATier.ESTABLISHED: 1.15,
    ReviewerQATier.SENIOR_AUDITED: 1.30,
    ReviewerQATier.MASTER_AUDITED: 1.50,
}

# Standard rate in cents per page band
PAGE_BAND_RATES_CENTS: Dict[str, int] = {
    "1-50": 3000,      # $30.00
    "51-200": 7500,    # $75.00
    "201-500": 15000,  # $150.00
    "501-1000": 25000, # $250.00
    "1000+": 40000,    # $400.00
}


class AffiliateConflictError(ValueError):
    """Raised when an affiliate reviewer is conflicted or shares entity with recipient."""
    pass


class ReviewerIncentiveViolation(ValueError):
    """Raised when forbidden incentives attempt to modify reviewer compensation."""
    pass


@dataclass(frozen=True)
class ReviewerAuditProfile:
    """Historical audited record used to determine rolling QA tier."""
    reviewer_id: str
    reviewer_firm_id: str
    total_audited_reviews: int
    accuracy_rate: float
    citation_precision: float
    disposition_concordance: float
    current_qa_tier: ReviewerQATier

    def __post_init__(self) -> None:
        if not (0.0 <= self.accuracy_rate <= 1.0):
            raise ValueError("accuracy_rate must be between 0.0 and 1.0")
        if not (0.0 <= self.citation_precision <= 1.0):
            raise ValueError("citation_precision must be between 0.0 and 1.0")
        if not (0.0 <= self.disposition_concordance <= 1.0):
            raise ValueError("disposition_concordance must be between 0.0 and 1.0")


def evaluate_rolling_qa_tier(
    total_audited: int,
    accuracy: float,
    citation_precision: float,
    disposition_concordance: float,
) -> ReviewerQATier:
    """Determine rolling QA tier purely from past audit performance."""
    if total_audited >= 100 and accuracy >= 0.98 and citation_precision >= 0.98 and disposition_concordance >= 0.95:
        return ReviewerQATier.MASTER_AUDITED
    elif total_audited >= 40 and accuracy >= 0.95 and citation_precision >= 0.95:
        return ReviewerQATier.SENIOR_AUDITED
    elif total_audited >= 10 and accuracy >= 0.90:
        return ReviewerQATier.ESTABLISHED
    else:
        return ReviewerQATier.PROVISIONAL


def get_approved_sla_multiplier(turnaround_hours: int) -> float:
    """SLA multiplier approved in affiliate agreements."""
    if turnaround_hours <= 12:
        return 1.50
    elif turnaround_hours <= 24:
        return 1.25
    elif turnaround_hours <= 48:
        return 1.10
    else:
        return 1.00


@dataclass(frozen=True)
class ReviewFeeStatement:
    """Immutable fee statement for an affiliate review engagement."""
    matter_id: str
    reviewer_id: str
    reviewer_firm_id: str
    recipient_firm_id: str
    page_band: str
    page_band_rate_cents: int
    established_qa_tier: ReviewerQATier
    qa_tier_multiplier: float
    approved_sla_multiplier: float
    review_fee_cents: int
    audit_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matter_id": self.matter_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_firm_id": self.reviewer_firm_id,
            "recipient_firm_id": self.recipient_firm_id,
            "page_band": self.page_band,
            "page_band_rate_cents": self.page_band_rate_cents,
            "established_qa_tier": self.established_qa_tier.value,
            "qa_tier_multiplier": self.qa_tier_multiplier,
            "approved_sla_multiplier": self.approved_sla_multiplier,
            "review_fee_cents": self.review_fee_cents,
            "audit_notes": self.audit_notes,
        }


def calculate_affiliate_review_fee(
    matter_id: str,
    reviewer_profile: ReviewerAuditProfile,
    recipient_firm_id: str,
    page_band: str,
    turnaround_hours: int,
    *,
    forbidden_incentive_check: Optional[Dict[str, Any]] = None,
) -> ReviewFeeStatement:
    """Calculate affiliate reviewer fee ensuring all non-lawyer fee split and incentive rules hold.

    Formula:
      review_fee = page_band_rate × established_QA_tier × approved_SLA_multiplier

    Guarantees:
    - Reviewer firm != recipient firm
    - No variable payout on packet score, bad conduct, acceptance, retainers, or recovery.
    """
    # 1. Strict firm separation: Reviewer firm != recipient firm
    if reviewer_profile.reviewer_firm_id.strip() and recipient_firm_id.strip():
        if reviewer_profile.reviewer_firm_id.strip().lower() == recipient_firm_id.strip().lower():
            raise AffiliateConflictError(
                f"Conflict of Interest: Reviewer firm '{reviewer_profile.reviewer_firm_id}' "
                f"cannot be the same as recipient firm '{recipient_firm_id}' on matter '{matter_id}'."
            )

    # 2. Check forbidden incentive payloads
    if forbidden_incentive_check:
        for key in forbidden_incentive_check:
            k = key.lower()
            if any(
                bad in k
                for bad in [
                    "recovery",
                    "settlement",
                    "damages",
                    "contingency",
                    "retainer",
                    "acceptance",
                    "bad_conduct",
                    "juice",
                    "packet_score",
                    "case_value",
                ]
            ):
                raise ReviewerIncentiveViolation(
                    f"Forbidden reviewer incentive input: '{key}'. "
                    "Reviewer compensation must never depend on outcome, score, acceptance, or recovery."
                )

    if page_band not in PAGE_BAND_RATES_CENTS:
        raise ValueError(f"Invalid page band: {page_band}. Must be one of {list(PAGE_BAND_RATES_CENTS.keys())}")

    page_band_rate = PAGE_BAND_RATES_CENTS[page_band]
    qa_mult = QA_TIER_MULTIPLIERS[reviewer_profile.current_qa_tier]
    sla_mult = get_approved_sla_multiplier(turnaround_hours)

    raw_fee = Decimal(str(page_band_rate)) * Decimal(str(qa_mult)) * Decimal(str(sla_mult))
    fee_cents = int(raw_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return ReviewFeeStatement(
        matter_id=matter_id,
        reviewer_id=reviewer_profile.reviewer_id,
        reviewer_firm_id=reviewer_profile.reviewer_firm_id,
        recipient_firm_id=recipient_firm_id,
        page_band=page_band,
        page_band_rate_cents=page_band_rate,
        established_qa_tier=reviewer_profile.current_qa_tier,
        qa_tier_multiplier=qa_mult,
        approved_sla_multiplier=sla_mult,
        review_fee_cents=fee_cents,
        audit_notes="Formula: page_band_rate × established_QA_tier × approved_SLA_multiplier",
    )
