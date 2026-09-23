"""Root discovery for the common register transport; no global import-path edits."""
from pathlib import Path
import importlib.util
import unittest

DIRECTORY = Path(__file__).resolve().parent / "revenue/uiowa_rfq_18649_workshare/methodology"
MODULES = ("test_validate_23_evidence_register", "test_evidence_register_interchange", "test_native_031_common_bridge")


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name in MODULES:
        spec = importlib.util.spec_from_file_location("harborglass23r_" + name, DIRECTORY / (name + ".py"))
        if spec is None or spec.loader is None:
            raise ImportError("Cannot load " + name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


if __name__ == "__main__":
    unittest.main()
