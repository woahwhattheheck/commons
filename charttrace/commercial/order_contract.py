"""ChartTrace Stripe-Shaped Opaque Order Contract & Payment Design (Lane E).

Guarantees strict data isolation and commercial safety:
1. Stripe-shaped opaque order contract ONLY contains:
   - order_id
   - customer_id
   - product_tier
   - non-sensitive workload bands (e.g. page_band, turnaround_hours, amount_cents, currency)

2. FORBIDDEN in Stripe fields:
   - patient names
   - medical conditions / diagnoses
   - healthcare providers
   - filenames
   - hypotheses / theories
   - juice / merits
   - case value / damages
   - destination firm
   - source text / record excerpts

3. Workbench contains:
   - NO Stripe secret keys (api_key)
   - NO payment forms
   - NO webhooks
   - NO network exceptions

4. System flags:
   Live routing = OFF
   Connect = HOLD_LEGAL_AND_PAYMENT_DESIGN
   Percentage fee = OFF
   Charges = OFF
   Products = OFF
   Subscriptions = OFF
   Transfers = OFF
   Payouts = OFF
   Tax = OFF
   Spend = OFF
   No Stripe account mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set

from charttrace.pricing.ledgers import (
    ALLOWED_TURNAROUND_HOURS,
    FORBIDDEN_ID_TOKENS,
    PAGE_BANDS,
    ProductTier,
    ReviewWorkScore,
    normalize_signal_key,
    reject_prohibited_payload,
    require_opaque_packet_id,
)


# Forbidden sensitive tokens/patterns in opaque order contracts
FORBIDDEN_STRIPE_PAYLOAD_KEYS = frozenset(
    {
        "patient",
        "patient_name",
        "patient_dob",
        "patient_ssn",
        "condition",
        "diagnosis",
        "provider",
        "provider_name",
        "doctor",
        "hospital",
        "filename",
        "filenames",
        "file_name",
        "hypothesis",
        "hypotheses",
        "theory",
        "juice",
        "case_value",
        "damages",
        "recovery",
        "destination_firm",
        "destination_firm_id",
        "source_text",
        "record_text",
        "medical_record",
        "phi",
        "legal_fees",
        "legal_fee",
        "success",
        "destination",
    }
)


class SensitiveDataExposureError(ValueError):
    """Raised when PHI, case merits, or sensitive legal/medical details appear in payment metadata."""
    pass


class LivePaymentOperationBlockedError(RuntimeError):
    """Raised when any live payment, charge, transfer, payout, or mutation is attempted."""
    pass


@dataclass(frozen=True)
class CommercialFeatureFlags:
    """Explicit state of all commercial and payment subsystem capabilities."""
    live_routing_enabled: bool = False
    connect_status: str = "HOLD_LEGAL_AND_PAYMENT_DESIGN"
    percentage_fee_enabled: bool = False
    charges_enabled: bool = False
    products_enabled: bool = False
    subscriptions_enabled: bool = False
    transfers_enabled: bool = False
    payouts_enabled: bool = False
    tax_automation_enabled: bool = False
    external_spend_enabled: bool = False
    stripe_account_mutation_allowed: bool = False


DEFAULT_COMMERCIAL_FLAGS = CommercialFeatureFlags()
ALLOWED_METADATA_KEYS = frozenset({"source_system", "work_score_id", "packet_id"})
OPAQUE_ORDER_ID_RE = re.compile(r"^ct_ord_[a-f0-9]{4,32}$")
OPAQUE_CUSTOMER_ID_RE = re.compile(r"^ct_cus_[a-f0-9]{4,32}$")
OPAQUE_META_VALUE_RE = re.compile(r"^[a-z0-9_]{1,64}$")


@dataclass(frozen=True)
class OpaqueOrderContract:
    """Stripe-shaped opaque order contract containing ONLY safe, non-sensitive workload indicators."""
    order_id: str
    customer_id: str
    product_tier: ProductTier
    page_band: str
    turnaround_hours: int
    amount_cents: int
    currency: str = "usd"
    metadata: Dict[str, str] = field(default_factory=dict)
    work_score: Optional[ReviewWorkScore] = None

    def __post_init__(self) -> None:
        if not OPAQUE_ORDER_ID_RE.match(self.order_id):
            raise ValueError("order_id must be an opaque hex ct_ord_ token with no payload data.")
        if not OPAQUE_CUSTOMER_ID_RE.match(self.customer_id):
            raise ValueError("customer_id must be an opaque hex ct_cus_ token with no payload data.")
        combined = normalize_signal_key(self.order_id + self.customer_id)
        for token in FORBIDDEN_ID_TOKENS:
            if token and token in combined:
                raise ValueError("Opaque identifiers may not carry payload tokens.")
        if self.page_band not in PAGE_BANDS:
            raise ValueError(f"page_band must be one of {PAGE_BANDS}.")
        if self.turnaround_hours not in ALLOWED_TURNAROUND_HOURS:
            raise ValueError("turnaround_hours must be an enumerated SLA band.")
        if self.amount_cents <= 0:
            raise ValueError("amount_cents must be positive.")
        if self.currency.lower() != "usd":
            raise ValueError("Only 'usd' is currently supported.")
        if self.work_score is None:
            raise ValueError("Order amount must bind to an immutable work-score receipt.")
        if self.amount_cents != self.work_score.calculated_price_cents:
            raise ValueError("amount_cents must equal the bound work-score receipt.")
        if self.page_band != self.work_score.page_band:
            raise ValueError("page_band must equal the bound work-score receipt.")
        if self.product_tier != self.work_score.product_tier:
            raise ValueError("product_tier must equal the bound work-score receipt.")
        if self.turnaround_hours != self.work_score.metrics.turnaround_hours:
            raise ValueError("turnaround_hours must equal the bound work-score receipt.")
        validate_opaque_metadata(self.metadata)

    def to_stripe_checkout_payload(
        self,
        flags: CommercialFeatureFlags = DEFAULT_COMMERCIAL_FLAGS,
    ) -> Dict[str, Any]:
        """Format strictly into standard opaque Stripe Checkout session schema while asserting live-ops OFF."""
        assert_live_operations_disabled(flags)
        return {
            "client_reference_id": self.order_id,
            "customer": self.customer_id,
            "line_items": [
                {
                    "price_data": {
                        "currency": self.currency.lower(),
                        "product_data": {
                            "name": f"ChartTrace {self.product_tier.value} Processing (Band {self.page_band})",
                            "metadata": {
                                "order_id": self.order_id,
                                "tier": self.product_tier.value,
                                "page_band": self.page_band,
                            },
                        },
                        "unit_amount": self.amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            "metadata": {
                "order_id": self.order_id,
                "tier": self.product_tier.value,
                "page_band": self.page_band,
                "turnaround_hours": str(self.turnaround_hours),
                **self.metadata,
            },
            "mode": "payment",
        }


def validate_opaque_metadata(metadata: Dict[str, Any]) -> None:
    """Allowlisted metadata only. Nested/aliased/suffixed prohibited keys fail."""
    if not isinstance(metadata, dict):
        raise SensitiveDataExposureError("Metadata must be an object.")
    reject_prohibited_payload(metadata, FORBIDDEN_STRIPE_PAYLOAD_KEYS, SensitiveDataExposureError)
    extra = set(metadata) - ALLOWED_METADATA_KEYS
    if extra:
        raise SensitiveDataExposureError(
            f"Unknown metadata keys are rejected: {sorted(extra)}."
        )
    for key, value in metadata.items():
        if not isinstance(value, str) or not OPAQUE_META_VALUE_RE.match(value):
            raise SensitiveDataExposureError(f"Metadata {key!r} must be a short opaque token.")
        normalized = normalize_signal_key(value)
        for token in FORBIDDEN_ID_TOKENS:
            if token and token in normalized:
                raise SensitiveDataExposureError(
                    f"Forbidden sensitive content in Stripe metadata value for key '{key}'."
                )
        if key in {"packet_id", "work_score_id"}:
            require_opaque_packet_id(value, key)


def assert_live_operations_disabled(flags: CommercialFeatureFlags = DEFAULT_COMMERCIAL_FLAGS) -> None:
    """Assert all live payment and transfer operations are strictly blocked."""
    if flags.live_routing_enabled:
        raise LivePaymentOperationBlockedError("Live routing remains OFF.")
    if flags.charges_enabled:
        raise LivePaymentOperationBlockedError("Live charges are disabled.")
    if flags.products_enabled:
        raise LivePaymentOperationBlockedError("Live products remain OFF.")
    if flags.subscriptions_enabled:
        raise LivePaymentOperationBlockedError("Live subscriptions remain OFF.")
    if flags.transfers_enabled or flags.connect_status != "HOLD_LEGAL_AND_PAYMENT_DESIGN":
        raise LivePaymentOperationBlockedError(f"Stripe Connect transfers are blocked ({flags.connect_status}).")
    if flags.payouts_enabled:
        raise LivePaymentOperationBlockedError("Live payouts remain OFF.")
    if flags.tax_automation_enabled:
        raise LivePaymentOperationBlockedError("Live tax remains OFF.")
    if flags.external_spend_enabled:
        raise LivePaymentOperationBlockedError("External spend is blocked.")
    if flags.stripe_account_mutation_allowed:
        raise LivePaymentOperationBlockedError("Stripe account mutations are prohibited.")
    if flags.percentage_fee_enabled:
        raise LivePaymentOperationBlockedError("Percentage fees remain OFF.")
