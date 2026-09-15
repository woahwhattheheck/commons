from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
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

# Snapshot limits apply before schema validation so hostile caller containers
# cannot consume unbounded recursion or memory before normal packet caps run.
_MAX_SNAPSHOT_DEPTH = 64
_MAX_SNAPSHOT_NODES = 250_000
_MISSING = object()


class _SnapshotState:
    __slots__ = ("active", "memo", "nodes")

    def __init__(self) -> None:
        self.active: set[int] = set()
        self.memo: dict[int, Any] = {}
        self.nodes = 0


# These are refreshed after every ordinary engine reload before the guarded
# entrypoints are reinstalled.
_CORE_NORMALIZE_PACKET = _engine.normalize_packet
_CORE_COMPILE_BOARD = _engine.compile_board
_CORE_VERIFY_BOARD = _engine.verify_board


def _detach(value: Any, *, path: str = "packet") -> Any:
    """Capture a bounded caller-owned object graph into plain containers.

    Repeated references retain one detached generation. Cycles fail closed
    rather than returning a partially-built graph. Provider validation and the
    core compiler therefore consume the same finite observation even when a
    caller supplies stateful Mapping/Sequence implementations.
    """

    return _detach_inner(value, path=path, depth=0, state=_SnapshotState())


def _detach_inner(value: Any, *, path: str, depth: int, state: _SnapshotState) -> Any:
    if depth > _MAX_SNAPSHOT_DEPTH:
        raise ContractError(f"{path} exceeds snapshot depth limit")

    state.nodes += 1
    if state.nodes > _MAX_SNAPSHOT_NODES:
        raise ContractError("packet exceeds snapshot node limit")

    if isinstance(value, Mapping):
        identity = id(value)
        if identity in state.active:
            raise ContractError(f"{path} contains a cyclic mapping")
        cached = state.memo.get(identity, _MISSING)
        if cached is not _MISSING:
            return cached

        try:
            keys = tuple(value.keys())
        except Exception as exc:
            raise ContractError(f"{path} could not be snapshotted") from exc

        out: dict[Any, Any] = {}
        state.memo[identity] = out
        state.active.add(identity)
        try:
            for key in keys:
                try:
                    child = value[key]
                except Exception as exc:
                    raise ContractError(f"{path} changed while being snapshotted") from exc
                try:
                    out[key] = _detach_inner(
                        child,
                        path=f"{path}[{key!r}]",
                        depth=depth + 1,
                        state=state,
                    )
                except (TypeError, ValueError) as exc:
                    if isinstance(exc, ContractError):
                        raise
                    raise ContractError(f"{path} contains an invalid mapping key") from exc
        finally:
            state.active.discard(identity)
        return out

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        identity = id(value)
        if identity in state.active:
            raise ContractError(f"{path} contains a cyclic sequence")
        cached = state.memo.get(identity, _MISSING)
        if cached is not _MISSING:
            return cached

        try:
            items = tuple(value)
        except Exception as exc:
            raise ContractError(f"{path} could not be snapshotted") from exc

        out: list[Any] = []
        state.memo[identity] = out
        state.active.add(identity)
        try:
            for index, item in enumerate(items):
                out.append(
                    _detach_inner(
                        item,
                        path=f"{path}[{index}]",
                        depth=depth + 1,
                        state=state,
                    )
                )
        finally:
            state.active.discard(identity)
        return out

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


def compile_board(packet: Any, *, now: Optional[datetime] = None):
    snapshot = _detach(packet)
    validate_message_providers(snapshot)
    return _CORE_COMPILE_BOARD(snapshot, now=now)


def verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
    # Core verification compiles historical and current views separately. Give
    # both evaluations the exact same detached packet generation.
    snapshot = _detach(packet)
    validate_message_providers(snapshot)
    return _CORE_VERIFY_BOARD(snapshot, board, now=now)


def _install_engine_guards(module: Any) -> None:
    """Capture fresh core entrypoints, then expose guarded direct-engine seams."""

    global _CORE_NORMALIZE_PACKET, _CORE_COMPILE_BOARD, _CORE_VERIFY_BOARD

    candidate_normalize = module.normalize_packet
    if getattr(candidate_normalize, "_commercial_deal_room_guarded", False):
        core_normalize = module._commercial_deal_room_core_normalize
        core_compile = module._commercial_deal_room_core_compile
        core_verify = module._commercial_deal_room_core_verify
    else:
        core_normalize = candidate_normalize
        core_compile = module.compile_board
        core_verify = module.verify_board

    _CORE_NORMALIZE_PACKET = core_normalize
    _CORE_COMPILE_BOARD = core_compile
    _CORE_VERIFY_BOARD = core_verify

    # Retain the unwrapped authority across guarded-module reloads, and keep one
    # ContractError identity when importlib re-executes engine.py.
    module._commercial_deal_room_core_normalize = core_normalize
    module._commercial_deal_room_core_compile = core_compile
    module._commercial_deal_room_core_verify = core_verify
    module.ContractError = ContractError
    module.normalize_packet = normalize_packet
    module.compile_board = compile_board
    module.verify_board = verify_board


class _EngineReloadLoader(importlib.abc.Loader):
    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def create_module(self, spec: Any) -> Any:
        create = getattr(self._wrapped, "create_module", None)
        return create(spec) if create is not None else None

    def exec_module(self, module: Any) -> None:
        self._wrapped.exec_module(module)
        _install_engine_guards(module)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


class _EngineReloadFinder(importlib.abc.MetaPathFinder):
    _commercial_deal_room_reload_guard = True

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> Any:
        if fullname != _engine.__name__ or target is None:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is not None and spec.loader is not None:
            spec.loader = _EngineReloadLoader(spec.loader)
        return spec


normalize_packet._commercial_deal_room_guarded = True
compile_board._commercial_deal_room_guarded = True
verify_board._commercial_deal_room_guarded = True


def _install_reload_finder() -> None:
    if not any(
        getattr(finder, "_commercial_deal_room_reload_guard", False)
        for finder in sys.meta_path
    ):
        sys.meta_path.insert(0, _EngineReloadFinder())


_install_engine_guards(_engine)
_install_reload_finder()
