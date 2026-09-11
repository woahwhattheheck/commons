"""Focused checks for the V3.1 source-baseline package-integrity gate."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_v31_source_baseline as baseline  # noqa: E402


class PackageIntegrityGateTests(unittest.TestCase):
    def test_check_invokes_build_v3_check_and_propagates_failure(self):
        completed = mock.Mock(returncode=17)
        with mock.patch.object(baseline.subprocess, "run", return_value=completed) as run:
            self.assertEqual(baseline._check_package_integrity(), 17)

        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command, [sys.executable, "build_v3.py", "--check"])
        self.assertEqual(run.call_args.kwargs["cwd"], baseline.HERE)
        self.assertFalse(run.call_args.kwargs["check"])
        self.assertEqual(run.call_args.kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")

    def test_check_success_returns_zero(self):
        completed = mock.Mock(returncode=0)
        with mock.patch.object(baseline.subprocess, "run", return_value=completed):
            self.assertEqual(baseline._check_package_integrity(), 0)

    def test_failed_integrity_stops_before_source_materialization_or_suites(self):
        with (
            mock.patch.object(baseline, "_check_package_integrity", return_value=23) as check,
            mock.patch.object(baseline, "_materialize_source") as materialize,
            mock.patch.object(baseline.subprocess, "run") as run,
        ):
            self.assertEqual(baseline.run(), 23)

        check.assert_called_once_with()
        materialize.assert_not_called()
        run.assert_not_called()

    def test_failed_integrity_stops_before_external_tree_copy(self):
        package_tree = Path("unused-package-tree")
        with (
            mock.patch.object(baseline, "_check_package_integrity", return_value=29),
            mock.patch.object(baseline, "_copy_tree") as copy_tree,
        ):
            self.assertEqual(baseline.run(package_tree), 29)

        copy_tree.assert_not_called()


if __name__ == "__main__":
    unittest.main()
