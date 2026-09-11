from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import preview


class H4ProductionWiringPreviewTests(unittest.TestCase):
    def test_reviewed_source_blobs_are_exact(self):
        self.assertEqual(
            preview.git_blob_sha(preview.DONOR.read_bytes()),
            preview.EXPECTED_DONOR_BLOB,
        )
        self.assertEqual(
            preview.git_blob_sha(preview.OVERLAY_R04.read_bytes()),
            preview.EXPECTED_R04_BLOB,
        )

    def test_patch_is_default_off_and_uses_reviewed_wrapper(self):
        source = preview.APPLY.read_text(encoding="utf-8")
        patched = preview.patch_apply_v3(source)
        self.assertIn('"r04_strawberry_topup": False', patched)
        self.assertIn('r04_strawberry_topup: bool = False', patched)
        self.assertIn('from r04_h4_strawberry import install', patched)
        self.assertIn('bool(self.features.r04_strawberry_topup))(observation, configuration)', patched)
        self.assertIn("self.diagnostics['strawberry_topup'] = bool(self.features.r04_strawberry_topup)", patched)
        self.assertNotEqual(source, patched)

    def test_patch_rejects_missing_or_duplicated_anchor(self):
        source = preview.APPLY.read_text(encoding="utf-8")
        missing = source.replace('    "r04_cattle_early": True,\n', '', 1)
        with self.assertRaisesRegex(ValueError, "PARAMS r04 default"):
            preview.patch_apply_v3(missing)

        duplicated = source.replace(
            '    "r04_cattle_early": True,\n',
            '    "r04_cattle_early": True,\n    "r04_cattle_early": True,\n',
            1,
        )
        with self.assertRaisesRegex(ValueError, "PARAMS r04 default"):
            preview.patch_apply_v3(duplicated)

    def test_materialize_is_out_of_tree_and_donor_is_byte_identical(self):
        apply_before = preview.APPLY.read_bytes()
        donor_before = preview.DONOR.read_bytes()
        r04_before = preview.OVERLAY_R04.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "preview"
            receipts = preview.materialize(out)
            emitted_h4 = out / "candidates" / "v3" / "overlay" / "r04_h4_strawberry.py"
            emitted_apply = out / "candidates" / "v3" / "apply_v3.py"
            self.assertEqual(emitted_h4.read_bytes(), donor_before)
            self.assertIn(b'r04_strawberry_topup', emitted_apply.read_bytes())
            self.assertEqual(receipts["source_h4_donor_blob"], preview.EXPECTED_DONOR_BLOB)
            self.assertEqual(receipts["source_r04_blob"], preview.EXPECTED_R04_BLOB)
            self.assertEqual(receipts["preview_h4_overlay_blob"], preview.EXPECTED_DONOR_BLOB)

        self.assertEqual(preview.APPLY.read_bytes(), apply_before)
        self.assertEqual(preview.DONOR.read_bytes(), donor_before)
        self.assertEqual(preview.OVERLAY_R04.read_bytes(), r04_before)

    def test_refuses_repository_output(self):
        with self.assertRaisesRegex(ValueError, "inside repository"):
            preview.materialize(preview.V3 / "_must_not_write")


if __name__ == "__main__":
    unittest.main()
