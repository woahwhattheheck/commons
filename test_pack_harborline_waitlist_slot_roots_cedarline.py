#!/usr/bin/env python3
"""Real paired-directory regressions for Harborline's selected-root reads.

Only filesystem locations and fixture hash pins are patched. The complete
production module, waitlist validator and copy validator execute unchanged.
No template, law, receipt or acceptance pin in the repository is modified.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "host"))
import pack_harborline_waitlist_slot as slot
import pack_waitlist as waitlist
import business_pack_unique as unique

SHEET = "packs/desk-website-service-20260902-01/waitlist-slot.md"
MANIFEST = "packs/desk-website-service-20260902-01/manifest.json"
DOOR = "packs/waitlist.html"
LAW = "ground/BUSINESS_PACK_WAITLIST.json"
TEMPLATE = "packs/_template/waitlist-slot.md"
PINS = {
    TEMPLATE: "TEMPLATE_BLOB",
    DOOR: "WAITLIST_DOOR_BLOB",
    "host/pack_waitlist.py": "WAITLIST_HELPER_BLOB",
    LAW: "WAITLIST_LAW_BLOB",
    "packs/desk-website-service-20260902-01/door.html": "DOOR_BLOB",
    "packs/desk-website-service-20260902-01/rating.md": "RATING_BLOB",
    "host/business_pack_harborline_tally_map.py": "SIDECAR_BLOB",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "POINTER_RECEIPT_BLOB",
    "p/cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01.md": "SLOT_POINTER_RECEIPT_BLOB",
    SHEET: "SHEET_BLOB",
    "p/cursor-pack-harborline-waitlist-slot-20260902-01.md": "LEFTOVER_RECEIPT_BLOB",
}


def write(root: Path, rel: str, text: str | bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))


def blob(root: Path, rel: str, length: int = 8) -> str:
    path = root / rel
    if not path.is_file():
        return ""
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()[:length]


def make_tree(root: Path, marker: str) -> None:
    for rel in PINS:
        write(root, rel, f"synthetic fixture {marker}: {rel}\n")
    write(root, TEMPLATE, f"packs/waitlist.html\n{marker}\n")
    write(root, LAW, json.dumps({"id": slot.LAW_ID, "fixture": marker}))
    write(root, DOOR, (
        '<meta name="robots" content="index, follow"><form>'
        '<input type="email"><select name="tier"></select>'
        '<select name="state"></select></form>'
        'May reach you on X, TikTok and Meta; unsubscribe any time. '
        + waitlist.CCPA_PHRASE + f" <!-- {marker} -->"
    ))
    write(root, SHEET, "\n".join((
        "Harborline Local Sites", slot.LAW_ID, slot.SCOUT_ID, slot.POINTER_ID,
        "packs/waitlist.html", slot.CCPA_PHRASE, "NOT_MINTED", "Zero sends",
        "not a second list", "Did not invent manifest.json", marker, "",
    )))


class HarborlineSelectedRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.checkout = Path(self.tmp.name) / "checkout"
        self.selected = Path(self.tmp.name) / "selected"
        make_tree(self.checkout, "checkout-a")
        make_tree(self.selected, "selected-b")
        stack = ExitStack()
        self.addCleanup(stack.close)
        old_path = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), old_path))
        stack.enter_context(patch.multiple(
            slot, ROOT=self.checkout, HARBORLINE=self.checkout / SHEET,
            MANIFEST=self.checkout / MANIFEST, TEMPLATE=self.checkout / TEMPLATE,
        ))
        stack.enter_context(patch.multiple(
            waitlist, DEFAULT_LAW=self.checkout / LAW,
            DEFAULT_DOOR=self.checkout / DOOR,
            DEFAULT_SLOT=self.checkout / TEMPLATE,
        ))

    def pins(self, root: Path):
        return patch.multiple(slot, **{name: blob(root, rel) for rel, name in PINS.items()})

    def same_trees(self) -> None:
        shutil.copytree(self.checkout, self.selected, dirs_exist_ok=True)

    def test_blob_helper_selects_explicit_root(self):
        self.assertNotEqual(blob(self.checkout, SHEET), blob(self.selected, SHEET))
        self.assertEqual(slot.git_blob_prefix(SHEET, root=self.selected), blob(self.selected, SHEET))

    def test_blob_helper_preserves_positional_length_and_default_root(self):
        self.assertEqual(slot.git_blob_prefix(SHEET, 40), blob(self.checkout, SHEET, 40))
        self.assertEqual(slot.git_blob_prefix(SHEET), blob(self.checkout, SHEET))

    def test_blob_helper_preserves_exact_binary_bytes(self):
        raw = b"\x00\xff\r\n" + "snowman \u2603".encode("utf-8") + b"\n"
        write(self.selected, "binary.dat", raw)
        expected = subprocess.check_output(["git", "hash-object", "--stdin"], input=raw).decode().strip()
        self.assertEqual(slot.git_blob_prefix("binary.dat", 40, root=self.selected), expected)

    def test_blob_helper_missing_selected_file_does_not_fall_back(self):
        write(self.checkout, "only-local.txt", "local")
        self.assertEqual(slot.git_blob_prefix("only-local.txt", root=self.selected), "")

    def test_all_eleven_hashes_and_final_verdict_use_selected_root(self):
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["blobs"], {rel: blob(self.selected, rel) for rel in PINS})
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")

    def test_each_changed_selected_file_prevents_stale_checkout_success(self):
        self.same_trees()
        with self.pins(self.checkout):
            for rel in PINS:
                with self.subTest(path=rel):
                    path = self.selected / rel
                    original = path.read_bytes()
                    # Whitespace is valid trailing JSON and harmless copy/HTML,
                    # so this isolates the actual-byte pin, not other validators.
                    path.write_bytes(original + b" \n")
                    try:
                        result = slot.classify_tree(self.selected)
                        self.assertEqual(result["blobs"][rel], blob(self.selected, rel))
                        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")
                    finally:
                        path.write_bytes(original)

    def test_each_missing_selected_file_has_empty_hash(self):
        self.same_trees()
        for rel in PINS:
            with self.subTest(path=rel):
                path = self.selected / rel
                original = path.read_bytes()
                path.unlink()
                try:
                    result = slot.classify_tree(self.selected)
                    self.assertEqual(result["blobs"][rel], "")
                    self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")
                finally:
                    path.write_bytes(original)

    def test_selected_manifest_is_detected(self):
        self.same_trees()
        write(self.selected, MANIFEST, "{}")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertFalse(result["did_not_invent_harborline_manifest"])
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_unrelated_checkout_manifest_is_ignored(self):
        self.same_trees()
        write(self.checkout, MANIFEST, "{}")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertTrue(result["did_not_invent_harborline_manifest"])
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")

    def test_selected_copy_is_validated(self):
        self.same_trees()
        path = self.selected / SHEET
        path.write_text(path.read_text(encoding="utf-8") + "Earn $100\n", encoding="utf-8")
        self.assertEqual(unique.classify_copy(path.read_text(encoding="utf-8"))["verdict"], "EARNINGS_CLAIM")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertFalse(result["copy_ok"])
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_unrelated_checkout_copy_does_not_poison_selected_tree(self):
        path = self.checkout / SHEET
        path.write_text(path.read_text(encoding="utf-8") + "Earn $100\n", encoding="utf-8")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertTrue(result["copy_ok"])
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")

    def test_selected_shared_door_is_validated(self):
        write(self.selected, DOOR, "<p>Missing form</p>")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["waitlist_door"], "WAITLIST_DOOR_INCOMPLETE")
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_missing_selected_shared_door_stays_missing(self):
        (self.selected / DOOR).unlink()
        self.assertEqual(slot.classify_tree(self.selected)["waitlist_door"], "WAITLIST_DOOR_MISSING")

    def test_selected_law_is_loaded(self):
        write(self.selected, LAW, json.dumps({"id": "different-selected-law"}))
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["law_id"], "different-selected-law")
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_missing_selected_law_does_not_fall_back(self):
        (self.selected / LAW).unlink()
        self.assertEqual(slot.classify_tree(self.selected)["law_id"], "")

    def test_malformed_selected_law_keeps_real_parser_error(self):
        write(self.selected, LAW, "{broken")
        with self.assertRaises(json.JSONDecodeError):
            slot.classify_tree(self.selected)

    def test_non_object_selected_law_keeps_real_loader_error(self):
        write(self.selected, LAW, "[]")
        with self.assertRaisesRegex(ValueError, "not an object"):
            slot.classify_tree(self.selected)

    def test_no_argument_behavior_and_explicit_same_root_agree(self):
        with self.pins(self.checkout):
            default = slot.classify_tree()
            explicit = slot.classify_tree(self.checkout)
        self.assertEqual(default["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")
        self.assertEqual(default, explicit)
        self.assertEqual(default["sends"], 0)
        self.assertEqual(default["checkout"], "NOT_MINTED")
        self.assertFalse(default["gate"])
        self.assertFalse(default["commons_admission"])

    def test_calls_across_two_roots_do_not_mutate_shared_defaults(self):
        second = Path(self.tmp.name) / "second-selection"
        make_tree(second, "selected-c")
        write(self.selected, LAW, json.dumps({"id": "selection-b"}))
        write(second, LAW, json.dumps({"id": "selection-c"}))
        before = (waitlist.DEFAULT_LAW, waitlist.DEFAULT_DOOR, waitlist.DEFAULT_SLOT)
        roots = [self.selected, second] * 16
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(slot.classify_tree, roots))
        self.assertEqual([r["law_id"] for r in results], ["selection-b", "selection-c"] * 16)
        for root, result in zip(roots, results):
            self.assertEqual(result["blobs"], {rel: blob(root, rel) for rel in PINS})
        self.assertEqual(before, (waitlist.DEFAULT_LAW, waitlist.DEFAULT_DOOR, waitlist.DEFAULT_SLOT))

    def test_absent_selected_root_never_borrows_checkout_evidence(self):
        result = slot.classify_tree(Path(self.tmp.name) / "does-not-exist")
        self.assertEqual(result["harborline"]["verdict"], "HARBORLINE_WAITLIST_SLOT_MISSING")
        self.assertEqual(result["waitlist_door"], "WAITLIST_DOOR_MISSING")
        self.assertEqual(result["law_id"], "")
        self.assertEqual(result["blobs"], dict.fromkeys(PINS, ""))
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_tree_classification_does_not_change_fixture_bytes(self):
        before = {str(p.relative_to(self.tmp.name)): p.read_bytes()
                  for p in Path(self.tmp.name).rglob("*") if p.is_file()}
        with self.pins(self.selected):
            slot.classify_tree(self.selected)
        after = {str(p.relative_to(self.tmp.name)): p.read_bytes()
                 for p in Path(self.tmp.name).rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
