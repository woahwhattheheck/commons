# SPDX-License-Identifier: Apache-2.0
"""Default-off TITAN candidate with final-action stock-prefix isolation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (str(HERE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import operating_stock as _operating_stock
from final_boundary import install_final_boundary

_spec = importlib.util.spec_from_file_location(
    "_titan_v3_operating_stock_final_prefix_parent", ROOT / "main.py"
)
if _spec is None or _spec.loader is None:
    raise ImportError("unable to load canonical TITAN entrypoint")
_parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent)

_original_new_instance = _parent._new_instance


def _new_instance(root, feature_data):
    instance = _original_new_instance(root, feature_data)
    return install_final_boundary(instance, _operating_stock)


_parent._new_instance = _new_instance


def agent(observation, configuration=None):
    # Defensive for harnesses that inject an already-constructed parent instance.
    instance = getattr(_parent, "_INSTANCE", None)
    if instance is not None:
        install_final_boundary(instance, _operating_stock)
    return _parent.agent(observation, configuration)
