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

    def test_cli_run_ignores_predecessor_execute_region_rebind(self) -> None:
        original = a._legacy.execute_region
        substitute_calls: list[tuple[str, Path, Path]] = []

        def substitute(region: str, output: Path, receipt: Path) -> dict[str, object]:
            substitute_calls.append((region, output, receipt))
            output.write_text("forged\n", encoding="utf-8")
            receipt.write_text('{"forged":true}\n', encoding="utf-8")
            return {"region": region, "rows": 999, "output_csv_sha256": "forged"}

        a._legacy.execute_region = substitute
        try:
            with tempfile.TemporaryDirectory() as td:
                collision = Path(td) / "same-path"
                with self.assertRaises(SystemExit) as raised:
                    a.main(
                        [
                            "run",
                            "--region",
                            "northern-ca",
                            "--output",
                            str(collision),
                            "--receipt",
                            str(collision),
                        ]
                    )
                self.assertEqual(2, raised.exception.code)
                self.assertEqual([], substitute_calls)
                self.assertFalse(collision.exists())
        finally:
            a._legacy.execute_region = original

    def test_legacy_cli_reference_is_rebound_to_hardened_dispatch(self) -> None:
        self.assertIs(a._legacy.main, a.main)
        signature = inspect.signature(a.main)
        self.assertEqual(("argv",), tuple(signature.parameters))


if __name__ == "__main__":
    unittest.main()
