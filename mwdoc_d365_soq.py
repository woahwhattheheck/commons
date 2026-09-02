#!/usr/bin/env python3
"""Root entrypoint for the deterministic MWDOC D365 partner packet compiler."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_IMPL = Path(__file__).resolve().parent / "scripts" / "build_mwdoc_d365_soq.py"
_SPEC = importlib.util.spec_from_file_location("mwdoc_d365_soq_impl", _IMPL)
impl = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(impl)

PacketError = impl.PacketError
artifacts = impl.artifacts
build_packet = impl.build_packet
check_outputs = impl.check_outputs
read_source = impl.read_source
score_target = impl.score_target
validate_source = impl.validate_source
write_outputs = impl.write_outputs


if __name__ == "__main__":
    raise SystemExit(impl.main())
