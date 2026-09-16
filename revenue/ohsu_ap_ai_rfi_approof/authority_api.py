"""Authority-bound public APProof compiler and verifier.

The reconciliation engine is intentionally kept byte-stable here.  This module
binds its compiler code to a private, code-owned all-false authority map so no
caller-mutable module binding participates in authority semantics.
"""
from __future__ import annotations

from types import FunctionType, MappingProxyType
from typing import Any

from . import common as _common
from . import engine as _engine

_AUTHORITY_ITEMS = (
    ("oracle_ebs_write_authorized", False),
    ("invoice_approval_authorized", False),
    ("payment_authorized", False),
    ("supplier_contact_authorized", False),
    ("buyer_submission_authorized", False),
    ("contract_award_claimed", False),
    ("revenue_claimed", False),
)

# Informational public view.  Compilation does not read this object.
AUTHORITY = MappingProxyType(dict(_AUTHORITY_ITEMS))


def _bind_authority_api(core_compile, canonicalizer, error_type):
    """Return compiler/verifier functions closed over private authority state."""
    authority = dict(_AUTHORITY_ITEMS)
    core_globals = dict(core_compile.__globals__)
    core_globals["AUTHORITY"] = authority
    bound_compile = FunctionType(
        core_compile.__code__,
        core_globals,
        name=core_compile.__name__,
        argdefs=core_compile.__defaults__,
        closure=core_compile.__closure__,
    )
    bound_compile.__kwdefaults__ = core_compile.__kwdefaults__

    def compile_packet(packet: Any) -> dict[str, Any]:
        return bound_compile(packet)

    def verify_projection(packet: Any, projection: Any) -> bool:
        if type(projection) is not dict:
            return False
        try:
            return canonicalizer(compile_packet(packet)) == canonicalizer(projection)
        except error_type:
            return False

    return compile_packet, verify_projection


compile_packet, verify_projection = _bind_authority_api(
    _engine.compile_packet,
    _common.canonical_json_bytes,
    _common.APProofError,
)

# Make every importable package-level authority name informational/immutable,
# and every normal engine entrypoint use the authority-bound functions.  A
# caller may rebind any of these module attributes later; the closures above do
# not consult those bindings.
_common.AUTHORITY = AUTHORITY
_engine.AUTHORITY = AUTHORITY
_engine.compile_packet = compile_packet
_engine.verify_projection = verify_projection

# Keep only the supported public surface discoverable from this module.
del _bind_authority_api, _AUTHORITY_ITEMS, FunctionType

__all__ = ["AUTHORITY", "compile_packet", "verify_projection"]
