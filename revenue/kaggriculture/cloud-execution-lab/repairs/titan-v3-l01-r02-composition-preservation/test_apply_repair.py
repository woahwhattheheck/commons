#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

import apply_repair as repair


class CompositionCarrierTests(unittest.TestCase):
    def fixture(self) -> str:
        return "prefix\n" + repair.INIT_OLD + "\n" + repair.R02_METHOD_OLD + "suffix\n"

    def test_transform_changes_only_the_two_owned_anchors(self):
        source = self.fixture()
        repaired = repair.transform(source)
        self.assertEqual(repaired.count(repair.INIT_NEW), 1)
        self.assertEqual(repaired.count(repair.R02_METHOD_NEW), 1)
        self.assertNotIn(repair.INIT_OLD, repaired)
        self.assertNotIn(repair.R02_METHOD_OLD, repaired)
        self.assertTrue(repaired.startswith("prefix\n"))
        self.assertTrue(repaired.endswith("suffix\n"))

    def test_repaired_generated_r02_method_is_valid_python(self):
        tree = ast.parse("VALUE = (\n" + repair.R02_METHOD_NEW + ")\n")
        method = ast.literal_eval(tree.body[0].value)
        self.assertIn("after > before", method)
        self.assertIn("self._v3_l01_install()", method)
        self.assertIn("'l01_reapplied': l01_reapplied", method)
        ast.parse("class Probe:\n" + method)

    def test_second_application_fails_closed(self):
        repaired = repair.transform(self.fixture())
        with self.assertRaisesRegex(ValueError, "initialize order"):
            repair.transform(repaired)

    def test_duplicate_anchor_fails_closed(self):
        source = self.fixture() + repair.INIT_OLD
        with self.assertRaisesRegex(ValueError, "initialize order"):
            repair.transform(source)

    def test_apply_file_rejects_unbound_preimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apply_v3.py"
            path.write_text(self.fixture(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preimage drift"):
                repair.apply_file(path)


if __name__ == "__main__":
    unittest.main()
