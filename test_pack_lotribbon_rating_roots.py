#!/usr/bin/env python3
"""Keep alternate LotRibbon checkout measurements within their selected root."""
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
import pack_lotribbon_rating as rating  # noqa: E402


LAW = Path("ground/BUSINESS_PACK_RATING.json")
SHEET = "packs/lotribbon-greetings-20260902-01/rating.md"
BLOB_PATHS = (
    "packs/_template/rating.md",
    "packs/lotribbon-greetings-20260902-01/index.html",
    SHEET,
    "p/cursor-lead-lotribbon-rating-20260902-01.md",
    "packs/desk-website-service-20260902-01/rating.md",
    "p/cursor-pack-harborline-rating-20260902-01.md",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
    "p/stamp-claude-peer-check-a4-yard-adopt-20260902-01.md",
    "p/cursor-claude-peer-check-a4-desk-test-adopt-20260902-01.md",
)
SHEET_TEXT = """# Third-party rating slot — LotRibbon Greetings
id: cursor-business-pack-rating-slot-20260902-01
Door blob 7804ec33 unread.
cursor-pack-harborline-rating-peer-unpin-20260902-01 stays bc-31c8ef9a.
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


class LotRibbonRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="lotribbon-roots-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.default = self.parent / "default"
        self.alternate = self.parent / "alternate"
        for root in (self.default, self.alternate):
            for rel in BLOB_PATHS:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                content = SHEET_TEXT if rel == SHEET else "fixture for " + rel + "\n"
                target.write_text(content + root.name + "\n", encoding="utf-8")
            (root / "p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md").write_text(
                "present\n", encoding="utf-8"
            )
            (root / LAW).parent.mkdir(parents=True, exist_ok=True)
            (root / LAW).write_text(json.dumps({
                "id": rating.FACTORY_ID if root == self.default else "alternate-law",
                "unique_pack_id": root.name,
                "badge_url": "OWNER_UNSET", "report_url": "OWNER_UNSET",
            }), encoding="utf-8")
        for obj, attr, value in (
            (rating, "ROOT", self.default),
            (factory, "DEFAULT_LAW", self.default / LAW),
        ):
            context = patch.object(obj, attr, value)
            context.start()
            self.addCleanup(context.stop)

    def expected_blobs(self, root: Path) -> dict[str, str]:
        return {rel: blob_prefix(root / rel) for rel in BLOB_PATHS}

    def test_selected_root_hashes_every_reported_file(self) -> None:
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["blobs"], self.expected_blobs(self.alternate))
        self.assertEqual(row["lotribbon"]["path"], str(self.alternate / SHEET))
        self.assertEqual(row["lotribbon"]["verdict"], "LOTRIBBON_RATING_INSTANCE_OK")

    def test_missing_selected_file_does_not_borrow_default_blob(self) -> None:
        (self.alternate / BLOB_PATHS[0]).unlink()
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["blobs"][BLOB_PATHS[0]], "")
        self.assertFalse(row["did_not_rewrite_goat_template"])

    def test_selected_root_uses_its_law(self) -> None:
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["factory_id"], "alternate-law")
        self.assertFalse(row["did_not_remint_factory_slot"])

    def test_selected_root_does_not_require_default_law(self) -> None:
        (self.default / LAW).unlink()
        row = rating.classify_tree(self.alternate)
        self.assertEqual(row["factory_id"], "alternate-law")
        self.assertEqual(row["lotribbon"]["factory_verdict"], "RATING_SLOT_EMPTY")

    def test_missing_selected_law_does_not_borrow_default_law(self) -> None:
        (self.alternate / LAW).unlink()
        with self.assertRaises(FileNotFoundError):
            rating.classify_tree(self.alternate)

    def test_malformed_selected_law_preserves_existing_validation(self) -> None:
        (self.alternate / LAW).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "law is not an object"):
            rating.classify_tree(self.alternate)

    def test_relative_root_uses_relative_tree(self) -> None:
        previous = Path.cwd()
        try:
            os.chdir(self.parent)
            row = rating.classify_tree(Path("alternate"))
        finally:
            os.chdir(previous)
        self.assertEqual(row["blobs"], self.expected_blobs(self.alternate))
        self.assertEqual(row["factory_id"], "alternate-law")

    def test_default_call_remains_unchanged_after_alternate_read(self) -> None:
        before = rating.classify_tree()
        files_before = {str(p): p.read_bytes() for p in self.parent.rglob("*") if p.is_file()}
        rating.classify_tree(self.alternate)
        after = rating.classify_tree()
        self.assertEqual(before, after)
        self.assertEqual(after["blobs"], self.expected_blobs(self.default))
        self.assertEqual(after["factory_id"], rating.FACTORY_ID)
        self.assertEqual(rating.ROOT, self.default)
        self.assertEqual(factory.DEFAULT_LAW, self.default / LAW)
        self.assertEqual(files_before, {
            str(p): p.read_bytes() for p in self.parent.rglob("*") if p.is_file()
        })

    def test_concurrent_root_reads_stay_separate(self) -> None:
        roots = [self.default, self.alternate] * 4
        with ThreadPoolExecutor(max_workers=2) as executor:
            rows = list(executor.map(rating.classify_tree, roots))
        for root, row in zip(roots, rows):
            self.assertEqual(row["blobs"], self.expected_blobs(root))
            expected_id = rating.FACTORY_ID if root == self.default else "alternate-law"
            self.assertEqual(row["factory_id"], expected_id)

    def test_selected_root_can_satisfy_all_existing_pins(self) -> None:
        law = self.alternate / LAW
        law.write_text(json.dumps({"id": rating.FACTORY_ID}), encoding="utf-8")
        sheet = self.alternate / SHEET
        sheet.write_text(sheet.read_text(encoding="utf-8").replace(
            rating.DOOR_BLOB, blob_prefix(self.alternate / BLOB_PATHS[1])
        ), encoding="utf-8")
        pin_paths = {
            "TEMPLATE_BLOB": BLOB_PATHS[0], "DOOR_BLOB": BLOB_PATHS[1],
            "SHEET_BLOB": SHEET, "ORIGINAL_RECEIPT_BLOB": BLOB_PATHS[3],
            "HARBORLINE_SHEET_BLOB": BLOB_PATHS[4],
            "HARBORLINE_RECEIPT_BLOB": BLOB_PATHS[5], "POINTER_RECEIPT_BLOB": BLOB_PATHS[6],
        }
        # Fixture-specific expected hashes exercise the unchanged acceptance
        # predicate; no repository pins or product files are modified.
        with patch.multiple(rating, **{
            key: blob_prefix(self.alternate / rel) for key, rel in pin_paths.items()
        }):
            row = rating.classify_tree(self.alternate)
        self.assertEqual(row["verdict"], "LOTRIBBON_RATING_OK")
        self.assertFalse(row["gate"])
        self.assertEqual(row["sends"], 0)

    def test_default_blob_hook_keeps_legacy_signature(self) -> None:
        original = rating.git_blob_prefix
        calls = []

        def legacy(rel: str, n: int = 8) -> str:
            calls.append(rel)
            return original(rel, n)

        with patch.object(rating, "git_blob_prefix", legacy):
            row = rating.classify_tree()
        self.assertEqual(set(calls), set(BLOB_PATHS))
        self.assertEqual(row["blobs"], self.expected_blobs(self.default))

    def test_factory_default_and_explicit_law_paths(self) -> None:
        default = factory.classify_rating()
        selected = factory.classify_rating(law_path=self.alternate / LAW)
        self.assertEqual(default["id"], rating.FACTORY_ID)
        self.assertEqual(selected["id"], "alternate-law")
        self.assertEqual(selected["unique_pack_id"], "alternate")
        self.assertEqual(default["verdict"], selected["verdict"])
        self.assertEqual(selected["checkout"], "NOT_MINTED")

    def test_factory_explicit_pack_fields_and_rating_rules_preserved(self) -> None:
        kwargs = {"law_path": self.alternate / LAW}
        empty = factory.classify_rating({"badge_url": "OWNER_UNSET", "report_url": "OWNER_UNSET"}, **kwargs)
        invented = factory.classify_rating({"badge_url": "https://example.invalid/badge"}, **kwargs)
        filled = factory.classify_rating({
            "badge_url": "https://example.invalid/badge", "report_url": "https://example.invalid/report",
            "owner_pasted_rating": True,
        }, **kwargs)
        self.assertEqual(empty["verdict"], "RATING_SLOT_EMPTY")
        self.assertEqual(invented["verdict"], "RATING_LINK_INVENTED")
        self.assertEqual(filled["verdict"], "RATING_SLOT_OWNER_FILLED")
        self.assertFalse(filled["gate"])
        self.assertFalse(filled["agents_spend_ads"])

    def test_explicit_sheet_law_does_not_require_default_checkout(self) -> None:
        (self.default / LAW).unlink()
        row = rating.classify_path(self.alternate / SHEET, law_path=self.alternate / LAW)
        self.assertEqual(row["verdict"], "LOTRIBBON_RATING_INSTANCE_OK")


if __name__ == "__main__":
    unittest.main()
