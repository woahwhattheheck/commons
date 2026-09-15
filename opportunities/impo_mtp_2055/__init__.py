"""Indianapolis MPO 2055 MTP bid-readiness compiler.

This package prepares non-authorizing owner-review packets. It never contacts the
buyer, registers a vendor, signs a form, commits pricing, submits a proposal, or
spends money. Current evaluation owns process UTC; explicit caller time remains
historical-integrity-only.
"""

from .engine import compile_current, compile_packet, verify_current, verify_packet
from .schema import OpportunityInputError, validate_input

__all__ = [
    "OpportunityInputError",
    "compile_current",
    "compile_packet",
    "validate_input",
    "verify_current",
    "verify_packet",
]
