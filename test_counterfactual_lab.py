"""Expose the isolated package tests to Commons' root unittest discovery."""
import importlib.util
from pathlib import Path


def load_tests(loader, tests, pattern):
    path = Path(__file__).parent / "host" / "counterfactual_lab" / "test_lab.py"
    spec = importlib.util.spec_from_file_location("commons_counterfactual_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)
