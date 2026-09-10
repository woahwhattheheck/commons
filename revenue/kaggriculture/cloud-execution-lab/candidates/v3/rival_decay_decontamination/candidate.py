# SPDX-License-Identifier: Apache-2.0
"""Default-off executable TITAN V3 carrier for rival crop-decay decontamination.

Every local and canonical module is bound to an exact filesystem origin. Each
execution of this carrier owns a private canonical ``main.py`` module, so
independently loaded evaluators cannot share its mutable ``_INSTANCE`` cell.
Canonical config, source, archive and Kaggle state are never mutated.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
SOURCE_COMMIT = "2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb"
EXPECTED_GIT_BLOBS = {
    "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "scheduler.py": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
    "reference/engine/kaggriculture.py": "3c202c7ee921da239356789e266b694635103fc4",
}

# Reproduce build_integrated.source_files()'s archive-root import closure from
# the repository checkout. LAB stays authoritative for duplicate bare names.
SOURCE_ROOTS = (
    LAB,
    LAB.parent / "cloud-runtime-pulse",
    LAB.parent / "cloud-quickstep",
    LAB.parent / "cloud-opponent-league" / "lark-responsive",
    LAB.parent / "cloud-committed-seed-retry",
    LAB.parent / "cloud-economic-stress" / "funded-payback",
)


class SourceDrift(RuntimeError):
    """The executable current seam no longer matches the reviewed source."""


def _origin(module: ModuleType) -> Path:
    raw = getattr(module, "__file__", None)
    if not raw:
        raise SourceDrift(f"module has no filesystem origin: {module!r}")
    return Path(raw).resolve()


def _load_private(name: str, path: Path) -> ModuleType:
    """Execute one exact source file without publishing a reusable module cell."""
    expected = path.resolve(strict=True)
    spec = importlib.util.spec_from_file_location(name, expected)
    if spec is None or spec.loader is None:
        raise SourceDrift(f"cannot load exact source: {expected}")
    module = importlib.util.module_from_spec(spec)
    # Deliberately do not register this module in sys.modules. The returned
    # function/class graph owns it privately, including canonical main._INSTANCE.
    spec.loader.exec_module(module)
    if _origin(module) != expected:
        raise SourceDrift(
            f"loaded {name} from unexpected path: {_origin(module)} != {expected}"
        )
    return module


_DECAY_OBSERVER = _load_private(
    f"{__name__}._rival_decay_observer", HERE / "decay_observer.py"
)
OPERATION = _DECAY_OBSERVER.OPERATION
make_decay_safe_frozen_selected = _DECAY_OBSERVER.make_decay_safe_frozen_selected


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity, not security.
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def verify_source(root: Path = LAB) -> dict[str, str]:
    root = root.resolve(strict=True)
    observed: dict[str, str] = {}
    for relative, expected in EXPECTED_GIT_BLOBS.items():
        path = root / relative
        if not path.is_file():
            raise SourceDrift(f"missing pinned source: {relative}")
        actual = git_blob_sha1(path.read_bytes())
        observed[relative] = actual
        if actual != expected:
            raise SourceDrift(
                f"source drift for {relative}: expected {expected}, observed {actual}"
            )
    return observed


def _install_source_roots() -> tuple[str, ...]:
    resolved: list[str] = []
    for root in SOURCE_ROOTS:
        try:
            path = root.resolve(strict=True)
        except FileNotFoundError as exc:
            raise SourceDrift(f"missing current source root: {root}") from exc
        if not path.is_dir():
            raise SourceDrift(f"current source root is not a directory: {path}")
        resolved.append(str(path))

    for root in reversed(resolved):
        while root in sys.path:
            sys.path.remove(root)
        sys.path.insert(0, root)
    return tuple(resolved)


def _lab_module(name: str) -> ModuleType:
    expected = (LAB / f"{name}.py").resolve(strict=True)
    loaded = sys.modules.get(name)
    if loaded is not None:
        origin = _origin(loaded)
        if origin != expected:
            raise SourceDrift(f"preloaded {name} from unexpected path: {origin}")
        return loaded
    module = importlib.import_module(name)
    origin = _origin(module)
    if origin != expected:
        raise SourceDrift(f"loaded {name} from unexpected path: {origin}")
    return module


def install() -> type:
    """Install the corrected class into this process's exact executable seam."""
    verify_source()
    _install_source_roots()
    scheduler = _lab_module("scheduler")
    frozen = _lab_module("frozen_selected")
    current = frozen.FrozenSelected
    existing = getattr(current, "_titan_rival_decay_decontamination", None)
    if existing == OPERATION:
        return current
    if existing is not None:
        raise SourceDrift(f"different decay observer already installed: {existing}")
    if not issubclass(current, scheduler.SellScheduler):
        raise SourceDrift("configured FrozenSelected no longer inherits SellScheduler")
    if current.observe is not scheduler.SellScheduler.observe:
        raise SourceDrift("configured FrozenSelected no longer uses inherited observer seam")

    patched = make_decay_safe_frozen_selected(
        current,
        products=scheduler.PRODUCTS,
        animals=scheduler.m.ANIMALS,
    )
    frozen.FrozenSelected = patched
    return patched


def _load_canonical_main() -> ModuleType:
    """Return an origin-checked canonical module private to this carrier load."""
    install()
    return _load_private(f"{__name__}._canonical_main", LAB / "main.py")


INSTALLED_CLASS = install()
CANONICAL_MAIN = _load_canonical_main()
agent = CANONICAL_MAIN.agent
