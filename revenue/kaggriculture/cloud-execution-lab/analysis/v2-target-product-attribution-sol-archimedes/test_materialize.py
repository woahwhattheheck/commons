# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import materialize


SCHEDULER = """class Scheduler:
    def act(self):
        shed = {}
        PRODUCTS = []
        baseline_q = {}
        self.pending = {}
        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS if shed.get(p,0)>0}
        return targets
"""


class MaterializeTests(unittest.TestCase):
    def source(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        (source / "candidate.py").write_text("def agent(*args): return {}\n", encoding="utf-8")
        (source / "scheduler.py").write_text(SCHEDULER, encoding="utf-8")
        (source / "other.txt").write_text("untouched\n", encoding="utf-8")
        return source

    def test_all_arms_are_one_file_and_source_stays_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            before = materialize.inventory(source)
            expected = materialize.git_blob_sha1((source / "scheduler.py").read_bytes())
            closures = set()
            for arm in materialize.VALID_ARMS:
                receipt = materialize.materialize(
                    source, root / arm, arm=arm, expected_scheduler_blob=expected
                )
                self.assertEqual(receipt["arm"], arm)
                self.assertEqual(receipt["candidate"]["changed_files"], ["scheduler.py"])
                self.assertEqual(receipt["source"]["closure_sha256"], materialize.closure_sha256(before))
                self.assertEqual(materialize.inventory(source), before)
                closures.add(receipt["candidate"]["closure_sha256"])
                text = (root / arm / "scheduler.py").read_text(encoding="utf-8")
                self.assertIn(materialize.CORE, text)
                self.assertNotIn(materialize.OLD, text)
                if arm != "CORE":
                    self.assertIn(f'targets["{arm}"]', text)
            self.assertEqual(len(closures), len(materialize.VALID_ARMS))

    def test_rejects_unknown_arm_and_blob_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            with self.assertRaises(materialize.MaterializeError):
                materialize.normalize_arm("WHEAT")
            with self.assertRaises(materialize.MaterializeError):
                materialize.materialize(
                    source, root / "bad", arm="CORE", expected_scheduler_blob="0" * 40
                )

    def test_rejects_output_nested_in_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            expected = materialize.git_blob_sha1((source / "scheduler.py").read_bytes())
            with self.assertRaises(materialize.MaterializeError):
                materialize.materialize(
                    source,
                    source / "nested",
                    arm="CORE",
                    expected_scheduler_blob=expected,
                )


if __name__ == "__main__":
    unittest.main()
