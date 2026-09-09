# SPDX-License-Identifier: Apache-2.0
"""Canonical-entrypoint carrier for the priority-safe Capillary candidate.

Canonical ``main.py`` is executed privately for every evaluator load, so its
mutable ``_INSTANCE`` cannot leak across a many-game panel.  Its exact factory
code object runs against an isolated ``titan_runtime`` import view whose only
substitution is ``TitanAgent = CapillaryTitanAgent``.  The live runtime module
is never mutated; deadline, fallback, reconstruction, finalization, and final
pressure remain canonical control flow.
"""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys
from types import FunctionType, ModuleType
from typing import Any


_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _load_exact(name: str, path: Path) -> ModuleType:
    target = path.resolve()
    existing = sys.modules.get(name)
    existing_path = getattr(existing, "__file__", None)
    if existing_path is not None and Path(existing_path).resolve() == target:
        return existing
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {target}")
    module = importlib.util.module_from_spec(spec)
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


def _load_private_exact(name: str, path: Path) -> ModuleType:
    target = path.resolve()
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_exact("jit_seed_staging", _HERE / "jit_seed_staging.py")
_load_exact("capillary_priority_guard", _HERE / "capillary_priority_guard.py")
_CANDIDATE_RUNTIME = _load_exact("titan_capillary", _HERE / "titan_capillary.py")

_CANONICAL = _load_private_exact(
    f"_capillary_priority_canonical_main_{id(globals()):x}",
    _HERE / "main.py",
)
_CANONICAL_NEW_INSTANCE = _CANONICAL._new_instance


def _factory_with_candidate_base(
    candidate_base: type,
    predecessor_base: type,
) -> FunctionType:
    import titan_runtime

    if titan_runtime.TitanAgent is not predecessor_base:
        raise RuntimeError("canonical TitanAgent identity drift")

    runtime_view = ModuleType("titan_runtime")
    runtime_view.__dict__.update(titan_runtime.__dict__)
    runtime_view.TitanAgent = candidate_base
    original_import = builtins.__import__

    def candidate_import(name, globals=None, locals=None, fromlist=(), level=0):
        loaded = original_import(name, globals, locals, fromlist, level)
        if level == 0 and name == "titan_runtime":
            return runtime_view
        return loaded

    isolated_builtins = dict(vars(builtins))
    isolated_builtins["__import__"] = candidate_import
    isolated_globals = dict(_CANONICAL_NEW_INSTANCE.__globals__)
    isolated_globals["__builtins__"] = isolated_builtins
    factory = FunctionType(
        _CANONICAL_NEW_INSTANCE.__code__,
        isolated_globals,
        _CANONICAL_NEW_INSTANCE.__name__,
        _CANONICAL_NEW_INSTANCE.__defaults__,
        _CANONICAL_NEW_INSTANCE.__closure__,
    )
    factory.__kwdefaults__ = _CANONICAL_NEW_INSTANCE.__kwdefaults__
    factory.__annotations__ = dict(_CANONICAL_NEW_INSTANCE.__annotations__)
    factory.__qualname__ = _CANONICAL_NEW_INSTANCE.__qualname__
    return factory


def _new_instance(root: Path, feature_data: dict[str, Any]):
    import titan_runtime

    candidate_base = _CANDIDATE_RUNTIME.CapillaryTitanAgent
    predecessor_base = candidate_base.__mro__[1]
    factory = _factory_with_candidate_base(candidate_base, predecessor_base)
    if factory.__code__ is not _CANONICAL_NEW_INSTANCE.__code__:
        raise RuntimeError("canonical factory code identity drift")
    instance = factory(root, feature_data)
    if titan_runtime.TitanAgent is not predecessor_base:
        raise RuntimeError("live TitanAgent was mutated during construction")
    mro = type(instance).__mro__
    if len(mro) < 3 or mro[1] is not candidate_base or mro[2] is not predecessor_base:
        raise RuntimeError("canonical FinalPressureAgent carrier was not constructed")
    return instance


_CANONICAL._new_instance = _new_instance


def _canonical_module() -> ModuleType:
    return _CANONICAL


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)


__all__ = ["agent"]
