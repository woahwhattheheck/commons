# SPDX-License-Identifier: Apache-2.0
"""Isolated current-source carrier for the P07 pair-atomic candidate.

The canonical entrypoint is loaded under a private module name.  Its constructor
is reused byte-for-byte, then the returned instance receives one reconstruction-
stable P07 hook.  Canonical module globals, package configuration, archive
pointers, and sibling evaluator arms are never modified.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from p07_atomic import install_agent


def _load_canonical_main():
    source = LAB / "main.py"
    spec = importlib.util.spec_from_file_location(
        "_titan_p07_private_canonical_main", source
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load canonical entrypoint: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CANONICAL = _load_canonical_main()
_CANONICAL_NEW_INSTANCE = _CANONICAL._new_instance


def _new_instance(root, feature_data):
    instance = _CANONICAL_NEW_INSTANCE(root, feature_data)
    return install_agent(instance, enabled=True)


_CANONICAL._new_instance = _new_instance


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)


def _reset_for_tests():
    _CANONICAL._INSTANCE = None
