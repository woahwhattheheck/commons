#!/usr/bin/env python3
"""Single fail-closed executable authority for NASPO SW1045 qualification v1.

The original v1 implementation bytes are retained beside this module only as
``qualification_core_v1.source`` so Git history/provenance remains inspectable
without leaving a second importable or directly executable compiler.  This
module loads that source into an isolated namespace only after replacing the
one predecessor packet-readiness policy with the v1 trust-root ceiling.

Caller-authored packet metadata is diagnostic evidence, not authentication.
Until a later compiler consumes an independently trusted official packet
preimage, metadata alone can never mint PRIME_READY or TEAMING_READY.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_SOURCE = Path(__file__).with_name("qualification_core_v1.source")

# Exact predecessor function text.  The loader fails closed if the retained
# source changes instead of silently executing an unreviewed policy variant.
_PREDECESSOR_PACKET_READY = '''def packet_ready(s,a,r):
    pa=s["packet_access"]
    if not pa["official_packet_acquired"] or not pa["official_addenda_inventory_confirmed"]: return False
    if not a["complete_inventory_confirmed"] or not a["official_addenda_inventory_confirmed"]: return False
    if not a["documents"] or any(d["status"]!="OFFICIAL_EXACT" for d in a["documents"]): return False
    if r["source_authority"]!="CONTROLLING_PACKET" or r["evaluation_model_status"]!="EXACT_CAPTURED": return False
    return True
'''

_FAIL_CLOSED_PACKET_READY = '''def packet_ready(s,a,r):
    # v1 has no independently authenticated packet preimage.  The inputs are
    # validated for diagnostics, but all three remain caller-authored metadata.
    del s, a, r
    return False
'''

try:
    _raw = _SOURCE.read_text(encoding="utf-8")
except (OSError, UnicodeError) as exc:  # fail closed before exposing compiler API
    raise RuntimeError("NASPO v1 implementation source unavailable") from exc

if _raw.count(_PREDECESSOR_PACKET_READY) != 1:
    raise RuntimeError("NASPO v1 predecessor policy marker mismatch")

_patched = _raw.replace(
    _PREDECESSOR_PACKET_READY,
    _FAIL_CLOSED_PACKET_READY,
    1,
)
_runtime: dict[str, Any] = {
    "__name__": f"{__name__}._implementation",
    "__file__": str(_SOURCE),
    "__package__": __package__,
}
exec(compile(_patched, str(_SOURCE), "exec"), _runtime, _runtime)

# Defensive postcondition: the runtime actually contains the fail-closed
# function before any API is exported.  Empty inputs are intentional here;
# the safe policy must not inspect caller metadata at all.
if _runtime["packet_ready"]({}, {}, {}) is not False:
    raise RuntimeError("NASPO v1 packet readiness ceiling not installed")

for _name, _value in tuple(_runtime.items()):
    if not _name.startswith("_"):
        globals()[_name] = _value

__all__ = tuple(sorted(name for name in _runtime if not name.startswith("_")))

if __name__ == "__main__":
    raise SystemExit(main())
