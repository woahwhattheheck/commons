"""Compatibility entry for the packaged pinned-engine loader.

The process-isolated evaluator predates the V3 package layout and imports this
historical path by default.  Keep that evaluator byte-stable while delegating
to the packaged loader next door.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "evaluator" / "loader.py"
_spec = importlib.util.spec_from_file_location("titan_v31_packaged_loader", TARGET)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot import packaged evaluator loader: {TARGET}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

ENGINE_REF = _module.ENGINE_REF
get_engine = _module.get_engine
