"""Compatibility facade for the outbound send guard.

The deterministic engine is retained byte-for-byte in :mod:`guard_legacy` for
historical replay and composed controls. Package and module CLI execution use
the verifier-clock current boundary.
"""
from __future__ import annotations

import sys

try:
    from . import guard_legacy as _legacy
except ImportError:  # pragma: no cover - direct script execution
    import guard_legacy as _legacy  # type: ignore

# Preserve the historical engine surface, including internal helpers consumed by
# the buyer-scope companion, without re-authoring its semantics.
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def main(argv: list[str] | None = None) -> int:
    """Route every supported CLI invocation through current process time."""
    try:
        from .current import main as current_main
    except ImportError:  # pragma: no cover - direct script execution
        from current import main as current_main  # type: ignore

    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"compile", "verify"}:
        return current_main(args)
    return current_main(["compile", *args])


if __name__ == "__main__":
    raise SystemExit(main())
