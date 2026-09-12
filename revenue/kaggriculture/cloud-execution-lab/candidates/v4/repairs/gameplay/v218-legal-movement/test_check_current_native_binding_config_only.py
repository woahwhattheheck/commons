#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import check_current_native_binding as gate


class V218ConfigOnlyBindingRegression(unittest.TestCase):
    def test_disabled_config_key_without_source_consumer_is_not_wiring(self):
        """A dead/disabled config key is metadata, not an executable V218 binding."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "main.py").write_text(
                "def agent(observation, configuration=None): return {}\n",
                encoding="utf-8",
            )
            (root / "titan_runtime.py").write_text("class TitanAgent: pass\n", encoding="utf-8")
            (root / "TITAN-CONFIG.json").write_text(
                json.dumps({"consumer": "frozen", "r04_v218_movement_parity": False}),
                encoding="utf-8",
            )

            report = gate.audit(root)

            self.assertEqual(
                ["r04_v218_movement_parity"],
                report["config"]["v218_keys"],
                "the diagnostic must still expose the V218-shaped config key",
            )
            self.assertFalse(
                report["explicit_binding"],
                "config-key presence alone must not mint an executable binding",
            )
            self.assertFalse(report["wired"])
            self.assertEqual("BLOCKED_AT_NATIVE_ASSEMBLY", report["disposition"])


if __name__ == "__main__":
    unittest.main()
