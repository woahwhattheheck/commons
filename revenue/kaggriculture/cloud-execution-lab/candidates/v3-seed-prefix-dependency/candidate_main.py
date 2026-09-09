# SPDX-License-Identifier: Apache-2.0
"""Panel-ready default-off entrypoint for the seed-prefix dependency candidate."""
from __future__ import annotations

from functools import wraps
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def _install_source_paths() -> None:
    """Expose canonical root-module origins in stripped evaluator workers.

    The source-tree builder maps some root archive members from sibling labs.
    The official process evaluator intentionally strips ``PYTHONPATH``; deriving
    these directories from the canonical builder avoids hard-coding a second
    dependency map. Installed archives already place those members together.
    """
    builder = LAB / "build_integrated.py"
    if not builder.is_file():
        return
    spec = importlib.util.spec_from_file_location(
        "_titan_seed_prefix_build_integrated", builder
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load canonical build_integrated.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for member, source in module.source_files().items():
        if Path(member).parent != Path("."):
            continue
        origin = (LAB / source).resolve()
        if not origin.is_file():
            raise FileNotFoundError(
                f"mapped root module {member} missing at {origin}"
            )
        parent = str(origin.parent)
        if parent not in sys.path:
            sys.path.append(parent)


_install_source_paths()

from seed_prefix_dependency import install_seed_prefix_dependency


def _load_canonical_main():
    """Load a private canonical module so the default entrypoint stays untouched."""
    name = "_titan_seed_prefix_canonical_main"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, LAB / "main.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load canonical TITAN main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _prepare_canonical(module):
    """Install only a candidate-local instance factory; preserve canonical agent()."""
    if getattr(module, "_seed_prefix_candidate_factory_installed", False):
        return module
    original = getattr(module, "_new_instance", None)
    if not callable(original):
        raise AttributeError("canonical main lacks callable _new_instance")

    @wraps(original)
    def candidate_new_instance(root, feature_data):
        instance = original(root, feature_data)
        # Source mismatch preserves the exact canonical instance. The report
        # stays attached for panel admission/telemetry instead of guessing a
        # new integration.
        install_seed_prefix_dependency(instance)
        return instance

    module._seed_prefix_candidate_original_factory = original
    module._new_instance = candidate_new_instance
    module._seed_prefix_candidate_factory_installed = True
    return module


# In a repository checkout, import and compose during evaluator startup, before
# the worker announces readiness. The source-independent contract bundle can
# still import this module without a checkout; its first real call then fails
# closed through the ordinary loader rather than constructing a fake actor.
_CANONICAL = (
    _prepare_canonical(_load_canonical_main())
    if (LAB / "main.py").is_file()
    else None
)


def agent(observation, configuration=None):
    global _CANONICAL
    if _CANONICAL is None:
        _CANONICAL = _prepare_canonical(_load_canonical_main())
    return _CANONICAL.agent(observation, configuration)


__all__ = ["agent"]
