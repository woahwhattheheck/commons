from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import wraps
from types import ModuleType
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

_ENGINE_NAME = _engine.__name__
_GUARD_MARKER = "__commercial_deal_room_guarded__"
_FINDER_MARKER = "__commercial_deal_room_reload_finder__"


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


def _install_engine_guards(module: ModuleType) -> None:
    """Install guarded entrypoints into one live engine module generation.

    ``importlib.reload`` executes source into the existing module dictionary.
    That preserves references held by callers but replaces monkey-patched
    functions. Reinstalling before reload returns protects both fresh attribute
    lookups and stale pre-reload function references, whose globals still point
    at this same dictionary.
    """

    namespace = ModuleType.__getattribute__(module, "__dict__")
    required = {
        "ContractError",
        "VERSION",
        "canonical_json",
        "render_markdown",
        "sha256_hex",
        "normalize_packet",
        "verify_board",
    }
    missing = sorted(required - set(namespace))
    if missing:
        raise ImportError(f"{_ENGINE_NAME} missing guarded entrypoints: {missing}")

    # Engine source defines a new exception class on every reload. Preserve the
    # original exported identity so callers that imported ContractError before a
    # reload continue to catch failures from the reloaded engine generation.
    namespace["ContractError"] = globals()["ContractError"]

    current_normalize = namespace["normalize_packet"]
    if getattr(current_normalize, _GUARD_MARKER, False):
        return

    core_normalize = current_normalize
    core_verify = namespace["verify_board"]

    # Refresh helper aliases after reload creates new function objects in the
    # existing engine module dictionary.
    globals()["VERSION"] = namespace["VERSION"]
    globals()["canonical_json"] = namespace["canonical_json"]
    globals()["render_markdown"] = namespace["render_markdown"]
    globals()["sha256_hex"] = namespace["sha256_hex"]

    @wraps(core_normalize)
    def guarded_normalize_packet(packet: Any):
        snapshot = _detach(packet)
        validate_message_providers(snapshot)
        return core_normalize(snapshot)

    setattr(guarded_normalize_packet, _GUARD_MARKER, True)

    @wraps(core_verify)
    def guarded_verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
        # Core verification compiles historical and current views separately.
        # Give both evaluations the exact same detached packet generation.
        snapshot = _detach(packet)
        return core_verify(snapshot, board, now=now)

    setattr(guarded_verify_board, _GUARD_MARKER, True)

    # Existing compile_board() resolves normalize_packet from engine globals at
    # call time. One patched normalizer therefore protects package entrypoints,
    # direct-engine entrypoints, and function references captured before reload.
    namespace["normalize_packet"] = guarded_normalize_packet
    namespace["verify_board"] = guarded_verify_board


class _ReloadGuardLoader(importlib.abc.Loader):
    """Delegate source execution, then restore guards before import returns."""

    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def create_module(self, spec: Any):
        create = getattr(self._wrapped, "create_module", None)
        return create(spec) if create is not None else None

    def exec_module(self, module: ModuleType) -> None:
        self._wrapped.exec_module(module)
        _install_engine_guards(module)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


class _ReloadGuardFinder(importlib.abc.MetaPathFinder):
    """Wrap only Commercial Deal Room engine loads/reloads."""

    __commercial_deal_room_reload_finder__ = True

    def find_spec(self, fullname: str, path: Any, target: Optional[ModuleType] = None):
        if fullname != _ENGINE_NAME:
            return None
        # Delegate directly to PathFinder so this finder never recurses through
        # sys.meta_path while resolving the engine's real loader.
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is not None and spec.loader is not None:
            spec.loader = _ReloadGuardLoader(spec.loader)
        return spec


_install_engine_guards(_engine)

# guarded.py may itself be reloaded. Keep exactly one finder; an older finder
# still resolves current functions because its globals share this module dict.
if not any(getattr(finder, _FINDER_MARKER, False) for finder in sys.meta_path):
    sys.meta_path.insert(0, _ReloadGuardFinder())


def normalize_packet(packet: Any):
    return _engine.normalize_packet(packet)


def compile_board(packet: Any, *, now: Optional[datetime] = None):
    return _engine.compile_board(packet, now=now)


def verify_board(packet: Any, board: Any, *, now: Optional[datetime] = None):
    return _engine.verify_board(packet, board, now=now)
