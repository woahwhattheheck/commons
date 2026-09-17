"""Reload-stable first-load trust root for current pilot-gate semantics.

The public engine may be re-executed with :func:`importlib.reload` or loaded again
under another module name.  A process-global ``builtins`` monkeypatch that is active
during that engine execution must not become trusted semantics.  This helper is loaded
once with the package and keeps the first-load builtins table in function defaults,
outside later engine module-global re-execution.

Explicit mutation/reload of this private trust-root module or surgery on the returned
function/default/closure is outside the cooperative in-process boundary, just like
direct surgery on the engine's sealed function closures.
"""
from __future__ import annotations

import builtins as _builtins


def _build_copy_function():
    snapshot = dict(vars(_builtins))
    copy_dict = dict

    def trusted_builtins_copy(*, _snapshot=snapshot, _copy=copy_dict):
        """Return a fresh copy of the first-load builtins mapping."""
        return _copy(_snapshot)

    return trusted_builtins_copy


trusted_builtins_copy = _build_copy_function()
del _build_copy_function
del _builtins
