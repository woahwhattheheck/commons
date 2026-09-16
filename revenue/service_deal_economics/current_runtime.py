from __future__ import annotations

from typing import Any

from . import authority as _authority
from . import engine as _engine
from . import strict_json as _strict_json
from .runtime_guard import freeze_call_graph


AuthorityError = _authority.AuthorityError

# Capture the exact implementation roots once. Public CURRENT calls use these
# captured objects, never a late lookup through writable module globals.
_COMPILE_AT = _authority._compile_current_at
_VERIFY_AT = _authority._verify_current_at
_RENDER = _authority.render_current_markdown
_CLOCK = _engine.now_utc

# Explicit bindings complement transitive bytecode discovery. They make the
# intended trust boundary reviewable and ensure direct rebinding of a root is
# itself detectable even though the public wrappers retain the original object.
_EXPLICIT_BINDINGS = (
    (_authority, "_compile_current_at"),
    (_authority, "_verify_current_at"),
    (_authority, "_historical_valid"),
    (_authority, "_authority_status"),
    (_authority, "_load_current"),
    (_authority, "_key"),
    (_authority, "_read_host"),
    (_authority, "_host_paths"),
    (_authority, "canonical_json"),
    (_authority, "digest"),
    (_authority, "parse_strict_json"),
    (_authority, "now_utc"),
    (_authority, "datetime"),
    (_authority, "timezone"),
    (_authority, "hashlib"),
    (_authority, "hmac"),
    (_authority, "os"),
    (_engine, "compile_report"),
    (_engine, "canonical_json"),
    (_engine, "digest"),
    (_engine, "parse_strict_json"),
    (_engine, "now_utc"),
    (_engine, "datetime"),
    (_strict_json, "canonical_json"),
    (_strict_json, "digest"),
    (_strict_json, "parse_strict_json"),
    (_strict_json, "json"),
    (_strict_json, "hashlib"),
)

_CURRENT_GRAPH_INTACT = freeze_call_graph(
    _COMPILE_AT,
    _VERIFY_AT,
    _RENDER,
    _CLOCK,
    bindings=_EXPLICIT_BINDINGS,
)


def assert_current_runtime(
    _guard=_CURRENT_GRAPH_INTACT,
    _error=AuthorityError,
) -> None:
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")


def compile_current(
    packet: Any,
    _guard=_CURRENT_GRAPH_INTACT,
    _clock=_CLOCK,
    _compile=_COMPILE_AT,
    _error=AuthorityError,
) -> dict[str, Any]:
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    now = _clock()
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    result = _compile(packet, now)
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    return result


def verify_current_authority(
    packet: Any,
    report: Any,
    _guard=_CURRENT_GRAPH_INTACT,
    _clock=_CLOCK,
    _verify=_VERIFY_AT,
    _error=AuthorityError,
) -> dict[str, Any]:
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    now = _clock()
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    result = _verify(packet, report, now)
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    return result


def render_current_markdown(
    report: Any,
    _guard=_CURRENT_GRAPH_INTACT,
    _render=_RENDER,
    _error=AuthorityError,
) -> str:
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    rendered = _render(report)
    if not _guard():
        raise _error("CURRENT runtime dependency graph changed after import")
    return rendered


# Keep the historical/test helpers in authority.py injectable, but replace its
# public CURRENT names so importing the submodule cannot bypass the frozen
# package/CLI boundary.
_authority.compile_current = compile_current
_authority.verify_current_authority = verify_current_authority
_authority.render_current_markdown = render_current_markdown
