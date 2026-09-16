#!/usr/bin/env python3
"""Historical/integrity-only UArk RFP09112026 qualifier facade.

This compatibility surface intentionally preserves the original deterministic
compiler and receipt verifier.  It is not CURRENT authority because its
``evaluated_at_utc`` value is caller supplied.  Use ``current_authority.py`` for
process-clock compilation and fresh current verification.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CORE_PATH = Path(__file__).with_name("_qualifier_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "uark_rfp09112026_qualifier_historical_core", _CORE_PATH
)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import contract
    raise ImportError(f"cannot load UArk qualifier core from {_CORE_PATH}")
_core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_core)

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

AUTHORITY_MODE = "HISTORICAL_INTEGRITY_ONLY"
compile_historical = _core.compile_qualification
verify_packet_historical = _core.verify_packet
compile_qualification = compile_historical
verify_packet = verify_packet_historical


def main(argv: list[str] | None = None) -> int:
    print(
        "NOTICE: HISTORICAL_INTEGRITY_ONLY; use current_authority.py for CURRENT authority",
        file=sys.stderr,
    )
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
