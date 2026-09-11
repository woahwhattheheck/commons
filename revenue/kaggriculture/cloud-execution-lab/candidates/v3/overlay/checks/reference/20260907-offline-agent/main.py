"""Compatibility entry for the packaged V3.1 candidate.

The process-isolated evaluator's historical default candidate lives beside its
loader.  Delegate that entry to the package's top-level main.py without
changing gameplay policy.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "main.py"
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("titan_v31_packaged_candidate", TARGET)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot import packaged candidate: {TARGET}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

agent = _module.agent
