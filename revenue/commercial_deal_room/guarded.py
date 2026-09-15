from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Optional

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

# Capture core entrypoints before installing package-level guards. Normal Python
# imports execute commercial_deal_room.__init__ before exposing a submodule, so
# patching these seams also protects callers that import engine directly.
_CORE_NORMALIZE_PACKET = _engine.normalize_packet
_CORE_VERIFY_BOARD = _engine.verify_board


def _detach(value: Any, *, path: str = "packet") -> Any:
    """Capture caller-owned containers once into plain dict/list values.

    The compiler intentionally accepts Mapping/Sequence inputs. A preflight
    validator must therefore not authorize one observation and let the core
    compiler consume a later observation from a stateful or concurrently-mutated
    object. This function establishes the retained snapshot consumed by provider
    validation and v1 normalization. verify_board captures once for both its
    historical and current evaluations.
    """

    if isinstance(value, Mapping):
        try:
            keys = tuple(value.keys())
        except Exception as exc:
            raise ContractError(f"{path} could not be snapshotted") from exc
        out: dict[Any, Any] = {}
        for key in keys:
            try:
                child = value[key]
            except Exception as exc:
                raise ContractError(f"{path} changed while being snapshotted") from exc
            try:
                out[key] = _detach(child, path=f"{path}[{key!r}]")
            except (TypeError, ValueError) as exc:
                if isinstance(exc, ContractError):
                    raise
                raise ContractError(f"{path} contains an invalid mapping key") from exc
        return out

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        try:
            items = tuple(value)
        except Exception as exc:
            raise ContractError(f"{path} could not be snapshotted") from exc
        return [_detach(item, path=f"{path}[{index}]") for index, item in enumerate(items)]

    return value


def validate_message_providers(packet: Any) -> None:
    """Reject non-canonical provider spellings on a detached packet snapshot."""

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
    snapshot = _detach(packet)
    validate_message_providers(snapshot)
    return _CORE_NORMALIZE_PACKET(snapshot)


# Existing compile_board() resolves normalize_packet from engine globals at call
# time. One patched normalizer therefore protects package and direct-engine compile.
_engine.normalize_packet = normalize_packet


def compile_board(packet: Any, *, now: Optional[datetime] = None):
    return _engine.compile_board(packet, now=now)


def verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
    # Core verification compiles historical and current views separately. Give
    # both evaluations the exact same detached packet generation.
    snapshot = _detach(packet)
    return _CORE_VERIFY_BOARD(snapshot, board, now=now)


# Normal direct-engine imports must get the same single-generation verify seam.
_engine.verify_board = verify_board
