from __future__ import annotations

from typing import Any

from . import authority as _authority
from . import engine as _engine
from . import strict_json as _strict_json
from .runtime_guard import freeze_call_graph


AuthorityError = _authority.AuthorityError

# Capture the exact implementation roots once. Public CURRENT calls use these
# original objects, never a late lookup through writable module globals.
_compile_at = _authority._compile_current_at
_verify_at = _authority._verify_current_at
_render = _authority.render_current_markdown
_clock = _engine.now_utc

# Explicit root pins complement transitive bytecode discovery. Historical/test
# helpers remain injectable, but any such injection makes the public CURRENT
# surface fail closed for the duration of the mutation.
_explicit_bindings = (
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
_guard = freeze_call_graph(
    _compile_at,
    _verify_at,
    _render,
    _clock,
    bindings=_explicit_bindings,
)


def _build_current_surface(guard, clock, compile_at, verify_at, render, error_type):
    # All authority-bearing dependencies live in closure cells. The returned
    # public functions expose only their business arguments: there is no
    # caller-selectable clock, trust root, guard, compile function, or verifier.
    def assert_current_runtime() -> None:
        if not guard():
            raise error_type("CURRENT runtime dependency graph changed after import")

    def compile_current(packet: Any) -> dict[str, Any]:
        assert_current_runtime()
        now = clock()
        assert_current_runtime()
        result = compile_at(packet, now)
        assert_current_runtime()
        return result

    def verify_current_authority(packet: Any, report: Any) -> dict[str, Any]:
        assert_current_runtime()
        now = clock()
        assert_current_runtime()
        result = verify_at(packet, report, now)
        assert_current_runtime()
        return result

    def render_current_markdown(report: Any) -> str:
        assert_current_runtime()
        rendered = render(report)
        assert_current_runtime()
        return rendered

    return assert_current_runtime, compile_current, verify_current_authority, render_current_markdown


(
    assert_current_runtime,
    compile_current,
    verify_current_authority,
    render_current_markdown,
) = _build_current_surface(_guard, _clock, _compile_at, _verify_at, _render, AuthorityError)

# Keep historical/test helpers in authority.py injectable, but replace its
# public CURRENT names so importing the submodule cannot bypass this boundary.
_authority.compile_current = compile_current
_authority.verify_current_authority = verify_current_authority
_authority.render_current_markdown = render_current_markdown

# Do not leave an alternate surface builder as a convenient public bypass.
del _build_current_surface
