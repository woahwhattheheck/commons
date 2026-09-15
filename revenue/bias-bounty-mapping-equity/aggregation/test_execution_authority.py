from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

import aggregate as a


class ExecutionAuthorityTests(unittest.TestCase):
    def test_authoritative_entrypoint_has_no_dependency_injection_surface(self) -> None:
        signature = inspect.signature(a.execute_region)
        self.assertEqual(("region", "output", "receipt"), tuple(signature.parameters))
        self.assertIs(a._legacy.execute_region, a.execute_region)
        self.assertIsNone(a.execute_region.__defaults__)
        self.assertIsNone(a.execute_region.__kwdefaults__)

    def test_predecessor_dependency_substitution_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(TypeError):
                a.execute_region(
                    "northern-ca",
                    root / "out.csv",
                    root / "receipt.json",
                    _materializer=lambda _region: None,
                )
            self.assertFalse((root / "out.csv").exists())
            self.assertFalse((root / "receipt.json").exists())

    def test_authoritative_entrypoint_factory_is_not_exported(self) -> None:
        self.assertFalse(hasattr(a, "_make_authoritative_execute_region"))


if __name__ == "__main__":
    unittest.main()
