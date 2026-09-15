from __future__ import annotations

import importlib.abc
import importlib.machinery
import math
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

# Public diagnostics only. The production snapshotter binds the actual limits
# into a private closure below, so later rebinding of these module names cannot
# weaken or tighten the installed product boundary.
_MAX_SNAPSHOT_DEPTH = 64
_MAX_SNAPSHOT_NODES = 250_000


def _make_detacher(*, max_depth: int, max_nodes: int):
    """Build one snapshotter with limits captured by value in closure cells."""

    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("max_depth must be a non-negative exact int")
    if type(max_nodes) is not int or max_nodes < 1:
        raise ValueError("max_nodes must be a positive exact int")

    def detach(
        value: Any,
        *,
        path: str = "packet",
        _memo: Optional[dict[int, tuple[Any, Any]]] = None,
        _active: Optional[set[int]] = None,
        _nodes: Optional[list[int]] = None,
        _depth: int = 0,
    ) -> Any:
        """Capture a bounded caller-owned JSON-shaped graph once by identity.

        Container aliases reuse one completed plain snapshot. Active back-edges
        fail closed as cycles. The identity memo retains each source object so an
        integer ``id()`` cannot be recycled during capture. Scalar leaves and
        mapping keys must be exact JSON builtin types; subclasses are rejected
        rather than carrying attacker-controlled equality/hash semantics across
        the trust boundary.
        """

        if _depth > max_depth:
            raise ContractError(f"{path} exceeds snapshot depth limit")
        if _memo is None:
            _memo = {}
        if _active is None:
            _active = set()
        if _nodes is None:
            _nodes = [0]

        value_type = type(value)
        if value_type in (type(None), bool, int, str):
            return value
        if value_type is float:
            if not math.isfinite(value):
                raise ContractError(f"{path} contains a non-finite JSON number")
            return value

        # Reject scalar subclasses before container classification. In
        # particular, a str/int subclass may serialize one wire value while
        # overriding equality/hash to route as another semantic value.
        if isinstance(value, (str, bytes, bytearray, bool, int, float)):
            raise ContractError(f"{path} scalar must use an exact JSON builtin type")

        is_mapping = isinstance(value, Mapping)
        is_sequence = isinstance(value, Sequence)
        if not (is_mapping or is_sequence):
            raise ContractError(f"{path} contains an unsupported value type")

        identity = id(value)
        if identity in _active:
            raise ContractError(f"{path} contains a cyclic input graph")
        memo_entry = _memo.get(identity)
        if memo_entry is not None:
            witness, snapshot = memo_entry
            if witness is value:
                return snapshot
            # A strong witness makes this unreachable for ordinary Python
            # objects, but fail closed if a runtime violates live identity
            # uniqueness rather than aliasing two distinct objects.
            raise ContractError(f"{path} contains a snapshot identity collision")

        _nodes[0] += 1
        if _nodes[0] > max_nodes:
            raise ContractError("input graph exceeds snapshot node limit")
        _active.add(identity)

        try:
            if is_mapping:
                out: dict[str, Any] = {}
                _memo[identity] = (value, out)
                try:
                    for key in value:
                        _nodes[0] += 1
                        if _nodes[0] > max_nodes:
                            raise ContractError("input graph exceeds snapshot node limit")
                        if type(key) is not str:
                            raise ContractError(
                                f"{path} mapping key must use exact str type"
                            )
                        try:
                            child = value[key]
                        except Exception as exc:
                            raise ContractError(
                                f"{path} changed while being snapshotted"
                            ) from exc
                        out[key] = detach(
                            child,
                            path=f"{path}[{key!r}]",
                            _memo=_memo,
                            _active=_active,
                            _nodes=_nodes,
                            _depth=_depth + 1,
                        )
                except ContractError:
                    raise
                except Exception as exc:
                    raise ContractError(f"{path} could not be snapshotted") from exc
                return out

            out_list: list[Any] = []
            _memo[identity] = (value, out_list)
            try:
                for index, child in enumerate(value):
                    _nodes[0] += 1
                    if _nodes[0] > max_nodes:
                        raise ContractError("input graph exceeds snapshot node limit")
                    out_list.append(
                        detach(
                            child,
                            path=f"{path}[{index}]",
                            _memo=_memo,
                            _active=_active,
                            _nodes=_nodes,
                            _depth=_depth + 1,
                        )
                    )
            except ContractError:
                raise
            except Exception as exc:
                raise ContractError(f"{path} could not be snapshotted") from exc
            return out_list
        except Exception:
            _memo.pop(identity, None)
            raise
        finally:
            _active.discard(identity)

    return detach


# Bind the safety policy once. Rebinding _MAX_SNAPSHOT_* later changes only the
# diagnostic names above; the installed product snapshotter retains 64/250000.
_detach = _make_detacher(
    max_depth=_MAX_SNAPSHOT_DEPTH,
    max_nodes=_MAX_SNAPSHOT_NODES,
)


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
        # Capture packet + board into one bounded identity domain before core
        # touches either caller-owned graph, so historical verification observes
        # one stable board generation and cross-input aliases share one snapshot.
        memo: dict[int, tuple[Any, Any]] = {}
        active: set[int] = set()
        nodes = [0]
        packet_snapshot = _detach(
            packet,
            path="packet",
            _memo=memo,
            _active=active,
            _nodes=nodes,
        )
        board_snapshot = _detach(
            board,
            path="board",
            _memo=memo,
            _active=active,
            _nodes=nodes,
        )
        return core_verify(packet_snapshot, board_snapshot, now=now)

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
