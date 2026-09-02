"""Root discovery shim for the focused MWDOC D365 partner packet tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "tests" / "test_mwdoc_d365_soq.py"
_SPEC = importlib.util.spec_from_file_location("mwdoc_d365_soq_focused_tests", _PATH)
_module = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_module)

MWDOCPartnerPacketTests = _module.MWDOCPartnerPacketTests
