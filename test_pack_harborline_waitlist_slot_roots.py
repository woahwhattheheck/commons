#!/usr/bin/env python3
"""Selected-root regressions using real files and isolated classifier boundaries.

The shared door/copy classifiers are input-recording doubles: this suite tests
which tree is read, not the classifiers' existing content policies.
"""
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).parent / "host" / "pack_harborline_waitlist_slot.py"
SHEET = "packs/desk-website-service-20260902-01/waitlist-slot.md"
MANIFEST = "packs/desk-website-service-20260902-01/manifest.json"
PATHS = {
    "packs/_template/waitlist-slot.md": "TEMPLATE_BLOB",
    "packs/waitlist.html": "WAITLIST_DOOR_BLOB",
    "host/pack_waitlist.py": "WAITLIST_HELPER_BLOB",
    "ground/BUSINESS_PACK_WAITLIST.json": "WAITLIST_LAW_BLOB",
    "packs/desk-website-service-20260902-01/door.html": "DOOR_BLOB",
    "packs/desk-website-service-20260902-01/rating.md": "RATING_BLOB",
    "host/business_pack_harborline_tally_map.py": "SIDECAR_BLOB",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "POINTER_RECEIPT_BLOB",
    "p/cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01.md": "SLOT_POINTER_RECEIPT_BLOB",
    SHEET: "SHEET_BLOB",
    "p/cursor-pack-harborline-waitlist-slot-20260902-01.md": "LEFTOVER_RECEIPT_BLOB",
}


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def blob(path, n=8):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()[:n]


class SelectedRootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name) / "module-tree"
        self.selected = Path(self.temp.name) / "selected-tree"
        self.waitlist = types.ModuleType("pack_waitlist")
        self.waitlist.classify = Mock(return_value={"verdict": "LOCAL_DOOR", "law_id": "local-law", "sends": 0})
        self.waitlist.classify_door = Mock(return_value={"verdict": "WAITLIST_DOOR_OK", "sends": 0})
        self.waitlist.load_law = Mock(side_effect=lambda path: json.loads(path.read_text(encoding="utf-8")))
        self.unique = types.ModuleType("business_pack_unique")
        self.unique.classify_copy = Mock(side_effect=lambda text: {"verdict": "COPY_BAD" if "copy-bad" in text else "COPY_OK"})
        module_patch = patch.dict(sys.modules, {"pack_waitlist": self.waitlist, "business_pack_unique": self.unique})
        module_patch.start()
        self.addCleanup(module_patch.stop)
        before_path = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), before_path))
        spec = importlib.util.spec_from_file_location("harborline_selected_root_test", SOURCE)
        self.subject = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.subject)
        for name, value in {"ROOT": self.local, "HARBORLINE": self.local / SHEET, "MANIFEST": self.local / MANIFEST}.items():
            setattr(self.subject, name, value)
        for root, marker in ((self.local, "local"), (self.selected, "selected")):
            for path in PATHS:
                write(root, path, marker + ":" + path + "\n")
            write(root, "ground/BUSINESS_PACK_WAITLIST.json", json.dumps({"id": self.subject.LAW_ID, "marker": marker}))
            write(root, SHEET, "\n".join(("Harborline Local Sites", self.subject.LAW_ID, self.subject.SCOUT_ID, self.subject.POINTER_ID,
                  "packs/waitlist.html", self.subject.CCPA_PHRASE, "NOT_MINTED", "Zero sends", "not a second list", "Did not invent manifest.json", marker)))

    def result(self, root=None):
        return self.subject.classify_tree(self.selected if root is None else root)

    def test_all_eleven_fingerprints_use_selected_tree(self):
        result = self.result()
        self.assertEqual(result["blobs"], {path: blob(self.selected / path) for path in PATHS})
        self.assertEqual(result["harborline"]["path"], str(self.selected / SHEET))

    def test_hash_helper_preserves_n_and_supports_explicit_root(self):
        self.assertEqual(self.subject.git_blob_prefix(SHEET), blob(self.local / SHEET))
        self.assertEqual(self.subject.git_blob_prefix(SHEET, 12), blob(self.local / SHEET, 12))
        self.assertEqual(self.subject.git_blob_prefix(SHEET, 12, root=self.selected), blob(self.selected / SHEET, 12))
        self.assertEqual(self.subject.git_blob_prefix("missing", root=self.selected), "")

    def test_selected_shared_door_and_law_are_passed_to_classifiers(self):
        result = self.result()
        self.waitlist.classify.assert_not_called()
        self.waitlist.classify_door.assert_called_once_with((self.selected / "packs/waitlist.html").read_text())
        self.waitlist.load_law.assert_called_once_with(self.selected / "ground/BUSINESS_PACK_WAITLIST.json")
        self.assertEqual(result["waitlist_door"], "WAITLIST_DOOR_OK")
        self.assertEqual(result["law_id"], self.subject.LAW_ID)

    def test_selected_copy_not_module_copy(self):
        write(self.selected, SHEET, (self.selected / SHEET).read_text() + "\ncopy-bad")
        result = self.result()
        self.unique.classify_copy.assert_called_once_with((self.selected / SHEET).read_text())
        self.assertFalse(result["copy_ok"])

    def test_module_copy_does_not_contaminate_selected_result(self):
        write(self.local, SHEET, "copy-bad")
        self.assertTrue(self.result()["copy_ok"])

    def test_selected_manifest_is_reported(self):
        write(self.selected, MANIFEST, "{}")
        self.assertFalse(self.result()["did_not_invent_harborline_manifest"])

    def test_module_manifest_does_not_contaminate_selected_result(self):
        write(self.local, MANIFEST, "{}")
        self.assertTrue(self.result()["did_not_invent_harborline_manifest"])

    def test_missing_selected_files_do_not_fall_back_to_module(self):
        (self.selected / "packs/waitlist.html").unlink()
        (self.selected / "ground/BUSINESS_PACK_WAITLIST.json").unlink()
        result = self.result()
        self.assertEqual(result["waitlist_door"], "WAITLIST_DOOR_MISSING")
        self.assertEqual(result["law_id"], "")
        self.assertEqual(result["blobs"]["packs/waitlist.html"], "")
        self.waitlist.classify.assert_not_called()
        self.waitlist.classify_door.assert_not_called()
        self.waitlist.load_law.assert_not_called()

    def test_missing_selected_sheet_does_not_check_module_copy(self):
        (self.selected / SHEET).unlink()
        result = self.result()
        self.assertEqual(result["harborline"]["verdict"], "HARBORLINE_WAITLIST_SLOT_MISSING")
        self.assertEqual(result["blobs"][SHEET], "")
        self.unique.classify_copy.assert_not_called()

    def test_default_root_still_uses_module_tree(self):
        result = self.subject.classify_tree()
        self.assertEqual(result["blobs"], {path: blob(self.local / path) for path in PATHS})
        self.waitlist.classify_door.assert_called_once_with((self.local / "packs/waitlist.html").read_text())

    def test_tree_reads_are_repeatable_and_do_not_mutate_files(self):
        before = {str(p): p.read_bytes() for p in Path(self.temp.name).rglob("*") if p.is_file()}
        first = self.result()
        second = self.result()
        self.assertEqual(first, second)
        self.assertEqual(before, {str(p): p.read_bytes() for p in Path(self.temp.name).rglob("*") if p.is_file()})

    def test_parallel_selections_do_not_rebind_shared_defaults(self):
        roots = [self.local, self.selected] * 8
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(self.subject.classify_tree, roots))
        for root, row in zip(roots, rows):
            self.assertEqual(row["blobs"][SHEET], blob(root / SHEET))
        self.assertEqual(self.subject.ROOT, self.local)

    def test_selected_manifest_changes_verdict_with_matching_fixture_pins(self):
        pins = {name: blob(self.selected / path) for path, name in PATHS.items()}
        with patch.multiple(self.subject, **pins):
            self.assertEqual(self.result()["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")
            write(self.local, MANIFEST, "{}")
            self.assertEqual(self.result()["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")
            write(self.selected, MANIFEST, "{}")
            self.assertEqual(self.result()["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")

    def test_cli_root_and_existing_file_mode(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.subject.main(["--root", str(self.selected)]), 0)
        self.assertEqual(json.loads(output.getvalue())["blobs"][SHEET], blob(self.selected / SHEET))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.subject.main(["--file", str(self.selected / SHEET)]), 0)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "HARBORLINE_WAITLIST_SLOT_INSTANCE_OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
