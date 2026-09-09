# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import materialize


def synthetic_scheduler(copies: int = 1) -> str:
    body = """def synthetic(base,route,now,config,receipt_feasible,item,targets,remaining,available,market,out):
    if True:
        if True:
"""
    body += materialize.OLD_FEASIBILITY * copies
    body += materialize.OLD_OUTPUT
    body += "\n\nclass SellScheduler:\n    pass\n"
    return body


class MaterializeTests(unittest.TestCase):
    def source_tree(self, root: Path, *, copies: int = 1) -> Path:
        source = root / "v2"
        (source / "reference").mkdir(parents=True)
        (source / "scheduler.py").write_text(
            synthetic_scheduler(copies), encoding="utf-8"
        )
        (source / "candidate.py").write_text(
            "from scheduler import SellScheduler\n", encoding="utf-8"
        )
        (source / "reference" / "receipt.txt").write_text(
            "unchanged\n", encoding="utf-8"
        )
        return source

    def test_generated_helper_selects_only_internal_vacancies(self):
        namespace = {}
        exec(materialize.HELPER, namespace)
        find = namespace["_internal_market_vacancies"]
        self.assertEqual(find([["A"], [], ["B"], [], ["C"]], 5), (1, 3))
        self.assertEqual(find([["A"], ["B"], [], []], 4), ())
        self.assertEqual(find([[], ["B"], [], []], 4), (0,))
        self.assertEqual(find([["A"], [], ["B"], []], 3), (1,))
        self.assertEqual(find([["A"], [], ["B"]], 0), ())

    def test_one_factor_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            original = (source / "scheduler.py").read_bytes()
            output = root / "candidate"
            receipt = materialize.materialize(
                source,
                output,
                expected_scheduler_blob=materialize.git_blob_sha1(original),
                expected_scheduler_sha256=materialize.sha256(original),
            )
            self.assertEqual(
                receipt["candidate"]["changed_files"], ["scheduler.py"]
            )
            self.assertNotEqual(
                receipt["source"]["closure_sha256"],
                receipt["candidate"]["closure_sha256"],
            )
            self.assertEqual(
                (source / "candidate.py").read_bytes(),
                (output / "candidate.py").read_bytes(),
            )
            self.assertEqual(
                (source / "reference" / "receipt.txt").read_bytes(),
                (output / "reference" / "receipt.txt").read_bytes(),
            )
            patched = (output / "scheduler.py").read_text(encoding="utf-8")
            self.assertEqual(patched.count(materialize.HELPER), 1)
            self.assertEqual(patched.count(materialize.NEW_FEASIBILITY), 1)
            self.assertEqual(patched.count(materialize.NEW_OUTPUT), 1)
            self.assertNotIn(materialize.OLD_FEASIBILITY, patched)
            self.assertNotIn(materialize.OLD_OUTPUT, patched)
            compile(patched, "scheduler.py", "exec")
            self.assertEqual((source / "scheduler.py").read_bytes(), original)

    def test_duplicate_source_seam_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root, copies=2)
            data = (source / "scheduler.py").read_bytes()
            with self.assertRaisesRegex(materialize.MaterializeError, "exactly one"):
                materialize.materialize(
                    source,
                    root / "candidate",
                    expected_scheduler_blob=materialize.git_blob_sha1(data),
                    expected_scheduler_sha256=materialize.sha256(data),
                )

    def test_wrong_source_identity_fails_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            with self.assertRaisesRegex(materialize.MaterializeError, "blob mismatch"):
                materialize.materialize(
                    source,
                    root / "candidate",
                    expected_scheduler_blob="0" * 40,
                    expected_scheduler_sha256="0" * 64,
                )
            self.assertFalse((root / "candidate").exists())

    def test_output_cannot_be_nested_in_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            data = (source / "scheduler.py").read_bytes()
            with self.assertRaisesRegex(materialize.MaterializeError, "nested"):
                materialize.materialize(
                    source,
                    source / "candidate",
                    expected_scheduler_blob=materialize.git_blob_sha1(data),
                    expected_scheduler_sha256=materialize.sha256(data),
                )

    def test_non_regular_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            try:
                (source / "alias").symlink_to(source / "candidate.py")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            data = (source / "scheduler.py").read_bytes()
            with self.assertRaisesRegex(materialize.MaterializeError, "non-regular"):
                materialize.materialize(
                    source,
                    root / "candidate",
                    expected_scheduler_blob=materialize.git_blob_sha1(data),
                    expected_scheduler_sha256=materialize.sha256(data),
                )


if __name__ == "__main__":
    unittest.main()
