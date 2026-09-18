#!/usr/bin/env python3
"""Real paired-root regressions for the LotRibbon waitlist readback helper."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import pack_lotribbon_waitlist_slot as slot

BLOB_PATHS = (
    "packs/_template/waitlist-slot.md",
    "packs/waitlist.html",
    "packs/lotribbon-greetings-20260902-01/index.html",
)
SHEET = "packs/lotribbon-greetings-20260902-01/waitlist-slot.md"
HARBORLINE = "packs/desk-website-service-20260902-01/waitlist-slot.md"
SIDEWALK = "packs/sidewalk-signal-web-desk-20260902-01/waitlist-slot.md"
VALID_SHEET = """# Waitlist slot - LotRibbon Greetings
id: cursor-pack-door-waitlist-20260902-01
Form: packs/waitlist.html
Door blob 7804ec33 unread.
Zero sends.
Checkout stays NOT_MINTED.
"""


def write(root: Path, relative: str, data: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def blob(root: Path, relative: str, width: int = 8) -> str:
    path = root / relative
    if not path.is_file():
        return ""
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()[:width]


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class SelectedRootTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="lotribbon-slot-roots-")
        self.addCleanup(directory.cleanup)
        self.default = Path(directory.name) / "module-checkout"
        self.selected = Path(directory.name) / "selected-checkout"
        for root, label in ((self.default, "default"), (self.selected, "selected")):
            for relative in BLOB_PATHS:
                write(root, relative, label + ":" + relative + "\n")
            write(root, SHEET, VALID_SHEET)
        # Model a genuinely separate module checkout, including its cached paths.
        patcher = mock.patch.multiple(
            slot, ROOT=self.default,
            TEMPLATE=self.default / BLOB_PATHS[0],
            WAITLIST_HTML=self.default / BLOB_PATHS[1],
            DOOR=self.default / BLOB_PATHS[2],
            LOTRIBBON=self.default / SHEET,
            HARBORLINE=self.default / HARBORLINE,
            SIDEWALK=self.default / SIDEWALK,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def pins(self, root: Path):
        return mock.patch.multiple(
            slot, TEMPLATE_BLOB=blob(root, BLOB_PATHS[0]),
            WAITLIST_HTML_BLOB=blob(root, BLOB_PATHS[1]),
            DOOR_BLOB=blob(root, BLOB_PATHS[2]),
        )

    def test_all_hashes_come_from_selected_root(self) -> None:
        result = slot.classify_tree(self.selected)
        self.assertEqual(result["blobs"], {p: blob(self.selected, p) for p in BLOB_PATHS})
        self.assertEqual(result["lotribbon"]["path"], str(self.selected / SHEET))

    def test_missing_selected_files_never_borrow_default_hashes(self) -> None:
        for relative in BLOB_PATHS:
            (self.selected / relative).unlink()
        self.assertEqual(slot.classify_tree(self.selected)["blobs"], dict.fromkeys(BLOB_PATHS, ""))

    def test_one_missing_selected_file_does_not_fall_back(self) -> None:
        (self.selected / BLOB_PATHS[1]).unlink()
        result = slot.classify_tree(self.selected)
        self.assertEqual(result["blobs"][BLOB_PATHS[1]], "")
        self.assertEqual(result["blobs"][BLOB_PATHS[0]], blob(self.selected, BLOB_PATHS[0]))

    def test_selected_matching_pins_determine_verdict(self) -> None:
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_OK")
        self.assertTrue(result["did_not_rewrite_goat_template"])
        self.assertTrue(result["did_not_overwrite_waitlist_html"])
        self.assertTrue(result["did_not_overwrite_lotribbon_door"])

    def test_matching_default_cannot_promote_different_selected_tree(self) -> None:
        with self.pins(self.default):
            self.assertEqual(slot.classify_tree()["verdict"], "LOTRIBBON_WAITLIST_SLOT_OK")
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_INCOMPLETE")
        self.assertFalse(result["did_not_rewrite_goat_template"])
        self.assertFalse(result["did_not_overwrite_waitlist_html"])
        self.assertFalse(result["did_not_overwrite_lotribbon_door"])

    def test_missing_selected_sheet_does_not_use_default_sheet(self) -> None:
        (self.selected / SHEET).unlink()
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["lotribbon"]["verdict"], "LOTRIBBON_WAITLIST_SLOT_MISSING")
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_INCOMPLETE")

    def test_invalid_selected_sheet_remains_incomplete(self) -> None:
        write(self.selected, SHEET, "incomplete sheet\n")
        with self.pins(self.selected):
            result = slot.classify_tree(self.selected)
        self.assertEqual(result["verdict"], "LOTRIBBON_WAITLIST_SLOT_INCOMPLETE")
        self.assertIn("brand", result["lotribbon"]["problems"])

    def test_selected_peer_presence_is_reported(self) -> None:
        write(self.selected, HARBORLINE, "present\n")
        write(self.selected, SIDEWALK, "present\n")
        result = slot.classify_tree(self.selected)
        self.assertTrue(result["harborline_slot_present"])
        self.assertTrue(result["sidewalk_slot_present"])

    def test_default_peer_presence_does_not_leak_into_selected_tree(self) -> None:
        write(self.default, HARBORLINE, "present\n")
        write(self.default, SIDEWALK, "present\n")
        result = slot.classify_tree(self.selected)
        self.assertFalse(result["harborline_slot_present"])
        self.assertFalse(result["sidewalk_slot_present"])

    def test_mixed_peer_presence_uses_one_root(self) -> None:
        write(self.selected, HARBORLINE, "present\n")
        write(self.default, SIDEWALK, "present\n")
        result = slot.classify_tree(self.selected)
        self.assertTrue(result["harborline_slot_present"])
        self.assertFalse(result["sidewalk_slot_present"])

    def test_default_none_and_explicit_module_root_are_equivalent(self) -> None:
        write(self.default, SIDEWALK, "present\n")
        implicit = slot.classify_tree()
        self.assertEqual(implicit, slot.classify_tree(None))
        self.assertEqual(implicit, slot.classify_tree(self.default))
        self.assertEqual(implicit["blobs"], {p: blob(self.default, p) for p in BLOB_PATHS})
        self.assertFalse(implicit["gate"])
        self.assertFalse(implicit["commons_admission"])
        self.assertEqual(implicit["sends"], 0)
        self.assertEqual(implicit["checkout"], "NOT_MINTED")
        self.assertEqual(implicit["do_not_overwrite"], list(slot.DO_NOT_OVERWRITE))

    def test_helper_preserves_default_root_and_positional_width(self) -> None:
        self.assertEqual(slot.git_blob_prefix(BLOB_PATHS[0]), blob(self.default, BLOB_PATHS[0]))
        self.assertEqual(slot.git_blob_prefix(BLOB_PATHS[0], 40), blob(self.default, BLOB_PATHS[0], 40))

    def test_helper_accepts_selected_root_and_width(self) -> None:
        self.assertEqual(slot.git_blob_prefix(BLOB_PATHS[0], 40, root=self.selected),
                         blob(self.selected, BLOB_PATHS[0], 40))

    def test_helper_missing_selected_file_returns_empty(self) -> None:
        (self.selected / BLOB_PATHS[0]).unlink()
        self.assertEqual(slot.git_blob_prefix(BLOB_PATHS[0], root=self.selected), "")

    def test_readback_is_deterministic_and_does_not_write_either_tree(self) -> None:
        before = snapshot(self.default), snapshot(self.selected)
        first = slot.classify_tree(self.selected)
        self.assertEqual(first, slot.classify_tree(self.selected))
        self.assertEqual(before, (snapshot(self.default), snapshot(self.selected)))

    def test_default_cli_keeps_existing_json_contract(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(slot.main([]), 0)
        self.assertEqual(json.loads(output.getvalue()), slot.classify_tree())

    def test_file_cli_keeps_explicit_path_contract(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(slot.main(["--file", str(self.selected / SHEET)]), 0)
        self.assertEqual(json.loads(output.getvalue()), slot.classify_path(self.selected / SHEET))


if __name__ == "__main__":
    unittest.main()
