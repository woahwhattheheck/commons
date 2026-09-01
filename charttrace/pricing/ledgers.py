"""ChartTrace Pricing Subsystem (Lane E - Commercial Guards).

Enforces strict separation between attorney attention prioritization (REVIEW_PRIORITY)
and workload-based service pricing (REVIEW_WORK_SCORE).

CRITICAL INVARIANTS:
1. REVIEW_PRIORITY is NEVER a probability, case value, damage estimate, or price.
2. REVIEW_WORK_SCORE is strictly derived from disclosed workload features.
3. Current-case signal severity, damages, expected recovery, success probability,
   firm interest, destination firm, or affiliate acceptance MUST NEVER change
   customer price, reviewer pay, routing, evidence, or presentation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class ProductTier(str, Enum):
    """Customer product tiers priced strictly by disclosed work."""
    INDEXED = "INDEXED"
    INVESTIGATIVE = "INVESTIGATIVE"
    COUNSEL_READY = "COUNSEL_READY"


# Explicitly forbidden keys across pricing and priority calculations
FORBIDDEN_ECONOMIC_SIGNAL_KEYS = frozenset(
    {
        "signal_severity",
        "severity",
        "damages",
        "damages_amount",
        "expected_recovery",
        "recovery_estimate",
        "case_value",
        "success_probability",
        "win_probability",
        "firm_interest",
        "destination_firm",
        "destination_firm_id",
        "affiliate_acceptance",
        "juice",
        "bad_conduct_score",
        "contingency",
        "contingency_percentage",
        "payment_level",
        "success",
        "destination",
        "recovery",
        "legal_fees",
        "legal_fee",
    }
)


class EconomicIsolationViolation(ValueError):
    """Raised when forbidden case-signal or economic indicators attempt to influence pricing or review priority."""
    pass


def assert_clean_workload_inputs(data: Dict[str, Any]) -> None:
    """Validate that input payloads do not contain forbidden case-value/probability/steering fields."""
    found_forbidden = [k for k in data.keys() if k.lower() in FORBIDDEN_ECONOMIC_SIGNAL_KEYS]
    if found_forbidden:
        raise EconomicIsolationViolation(
            f"Economic isolation violation: Payload contains forbidden keys: {sorted(found_forbidden)}. "
            "Case value, recovery, success probability, severity, and destination firm must never influence pricing or priority."
        )


@dataclass(frozen=True)
class ReviewPriorityScore:
    """Ledger 1: Orders lawyer attention.

    Ordered from:
    - evidence_support: strength and citation grounding of evidence
    - materiality_if_confirmed: legal significance if fact holds
    - temporal_linkage: proximity and sequence in care timeline
    - novelty: newly surfaced lead or anomaly
    - counterevidence: contradictory records or mitigating factors
    - completeness: completeness of documentation around event
    - deadline_investigation_urgency: statute/filing/spoliation timeline urgency

    CRITICAL INVARIANT:
    This score is NOT a probability, case value, recovery estimate, or price.
    """
    item_id: str
    evidence_support: float
    materiality_if_confirmed: float
    temporal_linkage: float
    novelty: float
    counterevidence: float
    completeness: float
    deadline_urgency: float
    composite_priority: float
    priority_band: str  # e.g., "URGENT", "HIGH", "STANDARD", "ROUTINE"
    notes: str = ""

    def __post_init__(self) -> None:
        for attr in (
            "evidence_support",
            "materiality_if_confirmed",
            "temporal_linkage",
            "novelty",
            "counterevidence",
            "completeness",
            "deadline_urgency",
        ):
            val = getattr(self, attr)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"Priority metric {attr}={val} must be in [0.0, 1.0]")
        if not (0.0 <= self.composite_priority <= 100.0):
            raise ValueError(f"composite_priority={self.composite_priority} must be in [0.0, 100.0]")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_review_priority(
    item_id: str,
    *,
    evidence_support: float,
    materiality_if_confirmed: float,
    temporal_linkage: float,
    novelty: float,
    counterevidence: float,
    completeness: float,
    deadline_urgency: float,
    notes: str = "",
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> ReviewPriorityScore:
    """Calculate REVIEW_PRIORITY ledger entry for ordering attorney attention.

    Guarantees no economic or probability factors enter the computation.
    """
    if extra_metadata:
        assert_clean_workload_inputs(extra_metadata)

    # Weighted combination of attention drivers (0.0 to 100.0)
    # Higher counterevidence also increases need for immediate lawyer examination
    raw_composite = (
        evidence_support * 25.0
        + materiality_if_confirmed * 20.0
        + deadline_urgency * 20.0
        + counterevidence * 15.0
        + temporal_linkage * 10.0
        + novelty * 5.0
        + completeness * 5.0
    )
    composite = round(min(100.0, max(0.0, raw_composite)), 2)

    if composite >= 75.0:
        band = "URGENT"
    elif composite >= 55.0:
        band = "HIGH"
    elif composite >= 35.0:
        band = "STANDARD"
    else:
        band = "ROUTINE"

    return ReviewPriorityScore(
        item_id=item_id,
        evidence_support=round(evidence_support, 4),
        materiality_if_confirmed=round(materiality_if_confirmed, 4),
        temporal_linkage=round(temporal_linkage, 4),
        novelty=round(novelty, 4),
        counterevidence=round(counterevidence, 4),
        completeness=round(completeness, 4),
        deadline_urgency=round(deadline_urgency, 4),
        composite_priority=composite,
        priority_band=band,
        notes=notes,
    )


@dataclass(frozen=True)
class WorkloadMetrics:
    """Disclosed workload characteristics that legitimately determine operational processing cost."""
    unique_pages: int
    file_count: int
    ocr_repair_page_count: int = 0
    source_provider_count: int = 1
    date_span_days: int = 1
    specialties_count: int = 1
    language_count: int = 1
    duplicate_conflict_pairs: int = 0
    jurisdiction_pack_count: int = 1
    turnaround_hours: int = 72  # standard 72h SLA
    estimated_human_qa_minutes: int = 30
    specialist_review_required: bool = False

    def __post_init__(self) -> None:
        if self.unique_pages < 0 or self.file_count < 0:
            raise ValueError("Pages and file counts cannot be negative.")
        if self.turnaround_hours <= 0:
            raise ValueError("Turnaround hours must be positive.")


@dataclass(frozen=True)
class ReviewWorkScore:
    """Ledger 2: Workload quantification used for service pricing.

    Prices service exclusively from disclosed workload:
    - unique pages/files
    - OCR repair volume
    - source/provider count
    - date span
    - specialties
    - language diversity
    - duplicate/conflict reconciliation
    - jurisdiction packs
    - turnaround SLA
    - human-QA time
    - specialist review
    """
    packet_id: str
    product_tier: ProductTier
    metrics: WorkloadMetrics
    base_work_units: float
    complexity_multiplier: float
    final_work_score: float
    page_band: str  # e.g. "1-50", "51-200", "201-500", "501-1000", "1000+"
    turnaround_multiplier: float
    calculated_price_cents: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "product_tier": self.product_tier.value,
            "metrics": asdict(self.metrics),
            "base_work_units": self.base_work_units,
            "complexity_multiplier": self.complexity_multiplier,
            "final_work_score": self.final_work_score,
            "page_band": self.page_band,
            "turnaround_multiplier": self.turnaround_multiplier,
            "calculated_price_cents": self.calculated_price_cents,
        }


# Base price per page in cents by product tier
TIER_BASE_PAGE_RATE_CENTS: Dict[ProductTier, int] = {
    ProductTier.INDEXED: 10,        # $0.10 / page
    ProductTier.INVESTIGATIVE: 35,  # $0.35 / page
    ProductTier.COUNSEL_READY: 75,  # $0.75 / page
}

TIER_BASE_FEE_CENTS: Dict[ProductTier, int] = {
    ProductTier.INDEXED: 2500,        # $25.00
    ProductTier.INVESTIGATIVE: 7500,  # $75.00
    ProductTier.COUNSEL_READY: 15000, # $150.00
}


def get_page_band(pages: int) -> str:
    """Categorize page volume into standardized non-sensitive workload bands."""
    if pages <= 50:
        return "1-50"
    elif pages <= 200:
        return "51-200"
    elif pages <= 500:
        return "201-500"
    elif pages <= 1000:
        return "501-1000"
    else:
        return "1000+"


def calculate_turnaround_multiplier(turnaround_hours: int) -> float:
    """Turnaround speed multiplier based strictly on processing SLA."""
    if turnaround_hours <= 12:
        return 2.0
    elif turnaround_hours <= 24:
        return 1.5
    elif turnaround_hours <= 48:
        return 1.25
    else:
        return 1.0


def calculate_review_work_score(
    packet_id: str,
    tier: ProductTier,
    metrics: WorkloadMetrics,
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> ReviewWorkScore:
    """Calculate REVIEW_WORK_SCORE ledger entry and price service.

    Prices service exclusively from disclosed workload metrics.
    Enforces that case merits, damages, or destinations NEVER affect price.
    """
    if extra_metadata:
        assert_clean_workload_inputs(extra_metadata)

    # 1. Base work units from page count + file count + OCR repair
    base_units = (
        float(metrics.unique_pages)
        + float(metrics.file_count * 2.0)
        + float(metrics.ocr_repair_page_count * 0.5)
    )

    # 2. Complexity multiplier strictly from operational factors
    provider_factor = max(1.0, 1.0 + (metrics.source_provider_count - 1) * 0.05)
    specialty_factor = max(1.0, 1.0 + (metrics.specialties_count - 1) * 0.08)
    language_factor = max(1.0, 1.0 + (metrics.language_count - 1) * 0.15)
    conflict_factor = max(1.0, 1.0 + (metrics.duplicate_conflict_pairs * 0.02))
    jurisdiction_factor = max(1.0, 1.0 + (metrics.jurisdiction_pack_count - 1) * 0.10)
    specialist_factor = 1.25 if metrics.specialist_review_required else 1.0

    complexity = round(
        provider_factor
        * specialty_factor
        * language_factor
        * conflict_factor
        * jurisdiction_factor
        * specialist_factor,
        4,
    )

    turnaround_mult = calculate_turnaround_multiplier(metrics.turnaround_hours)
    final_score = round(base_units * complexity * turnaround_mult, 2)

    # 3. Deterministic price calculation
    base_fee = TIER_BASE_FEE_CENTS[tier]
    page_rate = TIER_BASE_PAGE_RATE_CENTS[tier]
    page_cost = metrics.unique_pages * page_rate
    ocr_cost = metrics.ocr_repair_page_count * 5  # 5 cents per OCR repair page
    qa_cost = metrics.estimated_human_qa_minutes * 50  # 50 cents per QA min

    raw_price = (base_fee + page_cost + ocr_cost + qa_cost) * complexity * turnaround_mult
    price_cents = int(Decimal(str(raw_price)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return ReviewWorkScore(
        packet_id=packet_id,
        product_tier=tier,
        metrics=metrics,
        base_work_units=round(base_units, 2),
        complexity_multiplier=complexity,
        turnaround_multiplier=turnaround_mult,
        final_work_score=final_score,
        page_band=get_page_band(metrics.unique_pages),
        calculated_price_cents=price_cents,
    )
