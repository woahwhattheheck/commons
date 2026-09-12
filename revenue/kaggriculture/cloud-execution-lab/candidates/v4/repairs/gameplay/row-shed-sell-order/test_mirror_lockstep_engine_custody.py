# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import check_mirror_lockstep_engine as C


class MirrorLockstepEngineCustodyTests(unittest.TestCase):
    def test_engine_config_is_pinned_to_official_blob(self):
        self.assertEqual(
            C.ENGINE_CONFIG_BLOB,
            "b354d06b742fe48402513792253f1a5c29366b20",
        )

    def test_captured_dependency_survives_backing_path_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_path = root / "synthetic_engine.py"
            config_path = root / "kaggriculture.json"
            source = (
                "from pathlib import Path\n"
                "CONFIG = open(Path(__file__).with_name('kaggriculture.json')).read()\n"
            ).encode("utf-8")
            config_path.write_text("captured", encoding="utf-8")
            captured = config_path.read_bytes()
            config_path.write_text("attacker", encoding="utf-8")

            module = C.load_captured(
                "_rowshed_config_swap_control",
                module_path,
                source,
                text_captures={config_path: captured},
            )
            self.assertEqual(module.CONFIG, "captured")
            self.assertEqual(config_path.read_text(encoding="utf-8"), "attacker")

    def test_undeclared_engine_file_open_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_path = root / "synthetic_engine.py"
            config_path = root / "kaggriculture.json"
            other_path = root / "other.json"
            source = (
                "from pathlib import Path\n"
                "VALUE = open(Path(__file__).with_name('other.json')).read()\n"
            ).encode("utf-8")
            config_path.write_text("captured", encoding="utf-8")
            other_path.write_text("ambient", encoding="utf-8")

            with self.assertRaises(C.CheckError):
                C.load_captured(
                    "_rowshed_undeclared_open_control",
                    module_path,
                    source,
                    text_captures={config_path: config_path.read_bytes()},
                )


if __name__ == "__main__":
    unittest.main()
