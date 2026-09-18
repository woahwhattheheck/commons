#!/usr/bin/env python3
"""Harborline's selected checkout supplies its hashes, law and manifest."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_rating as factory  # noqa: E402
import pack_harborline_rating as rating  # noqa: E402


LAW = Path("ground/BUSINESS_PACK_RATING.json")
SHEET = "packs/desk-website-service-20260902-01/rating.md"
MANIFEST = "packs/desk-website-service-20260902-01/manifest.json"
PIN_PATHS = {
    "TEMPLATE_BLOB": "packs/_template/rating.md",
    "DOOR_BLOB": "packs/desk-website-service-20260902-01/door.html",
    "SHEET_BLOB": SHEET,
    "WAITLIST_SLOT_BLOB": "packs/desk-website-service-20260902-01/waitlist-slot.md",
    "LEFTOVER_RECEIPT_BLOB": "p/cursor-pack-harborline-rating-20260902-01.md",
    "SIDECAR_BLOB": "host/business_pack_harborline_tally_map.py",
    "MAP_POINTER_BLOB": "host/business_pack_harborline_tally_map_pointer.py",
    "MAP_HELPER_POINTER_BLOB": "host/business_pack_harborline_map_helper_pointer.py",
    "PACK_MAP_BLOB": "host/harborline_tally_pack_map.py",
    "PIN_LIFT_RECEIPT_BLOB": "p/cursor-pack-harborline-map-pin-lift-20260902-01.md",
    "POINTER_RECEIPT_BLOB": "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
}
SHEET_TEXT = """# Third-party rating slot — Harborline Local Sites
id: cursor-business-pack-rating-slot-20260902-01
Badge URL: `OWNER_UNSET`
Report URL: `OWNER_UNSET`
Partner name: `OWNER_UNSET`
Bulk price: `OWNER_UNSET`
Owner pasted: no
Checkout stays `NOT_MINTED`.
"""


def blob_prefix(path: Path) -> str:
    if not path.is_file():
        return ""
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()[:8]


class HarborlineRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="harborline-roots-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.default = self.parent / "default"
        self.alternate = self.parent / "alternate"
        for root in (self.default, self.alternate):
            for rel in PIN_PATHS.values():
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                content = SHEET_TEXT if rel == SHEET else "fixture for " + rel + "\n"
                target.write_text(content + root.name + "\n", encoding="utf-8")
            (root / LAW).parent.mkdir(parents=True, exist_ok=True)
            (root / LAW).write_text(json.dumps({
                "id": rating.FACTORY_ID if root == self.default else "alternate-law",
                "badge_url": "OWNER_UNSET", "report_url": "OWNER_UNSET",
            }), encoding="utf-8")
        for obj, attr, value in (
            (rating, "ROOT", self.default),
            (rating, "MANIFEST", self.default / MANIFEST),
            (factory, "DEFAULT_LAW", self.default / LAW),
        ):
            context = patch.object(obj, attr, value)
            context.start()
            self.addCleanup(context.stop)

    def expected_blobs(self, root: Path) -> dict[str, str]:
        return {rel: blob_prefix(root / rel) for rel in PIN_PATHS.values()}

    def fixture_pins(self, root: Path):
        # Bind the unchanged acceptance predicate to real fixture bytes only.
        # No product files or historical repository pins are changed.
        return patch.multiple(rating, **{
            name: blob_prefix(root / rel) for name, rel in PIN_PATHS.items()
        })

    def test_selected_root_supplies_all_eleven_hashes(self) -> None:
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["blobs"], self.expected_blobs(self.alternate))
        self.assertEqual(row["harborline"]["path"], str(self.alternate / SHEET))
        self.assertEqual(row["harborline"]["verdict"], "HARBORLINE_RATING_INSTANCE_OK")

    def test_selected_root_supplies_law_metadata(self) -> None:
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["factory_id"], "alternate-law")
        self.assertFalse(row["did_not_remint_factory_slot"])

    def test_missing_selected_file_is_not_borrowed_from_default(self) -> None:
        rel = PIN_PATHS["TEMPLATE_BLOB"]
        (self.alternate / rel).unlink()
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["blobs"][rel], "")
        self.assertFalse(row["did_not_rewrite_goat_template"])

    def test_alternate_checkout_works_without_default_law(self) -> None:
        (self.default / LAW).unlink()
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["factory_id"], "alternate-law")
        self.assertEqual(row["harborline"]["factory_verdict"], "RATING_SLOT_EMPTY")

    def test_missing_selected_law_is_not_borrowed_from_default(self) -> None:
        (self.alternate / LAW).unlink()
        with self.assertRaises(FileNotFoundError):
            rating.classify_tree(self.alternate)

    def test_malformed_selected_law_retains_existing_validation(self) -> None:
        (self.alternate / LAW).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "law is not an object"):
            rating.classify_tree(self.alternate)

    def test_relative_selected_root(self) -> None:
        previous = Path.cwd()
        try:
            os.chdir(self.parent)
            row = rating.classify_tree(Path("alternate"))
        finally:
            os.chdir(previous)
        self.assertEqual(row["blobs"], self.expected_blobs(self.alternate))
        self.assertEqual(row["factory_id"], "alternate-law")

    def test_concurrent_readers_keep_roots_separate(self) -> None:
        roots = [self.default, self.alternate] * 4
        (self.alternate / MANIFEST).write_text("{}", encoding="utf-8")
        with ThreadPoolExecutor(max_workers=2) as executor:
            rows = list(executor.map(rating.classify_tree, roots))
        for root, row in zip(roots, rows):
            self.assertEqual(row["blobs"], self.expected_blobs(root))
            self.assertEqual(row["did_not_invent_harborline_manifest"], root == self.default)

    def test_reading_alternate_root_preserves_files_and_default_behavior(self) -> None:
        before = rating.classify_tree()
        contents = {str(p): p.read_bytes() for p in self.parent.rglob("*") if p.is_file()}
        rating.classify_tree(self.alternate)
        self.assertEqual(rating.classify_tree(), before)
        self.assertEqual(contents, {
            str(p): p.read_bytes() for p in self.parent.rglob("*") if p.is_file()
        })
        self.assertEqual(rating.ROOT, self.default)
        self.assertEqual(rating.MANIFEST, self.default / MANIFEST)
        self.assertEqual(factory.DEFAULT_LAW, self.default / LAW)

    def test_legacy_default_blob_hook_keeps_its_signature(self) -> None:
        original = rating.git_blob_prefix
        calls = []

        def legacy(rel: str, n: int = 8) -> str:
            calls.append(rel)
            return original(rel, n)

        with patch.object(rating, "git_blob_prefix", legacy):
            row = rating.classify_tree()
        self.assertEqual(set(calls), set(PIN_PATHS.values()))
        self.assertEqual(row["blobs"], self.expected_blobs(self.default))

    def test_no_argument_call_preserves_explicit_manifest_override(self) -> None:
        custom = self.parent / "explicit-manifest.json"
        custom.write_text("{}", encoding="utf-8")
        with patch.object(rating, "MANIFEST", custom):
            self.assertFalse(rating.classify_tree()["did_not_invent_harborline_manifest"])

    def test_selected_manifest_presence_is_reported(self) -> None:
        (self.alternate / MANIFEST).write_text("{}", encoding="utf-8")
        row = rating.classify_tree(self.alternate)
        self.assertFalse(row["did_not_invent_harborline_manifest"])

    def test_default_manifest_presence_does_not_leak_into_selected_root(self) -> None:
        (self.default / MANIFEST).write_text("{}", encoding="utf-8")
        row = rating.classify_tree(self.alternate)
        self.assertTrue(row["did_not_invent_harborline_manifest"])

    def test_selected_root_can_satisfy_the_original_acceptance_predicate(self) -> None:
        (self.alternate / LAW).write_text(json.dumps({"id": rating.FACTORY_ID}), encoding="utf-8")
        (self.default / MANIFEST).write_text("{}", encoding="utf-8")
        with self.fixture_pins(self.alternate):
            row = rating.classify_tree(self.alternate)
        self.assertEqual(row["verdict"], "HARBORLINE_RATING_OK")
        self.assertFalse(row["gate"])
        self.assertEqual(row["sends"], 0)
        self.assertEqual(row["checkout"], "NOT_MINTED")

    def test_selected_manifest_prevents_acceptance_even_with_matching_hashes(self) -> None:
        (self.alternate / LAW).write_text(json.dumps({"id": rating.FACTORY_ID}), encoding="utf-8")
        (self.alternate / MANIFEST).write_text("{}", encoding="utf-8")
        with self.fixture_pins(self.alternate):
            row = rating.classify_tree(self.alternate)
        self.assertEqual(row["verdict"], "HARBORLINE_RATING_INCOMPLETE")
        self.assertFalse(row["did_not_invent_harborline_manifest"])

    def test_explicit_sheet_law_uses_the_landed_factory_extension(self) -> None:
        (self.default / LAW).unlink()
        row = rating.classify_path(self.alternate / SHEET, law_path=self.alternate / LAW)
        self.assertEqual(row["verdict"], "HARBORLINE_RATING_INSTANCE_OK")


if __name__ == "__main__":
    unittest.main()
