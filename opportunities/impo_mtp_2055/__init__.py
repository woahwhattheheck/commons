"""Indianapolis MPO 2055 MTP bid-readiness compiler.

This package prepares an owner-review packet only. It never contacts the buyer,
registers a vendor, signs a form, commits pricing, or submits a proposal.
"""

from .engine import compile_packet, verify_packet
from .schema import OpportunityInputError, validate_input

__all__ = ["OpportunityInputError", "compile_packet", "validate_input", "verify_packet"]
