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
        # Verify no forbidden keys exist in metadata
        for k in self.metadata:
            if k.lower() in FORBIDDEN_ROUTING_KEYS:
                raise RoutingPolicyViolation(
                    f"Forbidden routing input: '{k}'. "
                    "Routing may not consider review signals, juice, damages, probabilities, bids, or conversion history."
                )


@dataclass(frozen=True)
class RoutingDecision:
    """Outcome of routing execution."""
    policy_state: PolicyState
    routed_firm_id: Optional[str]
    routing_method: str  # "USER_SELECTED", "NEUTRAL_ROTATION", "NONE"
    is_paid_lead_generation: bool
    compliance_notes: str


class RoutingEngine:
    """Compliant routing engine enforcing policy states and neutral allocation."""

    def __init__(
        self,
        policy_state: PolicyState = PolicyState.OFF,
        paid_lead_generation_enabled_jurisdictions: Optional[Set[str]] = None,
    ):
        self.policy_state = policy_state
        # Paid lead generation disabled by default in ALL jurisdictions
        self.paid_lead_generation_enabled_jurisdictions: Set[str] = (
            set(paid_lead_generation_enabled_jurisdictions)
            if paid_lead_generation_enabled_jurisdictions is not None
            else set()
        )

    def route_matter(
        self,
        request: RoutingRequest,
        candidates: Sequence[FirmCandidate],
    ) -> RoutingDecision:
        """Route a matter according to current policy state and neutral rules."""
        # 1. Check policy state
        if self.policy_state == PolicyState.OFF:
            return RoutingDecision(
                policy_state=PolicyState.OFF,
                routed_firm_id=None,
                routing_method="NONE",
                is_paid_lead_generation=False,
                compliance_notes="Routing is globally OFF. No matches provided.",
            )

        # 2. Check paid lead gen guard
        is_paid_lead_gen = request.jurisdiction in self.paid_lead_generation_enabled_jurisdictions
        if is_paid_lead_gen and self.policy_state not in (
            PolicyState.QUALIFYING_PROVIDER_APPROVED,
            PolicyState.CERTIFIED_LRS,
            PolicyState.LICENSED_LEGAL_ENTITY,
        ):
            raise RoutingPolicyViolation(
                f"Paid lead generation is prohibited under policy state {self.policy_state.value} "
                f"in jurisdiction {request.jurisdiction}."
            )

        # 3. User explicit selection takes absolute priority if eligible and conflict cleared
        if request.user_selected_firm_id:
            matching = [
                f for f in candidates
                if f.firm_id == request.user_selected_firm_id
                and request.jurisdiction in f.jurisdictions
                and request.practice_category in f.practice_categories
                and f.is_conflict_cleared
            ]
            if matching:
                return RoutingDecision(
                    policy_state=self.policy_state,
                    routed_firm_id=matching[0].firm_id,
                    routing_method="USER_SELECTED",
                    is_paid_lead_generation=is_paid_lead_gen,
                    compliance_notes="Direct user selection honored.",
                )

        # 4. Filter eligible candidates strictly by permitted criteria:
        # jurisdiction, practice, language, capacity > 0, conflict clear
        eligible = [
            f for f in candidates
            if request.jurisdiction in f.jurisdictions
            and request.practice_category in f.practice_categories
            and (request.language in f.languages or not f.languages)
            and f.declared_capacity > 0
            and f.is_conflict_cleared
            and f.active_in_jurisdiction
        ]

        if not eligible:
            return RoutingDecision(
                policy_state=self.policy_state,
                routed_firm_id=None,
                routing_method="NONE",
                is_paid_lead_generation=is_paid_lead_gen,
                compliance_notes="No eligible, conflict-cleared firms with declared capacity.",
            )

        # 5. Neutral rotation (deterministic modulo on sorted firm_ids)
        sorted_eligible = sorted(eligible, key=lambda f: f.firm_id)
        selected_idx = request.neutral_rotation_seed % len(sorted_eligible)
        selected_firm = sorted_eligible[selected_idx]

        return RoutingDecision(
            policy_state=self.policy_state,
            routed_firm_id=selected_firm.firm_id,
            routing_method="NEUTRAL_ROTATION",
            is_paid_lead_generation=is_paid_lead_gen,
            compliance_notes=f"Neutral rotation selected firm {selected_firm.firm_id} from {len(sorted_eligible)} eligible candidates.",
        )
