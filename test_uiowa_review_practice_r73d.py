"""Expose the isolated UIOWA-044 contract to the existing root CI battery."""
import importlib.util
from pathlib import Path
import unittest


def load_tests(loader, tests, pattern):
    path = Path(__file__).resolve().parent / 'revenue/uiowa_rfq_18649_review_practice/test_review_practice.py'
    spec = importlib.util.spec_from_file_location('uiowa_review_practice_contract_r73d', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)


if __name__ == '__main__':
    unittest.main()
