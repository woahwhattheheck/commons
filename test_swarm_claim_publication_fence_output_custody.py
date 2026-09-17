import os
import tempfile
import unittest

import tools.swarm_claim_publication_fence.core as fence_core
from test_swarm_claim_publication_fence import ValidationError, compile_snapshot, snapshot


class OutputCustodyTests(unittest.TestCase):
    def test_output_parent_symlink_rejected(self):
        if not hasattr(os, "symlink") or not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("symlink-safe open unavailable")
        report, md, receipt = compile_snapshot(snapshot())
        with tempfile.TemporaryDirectory() as td:
            real = os.path.join(td, "real")
            link = os.path.join(td, "link")
            os.mkdir(real)
            os.symlink(real, link)
            with self.assertRaises(OSError):
                fence_core.write_compilation(os.path.join(link, "fence"), report, md, receipt)

    def test_output_parent_remint_detected_and_cleaned(self):
        report, md, receipt = compile_snapshot(snapshot())
        with tempfile.TemporaryDirectory() as td:
            parent = os.path.join(td, "out")
            displaced = os.path.join(td, "out-old")
            os.mkdir(parent)
            prefix = os.path.join(parent, "fence")
            original = fence_core._write_new_at
            calls = {"count": 0}

            def remint_after_first(dir_fd, name, text):
                original(dir_fd, name, text)
                calls["count"] += 1
                if calls["count"] == 1:
                    os.rename(parent, displaced)
                    os.mkdir(parent)

            fence_core._write_new_at = remint_after_first
            try:
                with self.assertRaises(ValidationError):
                    fence_core.write_compilation(prefix, report, md, receipt)
            finally:
                fence_core._write_new_at = original
            self.assertEqual(os.listdir(displaced), [])
            self.assertEqual(os.listdir(parent), [])

    def test_output_parent_remint_during_readback_detected_and_cleaned(self):
        report, md, receipt = compile_snapshot(snapshot())
        with tempfile.TemporaryDirectory() as td:
            parent = os.path.join(td, "out")
            displaced = os.path.join(td, "out-old")
            os.mkdir(parent)
            prefix = os.path.join(parent, "fence")
            original = fence_core._read_back_at
            calls = {"count": 0}

            def remint_after_first_readback(dir_fd, name, expected_text):
                original(dir_fd, name, expected_text)
                calls["count"] += 1
                if calls["count"] == 1:
                    os.rename(parent, displaced)
                    os.mkdir(parent)

            fence_core._read_back_at = remint_after_first_readback
            try:
                with self.assertRaises(ValidationError):
                    fence_core.write_compilation(prefix, report, md, receipt)
            finally:
                fence_core._read_back_at = original
            self.assertEqual(os.listdir(displaced), [])
            self.assertEqual(os.listdir(parent), [])


if __name__ == "__main__":
    unittest.main()
