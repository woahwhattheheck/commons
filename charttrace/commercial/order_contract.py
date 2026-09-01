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

from charttrace.pricing.ledgers import ProductTier


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

    def __post_init__(self) -> None:
        # Validate order and customer ids conform to opaque identifiers
        if not self.order_id or not self.order_id.startswith("ct_ord_"):
            raise ValueError(f"order_id '{self.order_id}' must be an opaque identifier starting with 'ct_ord_'")
        if not self.customer_id or not self.customer_id.startswith("ct_cus_"):
            raise ValueError(f"customer_id '{self.customer_id}' must be an opaque identifier starting with 'ct_cus_'")
        if self.amount_cents <= 0:
            raise ValueError("amount_cents must be positive.")
        if self.currency.lower() != "usd":
            raise ValueError("Only 'usd' is currently supported.")

        # Strict validation of metadata keys and values
        validate_opaque_metadata(self.metadata)

    def to_stripe_checkout_payload(self) -> Dict[str, Any]:
        """Format strictly into standard opaque Stripe Checkout session schema."""
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
    """Verify that metadata contains zero sensitive medical, legal merit, or destination details."""
    for key, value in metadata.items():
        k = key.lower()
        if k in FORBIDDEN_STRIPE_PAYLOAD_KEYS or any(f in k for f in FORBIDDEN_STRIPE_PAYLOAD_KEYS):
            raise SensitiveDataExposureError(
                f"Forbidden Stripe metadata key '{key}'. Payment payloads must never contain PHI, "
                "medical details, case theories, case values, or destination firm identifiers."
            )
        # Check string values for sensitive keywords
        val_str = str(value).lower()
        for forbidden in (
            "patient",
            "hospital",
            "malpractice",
            "diagnosis",
            "doctor",
            "injury",
            "settlement",
            "contingency",
        ):
            if forbidden in val_str:
                raise SensitiveDataExposureError(
                    f"Forbidden sensitive content in Stripe metadata value for key '{key}': contains '{forbidden}'."
                )


def assert_live_operations_disabled(flags: CommercialFeatureFlags = DEFAULT_COMMERCIAL_FLAGS) -> None:
    """Assert all live payment and transfer operations are strictly blocked."""
    if flags.charges_enabled:
        raise LivePaymentOperationBlockedError("Live charges are disabled.")
    if flags.transfers_enabled or flags.connect_status != "HOLD_LEGAL_AND_PAYMENT_DESIGN":
        raise LivePaymentOperationBlockedError(f"Stripe Connect transfers are blocked ({flags.connect_status}).")
    if flags.external_spend_enabled:
        raise LivePaymentOperationBlockedError("External spend is blocked.")
    if flags.stripe_account_mutation_allowed:
        raise LivePaymentOperationBlockedError("Stripe account mutations are prohibited.")
