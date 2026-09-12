from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import run_caresat_report as m


def blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class CareSatReportTrustTests(unittest.TestCase):
    def test_pins_match_reviewed_merged_sources(self):
        self.assertEqual(m.EXPECTED_ORACLE_BLOB, "efb612c7edebd920dd1f5b70da6c7f4a97e784d2")
        self.assertEqual(m.EXPECTED_CURRENT_CENSUS_BLOB, "d521dfcafd7d91287ec4cb18d6a29bfecc3627cd")

    def test_exact_regular_file_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = b"x = 1\n"
            (root / "x.py").write_bytes(data)
            self.assertEqual(m.verify_pinned_file(root, "x.py", blob(data)), (root / "x.py").resolve())

    def test_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.py").write_text("x = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(m.CareSatTrustError, "source drift"):
                m.verify_pinned_file(root, "x.py", blob(b"x = 1\n"))

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(m.CareSatTrustError, "unsafe path"):
                m.verify_pinned_file(Path(td), "../x.py", "0" * 40)

    def test_bad_pin_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.py").write_text("x=1\n", encoding="utf-8")
            with self.assertRaisesRegex(m.CareSatTrustError, "invalid expected Git blob"):
                m.verify_pinned_file(root, "x.py", "not-a-sha")

    def test_final_symlink_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "real.py"
            target.write_text("x=1\n", encoding="utf-8")
            try:
                (root / "x.py").symlink_to(target)
            except OSError:
                self.skipTest("symlink creation denied")
            with self.assertRaisesRegex(m.CareSatTrustError, "symlink ancestry"):
                m.verify_pinned_file(root, "x.py", blob(target.read_bytes()))

    def test_symlink_ancestor_rejected_even_inside_root(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real"
            real.mkdir()
            target = real / "x.py"
            target.write_text("x=1\n", encoding="utf-8")
            try:
                (root / "alias").symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation denied")
            with self.assertRaisesRegex(m.CareSatTrustError, "symlink ancestry"):
                m.verify_pinned_file(root, "alias/x.py", blob(target.read_bytes()))

    def test_tampered_oracle_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sentinel = root / "executed"
            oracle = root / m.ORACLE_NAME
            census = root / m.CURRENT_CENSUS_NAME
            oracle.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n", encoding="utf-8")
            census.write_text("x=1\n", encoding="utf-8")
            old_o, old_c = m.EXPECTED_ORACLE_BLOB, m.EXPECTED_CURRENT_CENSUS_BLOB
            try:
                m.EXPECTED_ORACLE_BLOB = "0" * 40
                m.EXPECTED_CURRENT_CENSUS_BLOB = blob(census.read_bytes())
                with self.assertRaisesRegex(m.CareSatTrustError, "source drift"):
                    m.load_authenticated_oracle(root)
                self.assertFalse(sentinel.exists())
            finally:
                m.EXPECTED_ORACLE_BLOB, m.EXPECTED_CURRENT_CENSUS_BLOB = old_o, old_c

    def test_tampered_census_rejected_before_oracle_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sentinel = root / "oracle-executed"
            oracle = root / m.ORACLE_NAME
            census = root / m.CURRENT_CENSUS_NAME
            oracle.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n", encoding="utf-8")
            census.write_text("x=2\n", encoding="utf-8")
            old_o, old_c = m.EXPECTED_ORACLE_BLOB, m.EXPECTED_CURRENT_CENSUS_BLOB
            try:
                m.EXPECTED_ORACLE_BLOB = blob(oracle.read_bytes())
                m.EXPECTED_CURRENT_CENSUS_BLOB = "0" * 40
                with self.assertRaisesRegex(m.CareSatTrustError, "source drift"):
                    m.load_authenticated_oracle(root)
                self.assertFalse(sentinel.exists())
            finally:
                m.EXPECTED_ORACLE_BLOB, m.EXPECTED_CURRENT_CENSUS_BLOB = old_o, old_c


if __name__ == "__main__":
    unittest.main()
