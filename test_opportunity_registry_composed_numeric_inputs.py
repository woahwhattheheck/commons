#!/usr/bin/env python3
"""Companion coverage for composed inputs using ACACIA's existing JSON guard.

Exercise the real compiler and CLI with a synthetic, complete input tree.
Primitive numeric parsing and selected-root load() are covered separately in
test_opportunity_registry_numeric_json.py; no historical receipt pins are used.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "host/opportunity_registry.py"
SPEC = importlib.util.spec_from_file_location("opportunity_registry_composed_numeric", SOURCE)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


class ComposedNumericInputTests(unittest.TestCase):
    @staticmethod
    def snapshot(root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    @staticmethod
    def fixture(root):
        """A synthetic input tree; does not rely on moving public receipt pins."""
        caps = sorted({cap for group in mod.GRANT_CAPS.values() for cap in group}
                      | {cap for group in mod.COLLAB_CAPS.values() for cap in group}
                      | set(mod.PROCUREMENT_CAPS))
        sources = {
            str(mod.SEED_PATH): {
                "kind": "OPPORTUNITY_SEED", "generated_from_main": mod.BASE_SHA,
                "as_of": mod.AS_OF, "checked_at": mod.AS_OF, "scope": "synthetic fixture",
                "capabilities": [{"id": cap, "name": cap, "status": "SHIPPED_ON_MAIN", "receipts": []}
                                 for cap in caps],
                "compose": [], "seed_programs": [],
            },
            "revenue/ip/grants_ledger.json": {"programs": []},
            "revenue/ip/collaboration_targets.json": {"targets": []},
            "revenue/ip/whitebox_collaboration_offers.json": {
                "generated_at": mod.AS_OF,
                "offers": [{"id": oid, "name": oid, "state": "SCOPING_AVAILABLE",
                            "deliverable": "Synthetic service", "price": {"known": True, "amount_usd": 12.5}}
                           for oid in mod.OFFER_LANE],
            },
            "revenue/distribution/channels.json": {"channels": [], "snapshot_as_of": mod.AS_OF},
            str(mod.SCHEMA_PATH): {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.test/revenue/ip/opportunity_registry.schema.json",
                "additionalProperties": False,
            },
        }
        for rel, value in sources.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
        (root / "titan-hour.html").write_text("Synthetic input only\n", encoding="utf-8")
        return sources

    def test_compile_rejects_overflow_in_each_composed_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.fixture(root)
            for rel in sources:
                if rel == str(mod.SCHEMA_PATH):
                    continue  # main() reads schema; compile_registry() reads the other five.
                with self.subTest(path=rel):
                    path = root / rel
                    original = path.read_text(encoding="utf-8")
                    path.write_text(original[:-1] + ',"numeric_extension":1e309}', encoding="utf-8")
                    before = self.snapshot(root)
                    try:
                        with self.assertRaisesRegex(mod.RegistryError, "non-finite JSON number"):
                            mod.compile_registry(root)
                        self.assertEqual(self.snapshot(root), before)
                    finally:
                        path.write_text(original, encoding="utf-8")

    def test_overflowing_offer_price_is_not_promoted_to_funding_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            path = root / "revenue/ip/whitebox_collaboration_offers.json"
            path.write_text(path.read_text(encoding="utf-8").replace('"amount_usd": 12.5', '"amount_usd": 1e309'),
                            encoding="utf-8")
            with self.assertRaisesRegex(mod.RegistryError, "non-finite JSON number"):
                mod.compile_registry(root)

    def test_finite_compile_and_all_read_commands_remain_usable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            before = self.snapshot(root)
            first = mod.compile_registry(root)
            self.assertEqual(first, mod.compile_registry(root))
            self.assertEqual(self.snapshot(root), before)
            self.assertEqual(first["counts"]["cash_received_usd"], 0)
            self.assertTrue(all(row["applicant_eligibility_state"] == "UNKNOWN" for row in first["opportunities"]))
            for command in ("compile", "validate", "list", "due", "next"):
                result = self.cli(root, command)
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = json.loads(result.stdout)
                self.assertEqual(result.stdout.strip(), json.dumps(parsed, sort_keys=True, separators=(",", ":")))
            self.assertTrue((root / mod.HTML_PATH).is_file())
            self.assertTrue((root / mod.PROOF_PATH).is_file())
            self.assertEqual(mod.load(root)[0], first)

    def cli(self, root, command):
        return subprocess.run([sys.executable, "-B", str(SOURCE), command, "--root", str(root)],
                              capture_output=True, text=True, timeout=15, check=False)

    def test_cli_bad_registry_never_reports_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            registry = mod.compile_registry(root)
            (root / mod.REGISTRY_PATH).write_text(json.dumps(registry)[:-1] + ',"extension":1e309}', encoding="utf-8")
            before = self.snapshot(root)
            for command in ("validate", "list", "due", "next"):
                with self.subTest(command=command):
                    result = self.cli(root, command)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("OPPORTUNITY REGISTRY INVALID: non-finite JSON number", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(self.snapshot(root), before)

    def test_cli_bad_compile_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            self.assertEqual(self.cli(root, "compile").returncode, 0)
            seed = root / mod.SEED_PATH
            seed.write_text(seed.read_text(encoding="utf-8")[:-1] + ',"extension":-1e309}', encoding="utf-8")
            before = self.snapshot(root)
            result = self.cli(root, "compile")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("non-finite JSON number", result.stderr)
            self.assertEqual(self.snapshot(root), before)



if __name__ == "__main__":
    unittest.main()
