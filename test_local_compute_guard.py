from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import local_compute_guard as guard


class LocalComputeGuardTests(unittest.TestCase):
    def test_current_tree_is_cloud_only(self):
        self.assertEqual(guard.validate(), [])

    def test_android_autostart_regression_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rule in guard.RULES:
                source = guard.ROOT / rule.path
                target = root / rule.path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            for name in guard.RETIRED_HOST_EVALUATORS:
                source = guard.ROOT / name
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            registration = root / "host/titan_hands/register_codex.ps1"
            registration.write_text(
                registration.read_text(encoding="utf-8").replace(
                    "TITAN_HANDS_ANDROID_AUTOSTART=0",
                    "TITAN_HANDS_ANDROID_AUTOSTART=1",
                ),
                encoding="utf-8",
            )
            errors = guard.validate(root)
            self.assertTrue(any("AUTOSTART=1" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
