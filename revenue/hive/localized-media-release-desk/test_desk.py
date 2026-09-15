import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from desk import (
    HoldError,
    IdempotencyConflict,
    InvalidState,
    ReleaseDesk,
    sha256_bytes,
    strict_json_loads,
)


class DeskTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "desk.sqlite3"
        self.source = self.root / "source.txt"
        self.source.write_bytes(b"MASTER-v1\n")
        self.es = self.root / "es.srt"
        self.es.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nHola\n")
        self.fr = self.root / "fr.srt"
        self.fr.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nBonjour\n")
        self.required = [
            {"locale": "es", "territory": "US", "kind": "subtitle"},
            {"locale": "fr", "territory": "CA", "kind": "subtitle"},
        ]
        self.desk = ReleaseDesk(self.db)
        self.desk.create_title("r-create", "title-1", str(self.source), self.required)

    def tearDown(self):
        self.tmp.cleanup()

    def _add_and_approve(self, locale, territory, path, prefix):
        added = self.desk.add_variant(
            f"{prefix}-add", "title-1", locale, territory, "subtitle", str(path)
        )
        self.desk.approve_variant(
            f"{prefix}-approve",
            "title-1",
            locale,
            territory,
            "subtitle",
            f"reviewer-{locale}",
            added["revision"],
            added["content_sha256"],
        )
        return added

    def _ready(self):
        self.desk.set_rights_ready("r-rights", "title-1", True)
        es = self._add_and_approve("es", "US", self.es, "es")
        fr = self._add_and_approve("fr", "CA", self.fr, "fr")
        return es, fr

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaises(InvalidState):
            strict_json_loads('{"a":1,"a":2}')

    def test_required_spec_duplicate_is_invalid(self):
        with self.assertRaises(InvalidState):
            ReleaseDesk(self.root / "other.sqlite3").create_title(
                "dup", "bad", str(self.source), [self.required[0], self.required[0]]
            )

    def test_initial_state_holds_fail_closed(self):
        status = self.desk.status("title-1")
        self.assertEqual(status["release_status"], "HOLD")
        self.assertIn("OWNER_RIGHTS_NOT_READY", status["holds"])
        self.assertIn("MISSING_VARIANT:es/US/subtitle", status["holds"])
        with self.assertRaises(HoldError):
            self.desk.build_package("title-1")

    def test_ready_requires_exact_current_approvals(self):
        self._ready()
        status = self.desk.status("title-1")
        self.assertEqual(status["release_status"], "READY_FOR_LOCAL_HANDOFF")
        self.assertEqual(status["holds"], [])
        self.assertFalse(status["external_publish_authorized"])

    def test_variant_revision_invalidates_prior_approval(self):
        self._ready()
        self.es.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nHola revisado\n")
        updated = self.desk.add_variant("es-revise", "title-1", "es", "US", "subtitle", str(self.es))
        self.assertEqual(updated["revision"], 2)
        status = self.desk.status("title-1")
        self.assertIn("MISSING_CURRENT_APPROVAL:es/US/subtitle", status["holds"])
        with self.assertRaises(InvalidState):
            self.desk.approve_variant(
                "stale-approval",
                "title-1",
                "es",
                "US",
                "subtitle",
                "reviewer-stale",
                1,
                "0" * 64,
            )

    def test_source_mutation_invalidates_all_variant_parent_bindings(self):
        self._ready()
        self.source.write_bytes(b"MASTER-v2\n")
        self.desk.update_source("source-v2", "title-1", str(self.source))
        status = self.desk.status("title-1")
        self.assertIn("STALE_SOURCE_BINDING:es/US/subtitle", status["holds"])
        self.assertIn("STALE_SOURCE_BINDING:fr/CA/subtitle", status["holds"])
        with self.assertRaises(InvalidState):
            self.desk.approve_variant(
                "approve-stale-parent",
                "title-1",
                "es",
                "US",
                "subtitle",
                "reviewer-new",
                status["variants"][0]["revision"],
                status["variants"][0]["content_sha256"],
            )

    def test_idempotent_replay_and_conflicting_remint(self):
        first = self.desk.set_rights_ready("same-request", "title-1", True)
        second = self.desk.set_rights_ready("same-request", "title-1", True)
        self.assertEqual(first, second)
        with self.assertRaises(IdempotencyConflict):
            self.desk.set_rights_ready("same-request", "title-1", False)

    def test_cross_title_approval_cannot_be_reused(self):
        es = self.desk.add_variant("es-add", "title-1", "es", "US", "subtitle", str(self.es))
        source2 = self.root / "source2.txt"
        source2.write_bytes(b"OTHER\n")
        self.desk.create_title("create-2", "title-2", str(source2), [self.required[0]])
        with self.assertRaises(InvalidState):
            self.desk.approve_variant(
                "cross",
                "title-2",
                "es",
                "US",
                "subtitle",
                "reviewer",
                es["revision"],
                es["content_sha256"],
            )

    def test_non_required_variant_is_rejected(self):
        with self.assertRaises(InvalidState):
            self.desk.add_variant("wrong", "title-1", "de", "DE", "subtitle", str(self.es))

    def test_deterministic_package_survives_reopen(self):
        self._ready()
        a, receipt_a = self.desk.build_package("title-1")
        reopened = ReleaseDesk(self.db)
        b, receipt_b = reopened.build_package("title-1")
        self.assertEqual(a, b)
        self.assertEqual(receipt_a, receipt_b)
        self.assertEqual(receipt_a["package_sha256"], sha256_bytes(a))

    def test_export_is_create_exclusive_and_verify_recomputes(self):
        self._ready()
        out = self.root / "release.zip"
        receipt = self.desk.export_package("title-1", out)
        self.assertTrue(out.is_file())
        self.assertEqual(receipt["package_sha256"], sha256_bytes(out.read_bytes()))
        verify = self.desk.verify_package("title-1", out)
        self.assertTrue(verify["valid"])
        with self.assertRaises(FileExistsError):
            self.desk.export_package("title-1", out)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_export_refuses_symlink_leaf_without_touching_target(self):
        self._ready()
        target = self.root / "foreign.txt"
        target.write_text("sentinel", encoding="utf-8")
        link = self.root / "release.zip"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(FileExistsError):
            self.desk.export_package("title-1", link)
        self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

    @unittest.skipUnless(
        hasattr(os, "symlink") and bool(getattr(os, "O_NOFOLLOW", 0)) and os.open in getattr(os, "supports_dir_fd", ()),
        "component-wise no-follow traversal unsupported",
    )
    def test_export_refuses_intermediate_symlink_component(self):
        self._ready()
        real = self.root / "real"
        nested = real / "nested"
        nested.mkdir(parents=True)
        alias = self.root / "alias"
        try:
            os.symlink(real, alias, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlink unavailable")
        with self.assertRaises(OSError):
            self.desk.export_package("title-1", alias / "nested" / "release.zip")
        self.assertEqual(list(nested.iterdir()), [])

    def test_export_failure_never_path_unlinks_owned_or_foreign_successor(self):
        if not getattr(os, "O_NOFOLLOW", 0) or os.open not in getattr(os, "supports_dir_fd", ()):
            self.skipTest("safe export traversal unsupported")
        self._ready()
        out = self.root / "release.zip"
        with mock.patch("os.unlink") as unlink, mock.patch("os.fsync", side_effect=OSError("forced durability failure")):
            with self.assertRaises(OSError):
                self.desk.export_package("title-1", out)
        unlink.assert_not_called()
        self.assertTrue(out.is_file())
        self.assertEqual(out.stat().st_size, 0)

    def test_package_tamper_is_detected(self):
        self._ready()
        out = self.root / "release.zip"
        self.desk.export_package("title-1", out)
        data = bytearray(out.read_bytes())
        data[-1] ^= 1
        out.write_bytes(data)
        self.assertFalse(self.desk.verify_package("title-1", out)["valid"])

    def test_db_constraints_reject_forged_boolean(self):
        with sqlite3.connect(self.db) as c:
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE titles SET rights_ready=7 WHERE title_id='title-1'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
