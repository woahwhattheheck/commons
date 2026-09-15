#!/usr/bin/env python3
"""Pure compatibility surface for the Commons swarm review engine.

The previously reviewed implementation bytes are retained as inert audit text in
``ground/swarm_review_core_legacy.txt``.  They are evaluated only to install the
non-CLI implementation helpers used by ``host.swarm_review``.  The legacy live
provider/mutation entry points are deleted before this module becomes usable.

Any command-line invocation of this module mechanically enters the hardened
``host.swarm_review`` surface and its exact PR/base/merge/workflow authority
bindings.  There is no independent core merge path.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

_MODULE_NAME = __name__
_MODULE_PACKAGE = __package__
_RETAINED = Path(__file__).resolve().parents[1] / "ground" / "swarm_review_core_legacy.txt"

# Evaluate the retained implementation with a non-__main__ identity so its old
# CLI guard can never fire during import.  Definitions still share this module's
# globals, which lets the hardened wrapper replace authority functions exactly
# as before.
_source = _RETAINED.read_text(encoding="utf-8")
globals()["__name__"] = "host._swarm_review_core_retained"
try:
    exec(compile(_source, str(_RETAINED), "exec"), globals(), globals())
finally:
    globals()["__name__"] = _MODULE_NAME
    globals()["__package__"] = _MODULE_PACKAGE

# The retained bytes contain the predecessor CLI/live path for auditability, but
# those names are not part of the executable module.  Provider reads used by the
# pure decision engine remain available for the wrapper's compatibility layer.
for _blocked in ("main", "live_pull", "verify_live"):
    globals().pop(_blocked, None)
del _blocked, _source


def _hardened_surface():
    """Return the wrapper that patched this core, importing it if necessary."""
    current_verify = globals().get("verify_live")
    owner_name = getattr(current_verify, "__module__", None)
    owner = sys.modules.get(owner_name) if owner_name else None
    if owner is not None and hasattr(owner, "_pr_identity"):
        return owner
    target = (f"{_MODULE_PACKAGE}.swarm_review"
              if _MODULE_PACKAGE else "swarm_review")
    owner = importlib.import_module(target)
    if not hasattr(owner, "_pr_identity") or not callable(getattr(owner, "verify_live", None)):
        raise RuntimeError("hardened swarm_review front door unavailable")
    return owner


def main(argv=None):
    """Delegate every direct core CLI invocation into the hardened front door."""
    owner = _hardened_surface()
    target = (f"{_MODULE_PACKAGE}.swarm_review_cli"
              if _MODULE_PACKAGE else "swarm_review_cli")
    cli = importlib.import_module(target)
    return cli.run(owner, argv)


if __name__ == "__main__":
    raise SystemExit(main())
