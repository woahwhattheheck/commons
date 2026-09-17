"""Deterministic, read-only inbound commercial response controller.

The reviewed v1 compiler bytes are retained as the non-importable
``_engine_v1.source`` artifact.  This module executes those bytes in a private
namespace and exposes only the chronology-fenced front door.  It has no
provider, messaging, calendar, pricing, contract, payment, or revenue authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

_STATE_EVENT_KINDS = frozenset({"HUMAN_INBOUND", "OUTBOUND_SENT", "BOUNCE"})
_REVIEWED_SOURCE = "_engine_v1.source"


def _reject_ambiguous_chronology(document: Any, input_error: type[ValueError]) -> None:
    """Reject state-driving events whose second-precision order is unknowable."""

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
            raise input_error(
                "chronology ambiguity: state-driving events share "
                f"route/thread second {occurred}: {event_ids}"
            )


def _build_frontdoor() -> tuple[
    type[ValueError],
    str,
    Callable[[Mapping[str, Any]], dict[str, Any]],
    Callable[[Mapping[str, Any], Mapping[str, Any]], bool],
    Callable[[Mapping[str, Any]], str],
]:
    """Load reviewed v1 bytes privately and return only fenced authorities."""

    source_path = Path(__file__).with_name(_REVIEWED_SOURCE)
    try:
        source = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError("reviewed inbound compiler source is unavailable") from exc

    namespace: dict[str, Any] = {
        "__name__": __name__,
        "__file__": str(source_path),
        "__package__": __package__,
    }
    exec(compile(source, str(source_path), "exec"), namespace, namespace)

    input_error = namespace["InputError"]
    schema_version = namespace["SCHEMA_VERSION"]
    original_compile = namespace["compile_snapshot"]
    original_render = namespace["render_markdown"]
    canonical = namespace["_canonical"]
    reject = _reject_ambiguous_chronology

    def compile_snapshot(document: Mapping[str, Any]) -> dict[str, Any]:
        reject(document, input_error)
        return original_compile(document)

    def verify_compiled(document: Mapping[str, Any], compiled: Mapping[str, Any]) -> bool:
        try:
            expected = compile_snapshot(document)
        except (input_error, TypeError, ValueError):
            return False
        return canonical(expected) == canonical(compiled)

    def render_markdown(compiled: Mapping[str, Any]) -> str:
        return original_render(compiled)

    compile_snapshot.__doc__ = "Compile retained evidence after fail-closed chronology preflight."
    verify_compiled.__doc__ = "Return True only for an exact fenced semantic replay."
    render_markdown.__doc__ = "Render deterministic queue text from a self-consistent bundle."
    return input_error, schema_version, compile_snapshot, verify_compiled, render_markdown


InputError, SCHEMA_VERSION, compile_snapshot, verify_compiled, render_markdown = _build_frontdoor()
del _build_frontdoor
