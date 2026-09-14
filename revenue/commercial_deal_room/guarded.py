from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from revenue.outbound_connector_lease.key import SUPPORTED_REPLY_PROVIDERS

from . import engine as _engine

ContractError = _engine.ContractError
VERSION = _engine.VERSION
canonical_json = _engine.canonical_json
render_markdown = _engine.render_markdown
sha256_hex = _engine.sha256_hex

# Provider identity is one cross-revenue seam. Reuse the registry that already
# protects outbound reply leases instead of minting a second vocabulary that can
# drift and reopen alias splits later.
CANONICAL_MESSAGE_PROVIDERS = SUPPORTED_REPLY_PROVIDERS

_MESSAGE_EVENT_TYPES = frozenset(
    {
        "OFFER_SENT",
        "BUYER_INTEREST",
        "PROPOSAL_SENT",
        "BUYER_ACCEPTED",
        "BUYER_REJECTED",
        "PAYMENT_REQUEST_SENT",
        "FULFILLMENT_SENT",
        "BUYER_FULFILLMENT_ACCEPTED",
    }
)

# Capture the core normalizer before installing the package-level guard below.
# Normal Python imports execute commercial_deal_room.__init__ before exposing a
# submodule, so patching this one normalization seam also protects callers that
# import commercial_deal_room.engine.compile_board directly.
_CORE_NORMALIZE_PACKET = _engine.normalize_packet


def validate_message_providers(packet: Any) -> None:
    """Reject non-canonical provider spellings before lifecycle compilation.

    Structural packet validation remains owned by engine.normalize_packet().
    This guard only acts once it can unambiguously identify a message-bearing
    event and its provider value.
    """

    if not isinstance(packet, Mapping):
        return
    events = packet.get("events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return

    for index, event in enumerate(events):
        if not isinstance(event, Mapping) or event.get("type") not in _MESSAGE_EVENT_TYPES:
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping) or "provider" not in payload:
            continue
        provider = payload["provider"]
        if not isinstance(provider, str) or provider not in CANONICAL_MESSAGE_PROVIDERS:
            raise ContractError(
                f"event[{index}].payload.provider must be a canonical provider ID: "
                f"{sorted(CANONICAL_MESSAGE_PROVIDERS)}"
            )


def normalize_packet(packet: Any):
    validate_message_providers(packet)
    return _CORE_NORMALIZE_PACKET(packet)


# Close the direct-engine import seam without rewriting the large v1 compiler.
# Existing compile_board()/verify_board() resolve normalize_packet from their
# module globals at call time, so canonical packets preserve their v1 behavior
# while every normal package/submodule entrypoint shares this pre-normalization
# guard.
_engine.normalize_packet = normalize_packet


def compile_board(packet: Any, *, now: Optional[datetime] = None):
    validate_message_providers(packet)
    return _engine.compile_board(packet, now=now)


def verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
    validate_message_providers(packet)
    return _engine.verify_board(packet, board, now=now)
