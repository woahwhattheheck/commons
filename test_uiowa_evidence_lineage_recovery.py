"""Discover the complete lineage suite without leaking generic module names."""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_evidence_lineage"
NAMES = ("lineage", "demo", "walkthrough", "test_lineage", "test_lineage_recovery")
ABSENT = object()


@contextmanager
def _bound_modules(modules):
    previous = {name: sys.modules.get(name, ABSENT) for name in NAMES}
    previous_path = sys.path[:]
    try:
        sys.path.insert(0, str(HERE))
        for name in NAMES:
            if name in modules:
                sys.modules[name] = modules[name]
            else:
                sys.modules.pop(name, None)
        yield
    finally:
        sys.path[:] = previous_path
        for name, old in previous.items():
            if old is ABSENT:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


class _LineageSuite(unittest.TestSuite):
    def __init__(self, tests, modules):
        super().__init__(tests)
        self.modules = modules

    def run(self, result, debug=False):
        with _bound_modules(self.modules):
            return super().run(result, debug)


def load_tests(loader, standard_tests, pattern):
    modules = {}
    with _bound_modules(modules):
        for name in NAMES:
            spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load lineage test source: {name}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            modules[name] = module
        suites = [loader.loadTestsFromModule(modules[name]) for name in NAMES if name.startswith("test_")]
    return _LineageSuite(suites, modules)
