from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from . import engine as _engine

ContractError = _engine.ContractError
VERSION = _engine.VERSION
canonical_json = _engine.canonical_json
render_markdown = _engine.render_markdown
sha256_hex = _engine.sha256_hex

# Keep this vocabulary aligned with the canonical provider IDs already used by
# Commons outbound-provider custody. Adapters may map provider-specific aliases
# to one of these values before constructing a Deal Room packet; the Deal Room
# itself never guesses aliases because that would make evidence identity depend
# on caller spelling.
CANONICAL_MESSAGE_PROVIDERS = frozenset({"devpost", "gmail", "github", "slack", "web-form"})

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


def validate_message_providers(packet: Any) -> None:
    """Reject non-canonical provider spellings before lifecycle compilation.

    This is deliberately a narrow pre-normalization guard. Structural packet
    validation remains owned by engine.normalize_packet(), so malformed objects
    still receive the engine's existing errors. The guard only acts once it can
    unambiguously identify a message-bearing event and its provider value.
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
        if provider not in CANONICAL_MESSAGE_PROVIDERS:
            raise ContractError(
                f"event[{index}].payload.provider must be a canonical provider ID: "
                f"{sorted(CANONICAL_MESSAGE_PROVIDERS)}"
            )


def normalize_packet(packet: Any):
    validate_message_providers(packet)
    return _engine.normalize_packet(packet)


def compile_board(packet: Any, *, now: Optional[datetime] = None):
    validate_message_providers(packet)
    return _engine.compile_board(packet, now=now)


def verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
    validate_message_providers(packet)
    return _engine.verify_board(packet, board, now=now)
