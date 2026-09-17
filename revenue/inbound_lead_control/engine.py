"""Deterministic, read-only inbound commercial response controller.

The original v1 compiler remains byte-preserved in ``_engine_v1``.  This
front-door module adds a fail-closed chronology fence before delegating to that
reviewed implementation.  The package has no provider, messaging, calendar,
pricing, contract, payment, or revenue authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from . import _engine_v1 as _legacy

InputError = _legacy.InputError
SCHEMA_VERSION = _legacy.SCHEMA_VERSION

_STATE_EVENT_KINDS = frozenset({"HUMAN_INBOUND", "OUTBOUND_SENT", "BOUNCE"})


def _reject_ambiguous_chronology(document: Any) -> None:
    """Reject state-driving events whose second-precision order is unknowable.

    Provider rows currently retain canonical UTC timestamps only to whole-second
    precision.  Two state-driving facts on the same route/thread in one second
    therefore have no authenticated causal order.  Treating list order or a
    fixed kind precedence as causality would make equivalent evidence multisets
    produce different or unjustifiably strong states.

    Shape/type validation remains owned by the v1 compiler; this preflight only
    acts when enough structure is present to prove an ambiguity.
    """

    if not isinstance(document, Mapping):
        return
    leads = document.get("leads")
    if not isinstance(leads, list):
        return

    for lead in leads:
        if not isinstance(lead, Mapping):
            continue
        route = lead.get("route_key")
        thread = lead.get("thread_key")
        events = lead.get("events")
        if not isinstance(events, list):
            continue

        by_second: dict[str, list[Mapping[str, Any]]] = {}
        for event in events:
            if not isinstance(event, Mapping):
                continue
            if event.get("kind") not in _STATE_EVENT_KINDS:
                continue
            if event.get("route_key") != route or event.get("thread_key") != thread:
                continue
            occurred = event.get("occurred_utc")
            if not isinstance(occurred, str):
                continue
            by_second.setdefault(occurred, []).append(event)

        for occurred, tied in sorted(by_second.items()):
            if len(tied) <= 1:
                continue
            event_ids = sorted(str(event.get("event_id", "?")) for event in tied)
            raise InputError(
                "chronology ambiguity: state-driving events share "
                f"route/thread second {occurred}: {event_ids}"
            )


def _make_fenced_compiler(
    original: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Capture the reviewed compiler without leaving a module-global bypass."""

    def fenced(document: Mapping[str, Any]) -> dict[str, Any]:
        _reject_ambiguous_chronology(document)
        return original(document)

    fenced.__name__ = "compile_snapshot"
    fenced.__qualname__ = "compile_snapshot"
    fenced.__doc__ = "Compile retained evidence after fail-closed chronology preflight."
    return fenced


compile_snapshot = _make_fenced_compiler(_legacy.compile_snapshot)
del _make_fenced_compiler


def verify_compiled(document: Mapping[str, Any], compiled: Mapping[str, Any]) -> bool:
    """Return True only for an exact semantic replay through the chronology fence."""

    try:
        expected = compile_snapshot(document)
        return _legacy._canonical(expected) == _legacy._canonical(compiled)
    except (InputError, TypeError, ValueError):
        return False


def render_markdown(compiled: Mapping[str, Any]) -> str:
    """Render deterministic queue text using the byte-preserved v1 renderer."""

    return _legacy.render_markdown(compiled)


# Importing a submodule first still executes package ``__init__``. Rebinding
# these legacy entry points therefore prevents an ordinary caller from bypassing
# the chronology fence merely by naming the byte-preserved implementation.
_legacy.compile_snapshot = compile_snapshot
_legacy.verify_compiled = verify_compiled


def __getattr__(name: str):
    """Preserve compatibility for callers that use non-front-door v1 helpers."""

    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_legacy)))
