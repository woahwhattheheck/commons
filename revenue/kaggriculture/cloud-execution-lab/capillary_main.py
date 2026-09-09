# SPDX-License-Identifier: Apache-2.0
"""Canonical-entrypoint-preserving carrier for the isolated Capillary candidate.

The candidate changes exactly one runtime seam: the base class used by canonical
``main.py::_new_instance``. Canonical ``FinalPressureAgent`` construction,
whole-call deadlines, fallback selection, interrupted-instance reconstruction,
and module-owned lifecycle remain the exact control implementation.
"""
from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


_CANONICAL: ModuleType | None = None
_CANONICAL_MODULE_NAME = "_titan_capillary_canonical_main_sol_janus"


def _canonical_module() -> ModuleType:
    """Load canonical ``main.py`` once and wrap only its instance factory."""
    global _CANONICAL
    if _CANONICAL is not None:
        return _CANONICAL

    import sys

    root = Path(__file__).resolve().parent
    canonical_path = root / "main.py"
    if not canonical_path.is_file():
        raise FileNotFoundError(f"canonical entrypoint missing: {canonical_path}")
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)

    import titan_runtime as runtime
    from titan_capillary import CapillaryTitanAgent

    module = runtime.load(
        _CANONICAL_MODULE_NAME,
        canonical_path,
        cache=True,
    )
    canonical_factory = getattr(module, "_new_instance", None)
    canonical_agent = getattr(module, "agent", None)
    if not callable(canonical_factory) or not callable(canonical_agent):
        raise RuntimeError("canonical entrypoint contract unavailable")

    def capillary_factory(
        factory_root: Path,
        feature_data: dict[str, Any],
    ):
        # Canonical _new_instance imports TitanAgent inside the call and defines
        # FinalPressureAgent(TitanAgent). Substitute the candidate base only
        # while that exact class is constructed, then restore shared runtime
        # state even if admission construction fails.
        previous = runtime.TitanAgent
        runtime.TitanAgent = CapillaryTitanAgent
        try:
            return canonical_factory(factory_root, feature_data)
        finally:
            runtime.TitanAgent = previous

    module._new_instance = capillary_factory
    _CANONICAL = module
    return module


def agent(observation, configuration=None):
    """Delegate the complete call to the exact canonical entrypoint."""
    return _canonical_module().agent(observation, configuration)


__all__ = ["agent"]
