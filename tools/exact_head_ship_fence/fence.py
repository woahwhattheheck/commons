"""Sealed public facade for the exact-head ship fence core.

The implementation core is retained in ``_core`` so the public API can pin its
semantic dependency generation. Ordinary module-global mutation/rebinding must
fail closed rather than teaching compile and verify the same attacker semantics.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any
import importlib as _importlib

from . import _core as _c
# Every ordinary facade import/reload restores the private core from source before
# sealing it, so a pre-reload helper/global mutation cannot become a trusted baseline.
_c = _importlib.reload(_c)

SCHEMA_VERSION = _c.SCHEMA_VERSION
TOOL_ID = _c.TOOL_ID
MAX_JSON_BYTES = _c.MAX_JSON_BYTES
EvidenceError = _c.EvidenceError
_CURRENT_CLOCK = _c._CURRENT_CLOCK  # compatibility alias; public calls pin the captured clock below.
_AUTHORITY_LITERAL = {
    "merge_authorized": False,
    "ref_mutation_authorized": False,
    "review_mutation_authorized": False,
    "provider_mutation_authorized": False,
    "outbound_authorized": False,
    "spend_authorized": False,
    "payment_authorized": False,
    "revenue_recognition_authorized": False,
}
AUTHORITY = MappingProxyType(dict(_AUTHORITY_LITERAL))


def _make_freezer(pattern_type=type(_c.SHA)):
    def freeze(value: Any):
        t = type(value)
        if value is None or t in (bool, int, str):
            return (t.__name__, value)
        if t is dict:
            return ("dict", tuple(sorted((k, freeze(v)) for k, v in value.items())))
        if t is set:
            return ("set", tuple(sorted(freeze(v) for v in value)))
        if t is tuple:
            return ("tuple", tuple(freeze(v) for v in value))
        if t is list:
            return ("list", tuple(freeze(v) for v in value))
        if isinstance(value, pattern_type):
            return ("regex", value.pattern, value.flags)
        return ("identity", id(value))
    return freeze


_freeze = _make_freezer()

def _make_api(core=_c, literal=dict(_AUTHORITY_LITERAL)):
    freeze = _freeze
    error = EvidenceError
    private_callables = {
        name: value
        for name, value in vars(core).items()
        if name.startswith("_") and callable(value)
    }
    public_callables = {
        name: getattr(core, name)
        for name in (
            "parse_json_bytes", "canonical_json_bytes", "compile_current",
            "verify_current", "render_markdown",
        )
    }
    constant_snapshot = {
        name: freeze(value)
        for name, value in vars(core).items()
        if name.isupper()
    }
    imported_bindings = {
        name: getattr(core, name)
        for name in ("datetime", "timezone", "hashlib", "json", "re")
    }
    clock = core._CURRENT_CLOCK
    compile_core = core.compile_current
    verify_core = core.verify_current
    parse_core = core.parse_json_bytes
    canonical_core = core.canonical_json_bytes
    render_core = core.render_markdown

    def integrity() -> None:
        for name, value in private_callables.items():
            if getattr(core, name, None) is not value:
                raise error(f"core semantic binding changed: {name}")
        for name, value in public_callables.items():
            if getattr(core, name, None) is not value:
                raise error(f"core public binding changed: {name}")
        for name, snapshot in constant_snapshot.items():
            if freeze(getattr(core, name, None)) != snapshot:
                raise error(f"core constant changed: {name}")
        for name, value in imported_bindings.items():
            if getattr(core, name, None) is not value:
                raise error(f"core runtime binding changed: {name}")

    def reviewer_guard(snapshot: Any) -> None:
        if type(snapshot) is not dict or type(snapshot.get("reviews")) is not list:
            return
        seen: set[str] = set()
        for row in snapshot["reviews"]:
            if type(row) is not dict or type(row.get("reviewer")) is not str:
                continue
            reviewer = row["reviewer"].casefold()
            if reviewer in seen:
                raise error("reviews: duplicate reviewer identity")
            seen.add(reviewer)

    def parse_json_bytes(data: bytes):
        integrity()
        value = parse_core(data)
        integrity()
        return value

    def canonical_json_bytes(value: Any) -> bytes:
        integrity()
        out = canonical_core(value)
        integrity()
        return out

    def compile_current(snapshot: Any) -> dict:
        integrity()
        reviewer_guard(snapshot)
        report = compile_core(snapshot, _clock=clock)
        integrity()
        if report.get("authority") != literal:
            raise error("authority ceiling widened")
        return report

    def verify_current(report: Any, snapshot: Any) -> bool:
        try:
            integrity()
            reviewer_guard(snapshot)
            if type(report) is not dict or report.get("authority") != literal:
                return False
            ok = verify_core(report, snapshot, _clock=clock)
            integrity()
            return bool(ok and report.get("authority") == literal)
        except error:
            return False

    def render_markdown(report: Any) -> str:
        integrity()
        if type(report) is not dict or report.get("authority") != literal:
            raise error("authority ceiling widened")
        out = render_core(report)
        integrity()
        return out

    return parse_json_bytes, canonical_json_bytes, compile_current, verify_current, render_markdown


parse_json_bytes, canonical_json_bytes, compile_current, verify_current, render_markdown = _make_api()

__all__ = [
    "AUTHORITY", "EvidenceError", "SCHEMA_VERSION", "TOOL_ID",
    "canonical_json_bytes", "compile_current", "parse_json_bytes",
    "render_markdown", "verify_current",
]
