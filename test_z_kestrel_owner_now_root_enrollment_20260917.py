#!/usr/bin/env python3
"""Root-level predecessor killers for owner-now static checkout enrollment."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGED = '\n<a href="https://buy.stripe.com/forged_owner_now_bypass">forged</a>\n'
EXPECTED = "owner-now-revenue.html must keep Stripe URLs out of static HTML"


def _load(name: str):
    path = ROOT / "host" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"zkestrel_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measure_with_owner_now_forge(module):
    original = module._read

    def forged_read(root: str, rel: str) -> str:
        text = original(root, rel)
        if rel == "owner-now-revenue.html":
            return text + FORGED
        return text

    module._read = forged_read
    try:
        return module.measure_root(str(ROOT))
    finally:
        module._read = original


class OwnerNowRootEnrollment(unittest.TestCase):
    def test_checkout_measure_root_rejects_owner_now_forged_static_stripe(self) -> None:
        row = _measure_with_owner_now_forge(_load("checkout_capability"))
        self.assertEqual(row.get("state"), "NOT_LANDED")
        self.assertIn(EXPECTED, row.get("errors") or [])

    def test_payment_measure_root_rejects_owner_now_forged_static_stripe(self) -> None:
        row = _measure_with_owner_now_forge(_load("payment_capability"))
        self.assertEqual(row.get("state"), "NOT_LANDED")
        self.assertIn(EXPECTED, row.get("errors") or [])


if __name__ == "__main__":
    unittest.main()
