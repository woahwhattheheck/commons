#!/usr/bin/env python3
"""Keep distinct valid work IDs distinct in the derived open-work directory."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import open_work as ow


ROOT = Path(__file__).resolve().parent
PREFIX = "restore-cloud-work-" + "a" * 59
LONG_IDS = tuple(PREFIX + suffix for suffix in ("01", "02", "03", "04"))


class ListingFilenameContract(unittest.TestCase):
    def test_existing_short_names_and_class_defaults_are_unchanged(self):
        ident = "kimi-continuity-kit-20260829-01"
        for klass in ("OPEN", "open", "OpEn", "", None):
            with self.subTest(klass=klass):
                self.assertEqual(ow.listing_filename(ident, klass), ident + "-open.md")
        self.assertEqual(ow.self_test(), 0)

    def test_every_valid_length_retains_the_full_id_for_every_class(self):
        for length in range(8, 81):
            ident = "work-job" + "a" * (length - 8)
            self.assertIsNotNone(ow.ID_RE.fullmatch(ident))
            for klass in ow.CLASSES:
                with self.subTest(length=length, klass=klass):
                    name = ow.listing_filename(ident, klass)
                    self.assertEqual(name, ident + "-" + klass.lower() + ".md")
                    self.assertLessEqual(len(name), 94)

    def test_shared_prefix_ids_do_not_alias(self):
        ids = LONG_IDS + (PREFIX + "._", PREFIX + "--")
        for ident in ids:
            self.assertEqual(len(ident), 80)
            self.assertTrue(ow.is_title_filename(ident))
        for klass in ow.CLASSES:
            with self.subTest(klass=klass):
                names = [ow.listing_filename(ident, klass) for ident in ids]
                self.assertEqual(len(set(names)), len(ids))

    def test_long_id_does_not_alias_its_shorter_prefix(self):
        for klass in ow.CLASSES:
            with self.subTest(klass=klass):
                long_id = LONG_IDS[0]
                short_id = long_id[:80 - len(klass) - 1]
                self.assertNotEqual(
                    ow.listing_filename(long_id, klass),
                    ow.listing_filename(short_id, klass),
                )

    def test_nonstandard_input_formatting_is_unchanged(self):
        self.assertEqual(ow.listing_filename("work / item", "OPEN"), "work---item-open.md")
        self.assertEqual(ow.listing_filename("", None), "open.md")
        self.assertEqual(ow.listing_filename("work-job", "custom"), "work-job-custom.md")


class ListingProjectionContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="open-work-listing-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "p" / "listing-source-record-20260907-01.md"
        self.source.parent.mkdir()
        self.source_text = (
            "from: PEER\nid: listing-source-record-20260907-01\n\n---\n\n"
            + "\n".join("WORK ORDER " + ident for ident in LONG_IDS) + "\n"
        )
        self.source.write_text(self.source_text, encoding="utf-8")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Commons Test", "-c",
                 "user.email=commons-test@example.invalid", "commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE,
        )

    def snapshot(self, claimed=LONG_IDS[2:]):
        snapshot = ow.project(
            str(self.root), self.sha, extra={"slack_claimed": list(claimed)},
        )
        self.assertEqual(snapshot["errors"], [])
        self.assertEqual(len(snapshot["items"]), 4)
        return snapshot

    def assert_written_rows(self, snapshot):
        directory = self.root / ow.LISTING_REL
        expected = {
            item["id"] + "-" + item["class"].lower() + ".md": item
            for item in snapshot["items"]
        }
        self.assertEqual({path.name for path in directory.glob("*.md")}, set(expected))
        for name, item in expected.items():
            with self.subTest(name=name):
                self.assertEqual(item["title_filename"], name)
                text = (directory / name).read_text(encoding="utf-8")
                self.assertTrue(text.startswith("# " + item["id"] + "\n"))
                self.assertIn("- class: `" + item["class"] + "`", text)
                self.assertIn("- receipt: `404`", text)
                self.assertIn(self.sha, text)
        machine = json.loads((self.root / ow.MACHINE_REL).read_text(encoding="utf-8"))
        self.assertEqual(machine["items"], snapshot["items"])
        self.assertEqual(self.source.read_text(encoding="utf-8"), self.source_text)
        self.assertEqual(self.git("diff", "--", "p"), "")
        self.assertEqual(len(list(self.source.parent.glob("*.md"))), 1)

    def test_snapshot_preserves_all_open_and_dead_claim_rows(self):
        snapshot = self.snapshot()
        self.assertEqual(snapshot["counts"]["OPEN"], 2)
        self.assertEqual(snapshot["counts"]["DEAD_CLAIM"], 2)
        ow.write_snapshot(str(self.root), snapshot)
        self.assert_written_rows(snapshot)

    def test_repeated_writes_and_status_changes_clean_up_only_derived_names(self):
        directory = self.root / ow.LISTING_REL
        directory.mkdir(parents=True)
        legacy_name = LONG_IDS[0][:75] + "-open.md"
        (directory / legacy_name).write_text("old truncated projection\n", encoding="utf-8")
        snapshot = self.snapshot()
        ow.write_snapshot(str(self.root), snapshot)
        self.assertFalse((directory / legacy_name).exists())
        self.assert_written_rows(snapshot)
        before = {path.name: path.read_bytes() for path in directory.glob("*.md")}
        ow.write_snapshot(str(self.root), snapshot)
        self.assertEqual(before, {path.name: path.read_bytes() for path in directory.glob("*.md")})
        changed = self.snapshot(claimed=LONG_IDS)
        ow.write_snapshot(str(self.root), changed)
        self.assertEqual(changed["counts"]["DEAD_CLAIM"], 4)
        self.assert_written_rows(changed)
        self.assertFalse(any(directory.glob("*-open.md")))

    def test_cli_write_uses_the_same_complete_filenames(self):
        command = [sys.executable, str(ROOT / "host" / "open_work.py"),
                   "--root", str(self.root), "--main-sha", self.sha, "--write"]
        for ident in LONG_IDS[2:]:
            command.extend(["--slack-claimed", ident])
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        snapshot = json.loads(result.stdout)
        self.assertEqual(snapshot["errors"], [])
        self.assert_written_rows(snapshot)


if __name__ == "__main__":
    unittest.main()
