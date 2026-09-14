#!/usr/bin/env python3
"""Compatibility facade adding full-envelope provider-event identity custody."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


_CORE_PATH = Path(__file__).with_name("reply_to_revenue_core.py")
_SPEC = importlib.util.spec_from_file_location("_commons_reply_to_revenue_core", _CORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load retained reply-to-revenue core: {_CORE_PATH}")
_CORE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _CORE
_SPEC.loader.exec_module(_CORE)

# Preserve the complete public surface of the reviewed owner implementation.
for _name in dir(_CORE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_CORE, _name)

_ORIGINAL_LOAD_OBSERVATIONS = _CORE.load_observations


def _event_envelope_identity(event: dict[str, Any]) -> tuple[object, str]:
    """Bind one provider reference to its complete canonical observation envelope."""
    return event.get("payload_sha256"), _CORE.sha256_text(_CORE.canonical_text(event))


def load_observations(path: Path = _CORE.OBSERVATIONS_PATH) -> dict[str, Any]:
    """Reject same-reference retries whose chronology or semantics changed."""
    raw = _CORE.read_object(path)
    events = raw.get("events")
    if isinstance(events, list):
        seen_refs: dict[str, tuple[object, str]] = {}
        for event in events:
            # The retained core owns exact shape/type validation. This facade
            # adds a pre-reduction identity fence without weakening that gate.
            if not isinstance(event, dict):
                continue
            event_ref = event.get("event_ref")
            if not isinstance(event_ref, str):
                continue
            identity = _event_envelope_identity(event)
            previous = seen_refs.get(event_ref)
            if previous is not None and previous != identity:
                if previous[0] != identity[0]:
                    raise _CORE.CollisionError(
                        f"duplicate event_ref with different payload: {event_ref}"
                    )
                raise _CORE.CollisionError(
                    f"duplicate event_ref with different observation envelope: {event_ref}"
                )
            seen_refs[event_ref] = identity
    return _ORIGINAL_LOAD_OBSERVATIONS(path)


# Functions retained from the core resolve module globals at call time. Patch
# that one binding so build_funnel(), validate_funnel(), and main() all pass
# through the same public identity fence.
_CORE.load_observations = load_observations
globals()["load_observations"] = load_observations


if __name__ == "__main__":
    raise SystemExit(_CORE.main())
