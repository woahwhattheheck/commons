#!/usr/bin/env python3
"""NASPO SW1045 qualification v1 with a fail-closed trust-root ceiling.

The original qualification compiler remains in qualification_core.py.  This
wrapper preserves its validation/receipt behavior while making the one
security boundary explicit: caller-authored metadata is diagnostic evidence,
not authentication for official packet custody.  Until a later compiler
consumes and verifies trusted packet bytes/preimages, metadata alone can never
mint PRIME_READY or TEAMING_SUBCONTRACT_READY.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from opportunities.naspo_sw1045_qualification_2026 import qualification_core as _core
from opportunities.naspo_sw1045_qualification_2026.qualification_core import *  # noqa: F401,F403,E402


def packet_ready(source: dict[str, Any], attachments: dict[str, Any], requirements: dict[str, Any]) -> bool:
    """Return False for the metadata-only v1 trust model.

    The three inputs are intentionally accepted so callers keep the existing
    API.  They have already been validated by the core compiler and remain
    useful for diagnostics, HOLD reasons, and draft preparation.  They are not
    a cryptographic or custody proof: all three objects are caller supplied.

    A future READY-capable version must bind requirements and the attachment
    manifest to independently trusted official packet bytes (or another
    external trust root) before this function may ever return True.
    """
    del source, attachments, requirements
    return False


# evaluate() is defined in qualification_core and resolves packet_ready from
# that module's globals.  Replace that single policy hook before any call.
_core.packet_ready = packet_ready


if __name__ == "__main__":
    _core.main()
