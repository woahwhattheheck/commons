"""Full-module root selection against real independent checkout directories."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "host" / "pack_waitlist_pointer.py"
POINTER = "ground/BUSINESS_PACK_WAITLIST_POINTER.json"


class PackWaitlistPointerRootsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.module_root = Path(self.temp.name) / "module checkout"
        self.selected_root = Path(self.temp.name) / "selected checkout \u03a9"
        self.populate(self.module_root, "module")
        self.populate(self.selected_root, "selected")
        self.module_path = self.module_root / "host" / "pack_waitlist_pointer.py"
        self.module_path.write_bytes(SOURCE.read_bytes())
        spec = importlib.util.spec_from_file_location("isolated_waitlist_pointer", self.module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        self.pointer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pointer)

    @staticmethod
    def populate(root, label):
        files = {
            POINTER: {"id": label + "-pointer", "scout_demand_id": label + "-demand",
                      "owner_seat": label + "-owner", "pointer_only": True,
                      "did_not_remint_scout_demand": True, "checkout": "NOT_MINTED"},
            "ground/BUSINESS_PACKS.json": {"id": label + "-law", "waitlist": {
                "id": label + "-unique-pointer", "claimed_by": label + "-fallback-owner"}},
            "packs/desk-website-service-20260902-01/instance.json": {
                "brand": "Harborline Local Sites", "door": label + "-door.html"},
            "packs/sidewalk-signal-web-desk-20260902-01/manifest.json": {"brand": "Sidewalk Signal"},
            "packs/thanks.html": "thanks from " + label,
            "host/business_pack_desk_instance.py": "# fixture\n",
            "host/business_pack_waitlist_pointer.py": "# fixture\n",
        }
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(content) if isinstance(content, dict) else content, encoding="utf-8")

    def test_selected_root_supplies_pointer_and_pack_facts(self):
        result = self.pointer.classify(root=self.selected_root)
        self.assertEqual(result["id"], "selected-pointer")
        self.assertEqual(result["scout_demand_id"], "selected-demand")
        self.assertEqual(result["owner_seat"], "selected-owner")
        self.assertEqual(result["unique_pack_law_id"], "selected-law")
        self.assertEqual(result["unique_pack_waitlist_pointer_id"], "selected-unique-pointer")
        self.assertEqual(result["harborline"]["harborline_door"], "selected-door.html")
        self.assertEqual(result["thanks_door"]["blob"], self.pointer.git_blob_sha(self.selected_root / "packs/thanks.html"))

    def test_missing_selected_pointer_is_not_replaced_by_module_pointer(self):
        path = self.selected_root / POINTER
        path.unlink()
        with self.assertRaises(FileNotFoundError) as caught:
            self.pointer.classify(root=self.selected_root)
        self.assertIn(str(path), str(caught.exception))

    def test_malformed_selected_pointer_is_not_replaced_by_module_pointer(self):
        (self.selected_root / POINTER).write_text("{invalid", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.pointer.classify(root=self.selected_root)

    def test_nonobject_selected_pointer_is_rejected(self):
        (self.selected_root / POINTER).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "is not an object"):
            self.pointer.classify(root=self.selected_root)

    def test_selected_root_does_not_need_module_pointer(self):
        (self.module_root / POINTER).unlink()
        self.assertEqual(self.pointer.classify(root=self.selected_root)["id"], "selected-pointer")

    def test_selected_root_ignores_malformed_module_pointer(self):
        (self.module_root / POINTER).write_text("[]", encoding="utf-8")
        self.assertEqual(self.pointer.classify(root=self.selected_root)["id"], "selected-pointer")

    def test_explicit_pointer_overrides_both_files_without_reading_them(self):
        (self.module_root / POINTER).unlink()
        (self.selected_root / POINTER).unlink()
        result = self.pointer.classify(root=self.selected_root, pointer={"id": "explicit", "owner_seat": "supplied"})
        self.assertEqual(result["id"], "explicit")
        self.assertEqual(result["owner_seat"], "supplied")
        self.assertEqual(result["unique_pack_law_id"], "selected-law")

    def test_empty_explicit_pointer_preserves_fallback_behavior(self):
        (self.module_root / POINTER).unlink()
        (self.selected_root / POINTER).unlink()
        result = self.pointer.classify(root=self.selected_root, pointer={})
        self.assertEqual(result["id"], "")
        self.assertEqual(result["owner_seat"], "selected-fallback-owner")
        self.assertEqual(result["checkout"], "NOT_MINTED")

    def test_default_root_and_explicit_default_root_agree(self):
        self.assertEqual(self.pointer.classify(), self.pointer.classify(root=self.module_root))
        self.assertEqual(self.pointer.classify()["id"], "module-pointer")

    def test_default_pointer_law_override_remains_supported(self):
        self.pointer.POINTER_LAW = self.selected_root / POINTER
        result = self.pointer.classify()
        self.assertEqual(result["id"], "selected-pointer")
        self.assertEqual(result["unique_pack_law_id"], "module-law")

    def test_existing_cli_defaults_and_pointer_override(self):
        def run(*args):
            result = subprocess.run([sys.executable, str(self.module_path), *args],
                                    text=True, capture_output=True, check=True)
            return json.loads(result.stdout)
        self.assertEqual(run()["id"], "module-pointer")
        explicit = run("--pointer", str(self.selected_root / POINTER))
        self.assertEqual(explicit["id"], "selected-pointer")
        self.assertEqual(explicit["unique_pack_law_id"], "module-law")

    def test_classification_is_read_only_and_keeps_existing_flags(self):
        def snapshot():
            return {str(path): path.read_bytes() for path in Path(self.temp.name).rglob("*") if path.is_file()}
        before = snapshot()
        result = self.pointer.classify(root=self.selected_root)
        self.assertEqual(snapshot(), before)
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)
        self.assertIs(result["did_not_write_owner_paths"], True)
        self.assertIs(result["harborline"]["similar_is_not_clone"], True)
        self.assertEqual(self.pointer.THANKS_BLOB_PREFIX, "7ec0bf86")


if __name__ == "__main__":
    unittest.main(verbosity=2)
