# SPDX-License-Identifier: Apache-2.0
"""Canonical-entrypoint carrier for the isolated KESTREL Titan V3 candidate.

The exported ``agent`` is the canonical source-tree entrypoint function itself.
Only its construction dependency is substituted: canonical ``_new_instance``
executes from its exact code object against an isolated ``titan_runtime`` import
view whose ``TitanAgent`` is ``KestrelTitanAgent``.  The live runtime module is
never mutated.  Whole-call deadline, fallback, reconstruction, finalization,
and final-pressure ordering therefore remain canonical byte-for-byte.
"""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
import sys
from types import FunctionType, ModuleType
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
for _source in (_HERE, _ROOT):
    if str(_source) not in sys.path:
        sys.path.insert(0, str(_source))


def _load_exact(name: str, path: Path) -> ModuleType:
    """Load one exact source path, replacing a stale same-name module."""
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


# Resolve candidate-local imports before the runtime class is loaded.  The
# public aliases are intentional: candidate modules use these exact import
# names, and an evaluator may load this entrypoint with the candidate directory
# absent from sys.path.
_load_exact("kestrel_early_capital", _HERE / "kestrel_early_capital.py")
_load_exact("lockstep_early_capital", _HERE / "lockstep_early_capital.py")
_CANDIDATE_RUNTIME = _load_exact(
    "_kestrel_candidate_runtime",
    _HERE / "candidate_runtime.py",
)
_CANONICAL = _load_exact("_kestrel_canonical_main", _ROOT / "main.py")
_CANONICAL_NEW_INSTANCE = _CANONICAL._new_instance


def _factory_with_candidate_base(
    candidate_base: type,
    predecessor_base: type,
) -> FunctionType:
    """Return canonical factory bytecode with one isolated import substitution.

    CPython binds a function's builtins mapping when the function object is
    created.  Rebuilding the function from the *same code object* lets only its
    ``from titan_runtime import TitanAgent, Features, load`` statement observe
    a private module view.  No entrypoint or factory control flow is copied, and
    no process-global runtime symbol is patched even briefly.
    """
    import titan_runtime

    if titan_runtime.TitanAgent is not predecessor_base:
        raise RuntimeError("canonical TitanAgent identity drift")

    runtime_view = ModuleType("titan_runtime")
    runtime_view.__dict__.update(titan_runtime.__dict__)
    runtime_view.TitanAgent = candidate_base

    original_import = builtins.__import__

    def candidate_import(
        name,
        globals=None,
        locals=None,
        fromlist=(),
        level=0,
    ):
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
    """Create canonical FinalPressureAgent directly over KestrelTitanAgent."""
    import titan_runtime

    candidate_base = _CANDIDATE_RUNTIME.KestrelTitanAgent
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


# Delegate the complete public entrypoint.  Its function globals remain the
# canonical module, so _INSTANCE, outer timer ownership, fallback selection,
# diagnostics, and interrupted-instance destruction are exactly canonical.
_CANONICAL._new_instance = _new_instance
agent = _CANONICAL.agent


__all__ = ["agent"]
