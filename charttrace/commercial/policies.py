"""ChartTrace Commercial & Routing Policy Subsystem (Lane E).

Implements:
1. Routing Policy States:
   OFF | ADVERTISING_ONLY | QUALIFYING_PROVIDER_APPROVED | CERTIFIED_LRS | LICENSED_LEGAL_ENTITY.
   Default: OFF.
   Paid lead generation jurisdiction-disabled by default.

2. Allowed routing inputs:
   user selection, jurisdiction/practice category, licensure, geography, language,
   firm-declared capacity, conflict-clear state, neutral rotation.

3. Forbidden routing inputs:
   review signal, juice, damages, success probability, payment level, contingency,
   prior case acceptance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set

from charttrace.pricing.ledgers import (
    normalize_signal_key,
    reject_prohibited_payload,
)


class PolicyState(str, Enum):
    """Regulatory and compliance policy states for routing and commercial enablement."""
    OFF = "OFF"
    ADVERTISING_ONLY = "ADVERTISING_ONLY"
    QUALIFYING_PROVIDER_APPROVED = "QUALIFYING_PROVIDER_APPROVED"
    CERTIFIED_LRS = "CERTIFIED_LRS"  # Certified Lawyer Referral Service
    LICENSED_LEGAL_ENTITY = "LICENSED_LEGAL_ENTITY"  # Utah sandbox / AZ ABS / UK ABS


# Allowed routing input fields
ALLOWED_ROUTING_KEYS = frozenset(
    {
        "user_selected_firm_id",
        "jurisdiction",
        "practice_category",
        "attorney_licensure_state",
        "geography_zip",
        "geography_county",
        "geography_state",
        "language_preference",
        "firm_declared_capacity",
        "conflict_clear",
        "neutral_rotation_index",
        "requested_turnaround_hours",
    }
)

# Forbidden routing input fields
FORBIDDEN_ROUTING_KEYS = frozenset(
    {
        "review_signal",
        "review_priority",
        "juice",
        "damages",
        "damages_amount",
        "success_probability",
        "win_rate",
        "payment_level",
        "bid_amount",
        "lead_price",
        "contingency",
        "contingency_percentage",
        "prior_case_acceptance",
        "historical_conversion_rate",
        "severity",
        "success",
        "case_value",
        "firm_interest",
        "destination",
        "destination_firm",
        "destination_firm_id",
        "recovery",
        "expected_recovery",
        "legal_fees",
        "legal_fee",
    }
)


class RoutingPolicyViolation(ValueError):
    """Raised when routing inputs contain prohibited steering, fee-splitting, or merit signals."""
    pass


class PolicyStateDisabledError(RuntimeError):
    """Raised when an operation is attempted while routing or paid generation is OFF/disabled."""
    pass


@dataclass(frozen=True)
class FirmCandidate:
    """Firm profile available for neutral rotation / matched capacity."""
    firm_id: str
    firm_name: str
    jurisdictions: List[str]
    practice_categories: List[str]
    languages: List[str]
    declared_capacity: int  # available intake slots
    is_conflict_cleared: bool = True
    active_in_jurisdiction: bool = True


@dataclass(frozen=True)
class RoutingRequest:
    """Sanitized routing request container."""
    jurisdiction: str
    practice_category: str
    language: str = "en"
    user_selected_firm_id: Optional[str] = None
    geography_state: Optional[str] = None
    neutral_rotation_seed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        reject_prohibited_payload(self.metadata, FORBIDDEN_ROUTING_KEYS, RoutingPolicyViolation)
        extra = set(self.metadata) - ALLOWED_ROUTING_KEYS
        if extra:
            raise RoutingPolicyViolation(
                f"Unknown routing metadata is rejected: {sorted(extra)}."
            )
        for field_name in (
            "jurisdiction",
            "practice_category",
            "language",
            "user_selected_firm_id",
            "geography_state",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoutingPolicyViolation(f"{field_name} must be a nonempty canonical token.")
            normalized = normalize_signal_key(value)
            blocked = set(FORBIDDEN_ROUTING_KEYS) | {
                "patient",
                "mrn",
                "phi",
                "ssn",
                "dob",
                "hospital",
                "diagnosis",
                "medical",
            }
            for bad in blocked:
                token = normalize_signal_key(bad)
                if token and token in normalized:
                    raise RoutingPolicyViolation(
                        f"{field_name} may not carry prohibited or payload tokens."
                    )


@dataclass(frozen=True)
class RoutingDecision:
    """Outcome of routing execution."""
    policy_state: PolicyState
    routed_firm_id: Optional[str]
    routing_method: str  # "USER_SELECTED", "NEUTRAL_ROTATION", "NONE"
    is_paid_lead_generation: bool
    compliance_notes: str


APPROVED_ROTATION_STATES = frozenset(
    {
        PolicyState.QUALIFYING_PROVIDER_APPROVED,
        PolicyState.CERTIFIED_LRS,
        PolicyState.LICENSED_LEGAL_ENTITY,
    }
)


class RotationLedger:
    """Internal auditable rotation cursor. Request seeds cannot choose a recipient."""

    def __init__(self) -> None:
        self.cursor = 0
        self.history: List[Dict[str, Any]] = []

    def next_firm(self, eligible: Sequence[FirmCandidate]) -> FirmCandidate:
        ordered = sorted(eligible, key=lambda firm: firm.firm_id)
        selected = ordered[self.cursor % len(ordered)]
        self.history.append(
            {
                "cursor": self.cursor,
                "firm_id": selected.firm_id,
                "eligible": [firm.firm_id for firm in ordered],
            }
        )
        self.cursor += 1
        return selected


class RoutingEngine:
    """Compliant routing engine enforcing policy states and neutral allocation."""

    def __init__(
        self,
        policy_state: PolicyState = PolicyState.OFF,
        paid_lead_generation_enabled_jurisdictions: Optional[Set[str]] = None,
        rotation_ledger: Optional[RotationLedger] = None,
    ):
        self.policy_state = policy_state
        self.paid_lead_generation_enabled_jurisdictions: Set[str] = (
            set(paid_lead_generation_enabled_jurisdictions)
            if paid_lead_generation_enabled_jurisdictions is not None
            else set()
        )
        self.rotation_ledger = rotation_ledger or RotationLedger()

    def route_matter(
        self,
        request: RoutingRequest,
        candidates: Sequence[FirmCandidate],
    ) -> RoutingDecision:
        """Route a matter according to current policy state and neutral rules."""
        is_paid_lead_gen = request.jurisdiction in self.paid_lead_generation_enabled_jurisdictions
        if is_paid_lead_gen and self.policy_state not in APPROVED_ROTATION_STATES:
            raise RoutingPolicyViolation(
                f"Paid lead generation is prohibited under policy state {self.policy_state.value} "
                f"in jurisdiction {request.jurisdiction}."
            )

        if self.policy_state in {PolicyState.OFF, PolicyState.ADVERTISING_ONLY}:
            return RoutingDecision(
                policy_state=self.policy_state,
                routed_firm_id=None,
                routing_method="NONE",
                is_paid_lead_generation=False,
                compliance_notes=(
                    "ADVERTISING_ONLY returns no automatic destination."
                    if self.policy_state is PolicyState.ADVERTISING_ONLY
                    else "Routing is globally OFF. No matches provided."
                ),
            )

        if self.policy_state not in APPROVED_ROTATION_STATES:
            return RoutingDecision(
                policy_state=self.policy_state,
                routed_firm_id=None,
                routing_method="NONE",
                is_paid_lead_generation=False,
                compliance_notes="Rotation is available only in approved policy states.",
            )

        if request.user_selected_firm_id:
            matching = [
                firm
                for firm in candidates
                if firm.firm_id == request.user_selected_firm_id
                and request.jurisdiction in firm.jurisdictions
                and request.practice_category in firm.practice_categories
                and firm.is_conflict_cleared
            ]
            if matching:
                return RoutingDecision(
                    policy_state=self.policy_state,
                    routed_firm_id=matching[0].firm_id,
                    routing_method="USER_SELECTED",
                    is_paid_lead_generation=is_paid_lead_gen,
                    compliance_notes="Direct user selection honored.",
                )

        eligible = [
            firm
            for firm in candidates
            if request.jurisdiction in firm.jurisdictions
            and request.practice_category in firm.practice_categories
            and (request.language in firm.languages or not firm.languages)
            and firm.declared_capacity > 0
            and firm.is_conflict_cleared
            and firm.active_in_jurisdiction
        ]

        if not eligible:
            return RoutingDecision(
                policy_state=self.policy_state,
                routed_firm_id=None,
                routing_method="NONE",
                is_paid_lead_generation=is_paid_lead_gen,
                compliance_notes="No eligible, conflict-cleared firms with declared capacity.",
            )

        selected_firm = self.rotation_ledger.next_firm(eligible)
        return RoutingDecision(
            policy_state=self.policy_state,
            routed_firm_id=selected_firm.firm_id,
            routing_method="NEUTRAL_ROTATION",
            is_paid_lead_generation=is_paid_lead_gen,
            compliance_notes=(
                f"Internal ledger selected firm {selected_firm.firm_id} "
                f"from {len(eligible)} eligible candidates."
            ),
        )
