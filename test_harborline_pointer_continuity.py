#!/usr/bin/env python3
"""Exercise the existing pointer CLIs against isolated copies of real source files."""
from __future__ import annotations

import copy
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_tally_map as sidecar
import business_pack_harborline_tally_map_pointer as tally
import business_pack_harborline_map_helper_pointer as catalog

MODULES = (sidecar, tally, catalog)
DOOR = "packs/desk-website-service-20260902-01/door.html"
WAITLIST = "packs/waitlist.html"
MAP = "host/harborline_tally_pack_map.py"


class HarborlinePointerContinuityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.law = sidecar.load_law()
        relatives = set()
        for module in MODULES:
            relatives.update(module.EXPECTED_BLOBS)
            relatives.update(module.OBSERVED_AT_LAND)
            for attr in ("MAP_HELPER", "MAP_POINTER_HELPER", "SIDECAR_LEFTOVER", "PEER_HELPER"):
                value = getattr(module, attr, None)
                if value:
                    relatives.add(value)
            for attr in ("POINTER_ID", "MAP_RECEIPT", "TALLY_MAP_POINTER_ID",
                         "TALLY_MAP_POINTER_HELPER_ID", "PEER_HELPER_ID"):
                value = getattr(module, attr, None)
                if value:
                    relatives.add(f"p/{value}.md")
        for relative in relatives:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def classify(self, module, law=None):
        with patch.object(module, "ROOT", self.root):
            return module.classify_pointer(copy.deepcopy(self.law if law is None else law))

    def test_current_pointer_is_valid_without_claiming_historical_byte_identity(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertTrue(result["pointer_ok"])
                self.assertEqual(result["missing_files"], [])
                for relative, actual in result["blobs"].items():
                    payload = (self.root / relative).read_bytes()
                    expected = hashlib.sha1(
                        f"blob {len(payload)}\0".encode() + payload
                    ).hexdigest()[:8]
                    self.assertEqual(actual, expected)
                self.assertEqual(
                    result["blobs_match"],
                    all(result["blobs"][p] == h for p, h in module.EXPECTED_BLOBS.items()),
                )

    def test_page_edits_preserve_pointer_and_expose_changed_bytes(self):
        for relative in (DOOR, WAITLIST):
            target = self.root / relative
            target.write_text(target.read_text() + "\n<!-- independent page revision -->\n")
        for module in MODULES:
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertTrue(result["pointer_ok"])
                self.assertFalse(result["blobs_match"])
                self.assertTrue(result["receipt_blobs_match"])

    def test_helper_edits_do_not_pin_the_operational_source(self):
        target = self.root / MAP
        target.write_text(target.read_text() + "\n# independent helper revision\n")
        for module in MODULES:
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertTrue(result["pointer_ok"])
                self.assertNotEqual(result["blobs"][MAP], module.EXPECTED_BLOBS[MAP])
                self.assertFalse(result["blobs_match"])

    def test_missing_live_targets_are_reported(self):
        for relative in (DOOR, WAITLIST, MAP):
            target = self.root / relative
            saved = target.read_bytes()
            target.unlink()
            try:
                for module in MODULES:
                    with self.subTest(module=module.__name__, path=relative):
                        result = self.classify(module)
                        self.assertFalse(result["pointer_ok"])
                        self.assertIn(relative, result["missing_files"])
            finally:
                target.write_bytes(saved)

    def test_canonical_receipt_edits_are_detected(self):
        for module in MODULES:
            relative = f"p/{module.POINTER_ID}.md"
            target = self.root / relative
            saved = target.read_bytes()
            target.write_bytes(saved + b"\nAltered canonical receipt.\n")
            try:
                with self.subTest(module=module.__name__):
                    result = self.classify(module)
                    self.assertFalse(result["pointer_ok"])
                    self.assertFalse(result["receipt_blobs_match"])
                    self.assertEqual(result["missing_files"], [])
            finally:
                target.write_bytes(saved)

    def test_missing_receipts_are_reported(self):
        for module in MODULES:
            relative = f"p/{module.POINTER_ID}.md"
            target = self.root / relative
            saved = target.read_bytes()
            target.unlink()
            try:
                with self.subTest(module=module.__name__):
                    result = self.classify(module)
                    self.assertFalse(result["pointer_ok"])
                    self.assertFalse(result["receipt_blobs_match"])
                    self.assertIn(relative, result["missing_files"])
            finally:
                target.write_bytes(saved)

    def test_incorrect_catalog_link_is_still_invalid(self):
        law = copy.deepcopy(self.law)
        law["instances"]["harborline_tally_pack_map_pointer"] = "different-pointer"
        for module in MODULES:
            with self.subTest(module=module.__name__):
                self.assertFalse(self.classify(module, law)["pointer_ok"])

    def test_classification_does_not_mutate_source_or_law(self):
        before_law = copy.deepcopy(self.law)
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        for module in MODULES:
            self.classify(module)
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before_law, self.law)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
