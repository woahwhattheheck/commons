#!/usr/bin/env python3
"""Real-file regression coverage for waitlist catalog pointer continuity."""
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

import business_pack_instance_waitlist as catalog
import business_pack_pixel_gate_helper_pointer as helper
import business_pack_waitlist_pixel_gate_pointer as pixel

MODULES = (catalog, helper, pixel)
WAITLIST = "packs/waitlist.html"
THANKS = "packs/thanks.html"
HARBORLINE = "packs/desk-website-service-20260902-01/door.html"


class WaitlistPointerContinuityTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.law = catalog.load_law()
        relatives = set()
        for module in MODULES:
            relatives.update(module.EXPECTED_BLOBS)
            relatives.update(getattr(module, "OBSERVED_AT_LAND", {}))
            for attr in ("POINTER_ID", "HELPER_ID", "PEER_HELPER_ID",
                         "LEFTOVER_HELPER_RECEIPT", "PIXEL_GATE_RECEIPT"):
                value = getattr(module, attr, None)
                if value:
                    relatives.add(f"p/{value}.md")
        for relative in relatives:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def classify(self, module, law=None):
        value = copy.deepcopy(self.law) if law is None else law
        call = catalog.classify_catalog if module is catalog else module.classify_pointer
        with patch.object(module, "ROOT", self.root):
            return call(value)

    def test_live_page_edits_preserve_pointer_with_visible_hash_drift(self):
        for relative in (WAITLIST, THANKS):
            target = self.root / relative
            target.write_bytes(target.read_bytes() + b"\n<!-- Independent revision -->\n")
        for module in MODULES:
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertTrue(result["pointer_ok"])
                self.assertTrue(result["receipt_blobs_match"])
                self.assertFalse(result.get("blobs_match", result.get("waitlist_blob_ok")))
                self.assertNotEqual(result["blobs"][WAITLIST], "b312ed6d")

    def test_operational_helper_changes_remain_observations(self):
        target = self.root / helper.LEFTOVER_HELPER
        target.write_bytes(target.read_bytes() + b"\n# Independent helper revision\n")
        for module in (helper, pixel):
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertTrue(result["pointer_ok"])
                self.assertFalse(result["blobs_match"])
        self.assertFalse(self.classify(helper)["did_not_overwrite_leftover_helper"])

    def test_missing_shared_waitlist_invalidates_every_pointer(self):
        (self.root / WAITLIST).unlink()
        for module in MODULES:
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertFalse(result["pointer_ok"])
                self.assertIn(WAITLIST, result["missing_files"])

    def test_missing_thanks_page_invalidates_pixel_pointers(self):
        (self.root / THANKS).unlink()
        for module in (helper, pixel):
            with self.subTest(module=module.__name__):
                result = self.classify(module)
                self.assertFalse(result["pointer_ok"])
                self.assertIn(THANKS, result["missing_files"])

    def test_changed_or_missing_receipt_is_not_live_page_evolution(self):
        for module in MODULES:
            relative = f"p/{module.POINTER_ID}.md"
            target = self.root / relative
            original = target.read_bytes()
            try:
                target.write_bytes(original + b"\nChanged canonical receipt.\n")
                with self.subTest(module=module.__name__, state="changed"):
                    result = self.classify(module)
                    self.assertFalse(result["pointer_ok"])
                    self.assertFalse(result["receipt_blobs_match"])
                    self.assertEqual(result["missing_files"], [])
                target.unlink()
                with self.subTest(module=module.__name__, state="missing"):
                    result = self.classify(module)
                    self.assertFalse(result["pointer_ok"])
                    self.assertIn(relative, result["missing_files"])
            finally:
                target.write_bytes(original)

    def test_catalog_preserves_missing_door_verdict(self):
        (self.root / HARBORLINE).unlink()
        result = self.classify(catalog)
        row = next(row for row in result["rows"] if row["brand"] == "Harborline Local Sites")
        self.assertEqual(row["verdict"], catalog.WAITLIST_DOOR_MISSING)
        self.assertFalse(result["pointer_ok"])

    def test_catalog_preserves_required_harborline_waitlist_link(self):
        (self.root / HARBORLINE).write_text("<p>Page without a waitlist link.</p>")
        result = self.classify(catalog)
        row = next(row for row in result["rows"] if row["brand"] == "Harborline Local Sites")
        self.assertEqual(row["verdict"], catalog.WAITLIST_CATALOG_POINTER)
        self.assertFalse(result["pointer_ok"])

    def test_incorrect_pointer_links_and_opt_out_metadata_remain_invalid(self):
        keys = (
            (catalog, "instances", "catalog_waitlist_rows_pointer", "other-pointer"),
            (helper, "waitlist", "pixel_gate_helper_pointer", "other-pointer"),
            (pixel, "waitlist", "pixel_gate_pointer", "other-pointer"),
            (pixel, "waitlist", "ccpa_opt_out_blocks_thanks_pixels", False),
            (pixel, "waitlist", "empty_slots_load_nothing", False),
        )
        for module, section, field, value in keys:
            with self.subTest(module=module.__name__, field=field):
                law = copy.deepcopy(self.law)
                law[section][field] = value
                self.assertFalse(self.classify(module, law)["pointer_ok"])

    def test_current_hash_reporting_and_read_only_behavior(self):
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        for module in MODULES:
            law = copy.deepcopy(self.law)
            result = self.classify(module, law)
            self.assertEqual(law, self.law)
            self.assertTrue(result["pointer_ok"])
            for relative, actual in result["blobs"].items():
                data = before[Path(relative)]
                expected = hashlib.sha1(
                    f"blob {len(data)}\0".encode() + data
                ).hexdigest()[:8]
                self.assertEqual(actual, expected)
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
