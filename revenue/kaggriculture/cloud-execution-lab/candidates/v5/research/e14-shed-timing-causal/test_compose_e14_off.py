# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import compose_e14_off as c


ROOT = Path(__file__).resolve()
for parent in ROOT.parents:
    if (parent / ".git").exists():
        REPO_ROOT = parent
        break
else:  # pragma: no cover - checkout contract
    raise RuntimeError("test requires a full commons git checkout")


def make_tar(entries, *, special=None) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
        if special is not None:
            archive.addfile(special)
    return buffer.getvalue()


class HistoricalIdentityTests(unittest.TestCase):
    def test_e14_commit_parent_is_pinned_predecessor(self):
        lineage = c.validate_git_ancestry(REPO_ROOT)
        self.assertEqual(lineage["e14_commit"], c.E14_COMMIT)
        self.assertEqual(lineage["immediate_parent"], c.PRE_E14_COMMIT)
        self.assertEqual(lineage["parent_count"], 1)
        self.assertEqual(lineage["submitted_v4_source"], c.V4_SOURCE)
        self.assertTrue(lineage["e14_ancestor_of_submitted_v4"])

    def test_wrong_immediate_parent_fails_inside_builder_authority(self):
        with patch.object(c, "PRE_E14_COMMIT", c.V31_SOURCE):
            with self.assertRaisesRegex(ValueError, "sole parent"):
                c.validate_git_ancestry(REPO_ROOT)

    def test_e14_must_be_on_submitted_v4_lineage(self):
        with patch.object(c, "V4_SOURCE", c.PRE_E14_COMMIT):
            with self.assertRaisesRegex(ValueError, "not an ancestor of submitted V4"):
                c.validate_git_ancestry(REPO_ROOT)

    def test_exact_scheduler_blob_lineage(self):
        self.assertEqual(
            c.git_path_blob(REPO_ROOT, c.V4_SOURCE, c.SCHEDULER_REPO_PATH),
            c.CONTROL_SCHEDULER_BLOB,
        )
        self.assertEqual(
            c.git_path_blob(REPO_ROOT, c.E14_COMMIT, c.SCHEDULER_REPO_PATH),
            c.CONTROL_SCHEDULER_BLOB,
        )
        self.assertEqual(
            c.git_path_blob(REPO_ROOT, c.PRE_E14_COMMIT, c.SCHEDULER_REPO_PATH),
            c.TREATMENT_SCHEDULER_BLOB,
        )

    def test_v31_and_v4_active_arlene_producer_is_identical(self):
        v31 = c.git_path_blob(REPO_ROOT, c.V31_SOURCE, c.ARLENE_REPO_PATH)
        v4 = c.git_path_blob(REPO_ROOT, c.V4_SOURCE, c.ARLENE_REPO_PATH)
        self.assertEqual(v31, c.ACTIVE_ARLENE_BLOB)
        self.assertEqual(v4, c.ACTIVE_ARLENE_BLOB)
        self.assertEqual(v31, v4)

    def test_source_delta_is_the_e14_overflow_projection(self):
        control = c.git_read_blob(REPO_ROOT, c.CONTROL_SCHEDULER_BLOB).decode("utf-8")
        predecessor = c.git_read_blob(REPO_ROOT, c.TREATMENT_SCHEDULER_BLOB).decode("utf-8")
        self.assertIn("f,p=post_units(obs,base,config,shed_capacity=10**6)", control)
        self.assertIn("if total>cap:return False", control)
        self.assertNotIn("f,p=post_units(obs,base,config,shed_capacity=10**6)", predecessor)
        self.assertIn("f,p=copy.deepcopy(farm),copy.deepcopy(private)", predecessor)
        self.assertIn("if o[0]=='SELL' and t>now and o[1]!=item", predecessor)


class ArchiveCustodyTests(unittest.TestCase):
    def test_git_blob_helper_matches_git_object(self):
        data = b"scheduler causal fixture\n"
        # Independent literal construction of Git's loose-object identity.
        import hashlib
        literal = hashlib.sha1(b"blob 25\0" + data).hexdigest()
        self.assertEqual(c.git_blob_sha1(data), literal)

    def test_archive_is_authenticated_before_parse(self):
        raw = make_tar([("scheduler.py", b"x")])
        with self.assertRaisesRegex(ValueError, "archive SHA256 mismatch"):
            c.read_authenticated_archive(raw, expected_sha256="0" * 64)

    def test_rejects_path_traversal(self):
        raw = make_tar([("../escape", b"x")])
        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
            c.read_authenticated_archive(raw, expected_sha256=c.sha256_bytes(raw))

    def test_rejects_symlink_member(self):
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "target"
        raw = make_tar([("safe", b"x")], special=link)
        with self.assertRaisesRegex(ValueError, "regular file"):
            c.read_authenticated_archive(raw, expected_sha256=c.sha256_bytes(raw))

    def test_duplicate_members_fail_closed(self):
        raw = make_tar([("same", b"a"), ("same", b"b")])
        with self.assertRaisesRegex(ValueError, "duplicate archive member"):
            c.read_authenticated_archive(raw, expected_sha256=c.sha256_bytes(raw))

    def test_treatment_changes_exactly_one_member_and_holds_producer(self):
        old_scheduler = b"old scheduler\n"
        donor_scheduler = b"pre-E14 scheduler\n"
        arlene = b"same producer\n"
        files = {
            "pkg/scheduler.py": c.ArchiveFile(old_scheduler, 0o644),
            "pkg/reference/arlene.py": c.ArchiveFile(arlene, 0o644),
            "pkg/other.py": c.ArchiveFile(b"constant\n", 0o644),
        }
        treatment, scheduler, producer = c.build_treatment_files(
            files,
            donor_scheduler,
            control_scheduler_blob=c.git_blob_sha1(old_scheduler),
            treatment_scheduler_blob=c.git_blob_sha1(donor_scheduler),
            arlene_blob=c.git_blob_sha1(arlene),
        )
        self.assertEqual(scheduler, "pkg/scheduler.py")
        self.assertEqual(producer, "pkg/reference/arlene.py")
        self.assertEqual(treatment[scheduler].data, donor_scheduler)
        self.assertEqual(treatment[producer], files[producer])
        self.assertEqual(treatment["pkg/other.py"], files["pkg/other.py"])
        self.assertNotEqual(c.tree_sha256(files), c.tree_sha256(treatment))

    def test_wrong_donor_blob_fails_before_treatment(self):
        old_scheduler = b"old\n"
        arlene = b"producer\n"
        files = {
            "scheduler.py": c.ArchiveFile(old_scheduler, 0o644),
            "arlene.py": c.ArchiveFile(arlene, 0o644),
        }
        with self.assertRaisesRegex(ValueError, "donor blob"):
            c.build_treatment_files(
                files,
                b"wrong\n",
                control_scheduler_blob=c.git_blob_sha1(old_scheduler),
                treatment_scheduler_blob="0" * 40,
                arlene_blob=c.git_blob_sha1(arlene),
            )

    def test_writer_rejects_receipt_path_collision_before_output(self):
        files = {c.RECEIPT_NAME: c.ArchiveFile(b"baseline member\n", 0o644)}
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "treatment"
            with self.assertRaisesRegex(ValueError, "collides with receipt path"):
                c._write_tree(output, files, {"schema": "fixture"})
            self.assertFalse(output.exists())

    def test_writer_is_fresh_only_and_receipt_is_additive(self):
        files = {"pkg/file.py": c.ArchiveFile(b"x\n", 0o644)}
        receipt = {"schema": "fixture"}
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "treatment"
            c._write_tree(output, files, receipt)
            self.assertEqual((output / "pkg/file.py").read_bytes(), b"x\n")
            self.assertEqual((output / c.RECEIPT_NAME).read_text(), '{\n  "schema": "fixture"\n}\n')
            with self.assertRaises(FileExistsError):
                c._write_tree(output, files, receipt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
